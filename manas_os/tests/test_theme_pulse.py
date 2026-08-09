"""Tests for scanner/theme_pulse.py -- correlated-group ("theme") surfacing.

Fixture: an in-memory DB seeded for one scan_date (2026-02-10) with three
industry groups, each hand-computable against the module's fire rule
(>=3 lane-members fires regardless of return; >=2 fires only if aggregate
5d return > 4%):

  "Water Supply & Management" (-> UTILITIES): 3 members across all three
    lanes (scan/watch/discovery), flat 0% 5d return each -- proves the
    strong (n>=3) rule fires with NO help from the return threshold.
  "Chemicals-Basic" (-> CHEMICALS): 2 members (scan/watch), average 5d
    return +2% (<=4%) -- must NOT fire (below both thresholds).
  "Iron & Steel" (-> METAL): 2 members (scan/discovery), average 5d return
    +6% (>4%) -- must fire via the weak-count-strong-return rule.

A fourth symbol (SYM_LONE) sits alone in "Textiles" (n=1, must never fire)
and a fifth (SYM_NOMAP) has no stock_industry_rs row at all (must be
excluded from grouping entirely, never guessed).
"""
from __future__ import annotations

import datetime
import json
import sqlite3

import pytest

from manas_os import db
from manas_os.scanner import theme_pulse

D0 = "2026-02-10"  # scan_date


def _mk_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    return conn


def _insert_price_series(conn, symbol: str, end_date: str, closes_newest_first: list[float]) -> None:
    """closes_newest_first[0] is the close on end_date, [1] is one session
    earlier, etc -- one row per element, walking backward one calendar day
    at a time (fine for a unit test; ROW_NUMBER only needs distinct dates)."""
    d0 = datetime.date.fromisoformat(end_date)
    for offset, close in enumerate(closes_newest_first):
        d = d0 - datetime.timedelta(days=offset)
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close) "
            "VALUES (?, 'EQ', ?, ?, ?, ?, ?)",
            (symbol, d.isoformat(), close, close, close, close),
        )


def _flat_series(base: float, n: int = 6) -> list[float]:
    return [base] * n


def _pct_series(base: float, pct_5d: float, n: int = 6) -> list[float]:
    """[latest, ..., base_5_sessions_ago] where latest = base*(1+pct/100)
    and everything in between is linearly interpolated (irrelevant to the
    module, which only reads rn=1 and rn=6)."""
    latest = base * (1 + pct_5d / 100.0)
    out = [latest]
    for i in range(1, n):
        out.append(latest - (latest - base) * i / (n - 1))
    return out


@pytest.fixture()
def seeded_conn():
    conn = _mk_conn()

    # -- lanes --
    conn.execute("INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'WABAG', 'breakout')", (D0,))
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'EIEL', 'WATCH', '{}', '{}')", (D0,),
    )
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'DENTA', 'DISCOVERY', '{}', '{}')", (D0,),
    )

    conn.execute("INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_C1', 'breakout')", (D0,))
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'SYM_C2', 'WATCH', '{}', '{}')", (D0,),
    )

    conn.execute("INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_M1', 'breakout')", (D0,))
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, classification, archetypes_json, metrics_json) "
        "VALUES (?, 'SYM_M2', 'DISCOVERY', '{}', '{}')", (D0,),
    )

    conn.execute("INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_LONE', 'breakout')", (D0,))
    conn.execute("INSERT INTO scan_candidates (scan_date, symbol, setup) VALUES (?, 'SYM_NOMAP', 'breakout')", (D0,))

    # -- industry membership (stock_industry_rs, snapshot at D0) --
    industry_rows = [
        ("WABAG", "Water Supply & Management"),
        ("EIEL", "Water Supply & Management"),
        ("DENTA", "Water Supply & Management"),
        ("SYM_C1", "Chemicals-Basic"),
        ("SYM_C2", "Chemicals-Basic"),
        ("SYM_M1", "Iron & Steel"),
        ("SYM_M2", "Iron & Steel"),
        ("SYM_LONE", "Textiles"),
        # SYM_NOMAP deliberately has no row.
    ]
    for ticker, industry in industry_rows:
        conn.execute(
            "INSERT INTO stock_industry_rs (snapshot_date, ticker, industry, rs) VALUES (?, ?, ?, ?)",
            (D0, ticker, industry, 80.0),
        )

    # -- 5d returns --
    for sym in ("WABAG", "EIEL", "DENTA"):
        _insert_price_series(conn, sym, D0, _flat_series(100.0))            # 0% each
    _insert_price_series(conn, "SYM_C1", D0, _pct_series(100.0, 2.0))       # +2%
    _insert_price_series(conn, "SYM_C2", D0, _pct_series(100.0, 2.0))       # +2% -> avg +2%
    _insert_price_series(conn, "SYM_M1", D0, _pct_series(100.0, 6.0))       # +6%
    _insert_price_series(conn, "SYM_M2", D0, _pct_series(100.0, 6.0))       # +6% -> avg +6%
    _insert_price_series(conn, "SYM_LONE", D0, _flat_series(50.0))
    _insert_price_series(conn, "SYM_NOMAP", D0, _flat_series(50.0))

    conn.commit()
    return conn


def test_three_member_industry_fires_regardless_of_return(seeded_conn):
    result = theme_pulse.compute_theme_pulse(seeded_conn, D0)
    assert result["available"] is True
    by_industry = {t["industry"]: t for t in result["themes"]}

    water = by_industry["Water Supply & Management"]
    assert water["member_count"] == 3
    assert set(water["member_symbols"]) == {"WABAG", "EIEL", "DENTA"}
    assert water["avg_5d_pct"] == pytest.approx(0.0)
    assert water["sector_key"] == "UTILITIES"
    assert water["lanes"]["scan"] == ["WABAG"]
    assert water["lanes"]["watch"] == ["EIEL"]
    assert water["lanes"]["discovery"] == ["DENTA"]


def test_two_member_weak_return_does_not_fire(seeded_conn):
    result = theme_pulse.compute_theme_pulse(seeded_conn, D0)
    industries = {t["industry"] for t in result["themes"]}
    assert "Chemicals-Basic" not in industries, "n=2 with avg 5d return +2% (<=4%) must not fire"


def test_two_member_strong_return_fires(seeded_conn):
    result = theme_pulse.compute_theme_pulse(seeded_conn, D0)
    by_industry = {t["industry"]: t for t in result["themes"]}
    metal = by_industry["Iron & Steel"]
    assert metal["member_count"] == 2
    assert metal["avg_5d_pct"] == pytest.approx(6.0)
    assert metal["sector_key"] == "METAL"
    assert set(metal["member_symbols"]) == {"SYM_M1", "SYM_M2"}


def test_lone_member_and_unmapped_symbol_excluded(seeded_conn):
    result = theme_pulse.compute_theme_pulse(seeded_conn, D0)
    industries = {t["industry"] for t in result["themes"]}
    assert "Textiles" not in industries, "n=1 can never fire (below MIN_MEMBERS_WEAK)"
    for t in result["themes"]:
        assert "SYM_NOMAP" not in t["member_symbols"], "symbol with no stock_industry_rs row must never be grouped"


def test_persist_and_read_roundtrip(seeded_conn):
    result = theme_pulse.compute_theme_pulse(seeded_conn, D0)
    rows = theme_pulse.persist_theme_pulse(seeded_conn, D0, result)
    seeded_conn.commit()
    assert rows == 2  # Water Supply & Management + Iron & Steel

    persisted = theme_pulse.read_persisted(seeded_conn, D0)
    assert persisted is not None
    by_industry = {t["industry"]: t for t in persisted}
    assert set(by_industry) == {"Water Supply & Management", "Iron & Steel"}
    assert by_industry["Iron & Steel"]["avg_5d_pct"] == pytest.approx(6.0)
    assert by_industry["Iron & Steel"]["sector_label"] == "Metal"

    raw = seeded_conn.execute(
        "SELECT member_symbols_json, lanes_json FROM theme_pulse WHERE scan_date = ? AND industry = ?",
        (D0, "Water Supply & Management"),
    ).fetchone()
    assert set(json.loads(raw["member_symbols_json"])) == {"WABAG", "EIEL", "DENTA"}
    assert json.loads(raw["lanes_json"])["scan"] == ["WABAG"]


def test_read_persisted_is_none_when_nothing_persisted_for_date(seeded_conn):
    assert theme_pulse.read_persisted(seeded_conn, D0) is None
    assert theme_pulse.read_persisted(seeded_conn, "2020-01-01") is None


def test_no_lane_activity_is_honestly_unavailable():
    conn = _mk_conn()
    conn.commit()
    result = theme_pulse.compute_theme_pulse(conn, "2026-03-01")
    assert result["available"] is False
    assert result["themes"] == []
    assert "no scan_candidates" in result["reason"]


def test_run_pipeline_stage_persists_and_logs(seeded_conn):
    out = theme_pulse.run(seeded_conn, D0)
    assert out["status"] == "ok"
    assert out["rows"] == 2

    persisted = theme_pulse.read_persisted(seeded_conn, D0)
    assert persisted is not None and len(persisted) == 2

    log_row = seeded_conn.execute(
        "SELECT stage, status, rows_affected FROM pipeline_runs WHERE run_date = ? AND stage = ?",
        (D0, theme_pulse.STAGE),
    ).fetchone()
    assert log_row is not None
    assert log_row["status"] == "ok"
    assert log_row["rows_affected"] == 2
