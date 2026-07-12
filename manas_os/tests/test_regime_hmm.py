import math

import numpy as np
import pandas as pd
import pytest

from manas_os import db
from manas_os.regime import regime_hmm as rh
from manas_os.tests.test_regime_snapshot import _insert_breadth


def _seed_nifty(conn, n=120, seed=0, vol=0.01, start="2025-01-01"):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range(start, periods=n)
    rets = rng.normal(0, vol, size=n)
    price = 100.0
    rows = []
    for d, r in zip(dates, rets):
        price *= (1 + r)
        rows.append((rh.NIFTY_SYMBOL, d.strftime("%Y-%m-%d"), price, None))
    conn.executemany(
        "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close, sma50) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    return [d.strftime("%Y-%m-%d") for d in dates]


def _seed_breadth(conn, dates, seed=1):
    rng = np.random.RandomState(seed)
    for i, dt in enumerate(dates):
        adv = int(1000 + rng.normal(0, 150))
        dec = int(1000 - (adv - 1000) + rng.normal(0, 50))
        _insert_breadth(conn, trade_date=dt, advances=max(adv, 1), declines=max(dec, 1))


def _seeded_conn(n=120, seed=0):
    conn = db.init_db(":memory:")
    dates = _seed_nifty(conn, n=n, seed=seed)
    _seed_breadth(conn, dates, seed=seed + 1)
    return conn, dates


# ---------------------------------------------------------------------------
# (1) Feature causality
# ---------------------------------------------------------------------------

def test_feature_causality_truncated_history():
    conn, dates = _seeded_conn(n=120, seed=3)
    full = rh.build_feature_frame(conn)

    cutoff = dates[60]
    conn2 = db.init_db(":memory:")
    price_rows = conn.execute(
        "SELECT symbol, trade_date, close FROM sector_index_prices WHERE trade_date <= ?", (cutoff,)
    ).fetchall()
    conn2.executemany(
        "INSERT OR REPLACE INTO sector_index_prices (symbol, trade_date, close) VALUES (?,?,?)",
        [(r["symbol"], r["trade_date"], r["close"]) for r in price_rows],
    )
    breadth_rows = conn.execute(
        "SELECT trade_date, advances, declines FROM breadth_daily WHERE trade_date <= ?", (cutoff,)
    ).fetchall()
    for r in breadth_rows:
        conn2.execute(
            "INSERT INTO breadth_daily (trade_date, advances, declines) VALUES (?,?,?)",
            (r["trade_date"], r["advances"], r["declines"]),
        )
    conn2.commit()
    truncated = rh.build_feature_frame(conn2)

    row_full = full[full["trade_date"] == pd.Timestamp(cutoff)].iloc[0]
    row_trunc = truncated[truncated["trade_date"] == pd.Timestamp(cutoff)].iloc[0]
    for col in rh.FEATURE_COLS:
        assert math.isclose(row_full[col], row_trunc[col], rel_tol=1e-9), col


def test_feature_frame_empty_without_data():
    conn = db.init_db(":memory:")
    out = rh.build_feature_frame(conn)
    assert out.empty


# ---------------------------------------------------------------------------
# (2) State-label mapping determinism
# ---------------------------------------------------------------------------

def test_state_label_mapping_is_deterministic_by_score_rank():
    scores = {0: -0.5, 1: 1.2, 2: 0.3, 3: -1.8}
    mapping = rh.map_states_to_labels(scores)
    assert mapping[1] == "RISK_ON"     # highest score
    assert mapping[2] == "SELECTIVE"
    assert mapping[0] == "DEFENSIVE"
    assert mapping[3] == "NO_TRADE"    # lowest score


def test_state_label_mapping_invariant_to_dict_insertion_order():
    scores_a = {0: -0.5, 1: 1.2, 2: 0.3, 3: -1.8}
    scores_b = {3: -1.8, 1: 1.2, 0: -0.5, 2: 0.3}
    assert rh.map_states_to_labels(scores_a) == rh.map_states_to_labels(scores_b)


def test_state_label_mapping_tie_break_by_state_index():
    scores = {2: 0.0, 0: 0.0, 3: 0.0, 1: 0.0}
    mapping = rh.map_states_to_labels(scores)
    # all tied -> stable sort by state index ascending
    assert mapping == {0: "RISK_ON", 1: "SELECTIVE", 2: "DEFENSIVE", 3: "NO_TRADE"}


# ---------------------------------------------------------------------------
# (3) Display-gate logic
# ---------------------------------------------------------------------------

def test_display_gate_not_allowed_below_threshold():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    for i in range(19):
        rh.persist_row(conn, f"2026-01-{i+1:02d}", state=0, label="SELECTIVE", p_state=0.9, source="live")
    conn.commit()
    gate = rh.display_gate(conn)
    assert gate["sessions_counted"] == 19
    assert gate["display_allowed"] is False


def test_display_gate_allowed_at_threshold():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    for i in range(20):
        rh.persist_row(conn, f"2026-01-{i+1:02d}", state=0, label="SELECTIVE", p_state=0.9, source="live")
    conn.commit()
    gate = rh.display_gate(conn)
    assert gate["sessions_counted"] == 20
    assert gate["display_allowed"] is True


def test_display_gate_excludes_backfill_source():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    for i in range(20):
        rh.persist_row(conn, f"2026-01-{i+1:02d}", state=0, label="SELECTIVE", p_state=0.9, source="backfill")
    conn.commit()
    gate = rh.display_gate(conn)
    assert gate["sessions_counted"] == 0
    assert gate["display_allowed"] is False


def test_caption_warming_up_vs_confirms_vs_disagrees():
    warming = rh.caption({"display_allowed": False, "sessions_counted": 5}, "SELECTIVE", "SELECTIVE")
    assert warming == "HMM confirm: warming up (5/20)"

    confirms = rh.caption({"display_allowed": True, "sessions_counted": 20}, "SELECTIVE", "SELECTIVE")
    assert confirms == "HMM: confirms SELECTIVE"

    disagrees = rh.caption({"display_allowed": True, "sessions_counted": 20}, "RISK_ON", "SELECTIVE")
    assert disagrees == "HMM: disagrees (says RISK_ON)"


def test_get_display_caption_gates_the_label_out_of_the_payload():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    for i in range(5):
        rh.persist_row(conn, f"2026-01-{i+1:02d}", state=0, label="SELECTIVE", p_state=0.9, source="live")
    conn.commit()
    out = rh.get_display_caption(conn, "2026-01-05")
    assert out["display_allowed"] is False
    assert out["hmm_label"] is None  # RENDER RULE: raw label never leaks pre-gate
    assert out["caption"].startswith("HMM confirm: warming up")


# ---------------------------------------------------------------------------
# (4) Stage skip without hmmlearn / insufficient history
# ---------------------------------------------------------------------------

def test_run_skips_without_hmmlearn(monkeypatch):
    conn = db.init_db(":memory:")
    monkeypatch.setattr(rh, "HAS_HMMLEARN", False)
    result = rh.run(conn, "2026-01-05")
    assert result["status"] == "skip"
    assert "hmmlearn" in result["detail"]


@pytest.mark.skipif(not rh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_run_skips_when_regime_snapshots_below_min_history():
    conn = db.init_db(":memory:")
    conn.execute(
        "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES ('2026-01-05', 'SELECTIVE')"
    )
    conn.commit()
    result = rh.run(conn, "2026-01-05")
    assert result["status"] == "skip"
    assert "regime_snapshots" in result["detail"]


@pytest.mark.skipif(not rh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_run_skips_when_feature_history_thin_even_with_enough_snapshots():
    conn = db.init_db(":memory:")
    for i in range(160):
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",),
        )
    conn.commit()
    dates = _seed_nifty(conn, n=10, seed=9)
    _seed_breadth(conn, dates, seed=10)
    result = rh.run(conn, dates[-1])
    assert result["status"] == "skip"


# ---------------------------------------------------------------------------
# End-to-end walk-forward + validation, only when hmmlearn is actually usable
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not rh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_walk_forward_and_validation_smoke():
    conn, dates = _seeded_conn(n=200, seed=42)
    full = rh.build_feature_frame(conn)
    wf = rh.walk_forward_hmm(full, min_train_rows=90)
    assert wf.n_folds >= 1
    assert not wf.rows.empty
    assert 0.0 <= wf.flip_rate <= 1.0

    mm_rows = []
    for d in dates:
        mode = "SELECTIVE" if hash(d) % 2 == 0 else "DEFENSIVE"
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, ?)", (d, mode)
        )
    conn.commit()
    mm_df = rh.load_market_mode(conn)
    contingency = rh.contingency_table(wf.rows, mm_df)
    assert contingency["n"] > 0
    assert 0.0 <= contingency["agreement_rate"] <= 1.0

    conditional = rh.regime_conditional_forward_returns(wf.rows, full[["trade_date", "close"]])
    assert isinstance(conditional, dict)
    report = rh.format_validation_report(wf, contingency, conditional)
    assert "flip_rate" in report


@pytest.mark.skipif(not rh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_run_end_to_end_persists_a_row():
    conn = db.init_db(":memory:")
    for i in range(160):
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",),
        )
    conn.commit()
    dates = _seed_nifty(conn, n=150, seed=5)
    _seed_breadth(conn, dates, seed=6)
    result = rh.run(conn, dates[-1])
    assert result["status"] == "ok"
    row = conn.execute(
        "SELECT * FROM hmm_regime WHERE session_date = ?", (dates[-1],)
    ).fetchone()
    assert row is not None
    assert row["label"] in rh.LABELS_BY_RANK
    assert row["source"] == "live"


@pytest.mark.skipif(not rh.HAS_HMMLEARN, reason="hmmlearn not installed")
def test_run_idempotency():
    conn = db.init_db(":memory:")
    for i in range(160):
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",),
        )
    conn.commit()
    dates = _seed_nifty(conn, n=150, seed=5)
    _seed_breadth(conn, dates, seed=6)
    
    # Run first time
    result1 = rh.run(conn, dates[-1])
    assert result1["status"] == "ok"
    count1 = conn.execute("SELECT COUNT(*) FROM hmm_regime").fetchone()[0]
    assert count1 == 1

    # Run second time
    result2 = rh.run(conn, dates[-1])
    assert result2["status"] == "ok"
    count2 = conn.execute("SELECT COUNT(*) FROM hmm_regime").fetchone()[0]
    assert count2 == 1


def test_get_status_payload_needs_data():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    # Seed less than 150 snapshots
    for i in range(50):
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (f"2025-01-{i+1:02d}",),
        )
    conn.commit()
    
    payload = rh.get_status_payload(conn, "2025-01-20")
    assert payload["status"] == "NEEDS-DATA"
    assert "needs data" in payload["reason"].lower() or "insufficient" in payload["reason"].lower()


def test_get_status_payload_warming():
    conn = db.init_db(":memory:")
    rh.ensure_schema(conn)
    # Seed 160 snapshots
    for i in range(160):
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (f"2025-01-{i+1:02d}",),
        )
    # Seed less than 20 live HMM runs
    for i in range(5):
        rh.persist_row(conn, f"2025-01-{i+1:02d}", state=0, label="SELECTIVE", p_state=0.9, source="live")
    conn.commit()
    
    payload = rh.get_status_payload(conn)
    assert payload["status"] == "WARMING"
    assert "warming" in payload["reason"].lower()

