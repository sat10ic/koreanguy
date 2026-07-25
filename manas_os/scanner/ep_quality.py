"""EP vs SIP -- burst nature + location doctrine.

Source: design/EP_VS_SIP_SPEC_2026-07-21.md, itself sourced from a
practitioner PDF ("EP & SIP -- A Thin Line Between Them", user-supplied
2026-07-21). The doctrine's core claim: an episodic pivot (EP) is only a
genuine SWING trade when the STOCK'S OWN NATURE holds bursts (its own
burst-day history shows continuation, not fade) AND the LOCATION is right
(fresh base breakout, room above, not already extended, not opening near
resistance). Get either wrong and the doctrine is explicit: burst-and-fade
names are intraday-only (SIP) no matter how good the EP gap looks, and
"price usually cannot break resistance without absorbing supply" makes a
near-resistance entry avoidable outright.

The tool already DETECTS episodic pivots (engine/eod_detectors.earnings_
power, scanner/discovery's D2 path) but never asked whether a given
stock's bursts historically HOLD before handing it a swing plan with a
swing stop -- exactly the silent category error this module exists to
name.

Scope (this lane only): three pure functions -- burst_nature, location_
read, classify -- plus one compute+persist helper for the new ep_quality_
daily table (schema.sql). Nothing here is wired into scan_candidates /
conviction / setup_regime yet; that wiring is a later, separately-scoped
wave (spec section 4).

Reused, not reinvented (all imported READ-ONLY; none of these modules is
edited by this file):
  - manas_os.engine.eod_detectors.ema / rvol20 -- the same EMA21 and
    day-RVOL primitives exit_state/trail_plan/d2_ready already use.
  - manas_os.scanner.discovery_metrics.prev_day_tightness_pctile -- the
    same own-history tightness percentile the Strong-Start-Ready detector
    uses for "extremely tight previous day".
  - manas_os.scanner.candidates._compute_breakout_age -- the same
    pivot-crossover leg-age definition conviction.py's fresh-base-breakout
    tier already reads.
  - manas_os.risk.plan.structural_target -- the same resistance scan
    choose_stop's symmetric counterpart already computes. Only its real
    tiers (1: prior swing high, 2: base ceiling) count as "overhead
    resistance" here; its tier-3 volatility PROJECTION is a synthetic
    number, not a real level the doctrine's "supply absorption" language
    is about, so a synthetic result is treated identically to "no
    resistance visible" (open sky, maximum room) rather than as a level.
"""
from __future__ import annotations

import json
import statistics
from typing import Any

from manas_os.engine import eod_detectors as ed
from manas_os.risk import plan as risk_plan
from manas_os.scanner import discovery_metrics as dm
from manas_os.scanner.candidates import _compute_breakout_age

Bar = dict[str, Any]


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Any, ndigits: int = 4) -> float | None:
    n = _num(value)
    return None if n is None else round(n, ndigits)


# ---------------------------------------------------------------------------
# 1. burst_nature -- does THIS stock's own burst-day history hold or fade?
# ---------------------------------------------------------------------------

# Assumption (spec section 1): "start 8.0 -- slightly below the D2 10% so the
# sample is not starved". Pending calibration against real hold-rate data.
BURST_CHANGE_PCT = 8.0
# Spec section 1's second burst-day test, given directly by the spec (not
# itself flagged Assumption there): "gap >= 5% with day RVOL >= 2".
BURST_GAP_PCT = 5.0
BURST_GAP_RVOL = 2.0

# Assumption (spec section 1): nature thresholds pending calibration.
NATURE_SWING_HOLD_RATE = 0.6
NATURE_FADE_HOLD_RATE = 0.35
NATURE_FADE_FWD5_PCT = -2.0
# Spec section 1's own floor: "n < 4 burst days -> unknown (never guess a
# nature from one event)".
NATURE_MIN_BURST_DAYS = 4


