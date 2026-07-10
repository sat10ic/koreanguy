"""backtest/entry_variants.py — WAVE_J counterfactual entry-refusal composition
(design/WAVE_J_SPEC.md J2).

Pure functions composing scanner/entry_quality.py's per-metric refusals
(H1/H2/H4/H5/H6) plus a buy-stop confirmation fill (H3, via
backtest/exit_variants.find_entry_bar) so the E1 gate-passed-cohort replay can
be re-walked under counterfactual entry-population hypotheses without
rescanning or touching gates.py/plan.py (LOCKED — WAVE_J_SPEC.md §4.6).

STRICT NO-LOOK-AHEAD: every refusal check in `apply_entry_refusals` only sees
`trigger_bars` — the caller's responsibility is to pass a bar list that ends
at (and includes) the trigger/signal date and contains nothing after it. This
module never reaches into `future_bars` to decide eligibility; `future_bars`
is only ever walked forward AFTER the eligibility verdict is final, exactly
mirroring exit_variants.walk_managed_exit's own bars-at-or-after-entry
convention.
"""
from __future__ import annotations

from typing import Any

from manas_os.backtest import exit_variants
from manas_os.scanner import entry_quality

Bar = dict[str, Any]

# Composition order mirrors the pre-registered ranking in WAVE_J_SPEC.md §2
# (H1 ~ H2 > H3 > H4 > H5 > H6); H3 (buy-stop fill) is not a refusal here —
# it is applied downstream in run_variant via the entry_mode fill search.
_HYPOTHESIS_CHECKS = {
    "H1": lambda trigger_bars, index_bars: entry_quality.rmv_eligible(trigger_bars),
    "H2": lambda trigger_bars, index_bars: entry_quality.leg_fresh(trigger_bars),
    "H4": lambda trigger_bars, index_bars: entry_quality.strong_start_quality(trigger_bars),
    "H5": lambda trigger_bars, index_bars: entry_quality.mswing_ok(trigger_bars, index_bars),
    "H6": lambda trigger_bars, index_bars: entry_quality.burst_exhausted(trigger_bars),
}
_HYPOTHESIS_ORDER = ("H1", "H2", "H4", "H5", "H6")


def apply_entry_refusals(
    trigger_bars: list[Bar],
    index_bars: list[Bar],
    hypotheses: set[str],
) -> dict[str, Any]:
    """Compose the requested entry-quality refusals over `trigger_bars` (bars
    at/before the trigger date ONLY — no look-ahead). `hypotheses` is a subset
    of {"H1","H2","H4","H5","H6"} (H3 is handled separately by run_variant,
    since it is a fill-mode concern, not an eligibility refusal). Unknown keys
    are ignored (forward-compatible with future WAVE_J hypotheses added to
    entry_quality.py without needing this composer touched every time).

    Returns {"eligible": bool, "failed": str|None, "reason": str|None,
    "evidence": dict|None}.
    """
    for key in _HYPOTHESIS_ORDER:
        if key not in hypotheses:
            continue
        verdict = _HYPOTHESIS_CHECKS[key](trigger_bars, index_bars)
        if not verdict["pass"]:
            return {
                "eligible": False,
                "failed": key,
                "reason": verdict["reason"],
                "evidence": verdict["evidence"],
            }
    return {"eligible": True, "failed": None, "reason": None, "evidence": None}


def run_variant(
    trigger_bars: list[Bar],
    index_bars: list[Bar],
    future_bars: list[Bar],
    plan_entry: float,
    plan_stop: float,
    horizon: int,
    hypotheses: set[str],
    stop_multiplier: float = 1.0,
    entry_mode: str = "next_open",
) -> dict[str, Any]:
    """Full counterfactual replay of one candidate under one hypothesis
    bundle: apply_entry_refusals (population gate) composed with
    exit_variants.walk_managed_exit / find_entry_bar (fill + exit modeling).

    H3 ("buy-stop default fill") is not an eligibility refusal — it changes
    HOW the trade fills, not WHETHER the name is eligible — so "H3" in
    `hypotheses` forces entry_mode='buy_stop' regardless of the `entry_mode`
    argument (matching WAVE_J_SPEC.md §2 H3: "trade exists only if a session
    actually trades above the pivot").

    `future_bars` must be all bars from the trigger date onward (so buy_stop
    has room to search for confirmation) — it is never touched until AFTER
    the refusal verdict is computed, and refusals never see it.

    Returns {"eligible": bool, "failed": str|None, "outcome": dict|None}.
    `outcome` is exit_variants.walk_managed_exit's return value (None if the
    window is still pending; {"skipped": True, ...} if buy_stop never
    confirmed) when eligible, else None.
    """
    refusal = apply_entry_refusals(trigger_bars, index_bars, hypotheses)
    if not refusal["eligible"]:
        return {"eligible": False, "failed": refusal["failed"], "outcome": None}

    mode = "buy_stop" if "H3" in hypotheses else entry_mode
    outcome = exit_variants.walk_managed_exit(
        future_bars, plan_entry, plan_stop, horizon,
        stop_multiplier=stop_multiplier, entry_mode=mode,
    )
    return {"eligible": True, "failed": None, "outcome": outcome}
