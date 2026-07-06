"""risk/plan.py — the SINGLE WRITER of stop / size / R:R (Manas 2.0, plan T1.2).

Every number a card, alert, or sizer shows comes from here. A trade whose risk
math doesn't clear the bars is REFUSED (named reasons), never displayed as a
plan. All thresholds are the plan's LOCKED table — do not tune here without a
LEARNINGS.md entry.

Two risk profiles (aggression lives in SIZE ONLY — stop caps, R:R floor and
gates are identical): AGGRESSIVE (default; small account, grow fast) and
STANDARD. Regime bands index into the active profile.
"""
from __future__ import annotations

import math
from typing import Any

from manas_os import config

# --- LOCKED thresholds (plan: "LOCKED design decisions") ---------------------
STOP_CAP_BY_REGIME = {"RISK_ON": 6.0, "SELECTIVE": 5.0, "DEFENSIVE": 4.0, "NO_TRADE": 0.0}
STOP_CAP_EXCEPTIONAL = 7.5   # EP / IPO-base only
STOP_CAP_ABSOLUTE = 8.0      # never exceeded, any setup
STOP_FLOOR = 1.0             # noise floor
RR_FLOOR = 1.5

PROFILES: dict[str, dict[str, Any]] = {
    # risk_per_trade: {regime: (base_pct, hard_max_pct)}; open_risk_cap %; max open positions
    "aggressive": {
        "risk_per_trade": {"RISK_ON": (0.75, 1.00), "SELECTIVE": (0.50, 0.75),
                           "DEFENSIVE": (0.30, 0.40), "NO_TRADE": (0.0, 0.0)},
        "open_risk_cap": {"RISK_ON": 3.0, "SELECTIVE": 2.0, "DEFENSIVE": 1.0, "NO_TRADE": 0.0},
        "max_open_positions": 5,
    },
    "standard": {
        "risk_per_trade": {"RISK_ON": (0.50, 0.75), "SELECTIVE": (0.35, 0.50),
                           "DEFENSIVE": (0.25, 0.35), "NO_TRADE": (0.0, 0.0)},
        "open_risk_cap": {"RISK_ON": 2.0, "SELECTIVE": 1.25, "DEFENSIVE": 0.75, "NO_TRADE": 0.0},
        "max_open_positions": 6,
    },
}
MAX_NEW_POSITIONS_PER_DAY = {"RISK_ON": 2, "SELECTIVE": 1, "DEFENSIVE": 1, "NO_TRADE": 0}
MAX_POSITIONS_PER_SECTOR = 2          # 3rd correlated name => half size
EXCEPTIONAL_FAMILIES = {"ep", "ipo_base"}


def active_profile() -> str:
    p = str(config.get("risk.profile", "aggressive")).lower()
    return p if p in PROFILES else "aggressive"


def capital() -> float:
    return float(config.get("risk.capital", 1_000_000.0))


# --- stops --------------------------------------------------------------------

def _atr(bars: list[dict], n: int = 20) -> float | None:
    """Wilder-free simple ATR over the last n bars (enough for a stop buffer)."""
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(len(bars) - n, len(bars)):
        h, l = bars[i].get("high"), bars[i].get("low")
        pc = bars[i - 1].get("close")
        if None in (h, l, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs) if trs else None


def candidate_stops(bars: list[dict], setup_family: str, entry: float) -> list[dict[str, Any]]:
    """Three candidate stops, each tied to a REAL level (plan T1.2).

    Returns [{method, stop, stop_pct}] for stops strictly below entry. The
    caller (or choose_stop) picks the tightest structurally-valid one.
    """
    out: list[dict[str, Any]] = []
    if not bars or entry <= 0:
        return out
    last = bars[-1]

    def add(method: str, stop: float | None) -> None:
        if stop is not None and 0 < stop < entry:
            out.append({"method": method, "stop": round(stop, 2),
                        "stop_pct": round((entry - stop) / entry * 100.0, 2)})

    # 1) trigger-bar / undercut low — tightest structural level
    add("trigger-bar low", last.get("low"))
    # 2) ATR hybrid — for noisy names where the bar low gets hunted
    atr = _atr(bars)
    if atr:
        add("entry - 1.2*ATR20", entry - 1.2 * atr)
    # 3) structure — recent base low (10-bar) with a small ATR buffer
    lows = [b.get("low") for b in bars[-10:] if b.get("low") is not None]
    if lows:
        buffer = 0.25 * atr if atr else 0.0
        add("base low (10-bar) - buffer", min(lows) - buffer)
    return out


