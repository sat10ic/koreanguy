"""SQLite connection + schema init for traderlog.db.

Adopted from manas_os/db/__init__.py (2026-08-23), including the production-DB
test guard -- that guard exists because the live 717MB manas.db was once
polluted with synthetic fixture rows by an ad-hoc script that called init_db()
with no argument. Same failure mode, same fix, before it can happen here.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = _DB_DIR / "traderlog.db"
_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def now_iso() -> str:
    """UTC timestamp for ingested_at columns. One helper so the format is uniform."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with sane defaults (row factory + FK + WAL).

    Refuses to fall back to the real DB_PATH from inside a test run. Tests must
    pass an isolated path (tmp_path / "traderlog.db"); a test that genuinely
    wants the real database passes DB_PATH explicitly.
    """
    if (
        db_path is None
        and os.environ.get("PYTEST_CURRENT_TEST")
        and not os.environ.get("TRADERLOG_ALLOW_PROD_DB_IN_TESTS")
    ):
        raise RuntimeError(
            "Refusing to open the production traderlog.db from inside a test run "
            "with no explicit db_path. Pass an isolated path (e.g. "
            "tmp_path / 'traderlog.db'), or set TRADERLOG_ALLOW_PROD_DB_IN_TESTS=1 "
            "for an intentional real-DB check."
        )
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create all tables (idempotent) and ensure singleton rows exist.

    schema.sql re-runs on every call, so a brand-new CREATE TABLE IF NOT EXISTS
    retrofits an existing traderlog.db with no extra step. Adding a COLUMN to a
    table that already exists on disk needs _migrate_add_columns below -- editing
    the CREATE statement in schema.sql does nothing to existing databases.
    """
    conn = connect(db_path)
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.execute("INSERT OR IGNORE INTO settings (id, data_json) VALUES (1, '{}')")
    # Column migrations. Editing a CREATE TABLE in schema.sql does nothing to a
    # database that already exists -- add the column here as well, or existing
    # installs silently diverge from fresh ones.
    _migrate_add_columns(conn, "post_class", {
        # W0: every content table must be able to declare itself mock, so that
        # seed_mock.py --clear can remove seeded rows without touching real ones.
        "is_mock": "INTEGER NOT NULL DEFAULT 0",
        # W0 (attention engine spec): captured on the FIRST classification pass.
        # Adding these later would mean re-running every historical post through
        # an LLM to backfill them. See design/ATTENTION_ENGINE.md §5.
        "play_type": "TEXT",
        "conviction_words": "TEXT",
    })
    # Indexes on migration-added columns belong here, after the ALTERs -- putting
    # them in schema.sql fails on an existing database, because that file runs
    # first.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_post_class_play ON post_class(play_type)"
    )
    conn.commit()
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_add_columns(
    conn: sqlite3.Connection, table: str, cols: dict[str, str]
) -> None:
    """ADD COLUMN for any of `cols` not already present on `table`. Idempotent."""
    have = _existing_columns(conn, table)
    for name, ddl in cols.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    sql = f"SELECT COUNT(*) FROM {table}"  # noqa: S608 - table names are internal
    if where:
        sql += f" WHERE {where}"
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row else 0
