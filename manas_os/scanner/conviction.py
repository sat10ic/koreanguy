"""manas_os/scanner/conviction.py — WAVE E1 conviction score (backend lane).

Implements manas_os/design/CONVICTION_RANK_SPEC_2026-07-21.md: the ordinal
rank a survivor gets today has NO setup-conviction axis (it sorts on
delivery_z + sector-adjusted momentum + confluence COUNT), so a quiet
pullback continuation routinely outranks a fresh initiation — backwards from
the corpus (Arora/TradeTM: initiation/catalyst first, continuation is the
add). This module is the pure-function scoring layer; scanner.candidates
wires it into the per-candidate build and the ordinal sort (rank composition
only — the gate itself is UNCHANGED, conviction never admits or refuses).

Every function here is a pure read: no schema writes, no side effects. Bars
are the same oldest-first OHLCV dict shape used throughout scanner/engine
(date/open/high/low/close/prev_close/volume/delivery_qty/delivery_pct — see
candidates.load_symbol_bars).

Weights below are Assumption-flagged, first-pass priors. Per the spec's own
rail: "calibration against practitioner picks + the scorecard is the
promotion gate" — nothing here is tuned against forward returns yet.
"""
from __future__ import annotations

import json
from typing import Any

from manas_os.engine import manas_indicators as mi

Bar = dict[str, Any]


def _num(bar: Bar, key: str) -> float | None:
    v = bar.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Axis 2 (participation) — U/D ratio
# ---------------------------------------------------------------------------

def ud_ratio(bars: list[Bar], n: int = 21) -> float | None:
    """sum(up-close volume) / sum(down-close volume) over the trailing `n`
    sessions (spec axis 2, "U/D RATIO (NEW)"). The shared practitioner charts
    (SAREGAMA 2.49, EXICOM 1.48) display this as a first-class accumulation
    read.

    Assumption (spec): >= 1.5 strong, 1.0-1.5 neutral, < 1.0 distribution —
    tell me if wrong. This function returns the raw ratio; the banding is
    applied by conviction_score's normalization, not here.

    Returns None when fewer than `n` bars exist (insufficient history) or
    when the window has no down-close volume at all (ratio undefined — a
    genuine all-up 21-session window is rare enough that treating it as
    "insufficient data" rather than inventing an infinite/capped ratio is the
    more honest failure mode; Assumption, tell me if wrong).
    """
    if n <= 0 or len(bars) < n:
        return None
    window = bars[-n:]
    up_vol = 0.0
    down_vol = 0.0
    for bar in window:
        close = _num(bar, "close")
        prev = _num(bar, "prev_close")
        vol = _num(bar, "volume")
        if close is None or prev is None or vol is None:
            continue
        if close > prev:
            up_vol += vol
        elif close < prev:
            down_vol += vol
    if down_vol <= 0:
        return None
    return up_vol / down_vol


# ---------------------------------------------------------------------------
# Chart-fit grade (gate-adjacent, not a rank axis) — 30-SMMA cross count
# ---------------------------------------------------------------------------

# Assumption (spec text is internally in tension: "since the last structure
# break" vs. the done-test's own "over the last ~60 sessions" — a fixed
# ~60-session lookback is used as the practical stand-in for both readings;
# tell me if wrong.
CHART_FIT_MA_PERIOD = 30
CHART_FIT_LOOKBACK = 60
CHART_FIT_TREND_SLOPE_PCT = 2.0  # Assumption: +/-2% MA drift over the window counts as "trending", else sideways.


def chart_fit_grade(
    bars: list[Bar], ma_period: int = CHART_FIT_MA_PERIOD, lookback: int = CHART_FIT_LOOKBACK,
) -> dict[str, Any]:
    """30-period SMOOTHED MA (SMMA/RMA — Koroush AK method, user-supplied
    2026-07-21) cross count over the trailing `lookback` sessions, plus MA
    slope direction. Grid (spec, LOCKED numbers): 0-3 crosses + trending MA
    = momentum-ideal; 7+ crosses or sideways MA = momentum-poor (reversion
    turf). `reversion_grade` is the complementary read: a momentum-poor chart
    is reversion-turf-ideal, and vice versa.

    Returns {"crosses": int|None, "ma_direction": "up"|"down"|"sideways"|None,
    "momentum_grade": "ideal"|"average"|"poor"|None, "reversion_grade": same
    set, "available": bool}. All fields None/False when there isn't enough
    history to compute the MA (never a fabricated grade on thin data).
    """
    closes = [_num(b, "close") for b in bars]
    if len(bars) < ma_period + 2:
        return {
            "crosses": None, "ma_direction": None,
            "momentum_grade": None, "reversion_grade": None, "available": False,
        }
    ma = mi._rma(closes, ma_period)
    window_start = max(ma_period, len(bars) - lookback)

    crosses = 0
    prev_side: str | None = None
    for i in range(window_start, len(bars)):
        c, m = closes[i], ma[i]
        if c is None or m is None:
            continue
        side = "above" if c > m else ("below" if c < m else None)
        if side is None:
            continue
        if prev_side is not None and side != prev_side:
            crosses += 1
        prev_side = side

    ma_in_window = [m for m in ma[window_start:] if m is not None]
    if len(ma_in_window) < 2:
        return {
            "crosses": crosses, "ma_direction": None,
            "momentum_grade": None, "reversion_grade": None, "available": False,
        }
    first, last = ma_in_window[0], ma_in_window[-1]
    change_pct = (last - first) / first * 100.0 if first else 0.0
    if change_pct > CHART_FIT_TREND_SLOPE_PCT:
        direction = "up"
    elif change_pct < -CHART_FIT_TREND_SLOPE_PCT:
        direction = "down"
    else:
        direction = "sideways"

    trending = direction in ("up", "down")
    if crosses <= 3 and trending:
        momentum_grade = "ideal"
    elif crosses >= 7 or direction == "sideways":
        momentum_grade = "poor"
    else:
        momentum_grade = "average"

    if crosses >= 7 or direction == "sideways":
        reversion_grade = "ideal"
    elif crosses <= 3 and trending:
        reversion_grade = "poor"
    else:
        reversion_grade = "average"

    return {
        "crosses": crosses, "ma_direction": direction,
        "momentum_grade": momentum_grade, "reversion_grade": reversion_grade,
        "available": True,
    }


# ---------------------------------------------------------------------------
# Axis 4 (confluence) — "featured in"
# ---------------------------------------------------------------------------

def featured_in(conn, symbol: str, scan_date: str, lookback_days: int = 10) -> dict[str, Any]:
    """Distinct SCREENER FAMILIES (ChartsMaze, via candidates.SCREENER_FAMILY)
    unioned with our own detector tags (persisted scan_candidates.setup_family
    history + discovery_bucket archetypes, mapped through the same
    archetype->setup_type->family chain candidates.py itself uses), each
    stamped with its most recent hit date over the trailing `lookback_days`
    sessions on/before scan_date.

    Assumption: a 10-session lookback window — the spec names no window and
    a same-day-only read would erase yesterday's still-live ChartsMaze
    confluence the very next session; tell me if wrong.

    Counts DISTINCT FAMILIES, never raw hit count (spec axis 4: "a symbol in
    6 momentum screens is one signal, not six").

    Returns {"families": [{"family": str, "newest": "YYYY-MM-DD"}, ...]
    (sorted newest-first), "count": int, "newest": str|None}.
    """
    # Lazy import: candidates.py imports this module at top level, so this
    # module must not import candidates.py back at MODULE scope (that would
    # be a real circular import). Deferring to function-call time is safe —
    # by the time featured_in() actually runs, both modules have finished
    # loading regardless of which one imported the other first.
    from manas_os.scanner.candidates import (
        DISCOVERY_ARCHETYPE_SETUP_TYPE, SCREENER_FAMILY, setup_family as _setup_family,
    )

    sym = symbol.upper()
    families: dict[str, str] = {}  # family -> most recent ISO date seen

    def _consider(fam: str | None, hit_date: str | None) -> None:
        if not fam or not hit_date:
            return
        if fam not in families or hit_date > families[fam]:
            families[fam] = hit_date

    def _table_exists(name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def _column_exists(table: str, column: str) -> bool:
        return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))

    # 1) ChartsMaze screener_hits -> SCREENER_FAMILY.
    if _table_exists("screener_hits"):
        rows = conn.execute(
            "SELECT trade_date, screener FROM screener_hits "
            "WHERE symbol = ? AND bearish = 0 AND trade_date <= ? "
            "AND trade_date >= date(?, ?)",
            (sym, scan_date, scan_date, f"-{lookback_days} days"),
        ).fetchall()
        for r in rows:
            _consider(SCREENER_FAMILY.get(str(r["screener"]).lower()), r["trade_date"])

    # 2) Our own detector tags — persisted scan_candidates setup_family
    # history (survivors only; a hard refusal isn't "featured"). setup_family
    # is an ADDITIVE column (candidates.ensure_schema); a base schema.sql
    # scan_candidates table predating that ALTER simply has no history yet.
    if _table_exists("scan_candidates") and _column_exists("scan_candidates", "setup_family"):
        rows = conn.execute(
            "SELECT DISTINCT scan_date, setup_family FROM scan_candidates "
            "WHERE symbol = ? AND scan_date <= ? AND scan_date >= date(?, ?)",
            (sym, scan_date, scan_date, f"-{lookback_days} days"),
        ).fetchall()
        for r in rows:
            _consider(r["setup_family"], r["scan_date"])

    # 3) discovery_bucket archetypes — catches our own detector's read on
    # names the cascade refused (a WATCH/DISCOVERY tag is still an
    # independent read of the chart), mapped through candidates.py's own
    # archetype->setup_type->family chain so this never drifts out of sync.
    if _table_exists("discovery_bucket"):
        rows = conn.execute(
            "SELECT scan_date, archetypes_json FROM discovery_bucket "
            "WHERE symbol = ? AND scan_date <= ? AND scan_date >= date(?, ?)",
            (sym, scan_date, scan_date, f"-{lookback_days} days"),
        ).fetchall()
        for r in rows:
            try:
                archetypes = json.loads(r["archetypes_json"] or "[]")
            except (json.JSONDecodeError, TypeError):
                archetypes = []
            for archetype in archetypes:
                st = DISCOVERY_ARCHETYPE_SETUP_TYPE.get(str(archetype).lower())
                if st:
                    _consider(_setup_family(st), r["scan_date"])

    ordered = sorted(families.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "families": [{"family": fam, "newest": hit_date} for fam, hit_date in ordered],
        "count": len(families),
        "newest": ordered[0][1] if ordered else None,
    }


