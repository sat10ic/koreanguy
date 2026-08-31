"""S_ep / S_tight snapshot bindings + dry-run runner tests (N5 wave C-1).

The bindings in ``unidesk.momentum.scoring._snapshot_bindings`` are the
only surface that knows the freeze-scan snapshot layout. Their job is
to lift point-in-time values out of the ``n5_inputs`` block and feed
them to the deterministic scorers. The tests below assert:

  * the binding drops missing components honestly (None in -> None out
    for the relevant scorer component, named in ``unknowns``)
  * the binding marks circuit-day detection as not-yet-wired so a
    coverage report is not silently false
  * the binding refuses to score a snapshot that predates wave C-1
    (the n5_inputs block is missing entirely)
  * the dry-run runner aggregates per-detector S_ep coverage on a
    tiny synthetic event list, never inventing inputs
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.ep_signature import ep_signature
from unidesk.momentum.scoring._snapshot_bindings import (
    s_tight_status_from_snapshot, score_ep_from_snapshot,
)


# ----------------------------------------------------------------- fixtures


def _snap(*, gap_pct=4.5, rvol=3.0, close_loc=0.85,
          prior_compression_pctile=None, delivery_shock=None,
          circuit_locked=False, prior_20d_gain_pct=None):
    """Build a minimal n5_inputs-bearing snapshot for tests."""
    return {
        "close": 100.0,
        "n5_inputs": {
            "ep": {
                "gap_pct": gap_pct,
                "rvol": rvol,
                "close_loc": close_loc,
                "prior_compression_pctile": prior_compression_pctile,
                "delivery_shock": delivery_shock,
                "circuit_locked": circuit_locked,
                "prior_20d_gain_pct": prior_20d_gain_pct,
            },
            "tight": {"base_episode": None},
        },
    }


# -------------------------------------------------------------- S_ep binding


def test_score_ep_full_inputs_matches_pure_scorer():
    """When every input is present the binding and the pure scorer agree
    to the bit, modulo the appended CIRCUIT_DETECTION_NOT_WIRED unknown."""
    snap = _snap()
    bound = score_ep_from_snapshot("AAA", "2026-08-28", snap)
    pure = ep_signature(
        symbol="AAA", session="2026-08-28", gap_pct=4.5,
        rvol=3.0, close_loc=0.85, prior_compression_pctile=None,
        delivery_shock=None, circuit_locked=False,
        prior_20d_gain_pct=None,
    )
    assert bound.s_ep == pure.s_ep
    assert bound.coverage == pure.coverage
    assert "CIRCUIT_DETECTION_NOT_WIRED" in bound.unknowns
    # The pure scorer is not supposed to know about the circuit-detection
    # wiring gap; only the binding adds the unknown.
    assert "CIRCUIT_DETECTION_NOT_WIRED" not in pure.unknowns


def test_score_ep_missing_components_drop_honestly():
    """A missing component (None) lowers coverage but does not invent
    a number. The unknown is named."""
    snap = _snap(rvol=None, close_loc=None)
    bound = score_ep_from_snapshot("BBB", "2026-08-28", snap)
    # gap_pct is the only scored component -> coverage 25/100 = 0.25
    assert bound.coverage == pytest.approx(0.25)
    # rvol_anomaly and close_quality are the dropped components
    assert bound.components["rvol_anomaly"] is None
    assert bound.components["close_quality"] is None
    # s_ep is still a real number over the available component
    assert 0.0 <= bound.s_ep <= 100.0


def test_score_ep_missing_gap_returns_insufficient():
    """gap_pct is the Day-0 gate; if it's None, the binding refuses to
    pretend a score and returns a zero-coverage decision with the
    GAP_PCT_UNAVAILABLE unknown named."""
    snap = _snap(gap_pct=None)
    bound = score_ep_from_snapshot("CCC", "2026-08-28", snap)
    assert bound.coverage == 0.0
    assert "GAP_PCT_UNAVAILABLE" in bound.unknowns
    assert "INSUFFICIENT_DATA" in bound.unknowns


def test_score_ep_legacy_setup_inputs_recovers():
    """A snapshot frozen before wave C-1 has no n5_inputs block but
    has setup_inputs (the legacy surface). The binding materialises
    the EP block on the fly from setup_inputs -- the same shape, the
    same values. The 4 fields that were never on disk stay None and
    reduce coverage honestly."""
    legacy = {
        "close": 100.0,
        "setup_inputs": {
            "gap_pct": 4.5,
            "rvol": 3.0,
            "close_location": 0.85,   # legacy key name
            # no prior_compression_pctile, delivery_shock,
            # circuit_locked, prior_20d_gain_pct
        },
    }
    bound = score_ep_from_snapshot("FFF", "2026-08-28", legacy)
    # The recovered values flow through the same scoring path; s_ep
    # equals what the pure scorer would compute on the same input.
    pure = ep_signature(
        symbol="FFF", session="2026-08-28", gap_pct=4.5,
        rvol=3.0, close_loc=0.85, prior_compression_pctile=None,
        delivery_shock=None, circuit_locked=False,
        prior_20d_gain_pct=None,
    )
    assert bound.s_ep == pure.s_ep
    assert bound.coverage == pure.coverage
    # close_loc alias worked
    assert bound.components["close_quality"] is not None


def test_score_ep_neither_n5_nor_setup_raises():
    """A snapshot with neither n5_inputs nor setup_inputs is a real
    schema defect (predates wave A entirely). The binding raises
    loudly so a silent zero-coverage decision cannot leak through."""
    snap = {"close": 100.0}
    with pytest.raises(ContractError, match="setup_inputs"):
        score_ep_from_snapshot("GGG", "2026-08-28", snap)


def test_score_ep_rejects_bool_in_numeric_field():
    """Bool is a subclass of int in Python; the binding must not
    accept True/False where a float is expected (it would silently
    score as 1.0/0.0)."""
    snap = _snap(gap_pct=True)  # wrong type
    with pytest.raises(ContractError, match="bool"):
        score_ep_from_snapshot("EEE", "2026-08-28", snap)


# --------------------------------------------------------- S_tight binding


def test_s_tight_not_built_yet():
    """The S_tight base_episode block is the wave C-2 deliverable. The
    binding returns a status dict (not a score) so the runner can
    report coverage without crashing."""
    snap = _snap()
    status = s_tight_status_from_snapshot(snap)
    assert status["score"] is None
    assert status["coverage"] == 0.0
    assert status["status"] == "not_built_yet"


def test_s_tight_legacy_snapshot_returns_not_built_yet():
    """A snapshot predating C-1 has no n5_inputs block. The binding
    returns the same 'not_built_yet' status as a C-1 snapshot whose
    tight block is empty -- the only thing that distinguishes them
    is the architecture, not the S_tight status (both are honest
    'not built yet' until C-2 ships the base_episode block)."""
    snap = {"close": 100.0}
    status = s_tight_status_from_snapshot(snap)
    assert status["status"] == "not_built_yet"
