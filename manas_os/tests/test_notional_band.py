"""Tests for the CONSERVATIVE notional-band layer in risk/plan.py (external UX
audit "Confetti sizing" FAIL).

risk/plan.py is the single sizing writer; this layer only nudges qty UP
toward TARGET_NOTIONAL_MIN (Rs 10,000) when doing so still clears the
profile's own per-trade risk ceiling (hard_max) and the portfolio open-risk
cap -- it never trims qty down, never exceeds an existing cap, and never
turns a passing trade into a refusal by itself.

All fixtures below are hand-computed (not asserted against the code's own
arithmetic) so they catch regressions in the sizing math itself.
"""
from manas_os.risk import plan as rp


def test_notional_band_in_band_is_untouched():
    # aggressive RISK_ON: base 0.75% * 100,000 capital = 750 rupee budget;
    # stop distance 5 -> qty = floor(750/5) = 150 -> notional = 15,000, which
    # already sits inside [10,000, 20,000] -- no adjustment should fire.
    r = rp.validate(entry=100.0, stop=95.0, measured_move=110.0, regime="RISK_ON",
                    profile="aggressive", account_capital=100000.0)
    assert r["pass"]
    assert r["qty"] == 150
    assert r["rupee_risk"] == 750.0
    assert r["notional"] == 15000.0
    assert r["notional_band"] == "in"
    assert r["band_note"] is None
    assert r["reasons"] == []


def test_notional_band_above_band_is_informational_only_no_trim():
    # Same shape as test_validate_aggressive_profile_qty_math (10-lakh
    # capital): qty = 1500, notional = 150,000 -- far above the 20,000
    # ceiling. Band is "above" but qty/rupee_risk are UNCHANGED (no trim
    # behavior this wave) and no refusal is created.
    r = rp.validate(entry=100.0, stop=95.0, measured_move=110.0, regime="RISK_ON",
                    profile="aggressive", account_capital=1_000_000.0)
    assert r["pass"]
    assert r["qty"] == 1500
    assert r["rupee_risk"] == 7500.0
    assert r["notional"] == 150000.0
    assert r["notional_band"] == "above"
    assert r["band_note"] is not None and "informational only" in r["band_note"]
    assert r["reasons"] == []  # above-band note never lands in reasons


def test_notional_band_below_band_achievable_sizes_up_to_min_notional():
    # standard RISK_ON: base 0.50% * 30,000 capital = 150 rupee budget; stop
    # distance 2 -> qty0 = floor(150/2) = 75 -> notional0 = 7,500 (below the
    # 10k floor). Sizing to the floor: qty_up = ceil(10000/100) = 100 ->
    # rupee_risk_up = 100*2 = 200 -> risk_pct_up = 200/30000*100 = 0.6667%,
    # which is <= the standard RISK_ON hard_max of 0.75% -- adopt.
    r = rp.validate(entry=100.0, stop=98.0, measured_move=110.0, regime="RISK_ON",
                    profile="standard", account_capital=30000.0)
    assert r["pass"]
    assert r["qty"] == 100  # sized UP from the risk-derived 75
    assert r["rupee_risk"] == 200.0
    assert r["risk_pct_used"] == 0.667
    assert r["notional"] == 10000.0
    assert r["notional_band"] == "in"
    assert r["band_note"] is not None and "sized up" in r["band_note"]
    assert r["band_note"] not in r["reasons"]  # achievable path is not a warning


def test_notional_band_below_band_not_achievable_keeps_qty_and_warns():
    # Same capital/profile/entry as the achievable case, but a wider stop
    # (4 instead of 2) means sizing to the floor would need risk_pct_up =
    # 100*4/30000*100 = 1.333%, which EXCEEDS the standard RISK_ON hard_max
    # of 0.75% -- the size-up is refused; risk-derived qty (37) is kept
    # unchanged and a warning is appended (pass stays True; the band never
    # creates a refusal by itself).
    r = rp.validate(entry=100.0, stop=96.0, measured_move=115.0, regime="RISK_ON",
                    profile="standard", account_capital=30000.0)
    assert r["pass"]
    assert r["qty"] == 37  # UNCHANGED risk-derived qty
    assert r["rupee_risk"] == 150.0
    assert r["risk_pct_used"] == 0.5
    assert r["notional"] == 3700.0
    assert r["notional_band"] == "below"
    expected_note = (
        "position Rs 3,700 below the Rs 10k compounding band - stop too "
        "wide to size up within your risk budget; consider skipping"
    )
    assert r["band_note"] == expected_note
    assert expected_note in r["reasons"]  # warning surfaces in reasons/notes


def test_notional_band_size_up_boundary_exactly_at_hard_max_is_adopted():
    # standard RISK_ON, 40,000 capital, stop distance 3.0: qty0 =
    # floor(200/3) = 66 -> notional0 = 6,600 (below floor). Sizing to the
    # floor: qty_up = 100 -> rupee_risk_up = 300 -> risk_pct_up =
    # 300/40000*100 = 0.75% EXACTLY equal to hard_max -- the cap comparison
    # is inclusive (<=), so this boundary case must be adopted, never
    # exceeded.
    r = rp.validate(entry=100.0, stop=97.0, measured_move=110.0, regime="RISK_ON",
                    profile="standard", account_capital=40000.0)
    assert r["pass"]
    assert r["qty"] == 100
    assert r["rupee_risk"] == 300.0
    assert r["risk_pct_used"] == 0.75
    assert r["notional"] == 10000.0
    assert r["notional_band"] == "in"
    assert r["band_note"] is not None and "sized up" in r["band_note"]


def test_notional_band_size_up_boundary_just_over_hard_max_is_rejected():
    # Identical fixture, stop distance nudged to 3.03: risk_pct_up =
    # 100*3.03/40000*100 = 0.7575%, a hair OVER the 0.75% hard_max -- must
    # be rejected (cap never exceeded), keeping the risk-derived qty (66).
    r = rp.validate(entry=100.0, stop=96.97, measured_move=110.0, regime="RISK_ON",
                    profile="standard", account_capital=40000.0)
    assert r["pass"]
    assert r["qty"] == 66  # UNCHANGED -- size-up would have exceeded hard_max
    assert r["notional"] == 6600.0
    assert r["notional_band"] == "below"


def test_notional_band_size_up_rejected_when_open_risk_cap_would_be_exceeded():
    # Same achievable fixture as the sizing-up test (30,000 capital, standard
    # RISK_ON, stop distance 2), but with 1.5% already open. The original
    # pre-check (open_risk + base_risk = 1.5 + 0.50 = 2.0 <= heat_cap 2.0)
    # still passes at the ORIGINAL base_risk, but sizing up to the notional
    # floor would push risk to 0.6667% -- open_risk_after = 1.5 + 0.6667 =
    # 2.1667% > the 2.0% heat_cap -- so the size-up must be rejected even
    # though risk_pct_up alone (0.6667%) is within hard_max (0.75%).
    open_positions = [{"risk_pct": 1.5}]
    r = rp.validate(entry=100.0, stop=98.0, measured_move=110.0, regime="RISK_ON",
                    profile="standard", account_capital=30000.0,
                    open_positions=open_positions)
    assert r["pass"]
    assert r["qty"] == 75  # UNCHANGED -- size-up would have breached open-risk cap
    assert r["notional"] == 7500.0
    assert r["notional_band"] == "below"
    assert "below the Rs 10k compounding band" in r["band_note"]


def test_notional_band_absent_fields_default_none_on_refusal():
    # A refused trade never reaches the notional-band logic; the fields must
    # still be present (contract) but stay None rather than stale/partial.
    r = rp.validate(entry=100, stop=73, measured_move=140, regime="RISK_ON",
                    profile="aggressive", account_capital=1_000_000)
    assert not r["pass"]
    assert r["notional"] is None
    assert r["notional_band"] is None
    assert r["band_note"] is None
