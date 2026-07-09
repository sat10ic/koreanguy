"""SHIP-1 #7 — LightGBM directional classifier (EXPERIMENTAL, walk-forward only).

AD8 (binding): this module produces a labeled probability FACT — P(close 10
sessions from now > close today) — plus its top-3 SHAP drivers. It NEVER
gates, sizes, or feeds any composite/score used by risk/plan.py or the
debate/gate machinery. Nothing in this file imports scanner.gates,
risk.plan, or agents.debate, and nothing in those modules imports this file
(grep-verified at write time — keep it that way on every edit).

Data reality (as of 2026-07-10, see manas_os/design/LEARNINGS.md):
  - daily_prices: ~285 trading sessions (2025-03-19 .. 2026-07-09), ~2,761
    EQ-series symbols. This is the ONLY table with full-history coverage,
    so price/volume/delivery-derived features are the primary signal.
  - fii_dii_daily: 21 rows (2026-06-09 .. 07-08) — market-wide, thin. The
    FII/DII feature is 0 (neutral) outside that window.
  - disclosures (bulk_deal kind): from 2026-01-13 — usable for the back
    half of the walk-forward window only.
  - screener_hits.basic_industry: only 2026-07-05..10 — there is no
    point-in-time sector/industry table with full history. We take the
    MOST RECENT known basic_industry per symbol as a static map and apply
    it across all history. This is a known approximation (a symbol's
    industry rarely changes, but the mapping is not point-in-time correct
    for any re-classifications) — documented, not hidden.
  - universe table (symbol -> sector) is empty on this DB; not used.

Leakage rule: every feature at (symbol, as_of_date) is computed ONLY from
rows with trade_date <= as_of_date. Pandas rolling/pct_change/ewm windows
are backward-looking by construction, so truncating future rows never
changes a past feature value (see test_ml_direction_leakage.py).
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
except Exception:  # pragma: no cover - exercised via HAS_LIGHTGBM=False path
    lgb = None

try:
    import shap
except Exception:  # pragma: no cover
    shap = None

HAS_LIGHTGBM = lgb is not None
HAS_SHAP = shap is not None

STAGE = "ml_direction"
SOURCE = "direction_lgbm"
HORIZON_DAYS = 10
MIN_HISTORY_DAYS = 65  # need >=60d lookback + a couple of warmup bars

FEATURE_COLS = [
    "ret_5d",
    "ret_20d",
    "ret_60d",
    "vol_20d",
    "delivery_pct",
    "delivery_pct_z20",
    "volume_z20",
    "dist_from_52w_high",
    "ema_stack_state",
    "sector_rel_ret_20d",
    "fii_dii_net5d_z",
    "bulk_deal_flag_5d",
]


# ---------------------------------------------------------------------------
# Raw loaders
# ---------------------------------------------------------------------------

def load_price_frame(conn, symbols: list[str] | None = None) -> pd.DataFrame:
    """Full-history EQ-series price/volume/delivery frame, one row per
    (symbol, trade_date), sorted ascending. Only uses daily_prices."""
    sql = (
        "SELECT symbol, trade_date, close, volume, delivery_pct "
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


def load_industry_map(conn) -> dict[str, str]:
    """Static best-effort symbol -> basic_industry map: most recent known
    value per symbol from screener_hits (see module docstring caveat)."""
    df = pd.read_sql_query(
        "SELECT symbol, basic_industry, trade_date FROM screener_hits "
        "WHERE basic_industry IS NOT NULL AND basic_industry != ''",
        conn,
    )
    if df.empty:
        return {}
    df = df.sort_values("trade_date").drop_duplicates("symbol", keep="last")
    return dict(zip(df["symbol"], df["basic_industry"]))


def load_fii_dii_frame(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT trade_date, fii_net, dii_net FROM fii_dii_daily ORDER BY trade_date", conn
    )
    if df.empty:
        return pd.DataFrame(columns=["trade_date", "fii_dii_net5d_z"])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["net"] = df["fii_net"].fillna(0) + df["dii_net"].fillna(0)
    df["net5d"] = df["net"].rolling(5, min_periods=1).sum()
    mean = df["net5d"].rolling(10, min_periods=3).mean()
    std = df["net5d"].rolling(10, min_periods=3).std()
    df["fii_dii_net5d_z"] = ((df["net5d"] - mean) / std.replace(0, np.nan)).fillna(0.0)
    return df[["trade_date", "fii_dii_net5d_z"]]


def load_bulk_deal_dates(conn) -> dict[str, set]:
    """symbol -> set of trade_date (Timestamp) with a bulk_deal disclosure."""
    df = pd.read_sql_query(
        "SELECT symbol, trade_date FROM disclosures WHERE kind='bulk_deal'", conn
    )
    if df.empty:
        return {}
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    out: dict[str, set] = {}
    for sym, sub in df.groupby("symbol"):
        out[sym] = set(sub["trade_date"])
    return out


# ---------------------------------------------------------------------------
# Pure per-symbol feature computation (leakage-safe: backward-looking only)
# ---------------------------------------------------------------------------

def compute_symbol_features(df: pd.DataFrame) -> pd.DataFrame:
    """df: one symbol's rows (trade_date ascending, columns close/volume/
    delivery_pct), already truncated to <= as_of_date by the caller.
    Returns a frame aligned to df.index with the price/volume/delivery
    derived feature columns (NOT sector/fii-dii/bulk-deal — those are
    joined in by the caller since they need cross-symbol/market data)."""
    close = df["close"]
    ret1 = close.pct_change()

    out = pd.DataFrame(index=df.index)
    out["ret_5d"] = close.pct_change(5)
    out["ret_20d"] = close.pct_change(20)
    out["ret_60d"] = close.pct_change(60)
    out["vol_20d"] = ret1.rolling(20, min_periods=10).std()

    delivery = df["delivery_pct"]
    out["delivery_pct"] = delivery
    d_mean = delivery.rolling(20, min_periods=10).mean()
    d_std = delivery.rolling(20, min_periods=10).std()
    out["delivery_pct_z20"] = ((delivery - d_mean) / d_std.replace(0, np.nan))

    volume = df["volume"]
    v_mean = volume.rolling(20, min_periods=10).mean()
    v_std = volume.rolling(20, min_periods=10).std()
    out["volume_z20"] = ((volume - v_mean) / v_std.replace(0, np.nan))

    roll_high = close.rolling(252, min_periods=60).max()
    out["dist_from_52w_high"] = close / roll_high - 1.0

    ema5 = close.ewm(span=5, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    bullish = (ema5 > ema20) & (ema20 > ema50)
    bearish = (ema5 < ema20) & (ema20 < ema50)
    out["ema_stack_state"] = np.select([bullish, bearish], [1, -1], default=0)

    return out


def compute_forward_label(df: pd.DataFrame) -> pd.Series:
    """Sign of forward HORIZON_DAYS return. Uses FUTURE rows deliberately
    (this is the label, not a feature) — NaN where the future window isn't
    present in df yet (most recent HORIZON_DAYS rows of the loaded frame)."""
    close = df["close"]
    fwd = close.shift(-HORIZON_DAYS) / close - 1.0
    return (fwd > 0).astype("float").where(fwd.notna())


# ---------------------------------------------------------------------------
# Full dataset assembly
# ---------------------------------------------------------------------------

def build_feature_matrix(conn, symbols: list[str] | None = None) -> pd.DataFrame:
    """Vectorized full-history feature matrix, one row per (symbol,
    trade_date) with all FEATURE_COLS + the forward-return label.
    Every feature column at a given row uses only that symbol's rows up
    to and including trade_date (see compute_symbol_features) plus, for
    the market-wide/sector columns, other symbols' same-date-or-earlier
    values — never a later date than the row's own trade_date."""
    prices = load_price_frame(conn, symbols)
    if prices.empty:
        return pd.DataFrame(columns=["symbol", "trade_date", *FEATURE_COLS, "label"])

    industry_map = load_industry_map(conn)
    fii_dii = load_fii_dii_frame(conn)
    bulk_deals = load_bulk_deal_dates(conn)

    feature_frames = []
    label_frames = []
    for sym, sub in prices.groupby("symbol", sort=False):
        sub = sub.reset_index(drop=True)
        feats = compute_symbol_features(sub)
        feats.insert(0, "trade_date", sub["trade_date"])
        feats.insert(0, "symbol", sym)
        feature_frames.append(feats)
        label = compute_forward_label(sub)
        label_frames.append(pd.DataFrame({"symbol": sym, "trade_date": sub["trade_date"], "label": label}))

    feat_df = pd.concat(feature_frames, ignore_index=True)
    label_df = pd.concat(label_frames, ignore_index=True)

    # Sector (industry) 20d relative return: symbol's ret_20d minus the
    # same-date mean ret_20d across all symbols mapped to its industry.
    feat_df["industry"] = feat_df["symbol"].map(industry_map)
    industry_mean = (
        feat_df.dropna(subset=["industry"])
        .groupby(["industry", "trade_date"])["ret_20d"]
        .transform("mean")
    )
    feat_df["sector_rel_ret_20d"] = np.nan
    mask = feat_df["industry"].notna()
    feat_df.loc[mask, "sector_rel_ret_20d"] = (
        feat_df.loc[mask, "ret_20d"] - industry_mean.reindex(feat_df.index[mask])
    )
    feat_df["sector_rel_ret_20d"] = feat_df["sector_rel_ret_20d"].fillna(0.0)

    # FII/DII: market-wide, join on trade_date.
    feat_df = feat_df.merge(fii_dii, on="trade_date", how="left")
    feat_df["fii_dii_net5d_z"] = feat_df["fii_dii_net5d_z"].fillna(0.0)

    # Bulk-deal flag: 1 if symbol had a bulk_deal disclosure in the
    # trailing 5 sessions (inclusive of trade_date), else 0.
    def _bulk_flag(row):
        dates = bulk_deals.get(row["symbol"])
        if not dates:
            return 0
        window = pd.date_range(end=row["trade_date"], periods=5, freq="D")
        return int(any(d in dates for d in window))

    feat_df["bulk_deal_flag_5d"] = feat_df.apply(_bulk_flag, axis=1)

    out = feat_df.merge(label_df, on=["symbol", "trade_date"], how="left")
    return out[["symbol", "trade_date", *FEATURE_COLS, "label"]]


