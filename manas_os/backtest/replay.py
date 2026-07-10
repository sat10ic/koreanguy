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


NEAR_MISS_GATES = ("fresh-leg", "participation", "risk", "trend-template")


def _near_miss_r_terms(conn, session_date: str, horizon: int = 10) -> list[dict[str, Any]]:
    """R-adjusted near-miss cohort, re-deriving entry/stop from the scanner
    output (the refusals table does NOT carry them). W1.2: the raw-% baseline
    above is not enough — a +3.5% move on an 8-12% stop is a bad trade in R.

    For each session's near-miss refusal, re-runs the scanner to capture the
    entry/stop the plan WOULD have set, then computes T+horizon forward R with
    the SAME fill check the passed cohort uses (`never_filled` if the trigger
    was never touched). Returns per-observation dicts: {r, stop_pct, gate,
    family}. This is the honest passed-vs-refused apples-to-apples comparison."""
    result = scanner_candidates.scan_candidates(conn, session_date)
    if not result.get("available"):
        return []
    observations: list[dict[str, Any]] = []
    for cand in result.get("dropped", []):
        gate = cand.get("failed_gate")
        if gate not in NEAR_MISS_GATES:
            continue
        entry = cand.get("entry")
        stop = cand.get("stop")
        try:
            entry_f = float(entry)
            stop_f = float(stop)
        except (TypeError, ValueError):
            continue
        risk = entry_f - stop_f
        if risk <= 0:
            continue
        sym = str(cand["symbol"]).upper()
        fwd = conn.execute(
            "SELECT high, close FROM daily_prices WHERE symbol = ? AND series = 'EQ' "
            "AND trade_date > ? AND close IS NOT NULL ORDER BY trade_date ASC LIMIT ?",
            (sym, session_date, horizon),
        ).fetchall()
        if len(fwd) < horizon:
            continue
        # Same fill check as _outcome_r: a refusal is not a trade unless its
        # hypothetical trigger was actually touched.
        if not any(r["high"] is not None and float(r["high"]) >= entry_f for r in fwd):
            observations.append({"r": "never_filled", "stop_pct": stop_f / entry_f * 100.0,
                                 "gate": gate, "family": cand.get("setup_family") or "unknown"})
            continue
        r_value = (float(fwd[-1]["close"]) - entry_f) / risk
        observations.append({"r": r_value, "stop_pct": stop_f / entry_f * 100.0,
                             "gate": gate, "family": cand.get("setup_family") or "unknown"})
    return observations


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
    # W1.2: R-adjusted near-miss cohort (the honest comparison the raw-%
    # baseline cannot make). Aggregated per failed gate so the verdict can name
    # WHICH near-miss gate's refusals actually beat the passed cohort in R.
    near_miss_r_by_gate: dict[str, list[float]] = defaultdict(list)
    near_miss_r_never_filled = 0

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
        for obs in _near_miss_r_terms(conn, session_date, horizon=10):
            if obs["r"] == "never_filled":
                near_miss_r_never_filled += 1
                continue
            near_miss_r_by_gate[obs["gate"]].append(float(obs["r"]))

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

    # Passed-cohort aggregate (all cells pooled) for the headline comparison.
    all_passed_r = [o["r"] for obs in buckets.values() for o in obs]
    near_miss_r_summary = {
        gate: {
            "n": len(rs),
            "median_r_T10": round(median(rs), 3) if rs else None,
            "hit_rate": round(sum(1 for r in rs if r >= 1.0) / len(rs), 3) if rs else None,
        }
        for gate, rs in sorted(near_miss_r_by_gate.items())
    }
    near_miss_r_summary["_never_filled"] = near_miss_r_never_filled
    return {
        "config": gate_config,
        "start_date": start_date,
        "end_date": end_date,
        "sessions": len(sessions),
        "cells": cells,
        "never_filled": never_filled,
        "passed_cohort_r": {
            "n": len(all_passed_r),
            "median_r_T10": round(median(all_passed_r), 3) if all_passed_r else None,
            "hit_rate": round(sum(1 for r in all_passed_r if r >= 1.0) / len(all_passed_r), 3) if all_passed_r else None,
        },
        "near_miss_baseline": {
            "n": len(near_miss),
            "median_pct": round(median(near_miss), 2) if near_miss else None,
        },
        "near_miss_r_by_gate": near_miss_r_summary,
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


def persist_replay(conn, start_date: str, end_date: str, as_of: str | None = None) -> dict[str, Any]:
    """E1-PERSIST: single-pass historical replay that PERSISTS both cohorts.

    For each historical session this makes exactly ONE scan_candidates() call
    (the deterministic cascade), then:
      - PASSED cohort: persists the survivors via the existing P2 writer
        (scanner.candidates.persist_candidates), so they accumulate in
        candidates/outcomes/scan_candidates just like a live daily run would.
      - REFUSED cohort: reuses the same call's `dropped` list (near-miss gates
        only -- fresh-leg/participation/risk/trend-template, the apples-to-
        apples population per replay.NEAR_MISS_GATES) and computes forward R
        directly with the SAME fill-checked _outcome_r used for the passed
        cohort, aggregated into setup_expectancy.

    ONE writer for setup_expectancy: expectancy.run() (passed+personal loops,
    reading the now-populated candidates/outcomes tables) is called from here,
    then the refused cohort is appended additively under the same as_of.
    Idempotent: reruns delete-then-insert by (as_of, cohort).
    """
    from manas_os.scanner import candidates as scanner_candidates
    from manas_os.scanner import outcomes as scanner_outcomes
    from manas_os.scanner import expectancy

    sessions = _sessions(conn, start_date, end_date)
    as_of = as_of or (sessions[-1] if sessions else end_date)
    days_persisted = 0
    days_scanned = 0

    for session_date in sessions:
        result = scanner_candidates.scan_candidates(conn, session_date)
        days_scanned += 1
        if not result.get("available"):
            continue
        scanner_candidates.persist_candidates(conn, result["as_of"], result.get("candidates") or [])
        days_persisted += 1
        if days_scanned % 25 == 0:
            conn.commit()

    conn.commit()
    scanner_outcomes.ensure_schema(conn)
    written = scanner_outcomes.backfill_forward_returns(conn)
    conn.commit()

    exp_result = expectancy.run(conn, as_of)

    # REFUSED cohort: the `refusals` ledger (written as a side effect of every
    # scan_candidates() call above, plus prior runs) carries no entry/stop --
    # only symbol/gate/reason -- so an R-multiple isn't reconstructable without
    # re-deriving a hypothetical plan per name. Rather than fabricate an R, this
    # uses the SAME close-to-close %-return baseline already established and
    # caveated in LEARNINGS 2026-07-07 for the near-miss cohort, now broken out
    # by (family, regime) instead of one aggregate. Units: raw %, NOT R -- the
    # UI must label this differently from the passed cohort's R-multiples.
    refused_result = _persist_refused_pct_cohort(conn, as_of, horizon=10)

    return {
        "status": "ok",
        "as_of": as_of,
        "sessions": len(sessions),
        "days_scanned": days_scanned,
        "days_persisted": days_persisted,
        "outcomes_backfilled": written,
        "refused_cells": refused_result["cells"],
        "refused_observations": refused_result["observations"],
        "expectancy": exp_result,
    }


def _persist_refused_pct_cohort(conn, as_of: str, horizon: int = 10) -> dict[str, Any]:
    """Aggregate the `refusals` ledger's near-miss gates into per-(family,regime)
    close-to-close %-return cells and upsert them into setup_expectancy as
    cohort='refused'. Pure SQL over the already-populated ledger -- no rescan."""
    from manas_os.scanner import expectancy

    from manas_os.scanner.candidates import ensure_refusals_schema
    ensure_refusals_schema(conn)
    rows = conn.execute(
        "SELECT r.scan_date, r.symbol, r.setup_family, p.close AS c0, "
        " (SELECT f.close FROM daily_prices f WHERE f.symbol = r.symbol AND f.series='EQ' "
        "  AND f.trade_date > r.scan_date AND f.close IS NOT NULL "
        "  ORDER BY f.trade_date LIMIT 1 OFFSET ?) AS c10 "
        "FROM refusals r JOIN daily_prices p "
        "  ON p.symbol = r.symbol AND p.trade_date = r.scan_date AND p.series='EQ' "
        "WHERE r.failed_gate IN ('fresh-leg','participation','risk','trend-template')",
        (horizon - 1,),
    ).fetchall()
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r["c0"] is None or r["c10"] is None or not r["c0"]:
            continue
        pct = (float(r["c10"]) - float(r["c0"])) / float(r["c0"]) * 100.0
        family = r["setup_family"] or "unknown"
        regime = _regime(conn, r["scan_date"])
        buckets[(family, regime)].append(pct)

    expectancy.ensure_schema(conn)
    conn.execute("DELETE FROM setup_expectancy WHERE as_of = ? AND cohort = 'refused'", (as_of,))
    cells = 0
    observations = 0
    for (family, regime), pcts in sorted(buckets.items()):
        n = len(pcts)
        if n == 0:
            continue
        win_rate = sum(1 for p in pcts if p > 0) / n
        mean_pct = sum(pcts) / n
        conn.execute(
            "INSERT INTO setup_expectancy (as_of, loop, setup_family, regime, cohort, n, "
            "hit_rate, mean_r, median_r, posterior_r, trust) "
            "VALUES (?, 'system', ?, ?, 'refused', ?, ?, ?, ?, ?, ?)",
            (as_of, family, regime, n, round(win_rate, 3), round(mean_pct, 3),
             round(median(pcts), 3), round(mean_pct, 3), expectancy._trust(n)),
        )
        cells += 1
        observations += n
    conn.commit()
    return {"cells": cells, "observations": observations}


# WAVE_J7: soft gates a near-miss is allowed to fail and still enter the
# counterfactual cohort -- SAME set as agents/debate.py SOFT_GATES (duplicated
# here, not imported, to avoid pulling agents.debate's OpenRouterClient import
# chain into the backtest package for a 3-string constant).
COUNTERFACTUAL_SOFT_GATES = {"trend-template", "fresh-leg", "participation"}


def _counterfactual_session_candidates(conn, session_date: str) -> list[dict[str, Any]]:
    """Re-run the SAME confluence-pool setup as
    scanner.candidates.scan_candidates_deterministic, but call
    candidate_for_symbol directly so refused candidates' entry/stop/plan
    survive (scan_candidates_deterministic's `dropped` list strips them down
    to symbol/setup_family/failed_gate via `_refuse`). This is NOT a second
    plan formula -- it is the identical one-writer candidate_for_symbol call;
    only the caller-side bookkeeping differs so soft-gate refusals keep their
    computed entry/stop. Returns dicts for names that pass ALL gates
    (failed_gate=None) or fail ONLY a COUNTERFACTUAL_SOFT_GATES gate."""
    from manas_os.scanner import candidates as sc

    price_date = sc.latest_price_date(conn, session_date)
    if price_date is None:
        return []
    screener_date, pool = sc.confluence_pool(conn, session_date)
    market_mode, _mode_defaulted = sc.market_mode_for(conn, price_date)
    _, quality_map = sc.symbol_quality_map(conn, session_date)
    quality_map = {
        sym: {**quality, **sc.fundamentals.growth_for(conn, sym, session_date, quality)}
        for sym, quality in quality_map.items()
    }
    _, top_quartile = sc.sector_rs_quartile(conn, session_date)
    rs_map = sc.stock_rs_map(session_date)
    abs_strength = sc.absolute_strength_percentiles(conn, price_date)
    eps_pctiles = sc.eps_growth_percentiles(quality_map)

    shortlist = sc.detector_shortlist(conn, price_date)
    pool_symbols = list(dict.fromkeys(list(pool.keys()) + shortlist))

    cfg = sc.GateConfig()
    out: list[dict[str, Any]] = []
    for sym in pool_symbols:
        quality = quality_map.get(sym)
        if quality is None:
            growth = sc.fundamentals.growth_for(conn, sym, session_date, None)
            quality = growth if any(v is not None for v in growth.values()) else None
        bars25 = sc.load_symbol_bars(conn, sym, price_date, limit=25)
        verdict = sc.evaluate_symbol(bars25, sym, cfg, market_cap_cr=(quality or {}).get("market_cap_cr"))
        if not verdict["tradeable"]:
            continue  # tradability is a hard gate, never soft -- excluded, not persisted

        candidate = sc.candidate_for_symbol(
            conn, sym, price_date,
            pool.get(sym, {"count": 0, "screeners": [], "rs_rating": None, "basic_industry": None}),
            quality, top_quartile, rs_map.get(sym),
            abs_strength.get(sym), eps_pctiles.get(sym),
            market_mode=market_mode, universe_verdict=verdict,
        )
        if candidate is None:
            continue
        entry = candidate.get("entry")
        stop = candidate.get("stop")
        if entry is None or stop is None:
            continue
        if candidate.get("refused"):
            gate = candidate.get("failed_gate")
            if gate not in COUNTERFACTUAL_SOFT_GATES:
                continue  # hard-gate refusal -- not a near-miss, excluded
            failed_gate = gate
        else:
            failed_gate = None
        out.append({
            "scan_date": price_date,
            "symbol": str(sym).upper(),
            "setup_family": candidate.get("setup_family") or "unknown",
            "entry": float(entry),
            "stop": float(stop),
            "failed_gate": failed_gate,
        })
    return out


def persist_counterfactual(conn, start_date: str, end_date: str) -> dict[str, Any]:
    """WAVE_J7 task 2: persist the counterfactual entry-quality cohort (soft-
    gate near-misses + full passes from the SAME confluence pool) into
    counterfactual_candidates, a table SEPARATE from scan_candidates/
    candidates so the real cascade output stays pure (never written here).
    Idempotent: DELETE-then-INSERT per session_date. Additive -- does not
    touch candidates/outcomes/scan_candidates/refusals.
    """
    from manas_os.scanner import outcomes as scanner_outcomes

    scanner_outcomes.ensure_counterfactual_schema(conn)
    sessions = _sessions(conn, start_date, end_date)
    sessions_scanned = 0
    rows_persisted = 0
    for session_date in sessions:
        regime = _regime(conn, session_date)
        rows = _counterfactual_session_candidates(conn, session_date)
        sessions_scanned += 1
        if not rows:
            continue
        conn.execute("DELETE FROM counterfactual_candidates WHERE scan_date = ?", (session_date,))
        for r in rows:
            conn.execute(
                "INSERT OR REPLACE INTO counterfactual_candidates "
                "(scan_date, symbol, setup_family, entry, stop, regime, failed_gate) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r["scan_date"], r["symbol"], r["setup_family"], r["entry"], r["stop"],
                 regime, r["failed_gate"]),
            )
            rows_persisted += 1
        if sessions_scanned % 10 == 0:
            conn.commit()
    conn.commit()

    written = scanner_outcomes.backfill_counterfactual_outcomes(conn, horizon=10)
    conn.commit()
    return {
        "status": "ok",
        "sessions": len(sessions),
        "sessions_scanned": sessions_scanned,
        "candidates_persisted": rows_persisted,
        "outcomes_backfilled": written,
    }


def format_ab_table(a: dict[str, Any], b: dict[str, Any]) -> str:
    left = format_replay_table(a).splitlines()
    right = format_replay_table(b).splitlines()
    width = max(len(line) for line in left) if left else 0
    n = max(len(left), len(right))
    left.extend([""] * (n - len(left)))
    right.extend([""] * (n - len(right)))
    return "\n".join(f"{left[i]:<{width}}    |    {right[i]}" for i in range(n))
