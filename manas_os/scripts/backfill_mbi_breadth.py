#!/usr/bin/env python3
"""
Backfill an MBI-style NSE breadth dataset from manas_os' own price history.

Reproduces the daily-breadth metrics tracked on a trader's "MBI" sheet
(stocksgeeks) directly from the `daily_prices` table, for the full window
our history covers (2021-07-12 -> present).

CALIBRATION VERDICT (see manas_os/data/MBI_BACKFILL_REPORT.md for the full table):
  * Universe: ALL EQ-series symbols (the "all_EQ" candidate). It is the
    fully-reproducible, no-tuning baseline and the best/near-best match on the
    most metrics. The sheet's true universe is unknown; a bottom-quartile
    liquidity floor matches the 4.5% metric marginally better but worsens the
    MA-level match, so we do NOT tune. The sheet is APPROXIMABLE (corr 0.86-0.96
    across metrics), not exactly reproducible (residual level offsets of
    2-13 pts because the exact universe + EOD-adjusted price source differ).
  * Moving averages: SMA, not EMA. SMA beats EMA vs the sheet on every window
    (10/20/50/200), decisively at 200-day (corr 0.93 vs 0.80). We store both
    SMA and EMA columns; SMA is the calibrated primary. This confirms the
    sheet header ("sma") over the conflicting "ema" claim.

METRIC DEFINITIONS (per trading day, % of that metric's valid universe):
  pct_up_4_5    = 100 * (# symbols with day-return >= +4.5%) / N_ret
  pct_down_4_5  = 100 * (# symbols with day-return <= -4.5%) / N_ret
  ratio_4_5     = 100 * pct_up_4_5 / pct_down_4_5   (the sheet's "4.5 r")
  pct_above_smaW/emaW = 100 * (# with close > MA_W) / N_maW
  pct_52w_high  = 100 * (# whose close == rolling 52-wk max) / N_52
  pct_52w_low   = 100 * (# whose close == rolling 52-wk min) / N_52
  day-return uses close vs prev_close (from daily_prices).

MIN-HISTORY / DENOMINATOR HANDLING (stated choice):
  Each metric uses its OWN denominator = symbols that have enough history for
  that metric on that day. A symbol with < W prior closes is EXCLUDED from the
  MA_W denominator (min_periods=W). 52-wk high/low uses a 250-session window
  with min_periods=100 (a symbol needs >=100 sessions before it can register).
  The 4.5% metrics require a valid prev_close only. This means early-listed
  symbols simply don't count toward long-window metrics until they qualify --
  denominators grow over time, which matches how such sheets are kept.

Rerunnable: drops+recreates `mbi_breadth_daily` (source='manas_backfill') and
rewrites manas_os/data/mbi_breadth_backfill.csv. Leaves the existing
`breadth_daily` table (4% bands, niftymidsml400) untouched.
"""
import os, sqlite3, datetime
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.normpath(os.path.join(HERE, '..', 'data', 'manas.db'))
CSV  = os.path.normpath(os.path.join(HERE, '..', 'data', 'mbi_breadth_backfill.csv'))

UP_T, DN_T = 0.045, -0.045
MA_WINDOWS = [10, 20, 50, 200]
HL_WINDOW, HL_MINP = 250, 100   # ~52 weeks of sessions


def load_prices(db):
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT symbol, trade_date, close, prev_close, volume "
        "FROM daily_prices WHERE series='EQ' AND close IS NOT NULL", con)
    con.close()
    df['date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    df['ret'] = np.where(
        (df['prev_close'].notna()) & (df['prev_close'] > 0),
        (df['close'] - df['prev_close']) / df['prev_close'], np.nan)
    return df


def add_rolling(df):
    g = df.groupby('symbol', sort=False)['close']
    for w in MA_WINDOWS:
        df[f'sma{w}'] = g.transform(lambda s, w=w: s.rolling(w, min_periods=w).mean())
        df[f'ema{w}'] = g.transform(lambda s, w=w: s.ewm(span=w, min_periods=w, adjust=False).mean())
    df['hi52'] = g.transform(lambda s: s.rolling(HL_WINDOW, min_periods=HL_MINP).max())
    df['lo52'] = g.transform(lambda s: s.rolling(HL_WINDOW, min_periods=HL_MINP).min())
    return df


