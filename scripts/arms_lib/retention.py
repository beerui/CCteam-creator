"""90-day retention cleanup."""
import sqlite3
import time

_NINETY_DAYS_SECS = 90 * 24 * 3600


def cleanup_old(conn: sqlite3.Connection, *, now: int = None) -> dict:
    """删除 90 天前的 resolved/ignored fingerprints 和所有过期 occurrences.

    保留: status='analyzed' (不论多老) + 所有 meta.

    返回: dict(fingerprints=N, occurrences=N) 被删数量.
    """
    if now is None:
        now = int(time.time())
    cutoff = now - _NINETY_DAYS_SECS

    fp_cursor = conn.execute(
        """DELETE FROM fingerprints
           WHERE status IN ('resolved', 'ignored')
             AND resolved_at IS NOT NULL
             AND resolved_at < ?""",
        (cutoff,),
    )
    fp_deleted = fp_cursor.rowcount

    occ_cursor = conn.execute(
        "DELETE FROM occurrences WHERE occurred_at < ?",
        (cutoff,),
    )
    occ_deleted = occ_cursor.rowcount

    conn.commit()
    return {"fingerprints": fp_deleted, "occurrences": occ_deleted}
