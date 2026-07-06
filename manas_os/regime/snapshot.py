"""Regime snapshot engine.

Builds the daily top-strip regime row from current manas_os tables. The pure
helpers keep every state traceable to named inputs; ``run`` is the DB wrapper
registered in ``manas run-eod``.
"""
from __future__ import annotations

import json
import time
from datetime import date
from typing import Any

from manas_os import market_calendar
from manas_os.regime.xp import xp_for_date

STAGE = "regime_snapshot"
SOURCE = "breadth_daily+xp"

RATIO_GREEN_MIN = 75.0
RATIO_WHITE_MIN = 50.0
R50_GREEN_MIN = 85.0
R50_WHITE_MIN = 60.0
R4_RED_MAX = 50.0
R4_GREEN_MIN = 200.0
R4_ORANGE_MIN = 400.0

# XP bands — beginner one-liner + label surfaced next to the XP dial value
# (JOB 1). Tuned so a "typical" quiet market sits in building/strong, and only
# genuine blow-off breadth reads as extreme.
XP_BAND_LOW_MAX = 15.0
XP_BAND_BUILDING_MAX = 40.0
XP_BAND_STRONG_MAX = 100.0


def _as_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    return dict(row)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ratio_from_pct_above(pct_above: float | None) -> float | None:
    """20R-style ratio: above / below * 100, from a percent-above input."""
    pct = _num(pct_above)
    if pct is None or pct < 0 or pct > 100:
        return None
    below = 100.0 - pct
    if below <= 0:
        return None
    return (pct / below) * 100.0


def burst_ratio(up_count: float | None, down_count: float | None) -> float | None:
    up = _num(up_count)
    down = _num(down_count)
    if up is None or down is None or down <= 0:
        return None
    return (up / down) * 100.0


