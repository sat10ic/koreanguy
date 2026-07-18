"""Institutional-footprint classifier over the canonical activity score.

``manas_os.alpha.activity`` remains the only score writer. This module only
joins ``alpha_activity_signals`` to ``daily_prices``, classifies the supplied
score in price/volume context, and persists display/evidence fields.
"""
from __future__ import annotations

import time
from typing import Any

from manas_os.alpha.activity import FORMULA_VERSION


STAGE = "footprint_driver"
SOURCE = "alpha_activity_signals+daily_prices"

ABNORMAL = 3.5
STRICT = 4.0
EXTREME = 8.0  # Assumption: locked by BUILD NUMERICS pending replay calibration.
VOLUME_HIGH = 1.5  # Assumption: deliberately stricter than breakout participation.
VOLUME_LOW = 0.8  # Assumption: locked by BUILD NUMERICS pending replay calibration.

LANES = (
    "silent_accumulation",
    "absorption",
    "public_markup",
    "retail_churn",
    "silent_offloading",
)

DDL = """
CREATE TABLE IF NOT EXISTS footprint_daily (
  trade_date TEXT NOT NULL, symbol TEXT NOT NULL,
  score REAL, tier TEXT, streak_days INTEGER, avg4 REAL,
  delivery_band TEXT, volume_ratio REAL, day_change_pct REAL,
  context TEXT, lane TEXT, split_suspect INTEGER NOT NULL DEFAULT 0,
  silent_accum_days_20 INTEGER, silent_dist_days_20 INTEGER, net_silent_flow REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (trade_date, symbol));
"""


def ensure_schema(conn) -> None:
    """Create the additive footprint table; safe to call repeatedly."""
    conn.executescript(DDL)


def _num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _delivery_band(value: Any) -> str | None:
    pct = _num(value)
    if pct is None:
        return None
    if pct >= 50.0:
        return "strong"
    if pct >= 25.0:
        return "moderate"
    return "weak"


def _ema21(bars: list[dict[str, Any]]) -> float | None:
    closes = [_num(bar.get("close")) for bar in bars]
    if len(closes) < 21 or any(value is None for value in closes):
        return None
    ema = float(closes[0])
    alpha = 2.0 / 22.0
    for close in closes[1:]:
        ema = alpha * float(close) + (1.0 - alpha) * ema
    return ema


def _adr20(bars: list[dict[str, Any]]) -> float | None:
    ranges: list[float] = []
    for bar in bars[-20:]:
        high, low, close = _num(bar.get("high")), _num(bar.get("low")), _num(bar.get("close"))
        if high is not None and low is not None and close:
            ranges.append((high - low) / close * 100.0)
    return sum(ranges) / len(ranges) if ranges else None


def _split_suspect(bar: dict[str, Any]) -> bool:
    close, previous = _num(bar.get("close")), _num(bar.get("prev_close"))
    if close is None or previous is None or previous <= 0:
        return False
    ratio = close / previous
    return ratio < 0.55 or ratio > 1.45


def _streak_and_avg4(
    bars: list[dict[str, Any]], scores: dict[str, dict[str, Any]]
) -> tuple[int, float | None]:
    streak = 0
    for bar in reversed(bars):
        signal = scores.get(str(bar["trade_date"]))
        score = _num(signal.get("score")) if signal else None
        if signal is None or _split_suspect(bar) or score is None or score <= ABNORMAL:
            break
        streak += 1

    last4 = bars[-4:]
    values: list[float] = []
    if len(last4) == 4:
        for bar in last4:
            signal = scores.get(str(bar["trade_date"]))
            score = _num(signal.get("score")) if signal else None
            if signal is None or _split_suspect(bar) or score is None:
                values = []
                break
            values.append(score)
    avg4 = round(sum(values) / 4.0, 2) if len(values) == 4 else None
    return streak, avg4


