"""AD4: run_card — one canonical JSON artifact per night, written from tables
that already exist. Zero LLM, zero new computation, idempotent overwrite.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.agents import _shared
from manas_os.agents.context_pack import LESSON_DIGEST_PATH
from manas_os.regime.governor import governor as _governor
from manas_os.scanner import outcomes as _scanner_outcomes

# Anchored to the repo root (parents[2] of this file) — a cwd-relative path
# split run cards across two directories depending on where the CLI was launched.
RUN_CARD_ROOT = Path(__file__).resolve().parents[2] / "data" / "run_cards"
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
        "SELECT snapshot_date, market_mode, xp_value, mbi_day_color, r4p5, r10, r20, r50 "
        "FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (run_date,),
    ).fetchone()
    if not row:
        return {
            "mode": None,
            "age_days": None,
            "xp": None,
            "mbi_day_color": None,
            "ratios": {"r4p5": None, "r10": None, "r20": None, "r50": None},
        }
    age_days = None
    try:
        from datetime import date as _date

        age_days = (_date.fromisoformat(run_date) - _date.fromisoformat(row["snapshot_date"])).days
    except ValueError:
        pass
    return {
        "mode": row["market_mode"],
        "age_days": age_days,
        "xp": row["xp_value"],
        "mbi_day_color": row["mbi_day_color"],
        "ratios": {
            "r4p5": row["r4p5"],
            "r10": row["r10"],
            "r20": row["r20"],
            "r50": row["r50"],
        },
    }


def _governor_law(regime: dict[str, Any]) -> dict[str, Any]:
    """F5: the day's LAW, from the same governor() the Setups API and risk
    sizing route through (anti-mashup single writer). Additive key."""
    return _governor(regime.get("mode"))


def _heat(conn, run_date: str) -> dict[str, Any]:
    """F5: open-risk numbers from the same tables/formula /api/portfolio/heat
    uses (journal_trades open positions, setup_decisions qty, governor cap).
    Additive key on the card; never raises on a night with no journal yet."""
    try:
        capital = float(config.get("risk.capital", 1_000_000) or 1_000_000)
        mode_row = conn.execute(
            "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
            "ORDER BY snapshot_date DESC LIMIT 1",
            (run_date,),
        ).fetchone()
        mode = mode_row["market_mode"] if mode_row else "NO_TRADE"
        cap_pct = _governor(mode).get("open_risk_cap_pct")
        _scanner_outcomes.ensure_setup_decisions_schema(conn)
        rows = conn.execute(
            "SELECT trade_date, symbol, entry, stop FROM journal_trades WHERE exit IS NULL"
        ).fetchall()
        open_risk_pct = 0.0
        for row in rows:
            decision = conn.execute(
                "SELECT qty FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
                (row["trade_date"], row["symbol"]),
            ).fetchone()
            qty = int(decision["qty"]) if decision and decision["qty"] is not None else 0
            entry = float(row["entry"]) if row["entry"] is not None else None
            stop = float(row["stop"]) if row["stop"] is not None else None
            if entry is not None and stop is not None and entry > 0 and qty > 0 and capital > 0:
                open_risk_pct += (entry - stop) / entry * qty * entry / capital * 100.0
        return {"open_risk_pct": round(open_risk_pct, 4), "cap_pct": cap_pct}
    except Exception:
        return {"open_risk_pct": None, "cap_pct": None}


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
    # AU3: a total-outage night logs debate/chair/vision/sizer as status='fail'
    # (rows==0) — include it here so the card honestly records the failure
    # instead of silently omitting it (only 'error'/'partial' were checked).
    rows = conn.execute(
        "SELECT stage, detail FROM pipeline_runs WHERE run_date = ? AND status IN ('error', 'partial', 'fail') "
        "ORDER BY run_id",
        (run_date,),
    ).fetchall()
    return [{"stage": r["stage"], "detail": r["detail"]} for r in rows]


def build(conn, run_date: str) -> dict[str, Any]:
    scan_date = _scan_date(conn, run_date)
    regime = _regime(conn, run_date)
    return {
        "run_date": run_date,
        "scan_date": scan_date,
        "regime": regime,
        "governor": _governor_law(regime),
        "heat": _heat(conn, run_date),
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


def _brief_model() -> str:
    model = config.get("agents.brief_model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return _shared.models()[0]


def _brief_fallback(card: dict[str, Any]) -> str:
    chair_takes = sum(1 for r in card.get("chair", []) if r.get("verdict") == "TAKE")
    sizer_takes = sum(1 for r in card.get("sizer", []) if r.get("verdict") == "TAKE")
    error_count = len(card.get("errors", []))
    return (
        f"Reviewed {len(card.get('shortlist', []))} names, chair took {chair_takes}, "
        f"and sizer took {sizer_takes}. "
        f"{error_count} pipeline issue{'s' if error_count != 1 else ''} recorded."
    )


def _rounded_regime(regime: dict[str, Any] | None) -> dict[str, Any]:
    """Display-rounded copy for the brief prompt — raw floats made a free model
    regurgitate 'XP 9. 505714006920162' (PROMPT REV 2026-07-09). The card itself
    keeps full precision; only the LLM sees rounded values."""
    if not isinstance(regime, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in regime.items():
        if isinstance(v, float):
            out[k] = round(v, 1)
        elif isinstance(v, dict):
            out[k] = {ik: (round(iv, 0) if isinstance(iv, float) else iv) for ik, iv in v.items()}
        else:
            out[k] = v
    return out


def _morning_brief(card: dict[str, Any], client: Any | None = None) -> str:
    numbers = {
        "run_date": card.get("run_date"),
        "scan_date": card.get("scan_date"),
        "regime": _rounded_regime(card.get("regime")),
        "shortlist_count": len(card.get("shortlist", [])),
        "debate_models": len(card.get("debate", [])),
        "debate_parsed_ok": sum(int(r.get("parsed_ok") or 0) for r in card.get("debate", [])),
        "chair_take_count": sum(1 for r in card.get("chair", []) if r.get("verdict") == "TAKE"),
        "chair_skip_count": sum(1 for r in card.get("chair", []) if r.get("verdict") == "SKIP"),
        "vision_count": len(card.get("vision", [])),
        "sizer_take_count": sum(1 for r in card.get("sizer", []) if r.get("verdict") == "TAKE"),
        "signal_count": len(card.get("signals", [])),
        "coach_count": len(card.get("coach", [])),
        "lessons_written_count": len(card.get("lessons_written", [])),
        "error_count": len(card.get("errors", [])),
    }
    try:
        llm = client
        model = _brief_model()
        if llm is None:
            key = _shared.api_key()
            if not key:
                return _brief_fallback(card)
            llm = OpenRouterClient(api_key=key, model=model, max_tokens=int(config.get("agents.max_tokens", 1000) or 1000))
        raw, _used_model = _shared.chat_tuple(
            llm,
            "Compose a plain morning trading-desk brief. Use only the provided numbers; do not compute new numbers.",
            "Write no more than 4 plain sentences from this JSON:\n"
            + json.dumps(numbers, sort_keys=True, default=str),
        )
        brief = " ".join(str(raw or "").split())
        if not brief:
            return _brief_fallback(card)
        sentences = [s.strip() for s in brief.split(".") if s.strip()]
        if len(sentences) > 4:
            brief = ". ".join(sentences[:4]) + "."
        return brief
    except Exception:
        return _brief_fallback(card)


def write(conn, run_date: str, client: Any | None = None) -> Path:
    """Build and idempotently overwrite data/run_cards/{run_date}.json."""
    card = build(conn, run_date)
    card["morning_brief"] = _morning_brief(card, client=client)
    RUN_CARD_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_CARD_ROOT / f"{run_date}.json"
    # AUDIT-2: tmp+rename atomic write (match lessons.py's digest pattern) so
    # /api/desk/run-card can never read a torn/partial JSON file mid-write.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return path
