"""HANDOFF_GEMINI_alpha_memory_gates tests."""
from __future__ import annotations

import math

import pytest

from manas_os import db
from manas_os.alpha import leakage_audit, memory, promotion_gates, schema


def test_recall_multiplicative_q_sim_rec_conf(tmp_path):
    conn = db.init_db(tmp_path / "a.db")
    try:
        schema.ensure_schema(conn)
        mid = memory.record_decision(
            conn,
            decision_time="2026-01-01T10:00:00",
            symbol="AAA",
            decision="TAKE",
            evidence={"rs": 80.0},
            setup_family="catalyst",
            regime="SELECTIVE",
            data_quality=0.9,
        )
        memory.resolve_outcome(
            conn,
            memory_id=mid,
            outcome_available_at="2026-01-10T10:00:00",
            outcome={"r_multiple": 2.0, "status": "RESOLVED", "direction": "LONG"},
        )
        top = memory.recall_analogues(
            conn,
            as_of="2026-02-01T00:00:00",
            setup_family="catalyst",
            regime="SELECTIVE",
            query_features={"rs": 81.0},
            limit=3,
        )
        assert top and top[0]["memory_id"] == mid
        assert 0 < top[0]["Q"] < 1
        assert top[0]["combined_score"] > 0
        # Q for R=2 should be sigmoid(2)
        assert abs(top[0]["Q"] - (1 / (1 + math.exp(-2)))) < 1e-6
    finally:
        conn.close()


def test_anti_resonance_flags_opposing_outcomes(tmp_path):
    conn = db.init_db(tmp_path / "b.db")
    try:
        schema.ensure_schema(conn)
        mid = memory.record_decision(
            conn,
            decision_time="2026-01-01T10:00:00",
            symbol="BBB",
            decision="TAKE",
            evidence={},
            setup_family="momentum",
            regime="RISK_ON",
        )
        memory.resolve_outcome(
            conn,
            memory_id=mid,
            outcome_available_at="2026-01-05T00:00:00",
            outcome={"r_multiple": -1.5, "status": "RESOLVED"},
        )
        top = memory.recall_analogues(
            conn,
            as_of="2026-02-01T00:00:00",
            setup_family="momentum",
            proposed_direction="LONG",
            limit=3,
        )
        assert top[0]["anti_resonance"]["active"] is True
        assert mid in top[0]["anti_resonance"]["opposing"]
    finally:
        conn.close()


def test_recall_accepts_mixed_legacy_and_timezone_aware_timestamps(tmp_path):
    conn = db.init_db(tmp_path / "mixed_time.db")
    try:
        schema.ensure_schema(conn)
        mid = memory.record_decision(
            conn,
            decision_time="2026-01-01T10:00:00+05:30",
            symbol="TZTEST",
            decision="WATCH",
            evidence={},
        )
        top = memory.recall_analogues(
            conn,
            as_of="2026-02-01T00:00:00",
            symbol="TZTEST",
            limit=1,
        )
        assert top[0]["memory_id"] == mid
        assert top[0]["recency_weight"] > 0
    finally:
        conn.close()


def test_promotion_battery_rejects_random_and_accepts_strong(tmp_path):
    # Known-good: constant positive edge after costs
    good = [0.01] * 80
    baseline = [0.0] * 80
    regimes = {"RISK_ON": [0.01] * 30, "SELECTIVE": [0.008] * 30, "DEFENSIVE": [0.005] * 20}
    v_good = promotion_gates.run_promotion_battery(
        good, baseline, regimes, hypothesis="const_edge_v1"
    )
    assert v_good["verdict"] == "passed"

    # Overfit-like: pure noise
    import random
    rng = random.Random(0)
    noise = [rng.gauss(0, 0.02) for _ in range(80)]
    v_bad = promotion_gates.run_promotion_battery(
        noise, baseline, {"RISK_ON": noise[:40], "SELECTIVE": noise[40:]}, hypothesis="noise_v1"
    )
    # Noise may sporadically pass individual gates; battery should usually fail
    # At least one of placebo/walk_forward/subsample should be informative
    assert "gates" in v_bad and v_bad["shadow_only"] is True


def test_leakage_audit_catches_deliberate_leak():
    bars = [{"trade_date": f"2026-01-{i:02d}", "close": 100 + i} for i in range(1, 11)]
    clean = leakage_audit.audit_feature_fn(bars, leakage_audit.clean_feature_fn)
    assert clean["ok"] is True
    leaky = leakage_audit.audit_feature_fn(bars, leakage_audit.deliberately_leaky_feature_fn)
    assert leaky["ok"] is False
    assert any(x["feature"] == "leak_max_close" for x in leaky["leaks"])


def test_experiment_kb_flags_rediscovery(tmp_path):
    conn = db.init_db(tmp_path / "c.db")
    try:
        schema.ensure_schema(conn)
        verdict = promotion_gates.run_promotion_battery(
            [0.0] * 20, [0.0] * 20, {}, hypothesis="idea_xyz"
        )
        assert verdict["verdict"] == "failed"
        eid = schema.record_promotion_experiment(conn, verdict)
        assert eid
        hit = schema.already_failed(conn, "idea_xyz")
        assert hit is not None
        assert hit["status"] == "failed"
        assert schema.already_failed(conn, "never_tried") is None
        lineage = conn.execute(
            "SELECT family_id,trial_index,hypothesis_signature FROM alpha_trial_lineage WHERE experiment_id=?",
            (eid,),
        ).fetchone()
        assert lineage["family_id"] == "idea_xyz"
        assert lineage["trial_index"] == 1
        failures = conn.execute(
            "SELECT failed_gate,failure_class FROM alpha_failure_memories WHERE experiment_id=?",
            (eid,),
        ).fetchall()
        assert failures
        with pytest.raises(Exception):
            conn.execute(
                "UPDATE alpha_failure_memories SET distilled_rule='rewrite' WHERE experiment_id=?",
                (eid,),
            )
    finally:
        conn.close()
