#!/usr/bin/env python3
"""Claude Code SessionStart hook entry.

Logic:
  1. 检查 meta.last_global_scan; 距今 ≤24h → exit 0 无输出
  2. >24h 或 db 不存在 → 数据采集 + 写 inbox.md + stdout brief
  3. 失败 → stderr 错误 + brief 写'巡检失败', exit 0 (不阻塞 IDE 启动)

性能预算: ≤15s
"""
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arms_lib.db import init_schema, get_meta, upsert_meta, select_fingerprint_match, insert_fingerprint
from arms_lib.inbox import render_inbox
from arms_lib.retention import cleanup_old


_TWENTY_FOUR_H = 24 * 3600
_BRIEF_OPEN = "<arms-session-context>"
_BRIEF_CLOSE = "</arms-session-context>"


def _emit_brief(body: str) -> None:
    """把 brief 字符串包装并打到 stdout (供 Claude Code SessionStart 注入)."""
    print(f"{_BRIEF_OPEN}\n{body.strip()}\n{_BRIEF_CLOSE}")


def _emit_failure(reason: str) -> None:
    _emit_brief(f"ARMS 巡检失败: {reason}\n手动重试: `/arms env=prod days=1`")


def _ensure_db(arms_dir: Path) -> sqlite3.Connection:
    """打开或创建 archive.db, 必要时调 migrate 脚本."""
    db_path = arms_dir / "archive.db"
    if not db_path.exists():
        migrate = Path(__file__).parent / "arms-migrate-archive.py"
        subprocess.run(
            [sys.executable, str(migrate), "--arms-dir", str(arms_dir)],
            check=True,
            timeout=10,
        )
    conn = sqlite3.connect(db_path)
    init_schema(conn)
    return conn


def _run_scan(conn: sqlite3.Connection) -> dict:
    """跑数据采集. 返回 dict(new=[], recurring=[], in_progress=[]).

    失败抛异常, 由上层 catch.
    """
    from arms_lib.sls import query_exceptions, aggregate_exceptions

    pid = os.environ.get("ARMS_PID")
    if not pid:
        raise RuntimeError("缺少 ARMS_PID 环境变量 (从 .env 加载)")

    logs = query_exceptions(pid=pid, env="prod", days=1, line=500)
    aggregated = aggregate_exceptions(logs)

    now = int(time.time())
    new_items, recurring_items = [], []

    for agg in aggregated:
        existing = select_fingerprint_match(
            conn,
            conv_message=agg["conv_message"],
            stack_top_frame=agg["stack_top_frame"],
            env=agg["env"],
        )
        if existing is None:
            # 新 → 生成 task_id 并 INSERT
            date_part = datetime.now().strftime("%Y%m%d")
            seq = conn.execute(
                "SELECT COUNT(*) FROM fingerprints WHERE task_id LIKE ?",
                (f"arms-{date_part}-%",),
            ).fetchone()[0] + 1
            task_id = f"arms-{date_part}-{seq:03d}"
            insert_fingerprint(conn, dict(
                task_id=task_id,
                conv_message=agg["conv_message"],
                stack_top_frame=agg["stack_top_frame"],
                view_name=agg["view_name"],
                env=agg["env"],
                app=agg["app"],
                pid=agg["pid"],
                status="analyzed",
                created_at=now,
                last_seen_at=now,
                last_seen_count=agg["count"],
            ))
            new_items.append({
                "task_id": task_id,
                "severity": "P2" if agg["count"] >= 5 else "P3",
                "conv_message": agg["conv_message"],
                "stack_top_frame": agg["stack_top_frame"],
                "env": agg["env"],
                "count": agg["count"],
            })
        elif existing["status"] == "resolved":
            recurring_items.append({
                "task_id": existing["task_id"],
                "severity": "P3",
                "conv_message": existing["conv_message"],
                "last_commit_hash": existing.get("commit_hash") or "<unknown>",
                "last_resolved_at": datetime.fromtimestamp(
                    existing.get("resolved_at") or now
                ).strftime("%Y-%m-%d"),
                "current_count": agg["count"],
                "current_date": datetime.now().strftime("%Y-%m-%d"),
            })

    # 进行中: status='analyzed' 且 last_seen_at within 30d
    cutoff = now - 30 * 86400
    in_progress_rows = conn.execute(
        """SELECT task_id, resolved_by, branch FROM fingerprints
           WHERE status='analyzed' AND last_seen_at >= ?
           ORDER BY last_seen_at DESC""",
        (cutoff,),
    ).fetchall()
    in_progress = [
        {
            "task_id": r[0],
            "assignee": r[1] or "<待派单>",
            "branch": r[2] or "<未建分支>",
        }
        for r in in_progress_rows
    ]

    return {"new": new_items, "recurring": recurring_items, "in_progress": in_progress}


def main() -> int:
    arms_dir_str = os.environ.get("ARMS_DIR")
    if not arms_dir_str:
        # 默认: 当前 cwd 下 .plans/<project>/arms/, project 用目录名
        cwd = Path.cwd()
        arms_dir_str = str(cwd / ".plans" / cwd.name / "arms")
    arms_dir = Path(arms_dir_str)
    arms_dir.mkdir(parents=True, exist_ok=True)

    try:
        conn = _ensure_db(arms_dir)
    except Exception as e:
        _emit_failure(f"db 初始化失败: {e}")
        return 0

    try:
        last_scan = get_meta(conn, "last_global_scan")
        if last_scan and (int(time.time()) - int(last_scan)) <= _TWENTY_FOUR_H:
            # 24h 内不重扫
            return 0

        cleanup_old(conn)
        result = _run_scan(conn)
        upsert_meta(conn, "last_global_scan", str(int(time.time())))

        # 写 inbox.md
        inbox_md = render_inbox(
            last_scan_iso=datetime.now().strftime("%Y-%m-%d %H:%M"),
            **result,
        )
        (arms_dir / "inbox.md").write_text(inbox_md, encoding="utf-8")

        # 输出 brief
        n_new = len(result["new"])
        n_rec = len(result["recurring"])
        n_prog = len(result["in_progress"])

        body_lines = [
            f"ARMS 巡检: 已自动扫描 prod env 最近 24h.",
            "",
            f"- 🆕 新增指纹 {n_new} 条",
            f"- 🔁 复发指纹 {n_rec} 条" + (
                " (建议复审)" if n_rec else ""
            ),
            f"- ⏳ 进行中 {n_prog} 条",
        ]
        if result["new"]:
            first = result["new"][0]
            body_lines.append("")
            body_lines.append(
                f'首条新增: "{first["conv_message"]}" @ '
                f'{first["stack_top_frame"]} ({first["count"]} 次, {first["env"]})'
            )
        body_lines.extend([
            "",
            f"完整列表: {arms_dir / 'inbox.md'}",
            "深挖某条 → /arms task=<task-id>; 忽略 → 不动作",
        ])
        _emit_brief("\n".join(body_lines))

    except Exception as e:
        _emit_failure(str(e))
        print(f"arms-on-session error: {e}", file=sys.stderr)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
