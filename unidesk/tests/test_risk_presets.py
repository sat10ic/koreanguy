"""N-42 — SOURCE_PRESET registry: provenance on every threshold, never a
silent default. The owner-approved values and the source-spec values coexist
— the planner picks from OWNER_PRESETS; SOURCE_SPEC_PRESETS are recorded for
comparison (some locally falsified, marked as such)."""
from __future__ import annotations

from unidesk.research.risk_presets import (
    OWNER_PRESETS, SOURCE_SPEC_PRESETS, SUGGESTED_PRESETS, SourcePreset,
)


def test_owner_presets_present_and_attributed():
    by_name = {p.name: p for p in OWNER_PRESETS}
    assert by_name["risk_fraction"].value == 0.5
    assert by_name["risk_fraction"].source.startswith("owner")
    assert by_name["equity"].value == 50000
    assert by_name["max_position_pct"].value == 40.0


def test_suggested_presets_present_for_governor():
    by_name = {p.name: p for p in SUGGESTED_PRESETS}
    assert "open_risk_ceiling" in by_name
    assert "dynamic" in by_name["open_risk_ceiling"].period


def test_source_spec_presets_carry_falsification_note():
    by_name = {p.name: p for p in SOURCE_SPEC_PRESETS}
    assert "locally falsified" in by_name["stop_width_ep_low"].source or \
           "locally falsified" in by_name["stop_width_ep_low"].strategy_context
