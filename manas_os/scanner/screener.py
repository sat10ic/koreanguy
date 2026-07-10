"""Chartink-style screener over existing per-symbol metrics (WAVE_M amendment,
user order 2026-07-11 ~09:30: "can't we have a screener option like Chartink..
from which we can push the stock to the debate panel").

Additive, read-only: computes a per-symbol metrics snapshot for the latest
(or given) trade date from daily_prices + the same metric functions
discovery.py already uses (discovery_metrics.py), plus scan_candidates.load
_symbol_bars/candidates.stock_rs_map for RS. Never writes candidates/
refusals; never gates the scanner. `apply_conditions` is a small AND-only
Chartink-style filter over that snapshot.
"""
from __future__ import annotations

from typing import Any

from manas_os.engine import eod_detectors
from manas_os.scanner import discovery_metrics as dm

Bar = dict[str, Any]

FIELDS = (
    "close", "pct_change_1d", "volume", "adr20", "rs", "pct_off_52w_high",
    "pct_up_from_65d_low", "purple_dot_count_60d", "delivery_pct",
    "ema10", "ema21", "ema50", "above_ema10", "above_ema21", "above_ema50",
)

# Built-in presets (user order 2026-07-11 ~09:30). Conditions are AND-ed,
# same shape the API accepts: {field, op, value}.
PRESETS: dict[str, dict[str, Any]] = {
    "TODAYS_MOVERS": {
        "label": "Today's Movers",
        "description": "pct_change_1d>=5, volume>=1,000,000, adr20>=4 — day-1 bursts "
                        "feed the D2 watch per doctrine.",
        "conditions": [
            {"field": "pct_change_1d", "op": "gte", "value": 5.0},
            {"field": "volume", "op": "gte", "value": 1_000_000},
            {"field": "adr20", "op": "gte", "value": 4.0},
        ],
    },
}

_OPS = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
}


def _universe_symbols(conn, as_of: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date = ?",
        (as_of,),
    ).fetchall()
    return [r["symbol"] for r in rows]


def _load_bars(conn, symbol: str, as_of: str, limit: int = 260) -> list[Bar]:
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol.upper(), as_of, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _closes(bars: list[Bar]) -> list[float | None]:
    out = []
    for b in bars:
        v = b.get("close")
        out.append(float(v) if v is not None else None)
    return out


def metrics_for_symbol(conn, symbol: str, as_of: str, bars: list[Bar] | None = None,
                        rs_map: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """One symbol's screenable snapshot as-of `as_of`. None when there is no
    price row on that date (nothing to screen)."""
    bars = bars if bars is not None else _load_bars(conn, symbol, as_of)
    if not bars or bars[-1].get("date") != as_of:
        return None
    last = bars[-1]
    close = last.get("close")
    prev_close = last.get("prev_close")
    if prev_close is None and len(bars) >= 2:
        prev_close = bars[-2].get("close")
    pct_change_1d = None
    if close is not None and prev_close:
        try:
            pct_change_1d = round((float(close) - float(prev_close)) / float(prev_close) * 100.0, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            pct_change_1d = None

    highs = [b.get("high") for b in bars if b.get("high") is not None]
    high_252 = max(float(h) for h in highs) if highs else None
    pct_off_52w_high = None
    if close is not None and high_252:
        try:
            pct_off_52w_high = round((1.0 - float(close) / high_252) * 100.0, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            pct_off_52w_high = None

    closes = _closes(bars)
    e10 = eod_detectors.ema(closes, 10)
    e21 = eod_detectors.ema(closes, 21)
    e50 = eod_detectors.ema(closes, 50)
    ema10 = e10[-1] if e10 else None
    ema21 = e21[-1] if e21 else None
    ema50 = e50[-1] if e50 else None

    rs_entry = (rs_map or {}).get(symbol.upper()) or {}
    rs = rs_entry.get("rs")

    return {
        "symbol": symbol.upper(),
        "close": close,
        "pct_change_1d": pct_change_1d,
        "volume": last.get("volume"),
        "adr20": dm.adr20(bars),
        "rs": rs,
        "pct_off_52w_high": pct_off_52w_high,
        "pct_up_from_65d_low": dm.pct_up_from_65d_low(bars),
        "purple_dot_count_60d": dm.purple_dot_count_60d(bars),
        "delivery_pct": last.get("delivery_pct"),
        "ema10": round(ema10, 2) if ema10 is not None else None,
        "ema21": round(ema21, 2) if ema21 is not None else None,
        "ema50": round(ema50, 2) if ema50 is not None else None,
        "above_ema10": bool(close is not None and ema10 is not None and close > ema10),
        "above_ema21": bool(close is not None and ema21 is not None and close > ema21),
        "above_ema50": bool(close is not None and ema50 is not None and close > ema50),
    }


def latest_universe_metrics(conn, as_of: str) -> list[dict[str, Any]]:
    """Metrics snapshot for every symbol priced on `as_of`. Pure read."""
    from manas_os.scanner.candidates import stock_rs_map

    symbols = _universe_symbols(conn, as_of)
    if not symbols:
        return []
    rs_map = stock_rs_map(as_of)
    out = []
    for sym in symbols:
        m = metrics_for_symbol(conn, sym, as_of, rs_map=rs_map)
        if m is not None:
            out.append(m)
    return out


def apply_conditions(rows: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chartink-style AND-only filter: [{field, op(gt/lt/gte/lte), value}, ...]."""
    if not conditions:
        return list(rows)
    out = []
    for row in rows:
        ok = True
        for cond in conditions:
            field = str(cond.get("field") or "")
            op = str(cond.get("op") or "").lower()
            value = cond.get("value")
            fn = _OPS.get(op)
            if field not in FIELDS or fn is None or value is None:
                ok = False
                break
            actual = row.get(field)
            if actual is None:
                ok = False
                break
            try:
                if not fn(float(actual), float(value)):
                    ok = False
                    break
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            out.append(row)
    return out


def ensure_screens_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_screens ("
        "name TEXT PRIMARY KEY, conditions_json TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )
