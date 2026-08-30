"""Universe tradeability gates — adopted by copy from
``traderlog/adopted/activity.py`` (which ported
``manas_os/engine/universe_filter.py``) on 2026-08-29, per the house
adopt-by-copy rule and D4/D8. No ``import traderlog``.

Provenance and drift:
* Gate semantics (price floor, avg-turnover floor, ETF keyword heuristic,
  circuit-lock heuristic, mcap-skip-with-reason) are a VERBATIM port of the
  adopted original's ``evaluate_symbol`` — same defaults (price ₹30,
  turnover ₹2 crore/day over trailing 20 sessions, mcap check skipped and
  surfaced), same "a skipped check is never a silent pass" stance.
* Drift: bars are our ``VersionedDailyBar`` objects (attribute access)
  rather than dicts; the swing-edges spec's tighter floors (₹8 crore ADV)
  are caller policy — pass them as parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from unidesk.contracts.base import ContractError, require_str

MIN_PRICE = 30.0
MIN_AVG_TURNOVER_CR = 2.0
EXCLUDE_ETF = True

# Verbatim port of the adopted ETF keyword heuristic (see provenance above),
# MINUS "ABSL" -- see _KNOWN_NON_ETF_OVERRIDES below.
_ETF_KEYWORDS = {
    "ETF", "BEES", "NIFTYBEES", "GOLDBEES", "LIQUIDBEES", "LIQUID", "SETFNIF",
    "SETF", "IETF", "NEXT50", "NIFTY", "SENSEX", "MOM50", "MOM100", "MOM30",
    "TOP100", "TOP50", "GSEC", "LOWVOL", "ALPHAETF", "ALPHA50", "FANG",
    "HDFCSML", "HDFCMID", "MID150", "SML250", "MIDCAPETF",
    "SMALLCAP250", "BANKADD", "HDFCNIF", "MOVALUE", "MOQUALITY", "MOMENTUM",
    "QUAL30", "VAL30",
}

# KNOWN FALSE POSITIVES, confirmed against the real archive
# (data/bhavcopy/sec_bhavdata_full_31122024.csv, 2752 unique symbols) on
# 2026-08-30, universe-gates wiring wave:
#   * ABSLAMC -- Aditya Birla Sun Life AMC, a real EQ-series stock (close
#     ~Rs 836, turnover ~Rs 32cr/day that session). The bare "ABSL"
#     keyword matched it as a substring (issuer-prefix false positive: ABSL
#     is also the prefix of several real ABSL-house ETFs). "ABSL" has been
#     REMOVED from _ETF_KEYWORDS above rather than papered over here, since
#     the genuine ABSL ETFs in the archive (ABSLBANETF, ABSLLIQUID) are
#     still caught by the "ETF"/"LIQUID" keywords on their own merits.
#   * JETFREIGHT -- a real logistics stock, caught by the bare "ETF"
#     keyword purely because "ETF" is a substring of "JETFREIGHT" (J-ETF-
#     REIGHT). This is the general failure mode of substring matching:
#     ANY keyword can collide with an unrelated real symbol that merely
#     contains those letters in sequence. This override list is a targeted
#     patch for the two cases actually observed in the real archive scan
#     that backs this module's F5 fix -- it is NOT a proof that no other
#     substring collision exists among the ~2750 real symbols. A symbol
#     newly flagged as a "probable ETF" should still be spot-checked before
#     being trusted, exactly as this file's own docstring already says for
#     every gate: "a cheap pre-filter, never ground truth."
_KNOWN_NON_ETF_OVERRIDES = {"ABSLAMC", "JETFREIGHT"}


def is_probable_etf(symbol: str) -> bool:
    """Keyword heuristic on the symbol — a cheap pre-filter, never ground
    truth. Substring matching over ``_ETF_KEYWORDS`` will still collide with
    real symbols that happen to contain those letters in sequence (see
    _KNOWN_NON_ETF_OVERRIDES above for two confirmed real-archive cases);
    this is a known, disclosed limitation, not a claim of completeness."""
    s = symbol.upper()
    if s in _KNOWN_NON_ETF_OVERRIDES:
        return False
    return any(k in s for k in _ETF_KEYWORDS)


def circuit_locked(bars) -> bool:
    """Suspected circuit-lock / illiquid freeze, inferred from OHLCV shape:
    latest bar has high == low, OR >=3 of last 5 have high == low, OR latest
    volume is 0/None. Not authoritative (no surveillance feed)."""
    if not bars:
        return False
    latest = bars[-1].bar
    if latest.volume is None or latest.volume == 0:
        return True
    tail = [b.bar for b in bars[-5:]]
    if sum(1 for b in tail if b.high == b.low) >= 3:
        return True
    return latest.high == latest.low


@dataclass(frozen=True)
class GateVerdict:
    symbol: str
    tradeable: bool
    reasons_failed: tuple
    metrics: dict


def evaluate_gates(
    symbol: str,
    bars,
    *,
    min_price: float = MIN_PRICE,
    min_avg_turnover_cr: float = MIN_AVG_TURNOVER_CR,
    exclude_etf: bool = EXCLUDE_ETF,
) -> GateVerdict:
    """Tradeability verdict for one symbol from its trailing bars (pure).

    ``bars``: ascending VersionedDailyBar list, trailing window INCLUDING the
    judged date (original ``bars[-20:]`` convention). Market cap cannot be
    checked (no source) — surfaced in metrics, never silently passed."""
    symbol = require_str(symbol, "symbol")
    reasons: list[str] = []
    metrics: dict = {}

    if not bars:
        metrics.update({"price": None, "avg_turnover_cr": None,
                        "etf": is_probable_etf(symbol), "circuit_locked": False,
                        "mcap_check": "skipped: mcap unavailable"})
        return GateVerdict(symbol, False, ("no price history available",), metrics)

    latest = bars[-1].bar
    price = latest.close
    metrics["price"] = price

    window = [b.bar for b in bars[-20:]]
    turnovers = [b.close * b.volume / 1e7 for b in window
                 if b.close is not None and b.volume is not None]
    avg_turnover_cr = (sum(turnovers) / len(turnovers)) if turnovers else None
    metrics["avg_turnover_cr"] = avg_turnover_cr
    metrics["etf"] = is_probable_etf(symbol)
    locked = circuit_locked(bars)
    metrics["circuit_locked"] = locked
    metrics["mcap_check"] = "skipped: mcap unavailable"

    if price is None:
        reasons.append("price unavailable")
    elif price < min_price:
        reasons.append(f"price ₹{price:.2f} < ₹{min_price:.2f} floor")
    if avg_turnover_cr is None:
        reasons.append("turnover unavailable")
    elif avg_turnover_cr < min_avg_turnover_cr:
        reasons.append(f"avg turnover ₹{avg_turnover_cr:.2f}cr < ₹{min_avg_turnover_cr:.2f}cr floor")
    if exclude_etf and is_probable_etf(symbol):
        reasons.append("probable ETF (keyword heuristic)")
    if locked:
        reasons.append("circuit-locked / illiquid freeze suspected")

    return GateVerdict(symbol, not reasons, tuple(reasons), metrics)
