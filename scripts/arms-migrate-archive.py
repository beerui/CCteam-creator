#!/usr/bin/env python3
"""一次性把旧 archive/index.md 迁到 archive.db.

无旧文件 → 创建空 db.
有旧文件 → 解析行并插入, 旧文件改名 .legacy.
幂等: 重复运行不报错也不重复插入.
"""
import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arms_lib.db import init_schema, upsert_meta

_ROW_RE = re.compile(
    r"\|\s*(arms-\d{8}-\d{3})\s*\|\s*(.+?)\s*\|\s*(P\d|N/A)\s*\|\s*(\w+)\s*\|\s*([\w-]*)\s*\|\s*(.*?)\s*\|"
)
_FP_RE = re.compile(r"^(.+?)\s+@\s+(.+)$")


def parse_index_md(content: str) -> list[dict]:
    """解析 markdown 月度表格, 返回 list[dict]."""
    rows = []
    for line in content.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        task_id, fp_str, severity, env, resolved_by, _resolution = m.groups()
        fp_m = _FP_RE.match(fp_str)
        if fp_m:
            conv_message, view_name = fp_m.groups()
        else:
            conv_message, view_name = fp_str, ""
        rows.append({
            "task_id": task_id,
            "conv_message": conv_message,
            "view_name": view_name,
            "env": env,
            "resolved_by": resolved_by or None,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms-dir", required=True, type=Path,
                        help="项目的 arms 目录 (e.g. .plans/<project>/arms/)")
    args = parser.parse_args()

    arms_dir: Path = args.arms_dir
    arms_dir.mkdir(parents=True, exist_ok=True)

    db_path = arms_dir / "archive.db"
    conn = sqlite3.connect(db_path)
    init_schema(conn)
    upsert_meta(conn, "schema_version", "1.0")

    index_path = arms_dir / "archive" / "index.md"
    if index_path.exists():
        rows = parse_index_md(index_path.read_text(encoding="utf-8"))
        now = int(time.time())
        for r in rows:
            existing = conn.execute(
                "SELECT 1 FROM fingerprints WHERE task_id=?", (r["task_id"],)
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO fingerprints (
                    task_id, conv_message, stack_top_frame, view_name,
                    env, app, pid, status, resolved_by, created_at,
                    last_seen_at, last_seen_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["task_id"],
                    r["conv_message"],
                    "<legacy>",
                    r["view_name"],
                    r["env"],
                    "<unknown>",
                    "<unknown>",
                    "resolved",
                    r["resolved_by"],
                    now,
                    now,
                    0,
                ),
            )
        conn.commit()
        index_path.rename(index_path.with_suffix(".md.legacy"))

    conn.close()
    print(f"migration ok: {db_path}")


if __name__ == "__main__":
    main()
