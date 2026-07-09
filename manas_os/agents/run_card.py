"""AD4: run_card — one canonical JSON artifact per night, written from tables
that already exist. Zero LLM, zero new computation, idempotent overwrite.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os import config
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
        "SELECT snapshot_date, market_mode, xp_value, mbi_day_color, r4p5, r10, r20, r50, vol_forecast "
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
            "vol_forecast": None,
        }
    age_days = None
    try:
        from datetime import date as _date

        age_days = (_date.fromisoformat(run_date) - _date.fromisoformat(row["snapshot_date"])).days
    except ValueError:
        pass
    # SHIP-1 #16 (I1): HAR-RV forecast, EXPERIMENTAL/display-only — written
    # by regime/vol_har.py ONLY when its walk-forward QLIKE beats the naive
    # baseline; null (never fabricated) otherwise. Never read by the governor.
    vol_forecast = None
    try:
        vol_forecast = _json(row["vol_forecast"], None) if "vol_forecast" in row.keys() else None
    except Exception:
        vol_forecast = None
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
        "vol_forecast": vol_forecast,
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
    # Latest attempt per stage only: an aborted earlier run the same day would
    # otherwise leave a stale 'partial' row that reads as an incomplete night.
    rows = conn.execute(
        "SELECT stage, status, rows_affected, duration_s, detail FROM pipeline_runs "
        "WHERE run_date = ? AND run_id IN "
        "(SELECT MAX(run_id) FROM pipeline_runs WHERE run_date = ? GROUP BY stage) "
        "ORDER BY run_id",
        (run_date, run_date),
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


def _has_fresh_scan(conn, run_date: str) -> bool:
    """Honest signal for 'did anything real happen tonight': an exact-date
    row in scan_candidates or regime_snapshots for run_date itself. A no-op
    night (agents_coach ran post-midnight with nothing new to scan) has
    neither — snapshot.py's phantom-snapshot guard already refuses to write
    a regime_snapshots row when breadth_daily has nothing for run_date, and
    the scanner never inserts scan_candidates for a date it didn't scan.
    Without this check, run_card.write minted a run_date-stamped card that
    silently carried the prior night's data forward as if it were fresh."""
    scan_row = conn.execute(
        "SELECT 1 FROM scan_candidates WHERE scan_date = ? LIMIT 1", (run_date,)
    ).fetchone()
    if scan_row is not None:
        return True
    snap_row = conn.execute(
        "SELECT 1 FROM regime_snapshots WHERE snapshot_date = ? LIMIT 1", (run_date,)
    ).fetchone()
    return snap_row is not None


def _errors(conn, run_date: str) -> list[dict[str, Any]]:
    # AU3: a total-outage night logs debate/chair/vision/sizer as status='fail'
    # (rows==0) — include it here so the card honestly records the failure
    # instead of silently omitting it (only 'error'/'partial' were checked).
    rows = conn.execute(
        "SELECT stage, detail FROM pipeline_runs WHERE run_date = ? AND status IN ('error', 'partial', 'fail') "
        "AND run_id IN (SELECT MAX(run_id) FROM pipeline_runs WHERE run_date = ? GROUP BY stage) "
        "ORDER BY run_id",
        (run_date, run_date),
    ).fetchall()
    return [{"stage": r["stage"], "detail": r["detail"]} for r in rows]


