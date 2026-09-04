"""Guru/mentor checklists — source-cited, advisory, never gate-binding."""
from __future__ import annotations

import json
from typing import Any

ARORA_ENTRY_ID = "arora_entry_v1"

# Each item: id, text, source_cite, kind hard|soft, scope, eval AUTO|MANUAL, auto_field optional
ARORA_ENTRY_ITEMS: list[dict[str, Any]] = [
    {
        "id": "breadth_ok",
        "text": "Market / breadth not clearly hostile (not NO_TRADE posture if trading continuation).",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Strong Start; design/knowledge/INDIA_PLAYBOOK.md regime",
        "kind": "hard",
        "scope": "market",
        "eval": "AUTO",
        "auto_field": "regime_mode_not_no_trade",
    },
    {
        "id": "rs_leadership",
        "text": "Relative strength / leadership present (RS not in the dumpster).",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Liquidity Force / leadership",
        "kind": "soft",
        "scope": "entry",
        "eval": "AUTO",
        "auto_field": "rs_ge_50",
    },
    {
        "id": "stop_distance_sane",
        "text": "Stop distance is tradeable (tight enough for size, not > regime-style wide noise).",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Tight Stop = Higher Position Size",
        "kind": "hard",
        "scope": "entry",
        "eval": "AUTO",
        "auto_field": "stop_pct_le_8",
    },
    {
        "id": "position_size_from_risk",
        "text": "Quantity comes from risk / stop distance — not a round-lot guess.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Tight Stop; INDIA_PLAYBOOK §5 R1",
        "kind": "hard",
        "scope": "entry",
        "eval": "AUTO",
        "auto_field": "has_final_qty",
    },
    {
        "id": "no_chase_huge_gap",
        "text": "Not chasing a gap that ruins R:R (Arora gap limit ~10%; Strong Start ~5-6%).",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Gap Limit Rule; LENS_STRONG_START gap disqualifier",
        "kind": "hard",
        "scope": "entry",
        "eval": "MANUAL",
    },
    {
        "id": "wait_after_open",
        "text": "Do not enter at 9:15; wait ~3 minutes for Strong Start / open reads.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Strong Start open≈low",
        "kind": "hard",
        "scope": "entry",
        "eval": "MANUAL",
    },
    {
        "id": "no_averaging_down",
        "text": "No averaging down a loser — adds only on strength / planned pyramid rules.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Pyramiding",
        "kind": "hard",
        "scope": "manage",
        "eval": "MANUAL",
    },
    {
        "id": "pyramid_size_cap",
        "text": "Second unit size ≤ first unit size when pyramiding.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Pyramiding",
        "kind": "soft",
        "scope": "manage",
        "eval": "MANUAL",
    },
    {
        "id": "live_stop_order",
        "text": "Stop is a live broker order, not a mental stop.",
        "source_cite": "design/knowledge/INDIA_PLAYBOOK.md §5 R12; ARORA risk practice",
        "kind": "hard",
        "scope": "entry",
        "eval": "MANUAL",
    },
    {
        "id": "journal_before_entry",
        "text": "Thesis / checklist noted before entry (journal-before-entry discipline).",
        "source_cite": "design/knowledge/TRADETM_NUANCES (process); ARORA trade review practice",
        "kind": "soft",
        "scope": "entry",
        "eval": "MANUAL",
    },
    {
        "id": "vcp_or_base_quality",
        "text": "If trading a base/VCP: contraction + quality structure, not just tightness.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §VCP; §Consolidation Quality",
        "kind": "soft",
        "scope": "entry",
        "eval": "MANUAL",
    },
    {
        "id": "home_run_patience",
        "text": "Expect few home runs; do not cut winners solely because a single is green.",
        "source_cite": "design/knowledge/ARORA_SHARDS_NUANCES.md §Distribution of Trade Outcomes",
        "kind": "soft",
        "scope": "manage",
        "eval": "MANUAL",
    },
]


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS guru_checklists ("
        "checklist_id TEXT PRIMARY KEY, mentor TEXT NOT NULL, name TEXT NOT NULL, "
        "items_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS guru_checklist_ticks ("
        "checklist_id TEXT NOT NULL, symbol TEXT NOT NULL, trade_date TEXT NOT NULL, "
        "item_id TEXT NOT NULL, ticked INTEGER NOT NULL DEFAULT 0, "
        "updated_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY(checklist_id, symbol, trade_date, item_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS guru_checklist_user_config ("
        "user_checklist_id TEXT PRIMARY KEY, parent_checklist_id TEXT NOT NULL, "
        "name TEXT NOT NULL, enabled_item_ids_json TEXT NOT NULL, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )


def seed_arora_entry(conn) -> str:
    ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO guru_checklists (checklist_id, mentor, name, items_json) "
        "VALUES (?,?,?,?)",
        (
            ARORA_ENTRY_ID,
            "Manas Arora",
            "Arora entry discipline",
            json.dumps(ARORA_ENTRY_ITEMS, sort_keys=True),
        ),
    )
    conn.commit()
    return ARORA_ENTRY_ID


def list_checklists(conn) -> list[dict[str, Any]]:
    ensure_schema(conn)
    seed_arora_entry(conn)
    rows = conn.execute(
        "SELECT checklist_id, mentor, name, items_json FROM guru_checklists ORDER BY checklist_id"
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "checklist_id": r["checklist_id"],
            "mentor": r["mentor"],
            "name": r["name"],
            "items": json.loads(r["items_json"]),
        })
    return out


