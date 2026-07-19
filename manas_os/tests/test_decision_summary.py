"""Shared actionable-decision contract (USABILITY_UX_AUDIT_2026-07-19
exec-verdict bullet 3): the live UI once simultaneously showed SIT OUT,
0 live, 12 gate-passed candidates, and a demand to review 4 setups -- four
competing authorities for one answer. app._decision_summary(conn, date) is
now the ONE writer for gate_passed/actionable/pending counts; every surface
(MARKET verdict strip via /api/desk/run-card's decision_summary field,
DECIDE's setups banner via the same field, and /api/flow/today's setups
step) reads its output instead of recomputing its own.

This suite covers: (1) the pure helper across the three canonical nights
(SIT_OUT-with-gate-passed, RISK_ON-with-pending, honest-zero), and (2) an
anti-drift lock proving /api/flow/today and /api/desk/run-card report the
identical pending_decisions_count for the same fixture.
"""
import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import run_card
from manas_os.api import app as api_app
from manas_os.scanner import outcomes as scanner_outcomes
from manas_os.tests.conftest import AS_OF, seed_regime, seed_sizer_verdict


def _client(db_path, monkeypatch, today=None):
    """TestClient bound to a temp DB (mirrors test_flow_today_api.py's pattern)."""
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    if today is not None:
        monkeypatch.setattr(api_app, "_today", lambda: today)
    return TestClient(api_app.app)


def _seed_candidate(conn, symbol, scan_date=AS_OF, entry=100.0, stop=95.0):
    """One gate-passed scan_candidates row -- a direct insert (not the full
    scanner/candidates pipeline) since this suite is testing the decision
    contract's arithmetic, not gate-passing itself."""
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates (scan_date, symbol, setup, entry, stop) "
        "VALUES (?, ?, 'breakout', ?, ?)",
        (scan_date, symbol, entry, stop),
    )


# ------------------------------------------------------------------
# helper unit cases
# ------------------------------------------------------------------

def test_decision_summary_sit_out_when_gate_passed_but_none_actionable(tmp_path):
    """12 names cleared the gate, none sized -> SIT_OUT verdict and a
    headline that reconciles the count instead of just saying 'sit out'."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        seed_regime(conn, scan_date=AS_OF, mode="SELECTIVE")
        for i in range(12):
            _seed_candidate(conn, f"SYM{i:02d}")
        conn.commit()
        summary = api_app._decision_summary(conn, AS_OF)
    finally:
        conn.close()

    assert summary["gate_passed_count"] == 12
    assert summary["actionable_count"] == 0
    assert summary["pending_decisions_count"] == 0
    assert summary["regime_verdict"] == "SIT_OUT"
    assert "SIT OUT" in summary["headline"]
    assert "12" in summary["headline"]
    assert "sized" in summary["headline"].lower() or "actionable" in summary["headline"].lower()
    assert "nothing to decide" in summary["headline"].lower()


def test_decision_summary_risk_on_with_pending_demands_review(tmp_path):
    """RISK_ON regime, 2 of 3 gate-passed names are actionable, neither
    reviewed yet -> the headline demands a TAKEN/SKIPPED call, not silence."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        seed_regime(conn, scan_date=AS_OF, mode="RISK_ON")
        _seed_candidate(conn, "AAA")
        _seed_candidate(conn, "BBB")
        _seed_candidate(conn, "CCC")
        conn.commit()
        seed_sizer_verdict(conn, symbol="AAA", scan_date=AS_OF, final_qty=25)
        seed_sizer_verdict(conn, symbol="BBB", scan_date=AS_OF, final_qty=10)
        # CCC deliberately left without a sizer verdict -- gate-passed, not actionable.
        summary = api_app._decision_summary(conn, AS_OF)
    finally:
        conn.close()

    assert summary["gate_passed_count"] == 3
    assert summary["actionable_count"] == 2
    assert summary["pending_decisions_count"] == 2
    assert summary["regime_verdict"] == "RISK_ON"
    assert "RISK ON" in summary["headline"]
    assert "2" in summary["headline"]
    assert "TAKEN/SKIPPED" in summary["headline"]


def test_decision_summary_zero_gate_passed_is_honest(tmp_path):
    """No scan / nothing cleared the gate -> a plain honest 'nothing' line,
    distinct from the SIT_OUT-with-gate-passed wording above."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        seed_regime(conn, scan_date=AS_OF, mode="NO_TRADE")
        summary = api_app._decision_summary(conn, AS_OF)
    finally:
        conn.close()

    assert summary["gate_passed_count"] == 0
    assert summary["actionable_count"] == 0
    assert summary["pending_decisions_count"] == 0
    assert summary["scan_date"] is None
    assert "no names cleared the gate" in summary["headline"].lower()
    assert "nothing to decide" in summary["headline"].lower()


# ------------------------------------------------------------------
# anti-drift lock: /api/flow/today and /api/desk/run-card must agree
# ------------------------------------------------------------------

def test_flow_today_and_run_card_agree_on_pending_decisions_count(tmp_path, monkeypatch):
    """The bug this whole contract exists to kill: two screens quoting two
    different pending-review counts for the same night. Seed 3 gate-passed
    candidates (2 actionable), mark one of the two actionable ones TAKEN, and
    assert /api/flow/today's setups step and /api/desk/run-card's
    decision_summary both report pending_decisions_count == 1 -- because both
    now call the exact same helper, not two independent derivations."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        scanner_outcomes.ensure_setup_decisions_schema(conn)
        seed_regime(conn, scan_date=AS_OF, mode="SELECTIVE")
        _seed_candidate(conn, "AAA", entry=100.0, stop=95.0)
        _seed_candidate(conn, "BBB", entry=50.0, stop=47.0)
        _seed_candidate(conn, "CCC", entry=30.0, stop=28.0)
        conn.commit()
        seed_sizer_verdict(conn, symbol="AAA", scan_date=AS_OF, final_qty=25)
        seed_sizer_verdict(conn, symbol="BBB", scan_date=AS_OF, final_qty=10)
        # CCC: gate-passed, no sizer verdict -- not actionable.
        conn.execute(
            "INSERT INTO setup_decisions (scan_date, symbol, decision) VALUES (?, 'AAA', 'taken')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    run_cards_root = tmp_path / "run_cards"
    run_cards_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_card, "RUN_CARD_ROOT", run_cards_root)
    (run_cards_root / f"{AS_OF}.json").write_text(
        json.dumps({
            "run_date": AS_OF, "scan_date": AS_OF, "no_op": False,
            "regime": {}, "governor": {}, "heat": {}, "pipeline": [],
            "shortlist": [], "tonights_call": {}, "errors": [],
        }),
        encoding="utf-8",
    )

    client = _client(db_path, monkeypatch, today=AS_OF)
    flow_payload = client.get("/api/flow/today").json()
    card_payload = client.get("/api/desk/run-card").json()

    assert card_payload["available"] is True
    assert card_payload["decision_summary"] is not None
    assert flow_payload["decision_summary"]["pending_decisions_count"] == 1
    assert card_payload["decision_summary"]["pending_decisions_count"] == 1
    assert (
        flow_payload["decision_summary"]["pending_decisions_count"]
        == card_payload["decision_summary"]["pending_decisions_count"]
    )
    # the visible workflow-rail text must carry the same number, not a
    # separately-derived one.
    setups = next(s for s in flow_payload["steps"] if s["id"] == "setups")
    assert "1" in setups["detail"]
