"""Tests for arms-migrate-archive.py."""
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "arms-migrate-archive.py"


def _run(arms_dir):
    """运行 migrate 脚本, 返回 (exit_code, stdout, stderr)."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--arms-dir", str(arms_dir)],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout, r.stderr


def test_migrate_with_no_existing_index_creates_empty_db(tmp_path):
    """目录无旧 archive/index.md → 创建空 db, schema 已 init."""
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    code, _, _ = _run(arms_dir)
    assert code == 0

    db_path = arms_dir / "archive.db"
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"fingerprints", "occurrences", "meta"}.issubset(tables)

    sv = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert sv[0] == "1.0"
    conn.close()


def test_migrate_with_existing_index_imports_rows(tmp_path):
    """有旧 archive/index.md → 解析并导入 db, 旧文件改名 .legacy"""
    arms_dir = tmp_path / "arms"
    archive_dir = arms_dir / "archive"
    archive_dir.mkdir(parents=True)

    (archive_dir / "index.md").write_text("""# ARMS Archive Index

## 2026-05
| task-id | fingerprint | severity | env | resolved_by | resolution |
|---------|-------------|----------|-----|-------------|------------|
| arms-20260514-001 | token无效或已过期 @ /agent | P3 | daily | backend-dev | fix/arms-20260514-001 |
| arms-20260514-002 | conv list failed: 33001 @ /agent | P2 | daily | backend-dev | fix/arms-20260514-002 |
""")

    code, _, _ = _run(arms_dir)
    assert code == 0

    db_path = arms_dir / "archive.db"
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT task_id, conv_message, view_name, env, stack_top_frame FROM fingerprints ORDER BY task_id"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0] == ("arms-20260514-001", "token无效或已过期", "/agent", "daily", "<legacy>")
    assert rows[1] == ("arms-20260514-002", "conv list failed: 33001", "/agent", "daily", "<legacy>")
    conn.close()

    assert not (archive_dir / "index.md").exists()
    assert (archive_dir / "index.md.legacy").exists()


def test_migrate_is_idempotent(tmp_path):
    """重复运行不应报错, 不应 duplicate insert."""
    arms_dir = tmp_path / "arms"
    arms_dir.mkdir()

    _run(arms_dir)
    code2, _, stderr = _run(arms_dir)
    assert code2 == 0, stderr
