"""Import all NSE index daily closes into Manas sector_index_prices.

NSE publishes a daily CSV containing every index:
https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv

The Manas schema currently stores index history as (symbol, trade_date, close,
sma50), so this importer writes each NSE "Index Name" as the symbol and computes
SMA50 locally after import. Missing/non-trading days are skipped.
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "manas_os" / "data" / "manas_backtest_2y.db"
SCHEMA_PATH = ROOT / "manas_os" / "db" / "schema.sql"
ARCHIVE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{datecode}.csv"


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,*/*",
            "Referer": "https://www.nseindia.com/",
        }
    )
    sess.get("https://www.nseindia.com", timeout=15)
    return sess


def fetch_day(sess: requests.Session, day: date, retries: int = 2) -> list[dict]:
    url = ARCHIVE_URL.format(datecode=day.strftime("%d%m%Y"))
    for attempt in range(retries + 1):
        try:
            resp = sess.get(url, timeout=20)
            if resp.status_code in {404, 403}:
                return []
            resp.raise_for_status()
            text = resp.text.lstrip("\ufeff")
            if not text.startswith("Index Name"):
                return []
            rows = []
            for row in csv.DictReader(io.StringIO(text)):
                name = (row.get("Index Name") or "").strip()
                close = parse_float(row.get("Closing Index Value"))
                if not name or close is None:
                    continue
                rows.append(
                    {
                        "symbol": name,
                        "trade_date": day.isoformat(),
                        "close": close,
                    }
                )
            return rows
        except requests.RequestException:
            if attempt >= retries:
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def upsert_rows(conn: sqlite3.Connection, rows: list[dict]) -> int:
    conn.executemany(
        """
        INSERT OR REPLACE INTO sector_index_prices
        (symbol, trade_date, close, sma50)
        VALUES (:symbol, :trade_date, :close, NULL)
        """,
        rows,
    )
    return len(rows)


def recompute_sma50(conn: sqlite3.Connection) -> None:
    symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM sector_index_prices ORDER BY symbol")]
    for symbol in symbols:
        rows = conn.execute(
            "SELECT trade_date, close FROM sector_index_prices WHERE symbol=? ORDER BY trade_date",
            (symbol,),
        ).fetchall()
        updates = []
        closes: list[float] = []
        for trade_date, close in rows:
            closes.append(float(close))
            sma = sum(closes[-50:]) / 50.0 if len(closes) >= 50 else None
            updates.append((sma, symbol, trade_date))
        conn.executemany(
            "UPDATE sector_index_prices SET sma50=? WHERE symbol=? AND trade_date=?",
            updates,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import all NSE index closes into sector_index_prices")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--start", default="2024-07-06")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--sleep", type=float, default=0.05)
    args = parser.parse_args(argv)

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()

    sess = session()
    total_rows = 0
    days_hit = 0
    started = time.monotonic()
    try:
        for idx, day in enumerate(daterange(start, end), start=1):
            rows = fetch_day(sess, day)
            if rows:
                total_rows += upsert_rows(conn, rows)
                days_hit += 1
            if idx % 25 == 0:
                conn.commit()
                print(f"checked {idx} days, trading_days={days_hit}, rows={total_rows}", flush=True)
            time.sleep(args.sleep)
        conn.commit()
        print("recomputing sma50...", flush=True)
        recompute_sma50(conn)
        conn.commit()
        coverage = conn.execute(
            """
            SELECT COUNT(*) AS rows, COUNT(DISTINCT symbol) AS indices,
                   MIN(trade_date) AS start_date, MAX(trade_date) AS end_date
            FROM sector_index_prices
            """
        ).fetchone()
        print(
            "done: rows={0} indices={1} start={2} end={3} elapsed={4:.1f}s".format(
                coverage[0], coverage[1], coverage[2], coverage[3], time.monotonic() - started
            )
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
