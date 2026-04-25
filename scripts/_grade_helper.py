import pandas as pd
import numpy as np
from scripts import _config

config = _config.load_config()

GRADE_ORDER = [
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-",
    "D+", "D", "D-", "E+", "E", "F", "G",
]
GRADE_ORDINAL = {g: (len(GRADE_ORDER) - 1 - i) for i, g in enumerate(GRADE_ORDER)}

GRADE_BANDS = [
    (0.95, "A+"), (0.90, "A"), (0.85, "A-"),
    (0.80, "B+"), (0.70, "B"), (0.60, "B-"),
    (0.50, "C+"), (0.40, "C"), (0.30, "C-"),
    (0.25, "D+"), (0.20, "D"), (0.15, "D-"),
    (0.10, "E+"), (0.05, "E"), (0.02, "F"),
]

def get_grade_label(rank_pct):
    if rank_pct is None or pd.isna(rank_pct):
        return "G"
    for thresh, label in GRADE_BANDS:
        if rank_pct >= thresh:
            return label
    return "G"

def get_grade_ordinal(grade_str):
    return GRADE_ORDINAL.get(grade_str, 0)

_GRADE_CACHE = {}

def calculate_grades_for_date(feat_conn, ohlcv_conn, target_date):
    if target_date in _GRADE_CACHE:
        return _GRADE_CACHE[target_date]

    query = "SELECT * FROM features WHERE date = ? AND symbol NOT IN ('_NIFTY50', '_NF500EW')"
    feat_df = pd.read_sql_query(query, feat_conn, params=(target_date,))

    ohlcv_query = "SELECT symbol, close FROM ohlcv WHERE date = ? AND symbol NOT IN ('_NIFTY50', '_NF500EW')"
    ohlcv_df = pd.read_sql_query(ohlcv_query, ohlcv_conn, params=(target_date,))

    if feat_df.empty or ohlcv_df.empty:
        empty = pd.DataFrame(columns=['symbol', 'date', 'grade', 'rs_score', 'bucket', 'rank_pct'])
        _GRADE_CACHE[target_date] = empty
        return empty

    df = pd.merge(feat_df, ohlcv_df, on='symbol')

    weights = config.rs.weights
    df['rs_score'] = (
        weights.get('d1', 0.2) * df['ret_1d'].fillna(0) +
        weights.get('d5', 0.3) * df['ret_5d'].fillna(0) +
        weights.get('d21', 0.5) * df['ret_21d'].fillna(0)
    )

    df['bucket'] = np.where(df['close'] > df['sma50'], 'Bullish', 'Bearish')
    df['rank_pct'] = df.groupby('bucket')['rs_score'].rank(pct=True, method='first')
    df['grade'] = df['rank_pct'].apply(get_grade_label)

    out = df[['symbol', 'date', 'grade', 'rs_score', 'bucket', 'rank_pct']].copy()
    _GRADE_CACHE[target_date] = out
    return out

def clear_cache():
    _GRADE_CACHE.clear()
