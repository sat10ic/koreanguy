"""SHIP-1 #16 (I1) — HAR-RV volatility forecaster (EXPERIMENTAL, display-only
until it beats the naive baseline).

AD8 (binding): this module produces a labeled forecast FACT — next-5-session
realized-vol forecast for NIFTY — plus a rising/falling band read. It NEVER
gates, sizes, or feeds risk/plan.py or scanner/gates.py. The governor is
untouched; only regime_snapshots.vol_forecast (an additive column) and the
DESK regime-strip caption may display it, and only after the walk-forward
QLIKE gate below passes.

Method (HAR-RV, Corsi 2009 — reimplemented from the public formulation, no
code copied): daily realized variance proxy rv_t = squared daily log return
of NIFTY. HAR regresses the h-day-forward average RV on three backward-only
components of the same series:
    rv_1d_t  = rv_t
    rv_5d_t  = mean(rv_{t-4..t})
    rv_22d_t = mean(rv_{t-21..t})
target_t = mean(rv_{t+1..t+5})           (next-5-session realized vol)
Fit in log-space (all terms are variances, strictly positive) via OLS
(numpy lstsq — no sklearn/statsmodels dependency). India VIX level (also in
sector_index_prices, symbol "India VIX", full 2y history) is included as a
4th regressor since the DB has it — LS-periodogram augmentation is
explicitly skipped per WAVE_I_SPEC (thin edge, not worth the complexity).

Baseline: naive-lag — forecast next-5d RV = today's rv_5d_t (last known 5-day
average carried forward). Loss: QLIKE (rv_true/rv_pred - log(rv_true/rv_pred)
- 1), the standard realized-vol forecast loss (penalizes both over- and
under-prediction, scale-free). Walk-forward: expanding window, monthly
refit, exactly the direction_lgbm.py pattern.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

STAGE = "regime_vol_har"
SOURCE = "vol_har"
NIFTY_SYMBOL = "NIFTY 50"
VIX_SYMBOL = "India VIX"
HORIZON_DAYS = 5
MIN_HISTORY_DAYS = 30  # need 22d lookback + a few warmup bars
EPS = 1e-10


# ---------------------------------------------------------------------------
# Raw loaders
# ---------------------------------------------------------------------------

def load_index_series(conn, symbol: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT trade_date, close FROM sector_index_prices WHERE symbol = ? "
        "ORDER BY trade_date ASC",
        conn, params=(symbol,),
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


# ---------------------------------------------------------------------------
# Pure feature/target computation (backward-looking only, see module docstring)
# ---------------------------------------------------------------------------

def build_har_frame(conn) -> pd.DataFrame:
    """One row per NIFTY trading day with HAR-RV features + forward target.
    Every feature at row t uses only rows <= t; target uses rows > t (the
    label, computed deliberately from the future — never used as a
    feature)."""
    nifty = load_index_series(conn, NIFTY_SYMBOL)
    if nifty.empty or len(nifty) < MIN_HISTORY_DAYS:
        return pd.DataFrame(columns=["trade_date", "rv_1d", "rv_5d", "rv_22d", "vix", "target"])

    nifty["ret"] = np.log(nifty["close"] / nifty["close"].shift(1))
    nifty["rv_1d"] = nifty["ret"] ** 2
    nifty["rv_5d"] = nifty["rv_1d"].rolling(5, min_periods=5).mean()
    nifty["rv_22d"] = nifty["rv_1d"].rolling(22, min_periods=22).mean()
    # Forward target: mean RV over the next HORIZON_DAYS sessions (strictly
    # after t) — this is why .shift(-1) before the forward rolling mean.
    nifty["target"] = (
        nifty["rv_1d"].shift(-1).rolling(HORIZON_DAYS, min_periods=HORIZON_DAYS).mean().shift(-(HORIZON_DAYS - 1))
    )

    vix = load_index_series(conn, VIX_SYMBOL).rename(columns={"close": "vix"})
    out = nifty.merge(vix[["trade_date", "vix"]], on="trade_date", how="left")
    out["vix"] = out["vix"].ffill()
    return out[["trade_date", "rv_1d", "rv_5d", "rv_22d", "vix", "target"]]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["rv_1d", "rv_5d", "rv_22d", "target"]).copy()
    d = d[(d["rv_1d"] > 0) & (d["rv_5d"] > 0) & (d["rv_22d"] > 0) & (d["target"] > 0)]
    d["month"] = d["trade_date"].dt.to_period("M").astype(str)
    return d


def _design_matrix(d: pd.DataFrame, has_vix: bool) -> np.ndarray:
    cols = [np.ones(len(d)), np.log(d["rv_1d"]), np.log(d["rv_5d"]), np.log(d["rv_22d"])]
    if has_vix:
        cols.append(d["vix"].fillna(d["vix"].median()))
    return np.column_stack(cols)


def fit_har(d: pd.DataFrame, has_vix: bool) -> np.ndarray:
    """OLS in log-target space. Returns coefficient vector."""
    X = _design_matrix(d, has_vix)
    y = np.log(d["target"].to_numpy())
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def predict_har(d: pd.DataFrame, coef: np.ndarray, has_vix: bool) -> np.ndarray:
    X = _design_matrix(d, has_vix)
    return np.exp(X @ coef)


def qlike(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean QLIKE loss — the standard realized-vol forecast loss."""
    ratio = np.clip(y_true, EPS, None) / np.clip(y_pred, EPS, None)
    return float(np.mean(ratio - np.log(ratio) - 1.0))


# ---------------------------------------------------------------------------
# Walk-forward validation
# ---------------------------------------------------------------------------

@dataclass
class FoldResult:
    test_month: str
    n: int
    qlike_model: float
    qlike_naive: float


def walk_forward_validate(df: pd.DataFrame, min_train_rows: int = 60, has_vix: bool = True):
    d = _clean(df)
    months = sorted(d["month"].unique())
    folds: list[FoldResult] = []
    pooled_true, pooled_pred_model, pooled_pred_naive = [], [], []

    for test_month in months:
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        if len(train) < min_train_rows or test.empty:
            continue
        try:
            coef = fit_har(train, has_vix)
        except Exception:
            continue
        pred_model = predict_har(test, coef, has_vix)
        # Naive-lag baseline: forecast next-5d RV = today's rv_5d (last
        # known 5-day average carried forward unchanged).
        pred_naive = test["rv_5d"].to_numpy()
        y_true = test["target"].to_numpy()

        folds.append(FoldResult(
            test_month=test_month, n=len(test),
            qlike_model=qlike(y_true, pred_model),
            qlike_naive=qlike(y_true, pred_naive),
        ))
        pooled_true.extend(y_true.tolist())
        pooled_pred_model.extend(pred_model.tolist())
        pooled_pred_naive.extend(pred_naive.tolist())

    pooled = {
        "n": len(pooled_true),
        "qlike_model": qlike(np.array(pooled_true), np.array(pooled_pred_model)) if pooled_true else None,
        "qlike_naive": qlike(np.array(pooled_true), np.array(pooled_pred_naive)) if pooled_true else None,
    }
    return folds, pooled


def format_walk_forward_report(folds: list[FoldResult], pooled: dict) -> str:
    lines = ["month       n     QLIKE(model)  QLIKE(naive)"]
    for f in folds:
        lines.append(f"{f.test_month}  {f.n:4d}  {f.qlike_model:11.5f}  {f.qlike_naive:11.5f}")
    if pooled["n"]:
        lines.append(f"POOLED      {pooled['n']:4d}  {pooled['qlike_model']:11.5f}  {pooled['qlike_naive']:11.5f}")
    return "\n".join(lines)


def beats_baseline(pooled: dict) -> bool:
    return bool(
        pooled.get("n") and pooled.get("qlike_model") is not None
        and pooled["qlike_model"] < pooled["qlike_naive"]
    )


# ---------------------------------------------------------------------------
# Nightly stage: display-only, gated on the walk-forward pass above
# ---------------------------------------------------------------------------

def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def band_label(forecast_rv: float, current_rv_5d: float) -> str:
    """rising/falling read for the DESK caption (e.g. 'vol forecast: rising,
    14->17'). Compares annualized-vol-pct(forecast) vs annualized-vol-pct
    (current 5d average) with a small deadband."""
    if forecast_rv <= 0 or current_rv_5d <= 0:
        return "flat"
    fcst_pct = math.sqrt(forecast_rv * 252) * 100
    cur_pct = math.sqrt(current_rv_5d * 252) * 100
    if fcst_pct > cur_pct * 1.05:
        return "rising"
    if fcst_pct < cur_pct * 0.95:
        return "falling"
    return "flat"


def rv_to_vol_pct(rv: float) -> float | None:
    """Realized variance -> annualized volatility, in percent (the number a
    human reads, e.g. 14.2 meaning 14.2%/yr)."""
    if rv is None or rv <= 0:
        return None
    return round(math.sqrt(rv * 252) * 100, 2)


def run(conn, run_date: str) -> dict:
    """Nightly stage: recompute the HAR-RV walk-forward gate on data
    strictly before run_date, and — only if it currently beats the naive
    baseline — write regime_snapshots.vol_forecast + vol_forecast_band for
    run_date. Failure-safe: any error is a `skip`, never a `fail` (this
    stage must never break run-eod; the governor never reads this column)."""
    started = time.monotonic()
    try:
        full = build_har_frame(conn)
        train = full[full["trade_date"] < pd.Timestamp(run_date)]
        d_train = _clean(train)
        if len(d_train) < 60:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "insufficient history for HAR-RV walk-forward")
            conn.commit()
            return {"status": "skip", "detail": "insufficient history"}

        _, pooled = walk_forward_validate(train)
        if not beats_baseline(pooled):
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     f"HAR-RV does not beat naive baseline (QLIKE {pooled.get('qlike_model')} "
                     f"vs {pooled.get('qlike_naive')}) — NOT-FOR-DISPLAY")
            conn.commit()
            return {"status": "skip", "detail": "does not beat baseline", "pooled": pooled}

        today_row = full[full["trade_date"] == pd.Timestamp(run_date)]
        if today_row.empty or today_row[["rv_1d", "rv_5d", "rv_22d"]].isna().any(axis=None):
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     "no NIFTY row / incomplete HAR inputs for run_date")
            conn.commit()
            return {"status": "skip", "detail": "no row for run_date"}

        coef = fit_har(d_train, has_vix=True)
        forecast_rv = float(predict_har(today_row, coef, has_vix=True)[0])
        current_rv_5d = float(today_row["rv_5d"].iloc[0])
        band = band_label(forecast_rv, current_rv_5d)
        vol_forecast_json = json.dumps({
            "rv_forecast_5d": forecast_rv,
            "vol_forecast_pct": rv_to_vol_pct(forecast_rv),
            "current_vol_pct": rv_to_vol_pct(current_rv_5d),
            "band": band,
            "qlike_model": pooled["qlike_model"],
            "qlike_naive": pooled["qlike_naive"],
            "n_train": len(d_train),
        })
        conn.execute(
            "UPDATE regime_snapshots SET vol_forecast = ? WHERE snapshot_date = ?",
            (vol_forecast_json, run_date),
        )
        _log_run(conn, run_date, "ok", 1, time.monotonic() - started,
                 f"vol_forecast written: {band}, {rv_to_vol_pct(current_rv_5d)}->{rv_to_vol_pct(forecast_rv)}")
        conn.commit()
        return {"status": "ok", "detail": "written", "pooled": pooled, "band": band}
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return {"status": "skip", "detail": f"error: {exc}"}
