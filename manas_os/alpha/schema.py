"""Canonical, additive SQLite schema for the alpha research fabric."""
from __future__ import annotations

import threading


DDL = """
CREATE TABLE IF NOT EXISTS alpha_feature_snapshots (
  as_of_date TEXT NOT NULL, symbol TEXT NOT NULL, feature_version TEXT NOT NULL,
  sector TEXT, universe TEXT NOT NULL, source_max_date TEXT NOT NULL,
  source_denominator INTEGER NOT NULL, freshness_sessions INTEGER NOT NULL DEFAULT 0,
  ret_5 REAL, ret_10 REAL, ret_20 REAL, ret_60 REAL,
  market_residual_5 REAL, market_residual_10 REAL,
  market_residual_20 REAL, market_residual_60 REAL,
  sector_residual_5 REAL, sector_residual_10 REAL,
  sector_residual_20 REAL, sector_residual_60 REAL,
  momentum_zscore REAL, momentum_percentile REAL,
  features_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(as_of_date, symbol, feature_version),
  CHECK(source_max_date <= as_of_date), CHECK(source_denominator >= 0)
);
CREATE INDEX IF NOT EXISTS idx_alpha_features_rank
  ON alpha_feature_snapshots(as_of_date, feature_version, momentum_percentile DESC);

CREATE TABLE IF NOT EXISTS alpha_activity_signals (
  as_of_date TEXT NOT NULL, symbol TEXT NOT NULL, formula_version TEXT NOT NULL,
  score REAL NOT NULL, percentile REAL, state TEXT NOT NULL,
  persistence_sessions INTEGER NOT NULL DEFAULT 0,
  avg_trade_qty REAL, avg_trade_qty_inclusive20 REAL, avg_trade_qty_ratio20 REAL,
  avg_trade_value REAL, delivery_pct REAL, delivery_pct_prior19 REAL, delivery_ratio19 REAL,
  source TEXT NOT NULL, quality_status TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(as_of_date,symbol,formula_version),
  CHECK(state IN ('baseline','abnormal','persistent_abnormal','isolated_extreme')),
  CHECK(quality_status IN ('ready','warming','stale','quarantined'))
);
CREATE INDEX IF NOT EXISTS idx_alpha_activity_rank
  ON alpha_activity_signals(as_of_date, score DESC);

CREATE TABLE IF NOT EXISTS alpha_predictions (
  prediction_id TEXT PRIMARY KEY, as_of_time TEXT NOT NULL, symbol TEXT NOT NULL,
  model_id TEXT NOT NULL, model_version TEXT NOT NULL, training_cutoff TEXT NOT NULL,
  universe TEXT NOT NULL, calibration_state TEXT NOT NULL, source_freshness TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'shadow', promotion_eligible INTEGER NOT NULL DEFAULT 0,
  probability_1r_first REAL, probability_2r_5d REAL, probability_2r_10d REAL,
  probability_2r_20d REAL, expected_mfe_r REAL, expected_mae_r REAL,
  expected_holding_sessions REAL, evidence_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK(status = 'shadow'), CHECK(promotion_eligible = 0),
  CHECK(training_cutoff <= as_of_time)
);

CREATE TABLE IF NOT EXISTS alpha_experiments (
  experiment_id TEXT PRIMARY KEY, hypothesis TEXT NOT NULL, specification_json TEXT NOT NULL,
  status TEXT NOT NULL, training_cutoff TEXT, results_json TEXT,
  failure_reason TEXT, frozen_at TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK(status IN ('draft','running','passed','failed','rejected'))
);
CREATE TABLE IF NOT EXISTS alpha_trial_lineage (
  experiment_id TEXT PRIMARY KEY, family_id TEXT NOT NULL, parent_experiment_id TEXT,
  generation INTEGER NOT NULL DEFAULT 0, trial_index INTEGER NOT NULL,
  hypothesis_signature TEXT NOT NULL, frozen_universe TEXT, frozen_oos_start TEXT,
  frozen_oos_end TEXT, frozen_cost_policy TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(experiment_id) REFERENCES alpha_experiments(experiment_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alpha_trial_signature
  ON alpha_trial_lineage(family_id,hypothesis_signature,trial_index);

CREATE TABLE IF NOT EXISTS alpha_factor_evaluations (
  factor_id TEXT NOT NULL,factor_version TEXT NOT NULL,evaluation_date TEXT NOT NULL,
  horizon_sessions INTEGER NOT NULL,pearson_ic REAL,spearman_rank_ic REAL,
  universe_denominator INTEGER NOT NULL,regime TEXT,turnover REAL,
  future_available_at TEXT NOT NULL,definition_version TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(factor_id,factor_version,evaluation_date,horizon_sessions),
  CHECK(horizon_sessions IN (5,10,20)),CHECK(future_available_at>evaluation_date)
);
CREATE TABLE IF NOT EXISTS alpha_factor_health (
  factor_id TEXT NOT NULL,factor_version TEXT NOT NULL,horizon_sessions INTEGER NOT NULL,
  mean_ic REAL,ic_std REAL,icir_sat10ic REAL,mean_rank_ic REAL,sign_consistency REAL,
  evaluation_count INTEGER NOT NULL,sample_size INTEGER NOT NULL,last_evaluation_date TEXT,
  definition_version TEXT NOT NULL,updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(factor_id,factor_version,horizon_sessions)
);

CREATE TABLE IF NOT EXISTS alpha_ablation_results (
  experiment_id TEXT NOT NULL,component_name TEXT NOT NULL,oos_slice TEXT NOT NULL,
  fitness_delta REAL,ic_delta REAL,expectancy_delta REAL,drawdown_delta REAL,trade_count_delta INTEGER,
  classification TEXT NOT NULL,policy_version TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(experiment_id,component_name,oos_slice)
);
CREATE TABLE IF NOT EXISTS alpha_plateau_results (
  experiment_id TEXT NOT NULL,parameter_name TEXT NOT NULL,tested_value REAL NOT NULL,
  relative_offset REAL NOT NULL,fitness REAL,status TEXT NOT NULL,policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(experiment_id,parameter_name,tested_value)
);
CREATE TABLE IF NOT EXISTS alpha_failure_memories (
  failure_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,variant_signature TEXT NOT NULL,
  failed_gate TEXT NOT NULL,failure_class TEXT NOT NULL,evidence_json TEXT NOT NULL,
  distilled_rule TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alpha_failed_signature
  ON alpha_failure_memories(variant_signature,failed_gate);
CREATE TRIGGER IF NOT EXISTS alpha_failure_memories_immutable_update
BEFORE UPDATE ON alpha_failure_memories BEGIN SELECT RAISE(ABORT,'alpha failure memories are immutable'); END;
CREATE TRIGGER IF NOT EXISTS alpha_failure_memories_immutable_delete
BEFORE DELETE ON alpha_failure_memories BEGIN SELECT RAISE(ABORT,'alpha failure memories are immutable'); END;

CREATE TABLE IF NOT EXISTS alpha_performance_cones (
  cone_id TEXT PRIMARY KEY,cohort_id TEXT NOT NULL,model_version TEXT NOT NULL,
  backtest_cutoff TEXT NOT NULL,sample_size INTEGER NOT NULL,bootstrap_method TEXT NOT NULL,
  deterministic_seed INTEGER NOT NULL,horizon_sessions INTEGER NOT NULL,bands_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS alpha_model_registry (
  model_id TEXT NOT NULL, model_version TEXT NOT NULL, model_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'shadow', promotion_eligible INTEGER NOT NULL DEFAULT 0,
  training_cutoff TEXT, validation_json TEXT NOT NULL DEFAULT '{}',
  live_shadow_sessions INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(model_id, model_version), CHECK(status = 'shadow'),
  CHECK(promotion_eligible = 0), CHECK(live_shadow_sessions >= 0)
);

-- Point-in-time symbol identity, built from daily_prices itself (no external
-- listing feed). Global summary for reference/UI only — NOT point-in-time
-- safe by itself, since first_seen/last_seen/delisted are computed over the
-- WHOLE panel. Backtests/ranking must use universe_on(conn, as_of_date) in
-- alpha/symbol_identity.py instead, which re-derives everything from
-- daily_prices rows with trade_date <= as_of_date only.
CREATE TABLE IF NOT EXISTS symbol_identity (
  symbol TEXT PRIMARY KEY,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  session_count INTEGER NOT NULL DEFAULT 0,
  max_gap_sessions INTEGER NOT NULL DEFAULT 0,
  trailing_gap_sessions INTEGER NOT NULL DEFAULT 0,
  delisted INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_symbol_identity_last_seen ON symbol_identity(last_seen);

CREATE TABLE IF NOT EXISTS decision_memories (
  memory_id TEXT PRIMARY KEY, decision_time TEXT NOT NULL, symbol TEXT NOT NULL,
  decision TEXT NOT NULL, setup_family TEXT, regime TEXT, sector TEXT, theme TEXT,
  execution_lens TEXT, evidence_json TEXT NOT NULL, proposed_path_json TEXT,
  data_quality REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK(decision IN ('TAKE','WATCH','SKIP','BLOCKED'))
);
CREATE INDEX IF NOT EXISTS idx_decision_memory_lookup
  ON decision_memories(symbol, decision_time);
CREATE TRIGGER IF NOT EXISTS decision_memories_immutable_update
BEFORE UPDATE ON decision_memories BEGIN SELECT RAISE(ABORT, 'decision memories are immutable'); END;
CREATE TRIGGER IF NOT EXISTS decision_memories_immutable_delete
BEFORE DELETE ON decision_memories BEGIN SELECT RAISE(ABORT, 'decision memories are immutable'); END;

CREATE TABLE IF NOT EXISTS decision_memory_outcomes (
  memory_id TEXT PRIMARY KEY, outcome_available_at TEXT NOT NULL, outcome_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(memory_id) REFERENCES decision_memories(memory_id)
);
CREATE TRIGGER IF NOT EXISTS decision_memory_outcomes_immutable_update
BEFORE UPDATE ON decision_memory_outcomes BEGIN SELECT RAISE(ABORT, 'memory outcomes are immutable'); END;
CREATE TRIGGER IF NOT EXISTS decision_memory_outcomes_immutable_delete
BEFORE DELETE ON decision_memory_outcomes BEGIN SELECT RAISE(ABORT, 'memory outcomes are immutable'); END;

CREATE TABLE IF NOT EXISTS memory_analogues (
  query_id TEXT NOT NULL, memory_id TEXT NOT NULL, query_as_of TEXT NOT NULL,
  similarity REAL NOT NULL, recency_weight REAL NOT NULL, quality_weight REAL NOT NULL,
  outcome_weight REAL NOT NULL, combined_score REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(query_id, memory_id),
  FOREIGN KEY(memory_id) REFERENCES decision_memories(memory_id),
  CHECK(similarity BETWEEN 0 AND 1), CHECK(query_as_of >= (SELECT decision_time FROM decision_memories WHERE memory_id = memory_analogues.memory_id))
);
"""

