"""SHIP-1 #15 (I14) — Hierarchical (empirical-Bayes ridge) sector downside risk.

AD8 (binding): this module produces a labeled probability FACT — P(sector
drawdown >= 2% over the next 5 sessions) — per sector, per day. It NEVER
gates, sizes, or feeds risk/plan.py, scanner/gates.py, or the debate/gate
machinery. Nothing here imports those modules; nothing there imports this.

Method (partial pooling via empirical-Bayes ridge, NO PyMC dependency, per
WAVE_I_SPEC I14): panel is (sector, day) from sector_index_prices (~2y,
15 sectors with a real Fyers index — see regime/sectors.py SECTOR_INDICES).
Predictors, computed from ONLY data <= that day:
  - sector_rv20   : sector's trailing-20d realized vol (std of daily log
                    returns, annualized %)
  - sector_ret5d  : sector's trailing 5-day return
  - market_ret5d  : NIFTY 50 trailing 5-day return (same value across
                    sectors on a given day — the market-wide predictor)
  - vix_level     : India VIX level (full 2y history in sector_index_prices)
  - vix_chg5d     : India VIX 5-day change
FII/DII z-score was in the original I14 predictor list but fii_dii_daily
only has 21 rows in this DB (2026-06-09..07-08) — nowhere near enough for a
2y panel, so it is OMITTED here, not silently zero-filled. Logged below.

Target: forward-5d sector drawdown event = sector return over the next 5
sessions <= -2%.

Fit: pooled logistic regression first (single intercept + shared
coefficients, all sector-days together) via Newton-Raphson IRLS. Then, per
sector, refit with an L2 penalty that pulls the sector's coefficients
toward the POOLED coefficients (not toward zero) — this is the
empirical-Bayes ridge approximation to a hierarchical model: sectors with
more/more-informative data pull away from the pooled prior more; thin
sectors stay close to it. Penalty strength scales inversely with the
sector's row count (thin cells shrink harder), the textbook partial-pooling
behavior for 490 days / 15 sectors thin cells.

Validation: walk-forward, expanding window, monthly refit (same pattern as
direction_lgbm.py / regime/vol_har.py). Metric: Brier score vs a base-rate
baseline (this sector's own trailing training-window event frequency,
predicted as a constant). Persist sector_downside ONLY if the pooled
walk-forward Brier beats the baseline; otherwise NOT-FOR-DISPLAY, logged.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from manas_os.regime.sectors import SECTORS

STAGE = "ml_sector_downside"
SOURCE = "sector_downside"
NIFTY_SYMBOL = "NIFTY 50"
VIX_SYMBOL = "India VIX"
HORIZON_DAYS = 5
DRAWDOWN_THRESHOLD = -0.02
MIN_HISTORY_DAYS = 25
FEATURE_COLS = ["sector_rv20", "sector_ret5d", "market_ret5d", "vix_level", "vix_chg5d"]

SECTOR_INDEX_KEYS: dict[str, str] = {s["index"]: s["key"] for s in SECTORS if s["index"]}


# ---------------------------------------------------------------------------
# Raw loaders
# ---------------------------------------------------------------------------

def load_index_series(conn, symbol: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT trade_date, close FROM sector_index_prices WHERE symbol = ? ORDER BY trade_date ASC",
        conn, params=(symbol,),
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


# ---------------------------------------------------------------------------
# Panel construction (backward-looking features; forward-looking label)
# ---------------------------------------------------------------------------

def build_panel(conn) -> pd.DataFrame:
    """One row per (sector_key, trade_date). Every FEATURE_COLS value at row
    t uses only data <= t; `label` uses data > t (the target)."""
    market = load_index_series(conn, NIFTY_SYMBOL)
    vix = load_index_series(conn, VIX_SYMBOL)
    if market.empty or vix.empty:
        return pd.DataFrame(columns=["sector_key", "trade_date", *FEATURE_COLS, "label"])

    market = market.rename(columns={"close": "nifty_close"})
    market["market_ret5d"] = market["nifty_close"].pct_change(5)

    vix = vix.rename(columns={"close": "vix_level"})
    vix["vix_chg5d"] = vix["vix_level"].diff(5)

    market_join = market[["trade_date", "market_ret5d"]]
    vix_join = vix[["trade_date", "vix_level", "vix_chg5d"]]

    frames = []
    for symbol, sector_key in SECTOR_INDEX_KEYS.items():
        s = load_index_series(conn, symbol)
        if s.empty:
            continue
        s = s.sort_values("trade_date").reset_index(drop=True)
        ret1 = s["close"].pct_change()
        s["sector_rv20"] = ret1.rolling(20, min_periods=20).std() * math.sqrt(252) * 100
        s["sector_ret5d"] = s["close"].pct_change(5)
        s["label"] = (s["close"].shift(-HORIZON_DAYS) / s["close"] - 1.0 <= DRAWDOWN_THRESHOLD).astype(float)
        # NaN out the label where the forward window isn't present yet.
        s.loc[s["close"].shift(-HORIZON_DAYS).isna(), "label"] = np.nan
        s = s.merge(market_join, on="trade_date", how="left").merge(vix_join, on="trade_date", how="left")
        s["sector_key"] = sector_key
        frames.append(s[["sector_key", "trade_date", *FEATURE_COLS, "label"]])

    if not frames:
        return pd.DataFrame(columns=["sector_key", "trade_date", *FEATURE_COLS, "label"])
    return pd.concat(frames, ignore_index=True)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=[*FEATURE_COLS, "label"]).copy()
    d["month"] = d["trade_date"].dt.to_period("M").astype(str)
    return d


# ---------------------------------------------------------------------------
# Empirical-Bayes ridge logistic regression (Newton-Raphson IRLS)
# ---------------------------------------------------------------------------

def fit_feature_scaler(d_train: pd.DataFrame) -> dict:
    """Per-feature (mean, std) from the TRAINING window only — the model is
    fit on data <= a given day, so the scaler must be too (no leakage from
    scaling on data the fold hasn't seen yet). Standardizing matters a lot
    here: sector_rv20 is O(10-40), vix_level O(10-20), the returns are
    O(0.01-0.05) — Newton-IRLS on the raw scales gives a badly-conditioned
    Hessian and the ridge penalty lands unevenly across coefficients."""
    means = d_train[FEATURE_COLS].mean()
    stds = d_train[FEATURE_COLS].std().replace(0, 1.0)
    return {"mean": means, "std": stds}


def apply_feature_scaler(d: pd.DataFrame, scaler: dict) -> pd.DataFrame:
    out = d.copy()
    out[FEATURE_COLS] = (out[FEATURE_COLS] - scaler["mean"]) / scaler["std"]
    return out


def _design(d: pd.DataFrame) -> np.ndarray:
    X = d[FEATURE_COLS].to_numpy(dtype=float)
    return np.column_stack([np.ones(len(d)), X])


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_ridge_logistic(
    X: np.ndarray, y: np.ndarray, prior: np.ndarray | None = None,
    lam: float = 1.0, n_iter: int = 50, tol: float = 1e-7,
) -> np.ndarray:
    """Newton-Raphson IRLS for L2-penalized logistic regression, penalty
    lam/2 * ||beta - prior||^2 (prior defaults to zero — the pooled fit;
    a non-zero prior is the empirical-Bayes shrinkage-toward-pooled step
    used for the per-sector fits)."""
    n, p = X.shape
    beta = np.zeros(p) if prior is None else prior.copy()
    prior_vec = np.zeros(p) if prior is None else prior
    reg = lam * np.eye(p)
    for _ in range(n_iter):
        eta = X @ beta
        mu = _sigmoid(eta)
        w = np.clip(mu * (1 - mu), 1e-6, None)
        grad = X.T @ (mu - y) + lam * (beta - prior_vec)
        H = (X * w[:, None]).T @ X + reg
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new
    return beta


def sector_shrinkage_lambda(n_sector_rows: int, base_lambda: float = 5000.0) -> float:
    """Shrinkage strength toward the pooled fit — inversely proportional to
    the sector's own row count (thin cells shrink hard toward pooled; large
    cells drift closer to their own MLE). This IS the "empirical-Bayes
    ridge approximation" standing in for a full hierarchical/PyMC fit."""
    return base_lambda / max(n_sector_rows, 1)


def fit_hierarchical(d_train: pd.DataFrame) -> dict:
    """Pooled fit + per-sector shrunk fits. Returns
    {'pooled': beta, 'per_sector': {sector_key: beta}}."""
    X_pool = _design(d_train)
    y_pool = d_train["label"].to_numpy(dtype=float)
    pooled_beta = fit_ridge_logistic(X_pool, y_pool, prior=None, lam=100.0)

    per_sector = {}
    for sector_key, sub in d_train.groupby("sector_key"):
        X_s = _design(sub)
        y_s = sub["label"].to_numpy(dtype=float)
        if y_s.sum() == 0 or y_s.sum() == len(y_s):
            # Degenerate (no variation) — fall back to the pooled fit outright.
            per_sector[sector_key] = pooled_beta
            continue
        lam = sector_shrinkage_lambda(len(sub))
        per_sector[sector_key] = fit_ridge_logistic(X_s, y_s, prior=pooled_beta, lam=lam)
    return {"pooled": pooled_beta, "per_sector": per_sector}


def predict_proba(model: dict, d: pd.DataFrame) -> np.ndarray:
    out = np.zeros(len(d))
    X = _design(d)
    for sector_key, sub in d.groupby("sector_key"):
        beta = model["per_sector"].get(sector_key, model["pooled"])
        idx = d.index.get_indexer(sub.index)
        out[idx] = _sigmoid(X[idx] @ beta)
    return out


def brier_score(y_true: np.ndarray, p_pred: np.ndarray) -> float:
    return float(np.mean((p_pred - y_true) ** 2))


# ---------------------------------------------------------------------------
# Walk-forward validation
# ---------------------------------------------------------------------------

@dataclass
class FoldResult:
    test_month: str
    n: int
    brier_model: float
    brier_baseline: float


def walk_forward_validate(df: pd.DataFrame, min_train_rows: int = 200):
    d = _clean(df)
    months = sorted(d["month"].unique())
    folds: list[FoldResult] = []
    pooled_y, pooled_p_model, pooled_p_base = [], [], []

    for test_month in months:
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        if len(train) < min_train_rows or test.empty or train["label"].nunique() < 2:
            continue
        scaler = fit_feature_scaler(train)
        train_s = apply_feature_scaler(train, scaler)
        test_s = apply_feature_scaler(test, scaler)
        model = fit_hierarchical(train_s)
        p_model = predict_proba(model, test_s)

        # Base-rate baseline: each sector's OWN trailing-training event
        # frequency, predicted as a constant for every row of that sector
        # in the test month (falls back to pooled rate if a sector has no
        # training rows yet).
        pooled_rate = train["label"].mean()
        base_rate = train.groupby("sector_key")["label"].mean()
        p_base = test["sector_key"].map(base_rate).fillna(pooled_rate).to_numpy()

        y_test = test["label"].to_numpy(dtype=float)
        folds.append(FoldResult(
            test_month=test_month, n=len(test),
            brier_model=brier_score(y_test, p_model),
            brier_baseline=brier_score(y_test, p_base),
        ))
        pooled_y.extend(y_test.tolist())
        pooled_p_model.extend(p_model.tolist())
        pooled_p_base.extend(p_base.tolist())

    pooled = {
        "n": len(pooled_y),
        "brier_model": brier_score(np.array(pooled_y), np.array(pooled_p_model)) if pooled_y else None,
        "brier_baseline": brier_score(np.array(pooled_y), np.array(pooled_p_base)) if pooled_y else None,
    }
    return folds, pooled


