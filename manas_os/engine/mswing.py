"""Mswing Homma — Python port of finallynitin's Pine indicator.

Source: TradingView "Mswing Homma" (c) finallynitin, MPL-2.0, v6.
Ported for private personal use; not for redistribution.

The MOMENTUM row of the Market Quadrant. Definition, verbatim from the Pine:

    f_momentum(src, len):
        available_len = largest i in 0..len where src[i] is not na
        actual_len    = available_len if available_len > 0 else len
        return (src - src[actual_len]) * 100 / src[actual_len] / actual_len

    momo_20 = f_momentum(close, 20)
    momo_50 = f_momentum(close, 50)
    mswing  = momo_20 + momo_50

So it is percent-change-per-bar over 20 sessions plus the same over 50 -- a
speed, not a level. A stock up 20% over 20 days scores 1.0 from the fast leg;
the slow leg adds whatever the 50-day pace contributes. Summing a fast and a
slow rate is what makes it turn before a plain ROC does.

The `available_len` branch is the IPO case: a name with only 12 bars of history
would give NaN on a 20-bar lookback, so it uses the longest lookback it actually
has. Ported as-is -- it matters for recent listings, which this user trades.

Also ported: the 9-EMA of mswing (the line over the histogram), and the
index-relative colour rule -- green only when the series is BOTH above zero AND
at least as strong as its reference index.
"""
from __future__ import annotations

FAST, SLOW, EMA_LEN = 20, 50, 9


def _momentum(closes: list[float], i: int, length: int) -> float | None:
    """Pine f_momentum at bar i. `closes` is oldest-first."""
    if i <= 0:
        return None
    # largest available lookback within `length`, mirroring the Pine loop
    actual = min(length, i)
    if actual <= 0:
        return None
    prev = closes[i - actual]
    if prev is None or prev == 0:
        return None
    cur = closes[i]
    if cur is None:
        return None
    return (cur - prev) * 100.0 / prev / actual


def mswing_series(closes: list[float]) -> list[float | None]:
    """Mswing at every bar. Same length as `closes`, None where uncomputable."""
    out: list[float | None] = []
    for i in range(len(closes)):
        f = _momentum(closes, i, FAST)
        s = _momentum(closes, i, SLOW)
        out.append(None if (f is None or s is None) else f + s)
    return out


def ema(values: list[float | None], length: int = EMA_LEN) -> list[float | None]:
    """EMA over a series that may start with Nones."""
    k = 2.0 / (length + 1)
    out: list[float | None] = []
    prev = None
    for v in values:
        if v is None:
            out.append(prev)
            continue
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def state(value: float | None, index_value: float | None) -> str:
    """The Pine's colour rule, as a word.

    green   above zero AND at least as strong as the reference index
    orange  one of the two, not both
    red     below zero and weaker than the index
    """
    if value is None:
        return "unknown"
    if index_value is None:
        return "up" if value > 0 else "down"
    if value > 0 and value >= index_value:
        return "up"
    if value > 0 or value >= index_value:
        return "mixed"
    return "down"


def for_symbol(conn, symbol: str, as_of: str, lookback: int = 120) -> dict:
    """Mswing history for one index symbol from sector_index_prices."""
    rows = conn.execute(
        "SELECT trade_date, close FROM sector_index_prices "
        "WHERE symbol=? AND trade_date<=? ORDER BY trade_date DESC LIMIT ?",
        (symbol, as_of, lookback + SLOW + 5),
    ).fetchall()
    rows = list(reversed(rows))
    if len(rows) < SLOW + 2:
        return {"symbol": symbol, "available": False, "rows": [],
                "reason": f"needs {SLOW + 2} sessions, has {len(rows)}"}
    dates = [r["trade_date"] for r in rows]
    closes = [r["close"] for r in rows]
    ms = mswing_series(closes)
    ma = ema(ms)
    out = [
        {"trade_date": d, "mswing": (round(m, 4) if m is not None else None),
         "mswing_ema": (round(e, 4) if e is not None else None)}
        for d, m, e in zip(dates, ms, ma)
    ][-lookback:]
    return {"symbol": symbol, "available": True, "rows": out,
            "latest": out[-1] if out else None,
            "as_of": dates[-1] if dates else None}
