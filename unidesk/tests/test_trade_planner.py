"""N-43 — Trade Planner: hand-calculation reproduced exactly, binding
constraint displayed, four risk fields distinct."""
from __future__ import annotations

import pytest

from unidesk.research.trade_planner import PlannerInputs, plan_trade


def test_hand_calculation_reproduced_exactly():
    """₹50,000 equity · 0.5% risk · entry 100 · stop 95 → risk/share 5,
    risk_budget 250, qty = 50. Position = ₹5,000 = 10% of equity."""
    inputs = PlannerInputs("TEST", entry=100.0, stop=95.0, risk_fraction_pct=0.5,
                           equity=50_000, max_position_pct=40)
    out = plan_trade(inputs)
    assert out.qty == 50
    assert out.planned_risk == 250.0
    assert out.planned_risk_pct == 0.5
    assert out.position_value == 5000.0
    assert out.position_pct_of_equity == 10.0
    assert out.risk_per_share == 5.0


def test_binding_constraint_is_named():
    inputs = PlannerInputs("TEST", entry=100.0, stop=95.0, risk_fraction_pct=0.5,
                           equity=50_000, max_position_pct=5)  # tight cap
    out = plan_trade(inputs)
    assert out.qty < 50
    assert "position cap" in out.binding_constraint


def test_open_risk_ceiling_binds():
    inputs = PlannerInputs("TEST", entry=100.0, stop=95.0, risk_fraction_pct=0.5,
                           equity=50_000, max_position_pct=40,
                           open_risk_total=200.0, open_risk_ceiling_pct=0.6)
    out = plan_trade(inputs)
    # ceiling = 50_000 * 0.006 = 300; remaining = 300 - 200 = 100; qty = 100/5 = 20
    assert out.qty == 20
    assert out.open_risk_after == 300.0
    assert "open-risk ceiling" in out.binding_constraint


def test_zero_size_when_ceiling_already_breached():
    inputs = PlannerInputs("TEST", entry=100.0, stop=95.0, risk_fraction_pct=0.5,
                           equity=50_000, max_position_pct=40,
                           open_risk_total=350.0, open_risk_ceiling_pct=0.6)
    out = plan_trade(inputs)
    assert out.qty == 0
    assert "open-risk ceiling" in out.binding_constraint


def test_removing_risk_fraction_makes_output_zero():
    """X-03 amendment acceptance (c): removing the owner's risk-fraction
    input makes every size output disappear — never a fallback default."""
    inputs = PlannerInputs("TEST", entry=100.0, stop=95.0, risk_fraction_pct=0.0,
                           equity=50_000, max_position_pct=40)
    out = plan_trade(inputs)
    assert out.qty == 0
    assert out.planned_risk == 0.0


def test_inverted_stop_warns():
    inputs = PlannerInputs("TEST", entry=95.0, stop=100.0, risk_fraction_pct=0.5,
                           equity=50_000, max_position_pct=40)
    out = plan_trade(inputs)
    assert any("inverted" in w.lower() for w in out.warnings)
