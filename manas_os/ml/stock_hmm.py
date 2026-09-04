"""Per-stock 3-state HMM regime pane (AlgoPoint "HMM Regime Probability"
style — the user's complaint was that our ML is buried; this module gives
each stock its own P(Bullish)/P(Bearish)/P(Chop) stacked-area read, next to
(not instead of) the market-wide regime_hmm.py confirmation gate).

AD8 (binding): this is a labeled probability FACT computed from that
symbol's OWN daily-bar history. It NEVER gates, sizes, or feeds any
composite/score used by scanner.gates or risk.plan — it is display-only,
always tagged EXPERIMENTAL by the caller. Nothing in this file imports
scanner.gates or risk.plan, and nothing in those modules imports this file.

Features (simple, causal, AlgoPoint-like — deliberately NOT the richer
5-feature market-wide regime_hmm.py feature set, since this fits one
symbol's own (much shorter, noisier) history):
  - log_ret    : log(close_t / close_{t-1})
  - vol_10d    : rolling std of log_ret, trailing 10 sessions (min_periods=10)
  - volume_z20 : rolling z-score of volume, trailing 20 sessions

Fit: standardize features (fold-free — this is a display read, not a
walk-forward-validated model), fit ONE 3-state GaussianHMM with a fixed
random_state (deterministic). Trained on the symbol's ENTIRE available
history (data reality: most symbols only have ~285 sessions total, so
there is no train/test split budget left for a walk-forward harness the
way direction_lgbm.py / regime_hmm.py do it) — this module is a display
read of the symbol's own history, not a forward-tested predictor, and is
labeled EXPERIMENTAL for exactly that reason.

State -> label mapping (deterministic, post-hoc, from the SAME fitted
model's Gaussian means — never from data being displayed): rank the 3
states by mean `log_ret` descending:
    rank 0 (highest mean return) -> BULLISH
    rank 1 (middle)              -> CHOP
    rank 2 (lowest mean return)  -> BEARISH
Ties broken by state index (stable sort) so the mapping is reproducible.

Honesty gate: requires >= MIN_HISTORY_BARS (150) clean feature rows for
the symbol as-of the requested date, else returns {"available": False,
"reason": ...} rather than a low-confidence guess dressed up as a fact.

Caching: fitting a fresh HMM per API request is the latency-expensive
part (measured; see manas_os/tests + LEARNINGS.md note at call site). A
small stock_hmm_cache table (symbol, as_of) memoizes the full JSON
payload so repeat views of the same chart on the same date are instant.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from hmmlearn.hmm import GaussianHMM
except Exception:  # pragma: no cover - exercised via HAS_HMMLEARN=False path
    GaussianHMM = None

HAS_HMMLEARN = GaussianHMM is not None

STAGE = "stock_hmm"
SOURCE = "stock_hmm"

N_STATES = 3
RANDOM_SEED = 42
VOL_WINDOW = 10
VOLZ_WINDOW = 20
MIN_HISTORY_BARS = 150          # honesty gate: below this, "unavailable" not a guess
DISPLAY_BARS = 250              # length of the returned probability series

FEATURE_COLS = ["log_ret", "vol_10d", "volume_z20"]

# Deterministic state->label mapping, rank 0 (highest mean return) .. rank 2
# (lowest) -> BULLISH / CHOP / BEARISH.
LABELS_BY_RANK = ["BULLISH", "CHOP", "BEARISH"]

# RENDER RULE: confidence tier from max-state-probability thresholds.
CONFIDENCE_HIGH = 0.7
CONFIDENCE_MED = 0.5


# ---------------------------------------------------------------------------
# Raw loader + causal feature computation
# ---------------------------------------------------------------------------

def load_bars(conn, symbol: str) -> pd.DataFrame:
    """Full-history EQ-series close/volume for one symbol, ascending."""
    df = pd.read_sql_query(
        "SELECT trade_date, close, volume FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' ORDER BY trade_date ASC",
        conn, params=(symbol,),
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Causal (backward-looking only) feature frame aligned to df's index."""
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    log_ret = np.log(close / close.shift(1))
    vol_10d = log_ret.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()
    v_mean = volume.rolling(VOLZ_WINDOW, min_periods=VOLZ_WINDOW).mean()
    v_std = volume.rolling(VOLZ_WINDOW, min_periods=VOLZ_WINDOW).std()
    volume_z20 = (volume - v_mean) / v_std.replace(0, np.nan)

    out = pd.DataFrame({
        "trade_date": df["trade_date"],
        "close": close,
        "log_ret": log_ret,
        "vol_10d": vol_10d,
        "volume_z20": volume_z20,
    })
    return out


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(subset=FEATURE_COLS).reset_index(drop=True)


