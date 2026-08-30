"""Unified P0.2 acceptance tests for the shared desk contracts.

Acceptance boxes (build manual P0.2): unknown enum values fail validation;
nulls remain null; `as_of` is required (and tz-aware) for every time-sensitive
snapshot; version/hash fields are mandatory where specified; same serialized
input produces stable schema output. Plus: OrderFlowAssessment ties to the
orderflow capability.json shape, and cross-contract hard gates hold.
"""
from datetime import datetime, timezone

import pytest

from unidesk.contracts import (
    ContractError,
    DecisionSnapshot,
    FlowDecision,
    FlowState,
    LiquidityState,
    OrderFlowAssessment,
    PolicyState,
    SetupCandidate,
    SetupType,
    DetectionState,
    Timeframe,
    IntradayBar,
    from_dict,
    to_dict,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 4, 15, 0, tzinfo=UTC)
T1 = datetime(2026, 8, 28, 4, 15, 30, tzinfo=UTC)


def make_assessment(**over):
    base = dict(
        assessment_id="as-1",
        candidate_id="cand-1",
        symbol="NSE:ABC-EQ",
        assessed_at=T0,
        valid_until=T1,
        feed_health="HEALTHY",
        capability_version="1",
        liquidity_score=72.0,
        liquidity_state="PASS",
        capacity_band="MODERATE",
        high_impact_band="HIGH",
        raw_flow_score=64.0,
        flow_confidence=0.78,
        effective_flow_score=49.9,
        flow_state="CONFIRMING",
        decision="CONFIRM",
        reason_codes=("spread_stable", "price_response_positive"),
        feature_snapshot_id="feat-1",
        flow_config_hash="cfg-abc123",
    )
    base.update(over)
    return OrderFlowAssessment(**base)


# ------------------------------------------------- unknown enum values fail


def test_unknown_enum_values_fail_closed():
    with pytest.raises(ContractError):
        make_assessment(flow_state="SUPER_BULLISH")
    with pytest.raises(ContractError):
        make_assessment(decision="BUY_IT")
    with pytest.raises(ContractError):
        make_assessment(liquidity_state="SORT_OF")


def test_intraday_bar_unknown_timeframe_fails():
    with pytest.raises(ContractError):
        IntradayBar(
            symbol="NSE:A-EQ", ts=T0, timeframe="7m",
            open=1, high=2, low=0.5, close=1.5, volume=10,
            data_version="v1",
        )


def test_enum_instances_and_strings_both_accepted():
    a = make_assessment(flow_state=FlowState.CONFIRMING)
    b = make_assessment(flow_state="CONFIRMING")
    assert a.flow_state is FlowState.CONFIRMING and b.flow_state is FlowState.CONFIRMING
    assert to_dict(a) == to_dict(b)


# ------------------------------------------------- nulls remain null


def test_nulls_stay_null_and_are_never_zero():
    a = make_assessment(liquidity_score=None, flow_confidence=None, capacity_band=None)
    d = to_dict(a)
    assert d["liquidity_score"] is None
    assert d["flow_confidence"] is None
    assert d["capacity_band"] is None


def test_null_reason_field_stays_null_not_empty_string():
    a = make_assessment(feature_snapshot_id=None)
    assert to_dict(a)["feature_snapshot_id"] is None


# ------------------------------------------------- as_of / timestamps


def test_naive_timestamps_rejected():
    naive = datetime(2026, 8, 28, 9, 45)  # no tzinfo
    with pytest.raises(ContractError):
        make_assessment(assessed_at=naive)
    with pytest.raises(ContractError):
        make_assessment(valid_until=naive)


def test_valid_until_must_not_precede_assessed_at():
    with pytest.raises(ContractError):
        make_assessment(assessed_at=T1, valid_until=T0)


# ------------------------------------------------- versions / hashes mandatory


@pytest.mark.parametrize("field", ["capability_version", "flow_config_hash"])
def test_version_and_hash_fields_mandatory(field):
    with pytest.raises(ContractError):
        make_assessment(**{field: ""})


