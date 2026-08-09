"""Tests for scanner/scorecard.py -- funnel + forward-performance scorecard.

Fixture: an in-memory DB (same pattern as test_discovery_bucket.py) seeded with
two scan dates --
  2026-01-05 ("mid-range"): one symbol per cohort (scan_picks, watch, refused,
    debated_pick, debated_skip), each with a hand-computable linear price path
    running D5..D20 (15 future EQ sessions -> all four horizons resolvable).
  2026-01-19 ("data edge"): one scan_picks symbol with only ONE future EQ
    session (D20) in the whole DB -- T+1 resolvable, T+3/T+5/T+10 must come
    back honestly empty (n=0, stats None), and get flagged as a truncated
    horizon in data_edge.truncated_dates.

All forward-return numbers below are computed by hand from the seeded slopes,
not copied from the implementation.
"""
from __future__ import annotations

import datetime
import sqlite3

import pytest

from manas_os import db
from manas_os.scanner import scorecard

D5 = "2026-01-05"
D19 = "2026-01-19"
D20 = "2026-01-20"


def _mk_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    # refusals is created lazily by scanner/candidates.py (not in schema.sql);
    # mirror its exact DDL here so scorecard's _table_exists guard sees it.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS refusals ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_family TEXT, "
        "failed_gate TEXT NOT NULL, reason TEXT, evidence_json TEXT, "
        "ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )
    # position_verdicts is created lazily by api/app.py::_ensure_position_verdicts_schema
    # (not in schema.sql); mirror its exact DDL here so scorecard's _table_exists guard sees it.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS position_verdicts ("
        "verdict_date TEXT NOT NULL, symbol TEXT NOT NULL, verdict TEXT, "
        "exit_state TEXT, fired_rules_json TEXT, close_at_verdict REAL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (verdict_date, symbol))"
    )
    return conn


def _insert_price(conn, symbol: str, trade_date: str, close: float) -> None:
    conn.execute(
        "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close) "
        "VALUES (?, 'EQ', ?, ?, ?, ?, ?)",
        (symbol, trade_date, close, close, close, close),
    )


def _seed_linear_series(conn, symbol: str, entry_date: str, entry_close: float, slope: float, days: int) -> None:
    """One row per calendar day from entry_date (offset 0) through
    entry_date + days, close = entry_close + slope * day_offset."""
    d0 = datetime.date.fromisoformat(entry_date)
    for offset in range(0, days + 1):
        d = d0 + datetime.timedelta(days=offset)
        _insert_price(conn, symbol, d.isoformat(), entry_close + slope * offset)


