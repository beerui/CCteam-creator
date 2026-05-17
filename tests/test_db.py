"""Tests for arms_lib.db."""
import sqlite3
import time
import pytest
from arms_lib.db import (
    init_schema,
    insert_fingerprint,
    update_fingerprint_status,
    select_fingerprint_match,
    upsert_meta,
    get_meta,
)


def test_init_schema_creates_three_tables(tmp_db_path):
    conn = sqlite3.connect(tmp_db_path)
    init_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"fingerprints", "occurrences", "meta"}.issubset(tables)
    conn.close()


def test_init_schema_is_idempotent(tmp_db_path):
    conn = sqlite3.connect(tmp_db_path)
    init_schema(conn)
    init_schema(conn)
    conn.close()


def test_insert_and_select_fingerprint(empty_db_conn):
    now = int(time.time())
    insert_fingerprint(empty_db_conn, dict(
        task_id="arms-20260517-001",
        conv_message="conv list failed: 33001",
        stack_top_frame="conv.js:onResponse",
        view_name="/agent",
        env="daily",
        app="大集客服",
        pid="c67xxx",
        status="analyzed",
        created_at=now,
        last_seen_at=now,
        last_seen_count=8,
    ))
    row = select_fingerprint_match(
        empty_db_conn,
        conv_message="conv list failed: 33001",
        stack_top_frame="conv.js:onResponse",
        env="daily",
    )
    assert row is not None
    assert row["task_id"] == "arms-20260517-001"
    assert row["status"] == "analyzed"


def test_select_no_match_returns_none(empty_db_conn):
    row = select_fingerprint_match(
        empty_db_conn,
        conv_message="never seen",
        stack_top_frame="x:y",
        env="prod",
    )
    assert row is None


def test_update_fingerprint_status(empty_db_conn):
    now = int(time.time())
    insert_fingerprint(empty_db_conn, dict(
        task_id="arms-20260517-002",
        conv_message="x", stack_top_frame="y", env="prod",
        app="A", pid="P", status="analyzed", created_at=now,
        last_seen_at=now, last_seen_count=1,
    ))
    update_fingerprint_status(
        empty_db_conn, "arms-20260517-002",
        status="resolved",
        resolved_at=now + 100,
        commit_hash="abc1234",
        branch="fix/arms-20260517-002",
        resolved_by="frontend-dev",
    )
    row = empty_db_conn.execute(
        "SELECT status, resolved_at, commit_hash FROM fingerprints WHERE task_id=?",
        ("arms-20260517-002",)
    ).fetchone()
    assert row[0] == "resolved"
    assert row[1] == now + 100
    assert row[2] == "abc1234"


def test_meta_upsert_and_get(empty_db_conn):
    assert get_meta(empty_db_conn, "last_global_scan") is None
    upsert_meta(empty_db_conn, "last_global_scan", "1716000000")
    assert get_meta(empty_db_conn, "last_global_scan") == "1716000000"
    upsert_meta(empty_db_conn, "last_global_scan", "1716003600")
    assert get_meta(empty_db_conn, "last_global_scan") == "1716003600"


def test_init_schema_sets_row_factory(tmp_db_path):
    """init_schema 应该把 row_factory 设成 sqlite3.Row, 让所有后续 query 返回 Row."""
    conn = sqlite3.connect(tmp_db_path)
    init_schema(conn)
    assert conn.row_factory is sqlite3.Row
    conn.close()


def test_init_schema_enables_foreign_keys(tmp_db_path):
    """init_schema 应该开启 PRAGMA foreign_keys."""
    conn = sqlite3.connect(tmp_db_path)
    init_schema(conn)
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1
    conn.close()
