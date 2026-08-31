"""History-screen outcome export (UI_BACKEND_INTEGRATION_PLAN.md row 4; N4).

Reads the research event store and emits real outcome-labelled calls for the
current Tonight report's symbols, in the shape the terminal's History /
YesterdaysCalls UI already renders.

    SAFETY GATE: this refuses to run while the event store is label-mixed.
    Uses a fast probe (first 5 rows per partition) rather than loading all
    864k events.

    Intended use once the regeneration settles and the store verifies
    label-homogeneous (run from repo root):

        .venv-orderflow/Scripts/python.exe unidesk/run_history_outcomes_export.py

    Writes outcomes_<report-session>.json -- committed build-time snapshot.
"""
from __future__ import annotations

import json
import sys

import pyarrow.parquet as pq
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.research.labels import OUTCOME_LABELS_VERSION

DATA_ROOT = REPO_ROOT / "data" / "market"
REPORT_SESSION = "2026-08-28"
TONIGHT_JSON = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"tonight_{REPORT_SESSION}.json"
OUT_PATH = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"outcomes_{REPORT_SESSION}.json"
EVENTS_DIR = DATA_ROOT / "research" / "events"


def _fast_probe() -> tuple[bool, dict]:
    total = 0
    versions: dict[str, int] = {}
    for p in sorted(EVENTS_DIR.glob("date=*")):
        f = p / "events.parquet"
        if not f.exists():
            continue
        table = pq.ParquetFile(f).read_row_group(0, columns=["outcome_json"])
        for row in table.slice(length=5).to_pylist():
            v = json.loads(row["outcome_json"] or "{}").get("label_version", "<missing>")
            versions[v] = versions.get(v, 0) + 1
            total += 1
    bad = {v: n for v, n in versions.items() if v != OUTCOME_LABELS_VERSION}
    return (total > 0 and not bad), {"sampled": total, "stale": bad, "version": OUTCOME_LABELS_VERSION}


def _outcome_of(o: dict) -> str:
    s = o.get("status")
    if s in ("UNRESOLVED", "INSUFFICIENT_DATA", "ADJUSTMENT_BASIS_MISMATCH", "UNCONFIRMED_CA"):
        return "unresolved"
    return "stopped_out" if o.get("stop_hit") else "hit_target"


def _note(o: dict, sym: str, session: str) -> str:
    bits = []
    if o.get("gap_through"):
        bits.append("gap-through stop")
    elif o.get("stop_hit"):
        bits.append("stopped at invalidation")
    if o.get("net_bps") is not None:
        bits.append(f"net {o['net_bps']:+.1f} bps")
    if not bits:
        bits.append(f"{o.get('status', '?').lower()} as of {session}")
    return f"{sym} -- " + ", ".join(bits) + "."


def _setup_type(snap: dict) -> str | None:
    for n, d in (snap.get("detectors") or {}).items():
        if isinstance(d, dict) and d.get("detection") == "VALID":
            return n
    return None


def build_outcomes() -> dict:
    ok, detail = _fast_probe()
    if not ok:
        print(f"[outcomes] SAFETY GATE: store not homogeneous {detail}", file=sys.stderr)
        sys.exit(3)
    tonight = json.loads(TONIGHT_JSON.read_text(encoding="utf-8"))
    symbols = list({c["symbol"] for c in tonight["candidates"]})
    calls = []
    for p in sorted(EVENTS_DIR.glob("date=*")):
        f = p / "events.parquet"
        if not f.exists():
            continue
        tab = pq.read_table(f, columns=["symbol", "snapshot_json", "outcome_json"],
                           filters=[("symbol", "in", symbols)])
        if tab.num_rows == 0:
            continue
        for row in tab.to_pylist():
            o = json.loads(row["outcome_json"] or "{}")
            if not o:
                continue
            st = _setup_type(json.loads(row["snapshot_json"] or "{}"))
            if st is None:
                continue
            session = p.name.replace("date=", "")
            calls.append({
                "symbol": row["symbol"], "setupType": st, "date": session,
                "entry": o.get("entry"), "outcome": _outcome_of(o),
                "rMultiple": o.get("r_multiple"),
                "mfePct": o.get("mfe_pct"), "maePct": o.get("mae_pct"),
                "stopHit": o.get("stop_hit"), "gapThrough": o.get("gap_through"),
                "netBps": o.get("net_bps"), "labelVersion": o.get("label_version"),
                "note": _note(o, row["symbol"], session),
            })
    calls.sort(key=lambda c: (c["symbol"], c["date"]))
    return {
        "report_session": REPORT_SESSION,
        "outcome_labels_version": OUTCOME_LABELS_VERSION,
        "count": len(calls),
        "symbols_with_calls": len(set(c["symbol"] for c in calls)),
        "symbols_sought": len(symbols),
        "calls": calls,
    }


if __name__ == "__main__":
    data = build_outcomes()
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[outcomes] {data['count']} calls for {data['symbols_with_calls']}/{data['symbols_sought']} symbols -> {OUT_PATH}")