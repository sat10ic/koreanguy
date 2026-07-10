"""Round-4 gate-recalibration EVIDENCE replays (2026-07-10).

Pure, dependency-light re-computation of managed-exit outcomes for the
ALREADY-PERSISTED candidate cohort (`manas_os.scanner.outcomes._managed_exit`
baseline). This module does NOT rescan or touch gates/plan -- it only varies
two things about how a persisted candidate's plan is walked forward, so the
E1 gate-passed-cohort-has-no-edge finding can be interrogated without a full
36-minute replay rerun:

  - stop width multiplier (E-A): scale the risk (entry-stop) distance used
    both as the R denominator AND as the actual stop price walked against.
    x1.0 reproduces the existing `_managed_exit` baseline exactly.
  - entry mode (E-B): 'next_open' (baseline -- fill unconditionally at the
    next session's open) vs 'buy_stop' (skip the trade entirely unless a
    session ON OR AFTER the next session trades a HIGH >= the plan entry/
    pivot price -- i.e. require the breakout to actually confirm before
    granting a fill; the fill price is the first such high-crossing
    session's open if it already gapped above entry, else the entry price
    itself printed intraday).

No look-ahead: every function only reads bars strictly at/after the entry
search start, and decisions at each bar only use that bar's own OHLC (the
same "stop-checked-before-favorable" conservative sequencing convention as
the baseline `_managed_exit`, since intraday order is unknown from daily
bars).

These are PURE functions over an explicit list of bar dicts (as fetched by
the caller from `daily_prices`) -- no sqlite connection is threaded through,
so they are trivially unit-testable with hand-built bar-walk fixtures.
"""
from __future__ import annotations

from typing import Any, TypedDict

STOP_SLIPPAGE_PCT = 0.002  # match scanner.outcomes._managed_exit convention


class Bar(TypedDict):
    trade_date: str
    open: float
    high: float
    low: float
    close: float


def find_entry_bar(
    bars: list[Bar], mode: str, plan_entry: float,
) -> tuple[int, float] | None:
    """Locate the index (into `bars`) and fill price of the entry bar.

    `bars` must already be restricted to sessions strictly AFTER the
    candidate/signal date, in trade_date ascending order (the caller decides
    where "after" starts -- this function does no date filtering itself).

    mode='next_open': always fills at bars[0]'s open (the existing baseline
    convention -- unconditional next-session fill).

    mode='buy_stop': requires CONFIRMATION -- skip forward until a bar's high
    trades at/above `plan_entry` (the breakout actually happens). Fill price:
    if that bar's open is already >= plan_entry (gapped above), fill at the
    open (an honest, if favorable, fill); otherwise fill at plan_entry itself
    (the buy-stop order triggers intraday at the pivot). Returns None if no
    bar in the supplied window ever confirms (buy-stop never fills --
    reported by the caller as a skip).

    Returns (index_into_bars_of_entry_bar, fill_price) or None.
    """
    if not bars:
        return None
    if mode == "next_open":
        return 0, float(bars[0]["open"])
    if mode == "buy_stop":
        for i, bar in enumerate(bars):
            o, h = float(bar["open"]), float(bar["high"])
            if h >= plan_entry:
                fill = o if o >= plan_entry else plan_entry
                return i, float(fill)
        return None
    raise ValueError(f"unknown entry mode {mode!r}; expected 'next_open' or 'buy_stop'")


