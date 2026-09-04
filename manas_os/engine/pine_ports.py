"""Small deterministic ports of Pine-style chart studies.

These functions are rules-first and return plain-English evidence strings. They
do not import Pine code; they reimplement the supplied Moving Average Relative
Strength idea for symbol-vs-benchmark chart context.
"""
from __future__ import annotations

from typing import Any

from manas_os.regime.sectors import STATE_LABELS, classify_state, sma


def _close(bar: dict[str, Any]) -> float | None:
    value = bar.get("close")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def moving_average_relative_strength(
    subject_bars: list[dict[str, Any]],
    benchmark_bars: list[dict[str, Any]],
    ma_length: int = 50,
) -> dict[str, Any]:
    """Pine-style MA relative strength for the latest bar.

    MARS = subject distance from SMA - benchmark distance from SMA. The state
    uses the same six-rule classification as the sector MARS implementation.
    """
    subject_closes = [_close(b) for b in subject_bars if _close(b) is not None]
    benchmark_closes = [_close(b) for b in benchmark_bars if _close(b) is not None]
    if len(subject_closes) < ma_length or len(benchmark_closes) < ma_length:
        return {
            "available": False,
            "state": None,
            "value": None,
            "detail": f"Insufficient history for {ma_length}-bar MA relative strength.",
        }
    subject_close = subject_closes[-1]
    benchmark_close = benchmark_closes[-1]
    subject_ma = sma(subject_closes, ma_length)
    benchmark_ma = sma(benchmark_closes, ma_length)
    if not subject_ma or not benchmark_ma:
        return {"available": False, "state": None, "value": None, "detail": "MA baseline unavailable."}

    subject_pct = (subject_close - subject_ma) / subject_ma * 100.0
    benchmark_pct = (benchmark_close - benchmark_ma) / benchmark_ma * 100.0
    value = round(subject_pct - benchmark_pct, 2)
    state = classify_state(
        value,
        sector_above_ma=subject_close > subject_ma,
        index_above_ma=benchmark_close > benchmark_ma,
    )
    label = STATE_LABELS.get(state, state)
    return {
        "available": True,
        "state": state,
        "value": value,
        "detail": (
            f"Symbol is {subject_pct:.2f}% from its {ma_length}SMA while benchmark is "
            f"{benchmark_pct:.2f}% from its {ma_length}SMA; MARS {value:+.2f} ({label})."
        ),
    }


def symbol_mars(
    conn,
    symbol: str,
    as_of_date: str,
    benchmark: str = "NIFTYMIDSML400",
    ma_length: int = 50,
) -> dict[str, Any]:
    def _bars(sym: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT trade_date AS date, close FROM daily_prices "
            "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
            "ORDER BY trade_date DESC LIMIT ?",
            (sym, as_of_date, ma_length + 20),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    result = moving_average_relative_strength(_bars(symbol.upper()), _bars(benchmark), ma_length)
    return {**result, "benchmark": benchmark, "ma_length": ma_length}
