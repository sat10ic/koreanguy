"""Tests for manas_os.sources.classify_universe.

The pure classification logic (classify_symbol, sector_for_industry,
parse_screener_html) is tested without any network or DB. The run() integration
tests use a seeded in-memory DB with daily_prices + screener_hits + universe +
pipeline_runs, and inject a fake Screener fetcher so no real network call runs.
"""
from __future__ import annotations

import sqlite3

from manas_os.sources import classify_universe as cu

# ─────────────────────────────────────────────────────────────────────────────
# DDL (matches schema.sql; the test DB stands these up itself)
# ─────────────────────────────────────────────────────────────────────────────

_DAILY_PRICES_DDL = """\
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol TEXT NOT NULL, trade_date TEXT NOT NULL, series TEXT DEFAULT 'EQ',
    open REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price REAL, avg_price REAL, volume INTEGER, turnover REAL,
    num_trades INTEGER, delivery_qty INTEGER, delivery_pct REAL,
    source TEXT, ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, series)
);
"""
_UNIVERSE_DDL = """\
CREATE TABLE IF NOT EXISTS universe (
    symbol TEXT NOT NULL, as_of_date TEXT NOT NULL, name TEXT, series TEXT DEFAULT 'EQ',
    sector TEXT, industry TEXT, market_cap_cr REAL, avg_turnover_cr REAL,
    is_tradeable INTEGER DEFAULT 1, ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, as_of_date)
);
"""
_SCREENER_HITS_DDL = """\
CREATE TABLE IF NOT EXISTS screener_hits (
    trade_date TEXT NOT NULL, symbol TEXT NOT NULL, screener TEXT NOT NULL,
    bearish INTEGER DEFAULT 0, rs_rating REAL, basic_industry TEXT,
    ingested_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (trade_date, symbol, screener)
);
"""
_PIPELINE_RUNS_DDL = """\
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT NOT NULL, stage TEXT NOT NULL,
    source TEXT, status TEXT, rows_affected INTEGER DEFAULT 0, duration_s REAL,
    detail TEXT, ran_at TEXT DEFAULT (datetime('now'))
);
"""


def _fresh_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for ddl in (_DAILY_PRICES_DDL, _UNIVERSE_DDL, _SCREENER_HITS_DDL, _PIPELINE_RUNS_DDL):
        conn.executescript(ddl)
    return conn


def _seed_price(conn, symbol, trade_date, *, close, volume=1_000_000, high=None, low=None,
                turnover_cr=10.0):
    """Seed a daily_prices row. high/low default to close±small so range > 0."""
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, turnover) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (symbol, trade_date, "EQ", close,
         high if high is not None else close * 1.01,
         low if low is not None else close * 0.99,
         close, close, volume, turnover_cr * 1e7),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pure-helper tests (no DB, no network)
# ─────────────────────────────────────────────────────────────────────────────

def test_sector_for_industry_uses_existing_map():
    # regime.sectors.INDUSTRY_TO_SECTOR maps 112 industries; spot-check a few.
    assert cu.sector_for_industry("Aerospace & Defense") == "CAPITAL_GOODS"
    assert cu.sector_for_industry("Pharmaceuticals") == "PHARMA"
    assert cu.sector_for_industry("Iron & Steel") == "METAL"
    assert cu.sector_for_industry("Software Services") == "IT"
    assert cu.sector_for_industry("PSU Banks") == "PSU_BANK"


def test_sector_for_industry_handles_none_and_unknown():
    assert cu.sector_for_industry(None) is None
    assert cu.sector_for_industry("") is None
    assert cu.sector_for_industry("Totally Made Up Industry") is None


def test_classify_symbol_layer1_chartmaze_wins():
    """ChartMaze basic_industry is authoritative; Screener data ignored."""
    industry, sector = cu.classify_symbol(
        "AARTIIND", "Chemicals Specialty", "Specialty Chemicals", "Chemicals"
    )
    assert industry == "Chemicals Specialty"   # ChartMaze label kept
    assert sector == "CHEMICALS"               # canonical key from the map


def test_classify_symbol_layer2_screener_when_no_chartmaze():
    """No ChartMaze basic_industry → fall to Screener industry, mapped to sector."""
    # Screener industry "Software Services" is in INDUSTRY_TO_SECTOR -> IT
    industry, sector = cu.classify_symbol("XYZ", None, "Software Services", "Technology")
    assert sector == "IT"


def test_classify_symbol_layer2_screener_sector_fallback():
    """Screener industry not in the map, but Screener sector label is known."""
    industry, sector = cu.classify_symbol("XYZ", None, "Obscure Sub-Niche", "Power")
    # "Power" maps to ENERGY via _SCREENER_SECTOR_TO_KEY
    assert sector == "ENERGY"
    assert industry == "Obscure Sub-Niche"


def test_classify_symbol_layer3_unknown():
    """No ChartMaze, no Screener → (None, None)."""
    industry, sector = cu.classify_symbol("ZZZ", None, None, None)
    assert industry is None
    assert sector is None


