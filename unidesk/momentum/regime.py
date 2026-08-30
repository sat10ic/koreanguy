"""R0 — market regime classifier (build manual P1.10-adjacent; swing-edges
spec §2, adopted D11).

Deterministic, breadth-driven, hysteresis-protected:

    BULL   pct_above_50 >= 0.60 and breadth rising
    BEAR   pct_above_50 <= 0.40 and breadth falling
    CHOP   otherwise

The spec's full rule also uses the Midcap-150 index vs its own SMA50.
When that boolean is supplied, ``source`` becomes
``breadth_and_midcap150_sma50`` and a BULL/BEAR call that disagrees with
the Midcap 150 side is forced to CHOP. When it is None the classifier
stays ``breadth_only`` and says so on every row.

Hysteresis: a new label is emitted only after ``hysteresis_days``
consecutive sessions in that state (default 3, spec §2.2) — no flicker.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from unidesk.contracts.base import ContractError


class Regime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    CHOP = "CHOP"


@dataclass(frozen=True)
class RegimeRow:
    session: date
    regime: Regime
    breadth: float            # fraction of the universe above its EMA/SMA-50
    source: str               # "breadth_only" until the index series lands
    hysteresis_pending: int   # consecutive sessions toward a flip, so far


class RegimeClassifier:
    def __init__(self, *, bull_breadth: float = 0.60, bear_breadth: float = 0.40,
                 hysteresis_days: int = 3, source: str = "breadth_only") -> None:
        if not (0 < bear_breadth < bull_breadth < 1):
            raise ContractError("require 0 < bear_breadth < bull_breadth < 1")
        if hysteresis_days < 1:
            raise ContractError("hysteresis_days must be >= 1")
        self.bull_breadth = bull_breadth
        self.bear_breadth = bear_breadth
        self.hysteresis_days = hysteresis_days
        self.source = source
        self.current: Regime = Regime.CHOP
        self._pending: Regime | None = None
        self._pending_days = 0
        self._started = False

    def _raw_state(self, breadth: float, midcap_above_sma50: bool | None) -> Regime:
        if breadth >= self.bull_breadth:
            raw = Regime.BULL
        elif breadth <= self.bear_breadth:
            raw = Regime.BEAR
        else:
            raw = Regime.CHOP
        if midcap_above_sma50 is None:
            return raw
        if raw is Regime.BULL and not midcap_above_sma50:
            return Regime.CHOP
        if raw is Regime.BEAR and midcap_above_sma50:
            return Regime.CHOP
        return raw

    def update(self, session: date, breadth: float,
               midcap_above_sma50: bool | None = None) -> RegimeRow:
        if not 0.0 <= breadth <= 1.0:
            raise ContractError(f"breadth must be a 0..1 fraction, got {breadth}")
        source = (
            "breadth_and_midcap150_sma50"
            if midcap_above_sma50 is not None
            else "breadth_only"
        )
        if not self._started:
            self._started = True
            self.current = self._raw_state(breadth, midcap_above_sma50)
            self.source = source
            return RegimeRow(session, self.current, breadth, self.source, 0)

        raw = self._raw_state(breadth, midcap_above_sma50)
        if raw == self.current:
            self._pending = None
            self._pending_days = 0
        else:
            if self._pending == raw:
                self._pending_days += 1
            else:
                self._pending = raw
                self._pending_days = 1
            if self._pending_days >= self.hysteresis_days:
                self.current = raw
                self._pending = None
                self._pending_days = 0
        self.source = source
        return RegimeRow(session, self.current, breadth, self.source, self._pending_days or 0)