@dataclass
class Scaler:
    mean: np.ndarray
    std: np.ndarray

    def transform(self, X: np.ndarray) -> np.ndarray:
        std = np.where(self.std == 0, 1.0, self.std)
        return (X - self.mean) / std


def fit_scaler(df: pd.DataFrame) -> Scaler:
    X = df[FEATURE_COLS].to_numpy(dtype=float)
    return Scaler(mean=X.mean(axis=0), std=X.std(axis=0))


def fit_hmm(X: np.ndarray, random_state: int = RANDOM_SEED):
    if not HAS_HMMLEARN:
        raise RuntimeError("hmmlearn not installed")
    model = GaussianHMM(
        n_components=N_STATES, covariance_type="diag",
        n_iter=200, random_state=random_state, init_params="stmc",
    )
    model.fit(X)
    return model


def state_label_map(model, feature_idx_ret: int = 0) -> dict[int, str]:
    """Deterministic: rank states by mean `log_ret` (Gaussian mean along the
    log_ret feature dimension) descending, ties broken by state index."""
    means = model.means_
    scores = {s: float(means[s, feature_idx_ret]) for s in range(means.shape[0])}
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return {state: LABELS_BY_RANK[rank] for rank, (state, _score) in enumerate(ordered)}


def _confidence_tier(max_p: float) -> str:
    if max_p >= CONFIDENCE_HIGH:
        return "HIGH"
    if max_p >= CONFIDENCE_MED:
        return "MED"
    return "LOW"


# ---------------------------------------------------------------------------
# Compute (no caching) — one symbol, as-of a date
# ---------------------------------------------------------------------------

def compute(conn, symbol: str, as_of_date: str) -> dict:
    """Fit a fresh 3-state GaussianHMM on `symbol`'s own history strictly
    <= as_of_date, and return the display payload. Honest 'unavailable' if
    there isn't enough clean history yet (never a fabricated read)."""
    bars = load_bars(conn, symbol)
    bars = bars[bars["trade_date"] <= pd.Timestamp(as_of_date)]
    feats = _clean(build_features(bars))
    n = len(feats)
    if n < MIN_HISTORY_BARS:
        return {
            "available": False,
            "symbol": symbol,
            "reason": f"insufficient history ({n} clean bars, need >= {MIN_HISTORY_BARS})",
        }
    if not HAS_HMMLEARN:
        return {"available": False, "symbol": symbol, "reason": "hmmlearn not installed"}

    scaler = fit_scaler(feats)
    X = scaler.transform(feats[FEATURE_COLS].to_numpy(dtype=float))
    try:
        model = fit_hmm(X)
    except Exception as exc:  # noqa: BLE001 - display layer must degrade, not 500
        return {"available": False, "symbol": symbol, "reason": f"fit failed: {exc}"}

    label_map = state_label_map(model)
    proba = model.predict_proba(X)  # (n, 3) columns are hmmlearn's internal state indices
    states = model.predict(X)

    # Map hmmlearn's internal state index -> BULLISH/CHOP/BEARISH column, so
    # the returned p_bull/p_chop/p_bear triple is always in that fixed order
    # regardless of which raw state index the fit happened to assign to it.
    label_to_state = {v: k for k, v in label_map.items()}
    col_bull = label_to_state["BULLISH"]
    col_chop = label_to_state["CHOP"]
    col_bear = label_to_state["BEARISH"]

    tail = feats.tail(DISPLAY_BARS).reset_index(drop=True)
    tail_proba = proba[-len(tail):]
    series = [
        {
            "time": row["trade_date"].strftime("%Y-%m-%d"),
            "p_bull": round(float(tail_proba[i, col_bull]), 4),
            "p_bear": round(float(tail_proba[i, col_bear]), 4),
            "p_chop": round(float(tail_proba[i, col_chop]), 4),
        }
        for i, row in tail.iterrows()
    ]

    last_p = proba[-1]
    last_state = int(states[-1])
    last_label = label_map[last_state]
    max_p = float(last_p[last_state])

    return {
        "available": True,
        "symbol": symbol,
        "as_of": feats.iloc[-1]["trade_date"].strftime("%Y-%m-%d"),
        "n_bars": n,
        "series": series,
        "current": {
            "state": last_label,
            "confidence": _confidence_tier(max_p),
            "p_bull": round(float(last_p[col_bull]), 4),
            "p_bear": round(float(last_p[col_bear]), 4),
            "p_chop": round(float(last_p[col_chop]), 4),
        },
    }


# ---------------------------------------------------------------------------
# Cache: stock_hmm_cache(symbol, as_of) -> payload_json
# ---------------------------------------------------------------------------

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS stock_hmm_cache ("
        "symbol TEXT NOT NULL, as_of TEXT NOT NULL, "
        "payload_json TEXT NOT NULL, "
        "computed_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (symbol, as_of))"
    )


def get_cached(conn, symbol: str, as_of_date: str) -> dict | None:
    """Cache-only read — never fits an HMM. Used by endpoints (e.g. the
    debate list) that must stay fast for many symbols at once; the chart
    drawer's own request is what actually populates the cache via
    get_or_compute() below."""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT payload_json FROM stock_hmm_cache WHERE symbol = ? AND as_of = ?",
        (symbol, as_of_date),
    ).fetchone()
    if row is None or not row["payload_json"]:
        return None
    try:
        return json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None


def get_or_compute(conn, symbol: str, as_of_date: str) -> dict:
    """Cache-through: one GaussianHMM fit per (symbol, as_of) pair, ever
    (until the cache row is cleared) — the fit doesn't change once the
    input history through as_of_date is fixed."""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT payload_json FROM stock_hmm_cache WHERE symbol = ? AND as_of = ?",
        (symbol, as_of_date),
    ).fetchone()
    if row is not None and row["payload_json"]:
        try:
            return json.loads(row["payload_json"])
        except json.JSONDecodeError:
            pass  # fall through and recompute a fresh (valid) payload

    payload = compute(conn, symbol, as_of_date)
    conn.execute(
        "INSERT INTO stock_hmm_cache (symbol, as_of, payload_json) VALUES (?, ?, ?) "
        "ON CONFLICT(symbol, as_of) DO UPDATE SET payload_json = excluded.payload_json, "
        "computed_at = datetime('now')",
        (symbol, as_of_date, json.dumps(payload)),
    )
    conn.commit()
    return payload


def summary_line(payload: dict) -> str | None:
    """Fact-only one-liner for the debate context_pack, e.g.
    'stock HMM: BULLISH 48% (low conf)'. None if unavailable."""
    if not payload or not payload.get("available"):
        return None
    current = payload.get("current") or {}
    state = current.get("state")
    if not state:
        return None
    p_key = {"BULLISH": "p_bull", "BEARISH": "p_bear", "CHOP": "p_chop"}.get(state)
    pct = current.get(p_key)
    pct_str = f"{round(pct * 100)}%" if pct is not None else "n/a"
    conf = (current.get("confidence") or "").lower()
    conf_str = {"low": "low conf", "med": "med conf", "high": "high conf"}.get(conf, conf)
    return f"stock HMM: {state} {pct_str} ({conf_str})" if conf_str else f"stock HMM: {state} {pct_str}"


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )
