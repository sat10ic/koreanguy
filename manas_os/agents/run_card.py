"""AD4: run_card — one canonical JSON artifact per night, written from tables
that already exist. Zero LLM, zero new computation, idempotent overwrite.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import re

from manas_os import config
from manas_os.agents.context_pack import LESSON_DIGEST_PATH
from manas_os.regime.governor import governor as _governor
from manas_os.regime import regime_hmm as _regime_hmm
from manas_os.regime import snapshot as _regime_snapshot
from manas_os.regime import four_phase as _four_phase_module
from manas_os.scanner import expectancy as _scanner_expectancy
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


def _known_pillars(technical_detail: str | None) -> int | None:
    if not technical_detail:
        return None
    match = re.search(r"known_pillars=(\d+)", technical_detail)
    return int(match.group(1)) if match else None


def _regime(conn, run_date: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT snapshot_date, market_mode, xp_value, mbi_day_color, r4p5, r10, r20, r50, "
        "vol_forecast, pillars_passed, technical_detail, four_phase_json, choppy_brake_json "
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
            "vol_forecast_as_of": None,
            "four_phase": None,
            "four_phase_confidence": None,
            "four_phase_evidence": None,
            "four_phase_cite": _regime_snapshot.FOUR_PHASE_CITE,
            "choppy_brake": {"active": False, "reason": None, "evidence": {}},
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
    # SHIP-3 #3: the forecast is written onto the SAME regime_snapshots row it
    # is read from (regime/vol_har.py:run() updates the row for its own
    # run_date), so the row's own snapshot_date IS the forecast's as_of date.
    # Surfaced explicitly so the desk can flag it stale when this regime row
    # is older than the card's scan_date (e.g. HAR-RV didn't run tonight).
    vol_forecast_as_of = row["snapshot_date"] if vol_forecast is not None else None
    # SHIP-1 #17 (I5): HMM confirmation caption. RENDER RULE (locked): the
    # caption is the ONLY thing surfaced — never the raw label — until the
    # 20-live-session display gate passes (regime_hmm.get_display_caption
    # already enforces this; never call anything else here).
    try:
        hmm = _regime_hmm.get_display_caption(conn, row["snapshot_date"])
    except Exception:
        hmm = {"display_allowed": False, "sessions_counted": 0,
               "caption": "HMM confirm: unavailable", "hmm_label": None}

    # M9: real four-phase classifier (regime/four_phase.py), persisted by
    # regime/snapshot.py.run() onto this same row. Falls back to the old
    # display-caption approximation (four_phase_label) only when the
    # classifier itself produced no phase (e.g. pre-M9 row, or missing
    # breadth data) — never silently prefers the caption over a real read.
    four_phase_data = _json(
        row["four_phase_json"] if "four_phase_json" in row.keys() else None, {}
    ) or {}
    real_phase = four_phase_data.get("phase")
    choppy_brake_data = _json(
        row["choppy_brake_json"] if "choppy_brake_json" in row.keys() else None,
        {"active": False, "reason": None, "evidence": {}},
    ) or {"active": False, "reason": None, "evidence": {}}

    four_phase = real_phase or _regime_snapshot.four_phase_label(
        row["market_mode"],
        row["mbi_day_color"],
        row["pillars_passed"] if "pillars_passed" in row.keys() else None,
        _known_pillars(row["technical_detail"] if "technical_detail" in row.keys() else None),
    )

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
        "vol_forecast_as_of": vol_forecast_as_of,
        "hmm_caption": hmm["caption"],
        "hmm_display_allowed": hmm["display_allowed"],
        "hmm_sessions_counted": hmm["sessions_counted"],
        # M9: real four-phase read (regime/four_phase.py) — rate-of-change of
        # %-above-MA breadth + NH/NL trend, NOT a market_mode caption anymore.
        # Still display-only: does not feed the governor/gates.
        "four_phase": four_phase,
        "four_phase_confidence": four_phase_data.get("confidence"),
        "four_phase_evidence": four_phase_data.get("evidence"),
        "four_phase_cite": _four_phase_module.CITE if real_phase else _regime_snapshot.FOUR_PHASE_CITE,
        "choppy_brake": choppy_brake_data,
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


def _has_any_data(scan_date: str | None, regime: dict[str, Any]) -> bool:
    """SHIP-2: one night's scan -> one card keyed by scan_date. A run_date
    that fires post-midnight (agents_coach reruns after midnight with
    nothing new to scan) still resolves the SAME scan_date as the original
    run — that is a real, describable night, not a no-op. A card is no_op
    ONLY when there is genuinely nothing to describe: no scan_date resolvable
    AND no regime snapshot resolvable either (a true empty night, e.g. before
    the pipeline ever ran)."""
    return scan_date is not None or regime.get("mode") is not None


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


def _sizer_chair_consistency(conn, scan_date: str | None) -> list[dict[str, Any]]:
    """Build-time display-truth guard (UI_BUILD_DIRECTION 4c): the sizer only
    ever prices chair TAKE rows, so any symbol with a sizer verdict must have a
    chair verdict of TAKE **or** a recorded strike (lens.struck). A sizer row
    whose chair reads SKIP-without-strike means the strike transition was lost
    between the two readers -- record it as an error rather than let the card
    silently disagree with the debate payload."""
    if not scan_date:
        return []
    rows = conn.execute(
        "SELECT symbol, agent, verdict, reasoning, lens_scores_json FROM agent_verdicts "
        "WHERE scan_date = ? AND agent IN ('chair', 'sizer')",
        (scan_date,),
    ).fetchall()
    chair_by: dict[str, Any] = {}
    sizer_symbols: set[str] = set()
    for r in rows:
        if r["agent"] == "sizer":
            sizer_symbols.add(r["symbol"])
        else:
            chair_by[r["symbol"]] = r
    errors: list[dict[str, Any]] = []
    for symbol in sorted(sizer_symbols):
        chair_row = chair_by.get(symbol)
        if chair_row is None:
            errors.append({"stage": "chair_sizer_consistency", "detail": f"{symbol}: sized with no chair verdict"})
            continue
        lens = _json(chair_row["lens_scores_json"], {})
        struck = lens.get("struck")
        if struck is None:  # pre-migration row: fall back to the prose marker
            struck = "struck: no" not in (chair_row["reasoning"] or "") and "struck:" in (chair_row["reasoning"] or "")
        if chair_row["verdict"] != "TAKE" and not struck:
            errors.append({
                "stage": "chair_sizer_consistency",
                "detail": f"{symbol}: sizer priced this name but chair={chair_row['verdict']} and not struck",
            })
    return errors


_STANCE_WHAT_TO_DO = {
    "STAND_ASIDE": [
        "Nothing to buy tonight — the regime itself says cash is the position.",
        "Do not override tonight's risk rules (the governor); a NO_TRADE night is a rule, not a suggestion.",
        "Re-check tomorrow's regime snapshot before looking at any setup.",
    ],
    "SIT_OUT": [
        "Nothing to buy tonight.",
        "Check the watchlist arrows — names the models upgraded (PROMOTE) are tomorrow's first look.",
        "If tempted anyway, paper-trade it and journal the itch.",
    ],
    "CAUTION": [
        "The setup cleared every gate, but its own track record argues against full size.",
        "Paper-trade it or cut the size in half — tonight's risk rules (the law), not a guess.",
        "Log the outcome either way so the historical win rate (base rate) keeps improving.",
    ],
    "ACT_PER_PLAN": [
        "Take the plan(s) below at the sizing the sizer already computed.",
        "Enter only at the stated entry/stop; do not chase past it.",
        "Journal the trade the same night so tomorrow's historical win rate (base rate) stays honest.",
    ],
}


_CHOPPY_FOUR_PHASES = {"Lack of Demand", "Supply Domination"}
_CHOPPY_MARKET_LINE = (
    "Choppy-tape read (four-phase: {phase}) — setups trigger but don't follow through in this "
    "phase; that's what a choppy market looks like, not a reason to distrust the setup itself. "
    "TradeTM: 3-4 stops in one week means the market is too tricky — take a 1-2 week break rather "
    "than force size. [TTM-C3, TTM-S21, AR-Market-Condition, AR-Poor-Market-Signal]"
)
_LACK_OF_SUPPLY_LINE = (
    "Lack of Supply (four-phase): supply exhausted after the prior distribution — long setups "
    "tend to follow through rather than reverse in this phase, unlike a 'Lack of' choppy read. "
    "[TradeTM C1]"
)


def _with_choppy_line(what_to_do: list[str], four_phase: str | None) -> list[str]:
    """CODEABLE, deterministic template extension (not a gate). Per TradeTM
    doctrine (design/knowledge/TRADETM_NUANCES.md C1): 'Lack of Demand' and
    'Supply Domination' are the choppy/failure-prone four-phase reads —
    setups trigger but don't follow through. 'Lack of Supply' is the
    OPPOSITE: after major supply exhaustion, long setups perform
    exceptionally well, so it gets a constructive note instead of a caution.
    """
    if four_phase == "Lack of Supply":
        return [*what_to_do, _LACK_OF_SUPPLY_LINE]
    if four_phase not in _CHOPPY_FOUR_PHASES:
        return what_to_do
    return [*what_to_do, _CHOPPY_MARKET_LINE.format(phase=four_phase)]


def _take_symbols_with_family(card: dict[str, Any]) -> list[tuple[str, str]]:
    """(symbol, setup_family) for every chair TAKE, family from the shortlist row
    the chair verdict was cast on. Symbols with no shortlist match are skipped —
    they contribute no family to check a base rate against."""
    family_by_symbol = {row["symbol"]: row["setup_family"] for row in card.get("shortlist", [])}
    out = []
    for row in card.get("chair", []):
        if row.get("verdict") == "TAKE":
            family = family_by_symbol.get(row["symbol"])
            if family:
                out.append((row["symbol"], family))
    return out


def _tonights_call(conn, card: dict[str, Any]) -> dict[str, Any]:
    """SHIP-2 finding 3: the constructive layer. A deterministic verdict block
    that tells a beginner what to DO tonight, derived only from fields already
    on the card (governor law, chair verdicts, base rates via
    scanner.expectancy.chip_for) -- zero LLM, zero new computation.

    Stance decision table (first match wins):
      NO_TRADE regime          -> STAND_ASIDE
      chair took 0              -> SIT_OUT
      TAKE(s) but family base
        rate negative, n>=20    -> CAUTION
      TAKE(s), rate positive/
        unproven                -> ACT_PER_PLAN
    """
    mode = (card.get("governor") or {}).get("market_mode") or (card.get("regime") or {}).get("mode")
    four_phase = (card.get("regime") or {}).get("four_phase")
    choppy_brake = (card.get("regime") or {}).get("choppy_brake") or {}
    brake_active = bool(choppy_brake.get("active"))
    brake_reason = choppy_brake.get("reason")
    chair_rows = card.get("chair", [])
    reviewed_count = len(chair_rows)
    takes = _take_symbols_with_family(card)
    take_count = len(takes)

    if (mode or "").upper() == "NO_TRADE":
        return {
            "stance": "STAND_ASIDE",
            "headline": "No trades by design — cash is the position.",
            "what_to_do": _STANCE_WHAT_TO_DO["STAND_ASIDE"],
        }

    if take_count == 0:
        return {
            "stance": "SIT_OUT",
            "headline": (
                f"The desk's edge tonight is NOT trading. {reviewed_count} name"
                f"{'s' if reviewed_count != 1 else ''} reviewed, none worth capital."
            ),
            "what_to_do": _with_choppy_line(_STANCE_WHAT_TO_DO["SIT_OUT"], four_phase),
        }

    worst_family = None
    worst_chip = None
    worst_mean_r = None
    regime_for_chip = mode or "UNKNOWN"
    for _symbol, family in takes:
        chip = _scanner_expectancy.chip_for(conn, family, regime_for_chip)
        system = (chip or {}).get("system")
        if not system:
            continue
        n = int(system.get("n") or 0)
        mean_r = system.get("mean_r")
        if n >= _scanner_expectancy.TRUST_FLOOR_N and mean_r is not None and mean_r < 0:
            if worst_mean_r is None or mean_r < worst_mean_r:
                worst_family, worst_chip, worst_mean_r = family, system, mean_r

    if worst_chip is not None:
        what_to_do = _with_choppy_line(_STANCE_WHAT_TO_DO["CAUTION"], four_phase)
        if brake_active and brake_reason:
            what_to_do = [*what_to_do, f"Choppy brake ON: {brake_reason} — do not add new entries tonight."]
        return {
            "stance": "CAUTION",
            "headline": (
                f"Setup passed the gate but its historical win rate (base rate) is negative "
                f"(n={worst_chip['n']}) — paper-trade or half-size per tonight's risk rules (the law)."
            ),
            "what_to_do": what_to_do,
        }

    # M9: choppy brake (3+ stops in 5 trading days, or weekly DD >= 4-5%)
    # floors the stance at CAUTION even when everything else says
    # ACT_PER_PLAN — TradeTM W3/W4: stop taking new entries when the tape
    # has been chopping you up.
    if brake_active:
        return {
            "stance": "CAUTION",
            "headline": (
                f"Choppy brake is ON ({brake_reason}) — {take_count} setup"
                f"{'s' if take_count != 1 else ''} cleared the gate, but this is not the week to add new entries."
            ),
            "what_to_do": [
                *_STANCE_WHAT_TO_DO["CAUTION"],
                f"Choppy brake ON: {brake_reason}.",
            ],
        }

    return {
        "stance": "ACT_PER_PLAN",
        "headline": (
            f"{take_count} setup{'s' if take_count != 1 else ''} cleared the gate — "
            f"trade it per plan, sized as the sizer computed."
        ),
        "what_to_do": _STANCE_WHAT_TO_DO["ACT_PER_PLAN"],
    }


def build(conn, run_date: str) -> dict[str, Any]:
    scan_date = _scan_date(conn, run_date)
    regime = _regime(conn, run_date)
    card = {
        "run_date": run_date,
        "scan_date": scan_date,
        "no_op": not _has_any_data(scan_date, regime),
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
        "errors": _errors(conn, run_date) + _sizer_chair_consistency(conn, scan_date),
    }
    card["tonights_call"] = _tonights_call(conn, card)
    return card


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
    # SHIP-2 #3: "reviewed" must mean debated (chair verdicts, one per
    # distinct symbol the debate actually ran on) — not gate-passed
    # shortlist count. A SELECTIVE night can debate 10 names while only 1
    # clears every gate; the old wording ("Reviewed 1 name") silently
    # dropped the other 9 the chair/vision/sizer rows plainly show.
    reviewed_count = len(card.get("chair", []))
    near_miss_count = max(reviewed_count - shortlist_count, 0)
    split_note = ""
    if reviewed_count and reviewed_count != shortlist_count:
        split_note = f" ({shortlist_count} gate-passed, {near_miss_count} near-miss)"

    sentence1 = (
        f"Regime {mode or 'UNKNOWN'}, day-color {day_color}, "
        f"XP {'unavailable' if xp is None else xp}."
    )
    sentence2 = (
        f"R10 {'—' if r10 is None else r10}, R20 {'—' if r20 is None else r20}, "
        f"R50 {'—' if r50 is None else r50}, burst-ratio {r4p5_ratio(ratios.get('r4p5'))}."
    )
    sentence3 = (
        f"Reviewed {reviewed_count} name{'s' if reviewed_count != 1 else ''}{split_note} across "
        f"{debate_models} model{'s' if debate_models != 1 else ''} "
        f"({debate_verdicts} verdict{'s' if debate_verdicts != 1 else ''}); "
        f"chair took {chair_takes}, sizer took {sizer_takes}. "
        f"{error_count} pipeline issue{'s' if error_count != 1 else ''} recorded."
    )
    sentence4 = _mode_meaning(mode)
    return " ".join([sentence1, sentence2, sentence3, sentence4])


def write(conn, run_date: str, client: Any | None = None) -> Path:
    """Build and idempotently overwrite data/run_cards/{canonical_date}.json.
    `client` is accepted for call-site compatibility but is no longer used —
    the morning brief is a deterministic template (AD5), zero LLM tokens.

    SHIP-2: one night's scan -> one card, keyed by the scan_date it carries
    (not by whatever run_date triggered the write). A post-midnight rerun of
    the same night (run_date rolls to the next calendar day, scan_date does
    not) must overwrite the SAME file the original run wrote, instead of
    minting a second run_date-stamped card that the desk then has to choose
    between. Only when no scan_date is resolvable (a truly empty night) does
    the card fall back to being keyed by run_date itself."""
    card = build(conn, run_date)
    card["morning_brief"] = _morning_brief(card)
    canonical_date = card["scan_date"] or card["run_date"]
    RUN_CARD_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_CARD_ROOT / f"{canonical_date}.json"
    # AUDIT-2: tmp+rename atomic write (match lessons.py's digest pattern) so
    # /api/desk/run-card can never read a torn/partial JSON file mid-write.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return path