def build(conn, run_date: str) -> dict[str, Any]:
    scan_date = _scan_date(conn, run_date)
    regime = _regime(conn, run_date)
    return {
        "run_date": run_date,
        "scan_date": scan_date,
        "no_op": not _has_fresh_scan(conn, run_date),
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


def round_display(value: Any, digits: int = 2) -> float | None:
    """Shared rounding helper — the SAME values DeskTab.jsx's regime strip
    shows (xp 1-decimal, r10/r20/r50 2-decimal). Keeping one function means
    the morning brief can never drift from what the strip renders."""
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def r4p5_ratio(r4p5: Any) -> str:
    """r4p5 is stored as (up_4pct / down_4pct) * 100 (see regime/snapshot.py
    burst_ratio) — a raw value like 2100 reads as nonsense to a human. Render
    it as the up:down ratio it actually is, e.g. '21:1 up:down'."""
    value = round_display(r4p5, 4)
    if value is None:
        return "unavailable"
    up_per_down = value / 100.0
    if abs(up_per_down - round(up_per_down)) < 1e-9:
        formatted = str(int(round(up_per_down)))
    else:
        formatted = f"{round(up_per_down, 1)}"
    return f"{formatted}:1 up:down"


_MODE_MEANING = {
    "RISK_ON": "risk-on conditions support taking size.",
    "SELECTIVE": "selective conditions call for staying picky.",
    "DEFENSIVE": "defensive conditions call for caution and smaller size.",
    "NO_TRADE": "no-trade conditions mean cash is the trade tonight.",
}


def _mode_meaning(mode: str | None) -> str:
    return _MODE_MEANING.get((mode or "").upper(), "regime mode is unavailable tonight.")


def _morning_brief(card: dict[str, Any]) -> str:
    """AD5: deterministic template over run_card fields — zero LLM tokens.
    Uses the same rounding helpers (round_display/r4p5_ratio) that
    DeskTab.jsx's regime strip uses, so the brief text never disagrees with
    the numbers shown right above it on the DESK tab."""
    regime = card.get("regime") or {}
    ratios = regime.get("ratios") or {}
    mode = (card.get("governor") or {}).get("market_mode") or regime.get("mode")
    xp = round_display(regime.get("xp"), 1)
    r10 = round_display(ratios.get("r10"), 2)
    r20 = round_display(ratios.get("r20"), 2)
    r50 = round_display(ratios.get("r50"), 2)
    day_color = regime.get("mbi_day_color") or "unavailable"

    debate = card.get("debate", [])
    debate_models = len(debate)
    debate_verdicts = sum(int(r.get("verdicts") or 0) for r in debate)
    chair_takes = sum(1 for r in card.get("chair", []) if r.get("verdict") == "TAKE")
    sizer_takes = sum(1 for r in card.get("sizer", []) if r.get("verdict") == "TAKE")
    error_count = len(card.get("errors", []))
    shortlist_count = len(card.get("shortlist", []))

    sentence1 = (
        f"Regime {mode or 'UNKNOWN'}, day-color {day_color}, "
        f"XP {'unavailable' if xp is None else xp}."
    )
    sentence2 = (
        f"R10 {'—' if r10 is None else r10}, R20 {'—' if r20 is None else r20}, "
        f"R50 {'—' if r50 is None else r50}, burst-ratio {r4p5_ratio(ratios.get('r4p5'))}."
    )
    sentence3 = (
        f"Reviewed {shortlist_count} name{'s' if shortlist_count != 1 else ''} across "
        f"{debate_models} model{'s' if debate_models != 1 else ''} "
        f"({debate_verdicts} verdict{'s' if debate_verdicts != 1 else ''}); "
        f"chair took {chair_takes}, sizer took {sizer_takes}. "
        f"{error_count} pipeline issue{'s' if error_count != 1 else ''} recorded."
    )
    sentence4 = _mode_meaning(mode)
    return " ".join([sentence1, sentence2, sentence3, sentence4])


def write(conn, run_date: str, client: Any | None = None) -> Path:
    """Build and idempotently overwrite data/run_cards/{run_date}.json.
    `client` is accepted for call-site compatibility but is no longer used —
    the morning brief is a deterministic template (AD5), zero LLM tokens."""
    card = build(conn, run_date)
    card["morning_brief"] = _morning_brief(card)
    RUN_CARD_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_CARD_ROOT / f"{run_date}.json"
    # AUDIT-2: tmp+rename atomic write (match lessons.py's digest pattern) so
    # /api/desk/run-card can never read a torn/partial JSON file mid-write.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return path