def _classify_day(
    bars: list[dict[str, Any]], scores: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    bar = bars[-1]
    signal = scores.get(str(bar["trade_date"]))
    score = _num(signal.get("score")) if signal else None
    close, previous = _num(bar.get("close")), _num(bar.get("prev_close"))
    high, low, volume = _num(bar.get("high")), _num(bar.get("low")), _num(bar.get("volume"))
    split = _split_suspect(bar)

    day_change = None
    if close is not None and previous is not None and previous > 0:
        day_change = (close / previous - 1.0) * 100.0
    direction = (
        "up" if close is not None and previous is not None and close > previous
        else "down" if close is not None and previous is not None and close < previous
        else "flat"
    )

    prior_volumes = [_num(item.get("volume")) for item in bars[-21:-1]]
    volume_ratio = None
    if len(prior_volumes) == 20 and all(value is not None for value in prior_volumes):
        mean_volume = sum(float(value) for value in prior_volumes) / 20.0
        if volume is not None and mean_volume > 0:
            volume_ratio = volume / mean_volume
    volume_high = volume_ratio is not None and volume_ratio >= VOLUME_HIGH

    adr = _adr20(bars)
    price_flat = day_change is not None and adr is not None and abs(day_change) <= 0.35 * adr
    narrow = (
        high is not None and low is not None and close not in (None, 0) and adr is not None
        and (high - low) / close * 100.0 <= 0.5 * adr
    )

    highs60 = [_num(item.get("high")) for item in bars[-60:]]
    leg_high = max(value for value in highs60 if value is not None) if any(
        value is not None for value in highs60
    ) else None
    in_base = (
        close is not None and leg_high is not None
        and close >= 0.85 * leg_high and close <= leg_high
    )
    highs252 = [_num(item.get("high")) for item in bars[-252:]]
    annual_high = max(value for value in highs252 if value is not None) if any(
        value is not None for value in highs252
    ) else None
    near_highs = close is not None and annual_high is not None and close >= 0.95 * annual_high

    prior20 = bars[-21:-1]
    prior_highs = [_num(item.get("high")) for item in prior20]
    breakout = bool(
        len(prior20) == 20
        and close is not None
        and all(value is not None for value in prior_highs)
        and close > max(float(value) for value in prior_highs)
        and volume_ratio is not None
        and volume_ratio >= 1.2
    )
    ema21 = _ema21(bars)
    extended = close is not None and ema21 is not None and close > 1.08 * ema21

    tier = None
    streak, avg4 = _streak_and_avg4(bars, scores)
    context = None
    lane = None
    if score is not None and not split:
        tier = (
            "EXTREME" if score >= EXTREME
            else "STRICT" if score > STRICT
            else "ABNORMAL" if score > ABNORMAL
            else None
        )
        if score > ABNORMAL:
            quiet_context = price_flat or (
                day_change is not None and adr is not None and abs(day_change) < adr
            )
            if in_base and quiet_context and not volume_high:
                context = "stealth_accumulation_in_base"
            elif breakout:
                context = "breakout_confirmation"
            elif (extended or near_highs) and direction == "down":
                context = "churn_against_holding"

            # Flow Board precedence is binding and separate from context.
            if volume_high and direction == "down" and narrow and (in_base or near_highs):
                lane = "absorption"
            elif direction == "down" and (near_highs or extended):
                lane = "silent_offloading"
            elif not volume_high and price_flat and in_base:
                lane = "silent_accumulation"
            elif (volume_high and direction == "up") or breakout:
                lane = "public_markup"
        if score <= 2.0 and volume_high and not price_flat:
            lane = "retail_churn"
    else:
        streak = 0

    return {
        "trade_date": str(bar["trade_date"]),
        "symbol": str(bar["symbol"]),
        "score": score,
        "tier": tier,
        "streak_days": streak,
        "avg4": avg4,
        "delivery_band": _delivery_band(signal.get("delivery_pct")) if signal else None,
        "volume_ratio": round(volume_ratio, 4) if volume_ratio is not None else None,
        "day_change_pct": round(day_change, 4) if day_change is not None else None,
        "context": context,
        "lane": lane,
        "split_suspect": int(split),
        "_direction": direction,
        "_delivery_pct": _num(signal.get("delivery_pct")) if signal else None,
    }


def _history(conn, symbol: str, trade_date: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    price_rows = conn.execute(
        "SELECT symbol,trade_date,high,low,close,prev_close,volume FROM daily_prices "
        "WHERE symbol=? AND series='EQ' AND trade_date<=? "
        "ORDER BY trade_date DESC LIMIT 300",
        (symbol, trade_date),
    ).fetchall()
    bars = [dict(row) for row in reversed(price_rows)]
    score_rows = conn.execute(
        "SELECT as_of_date,score,delivery_pct FROM alpha_activity_signals "
        "WHERE symbol=? AND formula_version=? AND as_of_date<=? "
        "ORDER BY as_of_date DESC LIMIT 300",
        (symbol, FORMULA_VERSION, trade_date),
    ).fetchall()
    scores = {str(row["as_of_date"]): dict(row) for row in score_rows}
    return bars, scores


def _campaign(bars: list[dict[str, Any]], scores: dict[str, dict[str, Any]]) -> tuple[int, int, float]:
    classified: list[dict[str, Any]] = []
    start = max(0, len(bars) - 20)
    for index in range(start, len(bars)):
        classified.append(_classify_day(bars[: index + 1], scores))
    accum = sum(item["lane"] == "silent_accumulation" for item in classified)
    dist = sum(item["lane"] == "silent_offloading" for item in classified)
    net = 0.0
    for item in classified:
        if item["lane"] not in {"silent_accumulation", "silent_offloading", "absorption"}:
            continue
        score, delivery = _num(item["score"]), _num(item["_delivery_pct"])
        sign = 1.0 if item["_direction"] == "up" else -1.0 if item["_direction"] == "down" else 0.0
        if score is not None and delivery is not None:
            net += sign * score * delivery / 100.0
    return accum, dist, round(net, 4)


def compute(conn, trade_date: str) -> list[dict[str, Any]]:
    """Classify and persist the activity rows for one exact trading date."""
    ensure_schema(conn)
    source_rows = conn.execute(
        "SELECT a.symbol FROM alpha_activity_signals a "
        "JOIN daily_prices p ON p.symbol=a.symbol AND p.trade_date=a.as_of_date AND p.series='EQ' "
        "WHERE a.as_of_date=? AND a.formula_version=? ORDER BY a.symbol",
        (trade_date, FORMULA_VERSION),
    ).fetchall()
    if not source_rows:
        return []
    conn.execute("DELETE FROM footprint_daily WHERE trade_date=?", (trade_date,))
    output: list[dict[str, Any]] = []
    for source in source_rows:
        bars, scores = _history(conn, str(source["symbol"]), trade_date)
        if not bars or str(bars[-1]["trade_date"]) != trade_date:
            continue
        item = _classify_day(bars, scores)
        accum, dist, net = _campaign(bars, scores)
        item.update({
            "silent_accum_days_20": accum,
            "silent_dist_days_20": dist,
            "net_silent_flow": net,
        })
        conn.execute(
            "INSERT INTO footprint_daily "
            "(trade_date,symbol,score,tier,streak_days,avg4,delivery_band,volume_ratio,day_change_pct,"
            "context,lane,split_suspect,silent_accum_days_20,silent_dist_days_20,net_silent_flow) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(item[key] for key in (
                "trade_date", "symbol", "score", "tier", "streak_days", "avg4",
                "delivery_band", "volume_ratio", "day_change_pct", "context", "lane",
                "split_suspect", "silent_accum_days_20", "silent_dist_days_20",
                "net_silent_flow",
            )),
        )
        item.pop("_direction", None)
        item.pop("_delivery_pct", None)
        output.append(item)
    return output


