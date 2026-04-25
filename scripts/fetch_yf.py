"""yfinance-based OHLCV fetcher for SwingEdge Lite.

Drop-in replacement for fetch.py when Fyers is unavailable. Pulls daily bars
for every symbol in universe.csv plus _NIFTY50, then computes _NF500EW from
the universe.
"""
import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config

import yfinance as yf


def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('fetch_yf')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/fetch_yf.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


logger = setup_logger()
config = _config.load_config()


def yf_ticker(sym: str) -> str:
    if sym == '_NIFTY50':
        return '^NSEI'
    return f'{sym}.NS'


def upsert_ohlcv(conn, records):
    if not records:
        return
    cur = conn.cursor()
    cur.executemany(
        '''INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(symbol, date) DO UPDATE SET
             open=excluded.open, high=excluded.high, low=excluded.low,
             close=excluded.close, volume=excluded.volume''',
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
    df['date'] = pd.to_datetime(df['date'])
    pv = df.pivot(index='date', columns='symbol', values='close').sort_index()
    rets = pv.pct_change()
    ew_rets = rets.mean(axis=1)
    ew = (1 + ew_rets.fillna(0)).cumprod() * 1000
    records = [
        ('_NF500EW', d.strftime('%Y-%m-%d'), float(v), float(v), float(v), float(v), 0)
        for d, v in ew.items()
    ]
    upsert_ohlcv(conn, records)
    logger.info("Computed _NF500EW (%d rows).", len(records))


def fetch_one(sym: str, start: datetime, end: datetime, retries: int = 2) -> pd.DataFrame:
    tkr = yf_ticker(sym)
    backoff = 1
    for _ in range(retries + 1):
        try:
            df = yf.download(
                tkr,
                start=start.strftime('%Y-%m-%d'),
                end=(end + timedelta(days=1)).strftime('%Y-%m-%d'),
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            # Flatten multi-index columns if needed
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:
            logger.warning("yfinance error %s: %s", sym, e)
            time.sleep(backoff)
            backoff *= 2
    return pd.DataFrame()


def run_fetch(progress_cb=None, max_symbols: int | None = None) -> dict:
    """Fetch OHLCV for all universe symbols + index. Returns summary dict."""
    _db.init_schemas()

    universe_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, 'file', 'universe.csv'),
    )
    universe_df = pd.read_csv(universe_path)
    # Drop accidental duplicates
    universe_df = universe_df.drop_duplicates(subset=['symbol']).reset_index(drop=True)
    symbols = universe_df['symbol'].tolist()
    if max_symbols:
        symbols = symbols[:max_symbols]
    targets = symbols + ['_NIFTY50']

    conn = _db.ohlcv_conn()
    today = datetime.now()
    backfill_days = int(getattr(config.fetch, 'backfill_days', 504))
    delay = float(getattr(config.fetch, 'batch_delay_ms', 200)) / 1000.0

    success = 0
    failures = []
    total = len(targets)

    for idx, sym in enumerate(targets):
        last = get_last_date(conn, sym)
        if last:
            start_dt = datetime.strptime(last, '%Y-%m-%d') + timedelta(days=1)
        else:
            start_dt = today - timedelta(days=int(backfill_days * 1.45))
        if start_dt > today:
            success += 1
            if progress_cb:
                progress_cb(idx + 1, total, sym, 'cached')
            continue

        df = fetch_one(sym, start_dt, today)
        if df.empty:
            failures.append(sym)
            if progress_cb:
                progress_cb(idx + 1, total, sym, 'empty')
            time.sleep(delay)
            continue

        records = []
        for ts, row in df.iterrows():
            dt = ts.strftime('%Y-%m-%d')
            try:
                vol_val = row['Volume']
                vol = int(vol_val) if pd.notna(vol_val) else 0
                rec = (
                    sym, dt,
                    float(row['Open']), float(row['High']), float(row['Low']),
                    float(row['Close']), vol,
                )
                records.append(rec)
            except Exception:
                continue
        upsert_ohlcv(conn, records)
        success += 1
        if progress_cb:
            progress_cb(idx + 1, total, sym, f'ok ({len(records)})')
        time.sleep(delay)

    compute_ew_index(conn)

    summary = {
        'total': total,
        'success': success,
        'failed': len(failures),
        'failures': failures[:20],
        'success_pct': round(success / total, 4) if total else 0,
    }
    logger.info("fetch_yf complete: %s", summary)
    return summary


if __name__ == '__main__':
    res = run_fetch(progress_cb=lambda i, t, s, st: print(f'[{i}/{t}] {s} {st}'))
    print(res)
