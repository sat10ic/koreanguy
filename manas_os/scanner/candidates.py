"""Manas 2.0 candidate engine — the deterministic refusal cascade (plan T1.4/T1.5).

Pool = (ChartsMaze screener confluence when a dump exists) UNION (an OHLCV
detector shortlist: tradeable names within 15% of their 252d high) UNION
(discovery.build_bucket: the ~100-140/day sensitive bucket across up to 9
recall-first archetypes — WAVE_M M2, user order 2026-07-11: "the filter IS
the defect", CONSTRAINT_METHOD_FIRST_IA.md amendment 3) — so the feed and the
replay harness work on EVERY session, not only dump dates (LEARNINGS
2026-07-06). build_bucket is called directly (not read from the persisted
discovery_bucket table) so the union is correct regardless of pipeline stage
order or replay/backtest context, which never runs the discovery_bucket CLI
stage; the nightly discovery_bucket stage still runs separately afterward to
persist the table for focus_themes/morning_setups. Every pooled name then
runs scanner.gates.run_cascade (regime → tradability → trend-template →
fresh-leg → participation → risk). HARD refusals are LEDGERED with the failed
gate + reason. WAVE_M M3: RS floor, 52w-high nearness, and a regime family-
kill no longer hard-refuse — they ride as named, weighted OBJECTIONS in gate
evidence; a surviving candidate's objections subtract from its ordinal rank
and cap its grade at B (never silent exclusion). Survivors get an ORDINAL
rank (1..M) ordered by (objection-adjusted delivery_z, sector-adjusted
momentum, confluence families) — there is no additive 0-100 score any more;
`readiness` persists the rank-percentile for backward compatibility only.
exit_state is joined at build time: Weakening caps the grade at B, Broken
refuses (one symbol = one opinion). risk/plan.py is the single writer of
stop/size/R:R.
"""
from typing import Any
import json
import time

from manas_os.engine import eod_detectors, price_action
from manas_os.engine.universe_filter import GateConfig, evaluate_symbol
from manas_os.regime.sectors import INDUSTRY_TO_SECTOR, canonical_sector_key, display_label
from manas_os.risk import plan as risk_plan
from manas_os.scanner import conviction, discovery, discovery_metrics, gates, outcomes
from manas_os.sources import chartsmaze, fundamentals
from manas_os.sources.chartsmaze_scanners import confluence_for_date

# WAVE E1 (CONVICTION_RANK_SPEC_2026-07-21.md): survivors are ranked TOP-15 by
# conviction_score; conviction_rank is populated 1..CONVICTION_TOP_N for the
# highest-conviction survivors and left None (below the cut) for the rest.
# The gate itself is UNCHANGED -- conviction only orders survivors.
CONVICTION_TOP_N = 15

STAGE = "scan_candidates"
SOURCE = "daily_prices+chartsmaze"

MIN_CONFLUENCE = 2  # symbols need >=2 distinct non-bearish screener hits to enter the pool
GROWTH_FIELDS = ("eps_yoy", "eps_qoq", "sales_yoy", "opm_yoy")
GROWTH_MIN = -200.0
GROWTH_MAX = 500.0
STOP_MIN_PCT = 1.0
STOP_MAX_PCT = 8.0
INTERIM_CAPITAL = 1_000_000.0
INTERIM_RISK_PCT = 0.005
LEADER_NEAR_LEVEL_PCT = 0.05
GAP_PROJECTION_SETUP_TYPES = frozenset({"ep", "d2_episodic"})

# setup_type -> gate FAMILY (plan T1.4 mapping; pullback is a pattern for
# regime-eligibility purposes — SELECTIVE allows it, per the LOCKED table).
SETUP_FAMILY = {
    "ep": "catalyst", "ipo_base": "catalyst",
    "vcp": "base/pattern", "launch_pad": "base/pattern", "tight": "base/pattern",
    "pullback": "base/pattern", "shakeout": "base/pattern",
    "pocket_pivot": "momentum", "near_pivot": "momentum", "watchlist_timing": "momentum",
    "strong_start_ready": "momentum", "d2_episodic": "momentum",
    "persistent_momentum": "momentum", "recent_listing": "catalyst",
    "reversal": "reversal", "busted_reversal": "busted_reversal",
    "long_tail": "reversal",
    "ants": "accumulation",
    "weekly_base_breakout": "weekly_base_breakout",
}
# discovery archetype -> setup_type. Ordered by _DISCOVERY_SETUP_PRIORITY below
# so early-turn tags can specialize otherwise-generic timing labels before
# gates.run_cascade receives setup_family.
DISCOVERY_ARCHETYPE_SETUP_TYPE = {
    "strong_start_ready": "strong_start_ready",
    "d2_episodic": "d2_episodic",
    "persistent_momentum": "persistent_momentum",
    "ep_ipo": "ipo_base",
    "recent_listing": "recent_listing",
    "reversal": "reversal",
    "busted_reversal": "busted_reversal",
    "pullback_to_rising_ma": "pullback",
    "pullback_to_50ma": "pullback",
    "vcp_coil": "vcp",
    "ipo_inside_bar": "ipo_base",
    "long_tail": "long_tail",
    "weekly_base_breakout": "weekly_base_breakout",
}
_DISCOVERY_SETUP_PRIORITY = (
    "busted_reversal",
    "reversal",
    "ep_ipo",
    "ipo_inside_bar",
    "recent_listing",
    "strong_start_ready",
    "d2_episodic",
    "persistent_momentum",
    "pullback_to_rising_ma",
    "pullback_to_50ma",
    "vcp_coil",
    "weekly_base_breakout",
    "long_tail",
)
# screener name -> family, for confluence-family counting
SCREENER_FAMILY = {
    "vcp": "base/pattern", "vcp-loose": "base/pattern", "tight-setup-daily": "base/pattern",
    "tight-setup-weekly": "base/pattern", "flag-pennants": "base/pattern",
    "inside-bar-daily": "base/pattern", "inside-bar-weekly": "base/pattern",
    "horizontal-resistance-daily": "base/pattern", "ipo-setups": "catalyst",
    "earnings-gap-up": "catalyst", "positive-earnings-reaction": "catalyst",
    "episodic-pivot": "catalyst", "momentum-scanner": "momentum", "gap-up": "momentum",
    "top-gainers": "momentum", "rs-high-before-price-high": "momentum",
    "past-winners": "momentum", "highest-volume": "accumulation",
    "volume-spike": "accumulation", "volume-footprint": "accumulation",
    "shakeout-10EMA": "base/pattern", "shakeout-21EMA": "base/pattern",
    "shakeout-50EMA": "base/pattern", "shakeout-200EMA": "base/pattern",
}


def setup_family(setup_type: str | None) -> str:
    return SETUP_FAMILY.get((setup_type or "").lower(), "momentum")


# WAVE_L 2026-07-21 (RAIN/SKIPPER/NUVOCO Monday-open refusal-class fix):
# setup_types whose corpus doctrine has NO fixed target -- trail the
# 10/21EMA and ride (ARORA_SHARDS_NUANCES/INDIA_PLAYBOOK half-sell rule) --
# derived FROM SETUP_FAMILY so this can never drift out of sync with the
# gate-family mapping above. "pullback" is added explicitly: it maps to
# "base/pattern" for regime-GATE purposes (unchanged) but a pullback-to-
# rising-MA continuation entry is itself trail-managed per corpus doctrine.
TRAIL_MANAGED_SETUP_TYPES = frozenset(
    {k for k, v in SETUP_FAMILY.items() if v in {"momentum", "catalyst", "reversal", "busted_reversal"}}
    | {"pullback"}
)


def append_footprint_evidence(
    conn, symbol: str, scan_date: str, evidence: list[dict[str, Any]]
) -> None:
    """Append one display-only chip without touching gates or rank inputs."""
    table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='footprint_daily'"
    ).fetchone()
    if table is None:
        return
    row = conn.execute(
        "SELECT score,tier,streak_days,delivery_band,split_suspect "
        "FROM footprint_daily WHERE trade_date=? AND symbol=?",
        (scan_date, symbol.upper()),
    ).fetchone()
    if row is None or row["score"] is None:
        return
    if int(row["split_suspect"] or 0):
        value = f"{float(row['score']):.1f} split-suspect"
    else:
        tier = str(row["tier"] or "normal").upper()
        plain_tier = (
            "extreme" if tier == "EXTREME"
            else "unusual" if tier in {"STRICT", "ABNORMAL"}
            else "normal"
        )
        parts = [f"{float(row['score']):.1f} {plain_tier}"]
        if int(row["streak_days"] or 0) > 0:
            parts.append(f"{int(row['streak_days'])}d streak")
        if row["delivery_band"]:
            parts.append(f"delivery {row['delivery_band']}")
        value = " | ".join(parts)
    evidence.append({"filter": "footprint", "value": value})


def setup_type_from_discovery_archetypes(archetypes: list[str]) -> str | None:
    seen = {str(a).lower() for a in archetypes or []}
    for archetype in _DISCOVERY_SETUP_PRIORITY:
        if archetype in seen:
            return DISCOVERY_ARCHETYPE_SETUP_TYPE[archetype]
    return None


def _candidate_discovery_archetypes(
    bars: list[dict[str, Any]], discovery_entry: dict[str, Any] | None,
) -> list[str]:
    """Keep reversal family assignment stable after discovery size control.

    The capped bucket controls which symbols discovery adds to the live pool;
    it must not relabel a symbol already surfaced by confluence or a detector.
    A population-independent reversal admission therefore supplements only the
    current candidate's family evidence and never widens the pool.
    """
    archetypes = list((discovery_entry or {}).get("archetypes") or [])
    if (
        discovery_entry is None
        and discovery.absolute_reversal_archetype(bars)
    ):
        archetypes.append("reversal")
    return archetypes


