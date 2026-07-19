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
    "learning": {
        "risk_per_trade": {"RISK_ON": (0.20, 0.20), "SELECTIVE": (0.15, 0.15),
                           "DEFENSIVE": (0.10, 0.10), "NO_TRADE": (0.0, 0.0)},
        "open_risk_cap": {"RISK_ON": 1.0, "SELECTIVE": 0.50, "DEFENSIVE": 0.25, "NO_TRADE": 0.0},
        "max_open_positions": 4,
    },
}
MAX_NEW_POSITIONS_PER_DAY = {"RISK_ON": 2, "SELECTIVE": 1, "DEFENSIVE": 1, "NO_TRADE": 0}
MAX_POSITIONS_PER_SECTOR = 2          # 3rd correlated name => half size
EXCEPTIONAL_FAMILIES = {"ep", "ipo_base", "d2_episodic", "strong_start_ready"}
# d2_episodic + strong_start_ready added 2026-07-19 (user authorization): a D1
# burst's day-low stop is naturally wider than a base pivot's; the SELECTIVE
# 5% cap refused HIRECT (5.8%) and INOXINDIA (6.2%) on their entry days while
# the corpus's own EP exception (7.5%) covers exactly this class. The 8%
# absolute ceiling is unchanged.

TRAIL_FAMILIES = {"momentum", "catalyst", "reversal", "busted_reversal"}
TRAIL_CONTINUATION_PCT = 0.15

# --- notional band (external UX audit "Confetti sizing" FAIL) ----------------
# Assumption: Rs 10,000-20,000 notional per trade is the user's own
# profitable size bucket per TRADE_AUTOPSY/BROKER_AUDIT — tell me if wrong.
# This is a CONSERVATIVE, size-UP-ONLY informational layer: it can nudge qty
# up toward the Rs 10k floor when the existing risk-derived qty leaves room
# within the trader's own per-trade risk band and open-risk cap, but it NEVER
# trims qty down, NEVER exceeds an existing cap, and NEVER creates a refusal
# by itself (validate()'s existing risk/stop/heat gates are untouched).
TARGET_NOTIONAL_MIN = 10000.0   # Rs; Assumption — user's profitable size floor
TARGET_NOTIONAL_MAX = 20000.0   # Rs; Assumption — informational ceiling only, no trim this wave

def get_trader_profile(conn=None) -> dict[str, Any]:
    from manas_os import db
    owns_conn = conn is None
    if owns_conn:
        conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM trader_profile WHERE id = 1").fetchone()
        if not row:
            return {"account_capital": 0.0, "experience_mode": "LEARNING", "profile_confirmed_at": None, "monthly_risk_budget_pct": 0.0, "monthly_risk_used_pct": 0.0, "drawdown_from_month_start_pct": 0.0}
        return dict(row)
    finally:
        if owns_conn:
            conn.close()

def active_profile(conn=None) -> str:
    record = get_trader_profile(conn) if conn is not None else get_trader_profile()
    p = str(record.get("experience_mode", "LEARNING")).lower()
    return p if p in PROFILES else "learning"

