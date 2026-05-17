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

    覆盖集成者最常踩的坑: 不加 load_dotenv() 时 VITE_APP_ARMS_PID 读不到,
    所有接入项目首次开 session 必看到'巡检失败'.
    """
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    # 写 .env 到 tmp_path 根 (作为子进程 cwd)
    (tmp_path / ".env").write_text(
        '# arms creds\n'
        'VITE_APP_ARMS_PID="from-dotenv-123"\n'
        "SLS_REGION=cn-hangzhou\n",
        encoding="utf-8",
    )

    # 不在 env 里传 VITE_APP_ARMS_PID, 只在 .env 里给; 若 _load_dotenv 生效则报错信息会变
    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    # VITE_APP_ARMS_PID 已被 .env 提供, 失败原因不再是"缺少 VITE_APP_ARMS_PID"
    # (会改为缺少 ARMS_AK_ID 等下游变量)
    assert "缺少 VITE_APP_ARMS_PID" not in out


def test_dotenv_does_not_override_existing_env(tmp_path):
    """env 中已存在的 key 优先, .env 不覆盖.

    Why: CI / 临时 export 凭证场景下, .env 不能反向覆盖, 否则调试体验崩坏.
    """
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    (tmp_path / ".env").write_text("VITE_APP_ARMS_PID=from-dotenv\n", encoding="utf-8")

    # env 里已有 VITE_APP_ARMS_PID, .env 不应覆盖
    env = {
        "PATH": "/usr/bin:/bin",
        "ARMS_DIR": str(arms_dir),
        "VITE_APP_ARMS_PID": "from-real-env",
    }
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    # 两种情况都说明 _load_dotenv 没覆盖: 不出现 "from-dotenv"
    assert "from-dotenv" not in out


def test_brief_uses_default_env_from_config(tmp_path):
    """config.json 含 default_env=test → 失败 brief 提示用 env=test 重试.

    Why: 文档承诺 hook 读 default_env, 否则集成者想跑"测试服日常巡检"走不通.
    用 _emit_failure 路径的"重试命令"作可观察信号 (brief 中含 env=test).
    """
    import json as _json

    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    (arms_dir / "config.json").write_text(
        _json.dumps({"default_env": "test"}), encoding="utf-8"
    )

    # 不提供凭证 → 走 _emit_failure 路径, brief 应建议 env=test
    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    assert "env=test" in out


def test_brief_falls_back_to_prod_when_no_config(tmp_path):
    """config.json 不存在 → 维持原有 prod 默认值"""
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    env = {"PATH": "/usr/bin:/bin", "ARMS_DIR": str(arms_dir)}
    code, out, _ = _run(env, cwd=str(tmp_path))
    assert code == 0
    assert "env=prod" in out


def test_run_scan_sorts_new_items_by_count_desc(tmp_path, monkeypatch):
    """_run_scan 返回的 new 列表按 count desc 排序, 让 brief 的'首条新增'选最值得 highlight 的.

    Why: T16 e2e 发现 brief 把 count=2 的 getEntries 排在 count=1 的 CSS preload 后,
    被 fingerprint 表查询顺序覆盖了优先级.
    """
    monkeypatch.setenv("VITE_APP_ARMS_PID", "test-pid")

    import importlib.util
    spec = importlib.util.spec_from_file_location("arms_on_session", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 假数据: 3 条新指纹, count 各不同; 用 mock 替掉 query_exceptions
    from arms_lib.db import init_schema
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()
    conn = sqlite3.connect(arms_dir / "archive.db")
    init_schema(conn)

    fake_logs = []
    for conv, frame_url, count in [
        ("low",  "https://x/a.js", 2),
        ("high", "https://x/b.js", 8),
        ("mid",  "https://x/c.js", 5),
    ]:
        for i in range(count):
            fake_logs.append({
                "__time__": str(1716000000 + i),
                "app.id": "p", "app.name": "a", "app.env": "prod",
                "view.name": "/v", "view.name.convergence": "/v",
                "exception.message": conv,
                "exception.message.convergence": conv,
                "exception.stack": f"TypeError\n    at fn ({frame_url}:1:1)",
                "event_id": f"e{count}-{i}", "session.id": f"s{count}-{i}",
            })

    with mock.patch("arms_lib.sls.query_exceptions", return_value=fake_logs):
        result = mod._run_scan(conn, env="prod")

    counts = [item["count"] for item in result["new"]]
    assert counts == sorted(counts, reverse=True)
    assert result["new"][0]["conv_message"] == "high"
    conn.close()