def confluence_families(screeners: list[str], setup_type: str | None) -> int:
    fams = {SCREENER_FAMILY.get(str(s).lower(), None) for s in (screeners or [])}
    fams.discard(None)
    fams.add(setup_family(setup_type))
    return len(fams)


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scan_candidates ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup TEXT NOT NULL, "
        "readiness REAL, grade TEXT, rs REAL, rs_as_of TEXT, delivery_pct REAL, "
        "delivery_as_of TEXT, pivot REAL, entry REAL, stop REAL, target REAL, "
        "sector TEXT, industry TEXT, evidence_json TEXT, read TEXT, timing_json TEXT, "
        "source TEXT DEFAULT 'scanner', ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol, setup))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_candidates_date_readiness "
        "ON scan_candidates(scan_date, readiness DESC)"
    )
    # score_breakdown_json / measured_move / measured_move_note are additive
    # columns on top of the P2 schema — added via ALTER so existing DBs
    # upgrade transparently (mirrors the pattern in manas_os.db.init_db).
    have = {r[1] for r in conn.execute("PRAGMA table_info(scan_candidates)")}
    for name, ddl in {
        "score_breakdown_json": "TEXT",
        "measured_move": "REAL",
        "measured_move_note": "TEXT",
        "confluence_count": "INTEGER",
        "setup_type": "TEXT",
        "pattern_label": "TEXT",
        "base_age": "INTEGER",
        "days_since_listing": "INTEGER",
        "trade_plan_json": "TEXT",
        "rr": "REAL",
        "suggested_qty": "INTEGER",
        "rank": "INTEGER",
        "rank_of": "INTEGER",
        "setup_family": "TEXT",
        "exit_state": "TEXT",
        "gates_json": "TEXT",
        "conviction_score": "REAL",
        "conviction_axes_json": "TEXT",
        "conviction_rank": "INTEGER",
    }.items():
        if name not in have:
            conn.execute(f"ALTER TABLE scan_candidates ADD COLUMN {name} {ddl}")