def test_mandatory_versions_on_contracts():
    with pytest.raises(ContractError):
        SetupCandidate(
            setup_id="s-1", symbol="NSE:A-EQ", detected_at=T0,
            setup_type=SetupType.PULLBACK, geometry_version="",
            pivot_price=100, trigger_price=101, structural_low=95,
            setup_start=datetime(2026, 8, 1, tzinfo=UTC).date(),
            setup_age_sessions=12, base_depth_pct=None, contraction_ratio=None,
            rest_depth_atr=None, volume_dryup_ratio=None, gap_pct=None,
            breakout_rvol=None, distance_from_pivot_pct=None,
            deterministic_valid=DetectionState.VALID, rule_failures=(),
            setup_quality_score=80.0,
        )


# ------------------------------------------------- stable serialization


def test_same_input_produces_identical_serialization():
    d1 = to_dict(make_assessment())
    d2 = to_dict(make_assessment())
    assert d1 == d2
    assert list(d1.keys()) == list(d2.keys())
    assert d1["assessed_at"] == "2026-08-28T04:15:00+00:00"


def test_round_trip_through_dict():
    a = make_assessment()
    assert from_dict(OrderFlowAssessment, to_dict(a)) == a


def test_round_trip_rejects_unknown_keys():
    d = to_dict(make_assessment())
    d["invented_field"] = 1
    with pytest.raises(ContractError):
        from_dict(OrderFlowAssessment, d)


# ------------------------------------------------- orderflow tie-in


def test_capability_version_accepts_orderflow_capability_json_shape():
    import json
    from pathlib import Path

    cap_path = Path(__file__).resolve().parents[2] / "orderflow" / "capability.json"
    schema_version = 1
    if cap_path.exists():
        schema_version = json.loads(cap_path.read_text(encoding="utf-8"))["schema_version"]
    a = make_assessment(capability_version=str(schema_version))
    assert a.capability_version == str(schema_version)


# ------------------------------------------------- hard gates across contracts


def test_liquidity_reject_hard_vetoes():
    with pytest.raises(ContractError):
        make_assessment(liquidity_state="REJECT", decision="CONFIRM")
    a = make_assessment(liquidity_state="REJECT", decision="VETO",
                        flow_state="BREAKOUT_RISK")
    assert a.decision is FlowDecision.VETO


def test_confirm_cannot_rest_on_unknown_flow_state():
    with pytest.raises(ContractError):
        make_assessment(flow_state="UNKNOWN", decision="CONFIRM")
    make_assessment(flow_state="UNKNOWN", decision="UNKNOWN")  # legal


def test_invalid_setup_cannot_carry_quality_score():
    with pytest.raises(ContractError):
        SetupCandidate(
            setup_id="s-1", symbol="NSE:A-EQ", detected_at=T0,
            setup_type=SetupType.BASE_BREAKOUT, geometry_version="g1",
            pivot_price=100, trigger_price=101, structural_low=95,
            setup_start=datetime(2026, 8, 1, tzinfo=UTC).date(),
            setup_age_sessions=10, base_depth_pct=None, contraction_ratio=None,
            rest_depth_atr=None, volume_dryup_ratio=None, gap_pct=None,
            breakout_rvol=None, distance_from_pivot_pct=None,
            deterministic_valid=DetectionState.INVALID, rule_failures=("no_base",),
            setup_quality_score=88.0,
        )


def test_decision_snapshot_policy_consistency():
    from unidesk.contracts import ConfluenceGrade

    def snap(**over):
        base = dict(
            decision_id="d-1", candidate_id="cand-1", as_of=T0,
            stock_quality=92.0, setup_quality=88.0, entry_quality=54.0,
            liquidity_state="PASS", flow_state="MIXED", flow_confidence=0.6,
            social_context_state="3_traders_discussing",
            judge_grade=ConfluenceGrade.B, policy_state="WARN",
            hard_gates=(), warnings=("room_to_move_thin",),
            unknowns=("delivery_unavailable_today",),
            source_snapshot_ids=("snap-1", "geo-1", "flow-1"),
            config_hash="cfg-1", policy_version="pol-1",
        )
        base.update(over)
        return DecisionSnapshot(**base)

    assert snap().policy_state is PolicyState.WARN
    with pytest.raises(ContractError):
        snap(liquidity_state="REJECT", policy_state="ELIGIBLE")
