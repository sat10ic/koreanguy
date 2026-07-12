"""Anti-overfit promotion battery (shadow-only).

Every candidate signal series is tested against Indian cost assumptions,
walk-forward folds, placebo/permutation, regime-split and sub-sample
stability. Emits a frozen verdict dict; never mutates live ranking.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Sequence

# Indian round-trip cost constants (documented; not secrets).
# STT equity delivery ~0.1% sell; brokerage ~0.03% each side (discount);
# slippage buffer ~0.05% each side. Round-trip approx used for daily CS scores.
STT_SELL_PCT = 0.10
BROKERAGE_ONE_WAY_PCT = 0.03
SLIPPAGE_ONE_WAY_PCT = 0.05
ROUND_TRIP_COST_PCT = STT_SELL_PCT + 2 * BROKERAGE_ONE_WAY_PCT + 2 * SLIPPAGE_ONE_WAY_PCT  # ~0.26%


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: dict[str, Any]


def _net_mean(returns: Sequence[float]) -> float:
    if not returns:
        return 0.0
    cost = ROUND_TRIP_COST_PCT / 100.0
    return sum(r - cost for r in returns) / len(returns)


def walk_forward(
    signal_returns: Sequence[float],
    baseline_returns: Sequence[float],
    n_folds: int = 4,
) -> GateResult:
    n = min(len(signal_returns), len(baseline_returns))
    if n < n_folds * 5:
        return GateResult("walk_forward", False, {"reason": "insufficient_sample", "n": n})
    fold = n // n_folds
    beats = 0
    fold_details = []
    for i in range(n_folds):
        a, b = i * fold, (i + 1) * fold if i < n_folds - 1 else n
        s = _net_mean(signal_returns[a:b])
        base = _net_mean(baseline_returns[a:b])
        win = s > base
        beats += int(win)
        fold_details.append({"fold": i, "signal_net": s, "baseline_net": base, "beats": win})
    # Require majority of folds beat baseline after costs
    passed = beats >= math.ceil(n_folds * 0.5) and _net_mean(signal_returns[:n]) > _net_mean(baseline_returns[:n])
    return GateResult("walk_forward", passed, {"beats": beats, "n_folds": n_folds, "folds": fold_details})


def placebo_permutation(
    signal_returns: Sequence[float],
    n_perm: int = 200,
    seed: int = 7,
) -> GateResult:
    if len(signal_returns) < 20:
        return GateResult("placebo", False, {"reason": "insufficient_sample"})
    rng = random.Random(seed)
    real = _net_mean(signal_returns)
    arr = list(signal_returns)
    # Degenerate constant series: shuffle/shift cannot beat real — treat as pass
    # only if real edge survives costs (real > 0).
    if max(arr) - min(arr) < 1e-15:
        return GateResult(
            "placebo",
            real > 0,
            {"real_net": real, "degenerate_constant": True, "n_null": 0},
        )
    nulls = []
    for _ in range(n_perm):
        k = rng.randint(1, max(1, len(arr) - 1))
        shifted = arr[k:] + arr[:k]
        nulls.append(_net_mean(shifted))
        shuf = arr[:]
        rng.shuffle(shuf)
        nulls.append(_net_mean(shuf))
    nulls.sort()
    thr_idx = int(0.95 * (len(nulls) - 1))
    thr = nulls[thr_idx]
    return GateResult("placebo", real > thr, {"real_net": real, "p95_null": thr, "n_null": len(nulls)})


def regime_stability(
    returns_by_regime: dict[str, Sequence[float]],
    min_regimes: int = 2,
) -> GateResult:
    signs = {}
    for reg, rets in returns_by_regime.items():
        if len(rets) < 5:
            continue
        signs[reg] = 1 if _net_mean(rets) > 0 else -1
    if len(signs) < min_regimes:
        return GateResult("regime_stability", False, {"reason": "need_ge_2_regimes", "signs": signs})
    pos = sum(1 for s in signs.values() if s > 0)
    neg = sum(1 for s in signs.values() if s < 0)
    # sign consistency in >=2 of 3 (or majority when fewer)
    passed = max(pos, neg) >= min_regimes
    return GateResult("regime_stability", passed, {"signs": signs, "pos": pos, "neg": neg})


def subsample_stability(
    signal_returns: Sequence[float],
    frac: float = 0.3,
    n_draws: int = 30,
    seed: int = 11,
    min_sign_consistency: float = 0.7,
) -> GateResult:
    if len(signal_returns) < 30:
        return GateResult("subsample_stability", False, {"reason": "insufficient_sample"})
    rng = random.Random(seed)
    n = len(signal_returns)
    k = max(5, int(n * frac))
    full_sign = 1 if _net_mean(signal_returns) > 0 else -1
    agree = 0
    for _ in range(n_draws):
        sample = [signal_returns[i] for i in rng.sample(range(n), k)]
        s = 1 if _net_mean(sample) > 0 else -1
        agree += int(s == full_sign)
    rate = agree / n_draws
    return GateResult(
        "subsample_stability",
        rate >= min_sign_consistency,
        {"agree_rate": rate, "full_sign": full_sign, "n_draws": n_draws},
    )


def min_sample_floor(n: int, floor: int = 60) -> GateResult:
    return GateResult("min_sample", n >= floor, {"n": n, "floor": floor})


def run_promotion_battery(
    signal_returns: Sequence[float],
    baseline_returns: Sequence[float],
    returns_by_regime: dict[str, Sequence[float]] | None = None,
    *,
    hypothesis: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run all gates; return frozen verdict record (not written to DB here)."""
    returns_by_regime = returns_by_regime or {}
    gates = [
        min_sample_floor(len(signal_returns)),
        walk_forward(signal_returns, baseline_returns),
        placebo_permutation(signal_returns),
        regime_stability(returns_by_regime) if returns_by_regime else GateResult(
            "regime_stability", False, {"reason": "no_regime_splits_provided"}
        ),
        subsample_stability(signal_returns),
    ]
    passed_all = all(g.passed for g in gates)
    return {
        "hypothesis": hypothesis,
        "config": config or {},
        "cost_constants": {
            "stt_sell_pct": STT_SELL_PCT,
            "brokerage_one_way_pct": BROKERAGE_ONE_WAY_PCT,
            "slippage_one_way_pct": SLIPPAGE_ONE_WAY_PCT,
            "round_trip_cost_pct": ROUND_TRIP_COST_PCT,
        },
        "gates": [{"name": g.name, "passed": g.passed, "detail": g.detail} for g in gates],
        "verdict": "passed" if passed_all else "failed",
        "shadow_only": True,
    }
