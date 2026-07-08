from __future__ import annotations

import json
from typing import Any

from manas_os import config
from manas_os.regime.governor import governor
from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import outcomes as scanner_outcomes


def _json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _latest_row(conn, table: str, date_col: str, on_or_before: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT * FROM {table} WHERE {date_col} <= ? ORDER BY {date_col} DESC LIMIT 1",
        (on_or_before,),
    ).fetchone()
    return dict(row) if row else None


def build_context_pack(conn, run_date: str) -> dict[str, Any]:
    regime = _latest_row(conn, "regime_snapshots", "snapshot_date", run_date)
    mode = (regime or {}).get("market_mode") or "SELECTIVE"
    if regime:
        regime["preferred_setups"] = _json(regime.pop("preferred_setups_json", None), [])
        regime["avoid_setups"] = _json(regime.pop("avoid_setups_json", None), [])
        regime["quadrant"] = _json(regime.pop("quadrant_json", None), {})

    breadth = [
        dict(r) for r in conn.execute(
            "SELECT trade_date, pct_above_20dma, advances, declines, up_4pct, down_4pct "
            "FROM breadth_daily WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 10",
            (run_date,),
        ).fetchall()
    ]

    cards_payload = scanner_candidates.load_persisted_candidates(conn, run_date, limit=80)
    gv = governor(mode)
    cards = []
    for item in (cards_payload.get("candidates") or [])[: gv["max_cards"]]:
        cards.append({
            "symbol": item.get("symbol"),
            "family": item.get("setup_family") or item.get("setup_type") or item.get("setup"),
            "rank": item.get("rank"),
            "rank_of": item.get("rank_of"),
            "gates": item.get("gates") or item.get("gates_json"),
            "evidence": item.get("evidence"),
            "plan": {
                "entry": item.get("entry"),
                "stop": item.get("stop"),
                "rr": item.get("rr"),
                "qty": item.get("suggested_qty"),
                **(item.get("trade_plan") or {}),
            },
            "expectancy": item.get("expectancy"),
        })

    scanner_candidates.ensure_refusals_schema(conn)
    refusals = [
        {
            "symbol": r["symbol"],
            "failed_gate": r["failed_gate"],
            "reason": r["reason"],
        }
        for r in conn.execute(
            "SELECT symbol, failed_gate, reason FROM refusals "
            "WHERE scan_date <= ? ORDER BY scan_date DESC, symbol LIMIT 10",
            (run_date,),
        ).fetchall()
    ]

    positions = _positions(conn, run_date)
    heat = _portfolio_heat(conn, mode)
    symbols = sorted({c["symbol"] for c in cards if c.get("symbol")} | {p["symbol"] for p in positions if p.get("symbol")})
    return {
        "as_of": run_date,
        "regime": {"snapshot": regime, "governor": gv},
        "breadth_trend": breadth,
        "cards": cards,
        "refusals": refusals,
        "positions": positions,
        "heat": heat,
        "structure_events": _structure_events(conn, run_date, cards, positions),
        "events": _events(conn, run_date, symbols),
    }


def _positions(conn, run_date: str) -> list[dict[str, Any]]:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_trades)")}
    exit_col = ", exit_state_json" if "exit_state_json" in cols else ""
    rows = conn.execute(
        f"SELECT trade_id, trade_date, symbol, setup, entry, stop, first_exit_flag_date{exit_col} "
        "FROM journal_trades WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
    ).fetchall()
    out = []
    for row in rows:
        out.append({
            "trade_id": row["trade_id"],
            "symbol": row["symbol"],
            "setup": row["setup"],
            "entry": row["entry"],
            "stop": row["stop"],
            "coach": _json(row["exit_state_json"], None) if "exit_state_json" in cols else None,
        })
    return out


