"""Corporate-action tests: detection conservatism, adjustment compounding,
volume inverse-adjustment, announcement parsing (record date, no ratio)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.corp_actions import (
    ConfirmedAction, adjust_ohlcv, detect_split_candidates,
    detect_split_candidates_bars, adjust_series,
    adjust_volume, load_confirmed_actions, persist_confirmed_actions,
)
from unidesk.momentum.data.market_store import VersionedDailyBar

UTC = timezone.utc


def test_split_candidate_detected_on_half_split():
    # 10:1... simplified 2:1 split: price ~200 -> ~100 gap with real volume
    closes = [200.0, 200.0, 100.0, 101.0]
    opens = [200.0, 200.0, 100.5, 101.0]
    vols = [1000.0, 1000.0, 5000.0, 4000.0]
    found = detect_split_candidates(closes, opens, vols, min_gap_pct=20)
    assert len(found) == 1
    c = found[0]
    assert c.implied_factor == pytest.approx(100.5 / 200.0, rel=1e-3)
    assert c.nearest_clean == pytest.approx(0.5)


def _bar(symbol, session, close, open_, vol):
    b = DailyBar(
        symbol=symbol, session=session,
        open=open_, high=max(open_, close) + 0.5, low=min(open_, close) - 0.5,
        close=close, volume=int(vol), data_version="test",
    )
    return VersionedDailyBar(bar=b, available_at=datetime(
        session.year, session.month, session.day, 18, 0, tzinfo=UTC
    ) + timedelta(days=1))


def test_split_candidate_bars_dates_the_correct_gap_day_on_flat_pre_gap_closes():
    """Regression for the closes.index(cand.prev_close) relocation bug:
    with FLAT/repeating pre-gap closes, list.index() returns the FIRST
    matching bar, not the true gap bar, so the old code mis-dated the
    candidate. Sessions 0-2 all close at 200.0 (repeating on purpose); the
    real gap is at index 3. A pre-fix implementation would have reported
    sessions[1] (closes.index(200.0) == 0, bars[0 + 1]) instead of the
    actual gap day, sessions[3]."""
    symbol = "FLATCO"
    start = date(2026, 1, 1)
    sessions = [start + timedelta(days=i) for i in range(5)]
    closes = [200.0, 200.0, 200.0, 100.0, 101.0]
    opens = [200.0, 200.0, 200.0, 100.5, 101.0]
    vols = [1000.0, 1000.0, 1000.0, 5000.0, 4000.0]
    bars = [
        _bar(symbol, s, c, o, v)
        for s, c, o, v in zip(sessions, closes, opens, vols)
    ]
    found = detect_split_candidates_bars(bars, min_gap_pct=20)
    assert len(found) == 1
    cand = found[0]
    assert cand.session == sessions[3], (
        f"expected the real gap day {sessions[3]}, got {cand.session} "
        "(closes.index() relocation bug would report sessions[1])"
    )
    assert cand.session != sessions[1]
    assert cand.symbol == symbol
    assert cand.gap_index == 3


def test_normal_gap_not_flagged():
    closes = [200.0, 200.0, 180.0, 181.0]     # -10% gap: under the 20% floor
    opens = [200.0, 200.0, 181.0, 181.0]
    vols = [1000.0, 1000.0, 5000.0, 4000.0]
    assert detect_split_candidates(closes, opens, vols) == []


def test_volume_collapse_not_flagged():
    # 50% gap but volume collapsed: a delisting-style artifact, not a tradeable split
    closes = [200.0, 200.0, 100.0, 100.0]
    opens = [200.0, 200.0, 100.5, 100.0]
    vols = [1000.0, 1000.0, 5.0, 5.0]
    assert detect_split_candidates(closes, opens, vols, min_gap_pct=20,
                                   min_post_volume=0.1) == []


def test_untidy_factor_rejected():
    closes = [200.0, 200.0, 140.0, 141.0]     # implied 0.70: ~4.9% from 2:3, not clean
    opens = [200.0, 200.0, 140.0, 141.0]
    vols = [1000.0, 1000.0, 5000.0, 4000.0]
    found = detect_split_candidates(closes, opens, vols, clean_tolerance_pct=3.0)
    assert found == []


def test_adjust_series_compounds_two_actions():
    sessions = [date(2025, 1, d) for d in (1, 2, 3, 4, 5, 6)]
    closes = [400.0, 400.0, 400.0, 200.0, 200.0, 200.0]
    actions = [
        ConfirmedAction("X", date(2025, 1, 4), 0.5, "test"),   # 2:1 split
        ConfirmedAction("X", date(2025, 1, 6), 0.8, "test"),   # later 1.25:1 bonus-ish
    ]
    out = adjust_series(closes, sessions, "X", actions)
    # bars before Jan-4: x0.5 then (before Jan-6) x0.8 => 400*0.4 = 160
    assert out[0] == pytest.approx(160.0)
    assert out[1] == pytest.approx(160.0)
    # bars Jan-4/5 (on/after first ex, before second ex): x0.8 => 160
    assert out[3] == pytest.approx(160.0)
    assert out[5] == pytest.approx(200.0)              # on/after last ex: raw


def test_adjust_volume_inverse():
    sessions = [date(2025, 1, d) for d in (1, 2, 3, 4)]
    vols = [1000.0, 1000.0, 2000.0, 2000.0]
    actions = [ConfirmedAction("X", date(2025, 1, 3), 0.5, "test")]
    out = adjust_volume(vols, sessions, "X", actions)
    assert out[0] == pytest.approx(2000.0)             # pre-split volume doubles
    assert out[2] == pytest.approx(2000.0)             # on/after ex: unchanged


def test_rejects_length_mismatch():
    with pytest.raises(ContractError):
        adjust_series([1.0, 2.0], [date(2025, 1, 1)], "X", [])


def test_seed_csv_has_the_four_close_to_close_2_for_1():
    actions = load_confirmed_actions()
    by = {(a.symbol, a.ex_date): a for a in actions}
    assert by[("ANANDRATHI", date(2026, 6, 3))].factor == 0.5
    assert by[("BEML", date(2025, 11, 3))].factor == 0.5
    assert by[("AGIIL", date(2025, 2, 7))].factor == 0.5
    assert by[("ANUHPHR", date(2025, 7, 15))].factor == 0.5
    assert "ASHOKLEY" not in {a.symbol for a in actions}
    assert len(actions) == 4


def test_load_missing_csv_is_empty(tmp_path):
    assert load_confirmed_actions(tmp_path / "nope.csv") == []


def test_adjust_ohlcv_does_not_mutate_raw():
    sessions = [date(2026, 1, d) for d in (2, 3, 4, 5)]
    closes = [200.0, 202.0, 101.0, 102.0]
    raw = list(closes)
    actions = [ConfirmedAction("X", date(2026, 1, 4), 0.5, "test")]
    out = adjust_ohlcv(
        opens=closes, highs=closes, lows=closes, closes=closes,
        volumes=[1000, 1000, 2000, 2000], sessions=sessions, symbol="X",
        actions=actions,
    )
    assert closes == raw
    assert out["adjusted"] is True
    assert out["close"][0] == pytest.approx(100.0)
    assert out["close"][2] == pytest.approx(101.0)
    assert out["volume"][0] == pytest.approx(2000.0)


def test_adjust_ohlcv_noop_for_unlisted_symbol():
    sessions = [date(2026, 1, d) for d in (2, 3)]
    closes = [200.0, 202.0]
    actions = [ConfirmedAction("X", date(2026, 1, 3), 0.5, "test")]
    out = adjust_ohlcv(
        opens=closes, highs=closes, lows=closes, closes=closes,
        volumes=[1, 1], sessions=sessions, symbol="Y", actions=actions,
    )
    assert out["adjusted"] is False
    assert out["close"] == closes


def test_persist_confirmed_actions_round_trip(tmp_path):
    actions = load_confirmed_actions()
    path = persist_confirmed_actions(actions, tmp_path / "ca.parquet")
    assert path.exists()
    import pyarrow.parquet as pq
    rows = pq.read_table(path).to_pylist()
    assert {r["symbol"] for r in rows} == {"ANANDRATHI", "BEML", "AGIIL", "ANUHPHR"}
