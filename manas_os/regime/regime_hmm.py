"""SHIP-1 #17 (I5) — HMM regime confirmation gate [shreyasfegade/regime feature
set + CC-Shivansh-Gupta fitting discipline; reimplemented, adopt-not-import].

AD8 (binding): this module produces a labeled state FACT — a 4-state
GaussianHMM read of NIFTY 50 — that CONFIRMS (never replaces) the existing
XP/MBI market_mode. Nothing in this file feeds scanner/gates.py, risk/plan.py,
or the debate/gate machinery; the governor stays untouched. The gate below is
even stricter than "experimental/display-only" (I1/I14 pattern): the label is
persisted every night but the RENDER RULE (locked, per WAVE_I_SPEC I5 task)
keeps it invisible everywhere until `display_gate()` reports
`display_allowed=True` (>= DISPLAY_GATE_N live nightly computations). Until
then the only string a caller may show is the "warming up (n/N)" caption from
`caption()` below — XP/MBI remains the SOLE authority throughout.

Trigger (per WAVE_I_SPEC I5): build only once regime_snapshots has >= 150
sessions of live-computed XP/MBI. That bar was cleared 2026-07-10 (285
causally-backfilled sessions, causality assertion green in
tests/test_backfill.py) — see WORK_ORDER_SHIP1.md item 17.

Data reality (2026-07-10): sector_index_prices "NIFTY 50" has 497 rows back to
2024-07-08, but breadth_daily / regime_snapshots only start 2025-03-19 (285
rows) — the feature frame below is joined against breadth, so it is bounded to
that 285-session window, not the longer NIFTY history.

Features (all causal — computed only from rows <= t; see
test_regime_hmm.py::test_feature_causality_truncated_history):
  - log_ret     : log(close_t / close_{t-1})
  - vol_5d      : rolling std of log_ret, trailing 5 sessions (min_periods=5)
  - vol_20d     : rolling std of log_ret, trailing 20 sessions (min_periods=20)
  - breadth_z   : rolling z-score (20d window) of net breadth (advances -
                  declines) from breadth_daily. NIFTY 50 in sector_index_prices
                  carries no volume column (close + sma50 only), so the spec's
                  "volume z" is substituted with a breadth up/down-count z —
                  documented substitution, not a silent approximation.
  - mom_10d     : close_t / close_{t-10} - 1

State->label mapping (deterministic, documented, post-hoc from TRAIN-fold
state stats only — never from the label being predicted):
  Rank the fitted HMM's 4 states by `mean_return - 0.5 * mean_vol_20d` (a
  crude risk-adjusted-return score, computed from each state's Gaussian mean
  along the log_ret/vol_20d feature dimensions on the TRAIN fold only)
  descending, then map rank 0..3 onto the SAME four-way vocabulary
  regime_snapshots.market_mode already uses:
      rank 0 (best risk-adj return)  -> RISK_ON
      rank 1                         -> SELECTIVE
      rank 2                         -> DEFENSIVE
      rank 3 (worst risk-adj return) -> NO_TRADE
  Using market_mode's own vocabulary makes the agreement/contingency-table
  validation an apples-to-apples comparison instead of inventing a second
  label taxonomy that would need its own translation layer.

Walk-forward (same discipline as regime/vol_har.py and ml/direction_lgbm.py):
  expanding window, monthly refit. Each fold: fit a StandardScaler on the
  TRAIN rows ONLY (fold-scoped scaling — the scaler never sees test-fold
  values), fit a 4-state GaussianHMM with N_RESTARTS random restarts (keep the
  restart with the highest training log-likelihood), decode TRAIN states via
  Viterbi to build the state->label map for that fold, then decode the TEST
  rows with the frozen (fold-scoped) scaler + fitted HMM and apply that same
  fold's state->label map.

Validation logged honestly to LEARNINGS.md (see run() docstring + the CLI
entry point that dumps the report): (a) walk-forward state flip rate, (b)
contingency table vs the stored XP/MBI market_mode, (c) regime-conditional
forward-5d NIFTY return per HMM label (does the state carry information?).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

try:
    from hmmlearn.hmm import GaussianHMM
except Exception:  # pragma: no cover - exercised via HAS_HMMLEARN=False path
    GaussianHMM = None

HAS_HMMLEARN = GaussianHMM is not None

STAGE = "regime_hmm"
SOURCE = "regime_hmm"
NIFTY_SYMBOL = "NIFTY 50"

N_STATES = 4
N_RESTARTS = 10
VOL_SHORT = 5
VOL_LONG = 20
BREADTH_Z_WINDOW = 20
MOMENTUM_DAYS = 10

MIN_HISTORY_SESSIONS = 150   # I5 trigger gate: regime_snapshots must have >= this many sessions
MIN_TRAIN_ROWS = 90          # walk-forward: smallest train fold we'll fit an HMM on
DISPLAY_GATE_N = 20          # RENDER RULE: n live nightly computations required before display

FEATURE_COLS = ["log_ret", "vol_5d", "vol_20d", "breadth_z", "mom_10d"]

# Deterministic state->label mapping, rank 0 (best risk-adj return) .. rank 3
# (worst) -> the SAME vocabulary regime_snapshots.market_mode uses.
LABELS_BY_RANK = ["RISK_ON", "SELECTIVE", "DEFENSIVE", "NO_TRADE"]


# ---------------------------------------------------------------------------
# Raw loaders
# ---------------------------------------------------------------------------

def load_nifty(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT trade_date, close FROM sector_index_prices WHERE symbol = ? "
        "ORDER BY trade_date ASC",
        conn, params=(NIFTY_SYMBOL,),
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_breadth(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT trade_date, advances, declines FROM breadth_daily ORDER BY trade_date ASC",
        conn,
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_market_mode(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT snapshot_date AS trade_date, market_mode FROM regime_snapshots ORDER BY snapshot_date ASC",
        conn,
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


# ---------------------------------------------------------------------------
# Pure, causal feature computation
# ---------------------------------------------------------------------------

def build_feature_frame(conn) -> pd.DataFrame:
    """One row per session with the 5 causal features (+ raw `close` kept for
    validation-only forward-return computation, never fed to the HMM).

    Every feature at row t is computed strictly from rows <= t (rolling
    windows with min_periods == window, plus a lag-based momentum term) —
    truncating the input DataFrame to any prefix and recomputing yields the
    identical value for every row still present (see
    test_regime_hmm.py::test_feature_causality_truncated_history)."""
    nifty = load_nifty(conn)
    breadth = load_breadth(conn)
    if nifty.empty or breadth.empty:
        return pd.DataFrame(columns=["trade_date", "close", *FEATURE_COLS])

    df = nifty.merge(breadth, on="trade_date", how="inner").sort_values("trade_date").reset_index(drop=True)
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    df["vol_5d"] = df["log_ret"].rolling(VOL_SHORT, min_periods=VOL_SHORT).std()
    df["vol_20d"] = df["log_ret"].rolling(VOL_LONG, min_periods=VOL_LONG).std()
    df["net_breadth"] = df["advances"] - df["declines"]
    roll_mean = df["net_breadth"].rolling(BREADTH_Z_WINDOW, min_periods=BREADTH_Z_WINDOW).mean()
    roll_std = df["net_breadth"].rolling(BREADTH_Z_WINDOW, min_periods=BREADTH_Z_WINDOW).std()
    df["breadth_z"] = (df["net_breadth"] - roll_mean) / roll_std.replace(0, np.nan)
    df["mom_10d"] = df["close"] / df["close"].shift(MOMENTUM_DAYS) - 1.0

    return df[["trade_date", "close", *FEATURE_COLS]]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=FEATURE_COLS).copy()
    d["month"] = d["trade_date"].dt.to_period("M").astype(str)
    return d.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Fold-scoped scaling + HMM fit
# ---------------------------------------------------------------------------

@dataclass
class FoldScaler:
    mean: np.ndarray
    std: np.ndarray

    def transform(self, X: np.ndarray) -> np.ndarray:
        std = np.where(self.std == 0, 1.0, self.std)
        return (X - self.mean) / std


def fit_scaler(train_df: pd.DataFrame) -> FoldScaler:
    """Fit ONLY on the train fold — never on test-fold rows (fold-scoped
    scaling, per WAVE_I_SPEC I5)."""
    X = train_df[FEATURE_COLS].to_numpy(dtype=float)
    return FoldScaler(mean=X.mean(axis=0), std=X.std(axis=0))


def fit_hmm_best_of_restarts(X: np.ndarray, n_states: int = N_STATES,
                              n_restarts: int = N_RESTARTS):
    """Fit a GaussianHMM `n_restarts` times with different random seeds and
    keep the restart with the highest training log-likelihood (score)."""
    if not HAS_HMMLEARN:
        raise RuntimeError("hmmlearn not installed")
    best_model = None
    best_score = -np.inf
    for seed in range(n_restarts):
        model = GaussianHMM(
            n_components=n_states, covariance_type="diag",
            n_iter=200, random_state=seed, init_params="stmc",
        )
        try:
            model.fit(X)
            score = model.score(X)
        except Exception:
            continue
        if score > best_score:
            best_score = score
            best_model = model
    if best_model is None:
        raise RuntimeError("all HMM restarts failed to fit")
    return best_model, float(best_score)


def state_risk_adjusted_scores(model, feature_idx_ret: int = 0, feature_idx_vol20: int = 2) -> dict[int, float]:
    """Per-state `mean_return - 0.5*mean_vol_20d` from the fitted Gaussian
    means (in SCALED feature space — fine since this is only used to RANK
    the states relative to each other, not to report a real number)."""
    means = model.means_  # shape (n_states, n_features)
    scores: dict[int, float] = {}
    for s in range(means.shape[0]):
        scores[s] = float(means[s, feature_idx_ret] - 0.5 * means[s, feature_idx_vol20])
    return scores


def map_states_to_labels(scores: dict[int, float]) -> dict[int, str]:
    """Deterministic: rank states by `scores` descending, then assign
    LABELS_BY_RANK[rank]. Ties broken by state index (stable sort) so the
    mapping is reproducible given the same scores regardless of dict
    insertion order (see
    test_regime_hmm.py::test_state_label_mapping_is_deterministic)."""
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return {state: LABELS_BY_RANK[rank] for rank, (state, _score) in enumerate(ordered)}


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardResult:
    rows: pd.DataFrame  # trade_date, close, state, label, p_state
    flip_rate: float
    n_folds: int


def walk_forward_hmm(df: pd.DataFrame, min_train_rows: int = MIN_TRAIN_ROWS,
                      n_restarts: int = N_RESTARTS) -> WalkForwardResult:
    d = _clean(df)
    months = sorted(d["month"].unique())
    out_rows = []
    n_folds = 0

    for test_month in months:
        train = d[d["month"] < test_month]
        test = d[d["month"] == test_month]
        if len(train) < min_train_rows or test.empty:
            continue
        scaler = fit_scaler(train)
        X_train = scaler.transform(train[FEATURE_COLS].to_numpy(dtype=float))
        try:
            model, _ll = fit_hmm_best_of_restarts(X_train, n_restarts=n_restarts)
        except Exception:
            continue
        train_states = model.predict(X_train)
        train_scored = train.assign(state=train_states)
        scores = {}
        for s in range(N_STATES):
            mask = train_scored["state"] == s
            if mask.sum() == 0:
                scores[s] = -np.inf
                continue
            scores[s] = float(
                train_scored.loc[mask, "log_ret"].mean() - 0.5 * train_scored.loc[mask, "vol_20d"].mean()
            )
        label_map = map_states_to_labels(scores)

        X_test = scaler.transform(test[FEATURE_COLS].to_numpy(dtype=float))
        test_states = model.predict(X_test)
        test_proba = model.predict_proba(X_test)
        p_state = test_proba[np.arange(len(test_states)), test_states]

        fold_out = test[["trade_date", "close"]].copy()
        fold_out["state"] = test_states
        fold_out["label"] = [label_map[s] for s in test_states]
        fold_out["p_state"] = p_state
        out_rows.append(fold_out)
        n_folds += 1

    if not out_rows:
        return WalkForwardResult(rows=pd.DataFrame(columns=["trade_date", "close", "state", "label", "p_state"]),
                                  flip_rate=float("nan"), n_folds=0)

    rows = pd.concat(out_rows, ignore_index=True).sort_values("trade_date").reset_index(drop=True)
    flips = (rows["label"] != rows["label"].shift(1)).iloc[1:]
    rate = float(flips.mean()) if len(flips) else float("nan")
    return WalkForwardResult(rows=rows, flip_rate=rate, n_folds=n_folds)


# ---------------------------------------------------------------------------
# Validation (b): contingency table vs XP/MBI market_mode
# ---------------------------------------------------------------------------

def contingency_table(rows: pd.DataFrame, market_mode_df: pd.DataFrame) -> dict:
    joined = rows.merge(market_mode_df, on="trade_date", how="inner")
    if joined.empty:
        return {"n": 0, "table": {}, "agreement_rate": None}
    table = pd.crosstab(joined["label"], joined["market_mode"]).to_dict()
    # normalize to plain nested dict[label][market_mode] = count
    nested: dict[str, dict[str, int]] = {}
    for mm_col, per_label in table.items():
        for label, count in per_label.items():
            nested.setdefault(label, {})[mm_col] = int(count)
    agree = int((joined["label"] == joined["market_mode"]).sum())
    return {"n": len(joined), "table": nested, "agreement_rate": round(agree / len(joined), 4)}


# ---------------------------------------------------------------------------
# Validation (c): regime-conditional forward 5d NIFTY return per state
# ---------------------------------------------------------------------------

def regime_conditional_forward_returns(rows: pd.DataFrame, full_close: pd.DataFrame, horizon: int = 5) -> dict:
    """`full_close` = the FULL (not walk-forward-truncated) trade_date/close
    frame so the forward window can look past the last labeled row; this is
    validation-only (never fed back into the HMM as a feature)."""
    closes = full_close.set_index("trade_date")["close"].sort_index()
    fwd = closes.shift(-horizon) / closes - 1.0
    fwd_df = fwd.rename("fwd_ret").reset_index()
    joined = rows.merge(fwd_df, on="trade_date", how="left").dropna(subset=["fwd_ret"])
    out: dict[str, dict] = {}
    for label, g in joined.groupby("label"):
        out[label] = {
            "n": int(len(g)),
            "mean_fwd_5d_pct": round(float(g["fwd_ret"].mean() * 100), 3),
            "median_fwd_5d_pct": round(float(g["fwd_ret"].median() * 100), 3),
        }
    return out


def format_validation_report(wf: WalkForwardResult, contingency: dict, conditional: dict) -> str:
    lines = [
        f"walk-forward folds: {wf.n_folds}, rows: {len(wf.rows)}, flip_rate: {wf.flip_rate:.4f}"
        if wf.n_folds else "walk-forward folds: 0 (insufficient history)",
        f"contingency n={contingency['n']}, agreement_rate={contingency['agreement_rate']}",
    ]
    for label, per_mm in contingency.get("table", {}).items():
        lines.append(f"  {label}: {per_mm}")
    lines.append("regime-conditional forward 5d NIFTY return:")
    for label, stats in conditional.items():
        lines.append(f"  {label}: n={stats['n']} mean={stats['mean_fwd_5d_pct']}% median={stats['median_fwd_5d_pct']}%")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS hmm_regime ("
        "session_date TEXT PRIMARY KEY, "
        "state INTEGER, "
        "label TEXT, "
        "p_state REAL, "
        "source TEXT DEFAULT 'live', "
        "ingested_at TEXT DEFAULT (datetime('now'))"
        ")"
    )


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def persist_row(conn, session_date: str, state: int, label: str, p_state: float, source: str = "live") -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO hmm_regime (session_date, state, label, p_state, source) VALUES (?,?,?,?,?) "
        "ON CONFLICT(session_date) DO UPDATE SET state=excluded.state, label=excluded.label, "
        "p_state=excluded.p_state, source=excluded.source",
        (session_date, int(state), label, float(p_state), source),
    )


# ---------------------------------------------------------------------------
# RENDER RULE (locked): display gate + caption
# ---------------------------------------------------------------------------

def display_gate(conn, asof_date: str | None = None, n_required: int = DISPLAY_GATE_N) -> dict:
    """20-session live-agreement gate. Counts `source='live'` hmm_regime rows
    (i.e. rows written by the nightly `regime_hmm` stage, never a bulk
    backfill/validation run) on/before `asof_date`. display_allowed only flips
    True once that count reaches `n_required` — this is a WARMUP gate (enough
    live nights have actually run), not a statistical accuracy bar; the
    contingency-table agreement_rate above is the separate, honestly-logged
    accuracy read in LEARNINGS.md. XP/MBI remains authoritative regardless."""
    ensure_schema(conn)
    if asof_date is None:
        row = conn.execute("SELECT COUNT(*) AS n FROM hmm_regime WHERE source = 'live'").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM hmm_regime WHERE source = 'live' AND session_date <= ?",
            (asof_date,),
        ).fetchone()
    n = int(row["n"]) if row and row["n"] is not None else 0
    return {"display_allowed": n >= n_required, "sessions_counted": n}


def caption(gate: dict, hmm_label: str | None, market_mode: str | None, n_required: int = DISPLAY_GATE_N) -> str:
    """The ONLY string a caller may render for the HMM confirmation line."""
    if not gate.get("display_allowed"):
        return f"HMM confirm: warming up ({gate.get('sessions_counted', 0)}/{n_required})"
    if hmm_label is None:
        return "HMM confirm: unavailable"
    if market_mode and hmm_label == market_mode:
        return f"HMM: confirms {market_mode}"
    return f"HMM: disagrees (says {hmm_label})"


def get_display_caption(conn, session_date: str) -> dict:
    """Convenience wrapper the desk endpoint calls: returns
    {display_allowed, sessions_counted, caption, hmm_label}."""
    gate = display_gate(conn, session_date)
    row = conn.execute(
        "SELECT state, label, p_state FROM hmm_regime WHERE session_date <= ? "
        "ORDER BY session_date DESC LIMIT 1",
        (session_date,),
    ).fetchone()
    hmm_label = row["label"] if row else None
    mm_row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (session_date,),
    ).fetchone()
    market_mode = mm_row["market_mode"] if mm_row else None
    return {
        "display_allowed": gate["display_allowed"],
        "sessions_counted": gate["sessions_counted"],
        "caption": caption(gate, hmm_label, market_mode),
        "hmm_label": hmm_label if gate["display_allowed"] else None,
    }


# ---------------------------------------------------------------------------
# Nightly stage: failure-safe, skips gracefully without hmmlearn or history
# ---------------------------------------------------------------------------

def run(conn, run_date: str) -> dict:
    """Refit on the expanding window up to (and including) run_date, decode
    run_date's state/label, and persist ONE hmm_regime row (source='live').
    Failure-safe: any error (missing dep, insufficient history, fit failure)
    is a `skip`, never a `fail` — this stage must never break run-eod, and
    the label is stored but display-gated regardless (see display_gate())."""
    started = time.monotonic()
    ensure_schema(conn)
    if not HAS_HMMLEARN:
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 "hmmlearn not installed")
        conn.commit()
        return {"status": "skip", "detail": "hmmlearn not installed"}
    try:
        n_sessions = conn.execute("SELECT COUNT(*) AS n FROM regime_snapshots").fetchone()["n"]
        if n_sessions < MIN_HISTORY_SESSIONS:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     f"regime_snapshots has {n_sessions} sessions, need >= {MIN_HISTORY_SESSIONS}")
            conn.commit()
            return {"status": "skip", "detail": "insufficient regime_snapshots history"}

        full = build_feature_frame(conn)
        d = _clean(full[full["trade_date"] <= pd.Timestamp(run_date)])
        if len(d) < MIN_TRAIN_ROWS + 1:
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     f"only {len(d)} clean feature rows up to {run_date}, need >= {MIN_TRAIN_ROWS + 1}")
            conn.commit()
            return {"status": "skip", "detail": "insufficient feature history"}

        train = d.iloc[:-1]
        today_row = d.iloc[[-1]]
        if today_row["trade_date"].iloc[0] != pd.Timestamp(run_date):
            _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                     f"no clean feature row for run_date {run_date} (NIFTY/breadth not caught up)")
            conn.commit()
            return {"status": "skip", "detail": "no feature row for run_date"}

        scaler = fit_scaler(train)
        X_train = scaler.transform(train[FEATURE_COLS].to_numpy(dtype=float))
        model, _ll = fit_hmm_best_of_restarts(X_train, n_restarts=N_RESTARTS)
        train_states = model.predict(X_train)
        train_scored = train.assign(state=train_states)
        scores = {}
        for s in range(N_STATES):
            mask = train_scored["state"] == s
            if mask.sum() == 0:
                scores[s] = -np.inf
                continue
            scores[s] = float(
                train_scored.loc[mask, "log_ret"].mean() - 0.5 * train_scored.loc[mask, "vol_20d"].mean()
            )
        label_map = map_states_to_labels(scores)

        X_today = scaler.transform(today_row[FEATURE_COLS].to_numpy(dtype=float))
        state_today = int(model.predict(X_today)[0])
        p_today = float(model.predict_proba(X_today)[0][state_today])
        label_today = label_map[state_today]

        persist_row(conn, run_date, state_today, label_today, p_today, source="live")
        _log_run(conn, run_date, "ok", 1, time.monotonic() - started,
                 f"hmm_regime written: state={state_today} label={label_today} p={p_today:.3f} "
                 "(display-gated per RENDER RULE, XP/MBI remains sole authority)")
        conn.commit()
        return {"status": "ok", "detail": "written", "state": state_today, "label": label_today, "p_state": p_today}
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return {"status": "skip", "detail": f"error: {exc}"}
