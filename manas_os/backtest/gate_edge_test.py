"""Does the gate's refusal actually discriminate? (2026-07-31)

Protocol pre-registered in design/EDGE_TEST_PREREGISTRATION_2026-07-31.md.
This module only measures; it never writes to the DB.

WHY THIS SHAPE AND NOT A FULL REPLAY
backtest/replay.py re-runs the live scanner per session, which is the right
architecture but costs >10 minutes per session -- 370 sessions is weeks of
compute. What exists instead is `refusals`: 186,635 point-in-time rows across
296 scan dates back to 2025-03, each stamped with the gate that rejected the
name. That is a large, dated, honest record of what the tool said NO to, and it
answers a real question without re-running anything.

The passed cohort cannot be recovered at the same scale -- `scan_candidates`
holds 65 rows across 49 dates before July 2026, because the historical replay
persisted refusals as a side effect but never persisted survivors. So the two
tests here are deliberately asymmetric:

  TEST 1 (296 dates, ~162k rows): for each failed_gate, did the REFUSED names
  under-perform the same-day universe? If a gate's rejects beat the market, that
  gate is destroying returns. This needs no passed cohort.

  TEST 2 (July 2026 only, ~15 dates): passed vs refused vs random. Small n,
  reported with the n, never dressed up as more than it is.

BIAS CONTROLS (see the pre-registration for the full ledger)
  - Entry is the NEXT session's open, never the scan day's close. The scanner
    runs on EOD data; you cannot buy at a close you only learn after the close.
    (scorecard.py:242 does exactly this and is why its numbers are optimistic.)
  - Excess return = the name's return minus the SAME-DAY universe median, so a
    rising tape is not mistaken for edge.
  - Survivorship is absent by construction: the universe for date D comes from
    daily_prices rows dated D (universe_filter.py:292), and no production code
    deletes daily_prices rows -- a since-delisted name still appears in its own
    historical sessions.
  - Significance by BLOCK bootstrap over whole scan dates. Names surfaced on one
    day share a market and a sector; treating 162k rows as 162k independent
    observations would overstate significance by roughly the clustering factor.
    n is reported as DATES alongside rows.
"""
from __future__ import annotations

import random
from bisect import bisect_right
from collections import defaultdict
from statistics import median

HORIZON = 10            # trading sessions held
BOOTSTRAP = 10_000
SEED = 20260731
COST_PCT = 0.40         # round-trip brokerage+STT+slippage; cancels in excess terms
MIN_UNIVERSE = 200      # a date with fewer priced names is not a real session


def load_prices(conn) -> dict[str, tuple[list[str], list, list]]:
    """symbol -> (dates, opens, closes), each ascending by date.

    Loaded once into memory: the alternative is ~2 queries per (symbol, date)
    pair across 296 dates, which is what made the naive version unusable.
    """
    per: dict[str, tuple[list, list, list]] = defaultdict(lambda: ([], [], []))
    cur = conn.execute(
        "SELECT symbol, trade_date, open, close FROM daily_prices "
        "WHERE series='EQ' AND close IS NOT NULL ORDER BY symbol, trade_date"
    )
    for sym, d, o, c in cur:
        dates, opens, closes = per[sym]
        dates.append(d)
        opens.append(o)
        closes.append(c)
    return dict(per)


def forward_return(prices, symbol: str, scan_date: str, horizon: int = HORIZON):
    """% return from the NEXT session's open to the close `horizon` sessions on.

    None when the name has no next session (delisted/suspended right after the
    scan) or not enough forward history. Returning None rather than falling back
    to the scan-day close is the point: a missing fill is missing data, not a
    zero-return trade.
    """
    rec = prices.get(symbol)
    if not rec:
        return None
    dates, opens, closes = rec
    i = bisect_right(dates, scan_date)       # first index strictly after scan_date
    if i >= len(dates) or i + horizon - 1 >= len(dates):
        return None
    entry = opens[i]
    if entry is None or entry <= 0:
        entry = closes[i]                    # some bhavcopy rows carry no open
        if entry is None or entry <= 0:
            return None
    exit_px = closes[i + horizon - 1]
    if exit_px is None:
        return None
    return (exit_px - entry) / entry * 100.0


