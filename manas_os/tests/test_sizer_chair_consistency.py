"""Tests for run_card._sizer_chair_consistency (UI_BUILD_DIRECTION 4c).

The sizer only ever prices chair-TAKE rows, so a sized symbol must have a
chair verdict of TAKE or a recorded strike. The build-time guard logs a
run-card error for any sizer row whose chair reads SKIP-without-strike.
"""
import json

from manas_os import db
from manas_os.agents import debate, run_card


AS_OF = "2026-06-30"


def _seed(conn, symbol, agent, verdict, *, lens=None, reasoning="reason"):
    debate.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning, lens_scores_json) "
        "VALUES (?, ?, ?, ?, 3, 1, 'b', 'b', ?, ?)",
        (AS_OF, symbol, agent, verdict, reasoning, json.dumps(lens or {})),
    )


def test_consistency_ok_for_struck_sized_row(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        # GROWW-shaped: chair SKIP but struck=true, sizer priced (then refused).
        _seed(conn, "GROWW", "chair", "SKIP", lens={"struck": True, "base_verdict": "TAKE"})
        _seed(conn, "GROWW", "sizer", "SKIP")
        # Clean TAKE that the sizer sized.
        _seed(conn, "AAA", "chair", "TAKE", lens={"struck": False, "base_verdict": "TAKE"})
        _seed(conn, "AAA", "sizer", "TAKE")
        conn.commit()
        assert run_card._sizer_chair_consistency(conn, AS_OF) == []
    finally:
        conn.close()


def test_consistency_flags_sized_skip_without_strike(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed(conn, "BAD", "chair", "SKIP", lens={"struck": False, "base_verdict": "SKIP"})
        _seed(conn, "BAD", "sizer", "SKIP")
        conn.commit()
        errors = run_card._sizer_chair_consistency(conn, AS_OF)
        assert len(errors) == 1
        assert errors[0]["stage"] == "chair_sizer_consistency"
        assert "BAD" in errors[0]["detail"]
    finally:
        conn.close()


def test_consistency_pre_migration_row_uses_prose_fallback(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        # Old row: no struck key in lens, strike recorded only in prose.
        _seed(conn, "OLD", "chair", "SKIP", lens={}, reasoning="models 4T/1S, spread 1; struck: sector risk")
        _seed(conn, "OLD", "sizer", "SKIP")
        conn.commit()
        assert run_card._sizer_chair_consistency(conn, AS_OF) == []
    finally:
        conn.close()
