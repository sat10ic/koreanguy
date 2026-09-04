"""Causal chart-behaviour context for debate agents.

This is observation, not a gate or setup classifier. It compresses bars known at
``as_of`` so an LLM can reason across several valid chart archetypes.
"""
from __future__ import annotations

from typing import Any

from manas_os.scanner import discovery_metrics


def _f(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def _ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    current = sum(values[:period]) / period
    out[period - 1] = current
    for idx in range(period, len(values)):
        current = alpha * values[idx] + (1.0 - alpha) * current
        out[idx] = current
    return out


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return (a / b - 1.0) * 100.0


def _slope_pct(series: list[float | None], lookback: int = 5) -> float | None:
    clean = [value for value in series if value is not None]
    return _pct(clean[-1], clean[-1 - lookback]) if len(clean) > lookback else None


def _range_pct(rows: list[dict[str, Any]]) -> float | None:
    highs = [_f(row.get("high")) for row in rows]
    lows = [_f(row.get("low")) for row in rows]
    highs = [value for value in highs if value is not None]
    lows = [value for value in lows if value is not None]
    if not highs or not lows or min(lows) <= 0:
        return None
    return (max(highs) / min(lows) - 1.0) * 100.0


def _volume_character(rows: list[dict[str, Any]]) -> dict[str, Any]:
    volumes = [_f(row.get("volume")) for row in rows]
    volumes = [value for value in volumes if value is not None and value >= 0]
    if not volumes:
        return {}
    avg20 = sum(volumes[-20:]) / min(20, len(volumes))
    avg50 = sum(volumes[-50:]) / min(50, len(volumes))
    recent10 = sum(volumes[-10:]) / min(10, len(volumes))
    up_vol: list[float] = []
    down_vol: list[float] = []
    for row in rows[-20:]:
        o, c, v = _f(row.get("open")), _f(row.get("close")), _f(row.get("volume"))
        if o is None or c is None or v is None:
            continue
        (up_vol if c >= o else down_vol).append(v)
    return {
        "latest_vs_20d": _round(volumes[-1] / avg20 if avg20 else None),
        "recent10_vs_50d": _round(recent10 / avg50 if avg50 else None),
        "up_day_vs_down_day_volume": _round(
            (sum(up_vol) / len(up_vol)) / (sum(down_vol) / len(down_vol))
            if up_vol and down_vol and sum(down_vol) else None
        ),
    }


def _compact_bars(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    out = []
    for row in rows[-limit:]:
        o, h, low, c, v = (_f(row.get(key)) for key in ("open", "high", "low", "close", "volume"))
        if None in (o, h, low, c):
            continue
        out.append({
            "date": row.get("trade_date") or row.get("date"),
            "o": _round(o), "h": _round(h), "l": _round(low), "c": _round(c),
            "chg_pct": _round(_pct(c, o)),
            "close_location_pct": _round((c - low) / (h - low) * 100.0 if h != low else None),
            "volume": int(v) if v is not None else None,
        })
    return out


def build(bars: list[dict[str, Any]], *, rs_rank: Any = None,
          sector_relative: Any = None) -> dict[str, Any]:
    """Return causal, continuous chart observations from ascending daily bars."""
    valid = [row for row in bars if _f(row.get("close")) is not None]
    if not valid:
        return {"available": False, "reason": "no complete daily bars"}
    closes = [_f(row.get("close")) for row in valid]
    closes = [value for value in closes if value is not None]
    latest = closes[-1]
    ema = {period: _ema(closes, period) for period in (10, 21, 50)}
    ema_values = {period: series[-1] if series else None for period, series in ema.items()}
    high50s = [_f(row.get("high")) for row in valid[-50:]]
    low50s = [_f(row.get("low")) for row in valid[-50:]]
    high20s = [_f(row.get("high")) for row in valid[-20:]]
    low20s = [_f(row.get("low")) for row in valid[-20:]]
    high50 = max((v for v in high50s if v is not None), default=None)
    low50 = min((v for v in low50s if v is not None), default=None)
    high20 = max((v for v in high20s if v is not None), default=None)
    low20 = min((v for v in low20s if v is not None), default=None)
    range50 = (high50 - low50) if high50 is not None and low50 is not None else None
    range20 = (high20 - low20) if high20 is not None and low20 is not None else None
    stacked = all(v is not None for v in ema_values.values()) and latest > ema_values[10] > ema_values[21] > ema_values[50]
    return {
        "available": True,
        "as_of": valid[-1].get("trade_date") or valid[-1].get("date"),
        "bars_available": len(valid),
        "trend_structure": {
            "close": _round(latest),
            "ema10": _round(ema_values[10]), "ema21": _round(ema_values[21]), "ema50": _round(ema_values[50]),
            "close_vs_ema_pct": {f"ema{p}": _round(_pct(latest, ema_values[p])) for p in (10, 21, 50)},
            "ema_slope_5d_pct": {str(p): _round(_slope_pct(ema[p])) for p in (10, 21, 50)},
            "stack": "close>10>21>50" if stacked else "mixed",
        },
        "relative_strength": {
            "rs_rank": _f(rs_rank),
            "sector_relative_momentum": _f(sector_relative),
            "adr20_pct": _round(discovery_metrics.adr20(valid)),
        },
        "base_and_contraction": {
            "range_5d_pct": _round(_range_pct(valid[-5:])),
            "range_20d_pct": _round(_range_pct(valid[-20:])),
            "range_50d_pct": _round(_range_pct(valid[-50:])),
            "range20_vs_range50": _round(range20 / range50 if range20 is not None and range50 else None),
            "close_in_50d_range_pct": _round((latest - low50) / range50 * 100.0 if low50 is not None and range50 else None),
        },
        "volume_behavior": _volume_character(valid),
        "recent_path": _compact_bars(valid),
        "interpretation_contract": (
            "Observations only. Consider EP/gap-and-go, flag/VCP, IPO base, long-base Stage 2, "
            "pocket pivot, pullback and reversal as parallel hypotheses; state confirming and contradicting evidence."
        ),
    }
