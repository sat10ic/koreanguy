"""Statistical significance for the desk's research claims (R-01/R-02/R-03,
A-05 promotion rule).

Clean-room implementations; source IDEAS harvested per UI_BUILD_SPEC_V1
PART 15 rules (idea, not code):

- R-01 Deflated Sharpe Ratio -- idea from reviewing Algo-Ankit/TradeProject
  (zero statistical testing while comparing many detector configurations
  manufactures a winner by construction). DSR after Bailey & López de
  Prado (2014): the probability that the TRUE Sharpe is positive after
  accounting for N configurations tried, skew, and kurtosis.
- R-02 A/B/C controlled-backtest structure -- idea from
  tanmaykaper/Paper-Trading-Bot; maps onto Constitution §7's three
  competitors (champion / champion+L1.5 / champion+L2). All arms run on
  the SAME sample; coverage per arm is reported next to every figure.
- R-03 standard walk-forward metric suite -- idea from
  chandewardnyanesh/kronos-nse-terminal whose compare_edge is a bare mean
  comparison. Every metric here carries its sample size `n`; a metric
  without `n` is not displayable (R-03 accept).

No runtime dependencies beyond stdlib (math, random). Conventions:
`returns` is a per-trade or per-session return series in the book's own
units (bps or R -- the functions are unit-agnostic); Sharpe here is
per-observation mean/std, deliberately NOT annualised (the horizon is
fixed by the label spec, and annualising invites arbitrary multipliers).
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from unidesk.contracts.base import ContractError


def _require_series(returns: Sequence[float], min_len: int = 3) -> list[float]:
    series = [float(x) for x in returns]
    if len(series) < min_len:
        raise ContractError(f"need at least {min_len} observations, got {len(series)}")
    if any(not math.isfinite(x) for x in series):
        raise ContractError("series contains a non-finite value")
    return series


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _std(xs: Sequence[float]) -> float:
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Acklam's rational approximation (absolute error < 1.15e-9) -- stdlib
    has no inverse normal CDF and new dependencies require owner sign-off."""
    if not 0.0 < p < 1.0:
        raise ContractError("p must be in (0, 1)")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > p_high:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def sharpe(returns: Sequence[float]) -> float:
    """Per-observation Sharpe = mean / std (ddof=1). 0.0 when std is 0."""
    s = _require_series(returns)
    sd = _std(s)
    return _mean(s) / sd if sd > 0 else 0.0


def deflated_sharpe_ratio(returns: Sequence[float], *, n_trials: int = 1) -> float:
    """R-01: DSR -- P(true SR > 0 | this was the best of `n_trials` tries).

    Bailey & López de Prado (2014), "The Deflated Sharpe Ratio". Returns a
    probability in [0, 1]; a value below ~0.90-0.95 means the observed Sharpe
    is indistinguishable from what the BEST OF N null configurations
    produces. A deliberately null signal therefore fails as `n_trials`
    grows -- that is the point.

    Guard: with variance(SR across trials) unavailable (we see only the
    winner), the expected-max formula uses the conservative
    SR0 = sqrt((1 - gamma) * Phi^-1(1 - 1/N) + gamma * Phi^-1(1 - 1/(N e)))
    variant with unit trial-variance (the standard practice when only N is
    known; documented here so nobody mistakes it for a measured spread).
    """
    s = _require_series(returns, min_len=4)
    if n_trials < 1:
        raise ContractError("n_trials must be >= 1")
    sr = sharpe(s)
    t = len(s)
    gamma = 0.5772156649015329  # Euler–Mascheroni
    n = n_trials
    if n == 1:
        # Single configuration: no multiple-testing discount applies; DSR
        # reduces to the probabilistic Sharpe test against SR0 = 0.
        expected_max = 0.0
    else:
        expected_max = math.sqrt(max(1e-12, (1 - gamma) * _norm_ppf(1 - 1.0 / n) + gamma * _norm_ppf(1 - 1.0 / (n * math.e))))
    # skewness and kurtosis of the return series
    m = _mean(s)
    sd = _std(s)
    if sd == 0:
        return 0.5
    skew = sum((x - m) ** 3 for x in s) / t / sd**3
    kurt = sum((x - m) ** 4 for x in s) / t / sd**4  # non-excess
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr * sr))
    return _norm_cdf((sr - expected_max) * math.sqrt(t - 1) / denom)


def block_bootstrap_ci(
    returns: Sequence[float],
    *,
    n_boot: int = 1000,
    block: int = 10,
    ci: float = 0.90,
    seed: int = 7,
) -> tuple[float, float]:
    """R-01: moving-block bootstrap CI for the MEAN return. Preserves the
    short-range dependence that per-trade iid resampling destroys.
    Returns (lo, hi) percentile bounds. A CI containing 0 is a null signal
    no matter how pretty the point estimate is."""
    s = _require_series(returns)
    if not 0 < ci < 1:
        raise ContractError("ci must be in (0, 1)")
    if block < 1 or block > len(s):
        raise ContractError("block must be in [1, len(series)]")
    rng = random.Random(seed)
    n_blocks = math.ceil(len(s) / block)
    means = []
    for _ in range(n_boot):
        sample: list[float] = []
        for _ in range(n_blocks):
            start = rng.randint(0, len(s) - block)
            sample.extend(s[start:start + block])
        means.append(_mean(sample[: len(s)]))
    means.sort()
    alpha = (1 - ci) / 2
    lo = means[int(alpha * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha) * n_boot))]
    return lo, hi


