"""Walk-forward folds and next-bar fills (N4 / swing-edges spec §1.6).

Defaults: expanding train, 5-session embargo, no same-bar lookahead.
A 4y-train / 1y-test scheme is accepted only when the calendar is long
enough; our current archive is not, and the function refuses to fake it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, ensure_date, require_float
from unidesk.momentum.data.calendar import TradingCalendar
from unidesk.research.costs import CostAssumptions, net_return_bps, round_trip_cost
from unidesk.research.labels import long_outcome

DEFAULT_EMBARGO = 5


@dataclass(frozen=True)
class Fold:
    fold_id: str
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    embargo_sessions: int
    scheme: str


def expanding_folds(
    calendar: TradingCalendar,
    *,
    min_train: int = 63,
    test_sessions: int = 21,
    embargo: int = DEFAULT_EMBARGO,
) -> tuple[Fold, ...]:
    """Expanding train, unused embargo gap, then a fixed-length test window."""
    if min_train < 1 or test_sessions < 1 or embargo < 0:
        raise ContractError("min_train, test_sessions must be >= 1; embargo >= 0")
    sessions = [d.trade_date for d in calendar.days]
    n = len(sessions)
    needed = min_train + embargo + test_sessions
    if n < needed:
        raise ContractError(
            f"calendar has {n} sessions; need at least {needed} "
            f"(min_train={min_train} + embargo={embargo} + test={test_sessions})"
        )
    folds = []
    cursor = min_train  # train is sessions[0:cursor]
    k = 1
    while True:
        test_start_i = cursor + embargo
        test_end_i = test_start_i + test_sessions - 1
        if test_end_i >= n:
            break
        train_end_i = cursor - 1
        folds.append(Fold(
            fold_id=f"exp-{k:02d}",
            train_start=sessions[0],
            train_end=sessions[train_end_i],
            test_start=sessions[test_start_i],
            test_end=sessions[test_end_i],
            embargo_sessions=embargo,
            scheme="expanding",
        ))
        cursor = test_end_i + 1
        k += 1
    if not folds:
        raise ContractError("no folds produced")
    return tuple(folds)


def years_4_1_folds(calendar: TradingCalendar, *, embargo: int = DEFAULT_EMBARGO) -> tuple[Fold, ...]:
    """Spec default. Refuses on a short calendar rather than shrinking the years."""
    n = len(calendar)
    if n < 5 * 200:
        raise ContractError(
            f"4y/1y walk-forward needs ~1000 sessions; calendar has {n}. "
            "Use expanding_folds until history reaches 2016."
        )
    return expanding_folds(calendar, min_train=4 * 252, test_sessions=252, embargo=embargo)


def session_in(session: date, start: date, end: date) -> bool:
    session = ensure_date(session, "session")
    return start <= session <= end


def assign_event(session: date, fold: Fold) -> Optional[str]:
    """``train``, ``test``, ``embargo``, or None (outside the fold span)."""
    session = ensure_date(session, "session")
    if session_in(session, fold.train_start, fold.train_end):
        return "train"
    if session_in(session, fold.test_start, fold.test_end):
        return "test"
    if fold.train_end < session < fold.test_start:
        return "embargo"
    return None


def next_session(calendar: TradingCalendar, session: date) -> Optional[date]:
    """Fill session: the next observed trading day. None at the calendar end.
    Same-bar fills are forbidden (spec §1.6)."""
    day = calendar.get(session)
    if day is None:
        return None
    return day.next_trade_date


def captured_return_bps(entry: float, future_closes: Sequence[float], horizon: int) -> float:
    """Close-to-close captured return over ``horizon`` future bars, in bps."""
    entry = require_float(entry, "entry")
    if entry <= 0:
        raise ContractError("entry must be positive")
    if horizon < 1:
        raise ContractError("horizon must be >= 1")
    if not future_closes:
        raise ContractError("no future closes")
    last = future_closes[min(horizon, len(future_closes)) - 1]
    last = require_float(last, "future_closes[]")
    return (last / entry - 1.0) * 10_000.0


def stop_aware_return_bps(
    entry: float,
    stop: float,
    future_closes: Sequence[float],
    horizon: int,
    *,
    stop_hit: bool,
) -> float:
    """Conservative realised return for an OHLC-labelled long.

    A stop touch exits at the stated stop, rather than allowing a later close
    to overwrite the loss. Gap-through execution requires intraday data and
    remains outside this EOD label; the separate cost model remains applied
    after this gross return is determined.
    """
    entry = require_float(entry, "entry")
    stop = require_float(stop, "stop")
    if entry <= 0:
        raise ContractError("entry must be positive")
    if stop >= entry:
        raise ContractError("stop must be below entry for a long")
    if stop_hit:
        return (stop / entry - 1.0) * 10_000.0
    return captured_return_bps(entry, future_closes, horizon)


def simulate_long(
    *,
    entry: float,
    stop: float,
    future_highs: Sequence[float],
    future_lows: Sequence[float],
    future_closes: Sequence[float],
    horizon: int,
    order_value: float,
    adv_value: float,
    gap_entry: bool = False,
    assumptions: CostAssumptions = CostAssumptions(),
) -> dict:
    """Event-driven long: labels from the future slice, net of the cost model."""
    outcome = long_outcome(
        entry=entry, stop=stop, highs=future_highs, lows=future_lows, horizon=horizon,
    )
    gross_bps = stop_aware_return_bps(
        entry, stop, future_closes, horizon, stop_hit=outcome.stop_hit,
    )
    cost = round_trip_cost(
        order_value=order_value, adv_value=adv_value,
        gap_entry=gap_entry, assumptions=assumptions,
    )
    return {
        "gross_bps": round(gross_bps, 4),
        "net_bps": round(net_return_bps(gross_bps, cost), 4),
        "cost_rt_bps": cost.total_rt_bps,
        "mfe_pct": outcome.mfe_pct,
        "mae_pct": outcome.mae_pct,
        "stop_hit": outcome.stop_hit,
        "potential_r_multiple": outcome.potential_r_multiple,
        "r_multiple": outcome.r_multiple,
        "assumptions_version": cost.assumptions_version,
    }