def burst_nature(bars: list[Bar]) -> dict[str, Any]:
    """Find every historical BURST DAY in this symbol's OWN history and
    measure whether ITS OWN bursts historically hold or fade.

    A burst day is a session whose change% >= BURST_CHANGE_PCT, OR whose
    gap% >= BURST_GAP_PCT with day RVOL >= BURST_GAP_RVOL (spec section 1).
    A burst day only counts toward `burst_days` when there is a full
    forward 5-session window to judge it -- a burst too close to the end
    of the supplied history is not guessed at, simply not counted (same
    "never guess" principle as the n<4 unknown floor below).

    "held" = fwd_5 > 0 AND the stock never closed below the burst day's own
    LOW within the next 5 sessions -- a fade that undercuts the burst bar
    is exactly the signature the doctrine names.

    Returns {burst_days, held, hold_rate, median_fwd_5, median_fwd_10,
    nature}. nature is one of "swing" | "mixed" | "fade" | "unknown";
    burst_days < 4 always forces "unknown".
    """
    records: list[dict[str, Any]] = []
    n_bars = len(bars)
    for i in range(1, n_bars):
        bar = bars[i]
        close = _num(bar.get("close"))
        prev_close = _num(bar.get("prev_close"))
        if prev_close is None:
            prev_close = _num(bars[i - 1].get("close"))
        open_ = _num(bar.get("open"))
        low = _num(bar.get("low"))
        if close is None or not prev_close or low is None:
            continue

        change_pct = (close - prev_close) / prev_close * 100.0
        is_burst = change_pct >= BURST_CHANGE_PCT
        if not is_burst and open_ is not None:
            gap_pct = (open_ - prev_close) / prev_close * 100.0
            if gap_pct >= BURST_GAP_PCT:
                day_rvol = ed.rvol20(bars[: i + 1])
                is_burst = day_rvol is not None and day_rvol >= BURST_GAP_RVOL
        if not is_burst:
            continue

        if i + 5 >= n_bars:
            # Not enough forward history left to verify hold/fade -- do not
            # guess; this burst day is simply not counted.
            continue
        fwd5_window = bars[i + 1 : i + 6]
        fwd5_close = _num(fwd5_window[-1].get("close"))
        fwd_5 = (fwd5_close - close) / close * 100.0 if fwd5_close is not None and close else None
        undercut = any(
            fwd_close is not None and fwd_close < low
            for fwd_close in (_num(b.get("close")) for b in fwd5_window)
        )
        held = bool(fwd_5 is not None and fwd_5 > 0 and not undercut)

        fwd_10 = None
        if i + 10 < n_bars:
            fwd10_close = _num(bars[i + 10].get("close"))
            if fwd10_close is not None and close:
                fwd_10 = (fwd10_close - close) / close * 100.0

        records.append({"held": held, "fwd_5": fwd_5, "fwd_10": fwd_10})

    n = len(records)
    held_count = sum(1 for r in records if r["held"])
    hold_rate = (held_count / n) if n else None
    fwd5_vals = [r["fwd_5"] for r in records if r["fwd_5"] is not None]
    fwd10_vals = [r["fwd_10"] for r in records if r["fwd_10"] is not None]
    median_fwd_5 = statistics.median(fwd5_vals) if fwd5_vals else None
    median_fwd_10 = statistics.median(fwd10_vals) if fwd10_vals else None

    if n < NATURE_MIN_BURST_DAYS:
        nature = "unknown"
    elif (
        hold_rate is not None and hold_rate >= NATURE_SWING_HOLD_RATE
        and median_fwd_5 is not None and median_fwd_5 > 0
    ):
        nature = "swing"
    elif (hold_rate is not None and hold_rate <= NATURE_FADE_HOLD_RATE) or (
        median_fwd_5 is not None and median_fwd_5 < NATURE_FADE_FWD5_PCT
    ):
        nature = "fade"
    else:
        nature = "mixed"

    return {
        "burst_days": n,
        "held": held_count,
        "hold_rate": _round(hold_rate),
        "median_fwd_5": _round(median_fwd_5, 2),
        "median_fwd_10": _round(median_fwd_10, 2),
        "nature": nature,
    }


# ---------------------------------------------------------------------------
# 2. location_read -- the doctrine's four location tests
# ---------------------------------------------------------------------------

# LOCKED (not an Assumption): the exact "close > 1.08 * EMA21" extension test
# already used by scanner/footprint.py's own `extended` flag (footprint.py
# `extended = close is not None and ema21 is not None and close > 1.08 *
# ema21`); reused verbatim rather than inventing a second extension number.
EXTENSION_EMA21_MULTIPLE = 1.08

# Bottom quartile is a definition (25th percentile), not a tuned Assumption;
# reuses discovery_metrics.prev_day_tightness_pctile's own-history percentile
# (same convention Strong-Start-Ready's tightness gate uses) rather than a
# fresh tightness metric.
FRESH_BASE_TIGHTNESS_MAX_PCTILE = 25.0

# Spec section 2's own number for "fresh base breakout" (breakout_age <= 3),
# reusing candidates._compute_breakout_age's existing pivot-crossover
# definition rather than a new leg-age metric.
FRESH_BASE_BREAKOUT_AGE_MAX = 3

# Assumption (spec section 2): "no room" when room_pct < 4 -- pending
# calibration.
NO_ROOM_PCT = 4.0
# Assumption (spec section 2): near_resistance / the doctrine's "avoidable"
# location when room_pct < 2.
NEAR_RESISTANCE_PCT = 2.0


