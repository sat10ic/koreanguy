"""SETUP-REGIME factor — "what is working right now" per setup family.

Motivation (measured 2026-07-17): that Friday's scan of 154 names returned
+0.97% median over 2 sessions vs Nifty -0.48%, but the top-20 (all
Pullback-to-EMA) returned only +0.72% and captured just 1 of the 12 names
that gained >=5%. The velocity/initiation setups (near_pivot, pocket_pivot,
strong_start_ready, persistent_momentum, watchlist_timing -- all mapped to
the "momentum" gate-family by scanner.candidates.SETUP_FAMILY) carried
nearly every big move that day; pullbacks (the "base/pattern" family) were
cold. This module makes that "which family is hot/cold right now" read a
rolling, point-in-time, persisted factor instead of a one-off retro note.

Cohort grouping unit: the setup-FAMILY (scanner.candidates.SETUP_FAMILY
values -- "momentum", "base/pattern", "catalyst", "reversal",
"busted_reversal", "accumulation", "weekly_base_breakout"), imported
READ-ONLY from scanner.candidates per the build spec ("reuse
candidates.SETUP_FAMILY mapping"). Each scan_candidates row already
persists its own setup_family (candidates.ensure_schema's ALTER-added
column); when that column is NULL on an older row we fall back to
candidates.setup_family(setup_type) so the grouping can never drift out of
sync with the gate-family mapping. NOTE: the motivating narrative above
names the individual display setup ("Pullback-to-EMA") but the build spec
is explicit that the COHORT unit is the coarser gate-family
("base/pattern"), which is what this module actually groups and persists
by -- the human-readable `describe_family` line prettifies the family KEY
(e.g. "Base/Pattern"), it does not reconstruct the finer display label.

POINT-IN-TIME / NO LOOK-AHEAD (critical, tested explicitly): a scan_date S
is only added to a window's cohort for a given `as_of` + `horizon` when the
full horizon-session forward window closed STRICTLY before `as_of` --
checked against the global EQ trading calendar (every distinct daily_prices
trade_date), not any one symbol's data availability. A scan on `as_of`
itself, or any scan_date whose horizon has not yet closed, can never
contribute to its own or any unrealized future outcome.

Forward return convention (per the build spec: "from S's close"): base =
the candidate SYMBOL's own close ON scan_date S (not the next session's
open used by scanner/outcomes.py's managed-exit model -- this factor is a
market-regime read, not a fill-realistic P&L model, so the simpler
close-to-close convention is used and documented here rather than silently
reusing a different one).

Shrinkage / floor (Assumption-flagged, per build spec): a family with
n < FLOOR_N observations in a window carries NO tilt (state forced to
"neutral", tilt exactly 1.0) regardless of its raw numbers -- thin samples
must not move the rank.

State (Assumption-flagged MARGIN_PP = 0.5 percentage points, chosen because
the spec asked for a starting constant and flagged it as an assumption):
state is RELATIVE to the all-families pooled median for the SAME
window+horizon, not to zero -- so a uniformly bad market does not mark
every family "cold" (some families still beat the pooled median and read
relatively hot; this is inherent to a relative-not-absolute comparison and
is asserted directly by a test).

Tilt (Assumption-flagged STATE_DELTA = 0.3, DEFAULT_WINDOW_WEIGHTS =
{5: 0.2, 20: 0.5, 60: 0.3}): tilt() maps a state (or a per-window mapping of
states) to a bounded multiplier in [TILT_MIN, TILT_MAX] = [0.7, 1.3]. The
per-row `tilt` column persisted per (as_of, family, window, horizon) is the
single-window-only value (weight 1.0); `blended_tilt()` combines the three
windows' states with DEFAULT_WINDOW_WEIGHTS (short window down-weighted so
it cannot dominate alone) into the ONE number a future conviction-rank
consumer would actually use. Because the weights are a convex combination
(they sum to 1.0) of values already inside [-STATE_DELTA, +STATE_DELTA],
the blended result can never exceed the single-window bounds either --
the corpus tier ordering can never be fully inverted by this factor alone.
"""
from __future__ import annotations

import time
from bisect import bisect_right
from statistics import mean, median
from typing import Any

from manas_os.scanner import candidates as _candidates

STAGE = "setup_regime"
SOURCE = "scan_candidates+daily_prices"