def universe_on(conn, scan_date: str) -> list[str]:
    """The tradeable pool as the scanner would have built it for this date."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date=?",
        (scan_date,))]


def block_bootstrap(by_date: dict[str, list[float]], iters: int = BOOTSTRAP) -> tuple:
    """5th/50th/95th percentile of the median, resampling whole DATES.

    Resampling rows would treat one market day as N independent bets.
    """
    dates = list(by_date)
    if len(dates) < 5:
        return (None, None, None)
    rng = random.Random(SEED)
    medians = []
    for _ in range(iters):
        pool = []
        for _ in range(len(dates)):
            pool.extend(by_date[dates[rng.randrange(len(dates))]])
        if pool:
            medians.append(median(pool))
    if not medians:
        return (None, None, None)
    medians.sort()
    lo = medians[int(0.05 * len(medians))]
    mid = medians[len(medians) // 2]
    hi = medians[int(0.95 * len(medians)) - 1]
    return (lo, mid, hi)


def run(conn, start: str, end: str, verbose=print) -> dict:
    """TEST 1 — per failed_gate, the excess return of what the gate REFUSED.

    Reads `refusals` (point-in-time, written by the scanner at the time) and
    daily_prices. Writes nothing.
    """
    verbose("loading prices…")
    prices = load_prices(conn)
    verbose("  %d symbols" % len(prices))

    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT scan_date FROM refusals WHERE scan_date BETWEEN ? AND ? "
        "ORDER BY scan_date", (start, end))]
    verbose("scan dates: %d (%s .. %s)" % (len(dates), dates[0], dates[-1]))

    # excess return of refused names, bucketed by the gate that rejected them
    by_gate: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    universe_by_date: dict[str, list[float]] = {}
    rng = random.Random(SEED)
    random_by_date: dict[str, list[float]] = {}
    skipped = 0

    for d in dates:
        univ = universe_on(conn, d)
        rets = [(s, forward_return(prices, s, d)) for s in univ]
        rets = [(s, r) for s, r in rets if r is not None]
        if len(rets) < MIN_UNIVERSE:
            skipped += 1
            continue
        vals = [r for _, r in rets]
        med = median(vals)
        _tape_up[d] = med > 0                              # was the tape rising?
        universe_by_date[d] = [v - med for v in vals]      # centred by construction
        lookup = dict(rets)

        # RANDOM control: same-day draw, so it carries the same market as the
        # cohorts it is compared against.
        pick = rng.sample(vals, min(40, len(vals)))
        random_by_date[d] = [v - med for v in pick]

        for sym, gate in conn.execute(
                "SELECT symbol, failed_gate FROM refusals WHERE scan_date=?", (d,)):
            r = lookup.get(sym)
            if r is not None:
                by_gate[gate][d].append(r - med)

    verbose("skipped %d dates with a thin universe" % skipped)

    out = {"dates": len(universe_by_date), "gates": {}, "skipped_dates": skipped,
           "window": (dates[0], dates[-1])}
    for gate, per_date in sorted(by_gate.items(),
                                 key=lambda kv: -sum(len(v) for v in kv[1].values())):
        flat = [v for vs in per_date.values() for v in vs]
        lo, mid, hi = block_bootstrap(per_date)
        out["gates"][gate] = {
            "rows": len(flat), "dates": len(per_date),
            "median_excess": median(flat) if flat else None,
            "ci": (lo, hi), "boot_median": mid,
            "hit_rate": sum(1 for v in flat if v > 0) / len(flat) if flat else None,
        }
    lo, mid, hi = block_bootstrap(random_by_date)
    flat = [v for vs in random_by_date.values() for v in vs]
    out["random_control"] = {
        "rows": len(flat), "dates": len(random_by_date),
        "median_excess": median(flat) if flat else None, "ci": (lo, hi),
        "hit_rate": sum(1 for v in flat if v > 0) / len(flat) if flat else None,
    }

    # --- self-attack -------------------------------------------------------
    # A median says nothing about the left tail, and the risk gate exists to cut
    # the left tail. A gate that refuses volatile names will look "anti-
    # selective" on medians in a rising tape while still being correct about
    # ruin. So: full distribution, plus an up-tape/down-tape split. If the
    # refused cohorts only outperform when the market rose, what was measured is
    # beta, not the gate being wrong.
    up_dates = {d for d, vs in universe_by_date.items() if _tape_up.get(d)}
    out["tails"] = {}
    for gate, per_date in by_gate.items():
        flat = [v for vs in per_date.values() for v in vs]
        if len(flat) < 50:
            continue
        s = sorted(flat)
        up = [v for d, vs in per_date.items() if d in up_dates for v in vs]
        dn = [v for d, vs in per_date.items() if d not in up_dates for v in vs]
        out["tails"][gate] = {
            "p10": s[int(0.10 * len(s))], "p50": s[len(s) // 2],
            "p90": s[int(0.90 * len(s))],
            "mean": sum(s) / len(s),
            "frac_below_-10": sum(1 for v in s if v < -10) / len(s),
            "up_tape_median": median(up) if len(up) >= 20 else None,
            "down_tape_median": median(dn) if len(dn) >= 20 else None,
            "up_n": len(up), "down_n": len(dn),
        }
    return out


# populated during run(); keyed by scan_date -> was the universe median positive
_tape_up: dict[str, bool] = {}
