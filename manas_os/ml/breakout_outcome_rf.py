"""Random-forest breakout-outcome probability model (shadow-only).

Governed by: manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md
Does NOT gate trades, controls position sizes, or influence live debate.
"""
from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score
    HAS_SKLEARN = True
except Exception:
    RandomForestClassifier = None
    roc_auc_score = None
    HAS_SKLEARN = False

from manas_os.engine import indicators_lite
from manas_os.alpha import promotion_gates

STAGE = "ml_breakout_rf"
SOURCE = "breakout_outcome_rf"
HORIZON_DAYS = 10
TARGET_PCT = 3.0
STOP_PCT = 2.5

FEATURE_COLS = [
    "rsi14",
    "volume_ratio",
    "ema_dist",
    "tr_atr_ratio",
    "ret_10d",
    "delivery_pct_z20",
    "rs"
]

# ---------------------------------------------------------------------------
# Raw Loaders
# ---------------------------------------------------------------------------

def load_price_frame(conn, symbols: list[str] | None = None) -> pd.DataFrame:
    sql = (
        "SELECT symbol, trade_date, open, high, low, close, volume, delivery_pct "
        "FROM daily_prices WHERE series='EQ'"
    )
    params: list = []
    if symbols:
        placeholders = ",".join("?" for _ in symbols)
        sql += f" AND symbol IN ({placeholders})"
        params = list(symbols)
    df = pd.read_sql_query(sql, conn, params=params)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    return df


def load_rs_frame(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT symbol, trade_date, rs_rating FROM screener_hits WHERE rs_rating IS NOT NULL",
        conn
    )
    if df.empty:
        return pd.DataFrame(columns=["symbol", "trade_date", "rs"])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.rename(columns={"rs_rating": "rs"})
    return df

# ---------------------------------------------------------------------------
# Pure per-symbol feature computation
# ---------------------------------------------------------------------------

def compute_symbol_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    delivery = df["delivery_pct"]

    out = pd.DataFrame(index=df.index)
    out["rsi14"] = indicators_lite.rsi(close, 14).fillna(50.0)
    
    vol_mean = volume.rolling(20, min_periods=10).mean()
    out["volume_ratio"] = (volume / vol_mean).fillna(1.0)
    
    ema20 = indicators_lite.ema(close, 20)
    out["ema_dist"] = (close / ema20 - 1.0).fillna(0.0)
    
    tr = indicators_lite.true_range(high, low, close)
    atr14 = indicators_lite.atr(high, low, close, 14)
    out["tr_atr_ratio"] = (tr / atr14).fillna(1.0)
    
    out["ret_10d"] = close.pct_change(10).fillna(0.0)
    
    d_mean = delivery.rolling(20, min_periods=10).mean()
    d_std = delivery.rolling(20, min_periods=10).std()
    out["delivery_pct_z20"] = ((delivery - d_mean) / d_std.replace(0, np.nan)).fillna(0.0)
    
    return out


def compute_asymmetric_label(df: pd.DataFrame) -> pd.Series:
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    labels = np.full(n, np.nan)
    
    for i in range(n - HORIZON_DAYS):
        entry = close[i]
        target_price = entry * (1 + TARGET_PCT / 100.0)
        stop_price = entry * (1 - STOP_PCT / 100.0)
        
        hit_target = False
        hit_stop = False
        
        for k in range(1, HORIZON_DAYS + 1):
            h = high[i + k]
            l = low[i + k]
            
            if h >= target_price:
                hit_target = True
            if l <= stop_price:
                hit_stop = True
                
            if hit_target or hit_stop:
                break
                
        if hit_target and not hit_stop:
            labels[i] = 1.0
        elif hit_stop:
            labels[i] = 0.0
        else:
            labels[i] = 0.0
            
    return pd.Series(labels, index=df.index)


def compute_trade_return(df: pd.DataFrame) -> pd.Series:
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    returns = np.full(n, np.nan)
    
    for i in range(n - HORIZON_DAYS):
        entry = close[i]
        target_price = entry * (1 + TARGET_PCT / 100.0)
        stop_price = entry * (1 - STOP_PCT / 100.0)
        
        hit_target = False
        hit_stop = False
        exit_price = close[i + HORIZON_DAYS]
        
        for k in range(1, HORIZON_DAYS + 1):
            h = high[i + k]
            l = low[i + k]
            
            if l <= stop_price:
                hit_stop = True
                exit_price = stop_price
                break
            if h >= target_price:
                hit_target = True
                exit_price = target_price
                break
                
        returns[i] = (exit_price - entry) / entry * 100.0
        
    return pd.Series(returns, index=df.index)

# ---------------------------------------------------------------------------
# Full dataset assembly
# ---------------------------------------------------------------------------

