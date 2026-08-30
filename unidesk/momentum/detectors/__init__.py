"""Setup detectors (P2.3): deterministic rule composition over features."""

from unidesk.momentum.detectors.momentum_burst import BurstRules, Detection, momentum_burst
from unidesk.momentum.detectors.registry import DETECTOR_NAMES, DetectorConfig, evaluate_all

__all__ = [
    "BurstRules",
    "DETECTOR_NAMES",
    "Detection",
    "DetectorConfig",
    "evaluate_all",
    "momentum_burst",
]
