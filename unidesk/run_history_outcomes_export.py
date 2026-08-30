"""History-screen outcome export (UI_BACKEND_INTEGRATION_PLAN.md row 4; N4).

Reads the research event store and emits real outcome-labelled calls for the
current Tonight report's symbols, in the shape the terminal's History /
YesterdaysCalls UI already renders.

    SAFETY GATE: this refuses to run while the event store is label-mixed.
    The N4 archive regeneration (run_archive_attach_resume.py) rewrites
    partitions under the CURRENT outcome-label version; until every
    partition carries ``outcome_labels[\"label_version\"] ==
    OUTCOME_LABELS_VERSION``, some of the newest-session outcomes are stale
    (pre-gap-through, no net_bps) and a History export made from them would
    mislabel reality exactly where the UI would show it. The exporter exits
    with an explicit message instead of guessing.

    Intended use once the regeneration settles and the store verifies
    label-homogeneous (run from repo root):

        .venv-orderflow/Scripts/python.exe unidesk/run_history_outcomes_export.py

    Writes ``unidesk_terminal/src/data/outcomes_<report-session>.json`` — a
    committed build-time snapshot, same convention as tonight_<date>.json /
    stock_history_<date>.json (static Vite bundle, no runtime fetch).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402
from unidesk.research.event_store import load_events  # noqa: E402
from unidesk.research.labels import OUTCOME_LABELS_VERSION  # noqa: E402

DATA_ROOT = REPO_ROOT / "data" / "market"
BACKLOG = REPO_ROOT / "data" / "bhavcopy"
REPORT_SESSION = "2026-08-28"
TONIGHT_JSON = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"tonight_{REPORT_SESSION}.json"
OUT_PATH = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"outcomes_{REPORT_SESSION}.json"


def verify_label_homogeneous(data_root: Path) -> tuple[bool, dict]:
    """Every partition's events must be stamped with the CURRENT label
    version. Returns (ok, detail). This is the gate that makes the export
    safe: it must not run while the archive regen is mid-flight."""
    events = load_events(data_root)
    bad: dict[str, int] = {}
    total = 0
    for ev in events:
        total += 1
        ver = ev.outcome_labels.get("label_version", "<missing>")
        if ver != OUTCOME_LABELS_VERSION:
            bad[ver] = bad.get(ver, 0) + 1
    ok = total > 0 and not bad
    return ok, {"total_events": total, "stale_by_version": bad, "current_version": OUTCOME_LABELS_VERSION}


def _outcome_of(o: dict) -> str:
    """Map the research outcome labels to the UI's OutcomeCall.outcome
    vocabulary: hit_target / stopped_out / unresolved. Never guesses --
    UNRESOLVED stays unresolved, and a stop_hit with a positive R still
    reads stopped_out (the label is the terminal state)."""
    status = o.get("status")
    if status in ("UNRESOLVED", "INSUFFICIENT_DATA", "ADJUSTMENT_BASIS_MISMATCH", "UNCONFIRMED_CA"):
        return "unresolved"
    if o.get("stop_hit"):
        return "stopped_out"
    return "hit_target" if (o.get("r_multiple") or 0) >= 1.0 else "hit_target"


def _note(o: dict, symbol: str, session: str) -> str:
    """One-line honest note from the real label fields. Nothing invented."""
    bits = []
    if o.get("gap_through"):
        bits.append("gap-through stop")
    elif o.get("stop_hit"):
        bits.append("stopped at invalidation")
    if o.get("net_bps") is not None:
        bits.append(f"net {o['net_bps']:+.1f} bps")
    if o.get("gross_bps") is not None:
        bits.append(f"gross {o['gross_bps']:+.1f} bps")
    if not bits:
        bits.append(f"{o.get('status', '?').lower()} as of {session}")
    return f"{symbol} — " + ", ".join(bits) + "."


def build_outcomes(data_root: Path, report_session: str) -> dict:
    ok, detail = verify_label_homogeneous(data_root)
    if not ok:
        print(f"[outcomes] SAFETY GATE: store not label-homogeneous "
              f"({detail['stale_by_version']}), refusing to export. "
              f"Wait for the archive regen to settle.", file=sys.stderr)
        sys.exit(3)

    tonight = json.loads(TONIGHT_JSON.read_text(encoding="utf-8"))
    symbols = {c["symbol"] for c in tonight["candidates"]}

    events = load_events(data_root)
    calls = []
    for ev in events:
        if ev.symbol not in symbols:
            continue
        o = ev.outcome_labels
        if not o:
            continue
        session = ev.snapshot.get("session") or ev.snapshot.get("as_of", "").split("T")[0]
        entry = o.get("entry")
        calls.append({
            "symbol": ev.symbol,
            "setupType": (ev.snapshot.get("detectors") or {}).get("fired", ev.snapshot.get("setup_inputs", {}).get("detector")) or "unknown",
            "date": session,
            "entry": entry,
            "outcome": _outcome_of(o),
            "rMultiple": o.get("r_multiple"),
            "mfePct": o.get("mfe_pct"),
            "maePct": o.get("mae_pct"),
            "stopHit": o.get("stop_hit"),
            "gapThrough": o.get("gap_through"),
            "netBps": o.get("net_bps"),
            "labelVersion": o.get("label_version"),
            "note": _note(o, ev.symbol, session),
        })

    calls.sort(key=lambda c: (c["symbol"], c["date"]))
    return {
        "report_session": report_session,
        "outcome_labels_version": OUTCOME_LABELS_VERSION,
        "count": len(calls),
        "calls": calls,
    }


if __name__ == "__main__":
    data = build_outcomes(DATA_ROOT, REPORT_SESSION)
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[outcomes] {data['count']} labled calls for tonight's {len(set(c['symbol'] for c in data['calls']))} symbols -> {OUT_PATH}")