def walk_managed_exit(
    bars: list[Bar],
    plan_entry: float,
    plan_stop: float,
    horizon: int,
    stop_multiplier: float = 1.0,
    entry_mode: str = "next_open",
) -> dict[str, Any] | None:
    """Recompute a managed-exit outcome under an (entry_mode, stop_multiplier)
    variant, given ALL bars from the candidate date onward (so `buy_stop` has
    room to search for confirmation; `next_open` only ever uses bars[0]).

    R unit convention (unchanged from the baseline `_managed_exit`): the risk
    denominator is `plan_entry - effective_stop`, where effective_stop is the
    ORIGINAL plan_entry minus (original risk * stop_multiplier) -- i.e. the
    stop distance is scaled from the plan's own entry, not from the actual
    fill. This keeps E-A's "wider stop" isolated from E-B's "different fill":
    scaling the stop does not silently change what a x1.0/next_open run
    reproduces. The reference price for R is still `plan_entry` (matching the
    baseline's documented convention of pricing R against the PLAN, not the
    realized fill), so a buy_stop fill that misses (skips) small early loss is
    still bounded correctly relative to that same plan-referenced risk.

    Returns None when:
      - plan_stop >= plan_entry (invalid long risk plan), or
      - entry_mode='buy_stop' and no bar ever confirms (buy-stop never
        filled -- the caller should count this as a skip, not silently drop
        it from the denominator), or
      - fewer than `horizon` bars remain after the entry bar (window
        incomplete -- still pending).
    """
    base_risk = float(plan_entry) - float(plan_stop)
    if base_risk <= 0:
        return None
    risk = base_risk * float(stop_multiplier)
    if risk <= 0:
        return None
    effective_stop = float(plan_entry) - risk

    located = find_entry_bar(bars, entry_mode, float(plan_entry))
    if located is None:
        return {"skipped": True, "skip_reason": "buy_stop_never_confirmed"}
    entry_idx, fill = located

    window = bars[entry_idx: entry_idx + horizon]
    if len(window) < horizon:
        return None  # incomplete window -- still pending, not a skip

    running_mfe_r: float | None = None
    running_mae_r: float | None = None
    hit_1r = False
    hit_2r = False
    for bar in window:
        o, h, low, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
        if o <= effective_stop:
            exit_price = o * (1.0 - STOP_SLIPPAGE_PCT)
            r = (exit_price - float(plan_entry)) / risk
            running_mae_r = r if running_mae_r is None else min(running_mae_r, r)
            return _result(
                fill, bar["trade_date"], exit_price, "gap_through_stop", r,
                running_mfe_r, running_mae_r, hit_1r, hit_2r,
            )
        if low <= effective_stop:
            exit_price = effective_stop * (1.0 - STOP_SLIPPAGE_PCT)
            r = (exit_price - float(plan_entry)) / risk
            bar_mae_r = (low - float(plan_entry)) / risk
            running_mae_r = bar_mae_r if running_mae_r is None else min(running_mae_r, bar_mae_r)
            return _result(
                fill, bar["trade_date"], exit_price, "stop", r,
                running_mfe_r, running_mae_r, hit_1r, hit_2r,
            )
        bar_mfe_r = (h - float(plan_entry)) / risk
        bar_mae_r = (low - float(plan_entry)) / risk
        running_mfe_r = bar_mfe_r if running_mfe_r is None else max(running_mfe_r, bar_mfe_r)
        running_mae_r = bar_mae_r if running_mae_r is None else min(running_mae_r, bar_mae_r)
        if bar_mfe_r >= 1.0:
            hit_1r = True
        if bar_mfe_r >= 2.0:
            hit_2r = True

    last = window[-1]
    close = float(last["close"])
    r = (close - float(plan_entry)) / risk
    return _result(
        fill, last["trade_date"], close, "horizon_close", r,
        running_mfe_r, running_mae_r, hit_1r, hit_2r,
    )


def _result(fill, exit_date, exit_price, exit_reason, r, mfe_r, mae_r, hit_1r, hit_2r) -> dict[str, Any]:
    return {
        "skipped": False,
        "entry_fill": round(fill, 4),
        "exit_date": exit_date,
        "exit_price": round(exit_price, 4),
        "exit_reason": exit_reason,
        "managed_r": round(r, 4),
        "managed_mfe_r": round(mfe_r, 4) if mfe_r is not None else round(r, 4),
        "managed_mae_r": round(mae_r, 4) if mae_r is not None else round(r, 4),
        "hit_1r": int(hit_1r),
        "hit_2r": int(hit_2r),
    }