def location_read(
    bars: list[Bar],
    pivot: float | None = None,
    entry: float | None = None,
    stop: float | None = None,
    setup_family: str = "",
) -> dict[str, Any]:
    """The doctrine's four location tests (spec section 2). Each test
    returns its boolean AND the number behind it -- never a bare boolean --
    for honest rendering.

    `pivot` is the breakout level (the same input candidates._compute_
    breakout_age already takes) used for the fresh_base_breakout age read.
    `entry`/`stop` feed risk.plan.structural_target's resistance scan
    read-only; when omitted, entry defaults to the latest close and stop to
    a nominal 1% below it. structural_target's real tiers (prior swing high
    / base ceiling -- the only ones this function trusts as "resistance")
    do not depend on the stop's exact value, only its tier-3 synthetic
    volatility projection does, and that tier is deliberately excluded
    below (see module docstring).
    """
    if not bars:
        return {
            "fresh_base_breakout": False, "breakout_age": None, "tightness_pctile": None,
            "extended": False, "close": None, "ema21": None, "extension_ratio": None,
            "room_above": False, "room_pct": None, "resistance": None,
            "resistance_method": None, "near_resistance": False,
        }

    closes = [_num(b.get("close")) for b in bars]
    close = closes[-1]
    ema21_series = ed.ema(closes, 21)
    ema21 = ema21_series[-1] if ema21_series else None

    breakout_age = _compute_breakout_age(bars, pivot)
    tightness_pctile = dm.prev_day_tightness_pctile(bars)
    fresh_base_breakout = bool(
        breakout_age is not None
        and breakout_age <= FRESH_BASE_BREAKOUT_AGE_MAX
        and tightness_pctile is not None
        and tightness_pctile <= FRESH_BASE_TIGHTNESS_MAX_PCTILE
    )

    extension_ratio = (close / ema21) if (close is not None and ema21) else None
    extended = bool(
        close is not None and ema21 is not None and close > EXTENSION_EMA21_MULTIPLE * ema21
    )

    entry_px = entry if entry is not None else close
    stop_px = stop if stop is not None else (entry_px * 0.99 if entry_px else None)
    resistance = None
    resistance_method = None
    if entry_px and stop_px and stop_px < entry_px:
        target = risk_plan.structural_target(bars, entry_px, stop_px, setup_family)
        if target and not target.get("synthetic"):
            resistance = target["target"]
            resistance_method = target["method"]

    room_pct = None
    if resistance is not None and close:
        room_pct = (resistance - close) / close * 100.0
    # No real resistance visible in the window reads as open sky -- maximum
    # room, not "no room" (the doctrine's "room above matters" names the
    # absence of a level as favourable, not as a penalty).
    room_above = bool(room_pct is None or room_pct >= NO_ROOM_PCT)
    near_resistance = bool(room_pct is not None and room_pct < NEAR_RESISTANCE_PCT)

    return {
        "fresh_base_breakout": fresh_base_breakout,
        "breakout_age": breakout_age,
        "tightness_pctile": _round(tightness_pctile, 2),
        "extended": extended,
        "close": _round(close, 2),
        "ema21": _round(ema21, 2),
        "extension_ratio": _round(extension_ratio),
        "room_above": room_above,
        "room_pct": _round(room_pct, 2),
        "resistance": _round(resistance, 2),
        "resistance_method": resistance_method,
        "near_resistance": near_resistance,
    }


# ---------------------------------------------------------------------------
# 3. classify -- the final verdict
# ---------------------------------------------------------------------------

VERDICTS = ("SWING_EP", "INTRADAY_SIP", "AVOID")


