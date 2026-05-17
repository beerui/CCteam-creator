"""Tests for arms-on-session.py main flow."""
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).parent.parent / "scripts" / "arms-on-session.py"


def _run(env_dict, extra_args=None, cwd=None):
    args = [sys.executable, str(SCRIPT)] + (extra_args or [])
    r = subprocess.run(args, env=env_dict, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def test_skips_if_last_scan_within_24h(tmp_path):
    """meta.last_global_scan 距今 ≤24h → exit 0 + 无 stdout"""
    from arms_lib.db import init_schema, upsert_meta

    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    conn = sqlite3.connect(arms_dir / "archive.db")
    init_schema(conn)
    upsert_meta(conn, "last_global_scan", str(int(time.time()) - 3600))  # 1h ago
    conn.close()

    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, err = _run(env)
    assert code == 0
    assert "<arms-session-context>" not in out


def test_emits_brief_when_overdue_with_no_creds(tmp_path):
    """无凭证时 brief 包含'巡检失败'但 exit 0 (不阻塞 Claude Code 启动)"""
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, err = _run(env)
    assert code == 0
    assert "<arms-session-context>" in out
    assert "巡检失败" in out or "无凭证" in out


def test_missing_db_triggers_migrate_then_scan(tmp_path):
    """archive.db 不存在 → 自动触发 migrate (创建空 db)"""
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, err = _run(env)
    # 即使 SLS 失败, db 也应被创建
    assert (arms_dir / "archive.db").exists()


def test_scan_failure_does_not_persist_last_global_scan(tmp_path):
    """扫描失败 (无凭证) 时 last_global_scan 不能被写入,
    否则下次 24h 内静默跳过, 用户彻底看不到 brief."""
    from arms_lib.db import get_meta

    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, _ = _run(env)
    assert code == 0
    assert "巡检失败" in out or "无凭证" in out

    # 关键: meta.last_global_scan 必须未写入, 让下次 session 还能重试
    conn = sqlite3.connect(arms_dir / "archive.db")
    assert get_meta(conn, "last_global_scan") is None
    conn.close()


def test_dotenv_is_loaded_from_cwd(tmp_path):
    """cwd 下存在 .env → 其中的变量进入 os.environ.

    覆盖集成者最常踩的坑: 不加 load_dotenv() 时 ARMS_PID 读不到,
    所有接入项目首次开 session 必看到'巡检失败'.
    """
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    # 写 .env 到 tmp_path 根 (作为子进程 cwd)
    (tmp_path / ".env").write_text(
        '# arms creds\n'
        'ARMS_PID="from-dotenv-123"\n'
        "ARMS_REGION=cn-hangzhou\n",
        encoding="utf-8",
    )

    # 不在 env 里传 ARMS_PID, 只在 .env 里给; 若 _load_dotenv 生效则报错信息会变
    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    # ARMS_PID 已被 .env 提供, 失败原因不再是"缺少 ARMS_PID"
    # (会改为缺少 ARMS_AK_ID 等下游变量)
    assert "缺少 ARMS_PID" not in out


def test_dotenv_does_not_override_existing_env(tmp_path):
    """env 中已存在的 key 优先, .env 不覆盖.

    Why: CI / 临时 export 凭证场景下, .env 不能反向覆盖, 否则调试体验崩坏.
    """
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    (tmp_path / ".env").write_text("ARMS_PID=from-dotenv\n", encoding="utf-8")

    # env 里已有 ARMS_PID, .env 不应覆盖
    env = {
        "PATH": "/usr/bin:/bin",
        "ARMS_DIR": str(arms_dir),
        "ARMS_PID": "from-real-env",
    }
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    # 两种情况都说明 _load_dotenv 没覆盖: 不出现 "from-dotenv"
    assert "from-dotenv" not in out
