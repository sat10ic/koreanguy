"""XP regime dial — the flagship regime number.

Adopted (copied, not imported) from ``manas_os/regime/xp.py`` on 2026-08-23
for TraderLog W4, whole file (115 lines), per DECISIONS.md 2026-08-23
"Adopt the XP and MBI scores, but not the regime governor". Once copied this
file is TraderLog's own; drift from the manas_os original is expected and
fine (CANONICAL.md §5).

XP recurses on the prior day's XP and z_state, driven by breadth PERCENT
inputs and moving-average participation. ``compute_xp`` is UNCHANGED — same
six-term log model, same weights, byte-for-byte the same math as manas_os.
Only ``xp_for_date`` (the DB-wiring half) was adapted:

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
    fresh start, exactly like day 1 (see "Reseed-time z seeding" below for
    what a reseed is seeded from). The function
    now returns a third element, ``reseeded: bool``, so callers (and tests)
    can see exactly which dates were chain breaks rather than silently
    guessing. 5 days was chosen after inspecting the real bhavcopy calendar:
    every genuine NSE weekend/holiday gap in the corpus is <=4 calendar days;
    the one 46-day hole is unambiguously an ingestion gap, not a holiday.
  * ``manas_os.config`` -> ``traderlog.config`` (keys ``regime.xp_seed`` /
    ``regime.xp_z_seed``, same defaults 15.0 / 20.0).

Term 5 is the 4.5%- big-decliner input (sheet `down_4pct`), per the source's
written formula. We use up_4pct / down_4pct (the sheet's 4% buckets) as the
4.5+/4.5- proxies.

Input convention — PERCENT, empirically validated (C6 RETRACTED 2026-08-24,
design/AUDIT_LEDGER.md): ``today_up4``/``today_down4`` are the
``breadth_daily.up_4pct``/``down_4pct`` PERCENTAGES (0..100) of the
NIFTYMIDSML400 universe, fed straight in UNCONVERTED. A prior audit pass read
this module's old "count" wording and "corrected" the pipeline to feed
advancer/decliner COUNTS (percent * universe / 100, ``adopted/regime_daily.py``)
— a ~4x scale error on a ~400-name universe. Recomputing all 451 sessions under
six input conventions proved the percent convention is the empirically correct
one: median ~7.7 against the reference "tops out ~30", most days LOW; the
count convention put half of all trading days above the top of the dial. C6 is
withdrawn; the call-site conversion is removed.

Reseed-time z seeding (C8, design/AUDIT_LEDGER.md 2026-08-24): at a reseed
point (first session of the series, or after a chain-break gap) the recursion
used to start from the count-scale constant seeds (xp_seed 15.0 /
xp_z_seed 20.0). z_state = 0.162*up4 + 0.838*z_prev has a ~1/0.162 = 6-session
z memory, and log_XP carries 0.592*log(XP_prev), so a mis-scaled 20.0 z-seed
took ~15-25 sessions to wash out and produced _XP_CAP (250.0) hits plus an
EXTREME band cluster at series start (real dates 2024-09-17 -> 2024-09-26) — a
seed transient, not a market event. ``xp_for_date`` now seeds the z-state at a
reseed point from that session's own observed ``up_4pct`` (percent scale)
instead of the constant; the ``xp_z_seed`` config value is only a last-resort
fallback when no observed breadth value exists. The recursion math itself
(``compute_xp``) and ``_XP_CAP`` are UNCHANGED. The z_state advancer input
must come from the SAME universe the formula was calibrated on
(NIFTYMIDSML400) — see ``adopted/universe_breadth.py``.
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

    ``today_up4``/``today_down4`` are the breadth_daily ``up_4pct`` /
    ``down_4pct`` PERCENTAGES (0..100) — the empirically validated input
    convention (C6 retracted, design/AUDIT_LEDGER.md 2026-08-24);
    ``today_down4`` is the 4.5%- big-decliner percent (term-5 penalty). Pure:
    no I/O; all log/logit inputs domain-guarded. UNCHANGED from manas_os.
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
    today_up4: float | None = None,
    today_down4: float | None = None,
    prior: tuple[float, float] | None = None,
) -> tuple[float, float, bool]:
    """Compute (xp, z_state, reseeded) for trade_date from the DB.

    Pulls today's breadth_daily row and the most-recent prior regime_daily
    xp_value/xp_z_state (strictly before trade_date). If that prior row is
    farther back than ``gap_threshold_days`` — or there is none — the
    recursion is NOT continued: it reseeds and ``reseeded`` is True. At a
    reseed point the z-state is seeded from THIS session's own observed
    ``up_4pct`` (percent scale — C8, design/AUDIT_LEDGER.md 2026-08-24), so
    the recursion starts on the correct z scale instead of unwinding from the
    count-scale xp_z_seed constant for ~15-25 sessions; ``xp_prev`` starts
    from the ``xp_seed`` config value (XP has no observable seed — it is the
    recursion's own output). The ``xp_z_seed`` config constant is used only
    when no observed breadth value exists (a NULL ``up_4pct`` row; such a
    row then fails at ``compute_xp`` rather than fabricating a number, and
    ``backfill`` records the date as failed). Backfill callers MUST process
    dates in strict ascending order — this function only ever looks backward.

    ``prior``: explicit in-memory chain override ``(xp_prev, z_prev)``. When
    given it takes precedence over the DB prior lookup AND over config seeds,
    and ``reseeded`` is always False — the caller is explicitly threading the
    recursion, never starting fresh. This is what ``backfill``'s warm-up phase
    uses to chain the first ``warmup_sessions`` sessions in memory before any
    row is persisted (see adopted/regime_daily.py, C8 second half).

    ``today_up4``/``today_down4``: when given, these OVERRIDE the values
    otherwise read straight from ``breadth_daily.up_4pct``/``down_4pct`` and
    are also the z-seed source at a reseed point. The DEFAULT is to read the
    raw percent columns — the empirically validated convention (C6 RETRACTED
    2026-08-24: feeding converted COUNTS was a ~4x scale error, see
    ``adopted/regime_daily.py``, which no longer converts). The override
    exists only for callers that want to exercise the recursion mechanics in
    isolation (this module's own tests), not as a production path.
    """
    row = conn.execute(
        "SELECT up_4pct, down_4pct, pct_above_10dma, pct_above_20dma "
        "FROM breadth_daily WHERE trade_date = ?",
        (trade_date,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no breadth_daily row for {trade_date}")

    db_prior = conn.execute(
        "SELECT trade_date, xp_value, xp_z_state FROM regime_daily "
        "WHERE trade_date < ? AND xp_value IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT 1",
        (trade_date,),
    ).fetchone()

    seeds = seeds or {}
    reseeded = False
    if prior is not None:
        # Explicit in-memory chain (warm-up threading): beats the DB lookup,
        # beats config seeds, and is never a reseed.
        xp_prev, z_prev = prior
    elif db_prior is not None and _days_between(db_prior["trade_date"], trade_date) <= gap_threshold_days:
        xp_prev = db_prior["xp_value"]
        z_prev = db_prior["xp_z_state"]
    else:
        reseeded = True
        # C8 (design/AUDIT_LEDGER.md 2026-08-24): at a reseed point, seed the
        # z-state from THIS session's own observed up_4pct (percent scale)
        # instead of the count-scale constant seed. z_state has a
        # ~1/0.162 = 6-session memory, so a mis-scaled constant seed takes
        # ~15-25 sessions to wash out — the _XP_CAP hits and EXTREME band
        # cluster at series start (2024-09-17 -> 2024-09-26). xp_prev keeps
        # the xp_seed config start (XP-scale; XP has no observable seed). The
        # xp_z_seed constant remains only as the fallback when no observed
        # breadth value exists (a NULL up_4pct row).
        xp_prev = seeds.get("xp_seed", config.get("regime.xp_seed", 15.0))
        observed_up4 = today_up4 if today_up4 is not None else row["up_4pct"]
        z_prev = (
            float(observed_up4)
            if observed_up4 is not None
            else seeds.get("xp_z_seed", config.get("regime.xp_z_seed", 20.0))
        )

    xp, z = compute_xp(
        today_up4=today_up4 if today_up4 is not None else row["up_4pct"],
        today_down4=today_down4 if today_down4 is not None else row["down_4pct"],
        pct_above_10dma=row["pct_above_10dma"],
        pct_above_20dma=row["pct_above_20dma"],
        xp_prev=xp_prev,
        z_prev=z_prev,
    )
    return xp, z, reseeded
