"""Horizon-derived research-governance read model.

Only mechanisms supported by canonical records are marked ready. Exact formulas
contained only in source images (notably DSR/complexity thresholds) remain
explicitly unimplemented rather than being approximated and mislabelled.
"""
from __future__ import annotations

from . import factor_health
from .schema import ensure_schema


def _count(conn, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"])


def overview(conn) -> dict:
    ensure_schema(conn)
    from manas_os.regime import regime_hmm

    experiments = _count(conn, "alpha_experiments")
    failures = _count(conn, "alpha_failure_memories")
    ablations = _count(conn, "alpha_ablation_results")
    plateau = _count(conn, "alpha_plateau_results")
    cones = _count(conn, "alpha_performance_cones")
    factor = factor_health.health(conn)
    transition = regime_hmm.transition_payload(conn)
    return {
        "shadow_only": True,
        "source": "Horizon Quant Frameworks Consolidated; sat10ic implementation policy",
        "cards": [
            {"key": "trial_accounting", "label": "Trial accounting", "state": "ready" if experiments else "warming",
             "value": experiments, "plain": "Counts every recorded attempt, including failures."},
            {"key": "dsr", "label": "Deflated Sharpe Ratio", "state": "not_implemented", "value": None,
             "plain": "Not calculated: the supplied exact formula is image-only and no verified library is wired."},
            {"key": "factor_health", "label": "Factor IC / Rank-IC", "state": factor["state"],
             "value": len(factor["rows"]), "plain": "Checks whether today’s rank relates to later 5/10/20-session returns."},
            {"key": "regime_transition", "label": "HMM persistence", "state": transition["state"],
             "value": transition.get("stay_probability"), "plain": "Measures state stickiness and transition risk—not price direction."},
            {"key": "overfit", "label": "Overfit gauntlet", "state": "ready" if ablations and plateau else "warming",
             "value": ablations + plateau, "plain": "Requires ablation and neighboring-parameter plateau evidence before promotion."},
            {"key": "failure_memory", "label": "Failure memory", "state": "ready" if failures else "warming",
             "value": failures, "plain": "Stores rejected signatures so the generator cannot rediscover the same dead end."},
            {"key": "edge_decay", "label": "Live edge health", "state": "ready" if cones else "warming",
             "value": cones, "plain": "Will compare live shadow performance with seeded block-bootstrap cones."},
        ],
        "factor_health": factor,
        "regime_transition": transition,
        "hard_boundary": "Research evidence cannot alter eligibility, stop, quantity, portfolio heat or Telegram gates.",
    }