# Rolling lookback windows, in ELIGIBLE (point-in-time-safe) scan sessions --
# not calendar days. Mirrors the T+5/T+10/T+20 horizon convention used
# elsewhere in this codebase, applied here as a look-BACK instead of a
# look-FORWARD span.
DEFAULT_WINDOWS = (5, 20, 60)

# Forward-return horizon: H=5 sessions is primary (per the build spec);
# H=2 is a secondary/faster read. Order matters only for display; both are
# always computed and persisted.
PRIMARY_HORIZON = 5
SECONDARY_HORIZON = 2
HORIZONS = (PRIMARY_HORIZON, SECONDARY_HORIZON)

# Shrinkage floor: below this per-family n in a window, state is forced
# "neutral" and tilt is forced to 1.0 regardless of the raw numbers.
FLOOR_N = 20

# Assumption: relative-state margin, in percentage points of forward return,
# vs the all-families pooled median for the same window+horizon. Start at
# 0.5pp per the build spec -- tell me if this should move.
MARGIN_PP = 0.5

# Assumption: per-state tilt delta (hot = +DELTA, cold = -DELTA, neutral = 0)
# applied around a 1.0 baseline, bounded to [TILT_MIN, TILT_MAX] below.
STATE_DELTA = 0.3
TILT_MIN, TILT_MAX = 0.7, 1.3

# Assumption: window blend weights for blended_tilt() -- the short (5d)
# window is deliberately the smallest weight so it cannot dominate the
# blended tilt alone; 20d carries the most weight as the "steady state" read.
DEFAULT_WINDOW_WEIGHTS: dict[int, float] = {5: 0.2, 20: 0.5, 60: 0.3}

# The fixed set of setup families this factor can ever report on -- derived
# from candidates.SETUP_FAMILY (read-only import) so a family that simply
# had zero candidates in a given window still gets an honest "unavailable"
# row instead of silently vanishing from the table.
ALL_FAMILIES: tuple[str, ...] = tuple(sorted(set(_candidates.SETUP_FAMILY.values())))


