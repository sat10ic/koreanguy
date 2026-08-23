"""XP regime dial — the flagship regime number.

Adopted (copied, not imported) from ``manas_os/regime/xp.py`` on 2026-08-23
for TraderLog W4, whole file (115 lines), per DECISIONS.md 2026-08-23
"Adopt the XP and MBI scores, but not the regime governor". Once copied this
file is TraderLog's own; drift from the manas_os original is expected and
fine (CANONICAL.md §5).

XP recurses on the prior day's XP and z_state, driven by breadth counts and
moving-average participation. ``compute_xp`` is UNCHANGED — same six-term log
model, same weights, byte-for-byte the same math as manas_os. Only
``xp_for_date`` (the DB-wiring half) was adapted:

Recursion (per the authoritative finallynitin infographic — precise weights):
    logit(p) = log(p / (100 - p))                # p is a percent 0..100
    z_state  = 0.162*today_4.5plus + 0.838*z_prev
    log_XP   = 0.592*log(XP_prev) + 0.471*log(z_state) + 0.198*logit(10dma%) + 0.334
               - 0.067*log(decliners) - 0.077*logit(20dma%)
    XP       = exp(log_XP)

Changes made during adoption (drift, documented per CANONICAL.md §5 — this is
the load-bearing part of the whole adoption, see
DECISIONS.md 2026-08-23 and TASKS.md W4):

  * ``xp_for_date`` now queries TraderLog's own ``regime_daily`` table
    (trade_date PK) instead of manas_os's ``regime_snapshots``.
  * **Gap handling.** manas_os's original blindly takes "the most recent PRIOR
    row with xp_value NOT NULL", with no bound on how far back that row is —
    which would silently carry a 46-day-old XP value across TraderLog's real
    data gap (2025-05-05 -> 2025-06-20, verified on disk) as if nothing
    happened. That is exactly the fabrication CANONICAL.md and DECISIONS.md
    warn against. ``xp_for_date`` now takes a ``gap_threshold_days`` bound
    (default ``DEFAULT_GAP_THRESHOLD_DAYS`` = 5 calendar days): if the most
    recent prior XP-bearing row is farther back than that — or there is no
    prior row at all — the recursion is NOT continued. It is treated as a
    fresh start: reseeded from config/seeds, exactly like day 1. The function
    now returns a third element, ``reseeded: bool``, so callers (and tests)
    can see exactly which dates were chain breaks rather than silently
    guessing. 5 days was chosen after inspecting the real bhavcopy calendar:
    every genuine NSE weekend/holiday gap in the corpus is <=4 calendar days;
    the one 46-day hole is unambiguously an ingestion gap, not a holiday.
  * ``manas_os.config`` -> ``traderlog.config`` (keys ``regime.xp_seed`` /
    ``regime.xp_z_seed``, same defaults 15.0 / 20.0).

Term 5 is the 4.5%- big-decliner count (sheet `down_4pct`), per the source's
written formula. We use up_4pct / down_4pct (the sheet's 4% buckets) as the
4.5+/4.5- proxies. The z_state advancer count must come from the SAME universe
the formula was calibrated on (NIFTYMIDSML400) — see ``adopted/universe_breadth.py``.
"""
from __future__ import annotations

import math

from traderlog import config

# Small epsilon guarding log/logit domains (never take log(0) or logit(0/100)).
_EPS = 1e-9
# XP display/recursion ceiling — reference tops out ~30; this is generous
# headroom while preventing runaway compounding on historic-rally sequences.
_XP_CAP = 250.0

# See "Gap handling" in the module docstring: the one genuine gap in the real
# bhavcopy corpus is 46 calendar days; every ordinary weekend/holiday gap is
# <=4. 5 gives one day of slack and unambiguously isolates the real break.
DEFAULT_GAP_THRESHOLD_DAYS = 5


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
    I/O; all log/logit inputs domain-guarded. UNCHANGED from manas_os.
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
    return min(math.exp(log_xp), _XP_CAP), z_state


def _days_between(a: str, b: str) -> int:
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def xp_for_date(
    conn,
    trade_date: str,
    seeds: dict | None = None,
    gap_threshold_days: int = DEFAULT_GAP_THRESHOLD_DAYS,
) -> tuple[float, float, bool]:
    """Compute (xp, z_state, reseeded) for trade_date from the DB.

    Pulls today's breadth_daily row and the most-recent prior regime_daily
    xp_value/xp_z_state (strictly before trade_date). If that prior row is
    farther back than ``gap_threshold_days`` — or there is none — the
    recursion is NOT continued: it reseeds from ``seeds`` (falling back to
    config ``regime.xp_seed``/``regime.xp_z_seed``) and ``reseeded`` is True.
    Backfill callers MUST process dates in strict ascending order — this
    function only ever looks backward.
    """
    row = conn.execute(
        "SELECT up_4pct, down_4pct, pct_above_10dma, pct_above_20dma "
        "FROM breadth_daily WHERE trade_date = ?",
        (trade_date,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no breadth_daily row for {trade_date}")

    prior = conn.execute(
        "SELECT trade_date, xp_value, xp_z_state FROM regime_daily "
        "WHERE trade_date < ? AND xp_value IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT 1",
        (trade_date,),
    ).fetchone()

    seeds = seeds or {}
    reseeded = False
    if prior is not None and _days_between(prior["trade_date"], trade_date) <= gap_threshold_days:
        xp_prev = prior["xp_value"]
        z_prev = prior["xp_z_state"]
    else:
        reseeded = True
        xp_prev = seeds.get("xp_seed", config.get("regime.xp_seed", 15.0))
        z_prev = seeds.get("xp_z_seed", config.get("regime.xp_z_seed", 20.0))

    xp, z = compute_xp(
        today_up4=row["up_4pct"],
        today_down4=row["down_4pct"],
        pct_above_10dma=row["pct_above_10dma"],
        pct_above_20dma=row["pct_above_20dma"],
        xp_prev=xp_prev,
        z_prev=z_prev,
    )
    return xp, z, reseeded
