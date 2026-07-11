"""Nightly alpha feature and decision-memory stages (shadow evidence only)."""
from __future__ import annotations

import hashlib
import json
import time

from . import features, memory


def _log(conn, run_date: str, stage: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date,stage,source,status,rows_affected,duration_s,detail) "
        "VALUES (?,?,?,?,?,?,?)",
        (run_date, stage, "alpha_shadow", status, rows, round(time.monotonic() - started, 3), detail),
    )


def run_features(conn, run_date: str) -> dict:
    started = time.monotonic()
    try:
        rows = features.compute_daily_features(conn, run_date)
        status = "ok" if rows else "skip"
        detail = f"causal feature snapshots={len(rows)}; shadow-only"
        _log(conn, run_date, "alpha_features", status, len(rows), started, detail)
        conn.commit()
        return {"status": status, "rows": len(rows), "detail": detail}
    except Exception as exc:  # noqa: BLE001 - research must not break run-eod
        _log(conn, run_date, "alpha_features", "skip", 0, started, f"error: {exc}")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": str(exc)}


def _memory_id(scan_date: str, symbol: str, source: str) -> str:
    return hashlib.sha256(f"{scan_date}|{symbol}|{source}".encode()).hexdigest()[:32]


def run_memory(conn, run_date: str) -> dict:
    """Freeze chair decisions and deterministic blocks after tonight's debate."""
    started = time.monotonic()
    try:
        memory.ensure_schema(conn)
        written = 0
        chair_rows = conn.execute(
            "SELECT scan_date,symbol,verdict,conviction,lens_scores_json,bull_case,bear_case,reasoning "
            "FROM agent_verdicts WHERE scan_date<=? AND agent='chair' "
            "AND scan_date=(SELECT MAX(scan_date) FROM agent_verdicts WHERE scan_date<=? AND agent='chair')",
            (run_date, run_date),
        ).fetchall()
        for row in chair_rows:
            mid = _memory_id(row["scan_date"], row["symbol"], "chair")
            if conn.execute("SELECT 1 FROM decision_memories WHERE memory_id=?", (mid,)).fetchone():
                continue
            lenses = json.loads(row["lens_scores_json"] or "{}")
            memory.record_decision(
                conn, memory_id=mid, decision_time=f"{row['scan_date']}T15:31:00+05:30",
                symbol=row["symbol"], decision=row["verdict"], evidence={
                    "conviction": row["conviction"], "bull_case": row["bull_case"],
                    "bear_case": row["bear_case"], "reasoning": row["reasoning"],
                    "chart_read": lenses,
                }, proposed_path={key: lenses.get(key) for key in (
                    "confirmation", "invalidation", "expected_path", "time_window"
                ) if lenses.get(key) is not None}, execution_lens=lenses.get("archetype"), data_quality=1.0,
            )
            written += 1
        status = "ok" if written else "skip"
        detail = f"immutable chair memories={written}"
        _log(conn, run_date, "alpha_memory", status, written, started, detail)
        conn.commit()
        return {"status": status, "rows": written, "detail": detail}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "alpha_memory", "skip", 0, started, f"error: {exc}")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": str(exc)}
