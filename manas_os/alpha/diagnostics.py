"""Transparent research diagnostics; none of these functions size positions."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from statistics import mean


def bayesian_setup_expectancy(conn, *, horizon: int = 10, prior_strength: float = 10.0) -> list[dict]:
    """Beta-binomial win probability plus shrunk mean R by setup.

    The parent prior is the complete cohort at the same horizon. Small setup
    cohorts therefore move toward observed parent performance, not certainty.
    """
    rows = conn.execute(
        "SELECT c.setup,o.managed_r FROM outcomes o JOIN candidates c USING(candidate_date,symbol,setup) "
        "WHERE o.status='complete' AND o.horizon=? AND o.managed_r IS NOT NULL", (horizon,),
    ).fetchall()
    if not rows:
        return []
    all_r = [float(r["managed_r"]) for r in rows]
    prior_p = sum(v > 0 for v in all_r) / len(all_r)
    prior_r = mean(all_r)
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[row["setup"]].append(float(row["managed_r"]))
    result = []
    for setup, values in sorted(groups.items()):
        n = len(values)
        wins = sum(v > 0 for v in values)
        posterior_p = (wins + prior_strength * prior_p) / (n + prior_strength)
        posterior_r = (sum(values) + prior_strength * prior_r) / (n + prior_strength)
        result.append({"setup": setup, "n": n, "raw_hit_rate": wins / n,
                       "posterior_hit_rate": posterior_p, "raw_expectancy_r": mean(values),
                       "posterior_expectancy_r": posterior_r, "prior_n": prior_strength})
    return result


def competing_risk_summary(conn, *, horizon: int = 10) -> dict:
    """Summarise the conservative managed path labels already written by outcomes."""
    rows = conn.execute(
        "SELECT hit_1r,exit_reason FROM outcomes WHERE status='complete' AND horizon=? "
        "AND exit_reason IS NOT NULL", (horizon,),
    ).fetchall()
    counts = {"plus_1r_first": 0, "stop_first": 0, "neither": 0}
    for row in rows:
        if int(row["hit_1r"] or 0) == 1:
            counts["plus_1r_first"] += 1
        elif row["exit_reason"] in {"stop", "gap_through_stop"}:
            counts["stop_first"] += 1
        else:
            counts["neither"] += 1
    n = len(rows)
    return {"horizon": horizon, "n": n, "counts": counts,
            "probabilities": {k: (v / n if n else None) for k, v in counts.items()},
            "state": "ready" if n else "warming"}


def block_bootstrap_diagnostics(
    returns_r: list[float], *, block_size: int = 5, simulations: int = 1000,
    sample_length: int | None = None, seed: int = 0,
) -> dict:
    """Seeded circular block bootstrap preserving local streak dependence."""
    values = [float(v) for v in returns_r]
    if not values:
        return {"state": "warming", "n": 0, "simulations": 0}
    if block_size < 1 or simulations < 1:
        raise ValueError("block_size and simulations must be positive")
    length = sample_length or len(values)
    rng = random.Random(seed)
    totals, drawdowns, losing_streaks = [], [], []
    for _ in range(simulations):
        path = []
        while len(path) < length:
            start = rng.randrange(len(values))
            path.extend(values[(start + j) % len(values)] for j in range(block_size))
        path = path[:length]
        equity = peak = 0.0
        max_dd = 0.0
        streak = max_streak = 0
        for value in path:
            equity += value
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)
            streak = streak + 1 if value < 0 else 0
            max_streak = max(max_streak, streak)
        totals.append(equity)
        drawdowns.append(max_dd)
        losing_streaks.append(max_streak)
    def q(xs: list[float], p: float) -> float:
        ys = sorted(xs); pos = (len(ys) - 1) * p; lo = int(math.floor(pos)); hi = int(math.ceil(pos))
        return ys[lo] if lo == hi else ys[lo] + (ys[hi] - ys[lo]) * (pos - lo)
    return {"state": "ready", "n": len(values), "simulations": simulations,
            "block_size": block_size, "seed": seed,
            "total_r": {"p05": q(totals, .05), "median": q(totals, .5), "p95": q(totals, .95)},
            "max_drawdown_r": {"p05": q(drawdowns, .05), "median": q(drawdowns, .5)},
            "max_losing_streak": {"median": q(losing_streaks, .5), "p95": q(losing_streaks, .95)}}
