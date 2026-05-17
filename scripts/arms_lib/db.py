"""SQLite schema + CRUD for ARMS archive."""
import sqlite3
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fingerprints (
  task_id           TEXT PRIMARY KEY,
  conv_message      TEXT NOT NULL,
  stack_top_frame   TEXT NOT NULL,
  view_name         TEXT,
  env               TEXT NOT NULL,
  app               TEXT NOT NULL,
  pid               TEXT NOT NULL,
  status            TEXT NOT NULL,
  resolved_by       TEXT,
  commit_hash       TEXT,
  branch            TEXT,
  created_at        INTEGER NOT NULL,
  resolved_at       INTEGER,
  last_seen_at      INTEGER,
  last_seen_count   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_fp_match
  ON fingerprints(conv_message, stack_top_frame, env);
CREATE INDEX IF NOT EXISTS idx_fp_status_resolved
  ON fingerprints(status, resolved_at);

CREATE TABLE IF NOT EXISTS occurrences (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id     TEXT NOT NULL REFERENCES fingerprints(task_id) ON DELETE CASCADE,
  occurred_at INTEGER NOT NULL,
  count       INTEGER NOT NULL,
  source      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_occ_task
  ON occurrences(task_id, occurred_at);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """创建 3 表 + 索引 (幂等)."""
    conn.executescript(_SCHEMA)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.commit()


def insert_fingerprint(conn: sqlite3.Connection, fields: dict) -> None:
    """INSERT 一条 fingerprint."""
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    conn.execute(
        f"INSERT INTO fingerprints ({cols}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    conn.commit()


def update_fingerprint_status(
    conn: sqlite3.Connection,
    task_id: str,
    *,
    status: str,
    resolved_at: Optional[int] = None,
    commit_hash: Optional[str] = None,
    branch: Optional[str] = None,
    resolved_by: Optional[str] = None,
) -> None:
    """转移 fingerprint 到终态 (resolved / ignored), 写入解析元数据.

    注意: 该函数把 resolved_at/commit_hash/branch/resolved_by 全部写入 (未传则置 NULL),
    不适合用来增量更新 last_seen_*; 后者请用原生 SQL.
    """
    conn.execute(
        """UPDATE fingerprints SET
           status=?, resolved_at=?, commit_hash=?, branch=?, resolved_by=?
           WHERE task_id=?""",
        (status, resolved_at, commit_hash, branch, resolved_by, task_id),
    )
    conn.commit()


def select_fingerprint_match(
    conn: sqlite3.Connection,
    *,
    conv_message: str,
    stack_top_frame: str,
    env: str,
) -> Optional[dict]:
    """精确匹配 (conv_message + stack_top_frame + env). 返回单行 dict 或 None."""
    row = conn.execute(
        """SELECT * FROM fingerprints
           WHERE conv_message=? AND stack_top_frame=? AND env=?
           LIMIT 1""",
        (conv_message, stack_top_frame, env),
    ).fetchone()
    return dict(row) if row else None


def upsert_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """meta key-value upsert."""
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None
