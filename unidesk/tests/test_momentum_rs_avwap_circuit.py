"""RS / AVWAP / circuit tests: hand-computed expectations, point-in-time
universe semantics, honest missing-data states."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.features.avwap import avwap, typical_price
from unidesk.momentum.features.circuit import CircuitRiskState, circuit_risk_state
from unidesk.momentum.features.rs import (
    percentile_rank, rs_excess, rs_snapshot, window_return,
)


# ------------------------------------------------------------------ RS core


def test_window_return_hand_computed_and_warmup():
    out = window_return([100.0, 110.0, 121.0], n=2)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(21.0)   # (121/100 - 1) * 100


def test_rs_excess_is_signed_and_none_safe():
    assert rs_excess(10.0, 2.5) == pytest.approx(7.5)
    assert rs_excess(-4.0, -1.0) == pytest.approx(-3.0)
    assert rs_excess(None, 2.0) is None
    assert rs_excess(2.0, None) is None


def test_percentile_rank_midrank_on_ties():
    assert percentile_rank([1.0, 2.0, 3.0, 4.0], 3.0) == pytest.approx(62.5)  # (2+0.5)/4
    assert percentile_rank([1.0, 3.0, 3.0, 3.0], 3.0) == pytest.approx((1 + 1.5) / 4 * 100)


def test_rs_snapshot_full_universe():
    returns = {"NIFTY500": 2.0, "TRENT": 8.0, "DIXON": 5.0, "CAMS": 1.0, "ROUTE": 6.0}
    sector_of = {"NIFTY500": "BENCHMARK", "TRENT": "RETAIL", "DIXON": "RETAIL",
                 "CAMS": "FINANCE", "ROUTE": "RETAIL"}
    r = rs_snapshot("TRENT", returns, sector_of, benchmark="NIFTY500")
    assert r.rs_market == pytest.approx(6.0)
    # RETAIL = TRENT(8), DIXON(5), ROUTE(6): mean 6.333
    assert r.rs_sector == pytest.approx(8.0 - 19.0 / 3.0)
    assert r.sector_vs_market == pytest.approx(19.0 / 3.0 - 2.0)
    # peers = DIXON(5), ROUTE(6), TRENT(8) -> mid-rank of 8 = (2+0.5)/3
    assert r.peer_rank == pytest.approx(83.333, rel=1e-3)
    assert r.peer_count == 2
    # universe returns [2,8,5,1,6] -> mid-rank of 8 = (4+0.5)/5
    assert r.rs_rank == pytest.approx(90.0)
    assert r.reasons == ()


def test_rs_snapshot_missing_sector_disables_not_falls_back():
    returns = {"NIFTY500": 2.0, "TRENT": 8.0}
    r = rs_snapshot("TRENT", returns, {}, benchmark="NIFTY500")
    assert r.rs_market == pytest.approx(6.0)     # market comparison still works
    assert r.rs_sector is None and r.peer_rank is None
    assert "NO_SECTOR_MEMBERSHIP" in r.reasons


def test_rs_snapshot_symbol_missing_from_universe_fails():
    with pytest.raises(ContractError):
        rs_snapshot("TRENT", {"NIFTY500": 1.0}, {}, benchmark="NIFTY500")


# ------------------------------------------------------------------ AVWAP


def test_typical_price_and_validation():
    tp = typical_price([12.0], [10.0], [11.0])
    assert tp == [11.0]
    with pytest.raises(ContractError):
        typical_price([9.0], [10.0], [11.0])   # low above high


def test_avwap_hand_computed_from_anchor():
    # constant 10x1000 volume for 3 bars, then a 12x1000 bar
    tp = [10.0, 10.0, 12.0]
    vol = [1000.0, 1000.0, 1000.0]
    out = avwap(tp, vol, anchor_index=0)
    assert out[0] == 10.0
    assert out[1] == 10.0
    assert out[2] == pytest.approx((10 + 10 + 12) / 3)


def test_avwap_anchor_cuts_history():
    tp = [50.0, 10.0, 10.0]
    vol = [99999.0, 1000.0, 1000.0]
    out = avwap(tp, vol, anchor_index=1)       # anchor excludes the 50 bar entirely
    assert out[0] is None
    assert out[1] == 10.0
    assert out[2] == 10.0


def test_avwap_zero_cumulative_volume_is_none():
    out = avwap([10.0, 11.0], [0.0, 0.0], anchor_index=0)
    assert out == [None, None]


def test_avwap_rejects_out_of_range_anchor():
    with pytest.raises(ContractError):
        avwap([10.0], [100.0], anchor_index=5)


# ------------------------------------------------------------------ circuit


def test_circuit_risk_states():
    # proximity is BAND-relative: 2% of the 20-point band = 0.4 from the edge
    st, why = circuit_risk_state(close=99.7, upper_circuit=100.0, lower_circuit=80.0, proximity_pct=2.0)
    assert st is CircuitRiskState.UC_RISK and "near_upper_circuit" in why
    st, why = circuit_risk_state(close=99.5, upper_circuit=100.0, lower_circuit=80.0, proximity_pct=2.0)
    assert st is CircuitRiskState.NONE and why == ()   # 0.5 from the edge > 0.4 proximity
    st, why = circuit_risk_state(close=80.3, upper_circuit=100.0, lower_circuit=80.0, proximity_pct=2.0)
    assert st is CircuitRiskState.LC_RISK and "near_lower_circuit" in why
    st, why = circuit_risk_state(close=90.0, upper_circuit=100.0, lower_circuit=80.0, proximity_pct=2.0)
    assert st is CircuitRiskState.NONE and why == ()
    st, why = circuit_risk_state(close=90.0, upper_circuit=None, lower_circuit=None)
    assert st is CircuitRiskState.UNKNOWN
    assert why == ("CIRCUIT_BANDS_NOT_PUBLISHED",)


def test_circuit_band_inversion_rejected():
    with pytest.raises(ContractError):
        circuit_risk_state(close=90.0, upper_circuit=80.0, lower_circuit=100.0)