def _auto_value(field: str, ctx: dict[str, Any]) -> tuple[bool | None, str]:
    """Return (pass?, display). None pass = unavailable."""
    if field == "regime_mode_not_no_trade":
        mode = str(ctx.get("regime_mode") or "").upper()
        if not mode:
            return None, "regime unavailable"
        ok = mode != "NO_TRADE"
        return ok, f"regime={mode}"
    if field == "rs_ge_50":
        rs = ctx.get("rs")
        if rs is None:
            return None, "RS unavailable"
        try:
            v = float(rs)
        except (TypeError, ValueError):
            return None, "RS unavailable"
        return v >= 50, f"RS={v:.0f}"
    if field == "stop_pct_le_8":
        entry, stop = ctx.get("entry"), ctx.get("stop")
        if entry is None or stop is None:
            return None, "plan entry/stop unavailable"
        try:
            e, s = float(entry), float(stop)
            pct = (e - s) / e * 100.0 if e else None
        except (TypeError, ValueError, ZeroDivisionError):
            return None, "plan entry/stop unavailable"
        if pct is None:
            return None, "plan entry/stop unavailable"
        return pct <= 8.0, f"stop {pct:.1f}% vs 8% soft cap"
    if field == "has_final_qty":
        q = ctx.get("final_qty")
        if q is None:
            return None, "final_qty unavailable"
        try:
            qi = int(q)
        except (TypeError, ValueError):
            return None, "final_qty unavailable"
        return qi > 0, f"final_qty={qi}"
    return None, f"unknown field {field}"


def evaluate_checklist(
    conn,
    checklist_id: str,
    *,
    symbol: str,
    trade_date: str,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate AUTO items from ctx; MANUAL from ticks table. Advisory only."""
    ensure_schema(conn)
    seed_arora_entry(conn)
    row = conn.execute(
        "SELECT mentor, name, items_json FROM guru_checklists WHERE checklist_id=?",
        (checklist_id,),
    ).fetchone()
    if not row:
        return {"available": False, "checklist_id": checklist_id, "items": []}
    items = json.loads(row["items_json"])
    ctx = ctx or {}
    ticks = {
        r["item_id"]: bool(r["ticked"])
        for r in conn.execute(
            "SELECT item_id, ticked FROM guru_checklist_ticks "
            "WHERE checklist_id=? AND symbol=? AND trade_date=?",
            (checklist_id, symbol.upper(), trade_date),
        ).fetchall()
    }
    out_items = []
    hard_fails = []
    n_pass = n_total = 0
    for it in items:
        n_total += 1
        entry = {
            "id": it["id"],
            "text": it["text"],
            "source_cite": it["source_cite"],
            "kind": it["kind"],
            "scope": it["scope"],
            "eval": it["eval"],
            "state": "UNAVAILABLE",
            "display": "",
            "advisory_only": True,
        }
        if it["eval"] == "AUTO":
            ok, display = _auto_value(it.get("auto_field") or "", ctx)
            entry["display"] = display
            if ok is None:
                entry["state"] = "UNAVAILABLE"
            else:
                entry["state"] = "PASS" if ok else "FAIL"
                if ok:
                    n_pass += 1
                elif it["kind"] == "hard":
                    hard_fails.append(it["id"])
        else:
            ticked = ticks.get(it["id"], False)
            entry["state"] = "PASS" if ticked else "UNCHECKED"
            entry["display"] = "user tick" if ticked else "manual"
            if ticked:
                n_pass += 1
            elif it["kind"] == "hard":
                hard_fails.append(it["id"])
        out_items.append(entry)
    return {
        "available": True,
        "checklist_id": checklist_id,
        "mentor": row["mentor"],
        "name": row["name"],
        "symbol": symbol.upper(),
        "trade_date": trade_date,
        "summary": f"{n_pass} of {n_total}",
        "hard_fails": hard_fails,
        "hard_fail_warning": bool(hard_fails),
        "blocks_plan": False,  # advisory never blocks
        "items": out_items,
    }


def set_tick(conn, checklist_id: str, symbol: str, trade_date: str, item_id: str, ticked: bool) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO guru_checklist_ticks (checklist_id, symbol, trade_date, item_id, ticked, updated_at) "
        "VALUES (?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(checklist_id, symbol, trade_date, item_id) DO UPDATE SET "
        "ticked=excluded.ticked, updated_at=datetime('now')",
        (checklist_id, symbol.upper(), trade_date, item_id, 1 if ticked else 0),
    )
    conn.commit()


def duplicate_checklist(conn, parent_id: str, name: str, enabled_ids: list[str] | None = None) -> str:
    ensure_schema(conn)
    from uuid import uuid4
    parent = conn.execute(
        "SELECT items_json FROM guru_checklists WHERE checklist_id=?", (parent_id,)
    ).fetchone()
    if not parent:
        raise ValueError("unknown parent checklist")
    items = json.loads(parent["items_json"])
    if enabled_ids is None:
        enabled_ids = [i["id"] for i in items]
    uid = uuid4().hex
    conn.execute(
        "INSERT INTO guru_checklist_user_config "
        "(user_checklist_id, parent_checklist_id, name, enabled_item_ids_json) VALUES (?,?,?,?)",
        (uid, parent_id, name, json.dumps(enabled_ids)),
    )
    conn.commit()
    return uid
