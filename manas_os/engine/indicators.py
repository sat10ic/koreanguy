"""Per-symbol daily features (lightweight indicators, no pandas_ta dependency).

Adopted from legacy scripts/indicators.py. The pure feature computation
`compute_indicators_for_symbol(df, mcap)` is kept intact. The legacy DB layer
(`upsert_features`, `run_indicators` reading legacy ohlcv/features DBs) is
DROPPED and replaced by `run(conn, run_date)` which reads `daily_prices` and
writes one JSON feature bag per (symbol, run_date) into `features_daily`.

`compute_indicators_for_symbol` expects a DataFrame with columns:
    symbol, date, open, high, low, close, volume
(oldest-first-friendly; it sorts by `date` internally).
"""
from __future__ import annotations

import json
import logging
import time

import numpy as np
import pandas as pd

from manas_os.engine import indicators_lite as ta

logger = logging.getLogger("manas_os.engine.indicators")

# Purple-dot thresholds — adopted from legacy config.yaml (purple_dot:).
PCT_MOVE_THRESHOLD = 0.05
VOLUME_THRESHOLD_DEFAULT = 1_000_000
VOLUME_THRESHOLD_MIDCAP = 500_000    # market cap < 10000 Cr
VOLUME_THRESHOLD_SMALLCAP = 300_000  # market cap < 2000 Cr


def _lin_slope(arr):
    """Linear-fit slope of the last N values. Used for RHS lows trend."""
    n = len(arr)
    if n < 2:
        return 0.0
    x = np.arange(n)
    # slope of best-fit line — np.polyfit gives [slope, intercept]
    try:
        return float(np.polyfit(x, arr, 1)[0])
    except Exception:
        return 0.0


def _bars_since_high(df):
    """Per-row count of bars since the rolling 126-day high was set."""
    high = df['high'].values
    h126 = df['high_126'].values
    out = np.full(len(df), np.nan)
    last_at_high = -1
    for i in range(len(df)):
        if not pd.isna(h126[i]) and high[i] >= h126[i] - 1e-9:
            last_at_high = i
        if last_at_high >= 0:
            out[i] = i - last_at_high
    return pd.Series(out, index=df.index)


def get_volume_threshold(mcap):
    if pd.isna(mcap):
        return VOLUME_THRESHOLD_DEFAULT
    if mcap < 2000:
        return VOLUME_THRESHOLD_SMALLCAP
    elif mcap < 10000:
        return VOLUME_THRESHOLD_MIDCAP
    return VOLUME_THRESHOLD_DEFAULT