def build_features_for_symbol_date(conn, symbol: str, as_of_date: str) -> dict | None:
    """Single (symbol, as_of_date) feature row from data <= as_of_date only.
    Used by the nightly scoring stage. Returns None if there isn't enough
    history yet."""
    df = build_feature_matrix(conn, symbols=[symbol])
    if df.empty:
        return None
    df = df[df["trade_date"] <= pd.Timestamp(as_of_date)]
    if df.empty:
        return None
    row = df.iloc[-1]
    if row[["ret_60d", "vol_20d"]].isna().any():
        return None
    return {c: row[c] for c in FEATURE_COLS}


# ---------------------------------------------------------------------------
# Walk-forward validation
# ---------------------------------------------------------------------------

@dataclass
class FoldResult:
    test_month: str
    n: int
    auc: float | None
    hit_rate: float
    baseline_hit_rate: float


def _clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=[*FEATURE_COLS, "label"]).copy()
    d["month"] = d["trade_date"].dt.to_period("M").astype(str)
    return d


def walk_forward_validate(df: pd.DataFrame, min_train_rows: int = 500) -> tuple[list[FoldResult], dict]:
    """Expanding-window, monthly refit. Train on all months strictly before
    the test month, score the test month OOS. Returns (per-fold results,
    pooled summary)."""
    if not HAS_LIGHTGBM:
        raise RuntimeError("lightgbm not installed")

    d = _clean_dataset(df)
    months = sorted(d["month"].unique())
    folds: list[FoldResult] = []
    pooled_y, pooled_p, pooled_baseline = [], [], []

    for i, test_month in enumerate(months):
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        if len(train) < min_train_rows or test.empty:
            continue
        X_train, y_train = train[FEATURE_COLS], train["label"]
        X_test, y_test = test[FEATURE_COLS], test["label"]
        if y_train.nunique() < 2:
            continue

        model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=4,
            num_leaves=15,
            learning_rate=0.05,
            min_child_samples=30,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba > 0.5).astype(int)

        baseline_hit = float(y_test.mean())  # "always up" baseline
        hit = float((pred == y_test).mean())
        try:
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(y_test, proba)) if y_test.nunique() > 1 else None
        except Exception:
            auc = None

        folds.append(FoldResult(
            test_month=test_month, n=len(test), auc=auc,
            hit_rate=hit, baseline_hit_rate=baseline_hit,
        ))
        pooled_y.extend(y_test.tolist())
        pooled_p.extend(proba.tolist())
        pooled_baseline.extend(y_test.tolist())

    pooled = {"n": len(pooled_y), "auc": None, "hit_rate": None, "baseline_hit_rate": None}
    if pooled_y:
        y_arr = np.array(pooled_y)
        p_arr = np.array(pooled_p)
        pooled["hit_rate"] = float(((p_arr > 0.5).astype(int) == y_arr).mean())
        pooled["baseline_hit_rate"] = float(y_arr.mean())
        try:
            from sklearn.metrics import roc_auc_score
            pooled["auc"] = float(roc_auc_score(y_arr, p_arr)) if len(set(y_arr.tolist())) > 1 else None
        except Exception:
            pooled["auc"] = None
    return folds, pooled