def doctrine_flags(row: dict[str, Any]) -> dict[str, bool]:
    score = _num(row.get("score"))
    excluded = bool(row.get("split_suspect")) or score is None
    return {
        "abnormal": not excluded and score > ABNORMAL,
        "strict": not excluded and score > STRICT,
        "streak3": not excluded and int(row.get("streak_days") or 0) >= 3,
        "avg4_over5": not excluded and _num(row.get("avg4")) is not None and float(row["avg4"]) > 5.0,
    }


def symbol_payload(conn, symbol: str, requested_date: str | None = None) -> dict[str, Any]:
    ensure_schema(conn)
    symbol = symbol.strip().upper()
    if requested_date is None:
        date_row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM footprint_daily WHERE symbol=?", (symbol,)
        ).fetchone()
        resolved_date = date_row["d"] if date_row else None
    else:
        resolved_date = requested_date
    row = None if resolved_date is None else conn.execute(
        "SELECT * FROM footprint_daily WHERE symbol=? AND trade_date=?", (symbol, resolved_date)
    ).fetchone()
    if row is None:
        return {
            "available": False, "symbol": symbol, "date": resolved_date,
            "score": None, "tier": None, "streak_days": None, "avg4": None,
            "delivery_band": None, "context": None, "lane": None,
            "split_suspect": False,
            "doctrine_flags": {"abnormal": False, "strict": False, "streak3": False, "avg4_over5": False},
            "campaign": {"silent_accum_days_20": 0, "silent_dist_days_20": 0, "net_silent_flow": 0.0},
            "series": [],
        }
    item = dict(row)
    series_rows = conn.execute(
        "SELECT trade_date,score,lane FROM footprint_daily WHERE symbol=? AND trade_date<=? "
        "ORDER BY trade_date DESC LIMIT 20", (symbol, resolved_date),
    ).fetchall()
    return {
        "available": True,
        "symbol": symbol,
        "date": resolved_date,
        "score": item["score"],
        "tier": item["tier"],
        "streak_days": item["streak_days"],
        "avg4": item["avg4"],
        "delivery_band": item["delivery_band"],
        "context": item["context"],
        "lane": item["lane"],
        "split_suspect": bool(item["split_suspect"]),
        "doctrine_flags": doctrine_flags(item),
        "campaign": {
            "silent_accum_days_20": item["silent_accum_days_20"],
            "silent_dist_days_20": item["silent_dist_days_20"],
            "net_silent_flow": item["net_silent_flow"],
        },
        "series": [
            {"date": series["trade_date"], "score": series["score"], "lane": series["lane"]}
            for series in reversed(series_rows)
        ],
    }


