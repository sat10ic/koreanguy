import pandas as pd
import numpy as np
from scripts import _config

config = _config.load_config()

GRADE_ORDER = [
    "A+", "A", "A-", "B+", "B", "B-",
    "C+", "C", "C-",
    "D+", "D", "D-", "E+", "E", "F", "G",
]
GRADE_ORDINAL = {g: (len(GRADE_ORDER) - 1 - i) for i, g in enumerate(GRADE_ORDER)}

# Percentile-rank bands — the PRIMARY grade signal. Relative strength is
# inherently relative, so a stock's rank against its peers is what matters.
GRADE_BANDS = [
    (0.95, "A+"), (0.90, "A"), (0.85, "A-"),
    (0.80, "B+"), (0.70, "B"), (0.60, "B-"),
    (0.50, "C+"), (0.40, "C"), (0.30, "C-"),
    (0.25, "D+"), (0.20, "D"), (0.15, "D-"),
    (0.10, "E+"), (0.05, "E"), (0.02, "F"),
]

# Absolute rs_score FLOORS by grade tier. The percentile grade is capped at
# the tier allowed by the absolute rs_score floor.
#
# Why this exists: in a uniformly weak market (median rs_score near 0), the
# top-5% by percentile can still have feeble absolute momentum — grade
# inflation. Measured on this universe, 40% of percentile-A+ stocks over the
# prior 30 days had absolute rs_score < 0.10. The floor suppresses A+/A
# grades in those conditions so "A+" still means "genuinely strong", not
# merely "least weak in a weak market".
#
# Tunable in config (grades.absolute_floors). Defaults below are calibrated
# to the observed NSE rs_score distribution (75th pct ≈ 0.057, 95th ≈ 0.12+).
# NOT the FIX_PLAN A4 values (0.30/0.20/0.12) — those were calibrated to
# unknown data and would have given an A to ~1% of stocks, collapsing the
# scale.
DEFAULT_ABSOLUTE_FLOORS = {
    "A+": 0.12,   # genuinely strong absolute momentum
    "A":  0.08,
    "A-": 0.05,
    "B+": 0.02,
}


def _absolute_floors():
    cfg_floors = getattr(getattr(config, 'grades', None), 'absolute_floors', None)
    if cfg_floors:
        return {g: float(v) for g, v in cfg_floors.items()}
    return DEFAULT_ABSOLUTE_FLOORS


def get_grade_label(rank_pct):
    if rank_pct is None or pd.isna(rank_pct):
        return "G"
    for thresh, label in GRADE_BANDS:
        if rank_pct >= thresh:
            return label
    return "G"


def get_grade_ordinal(grade_str):
    return GRADE_ORDINAL.get(grade_str, 0)


def _apply_absolute_floor(grade, rs_score, floors):
    """Cap a percentile grade at the tier allowed by the absolute rs_score
    floor. Never *raises* a grade via absolute — only suppresses. A stock
    with rs_score 0.15 and percentile A+ keeps A+; a stock with rs_score 0.03
    and percentile A+ is capped at B+ (the highest tier whose floor it clears).
    A stock that clears no floor at all is capped at the highest UNfloored
    tier (B), not G — floors only constrain B+ and above.
    """
    if pd.isna(rs_score):
        return grade
    cur_ord = GRADE_ORDINAL.get(grade, 0)
    # Determine the highest tier whose floor rs clears. Tiers without a floor
    # (B and below) are unconstrained, so the worst-case cap is the highest
    # unfloored tier, not G.
    highest_unfloored_ord = max(
        (GRADE_ORDINAL[g] for g in GRADE_ORDER if g not in floors),
        default=GRADE_ORDINAL['G'],
    )
    allowed_ord = highest_unfloored_ord
    for g in GRADE_ORDER:  # ordered best→worst
        fl = floors.get(g)
        if fl is not None and rs_score >= fl:
            allowed_ord = GRADE_ORDINAL[g]
            break  # first match is the highest allowed floored tier
    # Cap, never raise.
    return grade if cur_ord <= allowed_ord else GRADE_ORDER[len(GRADE_ORDER) - 1 - allowed_ord]


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

    # Hybrid: suppress percentile grades that lack absolute-momentum backing.
    floors = _absolute_floors()
    df['grade'] = df.apply(
        lambda r: _apply_absolute_floor(r['grade'], r['rs_score'], floors), axis=1
    )

    out = df[['symbol', 'date', 'grade', 'rs_score', 'bucket', 'rank_pct']].copy()
    _GRADE_CACHE[target_date] = out
    return out


def clear_cache():
    _GRADE_CACHE.clear()
