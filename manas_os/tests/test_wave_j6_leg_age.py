"""Tests for WAVE_J J6: real leg-age wired into gate_fresh_leg as a SHADOW
evidence field (enforce_staleness=False) with zero behavior change.
"""
from __future__ import annotations

from manas_os.scanner import candidates, gates


def _bar(i, close, high=None, low=None):
    return {
        "date": f"2026-01-{i + 1:02d}",
        "open": close,
        "high": high if high is not None else close * 1.01,
        "low": low if low is not None else close * 0.99,
        "close": close,
        "volume": 1_000_000,
    }


def _uptrend(n, start=100.0, step=0.3):
    return [_bar(i, start + i * step) for i in range(n)]


def _extended_above_21ema():
    bars = _uptrend(30, start=100.0, step=0.0)
    bars[-1] = _bar(29, 116.0, high=116.0, low=112.0)
    return bars


def _early_turn_downtrend(n=210):
    bars = []
    for i in range(n):
        if i < 200:
            close = 200.0 - i * 0.5
        else:
            close = 100.0 + (i - 199) * 1.0
        bars.append(_bar(i, close))
    return bars


# --- candidates._compute_breakout_age --------------------------------------------

def test_compute_breakout_age_finds_recent_crossover():
    bars = _uptrend(20, start=90.0, step=1.0)  # closes: 90, 91, ..., 109
    pivot = 100.0  # crossed between bar index 9 (99) and 10 (100)? close>pivot strictly
    age = candidates._compute_breakout_age(bars, pivot)
    # close[10]=100 not >100; close[11]=101>100, prior close[10]=100<=100 -> crossover at idx 11
    assert age == (len(bars) - 1) - 11


def test_compute_breakout_age_none_when_no_pivot():
    bars = _uptrend(10)
    assert candidates._compute_breakout_age(bars, None) is None


def test_compute_breakout_age_none_when_never_crossed():
    bars = _uptrend(10, start=50.0, step=0.1)  # closes stay well below pivot
    assert candidates._compute_breakout_age(bars, 1000.0) is None


def test_compute_breakout_age_none_thin_bars():
    assert candidates._compute_breakout_age([_bar(0, 100.0)], 90.0) is None


# --- gate_fresh_leg shadow behavior -----------------------------------------------

def test_gate_fresh_leg_shadow_records_would_refuse_without_refusing():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age,
                              enforce_staleness=False)
    assert r["pass"] is True  # zero behavior change
    assert r["evidence"]["would_refuse_stale"] is True
    assert r["evidence"]["leg_age"] == stale_age


def test_gate_fresh_leg_enforce_staleness_true_actually_refuses():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age,
                              enforce_staleness=True)
    assert r["pass"] is False
    assert "bars old" in r["reason"]


def test_gate_fresh_leg_non_stale_age_would_refuse_stale_false():
    bars = _uptrend(60, step=0.05)
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=3,
                              enforce_staleness=False)
    assert r["pass"] is True
    assert r["evidence"]["would_refuse_stale"] is False
    assert r["evidence"]["leg_age"] == 3


def test_gate_fresh_leg_default_enforce_staleness_is_false():
    bars = _uptrend(60, step=0.05)
    stale_age = gates.PULLBACK_AGE_MAX + 5
    r = gates.gate_fresh_leg(bars, pivot=bars[-1]["close"] * 0.99, breakout_age=stale_age)
    assert r["pass"] is True


# --- cascade wiring: same fixture passes identically before/after ----------------

def test_run_cascade_same_fixture_passes_identically_with_real_age():
    """Simulates the pre-J6 (breakout_age=None) vs post-J6 (real age,
    enforce_staleness=False) cascade call for the fresh-leg gate only —
    identical pass/fail, evidence now carries leg_age."""
    bars = _uptrend(60, step=0.05)
    pivot = bars[-1]["close"] * 0.99

    before = gates.gate_fresh_leg(bars, pivot=pivot, breakout_age=None)
    after = gates.gate_fresh_leg(bars, pivot=pivot, breakout_age=gates.PULLBACK_AGE_MAX + 10,
                                  enforce_staleness=False)

    assert before["pass"] == after["pass"] is True
    assert "leg_age" not in before["evidence"] or before["evidence"]["leg_age"] is None
    assert after["evidence"]["leg_age"] == gates.PULLBACK_AGE_MAX + 10
    assert after["evidence"]["would_refuse_stale"] is True


