"""Deterministic price-action detectors for NSE swing-trading workflows.

Pure detector functions accept OHLCV bars in date-ascending order and return
plain-English evidence with every signal. The DB helper only reads
``daily_prices``; it does not write metrics or wire into the pipeline runner.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any


Bar = dict[str, Any]
Signal = dict[str, Any]


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _date(bar: Bar) -> Any:
    return bar.get("date") or bar.get("trade_date")


def _ema(values: list[float | None], span: int) -> list[float | None]:
    alpha = 2.0 / (span + 1.0)
    out: list[float | None] = []
    prev: float | None = None
    for value in values:
        if value is None:
            out.append(prev)
            continue
        prev = value if prev is None else (value * alpha) + (prev * (1.0 - alpha))
        out.append(prev)
    return out


def _sma_at(values: list[float | None], end_idx: int, window: int) -> float | None:
    if end_idx + 1 < window:
        return None
    chunk = values[end_idx - window + 1 : end_idx + 1]
    if any(v is None for v in chunk):
        return None
    return sum(v for v in chunk if v is not None) / window


def _closes(bars: list[Bar]) -> list[float | None]:
    return [_num(bar.get("close")) for bar in bars]


def detect_ema_events(bars: list[Bar], spans: Iterable[int] = (10, 21, 50)) -> list[Signal]:
    """Detect EMA touches, losses, and reclaims on date-ascending OHLC bars."""
    closes = _closes(bars)
    signals: list[Signal] = []
    ema_by_span = {span: _ema(closes, span) for span in spans}

    for idx, bar in enumerate(bars):
        low = _num(bar.get("low"))
        high = _num(bar.get("high"))
        close = closes[idx]
        if low is None or high is None or close is None:
            continue
        for span, ema_values in ema_by_span.items():
            ema_now = ema_values[idx]
            if ema_now is None:
                continue
            label = f"{span}EMA"
            if low <= ema_now <= high and close > ema_now:
                signals.append({
                    "date": _date(bar),
                    "kind": f"EMA{span}_TOUCH",
                    "detail": (
                        f"Price tested the {label} and held "
                        f"(low {_fmt(low)} vs EMA {_fmt(ema_now)})."
                    ),
                })
            if idx == 0:
                continue
            prev_close = closes[idx - 1]
            prev_ema = ema_values[idx - 1]
            if prev_close is None or prev_ema is None:
                continue
            if prev_close >= prev_ema and close < ema_now:
                signals.append({
                    "date": _date(bar),
                    "kind": f"EMA{span}_LOSS",
                    "detail": (
                        f"Price closed below the {label} "
                        f"(close {_fmt(close)} vs EMA {_fmt(ema_now)})."
                    ),
                })
            elif prev_close <= prev_ema and close > ema_now:
                signals.append({
                    "date": _date(bar),
                    "kind": f"EMA{span}_RECLAIM",
                    "detail": (
                        f"Price reclaimed the {label} after being below it "
                        f"(close {_fmt(close)} vs EMA {_fmt(ema_now)})."
                    ),
                })
    return signals


def trailing_stop_state(bars: list[Bar], fast: int = 15, slow: int = 21) -> dict[str, Any]:
    """Current status for the 15/21-EMA trailing method."""
    if not bars:
        return {"status": None, "stop_level": None, "detail": "No bars available."}

    closes = _closes(bars)
    close = closes[-1]
    fast_ema = _ema(closes, fast)[-1]
    slow_ema = _ema(closes, slow)[-1]
    if close is None or fast_ema is None or slow_ema is None:
        return {"status": None, "stop_level": None, "detail": "Latest close or EMA is unavailable."}

    if close < slow_ema:
        return {
            "status": "TRAIL_HIT_SLOW",
            "stop_level": slow_ema,
            "detail": (
                f"Close {_fmt(close)} is below the {slow}EMA {_fmt(slow_ema)}; "
                "full trailing stop is hit."
            ),
        }
    if close < fast_ema:
        return {
            "status": "TRAIL_HIT_FAST",
            "stop_level": fast_ema,
            "detail": (
                f"Close {_fmt(close)} is below the {fast}EMA {_fmt(fast_ema)}; "
                "fast trailing warning for partial exit."
            ),
        }
    return {
        "status": "HOLD",
        "stop_level": fast_ema,
        "detail": (
            f"Close {_fmt(close)} is above the {fast}EMA {_fmt(fast_ema)} "
            f"and {slow}EMA {_fmt(slow_ema)}; trail remains intact."
        ),
    }


def detect_shakeout(bars: list[Bar], lookback: int = 10) -> list[Signal]:
    """Detect undercut-and-reclaim shakeouts versus the prior lookback low."""
    signals: list[Signal] = []
    for idx in range(lookback, len(bars)):
        prior_lows = [_num(b.get("low")) for b in bars[idx - lookback : idx]]
        if any(v is None for v in prior_lows):
            continue
        prior_low = min(v for v in prior_lows if v is not None)
        bar = bars[idx]
        low = _num(bar.get("low"))
        open_ = _num(bar.get("open"))
        close = _num(bar.get("close"))
        if low is None or close is None:
            continue
        if low < prior_low and close > prior_low:
            open_detail = ""
            if open_ is not None and close > open_:
                open_detail = f" and above open {_fmt(open_)}"
            signals.append({
                "date": _date(bar),
                "kind": "SHAKEOUT",
                "detail": (
                    f"Undercut {lookback}-day low {_fmt(prior_low)} intraday, "
                    f"closed {_fmt(close)} back above it{open_detail}, shakeout."
                ),
            })
    return signals


def detect_pocket_pivots(bars: list[Bar], lookback: int = 10) -> list[Signal]:
    """Detect up-day pocket pivots with upper-half close and close above 10EMA."""
    closes = _closes(bars)
    ema10 = _ema(closes, 10)
    signals: list[Signal] = []

    for idx in range(lookback, len(bars)):
        prior = bars[idx - lookback : idx]
        down_volumes: list[float] = []
        for pbar in prior:
            pclose = _num(pbar.get("close"))
            popen = _num(pbar.get("open"))
            pvolume = _num(pbar.get("volume"))
            if pclose is not None and popen is not None and pvolume is not None and pclose < popen:
                down_volumes.append(pvolume)
        if not down_volumes:
            continue

        bar = bars[idx]
        open_ = _num(bar.get("open"))
        high = _num(bar.get("high"))
        low = _num(bar.get("low"))
        close = closes[idx]
        volume = _num(bar.get("volume"))
        ema_now = ema10[idx]
        if None in (open_, high, low, close, volume, ema_now):
            continue
        assert open_ is not None and high is not None and low is not None
        assert close is not None and volume is not None and ema_now is not None
        max_down_volume = max(down_volumes)
        upper_half = close >= low + ((high - low) / 2.0)
        if close > open_ and volume > max_down_volume and upper_half and close > ema_now:
            signals.append({
                "date": _date(bar),
                "kind": "POCKET_PIVOT",
                "detail": (
                    f"Up-day volume {int(volume)} exceeded prior {lookback}-day "
                    f"max down-day volume {int(max_down_volume)}, closed in upper half "
                    f"and above 10EMA {_fmt(ema_now)}."
                ),
            })
    return signals


def weinstein_stage(bars: list[Bar]) -> dict[str, Any]:
    """Classify Weinstein stage from 150-day SMA position and 20-bar SMA slope."""
    closes = _closes(bars)
    if len(closes) < 150:
        return {
            "stage": None,
            "detail": f"Insufficient history for 150-day SMA ({len(closes)} bars available).",
        }
    idx = len(closes) - 1
    sma_now = _sma_at(closes, idx, 150)
    if sma_now is None:
        return {"stage": None, "detail": "Insufficient valid closes for 150-day SMA."}
    slope_idx = max(0, idx - 20)
    sma_then = _sma_at(closes, slope_idx, 150)
    close = closes[-1]
    if close is None:
        return {"stage": None, "detail": "Latest close is unavailable."}

    if sma_then is None:
        slope = 0.0
        slope_detail = "150-day SMA slope treated as flat because 20-bar prior SMA is unavailable"
    else:
        slope = sma_now - sma_then
        slope_detail = f"150-day SMA moved from {_fmt(sma_then)} to {_fmt(sma_now)} over 20 bars"

    flat_band = sma_now * 0.01
    near_band = sma_now * 0.03
    rising = slope > flat_band
    falling = slope < -flat_band
    near_sma = abs(close - sma_now) <= near_band

    if close > sma_now and rising:
        stage = 2
        label = "advancing"
    elif close < sma_now and falling:
        stage = 4
        label = "declining"
    elif close >= sma_now and falling:
        stage = 3
        label = "topping"
    elif near_sma:
        stage = 1
        label = "basing"
    elif close < sma_now:
        stage = 1
        label = "basing below a flat 150-day SMA"
    else:
        stage = 3
        label = "topping above a flat 150-day SMA"

    return {
        "stage": stage,
        "detail": (
            f"Stage {stage} ({label}): close {_fmt(close)} vs 150-day SMA {_fmt(sma_now)}; "
            f"{slope_detail}."
        ),
    }


def signals_for_symbol(conn, symbol: str, as_of_date: str, max_bars: int = 260) -> dict[str, Any]:
    """Load EQ daily prices and return current price-action state for one symbol."""
    rows = conn.execute(
        "SELECT trade_date AS date, open, high, low, close, prev_close, volume, "
        "delivery_qty, delivery_pct "
        "FROM daily_prices WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        (symbol, as_of_date, max_bars),
    ).fetchall()
    bars = [dict(row) for row in reversed(rows)]

    signals: list[Signal] = []
    signals.extend(detect_ema_events(bars))
    signals.extend(detect_shakeout(bars))
    signals.extend(detect_pocket_pivots(bars))
    signals.sort(key=lambda s: s.get("date") or "", reverse=True)

    return {
        "symbol": symbol,
        "as_of": as_of_date,
        "stage": weinstein_stage(bars),
        "trail": trailing_stop_state(bars),
        "recent_signals": signals[:15],
    }
