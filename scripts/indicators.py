import os
import sys
import logging
import pandas as pd
import pandas_ta as ta
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('indicators')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/indicators.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
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
    else:
        return config.purple_dot.volume_threshold_default

def compute_indicators_for_symbol(df, mcap):
    # Ensure sorted by date
    df = df.sort_values('date').copy()
    
    if len(df) < 20:
        logger.warning(f"Not enough data for {df['symbol'].iloc[0]} to compute indicators.")
        return pd.DataFrame()
        
    # Moving Averages
    df['sma20'] = ta.sma(df['close'], length=20)
    df['sma21'] = ta.sma(df['close'], length=21)
    df['sma50'] = ta.sma(df['close'], length=50)
    df['sma200'] = ta.sma(df['close'], length=200)
    
    df['ema10'] = ta.ema(df['close'], length=10)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema21'] = ta.ema(df['close'], length=21)
    df['ema50'] = ta.ema(df['close'], length=50)
    
    # Volatility / Volume
    try:
        df['atr14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['atr21'] = ta.atr(df['high'], df['low'], df['close'], length=21)
    except Exception:
        df['atr14'] = None
        df['atr21'] = None
        
    df['adv20'] = ta.sma(df['volume'], length=20)
    df['rsi14'] = ta.rsi(df['close'], length=14)
    
    # Rolling Highs / Lows
    df['high_126'] = df['high'].rolling(window=126).max()
    df['low_126'] = df['low'].rolling(window=126).min()
    
    # Returns
    df['ret_1d'] = df['close'].pct_change(1)
    df['ret_5d'] = df['close'].pct_change(5)
    df['ret_21d'] = df['close'].pct_change(21)
    
    # Purple Dot Logic — bidirectional per spec 4.3, indices forced to 0
    pct_thresh = config.purple_dot.pct_move_threshold
    vol_thresh = get_volume_threshold(mcap)
    sym_first = df['symbol'].iloc[0] if len(df) else ''
    if sym_first.startswith('_'):
        df['purple_dot'] = 0
    else:
        condition = (df['ret_1d'].abs() >= pct_thresh) & (df['volume'] >= vol_thresh)
        df['purple_dot'] = condition.fillna(False).astype(int)
    df['purple_dot_count_30d'] = df['purple_dot'].rolling(window=30, min_periods=1).sum()
    
    # Only keep records where at least SMA20 is valid, dropping initial NaN rows slightly
    # Actually, let's keep all and just let NaNs be null in DB, to match rows 1:1 if needed, 
    # but we can drop rows that don't even have ret_1d
    return df

def upsert_features(conn, df):
    if df.empty: return
    
    records = df[[
        'symbol', 'date', 'sma20', 'sma21', 'sma50', 'sma200',
        'ema10', 'ema20', 'ema21', 'ema50', 'atr14', 'atr21', 'adv20', 'rsi14',
        'high_126', 'low_126', 'ret_1d', 'ret_5d', 'ret_21d',
        'purple_dot', 'purple_dot_count_30d'
    ]].copy()
    
    # Convert NaNs to None for SQLite
    records = records.where(pd.notnull(records), None)
    
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO features (
            symbol, date, sma20, sma21, sma50, sma200, 
            ema10, ema20, ema21, ema50, atr14, atr21, adv20, rsi14,
            high_126, low_126, ret_1d, ret_5d, ret_21d, 
            purple_dot, purple_dot_count_30d
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            sma20=excluded.sma20, sma21=excluded.sma21, sma50=excluded.sma50, sma200=excluded.sma200,
            ema10=excluded.ema10, ema20=excluded.ema20, ema21=excluded.ema21, ema50=excluded.ema50,
            atr14=excluded.atr14, atr21=excluded.atr21, adv20=excluded.adv20, rsi14=excluded.rsi14,
            high_126=excluded.high_126, low_126=excluded.low_126,
            ret_1d=excluded.ret_1d, ret_5d=excluded.ret_5d, ret_21d=excluded.ret_21d,
            purple_dot=excluded.purple_dot, purple_dot_count_30d=excluded.purple_dot_count_30d
    ''', records.values.tolist())
    conn.commit()

def main():
    _db.init_schemas()
    
    universe_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), getattr(config.universe, 'file', 'universe.csv'))
    if not os.path.exists(universe_path):
        logger.error(f"Universe file {universe_path} not found.")
        sys.exit(1)
        
    universe_df = pd.read_csv(universe_path)
    # create a lookup dict for mcap
    mcap_map = dict(zip(universe_df['symbol'], universe_df['market_cap_cr']))
    
    ohlcv_conn = _db.ohlcv_conn()
    feat_conn = _db.features_conn()
    
    cursor = feat_conn.cursor()
    
    symbols = universe_df['symbol'].tolist() + ['_NIFTY50', '_NF500EW']
    
    success_count = 0
    total = len(symbols)
    
    for sym in symbols:
        # find the last calculated date in features
        cursor.execute("SELECT MAX(date) FROM features WHERE symbol=?", (sym,))
        row = cursor.fetchone()
        last_date = row[0] if row and row[0] else None
        
        # Load OHLCV data. To calculate a 200 SMA on a new day, we need the last 200 valid days.
        # We load the entire history to ensure all indicators are perfect.
        # For 504 days, it is very fast. 
        query = f"SELECT * FROM ohlcv WHERE symbol='{sym}' ORDER BY date ASC"
        df = pd.read_sql_query(query, ohlcv_conn)
        
        if df.empty:
            continue
            
        mcap = mcap_map.get(sym, float('nan'))
        
        feat_df = compute_indicators_for_symbol(df, mcap)
        if feat_df.empty:
            continue
            
        # If we have a last_date, only upsert rows strictly newer to save db writes
        if last_date:
            feat_df = feat_df[feat_df['date'] > last_date]
            
        if not feat_df.empty:
            upsert_features(feat_conn, feat_df)
            
        success_count += 1
        
    logger.info(f"Computed indicators for {success_count}/{total} symbols.")

if __name__ == '__main__':
    main()
