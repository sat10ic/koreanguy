"""SQLite connection + schema init for manas.db."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = _DB_DIR / "manas.db"
_SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with sane defaults (row factory + FK + WAL).

    Guard: refuses to silently fall back to the real DB_PATH when called with
    no explicit db_path from inside a test run. This is how the live
    manas_os/data/manas.db previously got polluted with synthetic
    ~100.0-close placeholder rows (arithmetic-progression pattern, e.g.
    NIFTYMIDSML400/NIFTY FIN SERVICE 2026-01-01..2026-03-02) — some ad-hoc
    invocation of test-style fixture data (matching test_mars_ingest.py's
    `_fake_bars`, normally only ever written into an isolated
    `tmp_path / "manas.db"`) called `db.init_db()`/`db.connect()` with no
    path and landed on the production DB by accident. Tests that
    legitimately want the real DB (e.g. test_sector_downside.py's
    walk-forward check) already pass an explicit path and are unaffected.
    """
    if db_path is None and os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get(
        "MANAS_ALLOW_PROD_DB_IN_TESTS"
    ):
        raise RuntimeError(
            "Refusing to open the production manas.db (DB_PATH) from inside a "
            "test run with no explicit db_path. Pass an isolated path (e.g. "
            "tmp_path / 'manas.db') or, for an intentional real-DB check, pass "
            "DB_PATH explicitly (or set MANAS_ALLOW_PROD_DB_IN_TESTS=1)."
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
    conn.execute("INSERT OR IGNORE INTO trader_profile (id, account_capital, experience_mode) VALUES (1, 0.0, 'LEARNING')")
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
        # M9: real four-phase classifier (regime/four_phase.py) — replaces the
        # display-caption approximation. four_phase_json is
        # {phase, confidence, evidence:{...}}; choppy_brake_json is
        # {active, reason, evidence:{...}} from regime/choppy_brake.py.
        "four_phase_json": "TEXT",
        "choppy_brake_json": "TEXT",
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
        # Chartink screener + push-to-debate amendment (2026-07-11 ~09:30).
        "source": "TEXT",
    })
    _migrate_add_columns(conn, "agent_watchlist", {
        "miss_streak": "INTEGER DEFAULT 0",
    })
    _migrate_add_columns(conn, "discovery_bucket", {
        "classification": "TEXT DEFAULT 'DISCOVERY'",
    })
    _migrate_add_columns(conn, "scan_agent_logs", {
        "model_status": "TEXT",
        "cost_inr": "REAL",
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
