from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from manas_os.alpha.diagnostics import (
    bayesian_setup_expectancy,
    block_bootstrap_diagnostics,
    competing_risk_summary,
)
from manas_os.alpha.features import compute_daily_features
from manas_os.alpha.memory import recall_analogues, record_decision, resolve_outcome
from manas_os.alpha.schema import ensure_schema
from manas_os.alpha.services import overview, symbol


def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def add_prices(c, symbols=("AAA", "BBB"), days=70):
    c.execute("CREATE TABLE daily_prices(symbol TEXT,trade_date TEXT,series TEXT,close REAL)")
    for si, sym in enumerate(symbols):
        for day in range(1, days + 1):
            stamp = (date(2026, 1, 1) + timedelta(days=day - 1)).isoformat()
            c.execute("INSERT INTO daily_prices VALUES(?,?,?,?)", (sym, stamp, "EQ", 100 + day * (si + 1)))


def add_outcomes(c):
    c.execute("CREATE TABLE candidates(candidate_date TEXT,symbol TEXT,setup TEXT,PRIMARY KEY(candidate_date,symbol,setup))")
    c.execute("""CREATE TABLE outcomes(candidate_date TEXT,symbol TEXT,setup TEXT,horizon INTEGER,status TEXT,
      managed_r REAL,hit_1r INTEGER,exit_reason TEXT)""")


def test_schema_is_idempotent_and_structurally_shadow_only():
    c = conn(); ensure_schema(c); ensure_schema(c)
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"alpha_feature_snapshots", "alpha_predictions", "alpha_experiments", "alpha_model_registry",
            "decision_memories", "memory_analogues", "intraday_bars"} <= tables
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("""INSERT INTO alpha_model_registry(model_id,model_version,model_type,status,promotion_eligible)
          VALUES('x','1','gbm','promoted',1)""")


def test_features_are_causal_under_future_append():
    c = conn(); add_prices(c, days=65)
    cutoff = (date(2026, 1, 1) + timedelta(days=59)).isoformat()
    first = compute_daily_features(c, cutoff)
    frozen = {r["symbol"]: r for r in first}
    for sym in ("AAA", "BBB"):
        c.execute("INSERT INTO daily_prices VALUES(?,?,?,?)", (sym, "2027-01-01", "EQ", 9999))
    second = compute_daily_features(c, cutoff)
    assert second == first
    assert all(r["source_max_date"] == cutoff for r in frozen.values())
    assert all(r["source_denominator"] == 2 for r in frozen.values())


def test_bayesian_expectancy_shrinks_sparse_setup_to_parent():
    c = conn(); add_outcomes(c)
    values = [("A", 4.0)] + [("B", -1.0)] * 9
    for i, (setup, value) in enumerate(values):
        key = (f"d{i}", f"S{i}", setup)
        c.execute("INSERT INTO candidates VALUES(?,?,?)", key)
        c.execute("INSERT INTO outcomes VALUES(?,?,?,?,?,?,?,?)", (*key, 10, "complete", value, int(value >= 1), "horizon_close"))
    rows = {r["setup"]: r for r in bayesian_setup_expectancy(c, prior_strength=10)}
    assert 0.1 < rows["A"]["posterior_hit_rate"] < rows["A"]["raw_hit_rate"]
    assert rows["A"]["posterior_expectancy_r"] < rows["A"]["raw_expectancy_r"]


def test_competing_risk_classification_uses_managed_path():
    c = conn(); add_outcomes(c)
    examples = [(1, "horizon_close"), (0, "stop"), (0, "gap_through_stop"), (0, "horizon_close")]
    for i, (hit, reason) in enumerate(examples):
        key = (f"d{i}", f"S{i}", "X")
        c.execute("INSERT INTO candidates VALUES(?,?,?)", key)
        c.execute("INSERT INTO outcomes VALUES(?,?,?,?,?,?,?,?)", (*key, 10, "complete", 0, hit, reason))
    result = competing_risk_summary(c)
    assert result["counts"] == {"plus_1r_first": 1, "stop_first": 2, "neither": 1}


def test_block_bootstrap_is_seeded_and_preserves_blocks():
    args = ([1, -1, -1, 2, .5],)
    a = block_bootstrap_diagnostics(*args, block_size=2, simulations=50, seed=44)
    b = block_bootstrap_diagnostics(*args, block_size=2, simulations=50, seed=44)
    assert a == b
    assert a["max_losing_streak"]["p95"] >= 2


def test_memory_recall_never_exposes_future_decision_or_outcome():
    c = conn()
    past = record_decision(c, memory_id="past", decision_time="2026-01-01T10:00:00", symbol="AAA",
                           decision="WATCH", evidence={"x": 1}, data_quality=.8)
    resolve_outcome(c, memory_id=past, outcome_available_at="2026-01-10T16:00:00", outcome={"r": 2})
    record_decision(c, memory_id="future", decision_time="2026-02-01T10:00:00", symbol="AAA",
                    decision="SKIP", evidence={"x": 2})
    early = recall_analogues(c, as_of="2026-01-05T12:00:00", symbol="AAA")
    assert [r["memory_id"] for r in early] == ["past"]
    assert early[0]["outcome"] is None
    late = recall_analogues(c, as_of="2026-01-15T12:00:00", symbol="AAA")
    assert late[0]["outcome"] == {"r": 2}


def test_services_are_honest_when_warming_and_behaviour_is_structured():
    c = conn(); ensure_schema(c)
    assert overview(c)["state"] == "warming"
    add_prices(c); cutoff = (date(2026, 1, 1) + timedelta(days=69)).isoformat()
    compute_daily_features(c, cutoff)
    payload = symbol(c, "AAA", as_of=cutoff)
    assert payload["state"] == "ready" and payload["shadow_only"] is True
    assert "ema_relationships" in payload["setup_behaviour"]
    assert "supporting_path_evidence" in payload
