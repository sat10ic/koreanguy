"""scanner/expectancy.py — the learnings-loop math (plan T2.3b).

Two rigorously separate loops:
  SYSTEM loop  — forward returns of EVERY persisted candidate (taken or not),
                 per (setup_family × regime) cell. Research-grade; proves or
                 kills each setup family over time.
  PERSONAL loop — r_result of the user's CLOSED journal trades, same cells.
                 The un-copyable asset; only shown as "yours" at n >= 30.

Anti-overfit (LOCKED): hierarchical shrinkage toward the family parent,
    posterior = n/(n+k) * cell_mean + k/(n+k) * parent_mean,   k = 25
Trust ladder: n<20 descriptive · 20-74 directional · 75-149 rank-usable ·
150+ operational. Nothing here changes gates automatically — display + review
only; threshold changes remain quarterly + human + logged in LEARNINGS.md.
"""
from __future__ import annotations

import json
import time
from statistics import median
from typing import Any

STAGE = "expectancy"
K_SHRINK = 25.0
HIT_R = 1.0


def ensure_schema(conn) -> None:
    """Create setup_expectancy (idempotent) with a `cohort` axis (passed|refused).

    E1-PERSIST: the table originally had no cohort column (single implicit
    'passed' cohort). If an existing (empty) table predates the column, it is
    safely dropped and recreated with cohort folded into the PRIMARY KEY --
    dropping is only done when the table is empty, so no data is ever lost.
    """
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='setup_expectancy'"
    ).fetchall()}
    if have:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(setup_expectancy)")}
        if "cohort" not in cols:
            n_rows = conn.execute("SELECT COUNT(*) FROM setup_expectancy").fetchone()[0]
            if n_rows == 0:
                conn.execute("DROP TABLE setup_expectancy")
            else:
                conn.execute("ALTER TABLE setup_expectancy ADD COLUMN cohort TEXT DEFAULT 'passed'")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS setup_expectancy ("
        "as_of TEXT NOT NULL, loop TEXT NOT NULL, setup_family TEXT NOT NULL, "
        "regime TEXT NOT NULL, cohort TEXT NOT NULL DEFAULT 'passed', "
        "n INTEGER, hit_rate REAL, mean_r REAL, median_r REAL, "
        "posterior_r REAL, trust TEXT, "
        "PRIMARY KEY (as_of, loop, setup_family, regime, cohort))"
    )


def _trust(n: int) -> str:
    if n < 20:
        return "descriptive"
    if n < 75:
        return "directional"
    if n < 150:
        return "rank-usable"
    return "operational"


def _regime_for(conn, d: str) -> str:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1", (d,),
    ).fetchone()
    return str(row["market_mode"]).upper() if row and row["market_mode"] else "UNKNOWN"


def _system_observations(conn) -> list[dict[str, Any]]:
    """(family, regime, r) for every completed T+10 outcome of a persisted candidate."""
    rows = conn.execute(
        "SELECT o.candidate_date, o.symbol, o.forward_r, c.source_payload_json "
        "FROM outcomes o JOIN candidates c "
        "  ON c.candidate_date = o.candidate_date AND c.symbol = o.symbol AND c.setup = o.setup "
        "WHERE o.horizon = 10 AND o.status = 'complete' AND o.forward_r IS NOT NULL"
    ).fetchall()
    out = []
    for r in rows:
        try:
            payload = json.loads(r["source_payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        family = payload.get("setup_family") or "unknown"
        out.append({"family": family, "regime": _regime_for(conn, r["candidate_date"]),
                    "r": float(r["forward_r"])})
    return out


def _personal_observations(conn) -> list[dict[str, Any]]:
    """(family, regime, r) for CLOSED journal trades, family via setup_decisions snapshot."""
    have = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='setup_decisions'"
    ).fetchone()
    if not have:
        return []
    rows = conn.execute(
        "SELECT j.trade_date, j.symbol, j.r_result, d.snapshot_json "
        "FROM journal_trades j LEFT JOIN setup_decisions d "
        "  ON d.symbol = j.symbol AND d.scan_date = j.trade_date "
        "WHERE j.exit IS NOT NULL AND j.r_result IS NOT NULL"
    ).fetchall()
    out = []
    for r in rows:
        try:
            snap = json.loads(r["snapshot_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            snap = {}
        out.append({"family": snap.get("setup_family") or "unknown",
                    "regime": _regime_for(conn, r["trade_date"]),
                    "r": float(r["r_result"])})
    return out


def _cells(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[float]] = {}
    by_cell: dict[tuple[str, str], list[float]] = {}
    for o in observations:
        by_family.setdefault(o["family"], []).append(o["r"])
        by_cell.setdefault((o["family"], o["regime"]), []).append(o["r"])
    cells = []
    for (family, regime), rs in sorted(by_cell.items()):
        parent = by_family[family]
        parent_mean = sum(parent) / len(parent)
        n = len(rs)
        cell_mean = sum(rs) / n
        posterior = (n / (n + K_SHRINK)) * cell_mean + (K_SHRINK / (n + K_SHRINK)) * parent_mean
        cells.append({
            "setup_family": family, "regime": regime, "n": n,
            "hit_rate": round(sum(1 for r in rs if r >= HIT_R) / n, 3),
            "mean_r": round(cell_mean, 3), "median_r": round(median(rs), 3),
            "posterior_r": round(posterior, 3), "trust": _trust(n),
        })
    return cells


def compute(conn, as_of: str) -> dict[str, list[dict[str, Any]]]:
    return {"system": _cells(_system_observations(conn)),
            "personal": _cells(_personal_observations(conn))}


def run(conn, run_date: str) -> dict[str, Any]:
    """Pipeline stage: recompute + persist both loops. Never raises."""
    started = time.monotonic()
    try:
        ensure_schema(conn)
        result = compute(conn, run_date)
        conn.execute("DELETE FROM setup_expectancy WHERE as_of = ? AND cohort = 'passed'", (run_date,))
        rows = 0
        for loop, cells in result.items():
            for c in cells:
                conn.execute(
                    "INSERT INTO setup_expectancy (as_of, loop, setup_family, regime, cohort, n, "
                    "hit_rate, mean_r, median_r, posterior_r, trust) "
                    "VALUES (?, ?, ?, ?, 'passed', ?, ?, ?, ?, ?, ?)",
                    (run_date, loop, c["setup_family"], c["regime"], c["n"], c["hit_rate"],
                     c["mean_r"], c["median_r"], c["posterior_r"], c["trust"]),
                )
                rows += 1
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, 'outcomes+journal', 'ok', ?, ?, ?)",
            (run_date, STAGE, rows, round(time.monotonic() - started, 3),
             f"system_cells={len(result['system'])} personal_cells={len(result['personal'])}"),
        )
        conn.commit()
        return {"status": "ok", "rows": rows}
    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail) VALUES (?, ?, 'outcomes+journal', 'fail', 0, ?, ?)",
            (run_date, STAGE, round(time.monotonic() - started, 3), str(exc)),
        )
        conn.commit()
        return {"status": "fail", "detail": str(exc)}


TRUST_FLOOR_N = 20


def chip_for(conn, setup_family: str, regime: str) -> dict[str, Any] | None:
    """The card chip: system cell + personal overlay + refused-cohort comparison.

    Each of system/personal/refused is looked up at ITS OWN latest as_of
    (rather than one global MAX(as_of)) so the passed cohort's daily
    expectancy.run() refresh never hides an older, richer historical
    replay-derived refused-cohort row (E1-PERSIST: replay and the daily
    pipeline write disjoint as_of dates for the same table)."""
    ensure_schema(conn)
    out: dict[str, Any] = {}
    for loop, cohort in (("system", "passed"), ("personal", "passed")):
        row = conn.execute(
            "SELECT n, hit_rate, mean_r, median_r, posterior_r, trust FROM setup_expectancy "
            "WHERE loop = ? AND cohort = ? AND setup_family = ? AND regime = ? "
            "ORDER BY as_of DESC LIMIT 1",
            (loop, cohort, setup_family, regime),
        ).fetchone()
        if row:
            d = dict(row)
            d["unproven"] = int(d["n"] or 0) < TRUST_FLOOR_N
            out[loop] = d
    refused = conn.execute(
        "SELECT n, hit_rate, mean_r, median_r, trust FROM setup_expectancy "
        "WHERE loop = 'system' AND cohort = 'refused' AND setup_family = ? AND regime = ? "
        "ORDER BY as_of DESC LIMIT 1",
        (setup_family, regime),
    ).fetchone()
    if refused:
        d = dict(refused)
        d["unproven"] = int(d["n"] or 0) < TRUST_FLOOR_N
        out["refused"] = d
    if not out:
        return None
    personal = out.get("personal")
    if personal and personal["n"] < 30:
        out["personal_note"] = f"yours: n={personal['n']} — too thin, showing system prior"
    return out