def format_walk_forward_report(folds: list[FoldResult], pooled: dict) -> str:
    lines = ["month       n      AUC     hit    baseline"]
    for f in folds:
        auc_s = f"{f.auc:.3f}" if f.auc is not None else "n/a"
        lines.append(f"{f.test_month}  {f.n:5d}  {auc_s:>6}  {f.hit_rate:.3f}  {f.baseline_hit_rate:.3f}")
    auc_s = f"{pooled['auc']:.3f}" if pooled.get("auc") is not None else "n/a"
    lines.append(f"POOLED      {pooled['n']:5d}  {auc_s:>6}  {pooled['hit_rate']:.3f}  {pooled['baseline_hit_rate']:.3f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full-history model + SHAP drivers (only meaningful if display threshold met)
# ---------------------------------------------------------------------------

def train_final_model(df: pd.DataFrame):
    if not HAS_LIGHTGBM:
        raise RuntimeError("lightgbm not installed")
    d = _clean_dataset(df)
    model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=4, num_leaves=15, learning_rate=0.05,
        min_child_samples=30, subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbosity=-1,
    )
    model.fit(d[FEATURE_COLS], d["label"])
    return model


def top_drivers(model, row: dict, n: int = 3) -> list[tuple[str, float]]:
    """Top-n |SHAP value| feature contributions for a single feature row.
    Falls back to model feature_importances_ ranking if shap isn't
    installed (still labeled EXPERIMENTAL either way by the caller)."""
    X = pd.DataFrame([row])[FEATURE_COLS]
    if HAS_SHAP:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X)
        vals = sv[1][0] if isinstance(sv, list) else sv[0]
        pairs = list(zip(FEATURE_COLS, vals))
    else:
        importances = model.feature_importances_
        pairs = list(zip(FEATURE_COLS, importances))
    pairs.sort(key=lambda p: abs(p[1]), reverse=True)
    return pairs[:n]


