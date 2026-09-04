"""Setup-quality snapshot (build manual Task P2.4).

``setup quality = detector verdict + named rule failures`` — a
coverage-honest 0..100 score per candidate, computed deterministically
from the detector's own verdict object. Nothing beyond the verdict is
measured here; no thresholds, no fabricated rule counts (R12, R14).

Scoring (documented coarse proxy — the verdict does not expose the
detector's total rule count, so a fixed denominator is used and labeled):

* ``INSUFFICIENT_DATA`` → score ``None``, coverage ``0.0``, named reasons.
* ``INVALID``       → not a candidate; score ``None`` (R12: never zero-fill
  an invalid verdict into a low-but-present number).
* ``VALID`` with no skipped rules → ``100``, coverage ``1.0``.
* ``VALID`` with ``n`` skipped *optional* rules → each skipped rule costs
  20 points (floor 40) and 15% of coverage: the rules that *could* be
  evaluated all passed, but a smaller share of the detector's rule set
  was actually exercised. Named skipped-rules land in ``unknowns``.

`feature_version` / `config_hash` are caller-supplied for the same
auditability the other snapshots carry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from unidesk.contracts.base import ensure_utc, require_str
from unidesk.momentum.detectors.momentum_burst import Detection

# one skipped optional rule = -20 points, floor 40; 15% coverage loss each
SKIP_POINTS_PENALTY = 20.0
SKIP_COVERAGE_PENALTY = 0.15
FLOOR_SCORE = 40.0

CONTRIBUTOR_NAMES: tuple = ()  # no weighted contributors; setup quality is
# a verdict-pass-rate snapshot, documented as a proxy (P2.4)


@dataclass(frozen=True)
class SetupQualitySnapshot:
    symbol: str
    as_of: datetime
    score: Optional[float]
    coverage: float
    unknowns: tuple
    feature_version: str
    config_hash: str


def _clamp100(v: float) -> float:
    return max(0.0, min(100.0, v))


def setup_quality_snapshot(
    symbol: str,
    as_of: datetime,
    *,
    verdict: Detection,
    failures: tuple = (),
    feature_version: str = "",
    config_hash: str = "",
) -> SetupQualitySnapshot:
    symbol = require_str(symbol, "symbol")
    as_of = ensure_utc(as_of, "as_of")
    feature_version = require_str(feature_version, "feature_version")
    config_hash = require_str(config_hash, "config_hash")

    if verdict is Detection.INVALID:
        return SetupQualitySnapshot(
            symbol=symbol, as_of=as_of, score=None, coverage=0.0,
            unknowns=("SETUP_INVALID_VERDICT",),
            feature_version=feature_version, config_hash=config_hash,
        )
    if verdict is Detection.INSUFFICIENT_DATA:
        return SetupQualitySnapshot(
            symbol=symbol, as_of=as_of, score=None, coverage=0.0,
            unknowns=("SETUP_INSUFFICIENT_DATA",) + tuple(failures),
            feature_version=feature_version, config_hash=config_hash,
        )

    # VALID: failures carries '' or 'skipped:<name>' entries (engine returns
    # skipped optional rules as the VALID tuple).
    skipped = tuple(f for f in failures if f.startswith("skipped:"))
    n = len(skipped)
    score = _clamp100(100.0 - SKIP_POINTS_PENALTY * n)
    if score < FLOOR_SCORE:
        score = FLOOR_SCORE
    coverage = max(0.0, 1.0 - SKIP_COVERAGE_PENALTY * n)
    unknowns = tuple(f.removeprefix("skipped:") for f in skipped)
    return SetupQualitySnapshot(
        symbol=symbol, as_of=as_of,
        score=round(score, 1),
        coverage=round(coverage, 3),
        unknowns=unknowns,
        feature_version=feature_version, config_hash=config_hash,
    )