def choose_stop(bars: list[dict], setup_family: str, entry: float) -> dict[str, Any] | None:
    """Tightest candidate that clears the noise floor. None = no valid stop."""
    valid = [c for c in candidate_stops(bars, setup_family, entry) if c["stop_pct"] >= STOP_FLOOR]
    if not valid:
        return None
    return max(valid, key=lambda c: c["stop"])  # highest stop price = tightest


# --- structural target (the symmetric counterpart to choose_stop) --------------
# Until 2026-07-06 the measured move was `entry + 2*risk`, which made every
# candidate's R:R uniformly 2.0 and so the R:R>=1.5 floor in validate() never
# bit (LEARNINGS.md, T1.6/T2.2). A real measured move is a RESISTANCE level
# the trade is racing toward — the prior swing high / base ceiling — not a
# constant multiple of risk. This helper is the single writer of that number
# (anti-mashup: one writer per metric), mirroring choose_stop's shape.
def structural_target(bars: list[dict], entry: float, stop: float,
                      setup_family: str = "") -> dict[str, Any] | None:
    """The closest REAL overhead resistance, used as the measured move.

    Walks the candidate hierarchy in priority order and picks the tightest
    level strictly above entry. Returns {target, method} or None if no
    overhead resistance is visible in the window (in which case the caller
    falls back to a volatility projection and flags it as synthetic).

    Hierarchy (a real trader's mental model, most-to-least structural):
      1. prior swing high in the trailing 60-90 sessions (the level that
         framed the current base — the textbook measured-move target).
      2. the high of the base itself (trailing 20-session high excluding
         the trigger bar) when the setup is a base breakout.
      3. entry + 1 ATR — a volatility projection, NOT structural; returned
         only when nothing real is visible, and flagged synthetic=True so
         the UI can label it and the R:R floor is still enforced honestly.
    EP/IPO names (setup_family in EXCEPTIONAL_FAMILIES) are allowed to use
    the volatility projection more readily — these are catalyst-driven and
    the "prior swing high" is often the gap itself.
    """
    if not bars or entry <= 0 or stop >= entry:
        return None
    risk = entry - stop
    atr = _atr(bars)
    exceptional = (setup_family or "").lower() in EXCEPTIONAL_FAMILIES

    def _above(level: float | None) -> float | None:
        return level if (level is not None and level > entry) else None

    # 1) prior swing high — the most recent bar whose high is the local max
    #    of a +-4 window, scanned over the trailing 90 sessions (excluding
    #    the last 5 so we don't pick up the trigger leg itself).
    swing = None
    window = bars[-95:-5] if len(bars) > 10 else bars[:-1]
    for i in range(4, len(window) - 4):
        h = window[i].get("high")
        if h is None:
            continue
        nbr = [window[j].get("high") for j in (i - 4, i - 3, i - 2, i - 1,
                                               i + 1, i + 2, i + 3, i + 4)]
        if all(n is not None and h >= n for n in nbr):
            swing = h if swing is None else max(swing, h)  # nearest/tighest = highest recent
    target = _above(swing)
    if target is not None:
        return {"target": round(target, 2), "method": "prior swing high", "synthetic": False}

    # 2) base ceiling — trailing 20-bar high excluding the trigger bar
    base_highs = [b.get("high") for b in bars[-21:-1] if b.get("high") is not None]
    base_ceiling = max(base_highs) if base_highs else None
    target = _above(base_ceiling)
    if target is not None:
        return {"target": round(target, 2), "method": "base ceiling (20-bar)", "synthetic": False}

    # 3) volatility projection — last resort, flagged synthetic. EP/IPO accept
    #    this more readily (catalyst names often have no overhead resistance
    #    above the gap); for everything else require at least 1.5x risk so we
    #    don't manufacture a passing R:R from a flat name.
    if atr and (exceptional or atr >= 1.5 * risk):
        projected = entry + atr
        return {"target": round(projected, 2), "method": "entry + 1 ATR (volatility projection)",
                "synthetic": True}
    return None


# --- the validator (refusal is the product) ------------------------------------

