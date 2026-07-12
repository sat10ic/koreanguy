"""Configurable mentor checklist definitions and response storage schema."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from manas_os import config

_PKG_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _PKG_DIR / "design" / "mentor_checklists.yaml"


def _configured_path() -> Path:
    override = config.get("mentor_checklists.path")
    if not override:
        return _DEFAULT_PATH
    path = Path(str(override))
    return path if path.is_absolute() else _PKG_DIR / path


def _read_checklists() -> list[dict[str, Any]]:
    path = _configured_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    checklists = data.get("checklists", [])
    return checklists if isinstance(checklists, list) else []


_CHECKLISTS = _read_checklists()


def load_checklists() -> list[dict[str, Any]]:
    """Return configured mentor checklists from the module-import cache."""
    return deepcopy(_CHECKLISTS)


def ensure_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checklist_responses (
            response_date TEXT NOT NULL,
            checklist_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            checked INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(response_date, checklist_id, item_id)
        )
        """
    )
    # Per-symbol ticks (guru evaluate path); additive.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checklist_symbol_ticks (
            response_date TEXT NOT NULL,
            checklist_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            item_id TEXT NOT NULL,
            checked INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY(response_date, checklist_id, symbol, item_id)
        )
        """
    )


def _auto_value(field: str, ctx: dict[str, Any]) -> tuple[bool | None, str]:
    if field == "regime_mode_not_no_trade":
        mode = str(ctx.get("regime_mode") or "").upper()
        if not mode:
            return None, "regime unavailable"
        return mode != "NO_TRADE", f"regime={mode}"
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
        return pct <= 8.0, f"stop {pct:.1f}% vs 8% cap"
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


def evaluate(
    checklist: dict[str, Any],
    *,
    symbol: str,
    trade_date: str,
    ctx: dict[str, Any] | None,
    ticks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """AUTO/MANUAL evaluation. Advisory only — never blocks plan/gates."""
    ctx = ctx or {}
    ticks = ticks or {}
    items_out = []
    hard_fails: list[str] = []
    n_pass = n_total = 0
    for it in checklist.get("items") or []:
        n_total += 1
        item_id = str(it.get("id"))
        kind = str(it.get("kind") or "soft")
        ev = str(it.get("eval") or "MANUAL").upper()
        row = {
            "id": item_id,
            "text": it.get("text"),
            "source_cite": it.get("source_cite"),
            "kind": kind,
            "scope": it.get("scope"),
            "eval": ev,
            "state": "UNAVAILABLE",
            "display": "",
            "advisory_only": True,
        }
        if ev == "AUTO":
            ok, display = _auto_value(str(it.get("auto_field") or ""), ctx)
            row["display"] = display
            if ok is None:
                row["state"] = "UNAVAILABLE"
            elif ok:
                row["state"] = "PASS"
                n_pass += 1
            else:
                row["state"] = "FAIL"
                if kind == "hard":
                    hard_fails.append(item_id)
        else:
            ticked = bool(ticks.get(item_id))
            row["state"] = "PASS" if ticked else "UNCHECKED"
            row["display"] = "user tick" if ticked else "manual"
            if ticked:
                n_pass += 1
            elif kind == "hard":
                hard_fails.append(item_id)
        items_out.append(row)
    return {
        "available": True,
        "checklist_id": checklist.get("id"),
        "mentor": checklist.get("mentor"),
        "name": checklist.get("title") or checklist.get("name"),
        "symbol": symbol.upper(),
        "trade_date": trade_date,
        "summary": f"{n_pass} of {n_total}",
        "hard_fails": hard_fails,
        "hard_fail_warning": bool(hard_fails),
        "blocks_plan": False,
        "items": items_out,
    }