@pytest.fixture()
def seeded_conn():
    conn = _mk_conn()

    # Universe as-of D5: exactly the 5 cohort symbols below.
    for sym in ("SYM_SCAN", "SYM_WATCH", "SYM_REFUSED", "SYM_PICK", "SYM_SKIP"):
        conn.execute(
            "INSERT INTO universe (symbol, as_of_date, name) VALUES (?, ?, ?)",
            (sym, D5, sym),
        )

    # discovery_bucket: SYM_WATCH is WATCH, SYM_DISC is plain DISCOVERY
    # (distinguishes bucket_n=2 from watch_n=1).
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'SYM_WATCH', 'WATCH', '{}', '{}')", (D5,),
    )
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'SYM_DISC', 'DISCOVERY', '{}', '{}')", (D5,),
    )

    # scan_candidates: SYM_SCAN at D5, SYM_SCAN2 at D19 (the data-edge date).
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_SCAN', 'breakout')", (D5,),
    )
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_SCAN2', 'breakout')", (D19,),
    )

    # refusals: SYM_REFUSED at D5.
    conn.execute(
        "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
        "VALUES (?, 'SYM_REFUSED', NULL, 'trend_template', 'below 200sma')", (D5,),
    )

    # agent_verdicts: SYM_PICK chair TAKE, SYM_SKIP chair SKIP (plus a
    # non-chair model row each, to prove pick/skip filters on agent='chair').
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict) VALUES (?, 'SYM_PICK', 'model_a', 'TAKE')", (D5,),
    )
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict) VALUES (?, 'SYM_PICK', 'chair', 'TAKE')", (D5,),
    )
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict) VALUES (?, 'SYM_SKIP', 'model_a', 'SKIP')", (D5,),
    )
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict) VALUES (?, 'SYM_SKIP', 'chair', 'SKIP')", (D5,),
    )

    # Price paths, D5 (offset 0) .. D20 (offset 15) -- entry always 100.0.
    _seed_linear_series(conn, "SYM_SCAN", D5, 100.0, +1.0, 15)     # T+1=+1% T+3=+3% T+5=+5% T+10=+10%
    _seed_linear_series(conn, "SYM_WATCH", D5, 100.0, -1.0, 15)    # T+1=-1% T+3=-3% T+5=-5% T+10=-10%
    _seed_linear_series(conn, "SYM_REFUSED", D5, 100.0, 0.0, 15)   # flat 0% throughout
    _seed_linear_series(conn, "SYM_PICK", D5, 100.0, +2.0, 15)     # T+1=+2% T+3=+6% T+5=+10% T+10=+20%
    _seed_linear_series(conn, "SYM_SKIP", D5, 100.0, -0.5, 15)     # T+1=-0.5% T+3=-1.5% T+5=-2.5% T+10=-5%

    # Data-edge symbol: entry at D19=50, exactly one future session D20=51 (+2%).
    _insert_price(conn, "SYM_SCAN2", D19, 50.0)
    _insert_price(conn, "SYM_SCAN2", D20, 51.0)

    # position_verdicts @ D5, reusing the price paths already seeded above so
    # forward returns are hand-computable from the same slopes:
    #   SYM_WATCH -1.0/day -> T+1=-1% T+3=-3% T+5=-5%   (verdict=EXIT)
    #   SYM_SCAN  +1.0/day -> T+1=+1% T+3=+3% T+5=+5%   (verdict=HOLD)
    #   SYM_PICK  +2.0/day -> T+1=+2% T+3=+6% T+5=+10%  (verdict=TRIM)
    #   SYM_REFUSED flat   -> verdict=MOVE_STOP (must NOT appear in the
    #                         EXIT/HOLD/TRIM cohort -- it's an imported-
    #                         holding-only verdict value, out of scope).
    conn.execute(
        "INSERT INTO position_verdicts (verdict_date, symbol, verdict, exit_state, fired_rules_json, close_at_verdict) "
        "VALUES (?, 'SYM_WATCH', 'EXIT', 'Broken', '[]', 100.0)", (D5,),
    )
    conn.execute(
        "INSERT INTO position_verdicts (verdict_date, symbol, verdict, exit_state, fired_rules_json, close_at_verdict) "
        "VALUES (?, 'SYM_SCAN', 'HOLD', 'Intact', '[]', 100.0)", (D5,),
    )
    conn.execute(
        "INSERT INTO position_verdicts (verdict_date, symbol, verdict, exit_state, fired_rules_json, close_at_verdict) "
        "VALUES (?, 'SYM_PICK', 'TRIM', 'Weakening', '[]', 100.0)", (D5,),
    )
    conn.execute(
        "INSERT INTO position_verdicts (verdict_date, symbol, verdict, exit_state, fired_rules_json, close_at_verdict) "
        "VALUES (?, 'SYM_REFUSED', 'MOVE_STOP', 'Intact', '[]', 100.0)", (D5,),
    )

    conn.commit()
    return conn


