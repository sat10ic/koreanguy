"""P2.3 registry: each detector is separately disableable; input math
for inside-bar geometry is frozen and hand-checked."""
from datetime import datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.corp_actions import ConfirmedAction
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.detectors.inputs import compute_setup_inputs
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.registry import (
    DETECTOR_NAMES, DetectorConfig, evaluate_all,
)
from unidesk.momentum.scan import scan_universe

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def test_unknown_detector_name_fails_closed():
    with pytest.raises(ContractError, match="unknown detector"):
        DetectorConfig(enabled=frozenset({"vibes"}))


def test_disabled_detector_absent_from_result():
    inputs = {
        "adr_pct": 8.0, "rs_rank": 90.0, "rvol": 3.0, "contraction_ratio": 0.4,
        "avwap_extension_adr": None, "gap_pct": 4.0, "close_location": 0.9,
        "delivery_ratio": 1.2, "listing_age_sessions": 30, "base_depth_pct": 20.0,
        "distance_from_listing_high_pct": 10.0, "is_inside_bar": True,
        "mother_range_pct": 4.0, "volume_ratio_bar_to_mother": 0.7,
        "breakout_rvol": 2.0, "close_cleared_pivot": True, "blue_sky": True,
        "overhead_room_adr": None, "base_breakout_depth_pct": 20.0,
        "base_breakout_contraction_ratio": 0.7, "proximity_to_anchor_pct": 1.0,
        "pullback_volume_ratio": 0.5, "reclaimed": True, "volume_expansion": 1.6,
        "rs_improving": True, "failed_breakdown": True,
    }
    only_burst = evaluate_all(inputs, config=DetectorConfig.only(["momentum_burst"]))
    assert set(only_burst) == {"momentum_burst"}
    assert only_burst["momentum_burst"][0] is Detection.VALID

    all_on = evaluate_all(inputs)
    assert set(all_on) == set(DETECTOR_NAMES)


def test_scan_honours_detector_config_disable():
    store = InMemoryMarketStore()
    for i in range(70):
        close = 90 + i * 0.75
        bar = DailyBar(
            symbol="STRONG", session=(DAY0 + timedelta(days=i)).date(),
            open=close, high=close + 0.5, low=close - 0.5, close=close,
            volume=1000 + i * 10, delivery_percentage=50.0, data_version="test",
        )
        store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))
    result = scan_universe(
        store, DAY0 + timedelta(days=70),
        detector_config=DetectorConfig.only(["power_play"]),
    )
    assert result.scanned == 1
    names = set(result.symbols[0].detectors)
    assert names == {"power_play"}


def test_scan_quarantines_an_unconfirmed_split_candidate_before_rs_ranking():
    store = InMemoryMarketStore()
    for symbol in ("CLEAN", "GAPCO"):
        for i in range(70):
            close = 100.0 + i
            if symbol == "GAPCO" and i >= 35:
                close /= 2.0
            bar = DailyBar(
                symbol=symbol, session=(DAY0 + timedelta(days=i)).date(),
                open=close, high=close + 0.5, low=close - 0.5, close=close,
                volume=1_000, delivery_percentage=50.0, data_version="test",
            )
            store.add_daily_bar(
                VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1))
            )

    result = scan_universe(store, DAY0 + timedelta(days=70), run_detectors=False)

    assert [scan.symbol for scan in result.symbols] == ["CLEAN"]
    assert set(result.universe_returns) == {"CLEAN"}
    assert result.skipped["unconfirmed_corporate_action"] == 1

    confirmed = scan_universe(
        store,
        DAY0 + timedelta(days=70),
        run_detectors=False,
        actions=[ConfirmedAction("GAPCO", (DAY0 + timedelta(days=35)).date(), 0.5, "test")],
    )
    assert {scan.symbol for scan in confirmed.symbols} == {"CLEAN", "GAPCO"}
    assert confirmed.skipped["unconfirmed_corporate_action"] == 0