def compute_indicators_for_symbol(df, mcap):
    df = df.sort_values('date').copy()
    if len(df) < 20:
        return pd.DataFrame()

    df['sma10'] = ta.sma(df['close'], 10)
    df['sma20'] = ta.sma(df['close'], 20)
    df['sma21'] = ta.sma(df['close'], 21)
    df['sma40'] = ta.sma(df['close'], 40)
    df['sma50'] = ta.sma(df['close'], 50)
    df['sma200'] = ta.sma(df['close'], 200)
    df['ema5'] = ta.ema(df['close'], 5)
    df['ema10'] = ta.ema(df['close'], 10)
    df['ema20'] = ta.ema(df['close'], 20)
    df['ema21'] = ta.ema(df['close'], 21)
    df['ema50'] = ta.ema(df['close'], 50)
    # 10-bar slope of sma40 — % change over the last 10 sessions. Drives the
    # Weinstein stage classifier (rising = S2, flat = S1, falling = S4).
    sma40_lag = df['sma40'].shift(10)
    df['sma40_slope_pct'] = (df['sma40'] - sma40_lag) / sma40_lag

    try:
        df['atr14'] = ta.atr(df['high'], df['low'], df['close'], 14)
        df['atr21'] = ta.atr(df['high'], df['low'], df['close'], 21)
    except Exception:
        df['atr14'] = None
        df['atr21'] = None

    df['adv20'] = ta.sma(df['volume'], 20)
    df['rsi14'] = ta.rsi(df['close'], 14)

    # ADR — Average Daily Range as % of close. 14-day and 20-day windows.
    # Captures how much *room* a stock typically gives intraday.
    daily_range_pct = (df['high'] - df['low']) / df['close']
    df['adr14_pct'] = daily_range_pct.rolling(14, min_periods=5).mean() * 100.0
    df['adr20_pct'] = daily_range_pct.rolling(20, min_periods=5).mean() * 100.0

    # Volume ratio — today's volume vs 20-day average. >2 = heavy.
    df['vol_ratio_20'] = df['volume'] / df['adv20']

    df['high_126'] = df['high'].rolling(126, min_periods=20).max()
    df['low_126'] = df['low'].rolling(126, min_periods=20).min()

    # 52-week (252 trading day) high / low — KID overlay
    df['high_252'] = df['high'].rolling(252, min_periods=50).max()
    df['low_252'] = df['low'].rolling(252, min_periods=50).min()

    # Minervini Trend Template pass (7 conditions, boolean):
    #  1. close > sma150 & sma200
    #  2. sma150 > sma200
    #  3. sma200 trending up (sma200 today > sma200 4 weeks ago)
    #  4. sma50 > sma150 > sma200
    #  5. close > sma50
    #  6. close >= 1.25 × low_252 (at least 25% above 52-week low)
    #  7. close >= 0.75 × high_252 (within 25% of 52-week high)
    sma200_4w_ago = df['sma200'].shift(21)
    mt = (
        (df['close'] > df['sma200'].fillna(0)) &
        (df['close'] > df['sma50'].fillna(0)) &
        (df['sma50'] > df['sma200'].fillna(0)) &
        (df['sma200'] > sma200_4w_ago.fillna(0)) &
        (df['close'] >= df['low_252'].fillna(0) * 1.25) &
        (df['close'] >= df['high_252'].fillna(df['close']) * 0.75)
    )
    df['minervini_pass'] = mt.fillna(False).astype(int)

    # ---- Method-shared columns (Based + Afzal) ---------------------------
    # TRP% — Afzal's True Range Percentage. ATR/close × 100. ≥3 is the
    # liquidity floor; also used as the SL distance for Afzal entries.
    df['trp_pct'] = (df['atr14'] / df['close']) * 100.0

    # Swing pivots — 20-bar high/low excluding today, anchors Based pivot
    # entry and SL.
    df['swing_high_20'] = df['high'].shift(1).rolling(20, min_periods=5).max()
    df['swing_low_20'] = df['low'].shift(1).rolling(20, min_periods=5).min()

    # Previous Day's High — Afzal's PDH-break entry trigger.
    df['pdh'] = df['high'].shift(1)

    # Inside-bar flag — today's high < yest high AND today's low > yest low.
    # Inside bars + RHS = Manas's "exhaustion of supply" cue.
    df['inside_bar'] = (
        (df['high'] < df['high'].shift(1)) & (df['low'] > df['low'].shift(1))
    ).astype(int)

    # Range contraction — current 5-bar range / prior 30-bar avg range. <0.5
    # marks Afzal PPC (Pre-Price Contraction) tightening.
    range_5 = (df['high'].rolling(5).max() - df['low'].rolling(5).min())
    range_30_prev = (df['high'].shift(5).rolling(30).max() - df['low'].shift(5).rolling(30).min())
    df['range_contraction'] = range_5 / range_30_prev

    # Bars since 126d high — base age, used by universe gate.
    df['bars_since_126d_high'] = _bars_since_high(df)

    # ---- RHS detector ----------------------------------------------------
    # Right-Hand Side: price has been making lower highs / flat-to-rising
    # lows for ≥5 bars after a base high. Captures the cup-handle handle.
    rhs_lookback = 10
    high_in_window = df['high'].rolling(rhs_lookback).max()
    low_in_window = df['low'].rolling(rhs_lookback).min()
    df['rhs_range_ratio'] = (high_in_window - low_in_window) / df['close']
    # Slope of last-5 lows (positive => rising lows under a flat ceiling).
    df['rhs_low_slope'] = (
        df['low'].rolling(5).apply(_lin_slope, raw=True) / df['close']
    )
    # rhs_today: tight range AND rising/flat lows AND price within 5% of
    # the 10-bar high (the right-hand handle).
    df['rhs_today'] = (
        (df['rhs_range_ratio'] < 0.10)
        & (df['rhs_low_slope'] >= 0)
        & (df['close'] >= 0.95 * high_in_window)
    ).fillna(False).astype(int)

    # ---- Weinstein stage classifier --------------------------------------
    # S1A — basing early   : close < sma40, sma40_slope flat-or-down
    # S1B — basing late    : close ≥ sma40, sma40_slope flat
    # S2  — advancing      : close > sma40 > sma_long, sma40_slope rising
    # S3  — topping        : close near sma40, sma40_slope rolling over
    # S4  — declining      : close < sma40, sma40_slope falling
    #
    # IPO-aware long-MA: use SMA200 when available, else fall back to
    # SMA50. Without this, every stock with <200 sessions of history
    # (post-2024 IPOs like GROWW) is locked out of S2 forever.
    #
    # Volatility-aware rising/falling: a stock must outpace its OWN average
    # daily range to count as trending. The old hardcoded 0.005 (0.5%/10d)
    # was within the noise floor of Indian equities (ADR 3-8%), which
    # mislabelled consolidating/basing stocks as advancing (S2) or topping
    # (S3). Using adr14_pct/100 means a stock with 4% ADR must rise >4% over
    # 10 sessions to be S2 — a real trend, not noise.
    slope = df['sma40_slope_pct'].fillna(0)
    vol_threshold = (df['adr14_pct'].fillna(0) / 100.0)
    above40 = df['close'] > df['sma40']
    sma_long = df['sma200'].fillna(df['sma50'])
    above_long = df['sma40'] > sma_long
    rising = slope > vol_threshold
    falling = slope < -vol_threshold

    stage = pd.Series('S1A', index=df.index, dtype=object)
    stage[above40 & rising & above_long] = 'S2'
    stage[above40 & ~rising & ~falling] = 'S1B'
    stage[~above40 & falling] = 'S4'
    stage[~above40 & ~falling & ~rising] = 'S1A'
    stage[above40 & falling] = 'S3'
    df['stage'] = stage

    df['ret_1d'] = df['close'].pct_change(1)
    df['ret_5d'] = df['close'].pct_change(5)
    df['ret_21d'] = df['close'].pct_change(21)

    pct_th = PCT_MOVE_THRESHOLD
    vol_th = get_volume_threshold(mcap)
    sym_first = df['symbol'].iloc[0] if len(df) else ''
    if sym_first.startswith('_'):
        df['purple_dot'] = 0
    else:
        cond = (df['ret_1d'].abs() >= pct_th) & (df['volume'] >= vol_th)
        df['purple_dot'] = cond.fillna(False).astype(int)
    df['purple_dot_count_30d'] = df['purple_dot'].rolling(30, min_periods=1).sum()

    # Buying-Force score — Manas Arora's "explosive buying" idea encoded as
    # a continuous metric: positive % move × volume-vs-20DMA ratio. Only
    # green-up days count (sells nullify). 30-day rolling MAX captures the
    # strongest demand event in the recent window.
    pos_ret = df['ret_1d'].clip(lower=0).fillna(0)
    df['buying_force_score'] = (pos_ret * df['vol_ratio_20'].fillna(0)) * 100.0  # in %·× units
    df['bf_score_30d_max'] = df['buying_force_score'].rolling(30, min_periods=1).max()
    return df


