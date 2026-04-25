"""Per-symbol features. Lightweight indicators (no pandas_ta dependency)."""
import os
import sys
import logging
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _indicators_lite as ta


def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('indicators')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/indicators.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


logger = setup_logger()
config = _config.load_config()


def get_volume_threshold(mcap):
    if pd.isna(mcap):
        return config.purple_dot.volume_threshold_default
    if mcap < 2000:
        return config.purple_dot.volume_threshold_smallcap
    elif mcap < 10000:
        return config.purple_dot.volume_threshold_midcap
    return config.purple_dot.volume_threshold_default


def compute_indicators_for_symbol(df, mcap):
    df = df.sort_values('date').copy()
    if len(df) < 20:
        return pd.DataFrame()

    df['sma20'] = ta.sma(df['close'], 20)
    df['sma21'] = ta.sma(df['close'], 21)
    df['sma50'] = ta.sma(df['close'], 50)
    df['sma200'] = ta.sma(df['close'], 200)
    df['ema10'] = ta.ema(df['close'], 10)
    df['ema20'] = ta.ema(df['close'], 20)
    df['ema21'] = ta.ema(df['close'], 21)
    df['ema50'] = ta.ema(df['close'], 50)

    try:
        df['atr14'] = ta.atr(df['high'], df['low'], df['close'], 14)
        df['atr21'] = ta.atr(df['high'], df['low'], df['close'], 21)
    except Exception:
        df['atr14'] = None
        df['atr21'] = None

    df['adv20'] = ta.sma(df['volume'], 20)
    df['rsi14'] = ta.rsi(df['close'], 14)

    df['high_126'] = df['high'].rolling(126, min_periods=20).max()
    df['low_126'] = df['low'].rolling(126, min_periods=20).min()

    df['ret_1d'] = df['close'].pct_change(1)
    df['ret_5d'] = df['close'].pct_change(5)
    df['ret_21d'] = df['close'].pct_change(21)

    pct_th = config.purple_dot.pct_move_threshold
    vol_th = get_volume_threshold(mcap)
    sym_first = df['symbol'].iloc[0] if len(df) else ''
    if sym_first.startswith('_'):
        df['purple_dot'] = 0
    else:
        cond = (df['ret_1d'].abs() >= pct_th) & (df['volume'] >= vol_th)
        df['purple_dot'] = cond.fillna(False).astype(int)
    df['purple_dot_count_30d'] = df['purple_dot'].rolling(30, min_periods=1).sum()
    return df


def upsert_features(conn, df):
    if df.empty:
        return
    cols = [
        'symbol', 'date', 'sma20', 'sma21', 'sma50', 'sma200',
        'ema10', 'ema20', 'ema21', 'ema50', 'atr14', 'atr21', 'adv20', 'rsi14',
        'high_126', 'low_126', 'ret_1d', 'ret_5d', 'ret_21d',
        'purple_dot', 'purple_dot_count_30d',
    ]
    out = df[cols].copy()
    out = out.where(pd.notnull(out), None)
    cur = conn.cursor()
    cur.executemany(
        '''INSERT INTO features (
            symbol, date, sma20, sma21, sma50, sma200,
            ema10, ema20, ema21, ema50, atr14, atr21, adv20, rsi14,
            high_126, low_126, ret_1d, ret_5d, ret_21d,
            purple_dot, purple_dot_count_30d
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            sma20=excluded.sma20, sma21=excluded.sma21, sma50=excluded.sma50, sma200=excluded.sma200,
            ema10=excluded.ema10, ema20=excluded.ema20, ema21=excluded.ema21, ema50=excluded.ema50,
            atr14=excluded.atr14, atr21=excluded.atr21, adv20=excluded.adv20, rsi14=excluded.rsi14,
            high_126=excluded.high_126, low_126=excluded.low_126,
            ret_1d=excluded.ret_1d, ret_5d=excluded.ret_5d, ret_21d=excluded.ret_21d,
            purple_dot=excluded.purple_dot, purple_dot_count_30d=excluded.purple_dot_count_30d''',
        out.values.tolist(),
    )
    conn.commit()


def run_indicators(progress_cb=None) -> dict:
    _db.init_schemas()
    universe_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, 'file', 'universe.csv'),
    )
    universe_df = pd.read_csv(universe_path).drop_duplicates(subset=['symbol'])
    mcap_map = dict(zip(universe_df['symbol'], universe_df['market_cap_cr']))

    ohlcv_conn = _db.ohlcv_conn()
    feat_conn = _db.features_conn()
    cur = feat_conn.cursor()
    symbols = universe_df['symbol'].tolist() + ['_NIFTY50', '_NF500EW']
    success = 0
    total = len(symbols)
    for idx, sym in enumerate(symbols):
        cur.execute("SELECT MAX(date) FROM features WHERE symbol=?", (sym,))
        row = cur.fetchone()
        last = row[0] if row and row[0] else None
        df = pd.read_sql_query(
            "SELECT * FROM ohlcv WHERE symbol=? ORDER BY date ASC", ohlcv_conn, params=(sym,)
        )
        if df.empty:
            if progress_cb:
                progress_cb(idx + 1, total, sym, 'no-data')
            continue
        mcap = mcap_map.get(sym, float('nan'))
        feat_df = compute_indicators_for_symbol(df, mcap)
        if feat_df.empty:
            continue
        if last:
            feat_df = feat_df[feat_df['date'] > last]
        if not feat_df.empty:
            upsert_features(feat_conn, feat_df)
        success += 1
        if progress_cb:
            progress_cb(idx + 1, total, sym, 'ok')
    logger.info("indicators: %d/%d", success, total)
    return {'total': total, 'success': success}


def main():
    res = run_indicators(progress_cb=lambda i, t, s, st: print(f'[{i}/{t}] {s} {st}'))
    print(res)


if __name__ == '__main__':
    main()