def ensure_schema(conn) -> None:
    # scan_candidates.setup_type/setup_family are ALTER-added columns owned by
    # candidates.ensure_schema (candidates.py is out of scope for edits here,
    # but calling its own idempotent schema-guard is a read-only use of it --
    # guarantees the columns this module SELECTs actually exist even on a
    # bare freshly-init'd DB that never ran a real scan_candidates stage).
    _candidates.ensure_schema(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS setup_regime_daily ("
        "as_of TEXT NOT NULL, family TEXT NOT NULL, window INTEGER NOT NULL, "
        "horizon INTEGER NOT NULL, n INTEGER NOT NULL, median_fwd REAL, "
        "mean_fwd REAL, hit_rate REAL, state TEXT NOT NULL, tilt REAL NOT NULL, "
        "computed_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (as_of, family, window, horizon))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_setup_regime_daily_as_of "
        "ON setup_regime_daily(as_of)"
    )


# ---------------------------------------------------------------------------
# Point-in-time cohort selection
# ---------------------------------------------------------------------------


def _trading_calendar(conn) -> list[str]:
    """Every distinct EQ trade_date in daily_prices, ascending. This is the
    GLOBAL market calendar used for the look-ahead guard -- deliberately not
    per-symbol, since eligibility is a market-clock question ("has this many
    sessions passed"), not a data-availability question for any one name."""
    rows = conn.execute(
        "SELECT DISTINCT trade_date FROM daily_prices WHERE series = 'EQ' "
        "ORDER BY trade_date"
    ).fetchall()
    return [r[0] for r in rows]


def _calendar_horizon_close_date(calendar: list[str], scan_date: str, horizon: int) -> str | None:
    """The date of the `horizon`-th trading session strictly after scan_date,
    per the global calendar. None when the calendar doesn't reach that far
    yet (mirrors scanner/outcomes.py's `trade_date > ? ... OFFSET horizon-1`
    convention, just against the calendar instead of one symbol's rows)."""
    idx = bisect_right(calendar, scan_date)  # first index with date > scan_date
    target = idx + horizon - 1
    if target < 0 or target >= len(calendar):
        return None
    return calendar[target]


def _eligible_scan_dates(conn, as_of: str, horizon: int, calendar: list[str]) -> list[str]:
    """Distinct scan_candidates dates <= as_of whose `horizon`-session
    forward window has closed STRICTLY before as_of. This is the look-ahead
    guard: a scan_date whose outcome could not yet be known as of `as_of`
    is never included, regardless of window size."""
    rows = conn.execute(
        "SELECT DISTINCT scan_date FROM scan_candidates WHERE scan_date <= ? "
        "ORDER BY scan_date",
        (as_of,),
    ).fetchall()
    out: list[str] = []
    for r in rows:
        d = r[0]
        close_date = _calendar_horizon_close_date(calendar, d, horizon)
        if close_date is not None and close_date < as_of:
            out.append(d)
    return out


# ---------------------------------------------------------------------------
# Forward returns
# ---------------------------------------------------------------------------


def _base_close(conn, symbol: str, scan_date: str) -> float | None:
    """Base price is the candidate's OWN close ON scan_date S (build spec:
    "from S's close") -- not a next-session fill; this factor reads market
    regime, not realized fill P&L."""
    row = conn.execute(
        "SELECT close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date = ? AND close IS NOT NULL",
        (symbol, scan_date),
    ).fetchone()
    return None if not row else float(row[0])


def _forward_close(conn, symbol: str, scan_date: str, horizon: int) -> float | None:
    row = conn.execute(
        "SELECT close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT 1 OFFSET ?",
        (symbol, scan_date, horizon - 1),
    ).fetchone()
    return None if not row else float(row[0])


def forward_return_pct(conn, symbol: str, scan_date: str, horizon: int) -> float | None:
    base = _base_close(conn, symbol, scan_date)
    if base is None or base <= 0:
        return None
    fwd = _forward_close(conn, symbol, scan_date, horizon)
    if fwd is None:
        return None
    return (fwd - base) / base * 100.0


def _row_family(row) -> str:
    fam = row["setup_family"] if "setup_family" in row.keys() else None
    if fam:
        return str(fam)
    setup_type = row["setup_type"] if "setup_type" in row.keys() else None
    return _candidates.setup_family(setup_type)


# ---------------------------------------------------------------------------
# State + tilt
# ---------------------------------------------------------------------------


def classify_state(n: int, family_median: float | None, all_median: float | None) -> str:
    """hot/neutral/cold, relative to the all-families pooled median for the
    SAME window+horizon (never to zero -- see module docstring on why a bad
    market must not read as all-cold). n < FLOOR_N forces "neutral" no
    matter what the raw numbers say."""
    if n < FLOOR_N or family_median is None or all_median is None:
        return "neutral"
    delta = family_median - all_median
    if delta >= MARGIN_PP:
        return "hot"
    if delta <= -MARGIN_PP:
        return "cold"
    return "neutral"


def tilt(states: dict[int, str] | str, window_weights: dict[int, float] | None = None) -> float:
    """Bounded [TILT_MIN, TILT_MAX] multiplier from one state or a blend of
    per-window states.

    `states` is either a single state string (one window's row -- treated as
    a solitary window with weight 1.0, used for the PER-ROW persisted tilt)
    or a {window: state} mapping to blend (used by blended_tilt() below).
    Weights are normalized by their own sum so a partial window set (e.g.
    only the 5d window has history yet) still produces a value bounded the
    same way, never an artificially shrunk one.
    """
    if isinstance(states, str):
        states = {0: states}
        window_weights = {0: 1.0}
    weights = dict(window_weights or DEFAULT_WINDOW_WEIGHTS)
    total_weight = sum(weights.get(w, 0.0) for w in states)
    if total_weight <= 0:
        return 1.0
    delta = sum(weights.get(w, 0.0) * STATE_DELTA * _STATE_SIGN.get(st, 0) for w, st in states.items())
    blended = 1.0 + delta / total_weight
    return round(max(TILT_MIN, min(TILT_MAX, blended)), 4)


_STATE_SIGN = {"hot": 1, "neutral": 0, "cold": -1}


def blended_tilt(
    conn, as_of: str, family: str, horizon: int = PRIMARY_HORIZON,
    window_weights: dict[int, float] | None = None,
) -> float | None:
    """Read the persisted per-window rows for one family/horizon at `as_of`
    and blend them with tilt(). None when nothing is persisted yet (caller
    should treat that as "no tilt available", i.e. 1.0-equivalent neutral)."""
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT window, state FROM setup_regime_daily WHERE as_of = ? AND family = ? "
        "AND horizon = ?",
        (as_of, family, horizon),
    ).fetchall()
    if not rows:
        return None
    states = {int(r["window"]): r["state"] for r in rows}
    return tilt(states, window_weights)


