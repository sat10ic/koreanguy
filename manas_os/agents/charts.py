"""Chart rendering for agent context (C1).

Pure PNG renderer: reads OHLCV rows from daily_prices, writes daily/weekly
charts under data/agent_charts, and returns paths for files actually written.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import mplfinance as mpf
import pandas as pd

CHART_ROOT = Path("data") / "agent_charts"
MIN_DAILY_BARS = 30
DAILY_BARS = 120
WEEKLY_LOOKBACK_DAYS = 730


def _daily_frame(conn, symbol: str, scan_date: str, limit: int | None = None) -> pd.DataFrame:
    sql = (
        "SELECT trade_date, open, high, low, close, volume FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL "
        "ORDER BY trade_date DESC"
    )
    params: tuple[Any, ...]
    if limit is not None:
        sql += " LIMIT ?"
        params = (symbol, scan_date, limit)
    else:
        params = (symbol, scan_date)
    rows = conn.execute(sql, params).fetchall()
    return _rows_to_frame(reversed(rows))


def _weekly_frame(conn, symbol: str, scan_date: str) -> pd.DataFrame:
    start = (date.fromisoformat(scan_date) - timedelta(days=WEEKLY_LOOKBACK_DAYS)).isoformat()
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date >= ? AND trade_date <= ? "
        "AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL "
        "ORDER BY trade_date ASC",
        (symbol, start, scan_date),
    ).fetchall()
    daily = _rows_to_frame(rows)
    if daily.empty:
        return daily
    weekly = daily.resample("W-FRI").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    return weekly.dropna(subset=["Open", "High", "Low", "Close"])


def _rows_to_frame(rows) -> pd.DataFrame:
    records = [
        {
            "Date": row["trade_date"],
            "Open": row["open"],
            "High": row["high"],
            "Low": row["low"],
            "Close": row["close"],
            "Volume": row["volume"] or 0,
        }
        for row in rows
    ]
    if not records:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    frame = pd.DataFrame.from_records(records)
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame = frame.set_index("Date").sort_index()
    return frame[["Open", "High", "Low", "Close", "Volume"]]


def _render_png(frame: pd.DataFrame, path: Path, mav: tuple[int, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mpf.plot(
        frame,
        type="candle",
        volume=True,
        mav=mav,
        style="yahoo",
        figsize=(12, 7),
        tight_layout=True,
        savefig={"fname": str(path), "dpi": 100, "bbox_inches": "tight"},
    )


def render_charts(conn, scan_date: str, symbols: list[str]) -> dict[str, dict[str, str]]:
    """Render daily and weekly PNG charts for symbols with enough OHLCV history."""
    out: dict[str, dict[str, str]] = {}
    chart_dir = CHART_ROOT / scan_date

    for symbol in symbols:
        daily_all = _daily_frame(conn, symbol, scan_date)
        if len(daily_all) < MIN_DAILY_BARS:
            out[symbol] = {"note": f"skipped: only {len(daily_all)} daily bars (<30)"}
            continue

        daily = daily_all.tail(DAILY_BARS)
        weekly = _weekly_frame(conn, symbol, scan_date)
        if weekly.empty:
            out[symbol] = {"note": "skipped: weekly resample produced no candles"}
            continue

        daily_path = chart_dir / f"{symbol}_daily.png"
        weekly_path = chart_dir / f"{symbol}_weekly.png"
        _render_png(daily, daily_path, (10, 21, 50))
        _render_png(weekly, weekly_path, (10, 30))
        out[symbol] = {"daily": str(daily_path), "weekly": str(weekly_path)}

    return out
