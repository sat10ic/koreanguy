import os
import sys
import pandas as pd
import numpy as np
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('screen')
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler('logs/screen.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()


def run_screen(feat_conn, ohlcv_conn):
    cursor = feat_conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 3")
    dates = [row[0] for row in cursor.fetchall()]
    if len(dates) < 3:
        logger.error("Need at least 3 trading days of features. Aborting.")
        return None
    today_str, yest_str, prev_str = dates[0], dates[1], dates[2]

    today_grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, today_str)
    yest_grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, yest_str)

    feat_q = (
        "SELECT * FROM features WHERE date IN (?, ?, ?) "
        "AND symbol NOT IN ('_NIFTY50', '_NF500EW')"
    )
    feat_df = pd.read_sql_query(feat_q, feat_conn, params=(today_str, yest_str, prev_str))
    ohlcv_q = (
        "SELECT * FROM ohlcv WHERE date IN (?, ?, ?) "
        "AND symbol NOT IN ('_NIFTY50', '_NF500EW')"
    )
    ohlcv_df = pd.read_sql_query(ohlcv_q, ohlcv_conn, params=(today_str, yest_str, prev_str))
    full_df = pd.merge(feat_df, ohlcv_df, on=['symbol', 'date'])

    today = full_df[full_df['date'] == today_str].copy()
    yest = full_df[full_df['date'] == yest_str].copy()
    prev = full_df[full_df['date'] == prev_str].copy()

    today = pd.merge(today, today_grades[['symbol', 'grade', 'rs_score', 'bucket', 'rank_pct']], on='symbol', how='left')
    yest_g = yest_grades[['symbol', 'grade']].rename(columns={'grade': 'grade_yesterday'})
    today = pd.merge(today, yest_g, on='symbol', how='left')

    merged = pd.merge(today, yest, on='symbol', suffixes=('', '_y'))
    merged = pd.merge(
        merged,
        prev[['symbol', 'close', 'sma20']].rename(columns={'close': 'close_p', 'sma20': 'sma20_p'}),
        on='symbol', how='left'
    )

    setup_cfg = config.setup
    uptrend_min_gain = setup_cfg.get('uptrend_min_gain', 0.25) if isinstance(setup_cfg, dict) else 0.25
    correction_min = setup_cfg.get('correction_min', 0.03) if isinstance(setup_cfg, dict) else 0.03
    correction_max = setup_cfg.get('correction_max', 0.30) if isinstance(setup_cfg, dict) else 0.30

    # Bread-and-butter setup
    merged['uptrend_pass'] = (
        (merged['close'] > merged['sma200']) &
        (merged['high_126'] >= (1.0 + uptrend_min_gain) * merged['low_126'])
    )
    merged['correction_pass'] = (
        (merged['close'] <= (1 - correction_min) * merged['high_126']) &
        (merged['close'] >= (1 - correction_max) * merged['high_126'])
    )

    # 2-day SMA20 reclaim tolerance per decisions.md #3
    reclaim_today = (merged['close'] > merged['sma20']) & (merged['close_y'] <= merged['sma20_y'])
    reclaim_yest = (
        (merged['close_y'] > merged['sma20_y']) &
        (merged['close_p'] <= merged['sma20_p']) &
        (merged['close'] > merged['sma20'])
    )
    merged['reclaim_pass'] = (reclaim_today | reclaim_yest).fillna(False)

    merged['setup_pass'] = (
        merged['uptrend_pass'].fillna(False) &
        merged['correction_pass'].fillna(False) &
        merged['reclaim_pass']
    ).astype(int)

    merged['extended_yellow'] = (merged['close'] > merged['sma50'] + 5 * merged['atr14']).astype(int)
    merged['extended_red'] = (merged['close'] > merged['sma50'] + 7 * merged['atr14']).astype(int)

    watchlist_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        getattr(config.universe, 'watchlist_file', 'watchlist.csv'),
    )
    if os.path.exists(watchlist_path):
        wl = pd.read_csv(watchlist_path)
        wl_set = set(wl['symbol'].tolist())
        merged['watchlist_member'] = merged['symbol'].apply(lambda x: 1 if x in wl_set else 0)
    else:
        merged['watchlist_member'] = 0

    merged['grade_sort'] = merged['grade'].map(_grade_helper.GRADE_ORDINAL).fillna(-1)
    merged = merged.sort_values(['grade_sort', 'rs_score'], ascending=[False, False])

    output_cols = [
        'symbol', 'date', 'grade', 'grade_yesterday', 'rs_score', 'rank_pct', 'bucket',
        'setup_pass', 'uptrend_pass', 'correction_pass', 'reclaim_pass',
        'extended_yellow', 'extended_red', 'watchlist_member',
        'close', 'sma20', 'sma50', 'sma200',
        'ema10', 'ema20', 'ema50',
        'atr14', 'adv20', 'volume',
        'purple_dot', 'purple_dot_count_30d',
        'ret_1d', 'ret_5d', 'ret_21d',
    ]
    existing = [c for c in output_cols if c in merged.columns]
    final = merged[existing].copy()

    os.makedirs('output', exist_ok=True)
    out_path = 'output/screen_today.csv'
    final.to_csv(out_path, index=False)

    setups = int(merged['setup_pass'].sum())
    logger.info(
        f"Screen complete: {len(merged)} stocks; setup_pass={setups}; "
        f"uptrend={int(merged['uptrend_pass'].sum())} correction={int(merged['correction_pass'].sum())} "
        f"reclaim={int(merged['reclaim_pass'].sum())}. -> {out_path}"
    )
    return final


def main():
    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()
    run_screen(feat_conn, ohlcv_conn)


if __name__ == '__main__':
    main()