def _portfolio_heat(conn, mode: str) -> dict[str, Any]:
    scanner_outcomes.ensure_setup_decisions_schema(conn)
    capital = float(config.get("risk.capital", 1_000_000) or 1_000_000)
    gv = governor(mode)
    cap_pct = gv.get("open_risk_cap_pct")
    rows = conn.execute(
        "SELECT trade_id, trade_date, symbol, setup, entry, stop FROM journal_trades "
        "WHERE exit IS NULL ORDER BY trade_date DESC, trade_id DESC"
    ).fetchall()
    positions = []
    sector_counts: dict[str, int] = {}
    open_risk_pct = 0.0
    for row in rows:
        decision = conn.execute(
            "SELECT qty, snapshot_json FROM setup_decisions WHERE scan_date = ? AND symbol = ?",
            (row["trade_date"], row["symbol"]),
        ).fetchone()
        qty = int(decision["qty"]) if decision and decision["qty"] is not None else 0
        sector = None
        if decision and decision["snapshot_json"]:
            try:
                sector = json.loads(decision["snapshot_json"]).get("sector")
            except json.JSONDecodeError:
                sector = None
        entry = float(row["entry"]) if row["entry"] is not None else None
        stop = float(row["stop"]) if row["stop"] is not None else None
        risk_pct = 0.0
        if entry is not None and stop is not None and entry > 0 and qty > 0 and capital > 0:
            risk_pct = (entry - stop) / entry * qty * entry / capital * 100.0
        open_risk_pct += risk_pct
        if sector:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        positions.append({
            "symbol": row["symbol"],
            "entry": entry,
            "stop": stop,
            "qty": qty,
            "risk_pct": round(risk_pct, 4),
            "sector": sector,
        })
    closed = conn.execute(
        "SELECT r_result FROM journal_trades WHERE exit IS NOT NULL AND r_result IS NOT NULL "
        "ORDER BY trade_date DESC, trade_id DESC LIMIT 10"
    ).fetchall()
    r_values = [float(r["r_result"]) for r in closed]
    rolling_avg = round(sum(r_values) / len(r_values), 2) if r_values else None
    return {
        "open_risk_pct": round(open_risk_pct, 4),
        "cap_pct": cap_pct,
        "positions": positions,
        "sector_counts": sector_counts,
        "rolling_10_avg_r": {"value": rolling_avg, "n": len(r_values)},
        "half_size_mode": bool(len(r_values) >= 10 and rolling_avg is not None and rolling_avg < 0),
    }


def _structure_events(conn, run_date: str, cards: list[dict[str, Any]], positions: list[dict[str, Any]]) -> dict[str, Any]:
    latest = conn.execute(
        "SELECT symbol, open, close, prev_close FROM daily_prices "
        "WHERE trade_date <= ? AND series = 'EQ' ORDER BY trade_date DESC LIMIT 1",
        (run_date,),
    ).fetchone()
    index_gap = None
    if latest and latest["open"] is not None and latest["prev_close"]:
        index_gap = round((float(latest["open"]) - float(latest["prev_close"])) / float(latest["prev_close"]) * 100, 2)
    symbols = {c.get("symbol") for c in cards} | {p.get("symbol") for p in positions}
    gaps = []
    for symbol in sorted(s for s in symbols if s):
        row = conn.execute(
            "SELECT open, prev_close FROM daily_prices WHERE symbol = ? AND trade_date <= ? "
            "AND series = 'EQ' ORDER BY trade_date DESC LIMIT 1",
            (symbol, run_date),
        ).fetchone()
        if row and row["open"] is not None and row["prev_close"]:
            gap = round((float(row["open"]) - float(row["prev_close"])) / float(row["prev_close"]) * 100, 2)
            if abs(gap) > 2:
                gaps.append({"symbol": symbol, "gap_pct": gap})
    dist = conn.execute(
        "SELECT nifty_chg_pct FROM breadth_daily WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 5",
        (run_date,),
    ).fetchall()
    distribution_days_5 = sum(1 for r in dist if r["nifty_chg_pct"] is not None and float(r["nifty_chg_pct"]) < 0)
    return {"index_gap_pct": index_gap, "gaps_gt_2pct": gaps, "drawdowns_gt_1r": [], "distribution_days_5": distribution_days_5}


def _events(conn, run_date: str, symbols: list[str]) -> list[dict[str, Any]]:
    if not symbols:
        return []
    placeholders = ",".join("?" for _ in symbols)
    rows = conn.execute(
        f"SELECT trade_date, symbol, kind, detail_json FROM disclosures "
        f"WHERE symbol IN ({placeholders}) AND trade_date >= ? "
        "ORDER BY trade_date, symbol LIMIT 50",
        (*symbols, run_date),
    ).fetchall()
    return [{"trade_date": r["trade_date"], "symbol": r["symbol"], "kind": r["kind"], "detail": _json(r["detail_json"], {})} for r in rows]
