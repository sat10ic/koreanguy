"""Conservative cash-delivery cost model (swing-edges spec §1.4 / Phase 0).

Net is the only number that can accept a strategy (R-J). Thresholds are
frozen in ``CostAssumptions`` (R14); they are not buried in call sites.
Impact is per-side and capped; gap-entry slippage is an additive T5 Day-1
haircut, not a silent extra in every trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from unidesk.contracts.base import ContractError, require_float


COSTS_VERSION = "costs-v1-spec-1.4"


@dataclass(frozen=True)
class CostAssumptions:
    brokerage_gst_rt_bps: float = 15.0      # conservative end of 6–15
    stt_rt_bps: float = 20.0                 # conservative RT
    exchange_sebi_stamp_rt_bps: float = 5.0  # conservative end of 3–5
    impact_cap_bps_side: float = 15.0
    impact_coef_bps: float = 8.0             # 8 bps * (order/ADV) per side
    gap_slippage_bps: float = 25.0           # conservative T5 Day-1 extra
    version: str = COSTS_VERSION


@dataclass(frozen=True)
class CostBreakdown:
    brokerage_gst_rt_bps: float
    stt_rt_bps: float
    exchange_rt_bps: float
    impact_rt_bps: float
    gap_slippage_bps: float
    total_rt_bps: float
    assumptions_version: str


def impact_bps_one_side(order_value: float, adv_value: float,
                        assumptions: CostAssumptions = CostAssumptions()) -> float:
    """``min(cap, coef * order/ADV)`` per side. Undefined ADV fails closed."""
    order_value = require_float(order_value, "order_value")
    adv_value = require_float(adv_value, "adv_value")
    if order_value < 0:
        raise ContractError("order_value must be >= 0")
    if adv_value <= 0:
        raise ContractError("adv_value must be positive (R12: missing ADV is not infinite liquidity)")
    raw = assumptions.impact_coef_bps * (order_value / adv_value)
    return min(assumptions.impact_cap_bps_side, raw)


def round_trip_cost(
    *,
    order_value: float,
    adv_value: float,
    gap_entry: bool = False,
    assumptions: CostAssumptions = CostAssumptions(),
) -> CostBreakdown:
    """All-in round-trip cost in bps of notional."""
    impact_side = impact_bps_one_side(order_value, adv_value, assumptions)
    impact_rt = 2.0 * impact_side
    gap = assumptions.gap_slippage_bps if gap_entry else 0.0
    total = (
        assumptions.brokerage_gst_rt_bps
        + assumptions.stt_rt_bps
        + assumptions.exchange_sebi_stamp_rt_bps
        + impact_rt
        + gap
    )
    return CostBreakdown(
        brokerage_gst_rt_bps=assumptions.brokerage_gst_rt_bps,
        stt_rt_bps=assumptions.stt_rt_bps,
        exchange_rt_bps=assumptions.exchange_sebi_stamp_rt_bps,
        impact_rt_bps=impact_rt,
        gap_slippage_bps=gap,
        total_rt_bps=total,
        assumptions_version=assumptions.version,
    )


def net_return_bps(gross_return_bps: float, cost: CostBreakdown) -> float:
    """Gross minus round-trip cost. Net is the only accept/reject number."""
    gross_return_bps = require_float(gross_return_bps, "gross_return_bps")
    return gross_return_bps - cost.total_rt_bps