def capital(conn=None) -> float:
    record = get_trader_profile(conn) if conn is not None else get_trader_profile()
    saved = float(record.get("account_capital", 0.0) or 0.0)
    return saved if saved > 0 else float(config.get("risk.capital", 1_000_000.0))


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
      4. trail continuation (+15%, TRAIL_CONTINUATION_PCT) — momentum /
         catalyst / reversal / busted_reversal ONLY (TRAIL_FAMILIES). These
         setups have no fixed target in the corpus at all (trail 10/21EMA
         and ride); returned only when tiers 1-3 found nothing, so R:R is
         COMPUTABLE instead of refusing with "no measured move" for a
         trade that is perfectly plannable, just open-ended.
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

    # 1) prior swing high — the local max of a +-4 window, scanned over the
    #    trailing 90 sessions (excluding the last 5 so we don't pick up the
    #    trigger leg itself). Among all confirmed swing highs ABOVE entry, the
    #    structural target is the NEAREST one (lowest qualifying high) — the
    #    first real resistance the trade would meet, not the most distant one.
    swing = None
    window = bars[-95:-5] if len(bars) > 10 else bars[:-1]
    for i in range(4, len(window) - 4):
        h = window[i].get("high")
        if h is None:
            continue
        nbr = [window[j].get("high") for j in (i - 4, i - 3, i - 2, i - 1,
                                               i + 1, i + 2, i + 3, i + 4)]
        if all(n is not None and h > n for n in nbr):
            candidate = _above(h)
            if candidate is not None and (swing is None or candidate < swing):
                swing = candidate
    if swing is not None:
        return {"target": round(swing, 2), "method": "prior swing high", "synthetic": False}

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

    # 4) trail continuation projection — momentum/catalyst/reversal ONLY
    #    (WAVE_L: "no measured move -> R:R unknowable" refusal-gap fix).
    #    Corpus doctrine for these families is explicit: there IS no fixed
    #    target — you trail 10/21 EMA and ride ("Half-sell at 15-20% gain,
    #    trail the rest, no predetermined target" — ARORA_SHARDS_NUANCES.md
    #    "Arora sell-into-strength" / INDIA_PLAYBOOK.md "Half-Sell Rule =
    #    At 15-20% Profit, Sell 50%, Trail Rest"). That refusal reason was
    #    conflating "no fixed target" with "R:R unknowable" — the trade IS
    #    plannable, it's just open-ended. TRAIL_CONTINUATION_PCT is the LOW
    #    end of that corpus range (15%, not 20%) and is ONE FIXED NUMBER
    #    applied identically to every name in these families regardless of
    #    stop width — it is NOT tuned per name to clear RR_FLOOR, so a
    #    wide-stop name still produces a low R:R and is still refused by
    #    the (unchanged) RR_FLOOR check in validate(). base/pattern setups
    #    are excluded here and keep only tiers 1-3 above — a base/pattern
    #    name with no overhead resistance and no ATR-qualifying projection
    #    is still refused as "no measured move", unchanged.
    if (setup_family or "").lower() in TRAIL_FAMILIES:
        projected = entry * (1.0 + TRAIL_CONTINUATION_PCT)
        return {
            "target": round(projected, 2),
            "method": f"trailed, projected +{TRAIL_CONTINUATION_PCT * 100:.0f}% "
                      "(half-sell checkpoint — ARORA_SHARDS_NUANCES/INDIA_PLAYBOOK: "
                      "no predetermined target, trail 10/21EMA and ride)",
            "synthetic": True,
        }
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
    conn=None,
) -> dict[str, Any]:
    """Full risk validation. Fails => the trade is REFUSED (never displayed as a plan).

    Returns {pass, reasons[], qty, rupee_risk, rr, stop_pct, risk_pct_used,
             stop_cap_applied, half_size_applied}.
    """
    reasons: list[str] = []
    explicit_profile = profile is not None
    explicit_capital = account_capital is not None
    if explicit_profile and explicit_capital:
        prof_rec = {
            "profile_confirmed_at": "explicit",
            "experience_mode": profile,
            "account_capital": account_capital,
        }
    else:
        # Keep compatibility with zero-argument profile providers while reusing
        # an explicit request/test connection whenever the caller has one.
        prof_rec = get_trader_profile(conn) if conn is not None else get_trader_profile()
    if profile is None:
        profile = str(prof_rec.get("experience_mode", "LEARNING")).lower()
        if profile not in PROFILES:
            profile = "learning"
    prof = PROFILES[profile]

    cap_ = account_capital if account_capital is not None else float(prof_rec.get("account_capital", 0.0) or 0.0)
    profile_pending = not explicit_capital and not prof_rec.get("profile_confirmed_at")
    open_positions = open_positions or []
    regime = (regime or "").upper()
    if regime not in STOP_CAP_BY_REGIME:
        regime = "SELECTIVE"  # conservative default, never permissive

    result: dict[str, Any] = {"pass": False, "reasons": reasons, "qty": 0, "rupee_risk": 0.0,
                              "rr": None, "stop_pct": None, "risk_pct_used": None,
                              "stop_cap_applied": None, "half_size_applied": False,
                              "notional": None, "notional_band": None, "band_note": None,
                              "provenance": None}

    if cap_ <= 0.0 or profile_pending:
        reasons.append("trader profile incomplete")
        return result

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
    qty = int(math.floor(rupee_risk / (entry - stop)))

    # -- notional band (size-up-only, see TARGET_NOTIONAL_MIN/MAX above) --
    notional = round(qty * entry, 2)
    notional_band = "in"
    band_note = None
    if notional < TARGET_NOTIONAL_MIN:
        # Assumption: round UP (ceil) so the sized-up qty never undershoots
        # the Rs 10k floor by a fraction of a share's worth of notional.
        qty_up = math.ceil(TARGET_NOTIONAL_MIN / entry)
        sized_up = False
        if qty_up > qty:
            rupee_risk_up = qty_up * (entry - stop)
            risk_pct_up = rupee_risk_up / cap_ * 100.0
            open_risk_after_up = open_risk + risk_pct_up
            # Adopt ONLY if the bigger size still clears the profile's own
            # per-trade risk ceiling (hard_max) AND the portfolio open-risk
            # cap (heat_cap) — stop caps are untouched (they depend on
            # stop_pct, not qty, and were already enforced above).
            if risk_pct_up <= hard_max and open_risk_after_up <= heat_cap:
                qty = qty_up
                rupee_risk = rupee_risk_up
                risk_pct = risk_pct_up
                notional = round(qty * entry, 2)
                sized_up = True
        if sized_up:
            notional_band = "in"
            band_note = (
                f"sized up to {qty} sh (Rs {notional:,.0f} notional) to clear the Rs "
                f"{TARGET_NOTIONAL_MIN:,.0f} compounding floor; risk {risk_pct:.2f}% stays "
                f"within the {hard_max:.2f}% per-trade band"
            )
        else:
            notional_band = "below"
            band_note = (
                f"position Rs {notional:,.0f} below the Rs 10k compounding band - stop too "
                "wide to size up within your risk budget; consider skipping"
            )
            # Informational only — appended AFTER the pass/refuse gate above,
            # so this can never turn a passing trade into a refusal.
            reasons.append(band_note)
    elif notional > TARGET_NOTIONAL_MAX:
        notional_band = "above"
        band_note = (
            f"position Rs {notional:,.0f} above the Rs {TARGET_NOTIONAL_MAX:,.0f} target "
            "band (informational only — no size change this wave)"
        )

    result.update({
        "pass": True,
        "risk_pct_used": round(risk_pct, 3),
        "rupee_risk": round(rupee_risk, 2),
        "qty": qty,
        "notional": notional,
        "notional_band": notional_band,
        "band_note": band_note,
        "provenance": {
            "capital": cap_,
            "risk_pct": round(risk_pct, 3),
            "rupee_budget": round(rupee_risk, 2),
            "stop_distance": round(entry - stop, 2),
            "final_qty": qty,
            "open_risk_before": round(open_risk, 2),
            "open_risk_after": round(open_risk + risk_pct, 2),
            "profile_pending": profile_pending,
        }
    })
    return result