def _gate_bars(symbol, *, price=200.0, volume=200_000, n=65, freeze_tail=False):
    """Sessions for one universe-gate fixture symbol. Default price/volume
    (Rs 200, 200k shares/day => ~Rs 4cr/day turnover) clears both the price
    (Rs 30) and turnover (Rs 2cr) floors comfortably. ``freeze_tail`` makes
    the last 3 of the last 5 bars high==low (circuit_locked heuristic)."""
    bars = []
    for i in range(n):
        high = price + 0.5
        low = price - 0.5
        if freeze_tail and i >= n - 3:
            high = low = price
        bar = DailyBar(
            symbol=symbol, session=(DAY0 + timedelta(days=i)).date(),
            open=price, high=high, low=low, close=price,
            volume=int(volume), delivery_percentage=50.0, data_version="test",
        )
        bars.append(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))
    return bars


def test_scan_applies_universe_gates_before_rs_ranking():
    """F5 fix: price floor, turnover floor, probable-ETF, and circuit-lock
    each independently exclude a symbol from the universe BEFORE the
    cross-sectional RS ranking is built -- same principle as the CA
    quarantine above, proven per-gate with one fixture symbol failing
    exactly one gate at a time, plus one clean symbol that clears all four."""
    store = InMemoryMarketStore()
    fixtures = {
        "GATEOK": _gate_bars("GATEOK"),                                  # passes every gate
        "GATEPENNY": _gate_bars("GATEPENNY", price=20.0),                # price < Rs 30 floor
        "GATETHIN": _gate_bars("GATETHIN", volume=500),                  # turnover < Rs 2cr/day
        "NIFTYBEES": _gate_bars("NIFTYBEES"),                            # real ETF-keyword symbol
        "GATEFROZEN": _gate_bars("GATEFROZEN", freeze_tail=True),        # circuit-locked tail
    }
    for symbol, bars in fixtures.items():
        for vb in bars:
            store.add_daily_bar(vb)

    as_of = DAY0 + timedelta(days=65)

    # Default (apply_universe_gates=False): existing behaviour is unchanged --
    # nothing beyond the session-count floor is filtered, so all 5 symbols
    # are scanned. This is the regression-safety half of the F5 fix: opting
    # in is explicit, not a silent behaviour change for every existing caller.
    ungated = scan_universe(store, as_of, run_detectors=False, min_sessions=61)
    assert {s.symbol for s in ungated.symbols} == set(fixtures)
    assert not any(k.startswith("universe_gate_") for k in ungated.skipped)

    # Opted in: each fixture is excluded by exactly the gate it was built to
    # fail, named in `skipped`, and absent from both the scanned symbols and
    # the RS-ranking input (`universe_returns`) -- never a silent drop.
    gated = scan_universe(
        store, as_of, run_detectors=False, min_sessions=61, apply_universe_gates=True,
    )
    assert {s.symbol for s in gated.symbols} == {"GATEOK"}
    assert set(gated.universe_returns) == {"GATEOK"}
    assert gated.skipped["universe_gate_price_floor"] == 1
    assert gated.skipped["universe_gate_turnover_floor"] == 1
    assert gated.skipped["universe_gate_probable_etf"] == 1
    assert gated.skipped["universe_gate_circuit_locked"] == 1
    assert sum(v for k, v in gated.skipped.items() if k.startswith("universe_gate_")) == 4


def test_inside_bar_input_math():
    # mother: range 10 on prev close 105 → 10/105; inside bar fully contained
    opens = [100, 101]
    highs = [110, 108]
    lows = [100, 102]
    closes = [105, 106]
    vols = [1000, 400]
    inp = compute_setup_inputs(opens=opens, highs=highs, lows=lows, closes=closes, volumes=vols)
    assert inp["is_inside_bar"] is True
    assert inp["mother_range_pct"] == pytest.approx((110 - 100) / 105 * 100, abs=1e-3)
    assert inp["volume_ratio_bar_to_mother"] == pytest.approx(0.4)
    assert inp["gap_pct"] == pytest.approx((101 / 105 - 1) * 100, abs=1e-3)
    outside = compute_setup_inputs(
        opens=[100, 101], highs=[110, 112], lows=[100, 99],
        closes=[105, 106], volumes=[1000, 400],
    )
    assert outside["is_inside_bar"] is False