def band_ratio(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= RATIO_GREEN_MIN:
        return "GREEN"
    if value >= RATIO_WHITE_MIN:
        return "WHITE"
    return "RED"


def band_r50(value: float | None) -> str | None:
    """50R band — separate thresholds from 20R/10R per JOB 1 (>=85 green,
    60-85 white, <60 red)."""
    if value is None:
        return None
    if value >= R50_GREEN_MIN:
        return "GREEN"
    if value >= R50_WHITE_MIN:
        return "WHITE"
    return "RED"


def xp_band(value: float | None) -> str | None:
    """Beginner-facing XP strength band: low / building / strong / extreme."""
    if value is None:
        return None
    if value < XP_BAND_LOW_MAX:
        return "LOW"
    if value < XP_BAND_BUILDING_MAX:
        return "BUILDING"
    if value < XP_BAND_STRONG_MAX:
        return "STRONG"
    return "EXTREME"


def band_r4p5(value: float | None) -> str | None:
    if value is None:
        return None
    if value < R4_RED_MAX:
        return "RED"
    if value < R4_GREEN_MIN:
        return "WHITE"
    if value < R4_ORANGE_MIN:
        return "GREEN"
    return "ORANGE"


def compute_mbi(row: dict[str, Any]) -> dict[str, Any]:
    """Compute MBI ratios, color, and warning flag from breadth_daily columns."""
    r10 = ratio_from_pct_above(row.get("pct_above_10dma"))
    r20 = ratio_from_pct_above(row.get("pct_above_20dma"))
    r50 = ratio_from_pct_above(row.get("pct_above_50dma"))
    r4p5 = burst_ratio(row.get("up_4pct"), row.get("down_4pct"))

    bands = {
        "r10": band_ratio(r10),
        "r20": band_ratio(r20),
        "r50": band_r50(r50),
        "r4p5": band_r4p5(r4p5),
    }
    score = 0
    red_count = 0
    scored = 0
    for band in bands.values():
        if band is None:
            continue
        scored += 1
        if band in {"GREEN", "ORANGE"}:
            score += 1
        elif band == "RED":
            score -= 1
            red_count += 1

    if scored and score >= 3:
        day_color = "GREEN"
    elif scored and score <= -3:
        day_color = "RED"
    else:
        day_color = "WHITE"

    return {
        "r10": r10,
        "r20": r20,
        "r50": r50,
        "r4p5": r4p5,
        "bands": bands,
        "mbi_day_color": day_color,
        "warning_day": red_count >= 3,
        "red_count": red_count,
        "score": score,
    }


def _state_from_pct(pct: float | None, good: float = 55.0, bad: float = 45.0) -> str:
    if pct is None:
        return "UNKNOWN"
    if pct >= good:
        return "PASS"
    if pct < bad:
        return "FAIL"
    return "UNKNOWN"


def compute_pillars(row: dict[str, Any], mbi: dict[str, Any]) -> dict[str, Any]:
    """Four legacy pillars, rewired to current schema where possible.

    Trend uses trend-breadth proxy columns because the legacy _NF500EW index is
    not stored in manas_os. Momentum uses Nifty day change plus 4.5R because
    the legacy Nifty RSI pillar is not materialized as an aggregate. Breadth
    uses 10DMA/20DMA participation. Volatility is unknown until the system has
    an index ATR/EMA aggregate or VIX input.
    """
    pct_20_gt_40 = _num(row.get("pct_20dma_gt_40dma"))
    pct_10_gt_20 = _num(row.get("pct_10dma_gt_20dma"))
    trend_pct = None
    if pct_20_gt_40 is not None and pct_10_gt_20 is not None:
        trend_pct = (pct_20_gt_40 + pct_10_gt_20) / 2.0
    elif pct_20_gt_40 is not None:
        trend_pct = pct_20_gt_40

    trend_state = _state_from_pct(trend_pct, 55.0, 45.0)
    trend_reason = (
        "Trend proxy uses pct_10dma_gt_20dma and pct_20dma_gt_40dma "
        f"averaged to {trend_pct:.1f}%."
        if trend_pct is not None
        else "Trend is unknown because _NF500EW close/SMA21 and trend-breadth columns are unavailable."
    )

    nifty_chg = _num(row.get("nifty_chg_pct"))
    r4p5 = _num(mbi.get("r4p5"))
    if r4p5 is None and nifty_chg is None:
        momentum_state = "UNKNOWN"
    elif (r4p5 is not None and r4p5 >= R4_GREEN_MIN) or (nifty_chg is not None and nifty_chg > 0.5):
        momentum_state = "PASS"
    elif (r4p5 is not None and r4p5 < R4_RED_MAX) or (nifty_chg is not None and nifty_chg < -0.5):
        momentum_state = "FAIL"
    else:
        momentum_state = "UNKNOWN"
    momentum_reason = (
        f"Momentum proxy uses r4p5={_fmt(r4p5)} and nifty_chg_pct={_fmt(nifty_chg)}; "
        "legacy Nifty RSI14 aggregate is not available."
    )

    breadth_avg = _avg(_num(row.get("pct_above_10dma")), _num(row.get("pct_above_20dma")))
    breadth_state = _state_from_pct(breadth_avg, 55.0, 45.0)
    breadth_reason = (
        f"Breadth uses pct_above_10dma={_fmt(row.get('pct_above_10dma'))} and "
        f"pct_above_20dma={_fmt(row.get('pct_above_20dma'))}, average={_fmt(breadth_avg)}."
    )

    volatility_state = "UNKNOWN"
    volatility_reason = (
        "Volatility is unknown because current schema has no VIX or index ATR/EMA aggregate."
    )

    pillars = {
        "trend": {"state": trend_state, "pass": trend_state == "PASS", "reason": trend_reason},
        "momentum": {
            "state": momentum_state,
            "pass": momentum_state == "PASS",
            "reason": momentum_reason,
        },
        "breadth": {
            "state": breadth_state,
            "pass": breadth_state == "PASS",
            "reason": breadth_reason,
        },
        "volatility": {
            "state": volatility_state,
            "pass": False,
            "reason": volatility_reason,
        },
    }
    return {
        "pillars": pillars,
        "pillars_passed": sum(1 for p in pillars.values() if p["pass"]),
        "known_pillars": sum(1 for p in pillars.values() if p["state"] != "UNKNOWN"),
    }


def classify_market_mode(
    pillars_passed: int, known_pillars: int, mbi_day_color: str, warning_day: bool, data_stale: bool
) -> str:
    """RED day, or all *known* pillars failing, forces DEFENSIVE/NO_TRADE.

    ``known_pillars`` (vs. the nominal 4) matters because Trend and
    Volatility are structurally UNKNOWN until their data sources exist
    (see compute_pillars' docstring) — an UNKNOWN pillar must never count
    against the day the way a FAILED pillar does, or the mode would read
    DEFENSIVE on most days regardless of actual conditions.
    """
    if data_stale:
        if mbi_day_color == "RED" or (known_pillars > 0 and pillars_passed == 0):
            return "DEFENSIVE"
        return "SELECTIVE"
    if mbi_day_color == "RED" and pillars_passed == 0:
        return "NO_TRADE"
    if mbi_day_color == "RED":
        return "DEFENSIVE"
    if known_pillars > 0 and pillars_passed == 0:
        return "DEFENSIVE"
    if pillars_passed >= 4 and mbi_day_color == "GREEN":
        mode = "RISK_ON"
    else:
        mode = "SELECTIVE"
    if warning_day and mode == "RISK_ON":
        return "SELECTIVE"
    return mode


def risk_profile(market_mode: str) -> dict[str, Any]:
    profiles = {
        "RISK_ON": {
            "allowed_risk_min_pct": 0.50,
            "allowed_risk_max_pct": 0.65,
            "max_open_risk_pct": 2.50,
            "preferred": ["Strong Start", "D2", "EP", "VCP", "Positional Pullback"],
            "avoid": ["Late breakouts", "Weak RS reversals"],
        },
        "SELECTIVE": {
            "allowed_risk_min_pct": 0.35,
            "allowed_risk_max_pct": 0.50,
            "max_open_risk_pct": 2.00,
            "preferred": ["EP", "Strong Start A/B", "D2 A/B", "VCP A+", "Positional Pullback"],
            "avoid": ["Late breakouts", "Weak RS reversals", "Low-quality pullbacks"],
        },
        "DEFENSIVE": {
            "allowed_risk_min_pct": 0.20,
            "allowed_risk_max_pct": 0.35,
            "max_open_risk_pct": 1.50,
            "preferred": ["EP with genuine surprise", "A+ pullback", "Reversal"],
            "avoid": ["Late breakouts", "Average breakouts", "Full-size new longs", "Weak RS reversals"],
        },
        "NO_TRADE": {
            "allowed_risk_min_pct": 0.00,
            "allowed_risk_max_pct": 0.20,
            "max_open_risk_pct": 1.00,
            "preferred": ["Exceptional EP only", "Tracking-size reversal"],
            "avoid": ["New breakouts", "Add-ons", "Full-size positions", "Weak RS reversals"],
        },
    }
    return profiles[market_mode]


def compute_quadrant(row: dict[str, Any], mbi: dict[str, Any], xp_value: float | None) -> dict[str, Any]:
    r4p5 = _num(mbi.get("r4p5"))
    nifty_chg = _num(row.get("nifty_chg_pct"))
    pct10 = _num(row.get("pct_above_10dma"))
    pct20 = _num(row.get("pct_above_20dma"))
    pct40 = _num(row.get("pct_above_40dma"))

    momentum_state = "UP" if (r4p5 and r4p5 >= 200) or (nifty_chg and nifty_chg > 0.5) else (
        "DOWN" if (r4p5 is not None and r4p5 < 50) or (nifty_chg is not None and nifty_chg < -0.5) else "NEUTRAL"
    )
    swing_state = "UP" if _avg(pct10, pct20) is not None and _avg(pct10, pct20) >= 55 else (
        "DOWN" if _avg(pct10, pct20) is not None and _avg(pct10, pct20) < 45 else "MIXED"
    )
    trend_state = "UP" if _avg(pct20, pct40) is not None and _avg(pct20, pct40) >= 55 else (
        "DOWN" if _avg(pct20, pct40) is not None and _avg(pct20, pct40) < 45 else "MIXED"
    )
    bias_state = "BULLISH" if pct40 is not None and pct40 >= 60 else (
        "BEARISH" if pct40 is not None and pct40 < 40 else "NEUTRAL"
    )

    return {
        "momentum": {
            "state": momentum_state,
            "confidence": _confidence_from_distance(_avg(r4p5 / 4.0 if r4p5 is not None else None, 50.0 + (nifty_chg or 0.0) * 10.0)),
            "reason": _momentum_reason(r4p5, nifty_chg),
        },
        "swing": {
            "state": swing_state,
            "confidence": _confidence_from_distance(_avg(pct10, pct20)),
            "reason": (
                f"{_fmt_pct(pct10)} of stocks are above their 10-day average and "
                f"{_fmt_pct(pct20)} above their 20-day average."
                if pct10 is not None or pct20 is not None
                else "Not enough breadth data yet for a short-term swing read."
            ),
        },
        "trend": {
            "state": trend_state,
            "confidence": _confidence_from_distance(_avg(pct20, pct40)),
            "reason": (
                f"{_fmt_pct(pct20)} of stocks are above their 20-day average and "
                f"{_fmt_pct(pct40)} above their 40-day average. (A true 50-day/new-highs "
                "read isn't wired in yet — this is the closest available proxy.)"
                if pct20 is not None or pct40 is not None
                else "Not enough breadth data yet for a trend read."
            ),
        },
        "bias": {
            "state": bias_state,
            "confidence": _confidence_from_distance(pct40),
            "reason": (
                f"{_fmt_pct(pct40)} of stocks are above their 40-day average. "
                "(Long-term 200-day breadth isn't tracked yet — this is a shorter-term stand-in.)"
                if pct40 is not None
                else "Not enough breadth data yet for a long-term bias read."
            ),
        },
    }


def _momentum_reason(r4p5: float | None, nifty_chg: float | None) -> str:
    bits = []
    if r4p5 is not None:
        burst_word = "strong" if r4p5 >= 200 else "weak" if r4p5 < 50 else "average"
        bits.append(f"today's burst-move ratio is {burst_word} ({r4p5:.0f})")
    if nifty_chg is not None:
        direction = "up" if nifty_chg > 0 else "down" if nifty_chg < 0 else "flat"
        bits.append(f"Nifty is {direction} {abs(nifty_chg):.2f}% today")
    if not bits:
        return "Not enough data yet for a momentum read."
    return (
        ", ".join(bits).capitalize()
        + ". (A fuller momentum score needs the EM dial and a real Mswing input, not wired in yet.)"
    )


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "an unknown share"
    return f"{value:.0f}%"


def build_snapshot(row: dict[str, Any], run_date: str, source_date: str, xp_value: float | None, xp_z_state: float | None) -> dict[str, Any]:
    mbi = compute_mbi(row)
    pillars = compute_pillars(row, mbi)
    data_stale = int(source_date != run_date and _days_between(source_date, run_date) > 1)
    if source_date != run_date:
        data_stale = 1
    mode = classify_market_mode(
        pillars["pillars_passed"],
        pillars["known_pillars"],
        mbi["mbi_day_color"],
        bool(mbi["warning_day"]),
        bool(data_stale),
    )
    profile = risk_profile(mode)
    quadrant = compute_quadrant(row, mbi, xp_value)
    days_behind = _trading_days_behind(source_date, run_date) if data_stale else 0
    explanation = _explanation(mode, pillars, mbi, data_stale, days_behind)
    technical_detail = _technical_detail(source_date, run_date, mbi, pillars, data_stale)
    return {
        "snapshot_date": run_date,
        "source_date": source_date,
        "market_mode": mode,
        "xp_value": xp_value,
        "xp_z_state": xp_z_state,
        "em_value": None,
        "em_source": "proxy_not_yet_computed",
        "mbi_day_color": mbi["mbi_day_color"],
        "warning_day": int(bool(mbi["warning_day"])),
        "r10": mbi["r10"],
        "r20": mbi["r20"],
        "r50": mbi["r50"],
        "r4p5": mbi["r4p5"],
        "pillars_passed": pillars["pillars_passed"],
        "allowed_risk_min_pct": profile["allowed_risk_min_pct"],
        "allowed_risk_max_pct": profile["allowed_risk_max_pct"],
        "max_open_risk_pct": profile["max_open_risk_pct"],
        "preferred_setups_json": json.dumps(profile["preferred"]),
        "avoid_setups_json": json.dumps(profile["avoid"]),
        "quadrant_json": json.dumps(quadrant),
        "explanation_text": explanation,
        "technical_detail": technical_detail,
        "data_stale": data_stale,
    }


def run(conn, run_date: str) -> dict:
    """Compute and persist one regime_snapshots row. Never raises.

    Guards against writing a "phantom" snapshot: if breadth_daily has no row
    for run_date itself (an eod run on a day with no fresh breadth data), the
    snapshot must NOT be written for run_date at all — a prior day's snapshot
    would otherwise get silently duplicated under a new date, which reads as a
    real new session when it isn't one. This is stricter than "most recent row
    on or before run_date": a stale-but-present run_date row is still fine
    (that's what data_stale/source_date already exist to flag), but a *missing*
    run_date row means nothing genuinely happened today and we skip outright,
    like every other pipeline stage does when its source data is missing.
    """
    started = time.monotonic()
    try:
        today_row = conn.execute(
            "SELECT 1 FROM breadth_daily WHERE trade_date = ?", (run_date,)
        ).fetchone()
        if today_row is None:
            detail = "no breadth_daily row for run_date; skipping snapshot (phantom-snapshot guard)"
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started, detail)
            conn.commit()
            return {"status": "skip", "rows_affected": 0, "detail": detail}

        row = conn.execute(
            "SELECT * FROM breadth_daily WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 1",
            (run_date,),
        ).fetchone()
        if row is None:
            snapshot = _empty_snapshot(run_date, "no breadth_daily row on or before run_date")
            _upsert_snapshot(conn, snapshot)
            detail = "missing breadth_daily; wrote stale defensive snapshot"
            _log_run(conn, run_date, "skip", 1, time.monotonic() - started, detail)
            conn.commit()
            return {"status": "skip", "rows_affected": 1, "detail": detail}

        source_date = row["trade_date"]
        # Compute XP as-of the actual breadth source date, not run_date — the
        # breadth sheet routinely lags a day, and a permanently-null headline
        # number is worse than an honestly-dated one (the "Selective, stale"
        # posture cap already prevents this from reading as confident/green).
        xp_value = None
        xp_z_state = None
        try:
            xp_value, xp_z_state = xp_for_date(conn, source_date)
        except Exception:
            xp_value = None
            xp_z_state = None

        snapshot = build_snapshot(_as_dict(row), run_date, source_date, xp_value, xp_z_state)
        _upsert_snapshot(conn, snapshot)
        detail = f"source_date={source_date} market_mode={snapshot['market_mode']}"
        _log_run(conn, run_date, "ok", 1, time.monotonic() - started, detail)
        conn.commit()
        return {"status": "ok", "rows_affected": 1, "detail": detail, "market_mode": snapshot["market_mode"]}
    except Exception as exc:
        detail = f"regime snapshot failed: {exc}"
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started, detail)
        conn.commit()
        return {"status": "fail", "rows_affected": 0, "detail": detail}