_SCHEMA_LOCK = threading.Lock()
_READY_DATABASES: set[str] = set()


def _database_identity(conn) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    path = str(row[2] or "") if row else ""
    return path or f":memory:{id(conn)}"


def _schema_present(conn) -> bool:
    """Guard the readiness cache against replaced files and reused object ids."""
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='decision_memories'"
    ).fetchone() is not None


def record_promotion_experiment(conn, verdict: dict) -> str:
    """Append-only write of a promotion-gate run (pass or fail) into alpha_experiments."""
    import json
    import hashlib
    from uuid import uuid4

    ensure_schema(conn)
    eid = uuid4().hex
    status = "passed" if verdict.get("verdict") == "passed" else "failed"
    conn.execute(
        "INSERT INTO alpha_experiments "
        "(experiment_id, hypothesis, specification_json, status, results_json, failure_reason, frozen_at) "
        "VALUES (?,?,?,?,?,?,datetime('now'))",
        (
            eid,
            str(verdict.get("hypothesis") or ""),
            json.dumps(verdict.get("config") or {}, sort_keys=True),
            status,
            json.dumps(verdict, sort_keys=True),
            None if status == "passed" else json.dumps(verdict.get("gates"), sort_keys=True),
        ),
    )
    config = verdict.get("config") or {}
    family_id = str(config.get("family_id") or verdict.get("hypothesis") or "unclassified")
    signature = hashlib.sha256(
        json.dumps({"hypothesis": verdict.get("hypothesis"), "config": config}, sort_keys=True).encode()
    ).hexdigest()
    trial_index = conn.execute(
        "SELECT COUNT(*) n FROM alpha_trial_lineage WHERE family_id=?", (family_id,)
    ).fetchone()["n"] + 1
    conn.execute(
        "INSERT INTO alpha_trial_lineage (experiment_id,family_id,parent_experiment_id,generation,"
        "trial_index,hypothesis_signature,frozen_universe,frozen_oos_start,frozen_oos_end,frozen_cost_policy) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (eid, family_id, config.get("parent_experiment_id"), int(config.get("generation") or 0),
         trial_index, signature, config.get("universe"), config.get("oos_start"), config.get("oos_end"),
         json.dumps(verdict.get("cost_constants") or {}, sort_keys=True)),
    )
    if status == "failed":
        for gate in verdict.get("gates") or []:
            if gate.get("passed"):
                continue
            gate_name = str(gate.get("name") or "unknown_gate")
            failure_id = hashlib.sha256(f"{signature}|{gate_name}".encode()).hexdigest()[:32]
            detail = gate.get("detail") or {}
            failure_class = {
                "placebo": "statistical_luck",
                "regime_stability": "regime_mismatch",
                "subsample_stability": "sample_instability",
                "min_sample": "sample_insufficiency",
                "walk_forward": "oos_failure",
            }.get(gate_name, "validation_failure")
            conn.execute(
                "INSERT OR IGNORE INTO alpha_failure_memories "
                "(failure_id,experiment_id,variant_signature,failed_gate,failure_class,evidence_json,distilled_rule) "
                "VALUES (?,?,?,?,?,?,?)",
                (failure_id, eid, signature, gate_name, failure_class, json.dumps(detail, sort_keys=True),
                 f"Reject this exact variant signature until the {gate_name} evidence changes."),
            )
    conn.commit()
    return eid