def test_base_breakout_inputs_exclude_the_decision_bar_from_pivot_and_depth():
    # The last bar wicks far below the base floor. It must not be allowed to
    # distort the base it is supposed to clear.
    opens = [95.0] * 25 + [101.0]
    highs = [100.0] * 25 + [150.0]
    lows = [90.0] * 25 + [10.0]
    closes = [95.0] * 25 + [101.0]
    volumes = [1_000.0] * 26

    inputs = compute_setup_inputs(
        opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes,
    )

    assert inputs["pre_breakout_pivot"] == 100.0
    assert inputs["close_cleared_pivot"] is True
    assert inputs["base_breakout_depth_pct"] == pytest.approx(10.0)


def test_blue_sky_is_unresolved_not_a_coincidental_true_on_a_short_history_symbol():
    """Regression for the F4 review finding: with only ~20 bars of history,
    ``h[-base_window-1:-1]`` (the pivot slice) and ``h[:-1]`` (the old
    "prior_listing_high" slice) are the *same* bars, so a close that clears
    the base pivot mechanically cleared the "listing high" too — blue_sky
    came out True by construction, not because the symbol is genuinely at a
    new high. That silently satisfied base_breakout()'s room-vs-ADR check
    for any short-history symbol, exactly the gameable path the room rule
    exists to prevent. blue_sky must be unresolved (None) below the trusted
    floor instead of guessing True, and base_breakout() must not silently
    pass on it.
    """
    base_window = 20
    n = base_window + 1  # the exact degenerate boundary from the review
    opens = [95.0] * n
    highs = [100.0] * (n - 1) + [101.0]
    lows = [90.0] * n
    closes = [95.0] * (n - 1) + [101.0]
    volumes = [1_000.0] * n

    inputs = compute_setup_inputs(
        opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes,
        base_window=base_window,
    )

    # The old bug's precondition still holds: the decision bar clears the
    # pivot computed from the identical short window.
    assert inputs["pre_breakout_pivot"] == 100.0
    assert inputs["close_cleared_pivot"] is True

    # But blue_sky must NOT be silently True just because the window is short.
    assert inputs["blue_sky"] is None
    assert inputs["overhead_room_adr"] is None

    # And base_breakout() must not silently pass the room check on it —
    # blue_sky=None is unresolved, which is a missing mandatory input.
    det, failures = evaluate_all(
        {**inputs, "rs_rank": 90.0}, config=DetectorConfig.only(["base_breakout"]),
    )["base_breakout"]
    assert det is Detection.INSUFFICIENT_DATA
    assert "missing:blue_sky" in failures


def test_blue_sky_resolves_once_the_history_floor_is_reached():
    """Sanity check on the other side of the floor: with enough real bars,
    blue_sky is computed normally and a close strictly above all prior highs
    is a genuine new high."""
    from unidesk.momentum.detectors.inputs import BLUE_SKY_MIN_SESSIONS

    n = BLUE_SKY_MIN_SESSIONS
    opens = [95.0] * (n - 1) + [101.0]
    highs = [100.0] * (n - 1) + [101.0]
    lows = [90.0] * n
    closes = [95.0] * (n - 1) + [101.0]
    volumes = [1_000.0] * n

    inputs = compute_setup_inputs(opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes)
    assert inputs["blue_sky"] is True

    # A close exactly at (not above) the prior high is not yet a new one —
    # matches close_cleared_pivot's strict ">" semantics.
    closes_at_high = [95.0] * (n - 1) + [100.0]
    opens_at_high = [95.0] * (n - 1) + [100.0]
    inputs_at_high = compute_setup_inputs(
        opens=opens_at_high, highs=highs, lows=lows, closes=closes_at_high, volumes=volumes,
    )
    assert inputs_at_high["blue_sky"] is False