def test_funnel_counts_per_scan_date(seeded_conn):
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")
    by_date = {row["scan_date"]: row for row in result["dates"]}

    assert set(by_date) == {D5, D19}, "only dates with recorded activity should appear"

    d5 = by_date[D5]
    assert d5["universe_n"] == 5
    assert d5["bucket_n"] == 2       # SYM_WATCH + SYM_DISC
    assert d5["watch_n"] == 1        # SYM_WATCH only
    assert d5["scan_n"] == 1         # SYM_SCAN
    assert d5["refused_n"] == 1      # SYM_REFUSED
    assert d5["debated_n"] == 2      # SYM_PICK, SYM_SKIP
    assert d5["pick_n"] == 1         # chair TAKE
    assert d5["skip_n"] == 1         # chair SKIP

    d19 = by_date[D19]
    assert d19["universe_n"] == 0    # no universe row seeded for D19 -- honest zero
    assert d19["scan_n"] == 1        # SYM_SCAN2
    assert d19["refused_n"] == 0
    assert d19["debated_n"] == 0


def test_cohort_cumulative_matches_hand_math(seeded_conn):
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")
    cum = result["cohorts"]["cumulative"]

    # scan_picks pools SYM_SCAN (D5, full horizon) + SYM_SCAN2 (D19, T+1 only).
    sp = cum["scan_picks"]
    assert sp[1]["n"] == 2
    assert sp[1]["median_pct"] == pytest.approx((1.0 + 2.0) / 2)
    assert sp[1]["hit_rate"] == pytest.approx(1.0)
    assert sp[3]["n"] == 1 and sp[3]["median_pct"] == pytest.approx(3.0)
    assert sp[5]["n"] == 1 and sp[5]["median_pct"] == pytest.approx(5.0)
    assert sp[5]["big_win_rate"] == pytest.approx(1.0)   # 5% >= 5% threshold
    assert sp[10]["n"] == 1 and sp[10]["median_pct"] == pytest.approx(10.0)

    watch = cum["watch"]
    assert watch[1]["n"] == 1 and watch[1]["median_pct"] == pytest.approx(-1.0)
    assert watch[1]["hit_rate"] == pytest.approx(0.0)
    assert watch[5]["median_pct"] == pytest.approx(-5.0)
    assert watch[5]["big_loss_rate"] == pytest.approx(1.0)  # -5% <= -5% threshold
    assert watch[10]["median_pct"] == pytest.approx(-10.0)

    refused = cum["refused"]
    for h in (1, 3, 5, 10):
        assert refused[h]["n"] == 1
        assert refused[h]["median_pct"] == pytest.approx(0.0)
        assert refused[h]["hit_rate"] == pytest.approx(0.0)  # 0% is not > 0

    pick = cum["debated_pick"]
    assert pick[1]["median_pct"] == pytest.approx(2.0)
    assert pick[3]["median_pct"] == pytest.approx(6.0)
    assert pick[3]["big_win_rate"] == pytest.approx(1.0)
    assert pick[10]["median_pct"] == pytest.approx(20.0)

    skip = cum["debated_skip"]
    assert skip[1]["median_pct"] == pytest.approx(-0.5)
    assert skip[10]["median_pct"] == pytest.approx(-5.0)
    assert skip[10]["big_loss_rate"] == pytest.approx(1.0)


def test_truncated_horizon_honesty_at_data_edge(seeded_conn):
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")

    per_date = result["cohorts"]["per_date"]["scan_picks"]
    d19_stats = per_date[D19]
    assert d19_stats[1]["n"] == 1
    assert d19_stats[1]["median_pct"] == pytest.approx(2.0)
    for h in (3, 5, 10):
        assert d19_stats[h]["n"] == 0
        assert d19_stats[h]["median_pct"] is None
        assert d19_stats[h]["hit_rate"] is None

    edge = result["data_edge"]
    truncated_by_date = {n["scan_date"]: n for n in edge["truncated_dates"]}
    assert D19 in truncated_by_date
    assert truncated_by_date[D19]["sessions_after"] == 1
    assert set(truncated_by_date[D19]["truncated_horizons"]) == {3, 5, 10}
    assert D5 not in truncated_by_date, "D5 has 15 future sessions -- no horizon should be truncated"
    assert edge["refusals_table_present"] is True