# Feature columns promoted from the computed frame into the JSON bag.
_FEATURE_COLS = [
    'sma10', 'sma20', 'sma21', 'sma40', 'sma50', 'sma200',
    'ema5', 'ema10', 'ema20', 'ema21', 'ema50',
    'atr14', 'atr21', 'adv20', 'rsi14',
    'high_126', 'low_126', 'high_252', 'low_252',
    'ret_1d', 'ret_5d', 'ret_21d',
    'purple_dot', 'purple_dot_count_30d',
    'adr14_pct', 'adr20_pct', 'vol_ratio_20',
    'buying_force_score', 'bf_score_30d_max',
    'sma40_slope_pct', 'trp_pct', 'swing_high_20', 'swing_low_20',
    'pdh', 'inside_bar', 'range_contraction', 'bars_since_126d_high',
    'rhs_range_ratio', 'rhs_low_slope', 'rhs_today', 'stage',
    'minervini_pass',
]


def _jsonify(value):
    """Convert a numpy/pandas scalar into a JSON-safe Python value."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (int, float)):
        return value
    return value


def _feature_bag(row) -> dict:
    bag = {}
    for col in _FEATURE_COLS:
        if col in row:
            bag[col] = _jsonify(row[col])
    return bag


def run(conn, run_date: str) -> dict:
    """Compute daily features for every symbol in `daily_prices` up to `run_date`.

    For each symbol, loads its trailing daily OHLCV history (trade_date <=
    run_date) into a DataFrame, calls `compute_indicators_for_symbol`, and
    upserts one `features_daily` row per (symbol, trade_date=run_date) storing
    the computed feature dict as JSON in `feature_json`.

    Also writes a `pipeline_runs` row (stage='indicators'). Handles an empty
    `daily_prices` table gracefully (0 rows, status 'ok').

    Returns: {'run_date', 'symbols', 'rows_affected', 'status', 'duration_s'}.
    """
    started = time.time()
    cur = conn.cursor()

    cur.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE trade_date <= ? ORDER BY symbol",
        (run_date,),
    )
    symbols = [r[0] for r in cur.fetchall()]

    rows_affected = 0
    processed = 0
    upsert_sql = (
        "INSERT INTO features_daily (symbol, trade_date, feature_json, ingested_at) "
        "VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(symbol, trade_date) DO UPDATE SET "
        "feature_json=excluded.feature_json, ingested_at=excluded.ingested_at"
    )

    for sym in symbols:
        df = pd.read_sql_query(
            "SELECT symbol, trade_date AS date, open, high, low, close, volume "
            "FROM daily_prices WHERE symbol = ? AND trade_date <= ? "
            "ORDER BY trade_date ASC",
            conn,
            params=(sym, run_date),
        )
        if df.empty:
            continue
        feat_df = compute_indicators_for_symbol(df, float('nan'))
        if feat_df.empty:
            continue
        processed += 1
        # Feature bag for the run_date row (latest row at/<= run_date).
        latest = feat_df.iloc[-1]
        bag = _feature_bag(latest)
        cur.execute(upsert_sql, (sym, run_date, json.dumps(bag)))
        rows_affected += 1

    duration_s = round(time.time() - started, 4)
    status = "ok"
    detail = f"symbols={len(symbols)} processed={processed} rows={rows_affected}"
    cur.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, 'indicators', 'daily_prices', ?, ?, ?, ?)",
        (run_date, status, rows_affected, duration_s, detail),
    )
    conn.commit()

    return {
        "run_date": run_date,
        "symbols": len(symbols),
        "rows_affected": rows_affected,
        "status": status,
        "duration_s": duration_s,
    }