# --- WAVE_M M4: family-scoped structural objections -------------------------------

def test_momentum_family_extended_above_21ema_passes_with_objection():
    r = gates.gate_fresh_leg(
        _extended_above_21ema(),
        pivot=None,
        breakout_age=1,
        setup_family="momentum",
    )

    assert r["pass"] is True
    assert r["evidence"]["extension_21"] > gates.EXT21_STALE
    objections = r["evidence"]["objections"]
    assert objections == [{
        "code": "extended_leg",
        "gate": "fresh-leg",
        "reason": (
            f"{r['evidence']['extension_21']:.1f}% above 21EMA -- extended; enter only on confirmation "
            "(buy-stop above the current day's high / ORB), not at market"
        ),
        "weight": gates.OBJECTION_WEIGHTS["extended_leg"],
    }]


def test_base_family_extended_above_21ema_still_hard_fails():
    r = gates.gate_fresh_leg(
        _extended_above_21ema(),
        pivot=None,
        breakout_age=1,
        setup_family="base/pattern",
    )

    assert r["pass"] is False
    assert r["gate"] == "fresh-leg"
    assert "extended:" in r["reason"]
    assert "objections" not in r["evidence"]


def test_reversal_family_downtrend_structure_passes_with_objection():
    r = gates.gate_trend_template(_early_turn_downtrend(), "reversal", rs_rating=90)

    assert r["pass"] is True
    objections = r["evidence"]["objections"]
    assert any(o == {
        "code": "downtrend_structure",
        "gate": "trend-template",
        "reason": "50SMA below 200SMA -- reversal/early-turn, not an established uptrend",
        "weight": gates.OBJECTION_WEIGHTS["downtrend_structure"],
    } for o in objections)


def test_base_family_downtrend_structure_still_hard_fails():
    r = gates.gate_trend_template(_early_turn_downtrend(), "base/pattern", rs_rating=90)

    assert r["pass"] is False
    assert r["gate"] == "trend-template"
    assert "not in a confirmed uptrend" in r["reason"]


def _recovery_bars(close=96.0, previous=92.0):
    closes = [100.0] * 150 + [90.0] * 48 + [previous, close]
    return [
        {"open": c, "high": c + 1, "low": c - 1, "close": c, "prev_close": closes[i - 1] if i else None}
        for i, c in enumerate(closes)
    ]


def test_catalyst_fresh_move_just_under_200sma_carries_objection():
    r = gates.gate_trend_template(_recovery_bars(), "catalyst", rs_rating=90)
    assert r["pass"] is True
    assert any(
        o["code"] == "downtrend_structure" and "within 3% below 200SMA" in o["reason"]
        for o in r["evidence"]["objections"]
    )


def test_momentum_does_not_get_pre_200sma_recovery_waiver():
    r = gates.gate_trend_template(_recovery_bars(), "momentum", rs_rating=90)
    assert r["pass"] is False


def test_catalyst_genuine_downtrend_still_refuses():
    r = gates.gate_trend_template(_recovery_bars(close=80.0, previous=76.0), "catalyst", rs_rating=90)
    assert r["pass"] is False


def test_mild_asm_surfaced_not_refused_by_tradability():
    # discovery-before-refusal (2026-07-15): LT-ASM stage I is the mildest tier
    # (1000+ NSE mid-caps, incl. real practitioner setups like FCL/JNKINDIA).
    # Surface with a warning chip; do NOT hard-block.
    r = gates.gate_tradability(
        _uptrend(30),
        symbol="LTASM1",
        quality={"asm_stage": "LTASM - I", "market_cap_cr": 5000},
        universe_verdict={"tradeable": True},
    )

    assert r["pass"] is True
    assert "ASM" in (r["evidence"].get("asm_warn") or "")


def test_severe_asm_still_hard_refused_by_tradability():
    # Restrictive tiers (LT stage III/IV, ST stage II, GSM, T2T) stay a hard refuse.
    r = gates.gate_tradability(
        _uptrend(30),
        symbol="LTASM4",
        quality={"asm_stage": "LTASM - IV", "market_cap_cr": 5000},
        universe_verdict={"tradeable": True},
    )

    assert r["pass"] is False
    assert r["gate"] == "tradability"
    assert "ASM" in r["reason"]


def test_no_trade_regime_still_hard_refuses():
    r = gates.gate_regime("momentum", "NO_TRADE")

    assert r["pass"] is False
    assert r["gate"] == "regime"
    assert r["evidence"]["hard"] is True
