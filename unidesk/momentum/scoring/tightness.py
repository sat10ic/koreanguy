"""S_tight — tightness-scored continuation quality (swing-edges spec §4.4, T1).

The deterministic T1 coil-quality composite. Frozen component weights (spec):
contraction monotonicity 25 · final swing depth 15 · volume dry-up on the
last swing 20 · range compression 15 · delivery integrity 10 · RS hold 15.

Same contributor contract as the other scorers: caller supplies raw,
point-in-time component values; this module normalizes each to 0..100 with
documented frozen mappings, weights them (config, R14), and returns a
decomposable result. Missing components reduce coverage and are named —
never zero (R12). Score is None below ``min_coverage`` (spec: "calibrate on
train"; default 0.70).

Contraction monotonicity (`contraction_ok`, spec §1.5): at least 2 pullbacks
and each pullback no deeper than 0.75 × the previous one. The caller passes
the pullback depth sequence (deepest-first as encountered); this module
judges monotonic decrease.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from unidesk.contracts.base import ContractError, require_float

CONTRIBUTOR_NAMES = (
    "contraction_monotonicity",   # weight 25
    "final_swing_depth",          # 15
    "volume_dryup_last_swing",    # 20
    "range_compression",          # 15
    "delivery_integrity",         # 10
    "rs_hold_during_base",        # 15
)
DEFAULT_WEIGHTS = {
    "contraction_monotonicity": 25.0,
    "final_swing_depth": 15.0,
    "volume_dryup_last_swing": 20.0,
    "range_compression": 15.0,
    "delivery_integrity": 10.0,
    "rs_hold_during_base": 15.0,
}
MIN_COVERAGE = 0.70


@dataclass(frozen=True)
class TightnessResult:
    score: Optional[float]
    coverage: float
    components: tuple            # (name, available, normalized 0..100 or None, reason)
    unknowns: tuple
    contraction_ok: Optional[bool]
    n_pullbacks: int


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _norm(value: float, zero_at: float, hundred_at: float) -> float:
    """Linear 0..100: value at zero_at scores 0, at hundred_at scores 100."""
    if zero_at == hundred_at:
        raise ContractError("zero_at == hundred_at")
    return _clamp((value - zero_at) / (hundred_at - zero_at) * 100.0)


def contraction_sequence(depths: Sequence[float], ratio: float = 0.75) -> tuple[bool, int]:
    """Spec §1.5 ``contraction_ok``: >=2 pullbacks, each no deeper than
    ``ratio`` × the previous one. Fewer than 2 pullbacks -> False (the
    monotonicity component then scores 0 — a single-leg move is not a coil)."""
    if len(depths) < 2:
        return False, len(depths)
    ok = all(d2 <= ratio * d1 for d1, d2 in zip(depths, depths[1:]))
    return ok, len(depths)


def tightness_score(
    *,
    pullback_depths: Sequence[float],
    final_depth_pct: Optional[float] = None,
    dryup_ratio: Optional[float] = None,
    atrp_percentile: Optional[float] = None,
    delivery_bottom_quintile: Optional[bool] = None,
    rs_made_20d_low: Optional[bool] = None,
    weights: Optional[dict] = None,
    contraction_ratio: float = 0.75,
    final_depth_zero_at: float = 12.0,
    dryup_zero_at: float = 1.0,
    dryup_hundred_at: float = 0.5,
    atrp_percentile_zero_at: float = 80.0,
    atrp_percentile_hundred_at: float = 40.0,
    min_coverage: float = MIN_COVERAGE,
) -> TightnessResult:
    """Score coil quality from caller-computed point-in-time values.

    * ``pullback_depths`` — % depth of each pullback in the base, deepest-
      window order as encountered. Weights: contraction monotonicity 25,
      final swing depth 15, dry-up 20, range compression 15, delivery 10,
      RS hold 15 (DEFAULT_WEIGHTS; override via ``weights``, R14/R15).
    * Normalizations (frozen): final swing depth 4%→100 .. 12%→0; dry-up
      ratio 0.5→100 .. 1.0→0; ATR-percentile 40→100 .. 80→0.
    * ``rs_made_20d_low`` — False means RS held (scores 100).
    * ``delivery_bottom_quintile`` — True means bottom-quintile delivery
      (scores 0); None = data missing.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        unknown = set(weights) - set(CONTRIBUTOR_NAMES)
        if unknown:
            raise ContractError(f"unknown contributor weights: {sorted(unknown)}")
        w.update(weights)
    total = sum(w.values())
    if total <= 0:
        raise ContractError("total configured weight must be positive")

    depths = [require_float(d, f"pullback_depths[{i}]") for i, d in enumerate(pullback_depths)]
    monotone, n_pb = contraction_sequence(depths, contraction_ratio)

    components: dict[str, Optional[float]] = {}
    unknowns: list[str] = []

    components["contraction_monotonicity"] = 100.0 if monotone and len(depths) >= 2 else 0.0

    if final_depth_pct is None:
        components["final_swing_depth"] = None
        unknowns.append("FINAL_SWING_DEPTH_UNAVAILABLE")
    else:
        components["final_swing_depth"] = _clamp(_norm(final_depth_pct, 12.0, 4.0))

    if dryup_ratio is None:
        components["volume_dryup_last_swing"] = None
        unknowns.append("DRYUP_UNAVAILABLE")
    else:
        components["volume_dryup_last_swing"] = _clamp(_norm(dryup_ratio, 1.0, 0.5))

    if atrp_percentile is None:
        components["range_compression"] = None
        unknowns.append("ATRP_PERCENTILE_UNAVAILABLE")
    else:
        components["range_compression"] = _clamp(_norm(atrp_percentile, 80.0, 40.0))

    if delivery_bottom_quintile is None:
        components["delivery_integrity"] = None
        unknowns.append("DELIVERY_UNAVAILABLE")
    else:
        components["delivery_integrity"] = 0.0 if delivery_bottom_quintile else 100.0

    if rs_made_20d_low is None:
        components["rs_hold_during_base"] = None
        unknowns.append("RS_HOLD_UNAVAILABLE")
    else:
        components["rs_hold_during_base"] = 0.0 if rs_made_20d_low else 100.0

    available_weight = 0.0
    weighted = 0.0
    for name in CONTRIBUTOR_NAMES:
        weight = w.get(name, 0.0)
        value = components.get(name)
        if weight == 0.0 or value is None:
            continue
        available_weight += weight
        weighted += weight * value

    coverage = available_weight / total
    score: Optional[float] = None
    if coverage < min_coverage:
        unknowns.append("INSUFFICIENT_DATA")
    else:
        score = round(weighted / available_weight, 3)

    return TightnessResult(
        score=score,
        coverage=round(coverage, 3),
        components=tuple(
            (name, components.get(name)) for name in CONTRIBUTOR_NAMES
        ),
        unknowns=tuple(dict.fromkeys(unknowns)),
        contraction_ok=monotone and len(depths) >= 2,
        n_pullbacks=len(depths),
    )
