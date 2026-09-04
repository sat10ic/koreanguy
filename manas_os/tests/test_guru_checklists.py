"""HANDOFF_GEMINI_guru_checklists."""
from manas_os.scanner import mentor_checklists


def test_arora_entry_seeded_with_cites():
    lists = mentor_checklists.load_checklists()
    arora = next(c for c in lists if c["id"] == "arora_entry_v1")
    assert arora["mentor"] == "Manas Arora"
    items = arora["items"]
    assert 8 <= len(items) <= 15
    for it in items:
        assert it.get("source_cite"), it
        assert it.get("eval") in {"AUTO", "MANUAL"}


def test_evaluate_auto_mappings_and_hard_fail_advisory():
    lists = mentor_checklists.load_checklists()
    arora = next(c for c in lists if c["id"] == "arora_entry_v1")
    out = mentor_checklists.evaluate(
        arora,
        symbol="ACME",
        trade_date="2026-07-10",
        ctx={
            "regime_mode": "NO_TRADE",
            "rs": 80,
            "entry": 100,
            "stop": 97,
            "final_qty": 10,
        },
        ticks={},
    )
    assert out["blocks_plan"] is False
    assert out["hard_fail_warning"] is True
    breadth = next(i for i in out["items"] if i["id"] == "breadth_ok")
    assert breadth["state"] == "FAIL"
    rs = next(i for i in out["items"] if i["id"] == "rs_leadership")
    assert rs["state"] == "PASS"
    assert "RS=" in rs["display"]


def test_manual_tick_counts_as_pass():
    lists = mentor_checklists.load_checklists()
    arora = next(c for c in lists if c["id"] == "arora_entry_v1")
    out = mentor_checklists.evaluate(
        arora,
        symbol="ACME",
        trade_date="2026-07-10",
        ctx={"regime_mode": "SELECTIVE", "rs": 60, "entry": 100, "stop": 98, "final_qty": 5},
        ticks={"wait_after_open": True, "no_chase_huge_gap": True, "no_averaging_down": True, "live_stop_order": True},
    )
    wait = next(i for i in out["items"] if i["id"] == "wait_after_open")
    assert wait["state"] == "PASS"