def driver_label(name: str, value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{name}{sign}"


# ---------------------------------------------------------------------------
# ml_scores schema + nightly stage (only wired to run-eod if display
# threshold is met — see manas_os/cli/__init__.py comment when/if added)
# ---------------------------------------------------------------------------

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ml_scores ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, "
        "p_up_10d REAL, top_drivers_json TEXT, "
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
    """Nightly scoring stage. Failure-safe: any missing dependency (no
    lightgbm installed) or any error is a `skip`, not a `fail` — this stage
    must never break run-eod. Writes ml_scores for `shortlist_symbols`
    (defaults to the current watchlist) using a model trained on all data
    strictly before run_date (no leakage into today's score).
    """
    started = time.monotonic()
    if not HAS_LIGHTGBM:
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 "lightgbm not installed")
        conn.commit()
        return 0
    try:
        ensure_schema(conn)
        if shortlist_symbols is None:
            rows = conn.execute("SELECT DISTINCT symbol FROM watchlist").fetchall()
            shortlist_symbols = [r[0] for r in rows]
        if not shortlist_symbols:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "no shortlist symbols")
            conn.commit()
            return 0

        full = build_feature_matrix(conn)
        train = full[full["trade_date"] < pd.Timestamp(run_date)]
        train = _clean_dataset(train)
        if len(train) < 500 or train["label"].nunique() < 2:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "insufficient training history")
            conn.commit()
            return 0

        model = train_final_model(train)
        written = 0
        for sym in shortlist_symbols:
            row = build_features_for_symbol_date(conn, sym, run_date)
            if row is None:
                continue
            proba = float(model.predict_proba(pd.DataFrame([row])[FEATURE_COLS])[0, 1])
            drivers = top_drivers(model, row, n=3)
            drivers_str = [driver_label(n, v) for n, v in drivers]
            conn.execute(
                "INSERT INTO ml_scores (scan_date, symbol, p_up_10d, top_drivers_json) "
                "VALUES (?,?,?,?) ON CONFLICT(scan_date, symbol) DO UPDATE SET "
                "p_up_10d=excluded.p_up_10d, top_drivers_json=excluded.top_drivers_json",
                (run_date, sym, proba, json.dumps(drivers_str)),
            )
            written += 1
        _log_run(conn, run_date, "ok", written, time.monotonic() - started,
                 f"{written} symbol(s) scored")
        conn.commit()
        return written
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return 0