def validate(
    entry: float,
    stop: float,
    measured_move: float | None,
    regime: str,
    setup_family: str = "",
    open_positions: list[dict] | None = None,   # [{sector, risk_pct, opened_today: bool}]
    sector: str | None = None,
    circuit_band_pct: float | None = None,
    profile: str | None = None,
    account_capital: float | None = None,
) -> dict[str, Any]:
    """Full risk validation. Fails => the trade is REFUSED (never displayed as a plan).

    Returns {pass, reasons[], qty, rupee_risk, rr, stop_pct, risk_pct_used,
             stop_cap_applied, half_size_applied}.
    """
    reasons: list[str] = []
    prof = PROFILES[profile or active_profile()]
    cap_ = account_capital if account_capital is not None else capital()
    open_positions = open_positions or []
    regime = (regime or "").upper()
    if regime not in STOP_CAP_BY_REGIME:
        regime = "SELECTIVE"  # conservative default, never permissive

    result: dict[str, Any] = {"pass": False, "reasons": reasons, "qty": 0, "rupee_risk": 0.0,
                              "rr": None, "stop_pct": None, "risk_pct_used": None,
                              "stop_cap_applied": None, "half_size_applied": False}

    if entry <= 0 or stop <= 0 or stop >= entry:
        reasons.append("invalid entry/stop geometry")
        return result

    stop_pct = (entry - stop) / entry * 100.0
    result["stop_pct"] = round(stop_pct, 2)

    # -- stop caps (LOCKED) --
    cap = STOP_CAP_BY_REGIME[regime]
    if setup_family in EXCEPTIONAL_FAMILIES:
        cap = max(cap, STOP_CAP_EXCEPTIONAL)
    cap = min(cap, STOP_CAP_ABSOLUTE)
    result["stop_cap_applied"] = cap
    if stop_pct < STOP_FLOOR:
        reasons.append(f"stop {stop_pct:.1f}% below {STOP_FLOOR:.0f}% noise floor")
    if stop_pct > cap:
        reasons.append(f"stop {stop_pct:.1f}% exceeds {cap:.1f}% cap ({regime}"
                       f"{', exceptional' if setup_family in EXCEPTIONAL_FAMILIES else ''})")

    # -- circuit-band feasibility (India-specific; plan T2.1 consumer) --
    if circuit_band_pct is not None and stop_pct < circuit_band_pct:
        reasons.append(f"stop {stop_pct:.1f}% inside the {circuit_band_pct:.0f}% circuit band — "
                       f"effective stop is the band; refuse or replan")

    # -- R:R floor --
    if measured_move is None:
        reasons.append("no measured move — R:R unknowable")
    else:
        rr = (measured_move - entry) / (entry - stop)
        result["rr"] = round(rr, 2)
        if rr < RR_FLOOR:
            reasons.append(f"R:R {rr:.2f} below {RR_FLOOR} floor")

    # -- regime allows any trade at all --
    base_risk, hard_max = prof["risk_per_trade"][regime]
    if base_risk <= 0:
        reasons.append(f"{regime}: no new positions by design")

    # -- portfolio heat --
    open_risk = sum(p.get("risk_pct", 0.0) for p in open_positions)
    heat_cap = prof["open_risk_cap"][regime]
    if base_risk > 0 and open_risk + base_risk > heat_cap:
        reasons.append(f"open risk {open_risk:.2f}% + {base_risk:.2f}% would breach "
                       f"{heat_cap:.2f}% cap")
    if len(open_positions) >= prof["max_open_positions"]:
        reasons.append(f"already at max {prof['max_open_positions']} open positions")
    opened_today = sum(1 for p in open_positions if p.get("opened_today"))
    if opened_today >= MAX_NEW_POSITIONS_PER_DAY[regime]:
        reasons.append(f"already {opened_today} new position(s) today "
                       f"(max {MAX_NEW_POSITIONS_PER_DAY[regime]} in {regime})")

    # -- sector concentration --
    risk_pct = base_risk
    if sector:
        same = sum(1 for p in open_positions if p.get("sector") == sector)
        if same >= MAX_POSITIONS_PER_SECTOR:
            reasons.append(f"{same} open positions already in {sector} "
                           f"(max {MAX_POSITIONS_PER_SECTOR}/sector)")
        elif same == MAX_POSITIONS_PER_SECTOR - 1:
            risk_pct = base_risk / 2.0        # 3rd correlated name = half size
            result["half_size_applied"] = True

    if reasons:
        return result

    rupee_risk = cap_ * risk_pct / 100.0
    result.update({
        "pass": True,
        "risk_pct_used": round(risk_pct, 3),
        "rupee_risk": round(rupee_risk, 2),
        "qty": int(math.floor(rupee_risk / (entry - stop))),
    })
    return result
