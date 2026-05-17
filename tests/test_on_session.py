"""Tests for arms-on-session.py main flow."""
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).parent.parent / "scripts" / "arms-on-session.py"


def _run(env_dict, extra_args=None):
    args = [sys.executable, str(SCRIPT)] + (extra_args or [])
    r = subprocess.run(args, env=env_dict, capture_output=True, text=True)
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