def _upsert_snapshot(conn, snap: dict[str, Any]) -> None:
    cols = [
        "snapshot_date", "source_date", "market_mode", "xp_value", "xp_z_state", "em_value", "em_source",
        "mbi_day_color", "warning_day", "r10", "r20", "r50", "r4p5", "pillars_passed",
        "allowed_risk_min_pct", "allowed_risk_max_pct", "max_open_risk_pct",
        "preferred_setups_json", "avoid_setups_json", "quadrant_json", "explanation_text",
        "technical_detail", "data_stale",
    ]
    values = [snap.get(c) for c in cols]
    update = ", ".join(f"{c}=excluded.{c}" for c in cols[1:])
    conn.execute(
        f"INSERT INTO regime_snapshots ({', '.join(cols)}, ingested_at) "
        f"VALUES ({', '.join('?' for _ in cols)}, datetime('now')) "
        f"ON CONFLICT(snapshot_date) DO UPDATE SET {update}, ingested_at=datetime('now')",
        values,
    )


def _log_run(conn, run_date: str, status: str, rows: int, duration: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
        "VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def _empty_snapshot(run_date: str, reason: str) -> dict[str, Any]:
    profile = risk_profile("DEFENSIVE")
    return {
        "snapshot_date": run_date,
        "source_date": None,
        "market_mode": "DEFENSIVE",
        "xp_value": None,
        "xp_z_state": None,
        "em_value": None,
        "em_source": "proxy_not_yet_computed",
        "mbi_day_color": "WHITE",
        "warning_day": 0,
        "r10": None,
        "r20": None,
        "r50": None,
        "r4p5": None,
        "pillars_passed": 0,
        "allowed_risk_min_pct": profile["allowed_risk_min_pct"],
        "allowed_risk_max_pct": profile["allowed_risk_max_pct"],
        "max_open_risk_pct": profile["max_open_risk_pct"],
        "preferred_setups_json": json.dumps(profile["preferred"]),
        "avoid_setups_json": json.dumps(profile["avoid"]),
        "quadrant_json": json.dumps({}),
        "explanation_text": (
            "This is a signal to mostly sit out — there isn't enough recent breadth data to read "
            "the market yet."
        ),
        "technical_detail": f"{reason}; stale-data rule prevents RISK_ON.",
        "data_stale": 1,
    }


def _avg(*values: float | None) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _fmt(value: Any) -> str:
    n = _num(value)
    if n is None:
        return "None"
    return f"{n:.2f}"


def _confidence_from_distance(value: float | None) -> int:
    if value is None:
        return 35
    return int(max(40, min(95, 50 + abs(value - 50.0) * 1.5)))


def _days_between(source_date: str, run_date: str) -> int:
    try:
        return (date.fromisoformat(run_date) - date.fromisoformat(source_date)).days
    except ValueError:
        return 999


def _trading_days_behind(source_date: str | None, run_date: str) -> int:
    """Trading-day gap for the beginner-facing explanation text (JOB 3): a
    weekend/holiday alone should not inflate this. Falls back to 0 on bad
    input rather than raising, since this only feeds display copy."""
    if not source_date:
        return 0
    try:
        return market_calendar.trading_days_between(
            date.fromisoformat(source_date), date.fromisoformat(run_date)
        )
    except ValueError:
        return 0


def _explanation(
    mode: str,
    pillars: dict[str, Any],
    mbi: dict[str, Any],
    data_stale: int,
    days_behind: int | None = None,
) -> str:
    """One clean, plain-English sentence — the primary on-screen read.

    Full var=value audit trail lives in ``_technical_detail`` instead, behind
    a collapsible "technical detail" toggle in the UI (no-black-box rule is
    kept by making it available, not by forcing everyone to read it by default).

    BUG FIX (JOB 1): when data is stale, this must lead with the staleness
    and never assert "breadth is green / checks favourable" as if it's an
    actionable read for today — that reads as a direct contradiction of a
    STALE posture badge. The "last-known" numbers are still surfaced, but
    clearly labelled as last-known, not today's read.
    """
    known = pillars["known_pillars"]
    passed = pillars["pillars_passed"]
    checks = (
        f"{passed} of {known} known checks are favourable" if known
        else "none of the deeper trend/volatility checks are wired in yet"
    )
    breadth_word = mbi["mbi_day_color"].lower()

    if data_stale:
        age = f"{days_behind} trading day{'s' if days_behind != 1 else ''}" if days_behind else "several trading days"
        return (
            f"Data is {age} old — treat this as last-known, not today's read. "
            f"When fresh: breadth was {breadth_word}, {checks}."
        )

    mode_word = {
        "RISK_ON": "a green light to trade at full size",
        "SELECTIVE": "a caution to trade smaller and be picky",
        "DEFENSIVE": "a signal to mostly sit out and manage, not add",
        "NO_TRADE": "a signal to take no new trades today",
    }.get(mode, "an unclear signal")
    return f"This is {mode_word} — {checks}, and market breadth is {breadth_word}."


def stale_read_explanation(
    mbi_day_color: str | None,
    pillars_passed: int | None,
    known_pillars: int | None,
    days_behind: int,
) -> str:
    """Public wrapper of the stale branch of ``_explanation`` for callers
    (the API) that only have a *persisted* regime_snapshots row in hand, not
    the full pillars/mbi dicts computed at write-time.

    BUG FIX (JOB 1): the API can mark a snapshot stale at *read* time (the
    snapshot is old relative to "today", even though it was fresh when
    written) without recomputing the whole snapshot. When that happens, the
    persisted explanation_text — written when the snapshot was NOT stale —
    would otherwise keep asserting "breadth is green / checks favourable" as
    if it were live, directly contradicting the now-STALE posture badge. This
    regenerates the honest stale-branch sentence from the same wording rules
    as ``_explanation`` so the two never disagree.
    """
    known = known_pillars or 0
    passed = pillars_passed or 0
    checks = (
        f"{passed} of {known} known checks are favourable" if known
        else "none of the deeper trend/volatility checks are wired in yet"
    )
    breadth_word = (mbi_day_color or "unknown").lower()
    age = f"{days_behind} trading day{'s' if days_behind != 1 else ''}" if days_behind else "several trading days"
    return (
        f"Data is {age} old — treat this as last-known, not today's read. "
        f"When fresh: breadth was {breadth_word}, {checks}."
    )


def _technical_detail(source_date: str, run_date: str, mbi: dict[str, Any], pillars: dict[str, Any], data_stale: int) -> str:
    """The full var=value audit trail — collapsed by default in the UI."""
    bits = [
        f"breadth_daily source_date={source_date} for run_date={run_date}",
        f"MBI bands: r10={mbi['bands']['r10']}, r20={mbi['bands']['r20']}, "
        f"r50={mbi['bands']['r50']}, r4p5={mbi['bands']['r4p5']}",
        f"pillars_passed={pillars['pillars_passed']} of 4; known_pillars={pillars['known_pillars']}",
    ]
    for name, info in pillars["pillars"].items():
        bits.append(f"{name}: {info['state']} ({info['reason']})")
    if mbi["bands"]["r50"] is None:
        bits.append("R50 is None because breadth_daily has no pct_above_50dma value for this row.")
    bits.append("EM is not computed; em_source=proxy_not_yet_computed per project gate.")
    if data_stale:
        bits.append("Data is stale, so market_mode is hard-degraded and cannot be RISK_ON.")
    return " ".join(bits)