def test_render_md_contains_funnel_cohorts_and_caveats(seeded_conn):
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")
    md = scorecard.render_md(result)

    assert md.startswith("# Scorecard: 2026-01-01 .. 2026-01-31")
    assert D5 in md and D19 in md
    assert "Scan picks (gate-passed)" in md
    assert "Anticipation WATCH" in md
    assert "Refused (hard gate)" in md
    assert "Debated -- chair TAKE" in md
    assert "Debated -- chair SKIP" in md
    assert "## Data caveats" in md
    # every cohort/horizon sample here is n=1 or n=2, well under MIN_RELIABLE_N=10
    assert "n<10" in md
    # the D19 truncation must be visible in the caveats prose, not silently dropped
    assert D19 in md.split("## Data caveats")[1]


def test_missing_refusals_table_is_handled_honestly():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    # deliberately do NOT create the refusals table
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'X', 'breakout')", (D5,),
    )
    _insert_price(conn, "X", D5, 10.0)
    _insert_price(conn, "X", "2026-01-06", 10.1)
    conn.commit()

    result = scorecard.build(conn, "2026-01-01", "2026-01-31")
    assert result["data_edge"]["refusals_table_present"] is False
    by_date = {row["scan_date"]: row for row in result["dates"]}
    assert by_date[D5]["refused_n"] == 0
    assert result["cohorts"]["cumulative"]["refused"][1]["n"] == 0

    md = scorecard.render_md(result)
    assert "refusals` table did not exist" in md


def test_verdict_cohort_matches_hand_math(seeded_conn):
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")
    verdicts = result["verdicts"]
    assert verdicts["available"] is True
    assert verdicts["horizons"] == [1, 3, 5]
    cum = verdicts["cumulative"]

    exit_ = cum["EXIT"]
    assert exit_[1]["n"] == 1 and exit_[1]["median_pct"] == pytest.approx(-1.0)
    assert exit_[3]["median_pct"] == pytest.approx(-3.0)
    assert exit_[5]["median_pct"] == pytest.approx(-5.0)
    assert exit_[5]["hit_rate"] == pytest.approx(0.0)

    hold = cum["HOLD"]
    assert hold[1]["median_pct"] == pytest.approx(1.0)
    assert hold[3]["median_pct"] == pytest.approx(3.0)
    assert hold[5]["median_pct"] == pytest.approx(5.0)

    trim = cum["TRIM"]
    assert trim[1]["median_pct"] == pytest.approx(2.0)
    assert trim[3]["median_pct"] == pytest.approx(6.0)
    assert trim[5]["median_pct"] == pytest.approx(10.0)

    # MOVE_STOP is not one of the three graded verdicts -- must not leak in.
    assert set(verdicts["order"]) == {"EXIT", "HOLD", "TRIM"}

    per_date = verdicts["per_date"]
    assert per_date["EXIT"][D5][1]["median_pct"] == pytest.approx(-1.0)

    md = scorecard.render_md(result)
    assert "## Exit-verdict grading (coach verdicts vs. actual forward return)" in md
    assert "Coach verdict -- EXIT" in md
    assert "Coach verdict -- HOLD" in md
    assert "Coach verdict -- TRIM" in md


def test_missing_position_verdicts_table_is_handled_honestly():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    # deliberately do NOT create the position_verdicts table
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'X', 'breakout')", (D5,),
    )
    _insert_price(conn, "X", D5, 10.0)
    conn.commit()

    result = scorecard.build(conn, "2026-01-01", "2026-01-31")
    assert result["verdicts"]["available"] is False
    assert "position_verdicts table does not exist" in result["verdicts"]["reason"]

    md = scorecard.render_md(result)
    assert "## Exit-verdict grading (coach verdicts vs. actual forward return)" in md
    assert "position_verdicts table does not exist" in md


def test_build_returns_json_serializable(seeded_conn):
    import json
    result = scorecard.build(seeded_conn, "2026-01-01", "2026-01-31")
    json.dumps(result)  # must not raise