def board_payload(conn, requested_date: str | None = None) -> dict[str, Any]:
    ensure_schema(conn)
    if requested_date is None:
        date_row = conn.execute("SELECT MAX(trade_date) AS d FROM footprint_daily").fetchone()
        resolved_date = date_row["d"] if date_row else None
    else:
        resolved_date = requested_date
    lanes: dict[str, list[dict[str, Any]]] = {lane: [] for lane in LANES}
    if resolved_date is None:
        return {"available": False, "date": None, "lanes": lanes}
    rows = conn.execute(
        "WITH board_scope(symbol) AS ("
        " SELECT symbol FROM scan_candidates WHERE scan_date=?"
        " UNION SELECT symbol FROM discovery_bucket WHERE scan_date=?"
        " UNION SELECT symbol FROM watchlist"
        ") SELECT f.* FROM footprint_daily f JOIN board_scope s ON s.symbol=f.symbol "
        "WHERE f.trade_date=? AND f.lane IS NOT NULL "
        "ORDER BY f.lane,ABS(COALESCE(f.net_silent_flow,0)) DESC,f.symbol",
        (resolved_date, resolved_date, resolved_date),
    ).fetchall()
    for row in rows:
        lanes[row["lane"]].append({
            "symbol": row["symbol"],
            "score": row["score"],
            "context": row["context"],
            "streak_days": row["streak_days"],
            "balance": f"{int(row['silent_accum_days_20'] or 0)}acc/{int(row['silent_dist_days_20'] or 0)}dist",
            "net_silent_flow": row["net_silent_flow"],
        })
    return {"available": bool(rows), "date": resolved_date, "lanes": lanes}


def run(conn, run_date: str) -> dict[str, Any]:
    """Persist one exact-date footprint cross-section and log the true outcome."""
    started = time.monotonic()
    try:
        rows = compute(conn, run_date)
        status = "ok" if rows else "skip"
        detail = (
            f"classified={len(rows)} from existing alpha_activity_signals"
            if rows else f"no joined activity and EQ price rows for {run_date}"
        )
        _log(conn, run_date, status, len(rows), started, detail)
        conn.commit()
        return {"status": status, "rows": len(rows), "detail": detail}
    except Exception as exc:  # noqa: BLE001 - keep later EOD stages isolated.
        # Preserve the last valid cross-section if classification fails after
        # its exact-date delete but before all replacement rows are inserted.
        conn.rollback()
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date,stage,source,status,rows_affected,duration_s,detail) "
        "VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )
