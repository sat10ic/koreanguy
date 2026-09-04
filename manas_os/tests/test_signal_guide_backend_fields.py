"""HANDOFF_GEMINI_backend_fields_batch — rupee_risk + management_contract."""
from __future__ import annotations

from manas_os.agents import signal_guide


def test_compute_rupee_risk_basic():
    assert signal_guide.compute_rupee_risk(100, 200.0, 190.0) == 1000.0
    assert signal_guide.compute_rupee_risk(0, 200.0, 190.0) == 0.0
    assert signal_guide.compute_rupee_risk(None, 200.0, 190.0) is None
    assert signal_guide.compute_rupee_risk(10, None, 190.0) is None


def test_management_contract_ep_has_cite_and_trail():
    steps = signal_guide.build_guide({"setup_type": "ep"}, "ep", {"entry": 100, "stop": 95, "final_qty": 10}, None, sizer={"final_qty": 10, "multiplier": 1.0})
    mc = signal_guide.build_management_contract({"setup_type": "ep"}, "ep", steps)
    assert mc["trade_type"] == "magnitude"
    assert "trail" in mc["trail_rule"].lower() or "EMA" in mc["trail_rule"] or "DMA" in mc["trail_rule"]
    assert mc["source_cite"]
    assert isinstance(mc["normal_behaviour"], list) and len(mc["normal_behaviour"]) >= 1


def test_management_contract_prefers_step_trail_language():
    steps = [
        {
            "n": 7,
            "title": "Know your exit line",
            "instruction": "CUSTOM TRAIL LANGUAGE from step.",
            "check": "x",
            "source_cite": "design/agents/LENS_EP.md §5",
        }
    ]
    mc = signal_guide.build_management_contract({"setup_type": "ep"}, "ep", steps)
    assert mc["trail_rule"] == "CUSTOM TRAIL LANGUAGE from step."
    assert "LENS_EP" in mc["source_cite"]


def test_focus_catalyst_helper_matches_ep_variants():
    # Mirror the helper logic used in app.desk_focus (kept local to avoid importing FastAPI app).
    def _is_focus_catalyst(c: dict) -> bool:
        st = str(c.get("setup_type") or "").lower()
        if st in {"ep", "ipo_base"}:
            return True
        blob = " ".join(str(c.get(k) or "") for k in ("setup", "setup_family", "pattern_label")).lower()
        return (
            st.startswith("ep")
            or "ipo" in st
            or "earnings" in blob
            or ("catalyst" in blob and ("ep" in blob or "ipo" in blob))
        )

    assert _is_focus_catalyst({"setup_type": "ep"})
    assert _is_focus_catalyst({"setup_type": "ipo_base"})
    assert _is_focus_catalyst({"setup_type": "ep_ipo", "setup": "ep_ipo"})
    assert _is_focus_catalyst({"setup_type": "pullback", "setup_family": "catalyst", "pattern_label": "EP base"})
    assert not _is_focus_catalyst({"setup_type": "pocket_pivot", "setup_family": "momentum"})
