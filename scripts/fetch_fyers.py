"""Fyers-based OHLCV fetcher for SwingEdge Lite.

Replaces fetch_yf.py. Pulls daily bars for every symbol in universe.csv
plus _NIFTY50, then computes _NF500EW from the universe.

Fyers symbol format: NSE:{SYM}-EQ for equities, NSE:NIFTY50-INDEX for the
benchmark.

The Fyers /data/history endpoint caps each request at ~366 days and 100
calls/sec, so for a fresh backfill (504 days) we issue two requests per
symbol back-to-back.
"""
from __future__ import annotations

import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _symbol_map
from scripts._fyers_token import fyers_client


def setup_logger():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("fetch_fyers")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("logs/fetch_fyers.log")
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


logger = setup_logger()
config = _config.load_config()


def fyers_symbol(sym: str) -> str | None:
    """Map our internal symbol to Fyers's symbol notation.

    Returns None for delisted symbols (caller should skip). Equity symbols are
    resolved through _symbol_map to handle NSE rebrands/short-symbol changes.
    """
    if sym == "_NIFTY50":
        return "NSE:NIFTY50-INDEX"
    if sym == "_INDIAVIX":
        return "NSE:INDIAVIX-INDEX"
    resolved = _symbol_map.resolve(sym)
    if resolved is None:
        return None  # delisted
    return f"NSE:{resolved}-EQ"


def upsert_ohlcv(conn, records):
    if not records:
        return
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(symbol, date) DO UPDATE SET
             open=excluded.open, high=excluded.high, low=excluded.low,
             close=excluded.close, volume=excluded.volume""",
        records,
    )
    conn.commit()


def get_last_date(conn, sym):
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM ohlcv WHERE symbol=?", (sym,))
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def compute_ew_index(conn):
    df = pd.read_sql_query(
        "SELECT symbol, date, close FROM ohlcv WHERE symbol NOT IN ('_NIFTY50', '_NF500EW')",
        conn,
    )
    if df.empty:
        return
    df["date"] = pd.to_datetime(df["date"])
    pv = df.pivot(index="date", columns="symbol", values="close").sort_index()
    rets = pv.pct_change()
    ew_rets = rets.mean(axis=1)
    ew = (1 + ew_rets.fillna(0)).cumprod() * 1000
    records = [
        ("_NF500EW", d.strftime("%Y-%m-%d"), float(v), float(v), float(v), float(v), 0)
        for d, v in ew.items()
    ]
    upsert_ohlcv(conn, records)
    logger.info("Computed _NF500EW (%d rows).", len(records))


_RATE_429 = "rate_limit"
_INVALID = "invalid"


def _fetch_window(client, fyers_sym: str, start: datetime, end: datetime) -> pd.DataFrame:
    """One Fyers /data/history call with 429 backoff.

    Fyers history endpoint enforces ~5 req/sec equity cap and a per-minute
    quota. On 429 we sleep with exponential backoff and retry. On
    'Invalid symbol' we give up immediately (no retry).
    """
    payload = {
        "symbol": fyers_sym,
        "resolution": "D",
        "date_format": "1",
        "range_from": start.strftime("%Y-%m-%d"),
        "range_to": end.strftime("%Y-%m-%d"),
        "cont_flag": "1",
    }
    backoffs = [5, 15, 30]  # seconds — for repeated 429s
    for attempt in range(len(backoffs) + 1):
        try:
            resp = client.history(payload)
        except Exception as e:
            logger.warning("history exception %s: %s", fyers_sym, e)
            time.sleep(2)
            continue
        if not resp:
            return pd.DataFrame()
        s = resp.get("s")
        if s == "ok":
            candles = resp.get("candles") or []
            if not candles:
                return pd.DataFrame()
            df = pd.DataFrame(candles, columns=["ts", "open", "high", "low", "close", "volume"])
            df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(
                "Asia/Kolkata"
            ).dt.strftime("%Y-%m-%d")
            return df[["date", "open", "high", "low", "close", "volume"]]
        if s == "no_data":
            return pd.DataFrame()
        # error path
        code = resp.get("code")
        msg = resp.get("message", "")
        if code == 429 or "request limit" in msg.lower():
            if attempt < len(backoffs):
                wait = backoffs[attempt]
                logger.info("rate-limited on %s, sleeping %ds", fyers_sym, wait)
                time.sleep(wait)
                continue
            logger.warning("giving up on %s after rate-limit retries", fyers_sym)
            return pd.DataFrame()
        if code == -300 or "invalid symbol" in msg.lower():
            logger.warning("invalid symbol %s", fyers_sym)
            return pd.DataFrame()
        logger.warning("history bad resp %s: %s", fyers_sym, resp)
        return pd.DataFrame()
    return pd.DataFrame()


def fetch_one(client, sym: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Fetch the full date range, splitting into 360-day windows if needed
    (Fyers caps each request at ~366 days)."""
    fy_sym = fyers_symbol(sym)
    if fy_sym is None:
        # Delisted — no provider symbol exists. Return empty rather than
        # building a malformed payload. (run_fetch skips these upstream, but
        # fetch_one is also a public entrypoint via the --only smoke test.)
        return pd.DataFrame()
    dfs = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=359), end)
        df = _fetch_window(client, fy_sym, cursor, window_end)
        if not df.empty:
            dfs.append(df)
        cursor = window_end + timedelta(days=1)
        # 2.5 req/sec — Fyers history endpoint per-minute quota is the
        # binding constraint, not per-second. Slower base rate beats
        # bursty + retries.
        time.sleep(0.4)
    if not dfs:
        return pd.DataFrame()
    out = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["date"])
    return out.sort_values("date")


def run_fetch(progress_cb=None, max_symbols: int | None = None) -> dict:
    """Fetch OHLCV for all universe symbols + index. Returns summary dict."""
    _db.init_schemas()

    universe_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, "file", "universe.csv"),
    )
    universe_df = pd.read_csv(universe_path)
    universe_df = universe_df.drop_duplicates(subset=["symbol"]).reset_index(drop=True)
    symbols = universe_df["symbol"].tolist()
    if max_symbols:
        symbols = symbols[:max_symbols]
    targets = symbols + ["_NIFTY50", "_INDIAVIX"]

    # Surface every symbol remap up front, so a wrong mapping is visible
    # immediately on the next fetch (rather than silently logging 'invalid
    # symbol' per-ticker and hiding missing data). Renames are verified
    # against NSE symbolchange.csv but NOT against the live Fyers API —
    # this log line is the verification surface.
    remapped = {s: _symbol_map.resolve(s) for s in symbols if s in _symbol_map.RENAME_MAP}
    delisted_hits = [s for s in symbols if _symbol_map.is_delisted(s)]
    if remapped:
        logger.info("symbol remaps active (%d): %s", len(remapped), remapped)
    if delisted_hits:
        logger.info("skipping delisted (%d): %s", len(delisted_hits), delisted_hits)

    client = fyers_client()
    conn = _db.ohlcv_conn()
    today = datetime.now()
    backfill_days = int(getattr(config.fetch, "backfill_days", 504))

    success = 0
    failures: list[str] = []
    total = len(targets)

    for idx, sym in enumerate(targets):
        # Skip delisted listings (IDFC, ICICISECPRD, etc.) — no provider symbol
        # will ever resolve, so retrying wastes a request and a log line forever.
        if _symbol_map.is_delisted(sym):
            if progress_cb:
                progress_cb(idx + 1, total, sym, "delisted")
            continue
        last = get_last_date(conn, sym)
        if last:
            start_dt = datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)
        else:
            start_dt = today - timedelta(days=int(backfill_days * 1.45))
        if start_dt > today:
            success += 1
            if progress_cb:
                progress_cb(idx + 1, total, sym, "cached")
            continue

        df = fetch_one(client, sym, start_dt, today)
        if df.empty:
            failures.append(sym)
            if progress_cb:
                progress_cb(idx + 1, total, sym, "empty")
            continue

        # Defensive: drop bars with NaN close (incomplete EOD on the source).
        df = df.dropna(subset=["close"])
        records = []
        for _, row in df.iterrows():
            try:
                vol = int(row["volume"]) if pd.notna(row["volume"]) else 0
                records.append((
                    sym, row["date"],
                    float(row["open"]), float(row["high"]), float(row["low"]),
                    float(row["close"]), vol,
                ))
            except Exception:
                continue
        upsert_ohlcv(conn, records)
        success += 1
        if progress_cb:
            progress_cb(idx + 1, total, sym, f"ok ({len(records)})")

    compute_ew_index(conn)

    summary = {
        "total": total,
        "success": success,
        "failed": len(failures),
        "failures": failures[:20],
        "success_pct": round(success / total, 4) if total else 0,
    }
    logger.info("fetch_fyers complete: %s", summary)
    return summary


if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        only = sys.argv[i + 1]
    if only:
        # quick single-symbol smoke test
        client = fyers_client()
        end = datetime.now()
        start = end - timedelta(days=10)
        df = fetch_one(client, only, start, end)
        print(df.tail(10).to_string(index=False))
    else:
        res = run_fetch(progress_cb=lambda i, t, s, st: print(f"[{i}/{t}] {s} {st}"))
        print(res)
