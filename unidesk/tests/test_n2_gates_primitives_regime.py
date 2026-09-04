"""N2 tests: universe gates (adopted semantics), spec-library primitives,
R0 regime classifier with hysteresis."""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.spec_library import (
    delivery_z, pocket_pivot, sma, stack_bull, stage2, tight_ratio, rvol_median,
)
from unidesk.momentum.regime import Regime, RegimeClassifier
from unidesk.momentum.universe.gates import GateVerdict, evaluate_gates, is_probable_etf

UTC = timezone.utc


# ------------------------------------------------------------------ gates


from datetime import timedelta
from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.market_store import VersionedDailyBar

BASE = datetime(2026, 6, 1, tzinfo=UTC)


def bars(closes, vols=None, freeze_days=()):
    """Trailing VersionedDailyBar list (attribute access, as gates expect)."""
    vols = vols or [10000] * len(closes)
    out = []
    for i, c in enumerate(closes):
        frozen = i in freeze_days
        bar = DailyBar(
            symbol="TEST", session=(BASE + timedelta(days=i)).date(),
            open=c - 0.01 if frozen else c, high=c + 0.01 if frozen else c + 1,
            low=c - 0.02, close=c, volume=0 if frozen else vols[i],
            data_version="test",
        )
        out.append(VersionedDailyBar(bar=bar, available_at=BASE + timedelta(days=i)))
    return out


def test_gate_passes_a_healthy_symbol():
    v = evaluate_gates("TRENT", bars([100.0] * 20, vols=[300000] * 20))
    assert v.tradeable is True and v.reasons_failed == ()
    assert v.metrics["mcap_check"].startswith("skipped")


def test_gate_fails_price_and_turnover_and_etf():
    v = evaluate_gates("GOLDBEES", bars([10.0] * 20, vols=[100] * 20))
    assert v.tradeable is False
    assert any("price" in r for r in v.reasons_failed)
    assert any("turnover" in r for r in v.reasons_failed)
    assert any("ETF" in r for r in v.reasons_failed)


def test_circuit_freeze_heuristic():
    v = evaluate_gates("TRENT", bars([50.0] * 20, freeze_days={17, 18, 19}))
    assert v.tradeable is False
    assert any("circuit" in r for r in v.reasons_failed)


def test_etf_heuristic_examples():
    assert is_probable_etf("NIFTYBEES") is True
    assert is_probable_etf("GOLDBEES") is True
    assert is_probable_etf("TRENT") is False


# ------------------------------------------------------------------ primitives


def test_sma_running_window_matches_naive():
    v = [float(i) for i in range(1, 11)]
    out = sma(v, 3)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(2.0)
    assert out[9] == pytest.approx((8 + 9 + 10) / 3)


def test_rvol_median_uses_median_not_mean():
    vols = [100.0] * 19 + [900.0, 200.0]     # one spike day inside the prior window
    out = rvol_median(vols, span=20)
    assert out[:20] == [None] * 20
    # prior window [0..20) has median 100 (spike at 900 resists), today 200
    assert out[20] == pytest.approx(2.0)


def test_delivery_z_zero_std_is_none():
    out = delivery_z([50.0] * 21, span=20)
    assert out[:20] == [None] * 20
    assert out[20] is None                            # std == 0 -> None, not divide-by-zero


def test_delivery_z_requires_full_window():
    out = delivery_z([50.0, None, 50.0], span=2)
    assert out == [None, None, None]                  # hole disables, R12


def test_pocket_pivot_benchmarks_down_day_volume():
    closes = [100.0, 95.0, 95.0, 96.0]               # day 3 closes up vs day 2
    down_vols = [100.0, 500.0, 100.0, 100.0]         # down day at index 1, vol 500
    out = pocket_pivot(closes, down_vols, lookback=3)
    assert out[3] is False                            # 100 <= 500 down-day benchmark
    up_vols = [100.0, 500.0, 100.0, 600.0]
    out2 = pocket_pivot(closes, up_vols, lookback=3)
    assert out2[3] is True                            # 600 > 500 benchmark
    assert out2[:3] == [None, None, None]             # lookback warm-up


def test_tight_ratio_hand_computed():
    highs = [10.5] * 9 + [10.8]
    lows = [10.0] * 10
    out = tight_ratio(highs, lows, n=10)
    assert out[8] is None
    assert out[9] == pytest.approx(0.08)              # 10.8/10.0 - 1: the spec's own example


def test_stack_bull_and_stage2():
    assert stack_bull(105, 100, 95, 90, 80) is True
    assert stack_bull(105, 106, 95, 90, 80) is False
    sma200 = [90.0] * 126 + [91.0] * 40
    assert stage2(105.0, sma200) is True
    assert stage2(100.0, sma200) is False             # below 1.15 premium
    assert stage2(105.0, [95.0] * 100) is False       # insufficient history


# ------------------------------------------------------------------ regime


def test_regime_seeds_then_hysteresis_blocks_flicker():
    from datetime import timedelta
    rc = RegimeClassifier(hysteresis_days=3)
    d0 = datetime(2026, 6, 1, tzinfo=UTC).date()
    rows = []
    plan = [(0.65, 1), (0.65, 1), (0.65, 1),          # BULL seeds immediately
            (0.30, 1), (0.30, 1),                     # BEAR pending, not flipped
            (0.30, 1), (0.30, 1),                     # day 3 -> BEAR flips
            (0.65, 1), (0.65, 1), (0.65, 1)]          # back to BULL after 3 days
    for i, (breadth, _) in enumerate(plan):
        rows.append(rc.update(d0 + timedelta(days=i), breadth))
    assert rows[0].regime is Regime.BULL
    assert rows[3].regime is Regime.BULL                   # hysteresis: not yet BEAR
    assert rows[5].regime is Regime.BEAR                   # 3 consecutive pending days
    assert rows[6].regime is Regime.BEAR
    assert rows[9].regime is Regime.BULL
    assert all(r.source == "breadth_only" for r in rows)


def test_regime_rejects_bad_breadth():
    rc = RegimeClassifier()
    with pytest.raises(ContractError):
        rc.update(date(2026, 6, 1), 1.5)
    with pytest.raises(ContractError):
        RegimeClassifier(bull_breadth=0.3, bear_breadth=0.5)