def classify(nature: dict[str, Any], location: dict[str, Any]) -> dict[str, Any]:
    """The doctrine's final verdict (spec section 3).

    SWING_EP only when fresh_base_breakout AND room_above AND not extended
    AND nature in {"swing","mixed"}. nature "unknown" (no burst history to
    judge) can never itself earn a SWING_EP -- it degrades to INTRADAY_SIP
    with the reason named, exactly like a proven fade. Every checklist item
    carries the NUMBER behind it (hold_rate, room_pct, extension ratio,
    breakout_age, burst count) -- never a bare boolean.
    """
    nat = nature.get("nature")
    hold_rate = nature.get("hold_rate")
    burst_days = nature.get("burst_days", 0)
    median_fwd_5 = nature.get("median_fwd_5")

    fresh_base_breakout = bool(location.get("fresh_base_breakout"))
    breakout_age = location.get("breakout_age")
    tightness_pctile = location.get("tightness_pctile")
    extended = bool(location.get("extended"))
    extension_ratio = location.get("extension_ratio")
    room_above = bool(location.get("room_above"))
    room_pct = location.get("room_pct")
    near_resistance = bool(location.get("near_resistance"))

    checklist = [
        {
            "item": "historical continuation nature",
            "pass": nat in ("swing", "mixed"),
            "value": {"nature": nat, "hold_rate": hold_rate, "burst_days": burst_days,
                      "median_fwd_5": median_fwd_5},
        },
        {
            "item": "room above",
            "pass": room_above,
            "value": {"room_pct": room_pct},
        },
        {
            "item": "fresh base breakout",
            "pass": fresh_base_breakout,
            "value": {"breakout_age": breakout_age, "tightness_pctile": tightness_pctile},
        },
        {
            "item": "extended already",
            "pass": not extended,
            "value": {"extended": extended, "extension_ratio": extension_ratio},
        },
        {
            "item": "near resistance",
            "pass": not near_resistance,
            "value": {"room_pct": room_pct},
        },
    ]

    if near_resistance:
        verdict = "AVOID"
        why = (
            f"Opening near resistance (room_pct={room_pct}, below the "
            f"{NEAR_RESISTANCE_PCT}% floor) -- the doctrine's avoidable location; "
            "price usually cannot break resistance without absorbing supply."
        )
    elif nat == "fade" and extended:
        verdict = "AVOID"
        why = (
            f"Burst-and-fade nature (hold_rate={hold_rate} over {burst_days} burst "
            f"days) AND already extended ({extension_ratio}x EMA21) -- doubly "
            "disqualified."
        )
    elif nat == "unknown":
        verdict = "INTRADAY_SIP"
        why = (
            f"No burst history to judge nature (burst_days={burst_days}, below the "
            f"{NATURE_MIN_BURST_DAYS}-burst floor) -- degrades to intraday-only "
            "rather than guessing a swing nature."
        )
    elif extended:
        verdict = "INTRADAY_SIP"
        why = (
            f"Extended {extension_ratio}x EMA21 (over {EXTENSION_EMA21_MULTIPLE}x) -- "
            "the doctrine: extended price is intraday only."
        )
    elif not room_above:
        verdict = "INTRADAY_SIP"
        why = f"No room above (room_pct={room_pct}, below the {NO_ROOM_PCT}% floor)."
    elif nat == "fade":
        verdict = "INTRADAY_SIP"
        why = (
            f"Burst-and-fade nature (hold_rate={hold_rate} over {burst_days} burst "
            "days) -- this stock's own bursts historically fade; intraday only."
        )
    elif fresh_base_breakout and room_above and not extended and nat in ("swing", "mixed"):
        verdict = "SWING_EP"
        why = (
            f"Fresh base breakout (breakout_age={breakout_age}), room above "
            f"(room_pct={room_pct}), not extended ({extension_ratio}x EMA21), "
            f"nature={nat} (hold_rate={hold_rate} over {burst_days} burst days)."
        )
    else:
        verdict = "INTRADAY_SIP"
        why = (
            f"Not (yet) a fresh base breakout (breakout_age={breakout_age}, "
            f"tightness_pctile={tightness_pctile}) -- not clean enough for a swing "
            "plan today."
        )

    return {"verdict": verdict, "checklist": checklist, "why": why}


# ---------------------------------------------------------------------------
# 4. compute + persist (pure computation above; this is the only writer)
# ---------------------------------------------------------------------------

def compute_ep_quality(
    conn,
    symbol: str,
    scan_date: str,
    bars: list[Bar],
    pivot: float | None = None,
    entry: float | None = None,
    stop: float | None = None,
    setup_family: str = "",
) -> dict[str, Any]:
    """Compute burst_nature + location_read + classify for one symbol/date
    and upsert the row into ep_quality_daily.

    This is a compute+persist helper only -- nothing else in the pipeline
    calls it yet. The EP/D2 candidate stage carrying this verdict, and an
    INTRADAY_SIP name being refused a SWING plan, are later, separately
    scoped wiring waves (spec section 4).
    """
    nature = burst_nature(bars)
    location = location_read(bars, pivot=pivot, entry=entry, stop=stop, setup_family=setup_family)
    result = classify(nature, location)
    checklist_json = json.dumps(result["checklist"])
    conn.execute(
        "INSERT INTO ep_quality_daily "
        "(scan_date, symbol, verdict, nature, hold_rate, median_fwd_5, room_pct, "
        "extended, fresh_base, checklist_json, why) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(scan_date, symbol) DO UPDATE SET "
        "verdict=excluded.verdict, nature=excluded.nature, hold_rate=excluded.hold_rate, "
        "median_fwd_5=excluded.median_fwd_5, room_pct=excluded.room_pct, "
        "extended=excluded.extended, fresh_base=excluded.fresh_base, "
        "checklist_json=excluded.checklist_json, why=excluded.why",
        (
            scan_date, symbol.upper(), result["verdict"], nature["nature"],
            nature["hold_rate"], nature["median_fwd_5"], location["room_pct"],
            int(bool(location["extended"])), int(bool(location["fresh_base_breakout"])),
            checklist_json, result["why"],
        ),
    )
    return {"nature": nature, "location": location, **result}
