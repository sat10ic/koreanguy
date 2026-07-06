"""Point-in-time replay harness for setup candidates.

The generator registry is intentionally small in Phase 0: `legacy` is the
current scanner path, and `cascade` is a named stub that delegates to legacy
until Phase 1 lands the refusal cascade.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any, Callable

from manas_os.scanner import candidates as scanner_candidates

THIN_N = 20


CandidateGenerator = Callable[[Any, str], list[dict[str, Any]]]


def _sessions(conn, start_date: str, end_date: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT trade_date FROM daily_prices "
        "WHERE series='EQ' AND trade_date >= ? AND trade_date <= ? "
        "ORDER BY trade_date",
        (start_date, end_date),
    ).fetchall()
    return [r["trade_date"] for r in rows]


def _legacy_candidates(conn, session_date: str) -> list[dict[str, Any]]:
    result = scanner_candidates.scan_candidates(conn, session_date)
    if not result.get("available"):
        return []
    return list(result.get("candidates") or [])


GENERATORS: dict[str, CandidateGenerator] = {
    "legacy": _legacy_candidates,
    "cascade": _legacy_candidates,
}


def _regime(conn, session_date: str) -> str:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (session_date,),
    ).fetchone()
    return str(row["market_mode"]) if row and row["market_mode"] else "UNKNOWN"


def _setup_family(candidate: dict[str, Any]) -> str:
    raw = candidate.get("setup_type") or candidate.get("setup") or "unknown"
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_") or "unknown"


def _outcome_r(conn, candidate: dict[str, Any], candidate_date: str, horizon: int = 10):
    """Forward R at T+horizon, WITH a fill check.

    A candidate whose trigger was never touched within the horizon is NOT a
    trade — counting it from a fictional fill at the pivot poisoned the first
    T1.6 run (LEARNINGS 2026-07-06). Returns float R, 'never_filled', or None."""
    entry = candidate.get("entry")
    stop = candidate.get("stop")
    try:
        entry_f = float(entry)
        stop_f = float(stop)
    except (TypeError, ValueError):
        return None
    risk = entry_f - stop_f
    if risk <= 0:
        return None
    sym = str(candidate["symbol"]).upper()
    fwd = conn.execute(
        "SELECT high, close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
        "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT ?",
        (sym, candidate_date, horizon),
    ).fetchall()
    if len(fwd) < horizon:
        return None
    if not any(r["high"] is not None and float(r["high"]) >= entry_f for r in fwd):
        return "never_filled"
    return (float(fwd[-1]["close"]) - entry_f) / risk


def _near_miss_baseline(conn, session_date: str, horizon: int = 10) -> list[float]:
    """T+horizon %-returns of the session's NEAR-MISS refusals (failed at
    fresh-leg / participation / risk / trend-template). The apples-to-apples
    baseline; regime/tradability refusals are a different population."""
    from manas_os.scanner.candidates import ensure_refusals_schema
    ensure_refusals_schema(conn)
    rows = conn.execute(
        "SELECT r.symbol, p.close AS c0, "
        " (SELECT f.close FROM daily_prices f WHERE f.symbol = r.symbol AND f.series='EQ' "
        "  AND f.trade_date > r.scan_date AND f.close IS NOT NULL "
        "  ORDER BY f.trade_date LIMIT 1 OFFSET ?) AS c10 "
        "FROM refusals r JOIN daily_prices p "
        "  ON p.symbol = r.symbol AND p.trade_date = r.scan_date AND p.series='EQ' "
        "WHERE r.scan_date = ? AND r.failed_gate IN "
        " ('fresh-leg','participation','risk','trend-template')",
        (horizon - 1, session_date),
    ).fetchall()
    return [
        (float(r["c10"]) - float(r["c0"])) / float(r["c0"]) * 100.0
        for r in rows if r["c0"] and r["c10"]
    ]


def _stop_pct(candidate: dict[str, Any]) -> float | None:
    try:
        entry = float(candidate.get("entry"))
        stop = float(candidate.get("stop"))
    except (TypeError, ValueError):
        return None
    risk = entry - stop
    return None if entry <= 0 or risk <= 0 else risk / entry * 100.0


def replay(conn, start_date: str, end_date: str, gate_config: str) -> dict[str, Any]:
    """Replay candidates over a historical window and aggregate family x regime cells."""
    if gate_config not in GENERATORS:
        raise ValueError(f"unknown gate_config {gate_config!r}; expected one of {sorted(GENERATORS)}")
    sessions = _sessions(conn, start_date, end_date)
    generator = GENERATORS[gate_config]
    buckets: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    never_filled = 0
    near_miss: list[float] = []

    for session_date in sessions:
        regime = _regime(conn, session_date)
        for candidate in generator(conn, session_date):
            fwd_r = _outcome_r(conn, candidate, session_date, horizon=10)
            stop_pct = _stop_pct(candidate)
            if fwd_r == "never_filled":
                never_filled += 1
                continue
            if fwd_r is None or stop_pct is None:
                continue
            buckets[(_setup_family(candidate), regime)].append({"r": fwd_r, "stop_pct": stop_pct})
        near_miss.extend(_near_miss_baseline(conn, session_date, horizon=10))

    cells = []
    for (setup_family, regime), observations in sorted(buckets.items()):
        n = len(observations)
        r_values = [o["r"] for o in observations]
        stop_values = [o["stop_pct"] for o in observations]
        thin = n < THIN_N
        cells.append({
            "setup_family": setup_family,
            "regime": regime,
            "n": n,
            "hit_rate": None if thin else sum(1 for r in r_values if r >= 1.0) / n,
            "median_r_T10": None if thin else median(r_values),
            "median_stop_pct": None if thin else median(stop_values),
            "cards_per_day": None if thin or not sessions else n / len(sessions),
            "note": "n<20 -- thin" if thin else "",
        })
    return {
        "config": gate_config,
        "start_date": start_date,
        "end_date": end_date,
        "sessions": len(sessions),
        "cells": cells,
        "never_filled": never_filled,
        "near_miss_baseline": {
            "n": len(near_miss),
            "median_pct": round(median(near_miss), 2) if near_miss else None,
        },
    }


def _fmt(value: Any, kind: str = "num") -> str:
    if value is None:
        return "n<20 -- thin"
    if kind == "pct":
        return f"{value * 100.0:5.1f}%"
    if kind == "stop":
        return f"{value:5.1f}%"
    if kind == "cards":
        return f"{value:5.2f}"
    if kind == "r":
        return f"{value:5.2f}R"
    return str(value)


def format_replay_table(result: dict[str, Any], title: str | None = None) -> str:
    heading = title or f"Replay {result['config']} {result['start_date']}..{result['end_date']}"
    lines = [heading, f"sessions: {result['sessions']}"]
    header = f"{'setup_family':<18} {'regime':<10} {'n':>5} {'hit_T10':>13} {'med_R_T10':>13} {'med_stop':>13} {'cards/day':>10}"
    lines.extend([header, "-" * len(header)])
    if not result["cells"]:
        lines.append("(no completed T+10 observations)")
        return "\n".join(lines)
    for cell in result["cells"]:
        lines.append(
            f"{cell['setup_family']:<18} {cell['regime']:<10} {cell['n']:>5} "
            f"{_fmt(cell['hit_rate'], 'pct'):>13} {_fmt(cell['median_r_T10'], 'r'):>13} "
            f"{_fmt(cell['median_stop_pct'], 'stop'):>13} {_fmt(cell['cards_per_day'], 'cards'):>10}"
        )
    return "\n".join(lines)


def format_ab_table(a: dict[str, Any], b: dict[str, Any]) -> str:
    left = format_replay_table(a).splitlines()
    right = format_replay_table(b).splitlines()
    width = max(len(line) for line in left) if left else 0
    n = max(len(left), len(right))
    left.extend([""] * (n - len(left)))
    right.extend([""] * (n - len(right)))
    return "\n".join(f"{left[i]:<{width}}    |    {right[i]}" for i in range(n))
