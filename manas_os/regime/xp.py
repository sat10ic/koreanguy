"""XP regime dial — the flagship regime number.

XP recurses on the prior day's XP and z_state, driven by breadth counts and
moving-average participation. `compute_xp` is a pure function of its inputs;
`xp_for_date` wires it to the DB (today's breadth_daily row + yesterday's
regime_snapshots, or config seeds on the first run).

Recursion (per the authoritative finallynitin infographic — precise weights):
    logit(p) = log(p / (100 - p))                # p is a percent 0..100
    z_state  = 0.162*today_4.5plus + 0.838*z_prev
    log_XP   = 0.592*log(XP_prev) + 0.471*log(z_state) + 0.198*logit(10dma%) + 0.334
               - 0.067*log(decliners) - 0.077*logit(20dma%)
    XP       = exp(log_XP)

Term 5 is the 4.5%- big-decliner count (sheet `down_4pct`), per the source's
written formula. We use up_4pct / down_4pct (the sheet's 4% buckets) as the
4.5+/4.5- proxies. The z_state advancer count must come from the SAME universe
the formula was calibrated on (NIFTYMIDSML400) — see `xp_for_date`.
"""
from __future__ import annotations

import math

from manas_os import config

# Small epsilon guarding log/logit domains (never take log(0) or logit(0/100)).
_EPS = 1e-9
# XP display/recursion ceiling — reference tops out ~30; this is generous
# headroom while preventing runaway compounding on historic-rally sequences.
_XP_CAP = 250.0


def _clamp_pct(p: float) -> float:
    """Clamp a percent into the open interval (0, 100)."""
    return min(100.0 - _EPS, max(_EPS, float(p)))


def logit(p: float) -> float:
    """logit of a percent p in 0..100: log(p / (100 - p)). Domain-guarded."""
    p = _clamp_pct(p)
    return math.log(p / (100.0 - p))


def _safe_log(x: float) -> float:
    return math.log(max(float(x), _EPS))


def compute_xp(
    today_up4: float,
    today_down4: float,
    pct_above_10dma: float,
    pct_above_20dma: float,
    xp_prev: float,
    z_prev: float,
) -> tuple[float, float]:
    """One XP recursion step. Returns (xp, z_state).

    ``today_down4`` is the 4.5%- big-decliner count (term-5 penalty). Pure: no
    I/O; all log/logit inputs domain-guarded.
    """
    z_state = 0.162 * float(today_up4) + 0.838 * float(z_prev)
    log_xp = (
        0.592 * _safe_log(xp_prev)
        + 0.471 * _safe_log(z_state)
        + 0.198 * logit(pct_above_10dma)
        + 0.334
        - 0.067 * _safe_log(today_down4)
        - 0.077 * logit(pct_above_20dma)
    )
    # Cap well above the reference's ~30 ceiling. XP feeds its own next-day
    # recursion (0.592*log(XP_prev)), so an uncapped extreme-rally value
    # compounds forward; the cap both bounds the display and stops runaway.
    return min(math.exp(log_xp), _XP_CAP), z_state


def xp_for_date(conn, trade_date: str, seeds: dict | None = None) -> tuple[float, float]:
    """Compute (xp, z_state) for trade_date from the DB.

    Pulls today's breadth_daily row and the most-recent prior regime_snapshots
    xp_value/xp_z_state (strictly before trade_date). On the first run (no prior
    snapshot) it bootstraps from seeds: `seeds` dict if given, else config
    `regime.xp_seed`/`regime.xp_z_seed`.
    """
    row = conn.execute(
        "SELECT up_4pct, down_4pct, pct_above_10dma, pct_above_20dma "
        "FROM breadth_daily WHERE trade_date = ?",
        (trade_date,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no breadth_daily row for {trade_date}")

    prior = conn.execute(
        "SELECT xp_value, xp_z_state FROM regime_snapshots "
        "WHERE snapshot_date < ? AND xp_value IS NOT NULL "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (trade_date,),
    ).fetchone()

    seeds = seeds or {}
    if prior is not None:
        xp_prev = prior["xp_value"]
        z_prev = prior["xp_z_state"]
    else:
        xp_prev = seeds.get("xp_seed", config.get("regime.xp_seed", 15.0))
        z_prev = seeds.get("xp_z_seed", config.get("regime.xp_z_seed", 20.0))

    return compute_xp(
        today_up4=row["up_4pct"],
        today_down4=row["down_4pct"],
        pct_above_10dma=row["pct_above_10dma"],
        pct_above_20dma=row["pct_above_20dma"],
        xp_prev=xp_prev,
        z_prev=z_prev,
    )
