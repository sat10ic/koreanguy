"""Import two-year NSE daily OHLCV history into Manas daily_prices.

Finstack's historical MCP output is Yahoo-style OHLCV. The MCP server itself is
not exposed as an importable batch API here, so this script uses yfinance for
the same NSE Yahoo symbols (`RELIANCE.NS`) and writes the result into the Manas
SQLite schema. It is idempotent.
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "manas_os" / "data" / "manas.db"
DEFAULT_UNIVERSE = ROOT / "manas_os" / "data" / "niftymidsml400_constituents.csv"
SCHEMA_PATH = ROOT / "manas_os" / "db" / "schema.sql"


def symbols_from_csv(path: Path, limit: int | None = None) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        field = "Symbol" if "Symbol" in (reader.fieldnames or []) else "symbol"
        out = []
        for row in reader:
            sym = (row.get(field) or "").strip().upper()
            series = (row.get("Series") or row.get("series") or "EQ").strip().upper()
            if sym and series == "EQ":
                out.append(sym)
            if limit and len(out) >= limit:
                break
        return list(dict.fromkeys(out))


def chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def normalize_download(raw: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
    if raw.empty:
        return {}
    out: dict[str, pd.DataFrame] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance may group by ticker or by price depending on version/options.
        level0 = set(str(v) for v in raw.columns.get_level_values(0))
        if any(s + ".NS" in level0 for s in symbols):
            for sym in symbols:
                ticker = sym + ".NS"
                if ticker in raw.columns.get_level_values(0):
                    out[sym] = raw[ticker].copy()
        else:
            for sym in symbols:
                ticker = sym + ".NS"
                try:
                    out[sym] = raw.xs(ticker, axis=1, level=1).copy()
                except KeyError:
                    pass
    elif len(symbols) == 1:
        out[symbols[0]] = raw.copy()
    return out


def records_for_symbol(symbol: str, frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    frame = frame.rename(columns={c: str(c).lower().replace(" ", "_") for c in frame.columns})
    need = {"open", "high", "low", "close", "volume"}
    if not need.issubset(frame.columns):
        return []
    frame = frame.reset_index()
    date_col = "Date" if "Date" in frame.columns else "date"
    frame[date_col] = pd.to_datetime(frame[date_col]).dt.date.astype(str)
    frame = frame.sort_values(date_col)
    frame["prev_close"] = frame["close"].shift(1)
    records = []
    for row in frame.itertuples(index=False):
        data = row._asdict()
        close = data.get("close")
        if pd.isna(close):
            continue
        volume = data.get("volume")
        records.append(
            {
                "symbol": symbol,
                "trade_date": data[date_col],
                "series": "EQ",
                "open": None if pd.isna(data.get("open")) else float(data.get("open")),
                "high": None if pd.isna(data.get("high")) else float(data.get("high")),
                "low": None if pd.isna(data.get("low")) else float(data.get("low")),
                "close": float(close),
                "prev_close": None if pd.isna(data.get("prev_close")) else float(data.get("prev_close")),
                "volume": 0 if pd.isna(volume) else int(volume),
                "source": "finstack_yahoo",
            }
        )
    return records


def upsert(conn: sqlite3.Connection, records: list[dict]) -> int:
    conn.executemany(
        """
        INSERT OR REPLACE INTO daily_prices
        (symbol, trade_date, series, open, high, low, close, prev_close,
         volume, source)
        VALUES
        (:symbol, :trade_date, :series, :open, :high, :low, :close, :prev_close,
         :volume, :source)
        """,
        records,
    )
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import NSE OHLCV history into Manas daily_prices")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--period", default="2y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of symbols for a smoke run")
    parser.add_argument("--chunk-size", type=int, default=40)
    args = parser.parse_args(argv)

    symbols = symbols_from_csv(args.universe, args.limit)
    if not symbols:
        raise SystemExit(f"No symbols found in {args.universe}")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    started = time.monotonic()
    total = 0
    failed: list[str] = []
    try:
        for batch_no, batch in enumerate(chunks(symbols, args.chunk_size), start=1):
            tickers = " ".join(sym + ".NS" for sym in batch)
            print(f"batch {batch_no}: fetching {len(batch)} symbols", flush=True)
            raw = yf.download(
                tickers,
                period=args.period,
                interval=args.interval,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            by_symbol = normalize_download(raw, batch)
            batch_records = []
            for sym in batch:
                frame = by_symbol.get(sym)
                records = records_for_symbol(sym, frame) if frame is not None else []
                if records:
                    batch_records.extend(records)
                else:
                    failed.append(sym)
            total += upsert(conn, batch_records)
            conn.commit()
            print(f"  wrote {len(batch_records)} rows (total {total})", flush=True)
        latest = conn.execute("SELECT MAX(trade_date) FROM daily_prices WHERE source='finstack_yahoo'").fetchone()[0]
        print(f"done: {total} rows, {len(failed)} failed/empty, latest={latest}, elapsed={time.monotonic()-started:.1f}s")
        if failed:
            print("failed:", ",".join(failed[:80]) + ("..." if len(failed) > 80 else ""))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