# ---------------------------------------------------------------------------
# Axis 5 (theme) — theme_pulse membership (another lane owns theme_pulse.py;
# this reads it defensively and never creates/modifies it).
# ---------------------------------------------------------------------------

def theme_membership(conn, symbol: str, scan_date: str) -> dict[str, Any] | None:
    """Is `symbol` a member of a firing industry theme (scanner.theme_pulse)
    on scan_date. Returns None (axis unavailable) when theme_pulse isn't
    importable or its table doesn't exist yet — never creates it (rails:
    "do NOT create or modify theme_pulse").

    Returns {"member": bool, "theme": {...}|None} once the table exists, even
    if empty for this scan_date (member=False there, not unavailable — the
    table existing means the axis is genuinely measurable, it's just a "no").
    """
    try:
        from manas_os.scanner import theme_pulse
    except ImportError:
        return None
    table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='theme_pulse'"
    ).fetchone()
    if table is None:
        return None
    try:
        themes = theme_pulse.read_persisted(conn, scan_date)
    except Exception:  # noqa: BLE001 — a malformed/partial theme_pulse row must
        # never take the whole conviction score down with it.
        return None
    if not themes:
        return {"member": False, "theme": None}
    sym = symbol.upper()
    for theme in themes:
        if sym in (theme.get("member_symbols") or []):
            return {"member": True, "theme": theme}
    return {"member": False, "theme": None}


# ---------------------------------------------------------------------------
# Axis 1 (setup tier)
# ---------------------------------------------------------------------------

# spec's three named tiers (LOCKED mapping; weight 3/2/1 collapses to a 0/0.5/
# 1.0 normalized scale in conviction_score, not re-derived here).
TIER_A_SETUP_TYPES = frozenset({"ep", "d2_episodic", "strong_start_ready", "ipo_base"})
TIER_B_SETUP_TYPES = frozenset({"pocket_pivot", "persistent_momentum"})
TIER_C_SETUP_TYPES = frozenset({"pullback", "long_tail", "watchlist_timing"})
NEAR_PIVOT_FRESH_EXTENSION_PCT = 8.0  # spec: "near_pivot when leg is fresh (extension_21 <= 8%)"
FRESH_BREAKOUT_AGE_MAX = 3            # spec: "fresh base breakout (breakout_age <= 3 AND close > pivot)"


def setup_tier(setup_type: str | None, evidence: dict[str, Any] | None = None) -> str:
    """"A"|"B"|"C" per the spec's mapping:
      A / initiation           — ep, d2_episodic, strong_start_ready, ipo_base,
                                  or a fresh base breakout (breakout_age <= 3
                                  AND close > pivot).
      B / velocity continuation — pocket_pivot, persistent_momentum, or
                                  near_pivot when the leg is fresh
                                  (extension_21 <= 8%).
      C / mean-reversion continuation — pullback, long_tail, generic
                                  watchlist_timing (and, Assumption, anything
                                  else not named above — tell me if wrong;
                                  this is a deliberate "don't invent a 4th
                                  tier" default, not a silent A/B demotion).

    `evidence` keys used: breakout_age, close, pivot, extension_21 (all
    optional; a missing key simply fails that specific fresh-leg test rather
    than raising).
    """
    st = (setup_type or "").lower()
    evidence = evidence or {}

    if st in TIER_A_SETUP_TYPES:
        return "A"
    breakout_age = evidence.get("breakout_age")
    close = evidence.get("close")
    pivot = evidence.get("pivot")
    if (
        breakout_age is not None and breakout_age <= FRESH_BREAKOUT_AGE_MAX
        and close is not None and pivot is not None and close > pivot
    ):
        return "A"

    if st in TIER_B_SETUP_TYPES:
        return "B"
    if st == "near_pivot":
        extension_21 = evidence.get("extension_21")
        if extension_21 is not None and extension_21 <= NEAR_PIVOT_FRESH_EXTENSION_PCT:
            return "B"
        return "C"  # near_pivot without a fresh leg reads as generic timing, not velocity continuation.

    if st in TIER_C_SETUP_TYPES:
        return "C"
    return "C"


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------

# Assumption (spec-flagged, calibration against practitioner picks + the
# scorecard is the promotion gate before these move): tier is the dominant
# axis per the spec header; the remaining four split the rest, participation
# next-heaviest per the trigger's diagnosis (RAIN/SKIPPER-style episodic
# bursts need volume confirmation to outrank a quiet pullback).
AXIS_WEIGHTS: dict[str, float] = {
    "tier": 0.40,
    "participation": 0.20,
    "location": 0.15,
    "confluence": 0.15,
    "theme": 0.10,
}
assert abs(sum(AXIS_WEIGHTS.values()) - 1.0) < 1e-9

_TIER_NORM = {"A": 1.0, "B": 0.5, "C": 0.0}
_TIER_LABEL = {"A": "A/initiation", "B": "B/velocity continuation", "C": "C/mean-reversion continuation"}


def _unavailable_axis(name: str) -> dict[str, Any]:
    return {
        "raw": None, "normalized": None, "weight": AXIS_WEIGHTS[name],
        "contribution": 0.0, "available": False,
    }


def _location_from_pct_up(pct_up: float) -> float:
    """Arora's buying-force test with the spec's LATE_IN_MOVE penalty: >80%
    up from the 65d low is "arriving late" (the trade-autopsy's worst tag),
    not extra credit. Assumption on the exact curve shape/decay rate — tell
    me if wrong; only the >80% penalty direction and the saturation point
    are spec-cited. The decay is deliberately steep (zeroed out by 120% up)
    so a genuinely late-stage mover reads clearly worse than a fresh,
    moderate 30-40% mover — a shallow decay would let "late" still outscore
    "early and modest", defeating the point of the penalty.
    """
    if pct_up > 80.0:
        return _clamp(1.0 - (pct_up - 80.0) / 40.0)
    return _clamp(pct_up / 50.0)


def conviction_score(components: dict[str, Any]) -> dict[str, Any]:
    """Composite conviction score across the spec's five named axes.

    `components` (all optional except setup_type):
      setup_type           -- candidate's setup_type string
      tier_evidence         -- {"breakout_age","close","pivot","extension_21"}
                               for setup_tier's fresh-leg/fresh-breakout tests
      day_rvol              -- today's volume / trailing-20d avg volume
                               (candidates.py symbol_timing's "rvol" field --
                               the spec's "have: eod_detectors day_rvol")
      ud_ratio               -- ud_ratio() output
      nearness_52w           -- close / trailing-252d high (0..~1+ ratio;
                               gates.py's own "have" field, reused not
                               re-derived)
      pct_up_from_65d_low    -- discovery_metrics.pct_up_from_65d_low() output
      featured_in            -- featured_in() output
      theme                  -- theme_membership() output, or None

    Every axis is normalized to 0-1 BEFORE weighting. A missing axis
    contributes 0 to the score and is named, verbatim, in "why" as
    unavailable — never silently imputed (spec rail).

    Returns {"score": 0-100 float, "axes": {name: {...}}, "why": [str, ...]}.
    """
    axes: dict[str, Any] = {}
    why: list[str] = []

    # ---- 1. SETUP TIER (dominant axis) ----
    tier = setup_tier(components.get("setup_type"), components.get("tier_evidence"))
    tier_norm = _TIER_NORM[tier]
    axes["tier"] = {
        "raw": tier, "normalized": tier_norm, "weight": AXIS_WEIGHTS["tier"],
        "contribution": round(tier_norm * AXIS_WEIGHTS["tier"], 4), "available": True,
    }
    why.append(f"Tier {_TIER_LABEL[tier]}")

    # ---- 2. PARTICIPATION SURGE ----
    day_rvol = components.get("day_rvol")
    ud = components.get("ud_ratio")
    sub_norms = []
    if day_rvol is not None:
        sub_norms.append(_clamp((day_rvol - 1.0) / 2.0))  # Assumption: 1x->0, 3x+->1.
    if ud is not None:
        sub_norms.append(_clamp((ud - 0.5) / 1.5))  # Assumption: 0.5->0, 2.0->1 (spans the spec's distribution/strong bands).
    if sub_norms:
        participation_norm = sum(sub_norms) / len(sub_norms)
        axes["participation"] = {
            "raw": {"day_rvol": day_rvol, "ud_ratio": ud},
            "normalized": round(participation_norm, 4), "weight": AXIS_WEIGHTS["participation"],
            "contribution": round(participation_norm * AXIS_WEIGHTS["participation"], 4),
            "available": True,
        }
        parts = []
        if day_rvol is not None:
            parts.append(f"RVOL {day_rvol:.2f}x")
        if ud is not None:
            parts.append(f"U/D {ud:.2f}")
        why.append("Participation: " + ", ".join(parts))
    else:
        axes["participation"] = _unavailable_axis("participation")
        why.append("Participation unavailable (no RVOL or U/D ratio)")

    # ---- 3. LOCATION ----
    nearness = components.get("nearness_52w")
    pct_up = components.get("pct_up_from_65d_low")
    loc_subs = []
    if nearness is not None:
        loc_subs.append(_clamp(nearness))
    if pct_up is not None:
        loc_subs.append(_location_from_pct_up(pct_up))
    if loc_subs:
        location_norm = sum(loc_subs) / len(loc_subs)
        axes["location"] = {
            "raw": {"nearness_52w": nearness, "pct_up_from_65d_low": pct_up},
            "normalized": round(location_norm, 4), "weight": AXIS_WEIGHTS["location"],
            "contribution": round(location_norm * AXIS_WEIGHTS["location"], 4),
            "available": True,
        }
        parts = []
        if nearness is not None:
            parts.append(f"{nearness * 100:.0f}% of 52w high")
        if pct_up is not None:
            late_tag = " (late-in-move)" if pct_up > 80.0 else ""
            parts.append(f"{pct_up:.0f}% up from 65d low{late_tag}")
        why.append("Location: " + ", ".join(parts))
    else:
        axes["location"] = _unavailable_axis("location")
        why.append("Location unavailable (no 52w-high nearness or 65d-low data)")

    # ---- 4. CONFLUENCE ("featured in") ----
    featured = components.get("featured_in")
    if featured and featured.get("count"):
        count = featured["count"]
        confluence_norm = _clamp(count / 3.0)  # Assumption: 3+ distinct families saturates (matches candidates.py's own confluence-count cap logic elsewhere).
        fam_names = [f["family"] for f in featured.get("families", [])]
        axes["confluence"] = {
            "raw": featured, "normalized": round(confluence_norm, 4),
            "weight": AXIS_WEIGHTS["confluence"],
            "contribution": round(confluence_norm * AXIS_WEIGHTS["confluence"], 4),
            "available": True,
        }
        newest = featured.get("newest")
        plural = "s" if count != 1 else ""
        tail = f", newest {newest}" if newest else ""
        why.append(f"Featured in {count} screen{plural} ({', '.join(fam_names)}){tail}")
    else:
        axes["confluence"] = _unavailable_axis("confluence")
        why.append("Confluence unavailable (not featured in any named screen)")

    # ---- 5. THEME MEMBERSHIP ----
    theme = components.get("theme")
    if theme is not None:
        member = bool(theme.get("member"))
        theme_norm = 1.0 if member else 0.0
        axes["theme"] = {
            "raw": theme, "normalized": theme_norm, "weight": AXIS_WEIGHTS["theme"],
            "contribution": round(theme_norm * AXIS_WEIGHTS["theme"], 4), "available": True,
        }
        if member and theme.get("theme"):
            t = theme["theme"]
            why.append(f"Theme: {t.get('sector_label') or t.get('industry')} ({t.get('member_count')} members)")
        else:
            why.append("Theme: not in a firing theme")
    else:
        axes["theme"] = _unavailable_axis("theme")
        why.append("Theme unavailable (theme_pulse not present)")

    score = round(sum(a["contribution"] for a in axes.values()) * 100.0, 2)
    return {"score": score, "axes": axes, "why": why}
