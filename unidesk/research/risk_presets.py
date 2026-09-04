"""Risk Desk P0 freeze (N-42) — risk ontology, objective enums, policy config,
and the SOURCE_PRESET registry. Every threshold carries its source, period and
strategy context — never a silent default (standing rule 4 / spec §2.3).

OWNER-APPROVED VALUES (BUILD_QUESTIONS batch 1, Q2/Q3/Q7):
  equity = ₹50,000 · MTF = no · risk_fraction = 0.5% · max_position = 40%
  open_risk_ceiling = TOOL-SUGGESTED per regime/breadth (no fixed number)

The values are stored as SOURCE_PRESET entries so they are editable — the
presets ship with provenance, not as hardcoded globals.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Objective(Enum):
    """What the trade is trying to achieve — determines which quality filters
    apply and how the position is managed after entry."""
    VELOCITY = "velocity"         # fast EP-type: quick momentum burst
    MAGNITUDE = "magnitude"       # sustained base breakout: multi-week run
    HYBRID = "hybrid"             # velocity entry with magnitude management
    PERSISTENT = "persistent"     # slow accumulation: regime-riding


class StopCandidateType(Enum):
    """Where a stop can come from. Ranked by preference at plan time."""
    STRUCTURAL_BELOW = "structural_below"       # nearest level below entry
    PRE_GAP_LOW = "pre_gap_low"                 # EP: the gap-day low
    LISTING_DAY_LOW = "listing_day_low"         # IPO: day-0 low
    ATR_MULTIPLE = "atr_multiple"               # fixed ATR multiple
    PERCENT_FIXED = "percent_fixed"             # fixed % below entry


@dataclass(frozen=True)
class SourcePreset:
    """A threshold that came from a named source with a stated period and
    strategy context. Never a silent default. Editable by the owner."""
    name: str
    value: float
    unit: str                       # "percent" | "rupees" | "sessions" | "ATR"
    source: str                     # where the number came from
    period: str                     # what regime/market it was calibrated on
    strategy_context: str           # which strategy it serves


# --- the owner-approved presets (BUILD_QUESTIONS batch 1, Q2/Q3/Q7) ---
OWNER_PRESETS = [
    SourcePreset("risk_fraction", 0.5, "percent",
                 "owner (BUILD_QUESTIONS batch 1 Q2a)", "FY25-26 delivery",
                 "per-trade planned risk"),
    SourcePreset("max_position_pct", 40.0, "percent",
                 "owner (BUILD_QUESTIONS batch 1 Q2a)", "FY25-26 delivery",
                 "maximum single-position size as % of capital"),
    SourcePreset("equity", 50000, "rupees",
                 "owner (BUILD_QUESTIONS batch 1 Q7a)", "current",
                 "trading capital; MTF not in use"),
]

# --- the tool-SUGGESTED presets (owner Q3c: suggested per regime/breadth,
#     never a fixed number). The Governor proposes these; the owner confirms. ---
SUGGESTED_PRESETS = [
    SourcePreset("open_risk_ceiling", 2.0, "percent",
                 "tool-suggested per regime/breadth", "dynamic",
                 "max total open risk; narrower in CHOP/RISK-OFF, wider in BULL"),
    SourcePreset("risk_fraction_dynamic", 0.5, "percent",
                 "tool-suggested per regime/breadth", "dynamic",
                 "risk fraction narrows in CHOP/RISK-OFF; base 0.5% in BULL"),
]

# --- source-spec thresholds stored as SOURCE_PRESET entries (never silent
#     defaults; the spec's §2.3 values, attributed and editable) ---
SOURCE_SPEC_PRESETS = [
    SourcePreset("risk_per_trade_low", 0.3, "percent",
                 "practitioner spec §2.3", "trending markets",
                 "aggressive risk when conviction is high"),
    SourcePreset("risk_per_trade_high", 0.5, "percent",
                 "practitioner spec §2.3", "trending markets",
                 "standard risk when conviction is normal"),
    SourcePreset("stop_width_ep_low", 1.5, "percent",
                 "practitioner spec §13.2", "EP Day-0 entry",
                 "NOTE: locally falsified — median stop_thrust_days 0.67 is already tighter; "
                 "spec assumed intraday management. Kept for reference only."),
    SourcePreset("stop_width_ipo_low", 4.0, "percent",
                 "practitioner spec §53.1", "IPO base entries",
                 "NOTE: same local-falsification caveat as EP stop width"),
    SourcePreset("max_position_alt", 40.0, "percent",
                 "practitioner spec §23", "position sizing",
                 "maximum single-position size as % of capital"),
    SourcePreset("partial_exit_at_4R", 4.0, "R",
                 "practitioner spec §15", "EP management",
                 "partial profit-taking at 4R"),
]
