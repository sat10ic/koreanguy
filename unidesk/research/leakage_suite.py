"""P7.3 leakage suite: honest helpers plus planted bugs the tests must catch.

Acceptance (build manual V2 N4): leakage tests *fail on planted bugs*.
A suite that only exercises the clean path is not a leakage suite.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from unidesk.contracts.base import ContractError, ensure_date, require_float
from unidesk.momentum.data.calendar import TradingCalendar
from unidesk.research.walkforward import Fold, assign_event


def pit_prefix(values: Sequence[float], as_of_index: int) -> list:
    """Bars with index <= as_of_index. Future bars are not in the prefix."""
    if as_of_index < 0:
        raise ContractError("as_of_index must be >= 0")
    return list(values[: as_of_index + 1])


def planted_include_future_bars(values: Sequence[float], as_of_index: int) -> list:
    """BUG: window accidentally includes the next bar."""
    return list(values[: as_of_index + 2])


def train_only_mean(train: Sequence[float], value: float) -> float:
    """Z-score style: mean fitted on train only, applied to ``value``."""
    if not train:
        raise ContractError("train window is empty")
    mu = sum(require_float(v, "train[]") for v in train) / len(train)
    return require_float(value, "value") - mu


def planted_full_sample_mean(all_values: Sequence[float], value: float) -> float:
    """BUG: normalisation fitted on train+test."""
    if not all_values:
        raise ContractError("series is empty")
    mu = sum(require_float(v, "all[]") for v in all_values) / len(all_values)
    return require_float(value, "value") - mu


def membership_as_of(history: Sequence[dict], symbol: str, as_of: date) -> bool:
    """PIT membership: active iff effective_from <= as_of <= effective_to.
    A missing ``effective_to`` is open-ended. Today's list is not consulted."""
    as_of = ensure_date(as_of, "as_of")
    for row in history:
        if row["symbol"] != symbol:
            continue
        start = ensure_date(row["effective_from"], "effective_from")
        end = row.get("effective_to")
        end_d = ensure_date(end, "effective_to") if end is not None else None
        if start <= as_of and (end_d is None or as_of <= end_d):
            return True
    return False


def planted_today_membership(today_symbols: Sequence[str], symbol: str, as_of: date) -> bool:
    """BUG: uses today's constituent list for every historical date."""
    return symbol in set(today_symbols)


def gold_known_at(cases: Sequence[dict], query: date) -> list:
    """Gold examples with session < query (strictly past)."""
    query = ensure_date(query, "query")
    return [c for c in cases if ensure_date(c["session"], "session") < query]


def planted_gold_includes_future(cases: Sequence[dict], query: date) -> list:
    """BUG: gold library has no date filter."""
    return list(cases)


def fold_leak(session: date, fold: Fold) -> bool:
    """True if this session would leak across the train/test cut (in both, or in embargo)."""
    bucket = assign_event(session, fold)
    return bucket in (None, "embargo") or False


def train_test_disjoint(train_sessions: Sequence[date], test_sessions: Sequence[date]) -> bool:
    return set(train_sessions).isdisjoint(set(test_sessions))


def embargo_respected(fold: Fold, calendar: TradingCalendar) -> bool:
    gap = calendar.session_distance(fold.train_end, fold.test_start)
    return gap is not None and gap == fold.embargo_sessions + 1


def planted_future_bars_is_caught() -> bool:
    """Runner smoke: the suite distinguishes a future-bar leak from a PIT prefix."""
    series = [1.0, 2.0, 3.0, 99.0]
    clean = pit_prefix(series, 2)
    leak = planted_include_future_bars(series, 2)
    return 99.0 not in clean and 99.0 in leak
