"""Tests for backtest/entry_variants.py (WAVE_J J2)."""
from __future__ import annotations

from unittest.mock import patch

from manas_os.backtest import entry_variants as ev
from manas_os.backtest import exit_variants


def _bar(o, h, l, c):
    return {"trade_date": "2026-01-01", "open": o, "high": h, "low": l, "close": c}


def _pass_verdict(**evidence):
    return {"pass": True, "reason": None, "evidence": evidence}


def _fail_verdict(reason, **evidence):
    return {"pass": False, "reason": reason, "evidence": evidence}


# --- apply_entry_refusals --------------------------------------------------------

def test_apply_entry_refusals_empty_hypotheses_always_eligible():
    result = ev.apply_entry_refusals([_bar(1, 2, 0.5, 1.5)], [_bar(1, 2, 0.5, 1.5)], set())
    assert result == {"eligible": True, "failed": None, "reason": None, "evidence": None}


def test_apply_entry_refusals_h1_refuses():
    with patch.object(ev.entry_quality, "rmv_eligible", return_value=_fail_verdict("no coil")):
        result = ev.apply_entry_refusals([], [], {"H1"})
    assert result["eligible"] is False
    assert result["failed"] == "H1"
    assert result["reason"] == "no coil"


def test_apply_entry_refusals_h2_refuses():
    with patch.object(ev.entry_quality, "rmv_eligible", return_value=_pass_verdict()), \
         patch.object(ev.entry_quality, "leg_fresh", return_value=_fail_verdict("stale")):
        result = ev.apply_entry_refusals([], [], {"H1", "H2"})
    assert result["failed"] == "H2"


def test_apply_entry_refusals_h4_refuses():
    with patch.object(ev.entry_quality, "strong_start_quality", return_value=_fail_verdict("bad trigger day")):
        result = ev.apply_entry_refusals([], [], {"H4"})
    assert result["failed"] == "H4"


def test_apply_entry_refusals_h5_refuses():
    with patch.object(ev.entry_quality, "mswing_ok", return_value=_fail_verdict("down")):
        result = ev.apply_entry_refusals([], [], {"H5"})
    assert result["failed"] == "H5"


def test_apply_entry_refusals_h6_refuses():
    with patch.object(ev.entry_quality, "burst_exhausted", return_value=_fail_verdict("climax")):
        result = ev.apply_entry_refusals([], [], {"H6"})
    assert result["failed"] == "H6"


def test_apply_entry_refusals_order_h1_before_h2():
    # both would fail; H1 is checked first per _HYPOTHESIS_ORDER
    with patch.object(ev.entry_quality, "rmv_eligible", return_value=_fail_verdict("no coil")), \
         patch.object(ev.entry_quality, "leg_fresh", return_value=_fail_verdict("stale")):
        result = ev.apply_entry_refusals([], [], {"H1", "H2"})
    assert result["failed"] == "H1"


def test_apply_entry_refusals_all_pass():
    with patch.object(ev.entry_quality, "rmv_eligible", return_value=_pass_verdict()), \
         patch.object(ev.entry_quality, "leg_fresh", return_value=_pass_verdict()), \
         patch.object(ev.entry_quality, "strong_start_quality", return_value=_pass_verdict()), \
         patch.object(ev.entry_quality, "mswing_ok", return_value=_pass_verdict()), \
         patch.object(ev.entry_quality, "burst_exhausted", return_value=_pass_verdict()):
        result = ev.apply_entry_refusals([], [], {"H1", "H2", "H4", "H5", "H6"})
    assert result["eligible"] is True


def test_apply_entry_refusals_unknown_hypothesis_ignored():
    result = ev.apply_entry_refusals([], [], {"H99"})
    assert result["eligible"] is True


def test_apply_entry_refusals_no_look_ahead_only_trigger_bars_passed():
    """Regression guard: refusal checks must only ever be called with
    trigger_bars, never future_bars-shaped data."""
    seen = []

    def _spy(trigger_bars, index_bars):
        seen.append(trigger_bars)
        return _pass_verdict()

    trigger_bars = [_bar(1, 2, 0.5, 1.5)]
    with patch.object(ev.entry_quality, "mswing_ok", side_effect=_spy):
        ev.apply_entry_refusals(trigger_bars, [_bar(1, 1, 1, 1)], {"H5"})
    assert seen == [trigger_bars]


# --- run_variant / reproduction guard --------------------------------------------

def _walk_fixture():
    """A simple multi-bar fixture: entry fills next_open, price grinds up,
    never hits the stop, horizon closes out positive."""
    bars = [
        _bar(100, 102, 99, 101),   # next-session open=100 -> next_open fill
        _bar(101, 106, 100, 105),
        _bar(105, 110, 104, 108),
    ]
    return bars


def test_run_variant_empty_hypotheses_reproduces_e1_baseline_exactly():
    """REPRODUCTION GUARD: empty hypothesis set + next_open fill must
    reproduce exit_variants.walk_managed_exit's own baseline output exactly
    for the same fixture — entry refusals must be a complete no-op when no
    hypothesis is selected."""
    bars = _walk_fixture()
    plan_entry, plan_stop, horizon = 100.0, 95.0, 3

    baseline = exit_variants.walk_managed_exit(bars, plan_entry, plan_stop, horizon)

    result = ev.run_variant(
        trigger_bars=[_bar(90, 95, 89, 94)],
        index_bars=[_bar(90, 95, 89, 94)],
        future_bars=bars,
        plan_entry=plan_entry,
        plan_stop=plan_stop,
        horizon=horizon,
        hypotheses=set(),
    )

    assert result["eligible"] is True
    assert result["failed"] is None
    assert result["outcome"] == baseline


def test_run_variant_refused_never_reaches_exit_walk():
    with patch.object(ev.entry_quality, "rmv_eligible", return_value=_fail_verdict("no coil")):
        result = ev.run_variant(
            trigger_bars=[_bar(90, 95, 89, 94)],
            index_bars=[_bar(90, 95, 89, 94)],
            future_bars=_walk_fixture(),
            plan_entry=100.0,
            plan_stop=95.0,
            horizon=3,
            hypotheses={"H1"},
        )
    assert result == {"eligible": False, "failed": "H1", "outcome": None}


def test_run_variant_h3_forces_buy_stop_mode():
    bars = _walk_fixture()
    plan_entry, plan_stop, horizon = 100.0, 95.0, 3
    with patch.object(exit_variants, "walk_managed_exit", wraps=exit_variants.walk_managed_exit) as spy:
        ev.run_variant(
            trigger_bars=[_bar(90, 95, 89, 94)],
            index_bars=[_bar(90, 95, 89, 94)],
            future_bars=bars,
            plan_entry=plan_entry,
            plan_stop=plan_stop,
            horizon=horizon,
            hypotheses={"H3"},
            entry_mode="next_open",
        )
    _, kwargs = spy.call_args
    assert kwargs["entry_mode"] == "buy_stop"
