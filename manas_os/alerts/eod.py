"""P3 end-of-day alerts derived from persisted scanner and watchlist state."""
from __future__ import annotations

from typing import Any
import json
import time

from manas_os.engine import price_action
from manas_os.scanner import candidates as scanner_candidates

STAGE = "eod_alerts"
SOURCE = "scan_candidates+watchlist"


def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS alert_log ("
        "alert_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "alert_date TEXT NOT NULL, symbol TEXT, alert_type TEXT NOT NULL, "
        "severity TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL, "
        "evidence_json TEXT, source_key TEXT, created_at TEXT DEFAULT (datetime('now')), "
        "UNIQUE(alert_date, symbol, alert_type, title))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_log_date ON alert_log(alert_date)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS alert_state ("
        "symbol TEXT PRIMARY KEY, last_alert_date TEXT, last_alert_type TEXT, "
        "last_detail TEXT, updated_at TEXT DEFAULT (datetime('now')))"
    )


def _latest_mode(conn, on_or_before: str) -> str | None:
    row = conn.execute(
        "SELECT market_mode FROM regime_snapshots WHERE snapshot_date <= ? "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (on_or_before,),
    ).fetchone()
    return row["market_mode"] if row else None


def _candidate_alerts(conn, run_date: str, limit: int = 12) -> tuple[str | None, list[dict[str, Any]]]:
    payload = scanner_candidates.load_persisted_candidates(
        conn,
        run_date,
        min_grade="B",
        limit=limit,
    )
    if not payload["available"]:
        return None, []
    mode = _latest_mode(conn, run_date) or "UNKNOWN"
    alerts = []
    for c in payload["candidates"]:
        severity = "info"
        if c.get("grade") in {"A", "A+"} and mode in {"RISK_ON", "SELECTIVE"}:
            severity = "action"
        if mode in {"NO_TRADE", "DEFENSIVE"}:
            severity = "blocked"
        alerts.append({
            "alert_date": payload["as_of"],
            "symbol": c["symbol"],
            "alert_type": "SETUP_READY",
            "severity": severity,
            "title": f"{c['grade']} {c['setup']} on {c['symbol']}",
            "detail": (
                f"{c['symbol']} has {c['setup']} readiness {c['readiness']}/100. "
                f"Regime is {mode}; use the regime risk cap. {c.get('read') or ''}"
            ).strip(),
            "evidence": c.get("evidence") or [],
            "source_key": "scan_candidates",
        })
    return payload["as_of"], alerts


def _watchlist_alerts(conn, run_date: str) -> tuple[str | None, list[dict[str, Any]]]:
    rows = conn.execute("SELECT symbol FROM watchlist WHERE alerts_enabled = 1 ORDER BY symbol").fetchall()
    price_date = scanner_candidates.latest_price_date(conn, run_date)
    if not rows or price_date is None:
        return price_date, []
    alerts = []
    for row in rows:
        state = price_action.signals_for_symbol(conn, row["symbol"], price_date, max_bars=260)
        trail = state.get("trail") or {}
        if trail.get("status") in {"TRAIL_HIT_FAST", "TRAIL_HIT_SLOW"}:
            severity = "warning" if trail["status"] == "TRAIL_HIT_FAST" else "critical"
            alerts.append({
                "alert_date": price_date,
                "symbol": row["symbol"],
                "alert_type": trail["status"],
                "severity": severity,
                "title": f"{row['symbol']} {trail['status'].replace('_', ' ').lower()}",
                "detail": trail.get("detail") or "Trailing stop status changed.",
                "evidence": [{"filter": trail["status"], "value": trail.get("detail")}],
                "source_key": "watchlist_trail",
            })
    return price_date, alerts


def generate_alerts(conn, run_date: str) -> dict[str, Any]:
    candidate_date, candidate_alerts = _candidate_alerts(conn, run_date)
    watch_date, watch_alerts = _watchlist_alerts(conn, run_date)
    alert_date = candidate_date or watch_date or scanner_candidates.latest_price_date(conn, run_date) or run_date
    alerts = candidate_alerts + watch_alerts
    return {"alert_date": alert_date, "alerts": alerts}


def persist_alerts(conn, alert_date: str, alerts: list[dict[str, Any]]) -> int:
    ensure_schema(conn)
    conn.execute("DELETE FROM alert_log WHERE alert_date = ?", (alert_date,))
    for alert in alerts:
        conn.execute(
            "INSERT INTO alert_log (alert_date, symbol, alert_type, severity, title, detail, "
            "evidence_json, source_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                alert_date,
                alert.get("symbol"),
                alert["alert_type"],
                alert["severity"],
                alert["title"],
                alert["detail"],
                json.dumps(alert.get("evidence") or []),
                alert.get("source_key"),
            ),
        )
        if alert.get("symbol"):
            conn.execute(
                "INSERT INTO alert_state (symbol, last_alert_date, last_alert_type, last_detail, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(symbol) DO UPDATE SET "
                "last_alert_date=excluded.last_alert_date, last_alert_type=excluded.last_alert_type, "
                "last_detail=excluded.last_detail, updated_at=excluded.updated_at",
                (alert["symbol"], alert_date, alert["alert_type"], alert["detail"]),
            )
    return len(alerts)


def load_alerts(conn, on_or_before: str, limit: int = 50) -> dict[str, Any]:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT MAX(alert_date) AS d FROM alert_log WHERE alert_date <= ?",
        (on_or_before,),
    ).fetchone()
    if not row or not row["d"]:
        return {"available": False, "as_of": None, "alerts": []}
    alert_date = row["d"]
    rows = conn.execute(
        "SELECT alert_id, alert_date, symbol, alert_type, severity, title, detail, "
        "evidence_json, source_key, created_at FROM alert_log "
        "WHERE alert_date = ? ORDER BY "
        "CASE severity WHEN 'critical' THEN 0 WHEN 'action' THEN 1 WHEN 'warning' THEN 2 "
        "WHEN 'blocked' THEN 3 ELSE 4 END, alert_id LIMIT ?",
        (alert_date, limit),
    ).fetchall()
    alerts = []
    for row in rows:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json") or "[]")
        alerts.append(item)
    return {"available": True, "as_of": alert_date, "alerts": alerts}


def run(conn, run_date: str) -> dict[str, Any]:
    """Generate persisted EOD alerts. Never raises; always logs pipeline_runs."""
    started = time.monotonic()
    try:
        result = generate_alerts(conn, run_date)
        rows = persist_alerts(conn, result["alert_date"], result["alerts"])
        detail = f"alert_date={result['alert_date']} alerts={rows}"
        _log(conn, run_date, "ok", rows, started, detail)
        conn.commit()
        return {"status": "ok", "rows": rows, "as_of": result["alert_date"]}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _log(conn, run_date: str, status: str, rows: int, started: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )
