"""Deletion detection that preserves both database rows and first-sight archives."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from traderlog.db import now_iso


def _log_run(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    status: str,
    rows: int,
    detail: str,
) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs "
        "(stage,run_date,status,rows,duration_ms,detail,ts) "
        "VALUES ('ingest.deletions',?,?,?,?,?,?)",
        (run_date, status, rows, 0, detail, now_iso()),
    )


def mark_missing_posts(
    conn: sqlite3.Connection,
    handle: str,
    *,
    seen_post_ids: set[str],
    observed_since: str | None,
    observed_until: str | None = None,
    deleted_at: str | None = None,
) -> int:
    """Stamp unseen posts only inside a successfully observed timeline window.

    An empty result or an unbounded first fetch is not evidence of deletion. That
    conservative rule prevents a login failure or partial page from mass-marking
    history as deleted.
    """
    deleted_at = deleted_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_date = deleted_at[:10]
    if not seen_post_ids or not observed_since:
        with conn:
            _log_run(
                conn,
                run_date=run_date,
                status="skip",
                rows=0,
                detail="no bounded non-empty observation window",
            )
        return 0

    observed_until = observed_until or deleted_at
    candidates = conn.execute(
        "SELECT post_id FROM posts "
        "WHERE handle=? AND is_mock=0 AND deleted_at IS NULL "
        "AND ts_utc>=? AND ts_utc<=?",
        (handle, observed_since, observed_until),
    ).fetchall()
    missing = [row["post_id"] for row in candidates if row["post_id"] not in seen_post_ids]

    with conn:
        conn.executemany(
            "UPDATE posts SET deleted_at=? WHERE post_id=? AND deleted_at IS NULL",
            [(deleted_at, post_id) for post_id in missing],
        )
        _log_run(
            conn,
            run_date=run_date,
            status="ok",
            rows=len(missing),
            detail=json.dumps(
                {
                    "handle": handle,
                    "observed_since": observed_since,
                    "observed_until": observed_until,
                },
                sort_keys=True,
            ),
        )
    return len(missing)
