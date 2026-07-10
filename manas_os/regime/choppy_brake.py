"""M9: choppy-market brake.

CITES (design/knowledge/TRADETM_NUANCES_COMPLETION.md):
  - W3: "if I lose 10 wrong trades worth of my portfolio [risk]" — hard
    brake after repeated stop-outs in chop. Tightened here to a 5-trading-day
    window (3+ stops hit in 5 sessions), the WAVE_M task's stated rule,
    rather than W3's raw 10-trade lifetime count, since a weekly cadence is
    what the run_card/tonights_call surfaces nightly.
  - W4: "if I lose 4% in one week, I will not trade" — weekly drawdown
    kill-switch at 4-5%.

Both conditions are OR'd: either one alone arms the brake.
"""
from __future__ import annotations

from typing import Any

CITE = "TRADETM_NUANCES_COMPLETION.md W3 (stop-out brake) + W4 (weekly-DD kill-switch)."

STOP_R_THRESHOLD = -0.8   # r_result <= this reads as "exited at/near stop" (proxy; journal has no explicit stopped-flag column)
STOP_COUNT_THRESHOLD = 3
LOOKBACK_TRADING_DAYS = 5
DD_THRESHOLD_PCT = 4.0


def _is_stop_hit(trade: dict[str, Any]) -> bool:
    r = trade.get("r_result")
    if r is None:
        return False
    try:
        return float(r) <= STOP_R_THRESHOLD
    except (TypeError, ValueError):
        return False


def brake(
    journal_trades: list[dict[str, Any]],
    as_of: str,
    weekly_dd_pct: float | None = None,
    stop_count_threshold: int = STOP_COUNT_THRESHOLD,
    lookback_trading_days: int = LOOKBACK_TRADING_DAYS,
    dd_threshold_pct: float = DD_THRESHOLD_PCT,
) -> dict[str, Any]:
    """Point-in-time choppy brake.

    journal_trades: journal_trades-shaped dicts (trade_date, r_result).
    weekly_dd_pct: optional externally-computed weekly % drawdown (negative
    for a loss, e.g. -4.5); when None the DD leg is skipped (no equity-curve
    input wired in yet — arms as soon as a caller supplies it).
    """
    trades = [t for t in journal_trades if t.get("trade_date") and t["trade_date"] <= as_of]
    window_dates = sorted({t["trade_date"] for t in trades}, reverse=True)[:lookback_trading_days]
    window = [t for t in trades if t["trade_date"] in window_dates]
    stops = [t for t in window if _is_stop_hit(t)]
    stop_count = len(stops)

    reasons: list[str] = []
    active = False

    if stop_count >= stop_count_threshold:
        active = True
        reasons.append(
            f"{stop_count} stops hit in the last {len(window_dates)} trading days "
            f"(>= {stop_count_threshold}) [W3]"
        )

    dd_triggered = weekly_dd_pct is not None and weekly_dd_pct <= -dd_threshold_pct
    if dd_triggered:
        active = True
        reasons.append(f"weekly drawdown {weekly_dd_pct:.1f}% breaches the {dd_threshold_pct:.0f}% kill-switch [W4]")

    return {
        "active": active,
        "reason": "; ".join(reasons) if reasons else None,
        "evidence": {
            "stop_count": stop_count,
            "stop_count_threshold": stop_count_threshold,
            "window_trading_days": len(window_dates),
            "weekly_dd_pct": weekly_dd_pct,
            "dd_threshold_pct": dd_threshold_pct,
        },
    }
