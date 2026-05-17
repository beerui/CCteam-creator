"""Tests for arms_lib.retention."""
import time
from arms_lib.db import insert_fingerprint
from arms_lib.retention import cleanup_old

NINETY_DAYS = 90 * 24 * 3600


def _insert(conn, task_id, status, created_at, resolved_at=None):
    insert_fingerprint(conn, dict(
        task_id=task_id,
        conv_message=f"msg-{task_id}",
        stack_top_frame=f"f.js:{task_id}",
        env="prod",
        app="A",
        pid="P",
        status=status,
        resolved_at=resolved_at,
        created_at=created_at,
        last_seen_at=created_at,
        last_seen_count=1,
    ))


def test_resolved_older_than_90d_is_deleted(empty_db_conn):
    now = int(time.time())
    _insert(empty_db_conn, "old-resolved", "resolved",
            created_at=now - NINETY_DAYS - 100,
            resolved_at=now - NINETY_DAYS - 100)
    deleted = cleanup_old(empty_db_conn, now=now)
    assert deleted["fingerprints"] == 1
    rows = empty_db_conn.execute("SELECT * FROM fingerprints").fetchall()
    assert len(rows) == 0


def test_resolved_within_90d_kept(empty_db_conn):
    now = int(time.time())
    _insert(empty_db_conn, "recent-resolved", "resolved",
            created_at=now - 1000,
            resolved_at=now - 500)
    deleted = cleanup_old(empty_db_conn, now=now)
    assert deleted["fingerprints"] == 0
    rows = empty_db_conn.execute("SELECT * FROM fingerprints").fetchall()
    assert len(rows) == 1


def test_analyzed_never_deleted(empty_db_conn):
    """status='analyzed' 即使很老也不删 (怕删进行中任务)"""
    now = int(time.time())
    _insert(empty_db_conn, "old-analyzed", "analyzed",
            created_at=now - NINETY_DAYS * 2)
    deleted = cleanup_old(empty_db_conn, now=now)
    assert deleted["fingerprints"] == 0
    rows = empty_db_conn.execute("SELECT * FROM fingerprints").fetchall()
    assert len(rows) == 1


def test_ignored_older_than_90d_is_deleted(empty_db_conn):
    now = int(time.time())
    _insert(empty_db_conn, "old-ignored", "ignored",
            created_at=now - NINETY_DAYS - 100,
            resolved_at=now - NINETY_DAYS - 100)
    deleted = cleanup_old(empty_db_conn, now=now)
    assert deleted["fingerprints"] == 1


def test_occurrences_older_than_90d_deleted(empty_db_conn):
    now = int(time.time())
    _insert(empty_db_conn, "fp-with-occ", "analyzed", created_at=now - 1000)
    empty_db_conn.execute(
        "INSERT INTO occurrences(task_id, occurred_at, count, source) VALUES(?,?,?,?)",
        ("fp-with-occ", now - NINETY_DAYS - 100, 5, "scan"),
    )
    empty_db_conn.execute(
        "INSERT INTO occurrences(task_id, occurred_at, count, source) VALUES(?,?,?,?)",
        ("fp-with-occ", now - 100, 3, "scan"),
    )
    empty_db_conn.commit()
    deleted = cleanup_old(empty_db_conn, now=now)
    assert deleted["occurrences"] == 1
    assert empty_db_conn.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0] == 1


def test_meta_not_touched(empty_db_conn):
    from arms_lib.db import upsert_meta, get_meta
    upsert_meta(empty_db_conn, "last_global_scan", "12345")
    cleanup_old(empty_db_conn, now=int(time.time()))
    assert get_meta(empty_db_conn, "last_global_scan") == "12345"
