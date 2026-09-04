"""Import Nifty 500 fundamentals into Manas symbol_quality.

The scanner consumes a compact quality row:
market_cap_cr, asm_stage, eps_qoq, eps_yoy, sales_yoy, opm_yoy, is_fno, exchange.

This importer downloads the official Nifty 500 constituents CSV and uses
yfinance's NSE Yahoo symbols (`RELIANCE.NS`) for market cap and quarterly income
statement fields. Fields that are not reliably available from this source
(ASM/GSM and F&O membership) are left NULL rather than guessed.
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "manas_os" / "data" / "manas_backtest_2y.db"
SCHEMA_PATH = ROOT / "manas_os" / "db" / "schema.sql"
NIFTY500_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"


def fetch_nifty500() -> list[dict[str, str]]:
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,*/*",
            "Referer": "https://www.niftyindices.com/",
        }
    )
    resp = sess.get(NIFTY500_URL, timeout=30)
    resp.raise_for_status()
    rows = []
    for row in csv.DictReader(io.StringIO(resp.text.lstrip("\ufeff"))):
        sym = (row.get("Symbol") or "").strip().upper()
        series = (row.get("Series") or "").strip().upper()
        if sym and series == "EQ":
            rows.append(row)
    return rows


def pct_change(new: Any, old: Any) -> float | None:
    if new is None or old is None:
        return None
    try:
        new_f = float(new)
        old_f = float(old)
    except (TypeError, ValueError):
        return None
    if not pd.notna(new_f) or not pd.notna(old_f) or old_f == 0:
        return None
    return (new_f - old_f) / abs(old_f) * 100.0


def row_value(frame: pd.DataFrame, names: list[str], pos: int) -> float | None:
    if frame.empty or pos >= len(frame.columns):
        return None
    for name in names:
        if name in frame.index:
            value = frame.loc[name].iloc[pos]
            if pd.notna(value):
                return float(value)
    return None


def quality_for_symbol(symbol: str) -> dict[str, Any]:
    ticker = yf.Ticker(symbol + ".NS")
    info: dict[str, Any] = {}
    try:
        info = ticker.get_info() or {}
    except Exception:
        info = {}

    market_cap = info.get("marketCap")
    market_cap_cr = None
    if market_cap is not None:
        try:
            market_cap_cr = float(market_cap) / 10_000_000.0
        except (TypeError, ValueError):
            market_cap_cr = None

    eps_qoq = eps_yoy = sales_yoy = opm_yoy = None
    try:
        q = ticker.quarterly_income_stmt
    except Exception:
        q = pd.DataFrame()

    if not q.empty:
        q = q.sort_index(axis=1, ascending=False)
        eps_latest = row_value(q, ["Diluted EPS", "Basic EPS"], 0)
        eps_prev = row_value(q, ["Diluted EPS", "Basic EPS"], 1)
        eps_year_ago = row_value(q, ["Diluted EPS", "Basic EPS"], 4)
        eps_qoq = pct_change(eps_latest, eps_prev)
        eps_yoy = pct_change(eps_latest, eps_year_ago)

        rev_latest = row_value(q, ["Total Revenue", "Operating Revenue"], 0)
        rev_year_ago = row_value(q, ["Total Revenue", "Operating Revenue"], 4)
        sales_yoy = pct_change(rev_latest, rev_year_ago)

        op_latest = row_value(q, ["Operating Income", "EBIT"], 0)
        op_year_ago = row_value(q, ["Operating Income", "EBIT"], 4)
        if rev_latest and rev_year_ago and op_latest is not None and op_year_ago is not None:
            opm_latest = float(op_latest) / float(rev_latest) * 100.0
            opm_year_ago = float(op_year_ago) / float(rev_year_ago) * 100.0
            opm_yoy = opm_latest - opm_year_ago

    # Yahoo's earningsQuarterlyGrowth/revenueGrowth are useful fallbacks but are
    # often absent for India. They are fractions, so convert to percent.
    if eps_yoy is None and info.get("earningsQuarterlyGrowth") is not None:
        eps_yoy = float(info["earningsQuarterlyGrowth"]) * 100.0
    if sales_yoy is None and info.get("revenueGrowth") is not None:
        sales_yoy = float(info["revenueGrowth"]) * 100.0

    return {
        "symbol": symbol,
        "market_cap_cr": market_cap_cr,
        "asm_stage": None,
        "eps_qoq": eps_qoq,
        "eps_yoy": eps_yoy,
        "sales_yoy": sales_yoy,
        "opm_yoy": opm_yoy,
        "is_fno": None,
        "exchange": "NSE",
    }


def upsert(conn: sqlite3.Connection, as_of: str, rows: list[dict[str, Any]]) -> int:
    payload = [{**row, "trade_date": as_of} for row in rows]
    conn.executemany(
        """
        INSERT OR REPLACE INTO symbol_quality
        (trade_date, symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy,
         sales_yoy, opm_yoy, is_fno, exchange)
        VALUES
        (:trade_date, :symbol, :market_cap_cr, :asm_stage, :eps_qoq, :eps_yoy,
         :sales_yoy, :opm_yoy, :is_fno, :exchange)
        """,
        payload,
    )
    return len(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import Nifty 500 fundamentals into symbol_quality")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--commit-every", type=int, default=25)
    args = parser.parse_args(argv)

    constituents = fetch_nifty500()
    if args.limit:
        constituents = constituents[: args.limit]
    symbols = [row["Symbol"].strip().upper() for row in constituents]
    print(f"symbols={len(symbols)} as_of={args.as_of}", flush=True)

    conn = sqlite3.connect(args.db, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()

    ok: list[dict[str, Any]] = []
    failed: list[str] = []
    started = time.monotonic()
    try:
        for idx, symbol in enumerate(symbols, start=1):
            try:
                row = quality_for_symbol(symbol)
                # Count as useful if at least market cap or one growth leg exists.
                if any(row.get(k) is not None for k in ("market_cap_cr", "eps_qoq", "eps_yoy", "sales_yoy", "opm_yoy")):
                    ok.append(row)
                else:
                    failed.append(symbol)
            except Exception:
                failed.append(symbol)

            if idx % args.commit_every == 0:
                wrote = upsert(conn, args.as_of, ok)
                conn.commit()
                ok.clear()
                print(f"processed {idx}/{len(symbols)} wrote+={wrote} failed={len(failed)}", flush=True)
            time.sleep(args.sleep)

        wrote = upsert(conn, args.as_of, ok)
        conn.commit()
        ok.clear()
        coverage = conn.execute(
            """
            SELECT COUNT(*) AS rows,
                   SUM(CASE WHEN market_cap_cr IS NOT NULL THEN 1 ELSE 0 END) AS market_cap_rows,
                   SUM(CASE WHEN eps_yoy IS NOT NULL THEN 1 ELSE 0 END) AS eps_yoy_rows,
                   SUM(CASE WHEN sales_yoy IS NOT NULL THEN 1 ELSE 0 END) AS sales_yoy_rows,
                   SUM(CASE WHEN opm_yoy IS NOT NULL THEN 1 ELSE 0 END) AS opm_yoy_rows
            FROM symbol_quality
            WHERE trade_date=?
            """,
            (args.as_of,),
        ).fetchone()
        print(f"final write += {wrote}")
        print(
            "done: rows={0} market_cap={1} eps_yoy={2} sales_yoy={3} opm_yoy={4} failed={5} elapsed={6:.1f}s".format(
                coverage[0], coverage[1], coverage[2], coverage[3], coverage[4], len(failed), time.monotonic() - started
            )
        )
        if failed:
            print("failed:", ",".join(failed[:100]) + ("..." if len(failed) > 100 else ""))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
