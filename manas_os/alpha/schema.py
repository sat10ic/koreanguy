"""Canonical, additive SQLite schema for the alpha research fabric."""
from __future__ import annotations


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


def record_promotion_experiment(conn, verdict: dict) -> str:
    """Append-only write of a promotion-gate run (pass or fail) into alpha_experiments."""
    import json
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