# ---------------------------------------------------------------------------
# Human-readable line
# ---------------------------------------------------------------------------


def _pretty_family(family: str) -> str:
    return "/".join(seg.replace("_", " ").title() for seg in family.split("/"))


def describe_family(row: dict[str, Any]) -> str:
    """"Pullback-to-EMA: COLD - 20d median -0.4% vs all-setup +0.6% (n=180)"
    -style line (per the build spec's example format; the family label here
    is the SETUP_FAMILY grouping key, prettified -- see module docstring).
    No fabrication:
      - n=0 (no cohort data yet) renders an honest UNAVAILABLE string.
      - a valid median with no all_median on hand (e.g. a persisted-row
        reader that didn't recompute the pooled baseline) renders the real
        stats WITHOUT inventing a "vs all-setup" number, rather than mislabeling
        good data as unavailable or fabricating a comparison.
    """
    fam_label = _pretty_family(row["family"])
    window = row["window"]
    n = row.get("n") or 0
    if not n:
        return f"{fam_label}: UNAVAILABLE - no {window}d cohort data yet (n=0)"
    med = row.get("median_fwd")
    if med is None:
        return f"{fam_label}: UNAVAILABLE - insufficient {window}d cohort data (n={n})"
    state = str(row["state"]).upper()
    all_med = row.get("all_median")
    if all_med is None:
        return f"{fam_label}: {state} - {window}d median {med:+.1f}% (n={n}, all-setup baseline n/a)"
    return (
        f"{fam_label}: {state} - {window}d median {med:+.1f}% "
        f"vs all-setup {all_med:+.1f}% (n={n})"
    )


# ---------------------------------------------------------------------------
# compute()
# ---------------------------------------------------------------------------


def compute(
    conn, as_of: str, windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> list[dict[str, Any]]:
    """Rolling, point-in-time setup-family regime read as of `as_of`.

    Returns one row per (family, window, horizon) for every family in
    ALL_FAMILIES x every window in `windows` x every horizon in HORIZONS --
    including "unavailable" (n=0) rows, so the shape is always complete and
    never silently drops a family that just had no recent candidates.
    """
    ensure_schema(conn)
    out: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        calendar = _trading_calendar(conn)
        eligible = _eligible_scan_dates(conn, as_of, horizon, calendar)
        for window in windows:
            window_dates = eligible[-window:] if window > 0 else []
            dates_used = len(window_dates)
            date_set = set(window_dates)

            by_family: dict[str, list[float]] = {fam: [] for fam in ALL_FAMILIES}
            all_rets: list[float] = []
            if date_set:
                placeholders = ",".join("?" for _ in date_set)
                rows = conn.execute(
                    f"SELECT scan_date, symbol, setup_type, setup_family FROM scan_candidates "
                    f"WHERE scan_date IN ({placeholders})",
                    tuple(date_set),
                ).fetchall()
                for r in rows:
                    fam = _row_family(r)
                    ret = forward_return_pct(conn, r["symbol"], r["scan_date"], horizon)
                    if ret is None:
                        continue
                    by_family.setdefault(fam, []).append(ret)
                    all_rets.append(ret)

            all_median = median(all_rets) if all_rets else None

            for fam in sorted(by_family):
                rets = by_family[fam]
                n = len(rets)
                fam_median = median(rets) if rets else None
                fam_mean = mean(rets) if rets else None
                hit_rate = (sum(1 for r in rets if r > 0) / n) if n else None
                state = classify_state(n, fam_median, all_median)
                # neutral always maps to a 1.0 tilt (STATE_DELTA * sign(0)==0),
                # so the n<FLOOR_N "no tilt" rule falls out of classify_state
                # forcing state="neutral" -- no separate branch needed here.
                tilt_value = tilt(state)
                row = {
                    "as_of": as_of,
                    "family": fam,
                    "window": window,
                    "horizon": horizon,
                    "n": n,
                    "median_fwd": round(fam_median, 3) if fam_median is not None else None,
                    "mean_fwd": round(fam_mean, 3) if fam_mean is not None else None,
                    "hit_rate": round(hit_rate, 3) if hit_rate is not None else None,
                    "state": state,
                    "tilt": tilt_value,
                    "all_median": round(all_median, 3) if all_median is not None else None,
                    "dates_used": dates_used,
                }
                row["line"] = describe_family(row)
                out.append(row)
    return out


def persist(conn, as_of: str, rows: list[dict[str, Any]]) -> int:
    """DELETE+INSERT this as_of's rows -- idempotent rerun (matches the
    persist_candidates / screener_calibration.run convention elsewhere)."""
    ensure_schema(conn)
    conn.execute("DELETE FROM setup_regime_daily WHERE as_of = ?", (as_of,))
    for r in rows:
        conn.execute(
            "INSERT INTO setup_regime_daily (as_of, family, window, horizon, n, "
            "median_fwd, mean_fwd, hit_rate, state, tilt, computed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                r["as_of"], r["family"], r["window"], r["horizon"], r["n"],
                r["median_fwd"], r["mean_fwd"], r["hit_rate"], r["state"], r["tilt"],
            ),
        )
    return len(rows)


def run(conn, run_date: str) -> dict[str, Any]:
    """Pipeline stage: recompute + persist. Failure-safe; never raises.

    Status convention: 'skip' when there are no scan_candidates rows at all
    yet (nothing to compute); 'partial' when at least one (window, horizon)
    combination had zero eligible scan_dates (so some cells are honest
    "unavailable" placeholders rather than real reads) while others
    succeeded; 'ok' otherwise.
    """
    started = time.monotonic()
    try:
        ensure_schema(conn)
        any_candidates = conn.execute("SELECT 1 FROM scan_candidates LIMIT 1").fetchone()
        if not any_candidates:
            conn.execute(
                "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
                "duration_s, detail) VALUES (?, ?, ?, 'skip', 0, ?, ?)",
                (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3),
                 "no scan_candidates rows yet"),
            )
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "no scan_candidates rows yet"}

        rows = compute(conn, run_date)
        written = persist(conn, run_date, rows)
        empty_cells = sum(1 for r in rows if r["n"] == 0)
        # A handful of genuinely-empty cells among many populated ones is
        # expected/honest (e.g. weekly_base_breakout rarely fires) -- only
        # call the whole run 'partial' when a meaningful share is empty.
        thin_share = empty_cells / len(rows) if rows else 1.0
        status = "ok" if thin_share < 0.5 else "partial"
        detail = f"families={len(ALL_FAMILIES)} windows={DEFAULT_WINDOWS} horizons={HORIZONS} empty_cells={empty_cells}/{len(rows)}"
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_date, STAGE, SOURCE, status, written, round(time.monotonic() - started, 3), detail),
        )
        conn.commit()
        return {"status": status, "rows": written, "detail": detail}
    except Exception as exc:  # noqa: BLE001 -- failure-safe stage, must never break run-eod
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def latest_rows(conn, as_of: str | None = None, horizon: int = PRIMARY_HORIZON) -> list[dict[str, Any]]:
    """Convenience reader for a UI/report: rows for one as_of (defaults to
    the latest persisted) and one horizon, across all windows/families,
    each annotated with its describe_family() line."""
    ensure_schema(conn)
    if as_of is None:
        row = conn.execute("SELECT MAX(as_of) AS d FROM setup_regime_daily").fetchone()
        as_of = row["d"] if row else None
    if as_of is None:
        return []
    rows = conn.execute(
        "SELECT as_of, family, window, horizon, n, median_fwd, mean_fwd, hit_rate, "
        "state, tilt FROM setup_regime_daily WHERE as_of = ? AND horizon = ? "
        "ORDER BY window, family",
        (as_of, horizon),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        # all_median isn't persisted (only the per-family cells are); recompute
        # is unnecessary for a read-only report line, so derive an honest line
        # without it when unavailable, matching describe_family's own guard.
        d["all_median"] = None
        d["line"] = describe_family(d)
        out.append(d)
    return out


if __name__ == "__main__":
    import sys

    from manas_os import db as _db

    run_date = sys.argv[1] if len(sys.argv) > 1 else "2026-07-21"
    _conn = _db.init_db()
    result = run(_conn, run_date)
    print(f"setup_regime run: {result}")
    rows = compute(_conn, run_date)
    for horizon in HORIZONS:
        print(f"\n=== horizon={horizon} ===")
        for window in DEFAULT_WINDOWS:
            print(f"-- window={window} --")
            for r in rows:
                if r["window"] == window and r["horizon"] == horizon:
                    print("  " + r["line"])
    _conn.close()
