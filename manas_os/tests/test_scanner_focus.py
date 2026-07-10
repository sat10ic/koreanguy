"""FOCUS aggregation layer (manas_os/scanner/focus.py) — n-floor honesty +
theme/watch ranking, over hand-seeded discovery_bucket/screener_hits/
industry_metrics rows (unit-level; no price ramps needed since focus.py
reads only already-persisted tables)."""
import json

from manas_os import db
from manas_os.scanner import focus
from manas_os.tests.conftest import AS_OF


def _seed_bucket(conn, scan_date, entries):
    """entries: [(symbol, archetypes list, metrics dict), ...]"""
    focus.ensure_schema(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS discovery_bucket ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "archetypes_json TEXT NOT NULL, metrics_json TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )
    for sym, archetypes, metrics in entries:
        conn.execute(
            "INSERT OR REPLACE INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
            "VALUES (?, ?, ?, ?)",
            (scan_date, sym, json.dumps(archetypes), json.dumps(metrics)),
        )
    conn.commit()


def _seed_screener_hits(conn, trade_date, rows):
    """rows: [(symbol, screener, basic_industry, rs_rating), ...]"""
    for sym, screener, industry, rs in rows:
        conn.execute(
            "INSERT OR REPLACE INTO screener_hits (trade_date, symbol, screener, basic_industry, rs_rating) "
            "VALUES (?, ?, ?, ?, ?)",
            (trade_date, sym, screener, industry, rs),
        )
    conn.commit()


def _seed_industry_metrics(conn, snapshot_date, rows):
    """rows: [(name, perf_1m, perf_1w, num_stocks), ...]"""
    for name, perf_1m, perf_1w, n in rows:
        conn.execute(
            "INSERT OR REPLACE INTO industry_metrics (snapshot_date, name, perf_1m, perf_1w, num_stocks) "
            "VALUES (?, ?, ?, ?, ?)",
            (snapshot_date, name, perf_1m, perf_1w, n),
        )
    conn.commit()


def _metrics(pct_up=50.0, adr=4.0, purple=2, momentum=30.0):
    return {
        "adr20": adr,
        "purple_dot_count_60d": purple,
        "pct_up_from_65d_low": pct_up,
        "momentum_63d": momentum,
    }


def test_compute_focus_honest_n_floor_excludes_thin_industries(tmp_path):
    """An industry with only 2 qualifying discovery_bucket members must NOT
    become a FOCUS theme (MIN_QUALIFYING_MEMBERS=3) even if both members are
    strong -- a pair is a stock call, not a theme call."""
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        _seed_bucket(conn, AS_OF, [
            ("STOCKA", ["persistent_momentum"], _metrics(pct_up=80)),
            ("STOCKB", ["persistent_momentum"], _metrics(pct_up=75)),
            ("STOCKC", ["persistent_momentum"], _metrics(pct_up=60)),
            ("STOCKD", ["persistent_momentum"], _metrics(pct_up=55)),
            ("STOCKE", ["persistent_momentum"], _metrics(pct_up=50)),
        ])
        _seed_screener_hits(conn, AS_OF, [
            ("STOCKA", "vcp", "Chemicals Specialty", 90),
            ("STOCKB", "vcp", "Chemicals Specialty", 85),
            ("STOCKC", "vcp", "Chemicals Specialty", 80),
            ("STOCKD", "vcp", "Thin Industry", 95),
            ("STOCKE", "vcp", "Thin Industry", 92),
        ])
        _seed_industry_metrics(conn, AS_OF, [
            ("Chemicals Specialty", 5.0, 1.0, 110),
            ("Thin Industry", 20.0, 4.0, 2),
        ])

        result = focus.compute_focus(conn, AS_OF)
        assert result["available"] is True
        industries = {t["industry"] for t in result["themes"]}
        assert "Chemicals Specialty" in industries
        assert "Thin Industry" not in industries  # only 2 qualifying members -- below n-floor

        chem = next(t for t in result["themes"] if t["industry"] == "Chemicals Specialty")
        assert chem["member_count"] == 3
        assert chem["rank"] == 1
        assert [s["symbol"] for s in chem["top_stocks"]] == ["STOCKA", "STOCKB", "STOCKC"]
    finally:
        conn.close()


def test_compute_focus_honest_empty_when_no_bucket(tmp_path):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        result = focus.compute_focus(conn, AS_OF)
        assert result == {
            "available": False, "as_of": None, "themes": [],
            "reason": "no discovery_bucket rows on/before scan_date",
        }
    finally:
        conn.close()


def test_ipo_watch_filters_to_recent_listings_only(tmp_path):
    """A symbol whose price history goes back further than IPO_MAX_DAYS
    sessions must not appear in ipo_watch even if it hit an IPO screener."""
    from manas_os.tests.conftest import insert_price_ramp

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        # BASECO anchors the archive start so OLDCO's own (later, but still
        # >IPO_MAX_DAYS-long) history isn't mistaken for "archive start" by
        # listing_status's own honesty check.
        insert_price_ramp(conn, symbol="BASECO", n=400, start=100.0, step=0.2, end=AS_OF)
        # NEWCO: short history -> recent listing.
        insert_price_ramp(conn, symbol="NEWCO", n=40, start=100.0, step=1.0, end=AS_OF)
        # OLDCO: long history -> not a recent listing, even if flagged.
        insert_price_ramp(conn, symbol="OLDCO", n=260, start=100.0, step=0.5, end=AS_OF)
        _seed_bucket(conn, AS_OF, [
            ("NEWCO", ["ep_ipo"], _metrics(pct_up=70, adr=5.0, purple=3)),
            ("OLDCO", ["ep_ipo"], _metrics(pct_up=60, adr=4.0, purple=2)),
        ])
        _seed_screener_hits(conn, AS_OF, [
            ("NEWCO", "ipo-setups", "EMS", 88),
            ("OLDCO", "ipo-setups", "EMS", 70),
        ])
        rows = focus.ipo_watch(conn, AS_OF)
        symbols = [r["symbol"] for r in rows]
        assert "NEWCO" in symbols
        assert "OLDCO" not in symbols
    finally:
        conn.close()