def already_failed(conn, hypothesis_signature: str) -> dict | None:
    """Return the frozen failed experiment if this hypothesis was already rejected."""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT experiment_id, hypothesis, status, frozen_at, results_json FROM alpha_experiments "
        "WHERE status IN ('failed','rejected') AND hypothesis = ? "
        "ORDER BY frozen_at DESC LIMIT 1",
        (hypothesis_signature,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def ensure_schema(conn) -> None:
    """Create the canonical alpha schema. Safe to call repeatedly."""
    identity = _database_identity(conn)
    if identity in _READY_DATABASES and _schema_present(conn):
        return
    # Alpha Lab opens several GETs in parallel. Serialise the one-time DDL and
    # make later read requests true no-ops instead of competing for SQLite's
    # schema write lock on every render.
    with _SCHEMA_LOCK:
        if identity in _READY_DATABASES and _schema_present(conn):
            return
        # Intraday storage has one writer/owner; reuse its richer provider-neutral
        # schema rather than maintaining a second incompatible table definition.
        from manas_os.sources import intraday

        intraday.ensure_schema(conn)
        # SQLite prohibits subqueries in CHECK constraints, so create that table separately.
        head, analogue = DDL.split("CREATE TABLE IF NOT EXISTS memory_analogues", 1)
        conn.executescript(head)
        analogue = "CREATE TABLE IF NOT EXISTS memory_analogues" + analogue
        analogue = analogue.replace(
            ", CHECK(query_as_of >= (SELECT decision_time FROM decision_memories WHERE memory_id = memory_analogues.memory_id))",
            "",
        )
        conn.executescript(analogue)
        conn.execute("""CREATE TRIGGER IF NOT EXISTS memory_analogues_no_future
            BEFORE INSERT ON memory_analogues
            WHEN NEW.query_as_of < (SELECT decision_time FROM decision_memories WHERE memory_id=NEW.memory_id)
            BEGIN SELECT RAISE(ABORT, 'future memory analogue'); END""")
        conn.commit()
        _READY_DATABASES.add(identity)