def latest_price_date(conn, on_or_before: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices "
        "WHERE series='EQ' AND trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def load_symbol_bars(conn, symbol: str, on_or_before: str, limit: int = 260) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), on_or_before, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _recent_burst(bars: list[dict[str, Any]], lookback: int = 2, pct: float = 10.0) -> bool:
    """True when one of the last `lookback` bars was a >=`pct`% day — the
    D1 expansion that starts an EP/D2 episode (used by the one-opinion
    episodic exception; corpus D2_DAY1_EXPANSION_PCT = 10)."""
    for bar in bars[-lookback:]:
        close, prev = bar.get("close"), bar.get("prev_close")
        if close and prev and (close - prev) / prev * 100.0 >= pct:
            return True
    return False


def _compute_breakout_age(bars: list[dict[str, Any]], pivot: float | None) -> int | None:
    """WAVE_J J6: real leg-age for gate_fresh_leg, replacing the previously
    hardcoded breakout_age=None (candidates.py ~line 792 historically).

    Definition chosen: bars since close FIRST crossed above the current pivot
    (a prior-close <= pivot, current-close > pivot crossover), scanning the
    most recent crossover within `bars`. This is the more faithful reading of
    gates.py's own PULLBACK_AGE_MAX semantics ("leg is N bars old") than a
    persistency(10EMA) count would be: PULLBACK_AGE_MAX/BREAKOUT_AGE_FRESH are
    both anchored to the pivot breakout event itself (gate_fresh_leg compares
    `close <= pivot * PIVOT_FRESH` alongside breakout_age for FRESH_BREAKOUT),
    not to a moving-average trend-persistence concept — persistency count
    answers "how long has price been above its own EMA", a different question
    from "how many bars since THIS pivot was cleared".

    Returns None (unknown — gate_fresh_leg's staleness/state-machine stays
    inert for that name, identical to the pre-J6 baseline) when: no pivot, a
    crossover can't be found in the window, or bars are too thin to tell.
    """
    if not pivot:
        return None
    closes = [b.get("close") for b in bars]
    closes = [float(c) if c is not None else None for c in closes]
    if len(closes) < 2:
        return None
    last_idx = len(closes) - 1
    for i in range(last_idx, 0, -1):
        c, pc = closes[i], closes[i - 1]
        if c is None or pc is None:
            continue
        if c > pivot and pc <= pivot:
            return last_idx - i
    # No crossover found in the window: if the latest close is already below
    # the pivot, age is not applicable (not yet broken out) -- None is
    # correct. If it's above pivot with no crossover visible (pivot itself
    # predates the window), age is unknown rather than assumed zero.
    return None


def _round(value: Any, ndigits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def ep_box_projection(
    bars: list[dict[str, Any]], entry: float, min_gap_pct: float = 5.0,
) -> dict[str, Any] | None:
    """Project the larger of gap-day range and pre-gap box height."""
    if len(bars) < 21 or entry <= 0:
        return None
    latest = bars[-1]
    day_open = _round(latest.get("open"))
    day_close = _round(latest.get("close"))
    prev_close = _round(latest.get("prev_close") or bars[-2].get("close"))
    gap_pct = (day_open - prev_close) / prev_close * 100.0 if day_open and prev_close else None
    # An EP is the day's BURST, not only the opening gap (TradeTM D1 >=10%
    # definition; NUVOCO regression: +12% day on a <5% open gap). Qualify on
    # whichever is larger — open gap or full day change.
    change_pct = (day_close - prev_close) / prev_close * 100.0 if day_close and prev_close else None
    burst_pct = max((v for v in (gap_pct, change_pct) if v is not None), default=None)
    if burst_pct is None or burst_pct <= 0 or burst_pct < min_gap_pct:
        return None
    day_high = _round(latest.get("high"))
    day_low = _round(latest.get("low"))
    gap_day_range = (
        day_high - day_low
        if day_high is not None and day_low is not None and day_high > day_low
        else None
    )
    highs = [v for v in (_round(b.get("high")) for b in bars[-21:-1]) if v is not None]
    lows = [v for v in (_round(b.get("low")) for b in bars[-21:-1]) if v is not None]
    box_height = max(highs) - min(lows) if highs and lows else None
    projections = [
        (height, method)
        for height, method in (
            (box_height, "pre-gap 20-session box height"),
            (gap_day_range, "gap-day range"),
        )
        if height is not None and height > 0
    ]
    if not projections:
        return None
    height, method = max(projections, key=lambda item: item[0])
    return {
        "target": round(entry + height, 2),
        "method": f"{method} ({height:.2f})",
        "synthetic": False,
    }


def leader_measured_move_projection(
    bars: list[dict[str, Any]], entry: float, stop: float, pivot: float | None,
    trail_managed: bool = False,
) -> dict[str, Any] | None:
    """Project an open-sky leader by current-leg height or 2x ADR20.

    This is only selected by the caller when no overhead structure exists.
    Eligibility: latest close within 5% of its trailing 52-week high, within
    5% of a positive pivot above the invalidation, OR (WAVE_L 2026-07-21,
    RAIN/SKIPPER/NUVOCO refusal-class fix) `trail_managed=True` -- the caller
    passes this when the setup_type has no fixed target in the corpus at all
    (momentum/catalyst/reversal/pullback families: TRAIL_MANAGED_SETUP_TYPES).
    Those names are open-ended by DESIGN, not just because price happens to
    sit near a round-number high, so gating them on 52w-high proximity was
    refusing plannable trades with "no measured move -- R:R unknowable" when
    an old, unrelated 52w spike simply put the current close outside the 5%
    band. Requires >=21 bars (ADR20 needs ~20 bars of range) for ANY path --
    below that, ADR is genuinely uncomputable and this returns None so the
    caller's refusal reason stays honest.
    """
    if len(bars) < 21 or entry <= 0 or stop >= entry:
        return None
    close = _round(bars[-1].get("close"))
    highs_52w = [
        value for value in (_round(bar.get("high")) for bar in bars[-252:])
        if value is not None
    ]
    if close is None or not highs_52w:
        return None
    high_52w = max(highs_52w)
    near_high = close >= high_52w * (1.0 - LEADER_NEAR_LEVEL_PCT)
    near_pivot = bool(
        pivot is not None
        and pivot > stop
        and abs(close - pivot) / pivot <= LEADER_NEAR_LEVEL_PCT
    )
    if not (near_high or near_pivot or trail_managed):
        return None
    trail_managed_only = trail_managed and not (near_high or near_pivot)

    leg_window = bars[-90:]
    leg_highs = [_round(bar.get("high")) for bar in leg_window]
    valid_highs = [(i, value) for i, value in enumerate(leg_highs) if value is not None]
    leg_height = None
    if valid_highs:
        high_index, swing_high = max(valid_highs, key=lambda item: item[1])
        prior_lows = [
            value for value in (_round(bar.get("low")) for bar in leg_window[:high_index + 1])
            if value is not None
        ]
        if prior_lows:
            leg_height = swing_high - min(prior_lows)

    adr_ranges = []
    for bar in bars[-20:]:
        high = _round(bar.get("high"))
        low = _round(bar.get("low"))
        bar_close = _round(bar.get("close"))
        if high is not None and low is not None and bar_close:
            adr_ranges.append((high - low) / bar_close)
    adr_projection = entry * 2.0 * (_avg(adr_ranges) or 0.0)
    projections = [
        (height, method)
        for height, method in (
            (leg_height, "current-leg height"),
            (adr_projection, "2.0x ADR20"),
        )
        if height is not None and height > 0
    ]
    if not projections:
        return None
    height, method = max(projections, key=lambda item: item[0])
    return {
        "target": round(entry + height, 2),
        "method": f"open-sky leader {method} ({height:.2f})",
        "synthetic": True,
        "trail_managed_only": trail_managed_only,
    }


def _growth_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    payload: dict[str, Any] = {"value": raw}
    if raw < GROWTH_MIN or raw > GROWTH_MAX:
        payload["untrusted"] = True
    return payload


def growth_payloads(quality: dict[str, Any] | None) -> dict[str, dict[str, Any] | None]:
    """UI/scoring boundary for all growth fields.

    Raw values stay in symbol_quality. Candidate payloads carry a trust marker
    so displays can render bad data as unavailable and scorers can ignore it.
    """
    quality = quality or {}
    return {field: _growth_payload(quality.get(field)) for field in GROWTH_FIELDS}


def trusted_growth_value(quality: dict[str, Any] | None, field: str) -> float | None:
    payload = growth_payloads(quality).get(field)
    if not payload or payload.get("untrusted"):
        return None
    return float(payload["value"])


def format_growth_value(value: Any) -> str:
    payload = _growth_payload(value)
    if not payload:
        return "N/A"
    if payload.get("untrusted"):
        return "N/A (data error)"
    return f"{float(payload['value']):+.0f}%"


def validate_interim_risk(entry: Any, stop: Any, measured_move: Any) -> dict[str, Any]:
    try:
        entry_f = float(entry)
        stop_f = float(stop)
        mm_f = float(measured_move)
    except (TypeError, ValueError):
        return {"valid": False, "reason": "missing valid entry/stop/measured move"}
    risk = entry_f - stop_f
    if entry_f <= 0 or risk <= 0:
        return {"valid": False, "reason": "missing valid entry/stop/measured move"}
    stop_pct = risk / entry_f * 100.0
    if stop_pct < STOP_MIN_PCT or stop_pct > STOP_MAX_PCT:
        return {
            "valid": False,
            "stop_pct": round(stop_pct, 1),
            "reason": f"stop {stop_pct:.1f}% -- no valid invalidation within cap",
        }
    rr = (mm_f - entry_f) / risk
    if rr <= 0:
        return {"valid": False, "stop_pct": round(stop_pct, 1), "reason": "missing valid R:R"}
    suggested_qty = int((INTERIM_CAPITAL * INTERIM_RISK_PCT) // risk)
    if suggested_qty <= 0:
        return {"valid": False, "stop_pct": round(stop_pct, 1), "reason": "position size is zero"}
    return {
        "valid": True,
        "stop_pct": round(stop_pct, 2),
        "rr": round(rr, 2),
        "suggested_qty": suggested_qty,
    }


def symbol_timing(conn, symbol: str, on_or_before: str) -> dict[str, Any]:
    sym = symbol.upper()
    bars = load_symbol_bars(conn, sym, on_or_before, 80)
    if not bars:
        return {"available": False, "symbol": sym, "as_of": None}

    latest = bars[-1]
    prior = bars[:-1]
    prior20 = prior[-20:]
    close = latest.get("close")
    open_ = latest.get("open")
    prev_close = latest.get("prev_close")
    if prev_close is None and prior:
        prev_close = prior[-1].get("close")

    prior_volumes = [float(b["volume"]) for b in prior20 if b.get("volume") not in (None, 0)]
    avg_vol = _avg(prior_volumes)
    rvol = (float(latest["volume"]) / avg_vol) if latest.get("volume") and avg_vol else None

    gap_pct = None
    if open_ is not None and prev_close:
        gap_pct = (float(open_) - float(prev_close)) / float(prev_close) * 100.0

    ranges = []
    for b in bars[-14:]:
        if b.get("high") is not None and b.get("low") is not None and b.get("close"):
            ranges.append((float(b["high"]) - float(b["low"])) / float(b["close"]) * 100.0)
    adr = _avg(ranges)

    prior_highs = [float(b["high"]) for b in prior20 if b.get("high") is not None]
    prior_lows = [float(b["low"]) for b in prior20 if b.get("low") is not None]
    pivot = max(prior_highs) if prior_highs else None
    stop = min(prior_lows) if prior_lows else None
    dist_pivot = None
    if close is not None and pivot:
        dist_pivot = (float(close) - pivot) / pivot * 100.0

    read_parts = []
    if rvol is not None:
        read_parts.append("RVOL building" if rvol >= 1.5 else "volume is not yet expanded")
    if dist_pivot is not None:
        if abs(dist_pivot) <= 1.0:
            read_parts.append("price is sitting near pivot")
        elif dist_pivot > 1.0:
            read_parts.append("price is extended above pivot")
        else:
            read_parts.append("price is still below pivot")
    if latest.get("delivery_pct") is not None:
        read_parts.append(
            "delivery is strong" if float(latest["delivery_pct"]) >= 60 else "delivery is ordinary"
        )

    return {
        "available": True,
        "symbol": sym,
        "as_of": latest["date"],
        "close": _round(close),
        "entry": _round(pivot),
        "pivot": _round(pivot),
        "stop": _round(stop),
        "rvol": _round(rvol),
        "gap_pct": _round(gap_pct),
        "dist_pivot": _round(dist_pivot),
        "adr": _round(adr),
        "delivery_pct": _round(latest.get("delivery_pct")),
        "read": "; ".join(read_parts) + "." if read_parts else "Not enough timing data yet.",
    }


def _most_recent_table_date(conn, table: str, date_col: str, on_or_before: str) -> str | None:
    """Latest `date_col` <= on_or_before that has rows in `table`.

    ChartsMaze-derived tables (screener_hits, symbol_quality, sector_metrics)
    can be stamped ahead of the latest bhavcopy/regime date (dated dump
    folders don't line up 1:1 with trade dates), so every read here resolves
    MOST-RECENT <= as_of rather than requiring an exact match — otherwise the
    feed goes empty on any date the dump folders don't exactly cover.
    """
    row = conn.execute(
        f"SELECT MAX({date_col}) AS d FROM {table} WHERE {date_col} <= ?",
        (on_or_before,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def confluence_pool(conn, on_or_before: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """The candidate pool: symbols with confluence_count >= MIN_CONFLUENCE,
    resolved from the most-recent screener_hits trade_date <= on_or_before.

    Returns (screener_date, {symbol: confluence_entry}) filtered to the
    confluence threshold. screener_date is None if no screener_hits rows
    exist on/before on_or_before (empty pool).
    """
    screener_date = _most_recent_table_date(conn, "screener_hits", "trade_date", on_or_before)
    if screener_date is None:
        return None, {}
    confluence = confluence_for_date(conn, screener_date)
    pool = {sym: entry for sym, entry in confluence.items() if entry["count"] >= MIN_CONFLUENCE}
    return screener_date, pool


def symbol_quality_map(conn, on_or_before: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """{symbol: symbol_quality row} as of the most-recent trade_date <= on_or_before."""
    quality_date = _most_recent_table_date(conn, "symbol_quality", "trade_date", on_or_before)
    if quality_date is None:
        return None, {}
    rows = conn.execute(
        "SELECT symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy, "
        "is_fno, exchange FROM symbol_quality WHERE trade_date = ?",
        (quality_date,),
    ).fetchall()
    return quality_date, {r["symbol"]: dict(r) for r in rows}


def sector_rs_quartile(conn, on_or_before: str) -> tuple[str | None, set[str]]:
    """Sector keys in the TOP quartile of sector_metrics.rs_score, resolved
    most-recent snapshot_date <= on_or_before. Returns (snapshot_date, set of
    top-quartile sector_key). Empty set if <4 sectors have an rs_score.
    """
    sec_date = _most_recent_table_date(conn, "sector_metrics", "snapshot_date", on_or_before)
    if sec_date is None:
        return None, set()
    rows = conn.execute(
        "SELECT sector_key, rs_score FROM sector_metrics "
        "WHERE snapshot_date = ? AND rs_score IS NOT NULL ORDER BY rs_score DESC",
        (sec_date,),
    ).fetchall()
    if len(rows) < 4:
        return sec_date, set()
    cutoff = max(1, len(rows) // 4)
    top = {r["sector_key"] for r in rows[:cutoff]}
    return sec_date, top


def market_mode_for(conn, on_or_before: str) -> tuple[str, bool]:
    """(market_mode, defaulted). No snapshot at all -> SELECTIVE with a
    defaulted flag (fresh DB / tests); the cascade's regime gate then only
    admits catalyst + base/pattern families — never permissive, never empty
    by accident. A real NO_TRADE snapshot still yields NO_TRADE."""
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (on_or_before,),
    ).fetchone()
    if row and row["market_mode"]:
        return str(row["market_mode"]).upper(), False
    return "SELECTIVE", True


def _index_return_63d(conn, index_symbol: str, on_or_before: str) -> float | None:
    rows = conn.execute(
        "SELECT close FROM sector_index_prices WHERE symbol = ? AND trade_date <= ? "
        "AND close IS NOT NULL ORDER BY trade_date DESC LIMIT 64",
        (index_symbol, on_or_before),
    ).fetchall()
    if len(rows) < 64 or not rows[-1]["close"]:
        return None
    return (float(rows[0]["close"]) - float(rows[-1]["close"])) / float(rows[-1]["close"]) * 100.0


def sector_adjusted_momentum(conn, bars: list[dict[str, Any]], sector_key: str | None,
                             on_or_before: str) -> float | None:
    """stock 63d return − sector-index 63d return (LOCKED rank tiebreak).

    Falls back to the NIFTYMIDSML400 benchmark, then to the raw stock return
    when no index history exists (thin sector_index_prices coverage)."""
    closes = [b.get("close") for b in bars if b.get("close")]
    if len(closes) < 64 or not closes[-64]:
        return None
    stock_ret = (float(closes[-1]) - float(closes[-64])) / float(closes[-64]) * 100.0
    bench = None
    if sector_key:
        idx_row = conn.execute(
            "SELECT DISTINCT symbol FROM sector_index_prices",
        ).fetchall()
        for r in idx_row:
            if canonical_sector_key(r["symbol"], "index") == sector_key:
                bench = _index_return_63d(conn, r["symbol"], on_or_before)
                break
    if bench is None:
        bench = _index_return_63d(conn, "NIFTYMIDSML400", on_or_before)
    return round(stock_ret - (bench or 0.0), 2)


# Discovery-sensitivity cap for detector_shortlist (NOT a refusal threshold --
# gates.py still refuses everything unqualified downstream; this only bounds
# query cost). Bug fix 2026-07-11: ~800-900 EQ names routinely clear the 85%-
# of-252d-high nearness bar, so the old limit=600 with `ORDER BY p.symbol`
# structurally dropped every S-Z ticker (verified: SKYGOLD ranked 705-778th,
# RAIN ranked 635-678th alphabetically, cut on every real entry-window date).
# 1200 comfortably covers the routine 800-900 qualifiers with headroom, and
# the sort key below now drops the WEAKEST names (lowest nearness to 252d
# high) if the cap ever does bite, instead of dropping by ticker letter.
DETECTOR_SHORTLIST_LIMIT = 1200


def detector_shortlist(conn, price_date: str, limit: int = DETECTOR_SHORTLIST_LIMIT) -> list[str]:
    """OHLCV pool: EQ names within 15% of their 252d high on price_date.

    This is what makes the feed + replay work on sessions with no ChartsMaze
    dump (LEARNINGS 2026-07-06): nearness>=0.85 is already a cascade gate, so
    pre-filtering on it is lossless for non-catalyst setups.

    ORDER BY nearness (p.close / mx.hi) DESC, not p.symbol: if the cap ever
    binds, it must drop the names FARTHEST from their 252d high (weakest),
    never a whole alphabetic tail (see DETECTOR_SHORTLIST_LIMIT comment)."""
    rows = conn.execute(
        "SELECT p.symbol FROM daily_prices p JOIN ("
        "  SELECT symbol, MAX(high) AS hi FROM daily_prices "
        "  WHERE series='EQ' AND trade_date <= ? AND trade_date >= date(?, '-372 days') "
        "  GROUP BY symbol) mx ON mx.symbol = p.symbol "
        "WHERE p.series='EQ' AND p.trade_date = ? AND p.close IS NOT NULL "
        "AND mx.hi > 0 AND p.close >= 0.85 * mx.hi "
        "ORDER BY (p.close / mx.hi) DESC LIMIT ?",
        (price_date, price_date, price_date, limit),
    ).fetchall()
    return [r["symbol"] for r in rows]


def discovery_bucket_map(conn, price_date: str) -> dict[str, dict[str, Any]]:
    """WAVE_M M2: {symbol: {"archetypes": [...], "metrics": {...}}} for every
    member of discovery.build_bucket on `price_date`, called directly (see
    module docstring) so it is available regardless of pipeline stage order
    or replay context. Pure read; never writes."""
    try:
        bucket = discovery.build_bucket(conn, price_date)
    except Exception:  # noqa: BLE001 — the live pool must never go dark because
        # the bucket computation hit an edge case; fall back to the
        # pre-M2 pool (confluence + detector_shortlist) for that scan.
        return {}
    # Anticipation WATCH is a distinct pre-trigger lane. It must not be added
    # to the candidate/refusal cascade by the discovery safety-net union.
    return {
        entry["symbol"]: entry for entry in bucket
        if entry.get("classification") != "WATCH"
    }


def watch_lane_entries(conn, price_date: str) -> list[dict[str, Any]]:
    """The Anticipation WATCH lane (discovery.build_bucket classification==
    'WATCH') — pre-trigger names deliberately excluded from the gate/
    candidate cascade above (discovery_bucket_map's own rule: "must not be
    added to the candidate/refusal cascade"). Returns raw bucket entries
    (symbol/classification/archetypes/metrics). Pure read; never writes, and
    never feeds scan_candidates/refusals — a WATCH name has no entry/stop/R:R
    and stays that way here."""
    try:
        bucket = discovery.build_bucket(conn, price_date)
    except Exception:  # noqa: BLE001 — mirrors discovery_bucket_map's own
        # fail-safe: a bucket computation edge case must not crash the caller.
        return []
    return [e for e in bucket if e.get("classification") == "WATCH"]


def watch_lane_conviction(conn, price_date: str) -> list[dict[str, Any]]:
    """Conviction score for each WATCH-lane name (WAVE E1 union, coordinator
    correction 2026-07-22 — evidence: a 53-name practitioner leaders list put
    22/53 in WATCH at a 2-day median +2.95% vs the gate-passed SCAN lane's
    +1.10%; a top-15 built only from scan_candidates survivors structurally
    excludes the best-performing cohort). Computed WITHOUT running the
    refusal cascade (regime/tradability/participation/risk do not apply to a
    name that hasn't triggered — there is no entry/stop yet); nearness_52w
    and extension_21 are pulled cheaply from gate_trend_template/gate_
    fresh_leg directly (the same fields candidate_for_symbol reads off the
    full cascade), not by re-running the whole gate stack.

    Rails: this NEVER writes to scan_candidates/refusals and produces no
    stop/size/R:R — risk/plan.py remains the only sizing authority. Each
    entry is tagged lane='watch' and action='armed, waiting for trigger --
    no size until it triggers' so a caller can never mistake it for a sized
    plan.
    """
    out: list[dict[str, Any]] = []
    for bucket_entry in watch_lane_entries(conn, price_date):
        sym = bucket_entry["symbol"]
        bars = load_symbol_bars(conn, sym, price_date, 260)
        if not bars:
            continue
        timing = symbol_timing(conn, sym, price_date)
        if not timing.get("available"):
            continue
        archetypes = list(bucket_entry.get("archetypes") or [])
        setup_type = setup_type_from_discovery_archetypes(archetypes) or "watchlist_timing"
        family = setup_family(setup_type)
        breakout_age = _compute_breakout_age(bars, timing.get("pivot"))
        tt_evidence = (gates.gate_trend_template(bars, family, None).get("evidence") or {})
        fl_evidence = (
            gates.gate_fresh_leg(bars, timing.get("pivot"), breakout_age, setup_family=family).get("evidence")
            or {}
        )
        components = {
            "setup_type": setup_type,
            "tier_evidence": {
                "breakout_age": breakout_age, "close": timing.get("close"),
                "pivot": timing.get("pivot"), "extension_21": fl_evidence.get("extension_21"),
            },
            "day_rvol": timing.get("rvol"),
            "ud_ratio": conviction.ud_ratio(bars),
            "nearness_52w": tt_evidence.get("nearness_52w"),
            "pct_up_from_65d_low": discovery_metrics.pct_up_from_65d_low(bars),
            "featured_in": conviction.featured_in(conn, sym, timing["as_of"]),
            "theme": conviction.theme_membership(conn, sym, timing["as_of"]),
        }
        result = conviction.conviction_score(components)
        out.append({
            "symbol": sym.upper(), "lane": "watch", "setup_type": setup_type,
            "setup_family": family, "archetypes": archetypes,
            "conviction_score": result["score"], "conviction_axes": result["axes"],
            "conviction_why": result["why"],
            "action": "armed, waiting for trigger -- no size until it triggers",
        })
    return out


def conviction_leaderboard(conn, scan_date: str, top_n: int = CONVICTION_TOP_N) -> dict[str, Any]:
    """WAVE E1 union leaderboard (coordinator correction 2026-07-22): the
    TOP-N by conviction_score across (a) today's gate-passed scan survivors
    (lane='scan', persisted scan_candidates rows — sized plans, entirely
    unaffected) and (b) the WATCH lane (lane='watch' — informational only,
    never sized, never persisted). The gate itself stays unchanged either
    way: this only RANKS a union for display, it does not admit a WATCH name
    into scan_candidates/refusals or size it.

    Requires scan_date to already be scanned (candidates.run()/
    persist_candidates() called first) — this reads scan_candidates, it does
    not run the cascade itself.
    """
    scan_rows = conn.execute(
        "SELECT symbol, setup_type, conviction_score, conviction_axes_json "
        "FROM scan_candidates WHERE scan_date = ?", (scan_date,),
    ).fetchall()
    entries: list[dict[str, Any]] = []
    for r in scan_rows:
        payload = json.loads(r["conviction_axes_json"] or "{}") if r["conviction_axes_json"] else {}
        entries.append({
            "symbol": r["symbol"], "lane": "scan", "setup_type": r["setup_type"],
            "conviction_score": r["conviction_score"] if r["conviction_score"] is not None else 0.0,
            "conviction_axes": payload.get("axes") or {}, "conviction_why": payload.get("why") or [],
            "action": "sized plan available",
        })
    entries.extend(watch_lane_conviction(conn, scan_date))
    entries.sort(key=lambda e: e["conviction_score"], reverse=True)
    for i, e in enumerate(entries, start=1):
        e["leaderboard_rank"] = i if i <= top_n else None
    return {
        "scan_date": scan_date, "entries": entries,
        "top": [e for e in entries if e["leaderboard_rank"]],
    }


def ensure_refusals_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS refusals ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_family TEXT, "
        "failed_gate TEXT NOT NULL, reason TEXT, evidence_json TEXT, "
        "ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )


def _refuse(conn, refusals: list, scan_date: str, symbol: str, family: str | None,
            gate_name: str, reason: str | None, evidence: Any = None) -> None:
    refusals.append({"symbol": symbol, "setup_family": family, "failed_gate": gate_name,
                     "reason": reason})
    conn.execute(
        "INSERT OR REPLACE INTO refusals (scan_date, symbol, setup_family, failed_gate, "
        "reason, evidence_json) VALUES (?, ?, ?, ?, ?, ?)",
        (scan_date, symbol.upper(), family, gate_name, reason,
         json.dumps(evidence) if evidence is not None else None),
    )


def _most_recent_stock_rs_date(on_or_before: str) -> str | None:
    root = chartsmaze.chartsmaze_dir()
    if not root.is_dir():
        return None
    candidates = []
    for child in root.iterdir():
        if not child.is_dir() or child.name > on_or_before:
            continue
        path = child / "analytics" / "sector-analytics-Relative Strength-stocks.csv"
        if path.is_file():
            candidates.append(child.name)
    return max(candidates) if candidates else None


def stock_rs_map(on_or_before: str) -> dict[str, dict[str, Any]]:
    run_date = _most_recent_stock_rs_date(on_or_before)
    if run_date is None:
        return {}
    try:
        df = chartsmaze.read_stock_relative_strength(run_date)
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        industry = str(row.get("industry") or "").strip()
        rs = row.get("rs")
        out[ticker] = {
            "rs": None if rs is None else float(rs),
            "rs_as_of": run_date,
            "industry": industry or None,
            "sector": INDUSTRY_TO_SECTOR.get(industry),
        }
    return out


def grade(readiness: float) -> str:
    if readiness >= 90:
        return "A+"
    if readiness >= 75:
        return "A"
    if readiness >= 60:
        return "B"
    return "C"


def _confluence_component(count: int) -> float:
    """More screeners = stronger. Capped at 30 (count 4+ saturates)."""
    return min(30.0, count * 7.5)


def _theme_component(sector_key: str | None, top_quartile: set[str]) -> float:
    """15pt boost when the symbol's sector is in the sector_metrics top quartile."""
    if sector_key and sector_key in top_quartile:
        return 15.0
    return 0.0


def _earnings_component(quality: dict[str, Any] | None) -> float:
    """Up to 15: 8 for eps_yoy>0, 7 for eps_qoq>0."""
    if not quality:
        return 0.0
    score = 0.0
    eps_yoy = trusted_growth_value(quality, "eps_yoy")
    eps_qoq = trusted_growth_value(quality, "eps_qoq")
    if eps_yoy is not None and eps_yoy > 0:
        score += 8.0
    if eps_qoq is not None and eps_qoq > 0:
        score += 7.0
    return score


def _delivery_component(delivery_pct: float | None) -> float:
    """Up to 10, scaled from delivery_pct."""
    if delivery_pct is None:
        return 0.0
    if delivery_pct >= 60:
        return 10.0
    if delivery_pct >= 40:
        return 5.0
    return 0.0


def _rs_component(rs_rating: float | None) -> float:
    """Up to 15, linear 0-100 -> 0-15."""
    if rs_rating is None:
        return 0.0
    return max(0.0, min(15.0, rs_rating / 100.0 * 15.0))


def _percentile(value: float | None, values: list[float]) -> float | None:
    if value is None or not values:
        return None
    below = sum(1 for v in values if v <= value)
    return round(below / len(values) * 100.0, 1)


def absolute_strength_percentiles(conn, on_or_before: str) -> dict[str, float]:
    """Own-price 63-session momentum percentile across the EQ universe.

    Single window-function query (was one query PER symbol — ~2,400/session —
    which made historical replay time out; see LEARNINGS 2026-07-06)."""
    date_row = conn.execute(
        "SELECT MAX(trade_date) AS d FROM daily_prices WHERE series='EQ' AND trade_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not date_row or not date_row["d"]:
        return {}
    latest_date = date_row["d"]
    rows = conn.execute(
        "WITH ranked AS ("
        "  SELECT symbol, close, ROW_NUMBER() OVER "
        "    (PARTITION BY symbol ORDER BY trade_date DESC) AS rn "
        "  FROM daily_prices WHERE series='EQ' AND trade_date <= ? AND close IS NOT NULL"
        ") "
        "SELECT a.symbol, a.close AS c0, b.close AS c63 FROM ranked a "
        "JOIN ranked b ON b.symbol = a.symbol AND b.rn = 64 WHERE a.rn = 1 AND b.close > 0",
        (latest_date,),
    ).fetchall()
    raw = {r["symbol"]: (float(r["c0"]) - float(r["c63"])) / float(r["c63"]) * 100.0 for r in rows}
    vals = list(raw.values())
    return {sym: pct for sym, value in raw.items() if (pct := _percentile(value, vals)) is not None}


def eps_growth_percentiles(quality_map: dict[str, dict[str, Any]]) -> dict[str, float]:
    values = [v for q in quality_map.values() if (v := trusted_growth_value(q, "eps_yoy")) is not None]
    return {
        sym: pct
        for sym, q in quality_map.items()
        if (pct := _percentile(trusted_growth_value(q, "eps_yoy"), values)) is not None
    }


_TRIGGER_KINDS = {"POCKET_PIVOT", "SHAKEOUT"}


def _signal_component(latest_signals: list[dict[str, Any]]) -> tuple[float, str | None]:
    """10pts if a price-action trigger fired on the as-of date. Returns
    (points, signal_label) — signal_label feeds score_breakdown."""
    for sig in latest_signals:
        kind = sig.get("kind")
        if kind in _TRIGGER_KINDS or "TOUCH" in (kind or "") or "RECLAIM" in (kind or ""):
            return 10.0, kind
    return 0.0, None


def candidate_for_symbol(
    conn,
    symbol: str,
    on_or_before: str,
    confluence_entry: dict[str, Any],
    quality: dict[str, Any] | None,
    top_quartile_sectors: set[str],
    rs_info: dict[str, Any] | None = None,
    absolute_strength_pctile: float | None = None,
    eps_growth_pctile: float | None = None,
    market_mode: str = "SELECTIVE",
    universe_verdict: dict[str, Any] | None = None,
    discovery_entry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build one candidate through the FULL cascade. Returns a survivor dict
    (rank assigned later by scan_candidates), a refusal dict ({refused: True,
    failed_gate, drop_reason, gates}), or None when no timing data exists.
    """
    timing = symbol_timing(conn, symbol, on_or_before)
    if not timing.get("available"):
        return None
    bars = load_symbol_bars(conn, symbol, timing["as_of"], 260)
    state = price_action.signals_for_symbol(conn, symbol, timing["as_of"], max_bars=180)
    latest_signals = [s for s in state["recent_signals"] if s.get("date") == timing["as_of"]]

    evidence: list[dict[str, Any]] = []
    append_footprint_evidence(conn, symbol, timing["as_of"], evidence)
    setup = "Watchlist timing"
    setup_type = "watchlist_timing"
    pattern_label = None
    base_age = None
    days_since_listing = None

    # Confluence + theme + ASM-clear + earnings evidence chips.
    # Only surface screener names with a recognized FAMILY (pattern/catalyst/
    # momentum/accumulation) as individual evidence — ChartsMaze also includes
    # ad-hoc personal screens (arbitrary user-named screens with no family) in
    # this list, which read as meaningless codenames to a trader and add no
    # decision value beyond the confluence count already shown separately.
    screeners = confluence_entry.get("screeners") or []
    screeners = ["vcp-loose" if str(name).lower() in {"tight-setup", "tight_setup", "chartsmaze-tight"} else name for name in screeners]
    named_screeners = [s for s in screeners if SCREENER_FAMILY.get(str(s).lower())]
    for name in named_screeners[:6]:
        evidence.append({"filter": name, "value": "hit"})

    # WAVE_M M2: discovery.build_bucket archetype(s) — setup-family evidence
    # for names the sensitive bucket tagged (whether or not ChartsMaze
    # confluence also hit them). Symbols the bucket didn't tag get an empty
    # list, no chip.
    discovery_archetypes = _candidate_discovery_archetypes(bars, discovery_entry)
    if discovery_archetypes:
        evidence.append({"filter": "discovery-archetype", "value": ", ".join(discovery_archetypes)})

    industry = confluence_entry.get("basic_industry") or (rs_info or {}).get("industry")
    sector_key = canonical_sector_key(industry, "chartsmaze") if industry else None
    theme_tag = None
    if sector_key:
        top = sector_key in top_quartile_sectors
        theme_tag = f"{display_label(sector_key)}" + (" (top-quartile)" if top else "")
        evidence.append({"filter": "theme", "value": theme_tag})

    if quality is not None and quality.get("asm_stage") is None:
        evidence.append({"filter": "ASM-clear", "value": "yes"})

    growth = growth_payloads(quality)
    eps_yoy = trusted_growth_value(quality, "eps_yoy")
    if eps_yoy is not None and eps_yoy > 0:
        evidence.append({"filter": "EPS YoY", "value": format_growth_value(eps_yoy)})

    if timing.get("delivery_pct") is not None and timing["delivery_pct"] >= 60:
        evidence.append({"filter": "delivery>=60", "value": f"{timing['delivery_pct']:.0f}%"})
    if timing.get("rvol") is not None and timing["rvol"] >= 1.5:
        evidence.append({"filter": "rvol>=1.5", "value": f"{timing['rvol']:.2f}x"})
    if timing.get("dist_pivot") is not None and abs(timing["dist_pivot"]) <= 3:
        evidence.append({"filter": "near-pivot", "value": f"{timing['dist_pivot']:+.1f}%"})
        setup = "Near pivot"
        setup_type = "near_pivot"

    for sig in latest_signals[:3]:
        evidence.append({"filter": sig["kind"], "value": sig["detail"]})
        if sig["kind"] == "POCKET_PIVOT":
            setup = "Pocket pivot"
            setup_type = "pocket_pivot"
        elif sig["kind"] == "SHAKEOUT":
            setup = "Shakeout"
            setup_type = "shakeout"
        elif "TOUCH" in sig["kind"]:
            setup = "Pullback-to-EMA"
            setup_type = "pullback"

    rs_rating = confluence_entry.get("rs_rating")
    rs = rs_rating if rs_rating is not None else (None if not rs_info else rs_info.get("rs"))
    if rs is not None and rs >= 70:
        evidence.append({"filter": "rs>=70", "value": f"{rs:.0f}"})

    launch = eod_detectors.launch_pad(bars)
    if launch:
        setup = launch["label"]
        setup_type = launch["setup"]
        evidence.append({"filter": "launch-pad", "value": "MA cluster"})

    ants = eod_detectors.ants_accumulation(bars)
    if ants:
        evidence.append({"filter": ants["filter"], "value": ants["value"]})

    detector_quality = dict(quality or {})
    for field in GROWTH_FIELDS:
        payload = growth.get(field)
        if payload and payload.get("untrusted"):
            detector_quality[field] = None
    ep = eod_detectors.earnings_power(bars, detector_quality)
    if ep:
        setup = ep["label"]
        setup_type = ep["setup"]
        pattern_label = "Earnings Power gap"
        evidence.append({"filter": "EP", "value": "30% growth + gap"})

    listing = eod_detectors.listing_status(conn, symbol, timing["as_of"])
    ipo = eod_detectors.ipo_base(bars, listing)
    if ipo:
        setup = "IPO Base"
        setup_type = "ipo_base"
        pattern_label = ipo["label"]
        days_since_listing = listing.get("days_since_listing")
        timing["stop"] = ipo["stop"]
        evidence.append({"filter": "IPO base", "value": ipo["label"]})

    if absolute_strength_pctile is not None:
        evidence.append({"filter": "abs-strength", "value": f"{absolute_strength_pctile:.0f} pctile"})
    if eps_growth_pctile is not None:
        evidence.append({"filter": "eps-growth", "value": f"{eps_growth_pctile:.0f} pctile"})

    discovery_setup_type = setup_type_from_discovery_archetypes(discovery_archetypes)
    if discovery_setup_type and (
        setup_type in {"watchlist_timing", "near_pivot"}
        # A momentum-labelled signal day (pocket pivot / shakeout / pullback
        # tag) on a name whose DISCOVERY admission is a reversal-class
        # archetype IS that reversal's trigger day — the reversal context
        # must govern the gates, or the trend-template hard-refuses the very
        # structure discovery admitted (DAMCAPITAL 07-16 autopsy: long_tail
        # rejection bar re-labelled momentum → refused below the 200SMA).
        or (
            setup_family(discovery_setup_type) in {"reversal", "busted_reversal"}
            and setup_family(setup_type) in {"momentum", "base/pattern"}
        )
    ):
        setup_type = discovery_setup_type
        setup = discovery_setup_type.replace("_", " ").title()

    # --- rank inputs (NOT a score): delivery_z, sector-adjusted momentum,
    # confluence FAMILIES — the LOCKED ordinal-rank tiebreak ---
    confluence_count = confluence_entry.get("count", 0)
    _, signal_label = _signal_component(latest_signals)
    family = setup_family(setup_type)
    # A contracted coil day deliberately carries no delivery penalty: neither
    # a hard gate/objection nor the ordinal delivery-z tiebreak may bury it.
    dz = 0.0 if gates.is_contracted_range(bars) else gates.delivery_z(bars)
    sam = sector_adjusted_momentum(conn, bars, sector_key, timing["as_of"])
    families = confluence_families(screeners, setup_type)
    components = {
        "confluence": confluence_count,
        "confluence_families": families,
        "delivery_z": None if dz is None else round(dz, 2),
        "sector_adj_momentum": sam,
        "theme": theme_tag,
        "eps_yoy": eps_yoy,
        "growth": growth,
        "rs": rs,
        "delivery": timing.get("delivery_pct"),
        "signal": signal_label,
        "ants": bool(ants),
        "setup_type": setup_type,
        "setup_family": family,
        "abs_strength_pctile": absolute_strength_pctile,
        "eps_growth_pctile": eps_growth_pctile,
    }

    # --- risk plan: risk/plan.py is the single writer of stop/size/R:R ---
    entry = timing.get("entry")
    chosen = risk_plan.choose_stop(bars, family, float(entry)) if entry else None
    stop = chosen["stop"] if chosen else timing.get("stop")
    if ipo:  # IPO hard <=4% day-low stop stays authoritative
        stop = timing.get("stop")
    timing["stop"] = stop

    # --- structural measured move (single writer: risk_plan.structural_target).
    # Replaces the old `entry + 2*risk` synthetic projection that made every
    # R:R uniformly 2.0 and so the R:R>=1.5 floor never bit (LEARNINGS T1.6).
    # Computed BEFORE validate() so the floor actually gates on the real level.
    measured_move = None
    measured_move_note = None
    if entry and stop and entry > stop:
        st = risk_plan.structural_target(bars, float(entry), float(stop), setup_type or family)
        # A discovery D2/EP setup is a gap setup even when its opening gap is
        # smaller than the standalone >=5% gap detector threshold (NUVOCO is
        # the regression case). Other setup types still require a real >=5% gap.
        is_gap_setup = (
            setup_type in GAP_PROJECTION_SETUP_TYPES
            or "d2_episodic" in discovery_archetypes
        )
        min_gap_pct = 0.0 if is_gap_setup else 5.0
        gap_projection = ep_box_projection(bars, float(entry), min_gap_pct=min_gap_pct)
        if gap_projection is not None:
            # Actual gap structure is authoritative regardless of whether the
            # setup reached us as literal `ep` or through a discovery gap tag.
            st = gap_projection
        elif st is None or st.get("synthetic"):
            trail_managed = (setup_type or family or "").lower() in TRAIL_MANAGED_SETUP_TYPES
            st = leader_measured_move_projection(
                bars, float(entry), float(stop), timing.get("pivot"),
                trail_managed=trail_managed,
            ) or st
        if st is not None:
            measured_move = st["target"]
            if not st.get("synthetic"):
                measured_move_note = (
                    f"Measured move = {st['method']} — prior resistance the trade "
                    "races toward, not a promise."
                )
            elif (setup_type or family or "").lower() in TRAIL_MANAGED_SETUP_TYPES:
                # WAVE_L 2026-07-21 (RAIN/SKIPPER/NUVOCO Monday-open refusal-
                # class fix): trail-managed setups (momentum/catalyst/reversal/
                # pullback/persistent_momentum/watchlist_timing etc — no fixed
                # target in the corpus, trail 10/21EMA and ride) get a
                # computable estimate instead of "R:R unknowable": current-leg
                # height or 2x ADR20 when the open-sky projection can compute
                # one (leader_measured_move_projection, trail_managed=True),
                # else the flat +15% continuation checkpoint
                # (risk_plan.structural_target tier 4). Either way the R:R
                # floor below evaluates against a REAL number — refusal is
                # honest, not a data gap.
                measured_move_note = (
                    "Target = trail-managed — no fixed target; estimate for R:R "
                    "only, manage by 10/21EMA trail."
                )
            else:
                measured_move_note = (
                    f"Measured move = {st['method']} "
                    "(projected — no overhead resistance visible; leg/volatility method)."
                )
        else:
            measured_move_note = "No structural target visible — R:R unknowable; refused by the risk gate."

    profile_record = risk_plan.get_trader_profile(conn)
    research_sizing = {}
    if not profile_record.get("profile_confirmed_at") or not profile_record.get("account_capital"):
        # Scanning is research, so an unfinished onboarding profile must not
        # erase otherwise-valid setups. Use conservative LEARNING assumptions;
        # the live/manual trade path still calls validate without this override
        # and therefore refuses sizing until the profile is confirmed.
        research_sizing = {"profile": "learning", "account_capital": risk_plan.capital(conn)}
    plan_result = risk_plan.validate(
        entry=float(entry) if entry else 0.0,
        stop=float(stop) if stop else 0.0,
        measured_move=measured_move,
        regime=market_mode,
        setup_family=setup_type or "",
        sector=sector_key,
        conn=conn,
        adr_pct=timing.get("adr"),
        **research_sizing,
    )
    if (
        plan_result.get("pass")
        and timing.get("adr")
        and plan_result.get("stop_pct") is not None
        and plan_result["stop_pct"] > 0.75 * timing["adr"] * 1.0
    ):
        evidence.append({
            "filter": "wide-stop-vs-ADR",
            "value": f"stop {plan_result['stop_pct']:.1f}% vs ADR {timing['adr']:.1f}%",
        })

    # --- one symbol = one opinion: exit_state reconciliation ---
    exit_info = eod_detectors.exit_state(bars)

    # --- the cascade ---
    breakout_age = _compute_breakout_age(bars, timing.get("pivot"))
    cascade = gates.run_cascade({
        "bars": bars, "symbol": symbol, "setup_family": family,
        "market_mode": market_mode, "quality": quality,
        "universe_verdict": universe_verdict, "rs_rating": rs,
        "pivot": timing.get("pivot"), "breakout_age": breakout_age,
        "breakout_day_entry": setup_type in ("pocket_pivot", "ep"),
        "plan_result": plan_result,
        # WAVE_J J6: enforce_staleness=False keeps the newly-live staleness
        # branch of gate_fresh_leg a SHADOW-ONLY evidence recorder (see
        # gates.gate_fresh_leg docstring) — zero behavior change vs the
        # breakout_age=None baseline; the refusal ledger starts recording
        # real leg-age via evidence["would_refuse_stale"].
        "enforce_staleness": False,
    })
    if exit_info["state"] == "Broken" and cascade["passed"]:
        # Episodic exception: an EP/D2 burst (>=10% day on the last 1-2 bars)
        # RESETS structure — the Broken read was authored on the pre-episode
        # downtrend and is stale evidence against a brand-new leg (HIRECT
        # 07-15/16 autopsy: +19.9% D1 on 13x RVOL refused as "Broken").
        # Rides as a weighted objection instead of a veto; all other families
        # keep the hard one-opinion refusal.
        if setup_type in GAP_PROJECTION_SETUP_TYPES and _recent_burst(bars):
            cascade.setdefault("objections", []).append({
                "code": "exit_broken_pre_episode", "gate": "one-opinion",
                "reason": ("exit engine read Broken on the pre-episode structure; "
                           "the EP burst resets the leg — treat as elevated risk, "
                           "not a veto"),
                "weight": 1.25,
            })
        else:
            cascade = {"passed": False, "failed_at": "one-opinion",
                       "reasons": ["exit state is Broken — a name flashing structural exits "
                                   "cannot also be a fresh entry"], "gates": cascade["gates"],
                       "objections": cascade.get("objections") or []}
    if not cascade["passed"]:
        return {
            "symbol": symbol.upper(), "refused": True,
            "setup_family": family, "setup_type": setup_type,
            "failed_gate": cascade["failed_at"],
            "drop_reason": (cascade["reasons"] or [None])[0],
            "gates": cascade["gates"],
            # M3: objections a name carried on its way to a HARD refusal still
            # ride into the refusals ledger's evidence_json (see _refuse()).
            "objections": cascade.get("objections") or [],
            "entry": entry, "stop": stop, "measured_move": measured_move,
        }

    # M3: scored objections (RS floor / 52w nearness / regime family-kill) —
    # the candidate already passed the cascade; each objection subtracts a
    # named weight from the ordinal rank (below) and, on its own, caps the
    # grade at B — visible, never a silent exclusion.
    objections = cascade.get("objections") or []
    objection_penalty = sum(float(o.get("weight") or 0.0) for o in objections)
    for obj in objections:
        evidence.append({"filter": f"objection:{obj.get('code')}", "value": obj.get("reason")})
    components["objections"] = objections
    components["discovery_archetypes"] = discovery_archetypes

    # --- WAVE E1 conviction score (CONVICTION_RANK_SPEC_2026-07-21.md) ---
    # Computed for every SURVIVOR (the gate is unchanged -- conviction only
    # orders survivors). Reuses already-computed cascade evidence
    # (nearness_52w from trend-template, extension_21 from fresh-leg) rather
    # than re-deriving them -- one writer per number.
    gate_evidence_by_name = {g["gate"]: (g.get("evidence") or {}) for g in cascade["gates"]}
    nearness_52w = gate_evidence_by_name.get("trend-template", {}).get("nearness_52w")
    extension_21 = gate_evidence_by_name.get("fresh-leg", {}).get("extension_21")
    conviction_components = {
        "setup_type": setup_type,
        "tier_evidence": {
            "breakout_age": breakout_age,
            "close": timing.get("close"),
            "pivot": timing.get("pivot"),
            "extension_21": extension_21,
        },
        "day_rvol": timing.get("rvol"),
        "ud_ratio": conviction.ud_ratio(bars),
        "nearness_52w": nearness_52w,
        "pct_up_from_65d_low": discovery_metrics.pct_up_from_65d_low(bars),
        "featured_in": conviction.featured_in(conn, symbol, timing["as_of"]),
        "theme": conviction.theme_membership(conn, symbol, timing["as_of"]),
    }
    conviction_result = conviction.conviction_score(conviction_components)
    components["chart_fit"] = conviction.chart_fit_grade(bars)

    # One-opinion grade cap: only REAL weakness (or a live M3 objection) caps
    # the grade. Mere below-21EMA is the entry condition of a pullback, not a
    # conflict — capping on it made every pullback grade B (QC 2026-07-06).
    _real_weakness = {"distribution-days", "distribution-cluster", "lower-low",
                      "downside-reversal-bar", "crossed-below-21EMA"}
    weak_rules = {r["rule"] for r in exit_info["fired_rules"]} & _real_weakness
    grade_cap = "B" if (objections or (exit_info["state"] == "Weakening" and weak_rules)) else None
    if grade_cap and exit_info["state"] == "Weakening" and weak_rules:
        evidence.append({"filter": "exit-conflict",
                         "value": f"entry conflicts with weakness ({', '.join(sorted(weak_rules))}) — grade capped at B"})

    plan = eod_detectors.trade_plan(setup_type or setup, entry, stop, measured_move)
    if plan is not None:
        plan["suggested_qty"] = plan_result["qty"]
        plan["position_size_source"] = (
            f"{plan_result['risk_pct_used']}% risk ({risk_plan.active_profile(conn)} profile)")

    return {
        "symbol": symbol.upper(),
        "setup": setup,
        "setup_type": setup_type,
        "setup_family": family,
        "pattern_label": pattern_label,
        # rank + readiness(=rank percentile) are assigned by scan_candidates
        "readiness": None,
        "grade": None,
        "grade_cap": grade_cap,
        # M3: the objection penalty subtracts from the primary ordinal-rank
        # key only (dz stays the pure metric in score_breakdown/boost calc
        # below) — an objection pushes a name down the rank without
        # excluding it or double-penalizing the grade-boost eligibility.
        "rank_inputs": ((dz if dz is not None else -99.0) - objection_penalty,
                        sam if sam is not None else -999.0,
                        families),
        "objections": objections,
        "discovery_archetypes": discovery_archetypes,
        "gates": cascade["gates"],
        "exit_state": exit_info["state"],
        "rs": rs,
        "rs_as_of": None if not rs_info else rs_info.get("rs_as_of"),
        "delivery_pct": timing.get("delivery_pct"),
        "delivery_as_of": timing.get("as_of"),
        "pivot": timing.get("pivot"),
        "entry": entry,
        "stop": stop,
        "measured_move": measured_move,
        "rr": plan_result["rr"],
        "suggested_qty": plan_result["qty"],
        "risk_pct_used": plan_result["risk_pct_used"],
        # WAVE_L: surface the ACTUAL basis (structural level vs. synthetic
        # ATR projection vs. trail-continuation) instead of one generic
        # sentence — the trade-plan screen needs to show WHY this target,
        # not just that one exists (measured_move_note computed above, the
        # single writer being risk_plan.structural_target).
        "measured_move_note": measured_move_note,
        "confluence_count": confluence_count,
        "score_breakdown": components,
        "conviction_score": conviction_result["score"],
        "conviction_axes": conviction_result["axes"],
        "conviction_why": conviction_result["why"],
        "evidence": evidence,
        "read": f"{setup}: " + "; ".join(f"{e['filter']} {e['value']}" for e in evidence[:3]) + ".",
        "timing": timing,
        "base_age": base_age,
        "days_since_listing": days_since_listing,
        "trade_plan": plan,
        "sector": sector_key,
        "industry": industry,
    }


def _assign_ranks(candidates: list[dict[str, Any]]) -> None:
    """Ordinal rank 1..M, primary-sorted by CONVICTION SCORE desc (WAVE E1,
    CONVICTION_RANK_SPEC_2026-07-21.md), keeping the pre-conviction ordinal
    key -- (objection-adjusted delivery_z, sector-adjusted momentum,
    confluence families) -- as deterministic tiebreaks, unchanged in meaning.
    readiness = rank percentile (backward-compat only). Grades (LOCKED):
    A+ = top-3 AND >=2 boosts · A = any boost · B = passed. exit-state
    Weakening caps at B (grade_cap).

    conviction_rank marks the TOP CONVICTION_TOP_N (15) of this same
    ordering (1..15); everyone else keeps `rank` but conviction_rank stays
    None -- "cleared the gate, lower conviction" display is another lane's
    concern, not a second gate here (rails: conviction only orders
    survivors, never admits/refuses)."""
    candidates.sort(
        key=lambda c: ((c.get("conviction_score") if c.get("conviction_score") is not None else -1.0),)
        + c["rank_inputs"],
        reverse=True,
    )
    m = len(candidates)
    for i, c in enumerate(candidates, start=1):
        c["rank"] = i
        c["rank_of"] = m
        c["readiness"] = round((m - i + 1) / m * 100.0, 1)
        c["conviction_rank"] = i if i <= CONVICTION_TOP_N else None
        comp = c.get("score_breakdown") or {}
        boosts = sum([
            1 if (comp.get("delivery_z") or 0) >= 1.5 else 0,
            1 if comp.get("theme") and "top-quartile" in str(comp.get("theme")) else 0,
            1 if c.get("setup_family") == "catalyst" or comp.get("signal") else 0,
        ])
        if i <= 3 and boosts >= 2:
            g = "A+"
        elif boosts >= 1:
            g = "A"
        else:
            g = "B"
        if c.get("grade_cap") == "B" and g in ("A+", "A"):
            g = "B"
        c["grade"] = g
        c.pop("rank_inputs", None)


def scan_candidates_deterministic(conn, on_or_before: str, scan_limit: int | None = None) -> dict[str, Any]:
    """Fallback deterministic scan cascade."""
    price_date = latest_price_date(conn, on_or_before)
    if price_date is None:
        return {
            "available": False, "as_of": None, "candidates": [],
            "reason": f"No EQ daily_prices on or before {on_or_before}.",
        }
    ensure_refusals_schema(conn)
    conn.execute("DELETE FROM refusals WHERE scan_date = ?", (price_date,))

    screener_date, pool = confluence_pool(conn, on_or_before)
    market_mode, mode_defaulted = market_mode_for(conn, price_date)
    _, quality_map = symbol_quality_map(conn, on_or_before)
    quality_map = {
        sym: {**quality, **fundamentals.growth_for(conn, sym, on_or_before, quality)}
        for sym, quality in quality_map.items()
    }
    _, top_quartile = sector_rs_quartile(conn, on_or_before)
    rs_map = stock_rs_map(on_or_before)
    abs_strength = absolute_strength_percentiles(conn, price_date)
    eps_pctiles = eps_growth_percentiles(quality_map)

    shortlist = detector_shortlist(conn, price_date)
    # WAVE_M M2 (user order 2026-07-11, "the filter IS the defect"): union the
    # discovery.build_bucket sensitive bucket into the live pool. pre_bucket_pool
    # is the old (confluence + detector_shortlist) pool size — kept so the
    # before/after counts are honest in the run-card, not just the final union.
    pre_bucket_pool = list(dict.fromkeys(list(pool.keys()) + shortlist))
    bucket_map = discovery_bucket_map(conn, price_date)
    pool_symbols = list(dict.fromkeys(pre_bucket_pool + list(bucket_map.keys())))
    pool_size_pre_discovery = len(pre_bucket_pool)
    discovery_bucket_size = len(bucket_map)
    discovery_added = len(pool_symbols) - len(pre_bucket_pool)
    if scan_limit is not None:
        pool_symbols = pool_symbols[:scan_limit]

    cfg = GateConfig()
    candidates: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for sym in pool_symbols:
        quality = quality_map.get(sym)
        if quality is None:
            growth = fundamentals.growth_for(conn, sym, on_or_before, None)
            quality = growth if any(v is not None for v in growth.values()) else None
        bars25 = load_symbol_bars(conn, sym, price_date, limit=25)
        verdict = evaluate_symbol(
            bars25, sym, cfg,
            market_cap_cr=(quality or {}).get("market_cap_cr"))
        if not verdict["tradeable"]:
            _refuse(conn, refused, price_date, sym, None, "tradability",
                    "; ".join(verdict.get("reasons_failed", [])))
            continue

        candidate = candidate_for_symbol(
            conn, sym, price_date,
            pool.get(sym, {"count": 0, "screeners": [], "rs_rating": None, "basic_industry": None}),
            quality, top_quartile, rs_map.get(sym),
            abs_strength.get(sym), eps_pctiles.get(sym),
            market_mode=market_mode, universe_verdict=verdict,
            discovery_entry=bucket_map.get(sym),
        )
        if candidate is None:
            continue
        if candidate.get("refused"):
            # M3: objections a name carried on the way to a hard refusal ride
            # into the refusals ledger's evidence_json alongside the gate
            # trace — visible either way, per named/scored-objection order.
            _refuse(conn, refused, price_date, sym, candidate.get("setup_family"),
                    candidate.get("failed_gate"), candidate.get("drop_reason"),
                    {"gates": candidate.get("gates"), "objections": candidate.get("objections") or []})
            continue
        candidates.append(candidate)

    _assign_ranks(candidates)
    conn.commit()
    advanced = price_date == on_or_before
    return {
        "available": True,
        "as_of": price_date,
        "screener_as_of": screener_date,
        "market_mode": market_mode,
        "market_mode_defaulted": mode_defaulted,
        "candidates": candidates,
        "refused_count": len(refused),
        "dropped": refused,
        # WAVE_M M2 honesty fields — before/after pool counts for the run-card
        # funnel (user order: "funnel numbers honest in run-card").
        "pool_size_pre_discovery": pool_size_pre_discovery,
        "discovery_bucket_size": discovery_bucket_size,
        "discovery_added": discovery_added,
        "pool_size": len(pool_symbols),
        # Ingest-stuck-date honesty (2026-07-15 fix): on_or_before is what the
        # caller asked to scan up to; as_of/price_date is what daily_prices
        # actually had. When they diverge, the caller (candidates.run / the
        # pipeline-run API path) must say so explicitly instead of silently
        # persisting an old date as if it were current.
        "requested_date": on_or_before,
        "advanced": advanced,
        "stale_reason": (
            None if advanced else
            f"No EQ daily_prices for {on_or_before} yet; latest available session is {price_date}."
        ),
    }


def scan_candidates(conn, on_or_before: str, scan_limit: int | None = None) -> dict[str, Any]:
    """Manas 2.0 deterministic refusal cascade.

    The agent debate stage runs after persisted scanner rows exist; this
    function is intentionally only the cascade/math authority.
    """
    return scan_candidates_deterministic(conn, on_or_before, scan_limit)


def persist_candidates(conn, scan_date: str, candidates: list[dict[str, Any]]) -> int:
    ensure_schema(conn)
    outcomes.ensure_schema(conn)
    conn.execute("DELETE FROM scan_candidates WHERE scan_date = ?", (scan_date,))
    for c in candidates:
        conn.execute(
            "INSERT INTO scan_candidates (scan_date, symbol, setup, readiness, grade, rs, rs_as_of, "
            "delivery_pct, delivery_as_of, pivot, entry, stop, target, sector, industry, "
            "evidence_json, read, timing_json, score_breakdown_json, measured_move, "
            "measured_move_note, confluence_count, setup_type, pattern_label, base_age, "
            "days_since_listing, trade_plan_json, rr, suggested_qty, rank, rank_of, "
            "setup_family, exit_state, gates_json, conviction_score, conviction_axes_json, "
            "conviction_rank, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scanner', datetime('now'))",
            (
                scan_date,
                c["symbol"],
                c["setup"],
                c["readiness"],
                c["grade"],
                c.get("rs"),
                c.get("rs_as_of"),
                c.get("delivery_pct"),
                c.get("delivery_as_of"),
                c.get("pivot"),
                c.get("entry"),
                c.get("stop"),
                c.get("measured_move"),
                c.get("sector"),
                c.get("industry"),
                json.dumps(c.get("evidence") or []),
                c.get("read"),
                json.dumps(c.get("timing") or {}),
                json.dumps(c.get("score_breakdown") or {}),
                c.get("measured_move"),
                c.get("measured_move_note"),
                c.get("confluence_count"),
                c.get("setup_type"),
                c.get("pattern_label"),
                c.get("base_age"),
                c.get("days_since_listing"),
                json.dumps(c.get("trade_plan") or {}),
                c.get("rr"),
                c.get("suggested_qty"),
                c.get("rank"),
                c.get("rank_of"),
                c.get("setup_family"),
                c.get("exit_state"),
                json.dumps(c.get("gates") or []),
                c.get("conviction_score"),
                json.dumps({"axes": c.get("conviction_axes") or {}, "why": c.get("conviction_why") or []}),
                c.get("conviction_rank"),
            ),
        )
        outcomes.persist_candidate_snapshot(conn, scan_date, c)
    return len(candidates)


def filter_candidates(
    candidates: list[dict[str, Any]],
    min_rs: float | None = None,
    setup: str | None = None,
    sector: str | None = None,
    min_grade: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    setup_filter = (setup or "").strip().lower()
    sector_filter = (sector or "").strip().upper()
    min_grade_rank = {"C": 0, "B": 1, "A": 2, "A+": 3}.get((min_grade or "C").upper(), 0)
    grade_rank = {"C": 0, "B": 1, "A": 2, "A+": 3}
    out = []
    for item in candidates:
        if min_rs is not None and (item.get("rs") is None or item["rs"] < min_rs):
            continue
        if setup_filter and setup_filter not in str(item.get("setup") or "").lower():
            continue
        if sector_filter and item.get("sector") != sector_filter:
            continue
        if grade_rank.get(item.get("grade"), 0) < min_grade_rank:
            continue
        out.append(item)
    return out[:limit]


def load_persisted_candidates(
    conn,
    on_or_before: str,
    min_rs: float | None = None,
    setup: str | None = None,
    sector: str | None = None,
    min_grade: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    ensure_schema(conn)
    from manas_os.agents import debate as agent_debate

    agent_debate.ensure_schema(conn)
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not row or not row["d"]:
        return {"available": False, "as_of": None, "candidates": []}
    scan_date = row["d"]
    rows = conn.execute(
        "SELECT * FROM scan_candidates WHERE scan_date = ? ORDER BY readiness DESC, symbol",
        (scan_date,),
    ).fetchall()
    verdict_rows = conn.execute(
        "SELECT symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning "
        "FROM agent_verdicts WHERE scan_date = ? "
        "ORDER BY symbol, CASE agent WHEN 'chair' THEN 0 ELSE 1 END, rank",
        (scan_date,),
    ).fetchall()
    verdicts_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for r in verdict_rows:
        item = dict(r)
        try:
            item["lens_scores"] = json.loads(item.pop("lens_scores_json") or "{}")
        except json.JSONDecodeError:
            item["lens_scores"] = {}
        verdicts_by_symbol.setdefault(item["symbol"], []).append(item)
    candidates = []
    # Circuit-state (focus fields, W0.2): one writer — pull the latest band_pct
    # as-of scan_date from circuit_bands. Attached to every candidate so the
    # focus slice surfaces it without a second endpoint; null when no band on
    # file (the JSX renders the field only when non-empty).
    circuit_bands = {}
    for r in conn.execute(
        "SELECT symbol, band_pct FROM circuit_bands WHERE as_of <= ? "
        "ORDER BY as_of DESC",
        (scan_date,),
    ).fetchall():
        # ORDER BY as_of DESC → first occurrence is the latest band per symbol.
        circuit_bands.setdefault(r["symbol"], r["band_pct"])
    for row in rows:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json") or "[]")
        item["timing"] = json.loads(item.pop("timing_json") or "{}")
        item["score_breakdown"] = json.loads(item.pop("score_breakdown_json", None) or "{}")
        item["trade_plan"] = json.loads(item.pop("trade_plan_json", None) or "{}") or None
        conviction_payload = json.loads(item.pop("conviction_axes_json", None) or "{}")
        item["conviction_axes"] = conviction_payload.get("axes") or {}
        item["conviction_why"] = conviction_payload.get("why") or []
        item.setdefault("measured_move", item.get("target"))
        item["circuit_state"] = circuit_bands.get(item["symbol"])
        item["agent_debate"] = verdicts_by_symbol.get(item["symbol"], [])
        item.pop("target", None)
        item.pop("source", None)
        item.pop("ingested_at", None)
        candidates.append(item)
    # expectancy chip (T2.3b): system + personal cell for this family × today's regime
    from manas_os.scanner import expectancy as _exp
    mode, _ = market_mode_for(conn, scan_date)
    _chips: dict[str, Any] = {}
    for item in candidates:
        fam = item.get("setup_family") or "unknown"
        if fam not in _chips:
            _chips[fam] = _exp.chip_for(conn, fam, mode)
        item["expectancy"] = _chips[fam]
    return {
        "available": True,
        "as_of": scan_date,
        "candidates": filter_candidates(candidates, min_rs, setup, sector, min_grade, limit),
    }


def run(conn, run_date: str) -> dict[str, Any]:
    """Run the persisted P2 scanner. Never raises; always logs pipeline_runs."""
    started = time.monotonic()
    try:
        result = scan_candidates(conn, run_date)
        if not result["available"]:
            reason = result.get("reason") or "no EQ prices for scan"
            _log(conn, run_date, "skip", 0, started, reason)
            conn.commit()
            return {"status": "skip", "rows": 0, "as_of": None, "reason": reason}
        rows = persist_candidates(conn, result["as_of"], result["candidates"])
        if result.get("advanced", result["as_of"] == run_date):
            detail = f"advanced to {result['as_of']}; candidates={rows}"
            status = "ok"
        else:
            # Honest-feedback fix (2026-07-15): scan_candidates DID something
            # (it persisted at the latest date it actually has inputs for),
            # but it did NOT reach run_date — that must not read as a clean
            # "ok" that leaves the user thinking today's scan ran.
            detail = (f"could not advance past {result['as_of']} because scan_candidates "
                      f"{result.get('stale_reason') or 'has no newer EQ prices yet'}")
            status = "stale"
        _log(conn, run_date, status, rows, started, detail)
        conn.commit()
        return {
            "status": status, "rows": rows, "as_of": result["as_of"],
            "requested": run_date, "advanced": result.get("advanced", result["as_of"] == run_date),
            "detail": detail,
        }
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )
