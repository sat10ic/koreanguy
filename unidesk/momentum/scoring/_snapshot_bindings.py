"""S_ep / S_tight score bindings for the freeze-scan snapshot (N5 wave C-1).

The two deterministic composite scorers live in:
  * unidesk.momentum/detectors/ep_signature.py  (T5 S_ep)
  * unidesk/momentum/scoring/tightness.py       (T1 S_tight)

Both take point-in-time values as keyword args and return a dataclass.
The freeze-scan snapshot carries those values under the ``n5_inputs`` block
(introduced in wave C-1, see ``research.candidates._snapshot``). This module
is the only thing that knows the snapshot layout; the scorers themselves
remain pure functions of caller-supplied values.

Backward compatibility (wave C-1):
    The existing persisted archive (v3/v4 regen) was frozen BEFORE the
    n5_inputs block existed. The EP-side values are recoverable from
    ``setup_inputs`` (which has been on disk since wave A), so this
    binding lazily materializes the n5_inputs.ep block on read. The
    T1 S_tight block cannot be recovered -- it is the wave C-2 work.
    Once the regen re-runs and re-freezes under the new schema, this
    lazy-materialize path will short-circuit and read the real block.

Honesty discipline (R12 / wave-B net-bps rule applied here too):
    * A snapshot field that is None flows through as None to the scorer; the
      scorer then drops the component and names it in ``unknowns``. Coverage
      drops honestly -- the resulting score is over a smaller, explicit
      component set, and the operator can see the missing fields.
    * ``circuit_locked`` is the one bool field the snapshot must commit to.
      Today it is always False because the freeze-scan layer does not run
      the day-classifier; the S_ep close_quality component is therefore
      computed for what may be locked days. A future wave will read
      circuit-locked from the day-classifier and route those events to the
      delayed list instead. The binding passes False and records the
      gap via the ``CIRCUIT_DETECTION_NOT_WIRED`` unknown.
"""
from __future__ import annotations

from typing import Optional

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.ep_signature import EPDecision, ep_signature


# Keys we know how to lift from the legacy setup_inputs dict when the
# n5_inputs block is missing. Tied to unidesk/momentum/detectors/inputs.py
# compute_setup_inputs() -- if that module's key names change, this map
# must change too.
_LEGACY_EP_KEYS = {
    "gap_pct": "gap_pct",
    "rvol": "rvol",
    "close_loc": "close_location",   # the legacy name is close_location
}


def _ep_inputs(snapshot: dict) -> dict:
    """Lift the EP inputs from the n5_inputs block. If the block is
    missing (legacy archive predating wave C-1), materialise it from
    ``setup_inputs`` on the fly. Raises ContractError if neither
    source is available -- a missing-both case is a real schema
    defect, not a backward-compat case."""
    n5 = snapshot.get("n5_inputs")
    if isinstance(n5, dict):
        ep = n5.get("ep")
        if isinstance(ep, dict):
            return ep
    setup = snapshot.get("setup_inputs")
    if not isinstance(setup, dict):
        raise ContractError(
            "snapshot has neither n5_inputs nor setup_inputs -- cannot "
            "recover EP inputs (predates wave A; refreeze required)"
        )
    return {
        "gap_pct": setup.get(_LEGACY_EP_KEYS["gap_pct"]),
        "rvol": setup.get(_LEGACY_EP_KEYS["rvol"]),
        "close_loc": setup.get(_LEGACY_EP_KEYS["close_loc"]),
        "prior_compression_pctile": None,
        "delivery_shock": None,
        "circuit_locked": False,
        "prior_20d_gain_pct": None,
    }


def _coerce_optional_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, bool):
        # bool is a subclass of int -- disallow it from numeric fields.
        raise ContractError(f"expected None or float, got bool: {v!r}")
    return float(v)


def score_ep_from_snapshot(symbol: str, session: str, snapshot: dict) -> EPDecision:
    """Compute S_ep from a freeze-scan snapshot. The snapshot's n5_inputs.ep
    block is the contract surface; see _snapshot in research.candidates.

    The contract:
      * gap_pct        required (point-in-time from setup_inputs)
      * rvol           optional -- None drops rvol_anomaly
      * close_loc      optional -- None drops close_quality
      * prior_compression_pctile  optional -- None drops prior_compression
      * delivery_shock optional -- None drops delivery_shock
      * circuit_locked bool (default False; documented caveat above)
      * prior_20d_gain_pct optional -- None leaves climax_on_climax None
    """
    ep = _ep_inputs(snapshot)
    gap = _coerce_optional_float(ep.get("gap_pct"))
    if gap is None:
        # The S_ep signature requires gap_pct (it's the Day-0 gate); a None
        # gap means the freeze-scan didn't have the prior bar to compute
        # it. Treat as INSUFFICIENT_DATA: return an EPDecision with
        # coverage 0 and the only known unknown, mirroring the scorer's
        # own "below min_coverage" branch without calling it.
        return EPDecision(
            symbol=symbol, session=session, s_ep=0.0, coverage=0.0,
            circuit_ep=False, climax_on_climax=None,
            components={
                "gap_significance": None, "rvol_anomaly": None,
                "close_quality": None, "prior_compression": None,
                "delivery_shock": None,
            },
            unknowns=("GAP_PCT_UNAVAILABLE", "INSUFFICIENT_DATA"),
        )
    decision = ep_signature(
        symbol=symbol,
        session=session,
        gap_pct=gap,
        rvol=_coerce_optional_float(ep.get("rvol")),
        close_loc=_coerce_optional_float(ep.get("close_loc")),
        prior_compression_pctile=_coerce_optional_float(ep.get("prior_compression_pctile")),
        delivery_shock=_coerce_optional_float(ep.get("delivery_shock")),
        circuit_locked=bool(ep.get("circuit_locked", False)),
        prior_20d_gain_pct=_coerce_optional_float(ep.get("prior_20d_gain_pct")),
    )
    # Document the circuit-detection gap honestly so the operator can see
    # it in coverage reports without having to read the binding source.
    if not bool(ep.get("circuit_locked", False)):
        # Append -- not replace -- so a future wave that supplies the
        # actual value can stop emitting this without a tuple-edit
        # collision.
        new_unknowns = list(decision.unknowns) + ["CIRCUIT_DETECTION_NOT_WIRED"]
        decision = EPDecision(
            symbol=decision.symbol, session=decision.session,
            s_ep=decision.s_ep, coverage=decision.coverage,
            circuit_ep=decision.circuit_ep,
            climax_on_climax=decision.climax_on_climax,
            components=decision.components,
            unknowns=tuple(dict.fromkeys(new_unknowns)),
        )
    return decision


def s_tight_status_from_snapshot(snapshot: dict) -> dict:
    """S_tight is not wired in wave C-1 (the base_episode block is a
    placeholder). Return an honest "not built yet" status instead of
    raising, so a runner that asks both scorers can log a single
    coverage line for S_tight without breaking the report.

    Legacy snapshots (no n5_inputs block) return the same
    'not_built_yet' status; the only thing that distinguishes
    "really new" from "legacy" is the underlying architecture, not
    the s_tight status -- both code paths report the same gap."""
    n5 = snapshot.get("n5_inputs")
    if isinstance(n5, dict):
        tight = n5.get("tight")
        if isinstance(tight, dict):
            be = tight.get("base_episode")
            if be is None:
                return {"score": None, "coverage": 0.0, "status": "not_built_yet"}
            return {"score": None, "coverage": 0.0, "status": "wave_c2_pending"}
    return {"score": None, "coverage": 0.0, "status": "not_built_yet"}
