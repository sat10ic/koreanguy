"""Export per-symbol metric history from the archived nightly reports
(spec §15.5/§15.9/§15.10 — RS trend, accumulation temporal view, deltas).

Reads the last N real tonight_*.json reports and emits, per symbol that
appeared as a candidate: rs_rank, activity_score, delivery_ratio, rvol and
close, by date. Nothing is interpolated — a symbol absent from a session
simply has no point that day.

Output: unidesk_terminal/src/data/metric_history.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
REPORTS = REPO / "data" / "market" / "reports"
OUT = REPO / "unidesk_terminal" / "src" / "data" / "metric_history.json"
SESSIONS_N = 10

if __name__ == "__main__":
    sessions = []
    for p in sorted(REPORTS.glob("tonight_*.json"), reverse=True):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("session_date"):
            sessions.append((raw["session_date"], raw))
        if len(sessions) >= SESSIONS_N:
            break
    sessions.reverse()  # oldest first

    symbols: dict[str, dict] = {}
    for date, raw in sessions:
        for c in raw.get("candidates", []):
            sym = c.get("symbol")
            if not sym:
                continue
            entry = symbols.setdefault(sym, {"rs": [], "act": [], "dlv": [], "rvol": [], "close": []})
            if c.get("rs_rank") is not None:
                entry["rs"].append([date, c["rs_rank"]])
            act = (c.get("activity_score") or {}).get("activity_score")
            if act is not None:
                entry["act"].append([date, act])
            if c.get("delivery_ratio") is not None:
                entry["dlv"].append([date, c["delivery_ratio"]])
            if c.get("rvol") is not None:
                entry["rvol"].append([date, c["rvol"]])
            if c.get("close") is not None:
                entry["close"].append([date, c["close"]])

    payload = {
        "source": "data/market/reports/tonight_*.json (candidate rows)",
        "generator": "unidesk/run_export_metric_history.py",
        "sessions": [d for d, _ in sessions],
        "symbols": symbols,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"[export] {len(symbols)} symbols x up to {len(sessions)} sessions -> {OUT}")
