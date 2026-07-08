"""AD4: run_card — one canonical JSON artifact per night, written from tables
that already exist. Zero LLM, zero new computation, idempotent overwrite.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os.agents.context_pack import LESSON_DIGEST_PATH

RUN_CARD_ROOT = Path("data") / "run_cards"
LESSON_DIR = LESSON_DIGEST_PATH.parent


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _regime(conn, run_date: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT snapshot_date, market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (run_date,),
    ).fetchone()
    if not row:
        return {"mode": None, "age_days": None}
    age_days = None
    try:
        from datetime import date as _date

        age_days = (_date.fromisoformat(run_date) - _date.fromisoformat(row["snapshot_date"])).days
    except ValueError:
        pass
    return {"mode": row["market_mode"], "age_days": age_days}


def _pipeline(conn, run_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT stage, status, rows_affected, duration_s, detail FROM pipeline_runs "
        "WHERE run_date = ? ORDER BY run_id",
        (run_date,),
    ).fetchall()
    return [
        {
            "stage": r["stage"],
            "status": r["status"],
            "rows_affected": r["rows_affected"],
            "duration_s": r["duration_s"],
            "detail": r["detail"],
        }
        for r in rows
    ]


def _scan_date(conn, run_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(scan_date) AS d FROM scan_candidates WHERE scan_date <= ?",
        (run_date,),
    ).fetchone()
    return row["d"] if row and row["d"] else None


def _shortlist(conn, scan_date: str | None) -> list[dict[str, Any]]:
    if not scan_date:
        return []
    rows = conn.execute(
        "SELECT symbol, rank, setup_family, entry, stop, target, rr, suggested_qty "
        "FROM scan_candidates WHERE scan_date = ? ORDER BY COALESCE(rank, 999999), symbol",
        (scan_date,),
    ).fetchall()
    return [
        {
            "symbol": r["symbol"],
            "rank": r["rank"],
            "setup_family": r["setup_family"],
            "entry": r["entry"],
            "stop": r["stop"],
            "target": r["target"],
            "rr": r["rr"],
            "suggested_qty": r["suggested_qty"],
        }
        for r in rows
    ]


def _agent_stage(conn, scan_date: str | None, agents: set[str]) -> list[dict[str, Any]]:
    if not scan_date:
        return []
    placeholders = ",".join("?" for _ in agents)
    rows = conn.execute(
        f"SELECT symbol, agent, verdict, conviction, rank, reasoning FROM agent_verdicts "
        f"WHERE scan_date = ? AND agent IN ({placeholders}) ORDER BY agent, symbol",
        (scan_date, *agents),
    ).fetchall()
    return [
        {
            "symbol": r["symbol"],
            "agent": r["agent"],
            "verdict": r["verdict"],
            "conviction": r["conviction"],
            "rank": r["rank"],
            "reasoning": r["reasoning"],
        }
        for r in rows
    ]


def _chair(conn, scan_date: str | None) -> list[dict[str, Any]]:
    if not scan_date:
        return []
    rows = conn.execute(
        "SELECT symbol, verdict, conviction, rank, reasoning FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair' ORDER BY rank",
        (scan_date,),
    ).fetchall()
    out = []
    for r in rows:
        reasoning = r["reasoning"] or ""
        struck = "struck: no" not in reasoning
        reason = None
        if struck and "struck:" in reasoning:
            reason = reasoning.split("struck:", 1)[1].strip()
        out.append(
            {
                "symbol": r["symbol"],
                "verdict": r["verdict"],
                "conviction": r["conviction"],
                "rank": r["rank"],
                "struck": struck,
                "reason": reason,
            }
        )
    return out


_SYNTHESIZED_AGENTS = {"chair", "vision", "sizer", "coach"}


def _debate_summary(conn, run_date: str) -> list[dict[str, Any]]:
    # debate.py logs raw model calls with agent = the model id itself (not a
    # fixed "debate" literal); chair/vision/sizer/coach use fixed agent names,
    # so excluding those isolates the per-model debate rows.
    placeholders = ",".join("?" for _ in _SYNTHESIZED_AGENTS)
    rows = conn.execute(
        f"SELECT model, COUNT(*) AS n, SUM(CASE WHEN parsed_ok THEN 1 ELSE 0 END) AS parsed_ok, "
        f"SUM(COALESCE(tokens_in, 0)) AS tokens_in, SUM(COALESCE(tokens_out, 0)) AS tokens_out "
        f"FROM scan_agent_logs WHERE run_date = ? AND agent NOT IN ({placeholders}) GROUP BY model",
        (run_date, *_SYNTHESIZED_AGENTS),
    ).fetchall()
    return [
        {
            "model": r["model"],
            "verdicts": r["n"],
            "parsed_ok": r["parsed_ok"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
        }
        for r in rows
    ]


def _signals(conn, scan_date: str | None) -> list[dict[str, Any]]:
    if not scan_date:
        return []
    rows = conn.execute(
        "SELECT channel, symbol, sent FROM agent_signals WHERE scan_date = ? ORDER BY symbol",
        (scan_date,),
    ).fetchall()
    return [{"channel": r["channel"], "symbol": r["symbol"], "sent": bool(r["sent"])} for r in rows]


def _coach(conn, run_date: str) -> list[dict[str, Any]]:
    row = conn.execute(
        "SELECT detail FROM pipeline_runs WHERE run_date = ? AND stage = 'agents_coach' "
        "ORDER BY run_id DESC LIMIT 1",
        (run_date,),
    ).fetchone()
    if not row:
        return []
    return [{"detail": row["detail"]}]


def _lessons_written(scan_date: str | None) -> list[str]:
    if not scan_date or not LESSON_DIR.exists():
        return []
    return sorted(p.name for p in LESSON_DIR.glob(f"{scan_date}_*.md"))


def _errors(conn, run_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT stage, detail FROM pipeline_runs WHERE run_date = ? AND status IN ('error', 'partial') "
        "ORDER BY run_id",
        (run_date,),
    ).fetchall()
    return [{"stage": r["stage"], "detail": r["detail"]} for r in rows]


def build(conn, run_date: str) -> dict[str, Any]:
    scan_date = _scan_date(conn, run_date)
    return {
        "run_date": run_date,
        "scan_date": scan_date,
        "regime": _regime(conn, run_date),
        "pipeline": _pipeline(conn, run_date),
        "shortlist": _shortlist(conn, scan_date),
        "debate": _debate_summary(conn, run_date),
        "chair": _chair(conn, scan_date),
        "vision": _agent_stage(conn, scan_date, {"vision"}),
        "sizer": _agent_stage(conn, scan_date, {"sizer"}),
        "signals": _signals(conn, scan_date),
        "coach": _coach(conn, run_date),
        "lessons_written": _lessons_written(scan_date),
        "errors": _errors(conn, run_date),
    }


def write(conn, run_date: str) -> Path:
    """Build and idempotently overwrite data/run_cards/{run_date}.json."""
    card = build(conn, run_date)
    RUN_CARD_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_CARD_ROOT / f"{run_date}.json"
    path.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    return path
