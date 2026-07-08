from __future__ import annotations

import json
import time
from typing import Any

from manas_os import config
from manas_os.advisor.client import OpenRouterClient
from manas_os.advisor.context import build_context_pack
from manas_os.advisor.guard import validate_notes

STAGE = "advisor"
SOURCE = "openrouter"
SYSTEM_PROMPT = (
    "You are a second-opinion advisor for a rules-based NSE swing-trading system. "
    "The rules have already decided. For each area give a SHORT opinion: agree / "
    "caution / disagree + why, citing only numbers present in the context. You "
    "cannot change any plan. Output JSON array of notes: {scope: regime|entry|exit|"
    "risk|event, symbol or null, stance: agree|caution|disagree, note: <=2 sentences, "
    "watch_for: <=1 sentence}."
)


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS advisor_notes ("
        "note_date TEXT NOT NULL, scope TEXT NOT NULL, symbol TEXT NOT NULL DEFAULT '', "
        "stance TEXT NOT NULL, note TEXT NOT NULL, watch_for TEXT, model TEXT, "
        "user_action TEXT, outcome_r REAL, created_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (note_date, scope, symbol))"
    )


def run(conn, run_date: str, client: Any | None = None) -> dict[str, Any]:
    started = time.monotonic()
    try:
        ensure_schema(conn)
        if not bool(config.get("advisor.enabled", False)):
            _log(conn, run_date, "skip", 0, started, "advisor disabled")
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "advisor disabled"}
        api_key = config.get("advisor.api_key")
        if not api_key and client is None:
            _log(conn, run_date, "skip", 0, started, "advisor api_key missing")
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "advisor api_key missing"}

        ctx = build_context_pack(conn, run_date)
        prompt = "<context>\n" + json.dumps(ctx, sort_keys=True, default=str) + "\n</context>"
        llm = client or OpenRouterClient(api_key=api_key)
        raw = None
        model = getattr(llm, "model", config.get("advisor.model", "unknown"))
        last_error = None
        for attempt in range(2):
            try:
                raw, model = llm.chat(system=SYSTEM_PROMPT, user=prompt)
                notes, rejected = validate_notes(raw, ctx)
                rows = _persist_notes(conn, run_date, notes, model)
                _log(conn, run_date, "ok", rows, started, f"notes={rows} rejected={len(rejected)}")
                conn.commit()
                return {"status": "ok", "rows": rows, "rejected": rejected}
            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt >= 1:
                    break
            except ValueError as exc:
                last_error = exc
                if attempt >= 1:
                    break
        _log(conn, run_date, "fail", 0, started, f"malformed model JSON: {last_error}")
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(last_error)}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _persist_notes(conn, note_date: str, notes: list[dict[str, Any]], model: str) -> int:
    rows = 0
    for note in notes:
        conn.execute(
            "INSERT INTO advisor_notes (note_date, scope, symbol, stance, note, watch_for, model) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(note_date, scope, symbol) DO UPDATE SET "
            "stance = excluded.stance, note = excluded.note, watch_for = excluded.watch_for, "
            "model = excluded.model, created_at = datetime('now')",
            (
                note_date,
                note["scope"],
                note.get("symbol") or "",
                note["stance"],
                note["note"],
                note.get("watch_for"),
                model,
            ),
        )
        rows += 1
    return rows


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, duration_s, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )

