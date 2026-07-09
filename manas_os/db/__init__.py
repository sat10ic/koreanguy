"""SQLite connection + schema init for manas.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = _DB_DIR / "manas.db"
_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with sane defaults (row factory + FK + WAL)."""
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create all tables (idempotent) and ensure the singleton settings row exists.

    Also runs lightweight in-place column migrations (ADD COLUMN guarded by a
    pragma check) so an existing manas.db upgrades transparently — we don't
    keep a separate migration framework for a single-user local tool.
    """
    conn = connect(db_path)
    # executescript re-runs on every init_db call, so brand-new
    # CREATE TABLE IF NOT EXISTS tables (e.g. screener_hits, symbol_quality)
    # retrofit an already-initialized manas.db with no extra step. The
    # ALTER-based _migrate_add_columns below is only needed for adding
    # columns to tables that already existed on disk.
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    conn.execute("INSERT OR IGNORE INTO settings (id, data_json) VALUES (1, '{}')")
    _migrate_add_columns(conn, "sector_metrics", {
        "mars_score": "REAL",
        "mars_state": "TEXT",
    })
    _migrate_add_columns(conn, "breadth_daily", {
        # Long-term participation input for the Participation panel
        # (pct_above_20dma vs pct_above_50dma). Already computed by
        # sources/universe_breadth.py but was previously dropped on upsert.
        "pct_above_50dma": "REAL",
    })
    _migrate_add_columns(conn, "regime_snapshots", {
        # The breadth_daily row a snapshot's XP/MBI were actually computed
        # from — often < snapshot_date when the source sheet lags a day.
        # Lets the UI label a stale-but-real XP ("XP 14 · as of Jul 3")
        # instead of leaving the headline number null.
        "source_date": "TEXT",
        # The old var=value audit trail, now separate from the plain-English
        # `explanation_text` — kept, not deleted, behind a UI toggle so the
        # "no black box" traceability rule still holds without dumping raw
        # diagnostics into a beginner's primary view by default.
        "technical_detail": "TEXT",
        # SHIP-1 #16 (I1 HAR-RV): next-5d realized-vol forecast, JSON blob
        # {rv_forecast_5d, vol_forecast_pct, current_vol_pct, band, qlike_model,
        # qlike_naive, n_train}. Written by regime/vol_har.py ONLY when its
        # walk-forward QLIKE beats the naive-lag baseline (else left NULL and
        # the stage logs a skip) — display-only, marked experimental, never
        # consumed by the governor.
        "vol_forecast": "TEXT",
    })
    _migrate_add_columns(conn, "journal_trades", {
        "first_exit_flag_date": "TEXT",
        # SHIP-1 #4: positions tab Edit-qty writes qty, but older journal_trades
        # rows predate this column on already-initialized manas.db files.
        "qty": "REAL",
    })
    _migrate_add_columns(conn, "agent_verdicts", {
        # G1: PASSED | NEAR_MISS — which lane a debated shortlist item came from.
        "tier": "TEXT",
    })
    _migrate_add_columns(conn, "agent_watchlist", {
        "miss_streak": "INTEGER DEFAULT 0",
    })
    conn.commit()
    return conn


def _existing_columns(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_add_columns(conn, table: str, cols: dict[str, str]) -> None:
    """ADD COLUMN for any of `cols` not already present on `table`. Idempotent."""
    have = _existing_columns(conn, table)
    for name, ddl in cols.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