# ---- R-03: walk-forward metric suite, every figure with its n -------------

@dataclass(frozen=True)
class MetricSuite:
    n: int                      # every displayed figure cites this
    total_return: float         # compounded sum of the series
    sharpe: float
    max_drawdown: float         # peak-to-trough of the cumulative curve, <= 0
    hit_rate: float             # share of observations > 0
    expectancy: float           # mean per observation
    pnl_curve: tuple[float, ...]  # cumulative curve (for the R-04 view)


def metric_suite(returns: Sequence[float]) -> MetricSuite:
    s = _require_series(returns)
    curve: list[float] = []
    equity = 1.0
    for x in s:
        equity *= (1 + x / 10_000)  # series interpreted in bps for compounding
        curve.append(equity)
    peak = curve[0]
    mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wins = sum(1 for x in s if x > 0)
    return MetricSuite(
        n=len(s),
        total_return=round(equity - 1, 6),
        sharpe=round(sharpe(s), 4),
        max_drawdown=round(mdd, 6),
        hit_rate=round(wins / len(s), 4),
        expectancy=round(_mean(s), 4),
        pnl_curve=tuple(round(v, 6) for v in curve),
    )


# ---- R-02: A/B/C controlled backtest --------------------------------------

@dataclass(frozen=True)
class ArmResult:
    name: str
    n: int
    coverage: float            # n / max n across arms, in [0, 1]
    expectancy: float          # mean return per trade (book's units)
    hit_rate: float
    sharpe: float


def compare_arms(arms: dict[str, Sequence[float]]) -> dict[str, ArmResult]:
    """R-02: run every arm's return series through the same metric suite and
    report coverage per arm. Arms are the Constitution §7 trio -- champion /
    champion+L1.5 / champion+L2 -- evaluated on the SAME sample; nothing
    here merges books or drops observations silently."""
    if not arms:
        raise ContractError("compare_arms needs at least one arm")
    suites = {name: metric_suite(series) for name, series in arms.items()}
    max_n = max(s.n for s in suites.values())
    return {
        name: ArmResult(
            name=name,
            n=s.n,
            coverage=round(s.n / max_n, 4),
            expectancy=s.expectancy,
            hit_rate=s.hit_rate,
            sharpe=s.sharpe,
        )
        for name, s in suites.items()
    }


# ---- A-05: the promotion rule, frozen before any holdout ------------------

@dataclass(frozen=True)
class PromotionInput:
    fold_beats: tuple[bool, ...]     # per walk-forward fold: candidate beat champion?
    returns: Sequence[float]         # candidate book's per-trade returns
    n_trials: int                    # configurations tried before this one
    expectancy_uplift: float         # (cand - champ) / |champ| net expectancy
    ci: float = 0.90
    min_uplift: float = 0.15         # Constitution §19: 15-20% band, low end

    def __post_init__(self) -> None:
        if len(self.fold_beats) != 5:
            raise ContractError("promotion is defined over exactly 5 walk-forward folds")


@dataclass(frozen=True)
class PromotionVerdict:
    folds_won: int
    ci_lo: float
    ci_hi: float
    ci_excludes_zero: bool
    dsr: float
    uplift_ok: bool
    classification: str   # RANKER | SNIPER FILTER | NO EDGE
    notes: tuple


def promotion_rule(inp: PromotionInput) -> PromotionVerdict:
    """Constitution §19, as code. PROMOTE requires ALL of:
    (1) lift persists in >= 3 of 5 walk-forward folds,
    (2) block-bootstrap 90% CI of the candidate's mean return excludes zero,
    (3) >= 15% net expectancy improvement (the low end of the 15-20% band),
    and the deflated Sharpe (best-of-n_trials) must be >= 0.90.
    Classification: RANKER = broad lift (hit-rate + expectancy up);
    SNIPER FILTER = narrow but deep (expectancy up, hit-rate flat);
    NO EDGE = everything else. A deliberately null signal fails all four
    gates -- see test_significance.py::test_null_signal_fails_promotion."""
    folds_won = sum(1 for b in inp.fold_beats if b)
    lo, hi = block_bootstrap_ci(inp.returns, ci=inp.ci)
    dsr = deflated_sharpe_ratio(inp.returns, n_trials=inp.n_trials)
    ci_excludes_zero = lo > 0 or hi < 0
    uplift_ok = inp.expectancy_uplift >= inp.min_uplift
    promoted = (
        folds_won >= 3
        and ci_excludes_zero
        and uplift_ok
        and dsr >= 0.90
    )
    if not promoted:
        classification = "NO EDGE"
    else:
        suite = metric_suite(inp.returns)
        classification = "RANKER" if suite.hit_rate >= 0.5 else "SNIPER FILTER"
    return PromotionVerdict(
        folds_won=folds_won,
        ci_lo=lo,
        ci_hi=hi,
        ci_excludes_zero=ci_excludes_zero,
        dsr=round(dsr, 4),
        uplift_ok=uplift_ok,
        classification=classification,
        notes=(
            f"folds {folds_won}/5, CI[{lo:.4f}, {hi:.4f}], DSR {dsr:.4f} "
            f"(n_trials={inp.n_trials}), uplift {inp.expectancy_uplift:.3f}"
        ),
    )