def format_walk_forward_report(folds: list[FoldResult], pooled: dict) -> str:
    lines = ["month       n     Brier(model)  Brier(baseline)"]
    for f in folds:
        lines.append(f"{f.test_month}  {f.n:4d}  {f.brier_model:12.5f}  {f.brier_baseline:12.5f}")
    if pooled["n"]:
        lines.append(f"POOLED      {pooled['n']:4d}  {pooled['brier_model']:12.5f}  {pooled['brier_baseline']:12.5f}")
    return "\n".join(lines)


def beats_baseline(pooled: dict) -> bool:
    return bool(
        pooled.get("n") and pooled.get("brier_model") is not None
        and pooled["brier_model"] < pooled["brier_baseline"]
    )


# ---------------------------------------------------------------------------
# Nightly stage: gated persistence
# ---------------------------------------------------------------------------

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sector_downside ("
        "as_of TEXT NOT NULL, sector TEXT NOT NULL, "
        "p_drawdown_5d REAL, n_train INTEGER, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (as_of, sector))"
    )


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def run(conn, run_date: str) -> dict:
    """Nightly stage. Failure-safe: any error is a `skip`, never a `fail`.
    Recomputes the walk-forward gate on data strictly before run_date; only
    if it currently beats the base-rate baseline does it fit today's model
    and write sector_downside rows for run_date."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        full = build_panel(conn)
        if full.empty:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "no sector_index_prices panel (missing NIFTY 50/India VIX/sector indices)")
            conn.commit()
            return {"status": "skip", "detail": "no panel"}

        train_full = full[full["trade_date"] < pd.Timestamp(run_date)]
        d_train_full = _clean(train_full)
        if len(d_train_full) < 200:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "insufficient panel history for walk-forward")
            conn.commit()
            return {"status": "skip", "detail": "insufficient history"}

        _, pooled = walk_forward_validate(train_full)
        if not beats_baseline(pooled):
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     f"sector downside model does not beat base-rate baseline "
                     f"(Brier {pooled.get('brier_model')} vs {pooled.get('brier_baseline')}) — NOT-FOR-DISPLAY")
            conn.commit()
            return {"status": "skip", "detail": "does not beat baseline", "pooled": pooled}

        today = full[full["trade_date"] == pd.Timestamp(run_date)].dropna(subset=FEATURE_COLS)
        if today.empty:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "no complete feature row for run_date")
            conn.commit()
            return {"status": "skip", "detail": "no row for run_date"}

        scaler = fit_feature_scaler(d_train_full)
        model = fit_hierarchical(apply_feature_scaler(d_train_full, scaler))
        p_today = predict_proba(model, apply_feature_scaler(today, scaler))
        written = 0
        for (sector_key,), p in zip(today[["sector_key"]].to_numpy(), p_today):
            n_train = int((d_train_full["sector_key"] == sector_key).sum())
            conn.execute(
                "INSERT INTO sector_downside (as_of, sector, p_drawdown_5d, n_train) VALUES (?,?,?,?) "
                "ON CONFLICT(as_of, sector) DO UPDATE SET p_drawdown_5d=excluded.p_drawdown_5d, n_train=excluded.n_train",
                (run_date, sector_key, float(p), n_train),
            )
            written += 1
        _log_run(conn, run_date, "ok", written, time.monotonic() - started,
                 f"{written} sector(s) scored, pooled Brier {pooled['brier_model']:.5f} vs "
                 f"baseline {pooled['brier_baseline']:.5f}")
        conn.commit()
        return {"status": "ok", "detail": "written", "pooled": pooled, "written": written}
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started, f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return {"status": "skip", "detail": f"error: {exc}"}
