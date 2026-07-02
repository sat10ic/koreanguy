"""SQLite layer for FilingsEdge disclosures data.

Separate database (data/disclosures.db) — NOT crammed into portfolio_state.db.
Rationale: different data domain, different invariants. The bhavcopy `prices`
table is the immutable point-in-time disclosure spine; ohlcv.db is the Fyers
convenience feed that gets overwritten nightly. Keeping them separate preserves
point-in-time integrity (the whole point of the disclosures layer).

Schema follows FilingsEdge_Handoff_Spec.md §5. All dates ISO YYYY-MM-DD;
tickers NSE symbols uppercased; every table carries ingested_at (omitted in
CREATE for brevity, added via migrations where needed).
"""
from __future__ import annotations

import os
import sqlite3

# Reuse the same data dir convention as scripts/_db.py
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(_ROOT, 'data')
DISCLOSURES_DB = os.path.join(DB_DIR, 'disclosures.db')


def disclosures_conn() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DISCLOSURES_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# SQL DDL — kept as a list so init_schema is idempotent and reviewable.
SCHEMA_STATEMENTS = [
    # S1: one row per symbol per day — the bhavcopy point-in-time spine.
    # Distinct from ohlcv.db: includes delivery_pct and is immutable.
    """
    CREATE TABLE IF NOT EXISTS prices (
      trade_date   TEXT NOT NULL,
      symbol       TEXT NOT NULL,
      series       TEXT,
      open REAL, high REAL, low REAL, close REAL, prev_close REAL,
      volume INTEGER, turnover REAL,
      delivery_qty INTEGER, delivery_pct REAL,
      PRIMARY KEY (trade_date, symbol, series)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_prices_symbol ON prices(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(trade_date)",

    # S2 raw: every announcement, before LLM. ann_id is exchange id or hash.
    """
    CREATE TABLE IF NOT EXISTS announcements_raw (
      ann_id    TEXT PRIMARY KEY,
      trade_date TEXT,
      symbol    TEXT,
      exchange  TEXT,
      headline  TEXT,
      pdf_path  TEXT,
      extracted_text TEXT,
      processed INTEGER DEFAULT 0,
      ingested_at TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ann_symbol ON announcements_raw(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_ann_processed ON announcements_raw(processed)",
    "CREATE INDEX IF NOT EXISTS idx_ann_date ON announcements_raw(trade_date)",

    # S2 structured: LLM output (M2). CHECK constraint enforces the taxonomy.
    """
    CREATE TABLE IF NOT EXISTS events (
      event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
      ann_id      TEXT REFERENCES announcements_raw(ann_id),
      symbol      TEXT,
      event_date  TEXT,
      event_type  TEXT CHECK(event_type IN
        ('ORDER_WIN','CAPEX','APPROVAL','FUNDRAISE','PLEDGE_CHANGE',
         'RATING_ACTION','MGMT_CHANGE','ROUTINE','NEGATIVE','OTHER')),
      order_value_cr   REAL,
      counterparty     TEXT,
      summary_one_line TEXT,
      confidence       REAL,
      needs_review     INTEGER DEFAULT 0,
      prompt_version   TEXT,
      model_used       TEXT,
      extracted_at     TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)",
    "CREATE INDEX IF NOT EXISTS idx_events_review ON events(needs_review)",

    """
    CREATE TABLE IF NOT EXISTS bulk_block_deals (
      deal_date  TEXT NOT NULL,
      symbol     TEXT NOT NULL,
      deal_type  TEXT,
      client_name TEXT,
      buy_sell   TEXT,
      qty        INTEGER,
      avg_price  REAL,
      PRIMARY KEY (deal_date, symbol, client_name, buy_sell, qty)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_deals_client ON bulk_block_deals(client_name)",
    "CREATE INDEX IF NOT EXISTS idx_deals_date ON bulk_block_deals(deal_date)",

    """
    CREATE TABLE IF NOT EXISTS surveillance (
      list_date  TEXT NOT NULL,
      symbol     TEXT NOT NULL,
      framework  TEXT,
      stage      TEXT,
      PRIMARY KEY (list_date, symbol, framework)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_surv_symbol ON surveillance(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_surv_date ON surveillance(list_date)",

    """
    CREATE TABLE IF NOT EXISTS fundamentals (
      symbol           TEXT NOT NULL,
      as_of_quarter    TEXT NOT NULL,
      ttm_revenue_cr   REAL,
      market_cap_cr    REAL,
      gross_block_cr   REAL,
      promoter_pledge_pct REAL,
      PRIMARY KEY (symbol, as_of_quarter)
    )
    """,

    # M3 output: long-format features, versioned. Makes every backtest
    # reproducible and lets features be added without migrations.
    """
    CREATE TABLE IF NOT EXISTS features (
      trade_date     TEXT NOT NULL,
      symbol         TEXT NOT NULL,
      feature_name   TEXT NOT NULL,
      feature_version TEXT NOT NULL,
      value          REAL,
      PRIMARY KEY (trade_date, symbol, feature_name, feature_version)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_feat_name ON features(feature_name)",
    "CREATE INDEX IF NOT EXISTS idx_feat_date ON features(trade_date)",

    # M4+M5 output: the nightly digest, and the proprietary dataset (the moat).
    # Joined with outcomes, this is the crown jewel — back it up nightly.
    """
    CREATE TABLE IF NOT EXISTS candidates (
      cand_id        INTEGER PRIMARY KEY AUTOINCREMENT,
      trade_date     TEXT NOT NULL,
      symbol         TEXT NOT NULL,
      event_id       INTEGER REFERENCES events(event_id),
      materiality    REAL,
      technical_state TEXT,
      veto_passed    INTEGER,
      veto_detail    TEXT,
      risk_memo      TEXT,
      decision       TEXT DEFAULT 'PENDING',
      decision_note  TEXT,
      created_at     TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cand_date ON candidates(trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_cand_symbol ON candidates(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_cand_decision ON candidates(decision)",

    # M8 output.
    """
    CREATE TABLE IF NOT EXISTS outcomes (
      cand_id          INTEGER REFERENCES candidates(cand_id) PRIMARY KEY,
      ret_5d           REAL,
      ret_10d          REAL,
      ret_20d          REAL,
      max_drawdown_20d REAL,
      hit_circuit      INTEGER,
      computed_at      TEXT DEFAULT (datetime('now'))
    )
    """,

    # Pipeline run log — per-source per-day status, LLM cost, durations.
    # The health message (M6) and dashboard health page read from this.
    """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
      run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
      run_date    TEXT NOT NULL,
      stage       TEXT NOT NULL,
      source      TEXT,
      rows_affected INTEGER,
      duration_s  REAL,
      status      TEXT,
      detail      TEXT,
      llm_cost_usd REAL,
      ran_at      TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_runs_date ON pipeline_runs(run_date)",
    "CREATE INDEX IF NOT EXISTS idx_runs_stage ON pipeline_runs(stage)",
]


def init_schema():
    """Create all tables if not exist. Idempotent — safe to call on every run."""
    with disclosures_conn() as conn:
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)
        conn.commit()


def log_run(run_date: str, stage: str, *, source: str | None = None,
            rows_affected: int | None = None, duration_s: float | None = None,
            status: str = 'ok', detail: str | None = None,
            llm_cost_usd: float | None = None):
    """Append a status row to pipeline_runs. Used by every M-stage."""
    with disclosures_conn() as conn:
        conn.execute(
            """INSERT INTO pipeline_runs
               (run_date, stage, source, rows_affected, duration_s, status,
                detail, llm_cost_usd)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_date, stage, source, rows_affected, duration_s, status,
             detail, llm_cost_usd),
        )
        conn.commit()


if __name__ == '__main__':
    init_schema()
    # Report
    with disclosures_conn() as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
    print(f"disclosures.db initialized at {DISCLOSURES_DB}")
    print(f"Tables ({len(tables)}): {', '.join(tables)}")