def build_feature_matrix(conn, symbols: list[str] | None = None) -> pd.DataFrame:
    prices = load_price_frame(conn, symbols)
    if prices.empty:
        return pd.DataFrame(columns=["symbol", "trade_date", *FEATURE_COLS, "label", "trade_ret"])

    rs_df = load_rs_frame(conn)
    feature_frames = []
    
    for sym, sub in prices.groupby("symbol", sort=False):
        sub = sub.reset_index(drop=True)
        if len(sub) < 30:
            continue
        feats = compute_symbol_features(sub)
        feats.insert(0, "trade_date", sub["trade_date"])
        feats.insert(0, "symbol", sym)
        
        high_20d = sub["high"].rolling(20).max().shift(1)
        feats["is_breakout"] = sub["close"] > high_20d
        
        label = compute_asymmetric_label(sub)
        feats["label"] = label
        
        trade_ret = compute_trade_return(sub)
        feats["trade_ret"] = trade_ret
        
        feature_frames.append(feats)

    if not feature_frames:
        return pd.DataFrame(columns=["symbol", "trade_date", *FEATURE_COLS, "label", "trade_ret"])
        
    feat_df = pd.concat(feature_frames, ignore_index=True)
    
    feat_df = feat_df.merge(rs_df, on=["symbol", "trade_date"], how="left")
    feat_df["rs"] = feat_df["rs"].fillna(50.0)
    
    breakout_df = feat_df[feat_df["is_breakout"] == True].copy()
    
    return breakout_df[["symbol", "trade_date", *FEATURE_COLS, "label", "trade_ret"]]

# ---------------------------------------------------------------------------
# Walk-forward validation & Battery
# ---------------------------------------------------------------------------

def walk_forward_validate(df: pd.DataFrame, min_train_rows: int = 200) -> dict[str, Any]:
    if not HAS_SKLEARN:
        return {"verdict": "skipped", "reason": "sklearn not installed"}
        
    d = df.dropna(subset=[*FEATURE_COLS, "label"]).copy()
    d["month"] = d["trade_date"].dt.to_period("M").astype(str)
    months = sorted(d["month"].unique())
    
    signal_returns = []
    baseline_returns = []
    
    for test_month in months:
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        
        if len(train) < min_train_rows or test.empty:
            continue
            
        X_train, y_train = train[FEATURE_COLS], train["label"]
        X_test, y_test = test[FEATURE_COLS], test["label"]
        
        if y_train.nunique() < 2:
            continue
            
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        proba = model.predict_proba(X_test)[:, 1]
        
        test_rets = test["trade_ret"].values
        for p, r in zip(proba, test_rets):
            baseline_returns.append(r)
            if p > 0.5:
                signal_returns.append(r)
                
    battery = promotion_gates.run_promotion_battery(
        signal_returns=signal_returns,
        baseline_returns=baseline_returns,
        hypothesis="RandomForest Breakout Outcome Model",
        config={"model": "RandomForestClassifier", "n_estimators": 200, "max_depth": 5}
    )
    
    return battery

# ---------------------------------------------------------------------------
# Persistence & CLI
# ---------------------------------------------------------------------------

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ml_breakout_scores ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "p_success REAL, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )

def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def run(conn, run_date: str, shortlist_symbols: list[str] | None = None) -> int:
    started = time.monotonic()
    if not HAS_SKLEARN:
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 "scikit-learn not installed")
        conn.commit()
        return 0
        
    try:
        ensure_schema(conn)
        if shortlist_symbols is None:
            rows = conn.execute(
                "SELECT DISTINCT symbol FROM scan_candidates WHERE scan_date = ?",
                (run_date,),
            ).fetchall()
            shortlist_symbols = [r[0] for r in rows]
            
        if not shortlist_symbols:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "no shortlist symbols")
            conn.commit()
            return 0
            
        full = build_feature_matrix(conn)
        train = full[full["trade_date"] < pd.Timestamp(run_date)]
        train = train.dropna(subset=[*FEATURE_COLS, "label"])
        
        if len(train) < 200 or train["label"].nunique() < 2:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "insufficient training history")
            conn.commit()
            return 0
            
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(train[FEATURE_COLS], train["label"])
        
        written = 0
        for sym in shortlist_symbols:
            df_sym = build_feature_matrix(conn, symbols=[sym])
            if df_sym.empty:
                continue
            df_sym = df_sym[df_sym["trade_date"] <= pd.Timestamp(run_date)]
            if df_sym.empty:
                continue
            row = df_sym.iloc[-1]
            if row[FEATURE_COLS].isna().any():
                continue
                
            proba = float(model.predict_proba(pd.DataFrame([row[FEATURE_COLS]]))[0, 1])
            
            conn.execute(
                "INSERT INTO ml_breakout_scores (scan_date, symbol, p_success) "
                "VALUES (?,?,?) ON CONFLICT(scan_date, symbol) DO UPDATE SET "
                "p_success=excluded.p_success",
                (run_date, sym, proba),
            )
            written += 1
            
        _log_run(conn, run_date, "ok", written, time.monotonic() - started,
                 f"{written} breakout outcome score(s) written")
        conn.commit()
        return written
        
    except Exception as exc:
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return 0
