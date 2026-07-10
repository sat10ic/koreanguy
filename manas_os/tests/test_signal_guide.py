from manas_os.agents import signal_guide


def _plan(entry=100.0, stop=95.0, target=115.0, qty=10):
    return {"entry": entry, "stop": stop, "target": target, "rr": 3.0, "suggested_qty": qty}


def test_ep_guide_has_skip_and_day0_steps_with_cites():
    steps = signal_guide.build_guide({"setup_type": "ep"}, "catalyst", _plan(), "SELECTIVE")
    assert len(steps) >= 6
    for step in steps:
        assert step["n"] and step["title"] and step["instruction"] and step["check"] and step["source_cite"]

    skip_step = next(s for s in steps if "12%" in s["instruction"])
    assert "LENS_EP.md" in skip_step["source_cite"]

    day0_step = next(s for s in steps if "risk-free" in s["instruction"].lower() and "day" in s["title"].lower())
    assert "W23" in day0_step["source_cite"]

    sizing_step = next(s for s in steps if "provisional" in s["instruction"].lower())
    assert "W11" in sizing_step["source_cite"]

    # Actual plan numbers land in the text, not just placeholders.
    assert any("100" in s["instruction"] for s in steps)
    assert any("95" in s["instruction"] for s in steps)


def test_strong_start_guide_has_3min_and_gap_cap():
    steps = signal_guide.build_guide({"setup_type": "pullback", "pattern_label": "Strong Start"}, "momentum", _plan(50, 47), None)
    wait_step = next(s for s in steps if "2-3 minute" in s["instruction"])
    assert "LENS_STRONG_START.md" in wait_step["source_cite"]
    gap_step = next(s for s in steps if "5-6%" in s["instruction"])
    assert gap_step is not None


def test_d2_guide_routes_and_has_branch_and_orb_steps():
    steps = signal_guide.build_guide({"setup_type": "d2_ready"}, "momentum", _plan(120, 118), None)
    assert signal_guide.guide_family_label({"setup_type": "d2_ready"}, None) == "d2"
    branch_step = next(s for s in steps if "three" in s["instruction"].lower() or "branch" in s["title"].lower())
    assert branch_step is not None
    orb_step = next(s for s in steps if "opening-range" in s["instruction"].lower())
    assert "TRADETM_NUANCES_COMPLETION.md" in orb_step["source_cite"]


def test_ipo_guide_has_inside_bar_and_wide_stop_steps():
    steps = signal_guide.build_guide({"setup_type": "ipo_base"}, "catalyst", _plan(200, 190), "RISK_ON")
    inside_bar_step = next(s for s in steps if "inside bar" in s["instruction"].lower())
    assert "LENS_IPO.md" in inside_bar_step["source_cite"]
    wide_stop_step = next(s for s in steps if "TIGHT" in s["instruction"])
    assert wide_stop_step is not None


def test_generic_guide_used_for_unmatched_family():
    steps = signal_guide.build_guide({"setup_type": "pocket_pivot"}, "momentum", _plan(), None)
    assert len(steps) >= 4
    assert any("pullback" in (s["instruction"] + s["title"]).lower() for s in steps)


def test_unsized_plan_gets_honest_placeholder_not_fake_numbers():
    steps = signal_guide.build_guide({"setup_type": "ep", "near_miss": {"reason": "gap 14%"}}, "catalyst", None, "SELECTIVE")
    assert len(steps) == 1
    assert "debate-only" in steps[0]["instruction"]
    assert "gap 14%" in steps[0]["instruction"]


def test_missing_plan_dict_also_treated_as_unsized():
    steps = signal_guide.build_guide({"setup_type": "ipo_base"}, "catalyst", {}, None)
    assert len(steps) == 1
    assert "debate-only" in steps[0]["instruction"]


def test_lens_key_prefers_specific_setup_type_over_coarse_family():
    assert signal_guide.guide_family_label({"setup_type": "ep"}, "catalyst") == "ep"
    assert signal_guide.guide_family_label({"setup_type": "ipo_base"}, "catalyst") == "ipo_base"
    assert signal_guide.guide_family_label({"setup_type": "shakeout"}, "momentum") == "generic"


# Trust-fix regression: sizer has final authority over sizing (final_qty),
# never plan.suggested_qty. A card where the plan's stale base qty was 439
# but the sizer refused (final_qty=0) must never surface "439" anywhere in
# the guide, and must lead with a live-order refusal step 0.
def test_sizer_zero_final_qty_injects_refusal_step_and_never_uses_stale_base_qty():
    plan = {"entry": 100.0, "stop": 95.0, "target": 115.0, "rr": 3.0,
            "suggested_qty": 439, "final_qty": 0}
    sizer = {"multiplier": 0, "final_qty": 0, "reasoning": "risk quality too weak tonight"}
    steps = signal_guide.build_guide({"setup_type": "ep"}, "catalyst", plan, "SELECTIVE", sizer=sizer)

    assert steps[0]["n"] == 0
    assert "do not place a live order" in steps[0]["title"].lower()
    assert "paper-trade" in steps[0]["instruction"].lower()
    assert "risk quality too weak tonight" in steps[0]["instruction"]

    for step in steps:
        assert "439" not in step["instruction"]
        assert "439" not in step["check"]

    qty_step = next(s for s in steps if s["n"] != 0 and "final qty (sizer)" in s["instruction"].lower())
    assert "final qty (sizer): 0" in qty_step["instruction"].lower()


def test_sizer_nonzero_final_qty_used_in_place_of_suggested_qty():
    plan = {"entry": 100.0, "stop": 95.0, "target": 115.0, "rr": 3.0,
            "suggested_qty": 439, "final_qty": 220}
    sizer = {"multiplier": 0.5, "final_qty": 220, "reasoning": "half size, weak conviction"}
    steps = signal_guide.build_guide({"setup_type": "ep"}, "catalyst", plan, "SELECTIVE", sizer=sizer)

    assert all(s["n"] != 0 for s in steps)
    qty_step = next(s for s in steps if "final qty" in s["instruction"].lower())
    assert "final qty (sizer): 220" in qty_step["instruction"].lower()
    for step in steps:
        assert "439" not in step["instruction"]
