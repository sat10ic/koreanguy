"""SHIP-1 item 8 — screener-hit forward-return calibration.

We ingest ~4,932 ChartsMaze screener hits nightly (screener_hits table) and
have never measured whether any given screener's hits actually go up
afterwards. This is the ONE writer for `screener_calibration`: per screener
key, per horizon (T+5/T+10/T+20), the forward close-to-close return
distribution of its hits vs a universe baseline.

Entry/exit convention (consistent with scanner/outcomes.py):
  - entry  = the NEXT session's open after the hit's trade_date (a screener
    hit is a signal generated ON trade_date; the honest fill is the next
    session, never same-day/pivot).
  - exit   = the close of the horizon-th trading session strictly after
    trade_date (T+5/T+10/T+20 close-to-close, unmanaged -- no stop; a
    screener hit carries no plan/stop, unlike a persisted setup candidate).

Baseline (documented choice): a RANDOM-SAMPLE universe baseline, not the
full EQ universe. Computing every EQ symbol's forward return on every
distinct hit-date would be O(hit_dates x ~2000 symbols x 3 horizons) --
too slow for a nightly stage. Instead, for each distinct trade_date that
appears in screener_hits, take a deterministic stride-sample of that day's
EQ universe (alphabetical, every Nth symbol, capped at BASELINE_SAMPLE_CAP
symbols/date) and compute the same forward return. All baseline
observations across all hit-dates are pooled into ONE global baseline per
horizon, shared by every screener (the baseline is date-STRATIFIED --
built only from dates screeners actually fired on -- but not screener- or
symbol-specific). This is deliberately conservative/simple over a
per-screener-exact-date baseline; it still tells you "hits from screener X
beat/lagged an average EQ name on the same calendar footprint."

n<30 rows are not dropped -- they are computed and persisted (so the count
itself is visible/auditable) but callers MUST treat them as UNPROVEN via
TRUST_FLOOR_N, matching the scanner/expectancy.py trust-ladder convention
used everywhere else in this codebase. Idempotent: reruns for the same
as_of DELETE+INSERT that as_of's rows only.
"""
from __future__ import annotations

import time
from statistics import median
from typing import Any

STAGE = "screener_calibration"
SOURCE = "screener_hits+daily_prices"
HORIZONS = (5, 10, 20)
TRUST_FLOOR_N = 30
BASELINE_SAMPLE_CAP = 60


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS screener_calibration ("
        "as_of TEXT NOT NULL, screener TEXT NOT NULL, horizon INTEGER NOT NULL, "
        "n INTEGER, avg_excess_pct REAL, median_excess_pct REAL, "
        "win_rate REAL, baseline_win_rate REAL, baseline_n INTEGER, "
        "created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (as_of, screener, horizon))"
    )


def _entry_open(conn, symbol: str, hit_date: str) -> float | None:
    row = conn.execute(
        "SELECT open FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND open IS NOT NULL ORDER BY trade_date ASC LIMIT 1",
        (symbol, hit_date),
    ).fetchone()
    return None if not row or row["open"] is None else float(row["open"])


def _horizon_close(conn, symbol: str, hit_date: str, horizon: int) -> float | None:
    row = conn.execute(
        "SELECT close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT 1 OFFSET ?",
        (symbol, hit_date, horizon - 1),
    ).fetchone()
    return None if not row or row["close"] is None else float(row["close"])


def _forward_return_pct(conn, symbol: str, hit_date: str, horizon: int) -> float | None:
    entry = _entry_open(conn, symbol, hit_date)
    if entry is None or entry <= 0:
        return None
    exit_close = _horizon_close(conn, symbol, hit_date, horizon)
    if exit_close is None:
        return None
    return (exit_close - entry) / entry * 100.0


def _baseline_symbols_for_date(conn, trade_date: str, cap: int = BASELINE_SAMPLE_CAP) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series = 'EQ' AND trade_date = ? "
        "ORDER BY symbol",
        (trade_date,),
    ).fetchall()
    symbols = [r["symbol"] for r in rows]
    if len(symbols) <= cap:
        return symbols
    step = max(1, len(symbols) // cap)
    return symbols[::step][:cap]


def _baseline_by_horizon(conn, hit_dates: list[str]) -> dict[int, list[float]]:
    """Pooled random-sample universe baseline returns, keyed by horizon."""
    out: dict[int, list[float]] = {h: [] for h in HORIZONS}
    for d in hit_dates:
        symbols = _baseline_symbols_for_date(conn, d)
        for sym in symbols:
            for h in HORIZONS:
                r = _forward_return_pct(conn, sym, d, h)
                if r is not None:
                    out[h].append(r)
    return out


def compute(conn, as_of: str) -> list[dict[str, Any]]:
    ensure_schema(conn)
    hit_rows = conn.execute(
        "SELECT trade_date, symbol, screener FROM screener_hits ORDER BY trade_date, screener"
    ).fetchall()
    if not hit_rows:
        return []

    hit_dates = sorted({r["trade_date"] for r in hit_rows})
    baseline = _baseline_by_horizon(conn, hit_dates)
    baseline_stats: dict[int, dict[str, float | int]] = {}
    for h, obs in baseline.items():
        n = len(obs)
        baseline_stats[h] = {
            "n": n,
            "avg": (sum(obs) / n) if n else 0.0,
            "win_rate": (sum(1 for o in obs if o > 0) / n) if n else 0.0,
        }

    by_screener_horizon: dict[tuple[str, int], list[float]] = {}
    for r in hit_rows:
        screener = r["screener"]
        for h in HORIZONS:
            ret = _forward_return_pct(conn, r["symbol"], r["trade_date"], h)
            if ret is not None:
                by_screener_horizon.setdefault((screener, h), []).append(ret)

    out = []
    for (screener, h), rets in sorted(by_screener_horizon.items()):
        n = len(rets)
        base = baseline_stats[h]
        avg = sum(rets) / n
        med = median(rets)
        win_rate = sum(1 for r in rets if r > 0) / n
        out.append({
            "screener": screener,
            "horizon": h,
            "n": n,
            "avg_excess_pct": round(avg - float(base["avg"]), 3),
            "median_excess_pct": round(med - float(base["avg"]), 3),
            "win_rate": round(win_rate, 3),
            "baseline_win_rate": round(float(base["win_rate"]), 3),
            "baseline_n": int(base["n"]),
        })
    return out


def run(conn, run_date: str) -> dict[str, Any]:
    """Pipeline stage: recompute + persist. Never raises (failure-safe)."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        rows = compute(conn, run_date)
        conn.execute("DELETE FROM screener_calibration WHERE as_of = ?", (run_date,))
        for r in rows:
            conn.execute(
                "INSERT INTO screener_calibration (as_of, screener, horizon, n, "
                "avg_excess_pct, median_excess_pct, win_rate, baseline_win_rate, baseline_n) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_date, r["screener"], r["horizon"], r["n"], r["avg_excess_pct"],
                 r["median_excess_pct"], r["win_rate"], r["baseline_win_rate"], r["baseline_n"]),
            )
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'ok', ?, ?, ?)",
            (run_date, STAGE, SOURCE, len(rows), round(time.monotonic() - started, 3),
             f"screener_horizon_cells={len(rows)}"),
        )
        conn.commit()
        return {"status": "ok", "rows": len(rows)}
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, ?, 'fail', 0, ?, ?)",
            (run_date, STAGE, SOURCE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "detail": str(exc)}


def latest_ranked(conn, horizon: int = 10) -> list[dict[str, Any]]:
    """Latest as_of's screener_calibration rows for one horizon, ranked by
    avg_excess_pct desc. Each row is annotated `unproven` (n < TRUST_FLOOR_N)
    for callers to render trust-ladder suppression instead of hiding data."""
    ensure_schema(conn)
    latest = conn.execute("SELECT MAX(as_of) AS d FROM screener_calibration").fetchone()
    if not latest or not latest["d"]:
        return []
    rows = conn.execute(
        "SELECT screener, horizon, n, avg_excess_pct, median_excess_pct, win_rate, "
        "baseline_win_rate, baseline_n FROM screener_calibration "
        "WHERE as_of = ? AND horizon = ? ORDER BY avg_excess_pct DESC",
        (latest["d"], horizon),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["as_of"] = latest["d"]
        d["unproven"] = int(d["n"] or 0) < TRUST_FLOOR_N
        out.append(d)
    return out


if __name__ == "__main__":
    import sys
    from datetime import date as _date

    from manas_os import db as _db

    run_date = sys.argv[1] if len(sys.argv) > 1 else _date.today().isoformat()
    _conn = _db.init_db()
    result = run(_conn, run_date)
    print(f"screener_calibration run: {result}")
    ranked = latest_ranked(_conn, horizon=10)
    print(f"\n{'screener':35s} {'n':>5s} {'avg_excess%':>12s} {'med_excess%':>12s} {'win%':>7s} {'base_win%':>10s}")
    for r in ranked:
        flag = " (n<30)" if r["unproven"] else ""
        print(f"{r['screener']:35s} {r['n']:5d} {r['avg_excess_pct']:12.2f} "
              f"{r['median_excess_pct']:12.2f} {r['win_rate']*100:6.1f}% "
              f"{r['baseline_win_rate']*100:9.1f}%{flag}")
    _conn.close()