def test_parse_screener_html_extracts_sector_and_industry():
    html = (
        '<a href="/market/IN11/IN1101/" title="Sector">Utilities</a>'
        '<i class="icon-right"></i>'
        '<a href="/market/IN11/IN1101/IN110101/" title="Industry">Power Generation</a>'
    )
    sec, ind = cu.parse_screener_html(html)
    assert sec == "Utilities"
    assert ind == "Power Generation"


def test_parse_screener_html_unescapes_entities():
    html = '<a title="Sector">Metals &amp; Mining</a><a title="Industry">Iron &amp; Steel</a>'
    sec, ind = cu.parse_screener_html(html)
    assert sec == "Metals & Mining"
    assert ind == "Iron & Steel"


def test_parse_screener_html_returns_none_when_no_match():
    sec, ind = cu.parse_screener_html("<html><body>no breadcrumbs here</body></html>")
    assert sec is None
    assert ind is None


# ─────────────────────────────────────────────────────────────────────────────
# run() integration tests — in-memory DB, injected fake Screener fetcher
# ─────────────────────────────────────────────────────────────────────────────

def _fake_screener(responses):
    """Build a fake screener_fetch callable returning canned (sector, industry)."""
    def _fetch(sess, symbol):
        return responses.get(symbol, (None, None))
    return _fetch


def test_run_case1_chartmaze_symbol_gets_sector():
    """Symbol with basic_industry in screener_hits → industry + sector populated.

    CHEMCO has basic_industry='Chemicals Specialty' (in INDUSTRY_TO_SECTOR ->
    CHEMICALS). Priced at 100 with 10cr turnover -> is_tradeable=1.
    """
    conn = _fresh_db()
    _seed_price(conn, "CHEMCO", "2026-07-10", close=100.0)
    conn.execute(
        "INSERT INTO screener_hits (trade_date, symbol, screener, basic_industry) "
        "VALUES ('2026-07-10', 'CHEMCO', 'vcp', 'Chemicals Specialty')"
    )
    conn.commit()

    # no gap symbols -> screener never called; pass empty fake to be safe
    result = cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    assert result["status"] == "ok"

    row = conn.execute(
        "SELECT sector, industry, is_tradeable FROM universe WHERE symbol='CHEMCO'"
    ).fetchone()
    assert row["sector"] == "CHEMICALS"
    assert row["industry"] == "Chemicals Specialty"
    assert row["is_tradeable"] == 1
    conn.close()


def test_run_case2_screener_gap_fill():
    """Symbol NOT in screener_hits → Screener scrape provides industry.

    NEWCO has no basic_industry. Fake Screener returns ('Technology', 'Software Services').
    'Software Services' is in INDUSTRY_TO_SECTOR -> IT.
    """
    conn = _fresh_db()
    _seed_price(conn, "NEWCO", "2026-07-10", close=100.0)
    conn.commit()

    result = cu.run(conn, "2026-07-10",
                    screener_fetch=_fake_screener({"NEWCO": ("Technology", "Software Services")}))
    assert result["status"] == "ok"

    row = conn.execute(
        "SELECT sector, industry FROM universe WHERE symbol='NEWCO'"
    ).fetchone()
    assert row["sector"] == "IT"
    assert row["industry"] == "Software Services"
    conn.close()


def test_run_case3_unclassified_still_in_universe():
    """Symbol in neither ChartMaze nor Screener → industry/sector NULL but row EXISTS.

    This is the critical constraint: the symbol must still get a universe row
    so alpha/features.py's is_tradeable gate doesn't drop it.
    """
    conn = _fresh_db()
    _seed_price(conn, "UNKNOWN", "2026-07-10", close=100.0)
    conn.commit()

    result = cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    assert result["status"] == "ok"

    row = conn.execute(
        "SELECT sector, industry, is_tradeable FROM universe WHERE symbol='UNKNOWN'"
    ).fetchone()
    assert row is not None              # row EXISTS even though unclassified
    assert row["sector"] is None
    assert row["industry"] is None
    assert row["is_tradeable"] == 1     # priced at 100, liquid -> tradeable
    conn.close()


def test_run_case4_sub_threshold_price_untradeable_but_present():
    """A sub-₹30 stock gets is_tradeable=0 but is STILL in universe.

    The liquidity gate (GateConfig min_price=30) excludes it from tradeable,
    but classify_universe writes the row anyway — is_tradeable=0, not dropped.
    """
    conn = _fresh_db()
    _seed_price(conn, "PENNY", "2026-07-10", close=15.0)  # ₹15 < ₹30 floor
    conn.commit()

    result = cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    assert result["status"] == "ok"

    row = conn.execute(
        "SELECT is_tradeable FROM universe WHERE symbol='PENNY'"
    ).fetchone()
    assert row is not None
    assert row["is_tradeable"] == 0     # excluded by price gate, but row present
    conn.close()


