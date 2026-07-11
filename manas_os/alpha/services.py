"""Read services for Alpha Lab and debate evidence cards.

Headlines centre regime quality, opportunity rank and observable behaviour.
Calibrated path probabilities are supporting evidence only.
"""
from __future__ import annotations

import json

from manas_os.agents import chart_behavior

from .diagnostics import bayesian_setup_expectancy, competing_risk_summary
from .memory import recall_analogues
from .schema import ensure_schema


BEHAVIOUR_KEYS = (
    "ema_relationships", "ema_slopes", "rs", "adr", "volume_dry_up",
    "volume_expansion", "base_age", "base_depth", "base_tightness",
    "gap_retention", "pocket_pivots", "stage", "base_archetype", "contradictions",
)


def _latest_date(conn) -> str | None:
    row = conn.execute("SELECT MAX(as_of_date) d FROM alpha_feature_snapshots").fetchone()
    return row["d"] if row else None


def overview(conn) -> dict:
    ensure_schema(conn)
    as_of = _latest_date(conn)
    models = conn.execute("SELECT COUNT(*) n,COALESCE(SUM(live_shadow_sessions),0) sessions FROM alpha_model_registry").fetchone()
    if not as_of:
        return {"state": "warming", "headline": "Alpha evidence is waiting for its first point-in-time feature build.",
                "as_of": None, "shadow_only": True, "models": 0, "live_shadow_sessions": 0}
    denominator = conn.execute("SELECT MAX(source_denominator) n FROM alpha_feature_snapshots WHERE as_of_date=?", (as_of,)).fetchone()["n"]
    return {"state": "ready", "headline": "Opportunity ranks compare current leadership; they are evidence, not trade instructions.",
            "as_of": as_of, "source_denominator": denominator, "shadow_only": True,
            "models": models["n"], "live_shadow_sessions": models["sessions"],
            "setup_expectancy": bayesian_setup_expectancy(conn),
            "competing_risks": competing_risk_summary(conn)}


def leaders(conn, *, as_of: str | None = None, limit: int = 20) -> dict:
    ensure_schema(conn); as_of = as_of or _latest_date(conn)
    if not as_of:
        return {"state": "warming", "as_of": None, "rows": [], "shadow_only": True}
    rows = conn.execute("""SELECT symbol,sector,momentum_percentile,momentum_zscore,
      market_residual_20,sector_residual_20,source_denominator,source_max_date
      FROM alpha_feature_snapshots WHERE as_of_date=?
      ORDER BY momentum_percentile DESC,symbol LIMIT ?""", (as_of, limit)).fetchall()
    return {"state": "ready" if rows else "warming", "as_of": as_of, "shadow_only": True,
            "ranking_basis": "20-session cross-sectional momentum with market and sector context",
            "rows": [dict(r) for r in rows]}


def symbol(conn, symbol_name: str, *, as_of: str | None = None) -> dict:
    ensure_schema(conn); as_of = as_of or _latest_date(conn); symbol_name = symbol_name.upper()
    if not as_of:
        return {"state": "warming", "symbol": symbol_name, "as_of": None, "shadow_only": True}
    row = conn.execute("SELECT * FROM alpha_feature_snapshots WHERE symbol=? AND as_of_date<=? ORDER BY as_of_date DESC LIMIT 1",
                       (symbol_name, as_of)).fetchone()
    if not row:
        return {"state": "empty", "symbol": symbol_name, "as_of": as_of, "shadow_only": True,
                "explanation": "No causal feature snapshot exists for this symbol yet."}
    features = json.loads(row["features_json"])
    behaviour = {key: features.get(key) for key in BEHAVIOUR_KEYS}
    available_cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_prices)")}
    bar_cols = [name for name in ("trade_date", "open", "high", "low", "close", "volume") if name in available_cols]
    bars = [dict(r) for r in conn.execute(
        f"SELECT {','.join(bar_cols)} FROM daily_prices "
        "WHERE symbol=? AND series='EQ' AND trade_date<=? ORDER BY trade_date DESC LIMIT 420",
        (symbol_name, row["as_of_date"]),
    ).fetchall()] if {"trade_date", "close"} <= available_cols else []
    observed_chart = chart_behavior.build(list(reversed(bars)))
    predictions = [dict(r) for r in conn.execute("""SELECT model_id,model_version,calibration_state,
      probability_1r_first,probability_2r_10d,expected_mfe_r,expected_mae_r,expected_holding_sessions,
      source_freshness,status FROM alpha_predictions WHERE symbol=? AND as_of_time<=?
      ORDER BY as_of_time DESC LIMIT 5""", (symbol_name, as_of + "T23:59:59")).fetchall()]
    return {"state": "ready", "symbol": symbol_name, "as_of": row["as_of_date"], "shadow_only": True,
            "opportunity_rank": row["momentum_percentile"], "regime_quality": features.get("regime_quality"),
            "setup_behaviour": behaviour, "chart_behavior": observed_chart,
            "uncertainty": {"calibrated_models": len(predictions),
            "note": "Path probabilities support the behavioural read; they are not the headline or a sizing input."},
            "features": features, "supporting_path_evidence": predictions,
            "analogues": recall_analogues(conn, as_of=as_of + "T23:59:59", symbol=symbol_name, limit=3)}


def models(conn) -> dict:
    ensure_schema(conn); rows = [dict(r) for r in conn.execute("SELECT * FROM alpha_model_registry ORDER BY model_id,model_version")]
    return {"state": "ready" if rows else "warming", "shadow_only": True, "rows": rows}


def experiments(conn, experiment_id: str | None = None) -> dict:
    ensure_schema(conn)
    if experiment_id:
        row = conn.execute("SELECT * FROM alpha_experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        return {"state": "ready" if row else "empty", "shadow_only": True, "experiment": dict(row) if row else None}
    rows = [dict(r) for r in conn.execute("SELECT * FROM alpha_experiments ORDER BY created_at DESC")]
    return {"state": "ready" if rows else "warming", "shadow_only": True, "rows": rows}


def memory(conn, symbol_name: str, *, as_of: str, limit: int = 3) -> dict:
    rows = recall_analogues(conn, as_of=as_of, symbol=symbol_name, limit=limit)
    return {"state": "ready" if rows else "warming", "symbol": symbol_name.upper(),
            "as_of": as_of, "shadow_only": True, "rows": rows}