def compute_daily(df):
    rows = []
    for d, gr in df.groupby('date', sort=True):
        rec = {'trade_date': d.strftime('%Y-%m-%d')}
        r = gr[gr['ret'].notna()]
        n = len(r)
        rec['universe_count'] = int(n)
        up = int((r['ret'] >= UP_T).sum()); dn = int((r['ret'] <= DN_T).sum())
        rec['up_count'] = up; rec['down_count'] = dn
        rec['pct_up_4_5']   = round(100 * up / n, 4) if n else None
        rec['pct_down_4_5'] = round(100 * dn / n, 4) if n else None
        pu = rec['pct_up_4_5']; pdn = rec['pct_down_4_5']
        rec['ratio_4_5'] = round(100 * pu / pdn, 2) if (pdn and pdn > 0) else None
        for w in MA_WINDOWS:
            for kind in ('sma', 'ema'):
                col = f'{kind}{w}'; v = gr[gr[col].notna()]
                m = len(v)
                rec[f'pct_above_{col}'] = round(100 * int((v['close'] > v[col]).sum()) / m, 4) if m else None
            rec[f'ma{w}_count'] = int(gr[f'sma{w}'].notna().sum())
        h = gr[gr['hi52'].notna()]; nh = len(h)
        rec['hl_count'] = int(nh)
        rec['pct_52w_high'] = round(100 * int((h['close'] >= h['hi52'] - 1e-9).sum()) / nh, 4) if nh else None
        rec['pct_52w_low']  = round(100 * int((h['close'] <= h['lo52'] + 1e-9).sum()) / nh, 4) if nh else None
        rows.append(rec)
    return pd.DataFrame(rows)


DDL = """
CREATE TABLE IF NOT EXISTS mbi_breadth_daily (
    trade_date TEXT PRIMARY KEY,
    universe_count INTEGER,
    up_count INTEGER, down_count INTEGER,
    pct_up_4_5 REAL, pct_down_4_5 REAL, ratio_4_5 REAL,
    pct_above_sma10 REAL, pct_above_sma20 REAL, pct_above_sma50 REAL, pct_above_sma200 REAL,
    pct_above_ema10 REAL, pct_above_ema20 REAL, pct_above_ema50 REAL, pct_above_ema200 REAL,
    ma10_count INTEGER, ma20_count INTEGER, ma50_count INTEGER, ma200_count INTEGER,
    pct_52w_high REAL, pct_52w_low REAL, hl_count INTEGER,
    source TEXT DEFAULT 'manas_backfill',
    ingested_at TEXT
);
"""


def write_db(db, out):
    con = sqlite3.connect(db); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS mbi_breadth_daily")
    cur.executescript(DDL)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    cols = [c for c in out.columns]
    out = out.copy(); out['source'] = 'manas_backfill'; out['ingested_at'] = now
    allcols = cols + ['source', 'ingested_at']
    placeholders = ','.join('?' * len(allcols))
    cur.executemany(
        f"INSERT INTO mbi_breadth_daily ({','.join(allcols)}) VALUES ({placeholders})",
        [tuple(None if (isinstance(v, float) and np.isnan(v)) else v for v in row)
         for row in out[allcols].itertuples(index=False, name=None)])
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM mbi_breadth_daily").fetchone()[0]
    con.close()
    return n


def main():
    print(f"DB : {DB}")
    df = load_prices(DB)
    print(f"loaded {len(df):,} EQ rows, {df['date'].nunique()} trading days "
          f"({df['date'].min().date()} -> {df['date'].max().date()})")
    df = add_rolling(df)
    out = compute_daily(df)
    out.to_csv(CSV, index=False)
    n = write_db(DB, out)
    print(f"wrote {len(out)} rows to CSV: {CSV}")
    print(f"wrote {n} rows to table mbi_breadth_daily (source='manas_backfill')")
    print(out[['trade_date', 'universe_count', 'pct_up_4_5', 'pct_down_4_5',
               'ratio_4_5', 'pct_above_sma50', 'pct_above_sma200',
               'pct_52w_high', 'pct_52w_low']].tail(3).to_string(index=False))


if __name__ == '__main__':
    main()