def test_run_case5_idempotent():
    """run() twice → one row per (symbol, as_of_date), values stable."""
    conn = _fresh_db()
    _seed_price(conn, "DUP", "2026-07-10", close=100.0)
    conn.execute(
        "INSERT INTO screener_hits (trade_date, symbol, screener, basic_industry) "
        "VALUES ('2026-07-10', 'DUP', 'vcp', 'Pharmaceuticals')"
    )
    conn.commit()

    cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))

    n = conn.execute(
        "SELECT COUNT(*) FROM universe WHERE symbol='DUP' AND as_of_date='2026-07-10'"
    ).fetchone()[0]
    assert n == 1  # upsert, not duplicate

    row = conn.execute(
        "SELECT sector FROM universe WHERE symbol='DUP'"
    ).fetchone()
    assert row["sector"] == "PHARMA"
    conn.close()


def test_run_skip_when_no_priced_universe():
    """No daily_prices rows for the date → status='skip', no universe rows written."""
    conn = _fresh_db()
    _seed_price(conn, "X", "2026-07-09", close=100.0)  # different date
    conn.commit()

    result = cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    assert result["status"] == "skip"
    n = conn.execute("SELECT COUNT(*) FROM universe").fetchone()[0]
    assert n == 0
    conn.close()


def test_run_circuit_breaker_abort_is_partial_not_ok():
    """RELIABILITY_AUDIT_2026-07-19 defect #7: when the screener.in gap-fill
    circuit breaker trips (8 consecutive failures, 0 successes), sector/
    industry coverage for the skipped symbols is known-incomplete -- the
    stage must report 'partial', not 'ok', so jobs.run_stages() (which
    treats any non-'ok' stage status as 'partial' for the whole run) and
    Pipeline Health both see the degradation instead of a clean success.
    """
    conn = _fresh_db()
    # 10 gap symbols (no basic_industry, so all fall to the screener
    # fetcher) with a fetcher that always fails -> trips the breaker at the
    # 8th consecutive failure with 0 successes, aborting the last fetch.
    symbols = [f"GAP{i}" for i in range(10)]
    for sym in symbols:
        _seed_price(conn, sym, "2026-07-10", close=100.0)
    conn.commit()

    def _always_fail(sess, symbol):
        return (None, None)

    result = cu.run(conn, "2026-07-10", screener_fetch=_always_fail)

    assert result["status"] == "partial"
    assert "screener.in unreachable" in result["detail"]
    assert "skipped" in result["detail"]

    # Every priced symbol still gets a universe row -- the breaker degrades
    # coverage, it does not drop symbols (test_run_case3's constraint holds).
    n = conn.execute("SELECT COUNT(*) FROM universe WHERE as_of_date='2026-07-10'").fetchone()[0]
    assert n == len(symbols)

    pr = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage='classify_universe' "
        "ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    assert pr["status"] == "partial"
    conn.close()


def test_run_logs_ok_to_pipeline_runs():
    """Successful run writes an 'ok' pipeline_runs row with stage=classify_universe."""
    conn = _fresh_db()
    _seed_price(conn, "S", "2026-07-10", close=100.0)
    conn.commit()
    cu.run(conn, "2026-07-10", screener_fetch=_fake_screener({}))
    pr = conn.execute(
        "SELECT status, stage FROM pipeline_runs WHERE stage='classify_universe'"
    ).fetchone()
    assert pr["status"] == "ok"
    assert pr["stage"] == "classify_universe"
    conn.close()


def test_run_full_universe_gets_rows():
    """Multiple symbols, mixed classification — every priced symbol gets a row."""
    conn = _fresh_db()
    _seed_price(conn, "CM", "2026-07-10", close=100.0)     # has chartmaze
    _seed_price(conn, "SC", "2026-07-10", close=100.0)     # screener-only
    _seed_price(conn, "UN", "2026-07-10", close=100.0)     # unknown
    conn.execute(
        "INSERT INTO screener_hits (trade_date, symbol, screener, basic_industry) "
        "VALUES ('2026-07-10', 'CM', 'vcp', 'Cement')"
    )
    conn.commit()

    result = cu.run(conn, "2026-07-10",
                    screener_fetch=_fake_screener({"SC": ("Realty", "Real Estate")}))
    assert result["status"] == "ok"
    assert result["rows_affected"] == 3   # all three priced symbols

    total = conn.execute("SELECT COUNT(*) FROM universe WHERE as_of_date='2026-07-10'").fetchone()[0]
    assert total == 3
    # CM: Cement -> INFRASTRUCTURE; SC: Real Estate -> REALTY; UN: NULL
    cm = conn.execute("SELECT sector FROM universe WHERE symbol='CM'").fetchone()["sector"]
    sc = conn.execute("SELECT sector FROM universe WHERE symbol='SC'").fetchone()["sector"]
    un = conn.execute("SELECT sector FROM universe WHERE symbol='UN'").fetchone()["sector"]
    assert cm == "INFRASTRUCTURE"
    assert sc == "REALTY"
    assert un is None
    conn.close()
