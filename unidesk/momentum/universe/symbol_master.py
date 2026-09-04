"""Normalized, point-in-time symbol classification.

The normalizer is intentionally provider-neutral: it does not accept exchange
prefixes, provider identifiers, or wire-format suffixes.  A symbol is the
uppercase, trimmed local identifier made of ASCII letters, digits, ``.``,
``-``, and ``_``.  It must start with a letter or digit and be at most 32
characters long.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, Optional

from unidesk.contracts.base import ContractError, ensure_utc, require_str
from unidesk.contracts.market import SymbolMaster

# `&` amended 2026-08-29 (unidesk DECISIONS context: DATA_POLICY amendment):
# M&M and similar real, liquid NSE tickers were rejected by the original
# charset. Skip-and-count remains the safety net for genuinely malformed ids.
_SYMBOL_RE = re.compile(r"[A-Z0-9][A-Z0-9._&-]{0,31}\Z")


def normalize_symbol(value: str) -> str:
    """Return the canonical local symbol, rejecting ambiguous wire vocabulary."""
    raw = require_str(value, "symbol")
    normalized = raw.strip().upper()
    if not _SYMBOL_RE.fullmatch(normalized):
        raise ContractError(
            "symbol must be 1..32 ASCII [A-Z0-9._&-] characters, start with "
            "a letter or digit, and contain no provider/exchange prefix"
        )
    return normalized


@dataclass(frozen=True)
class SymbolClassification:
    """One immutable classification version over a half-open effective interval.

    ``available_at`` is separate from the effective interval so a later
    correction cannot appear in an earlier point-in-time query.
    """

    master: SymbolMaster
    effective_from: datetime
    effective_to: Optional[datetime]
    available_at: datetime
    version: str
    # None means the surveillance feed did not provide a state.  An empty
    # tuple is distinct: it means the feed explicitly reported no flags.
    surveillance_state: Optional[tuple[str, ...]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_from", ensure_utc(self.effective_from, "effective_from"))
        if self.effective_to is not None:
            object.__setattr__(self, "effective_to", ensure_utc(self.effective_to, "effective_to"))
            if self.effective_to <= self.effective_from:
                raise ContractError("effective_to must be after effective_from")
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        object.__setattr__(self, "version", require_str(self.version, "version"))
        if self.surveillance_state is not None:
            if isinstance(self.surveillance_state, str) or not isinstance(self.surveillance_state, tuple):
                raise ContractError("surveillance_state must be a tuple of strings or None")
            normalized_flags = tuple(
                require_str(flag, "surveillance_state[]") for flag in self.surveillance_state
            )
            object.__setattr__(self, "surveillance_state", normalized_flags)
        normalized = normalize_symbol(self.master.symbol)
        if normalized != self.master.symbol:
            raise ContractError("SymbolMaster.symbol must already be normalized")

    @property
    def symbol(self) -> str:
        return self.master.symbol

    def applies_at(self, as_of: datetime) -> bool:
        instant = ensure_utc(as_of, "as_of")
        return self.effective_from <= instant and (
            self.effective_to is None or instant < self.effective_to
        )


def resolve_classification(
    classifications: Iterable[SymbolClassification], symbol: str, as_of: datetime
) -> Optional[SymbolClassification]:
    """Return the latest available version effective at ``as_of``.

    Ties are prohibited on insert by the store; this pure helper also fails
    closed if callers hand it an ambiguous collection.
    """
    normalized = normalize_symbol(symbol)
    instant = ensure_utc(as_of, "as_of")
    candidates = [
        item
        for item in classifications
        if item.symbol == normalized and item.applies_at(instant) and item.available_at <= instant
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.available_at, item.version), reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and candidates[1].available_at == best.available_at:
        raise ContractError("ambiguous classification versions have equal available_at")
    return best
