"""Resume driver for directive-1f / N4 label-version regeneration: picks an
archive-wide attach run back up from the exact sessions not yet correctly
persisted under the CURRENT outcome-label schema.

A session counts as done only if its partition exists AND every one of its
events carries ``outcome_labels["label_version"] == OUTCOME_LABELS_VERSION``
(see ``research.archive_attach.sessions_needing_label_refresh``). This is
version-aware, not just presence-aware: a stale partition persisted before
the stop-aware label fix (03778ecd) already has a ``status`` key on every
event, so a mere ``status``-presence check (the original form of this
script) would wrongly treat every stale partition as done and skip it,
defeating regeneration entirely. See
``design/handoffs/HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_COMPLETED.md``
"Still open" #1.

    python unidesk/run_archive_attach_resume.py

After the resume finishes, re-aggregates status/reason counts by reading
EVERY persisted partition back from disk (not from in-memory tallies of
either run), so the final report reflects ground truth regardless of how
many process restarts it took.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402
from unidesk.research.archive_attach import (  # noqa: E402
    archive_sessions, run_archive_attach, sessions_needing_label_refresh,
)
from unidesk.research.event_store import load_events  # noqa: E402

DATA_ROOT = REPO_ROOT / "data" / "market"
BACKLOG = REPO_ROOT / "data" / "bhavcopy"
EVENTS_DIR = DATA_ROOT / "research" / "events"


def find_resume_sessions(store: InMemoryMarketStore) -> list:
    """Version-aware: every eligible session whose partition is either
    missing entirely or carries any event not stamped with the current
    ``OUTCOME_LABELS_VERSION`` gets (re)processed."""
    eligible = archive_sessions(store)
    eligible_iso = {s.isoformat() for s in eligible}
    stale_iso = set(sessions_needing_label_refresh(DATA_ROOT))
    # sessions_needing_label_refresh only walks existing partitions; a
    # session with NO partition at all also needs processing.
    existing_iso = set()
    if EVENTS_DIR.exists():
        existing_iso = {d.name.removeprefix("date=") for d in EVENTS_DIR.iterdir() if d.is_dir()}
    missing_iso = eligible_iso - existing_iso
    needs_iso = (stale_iso | missing_iso) & eligible_iso
    return sorted(date.fromisoformat(iso) for iso in needs_iso)


def aggregate_from_disk() -> dict:
    status_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    total = 0
    partitions = 0
    for part in sorted(EVENTS_DIR.glob("date=*")):
        events = load_events(DATA_ROOT, session=part.name.replace("date=", ""))
        if not events:
            continue
        partitions += 1
        for ev in events:
            total += 1
            status = ev.outcome_labels.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "UNRESOLVED":
                reason = ev.outcome_labels.get("reason", "unknown")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "total_events": total,
        "total_partitions": partitions,
        "status_counts": status_counts,
        "reason_counts": reason_counts,
    }


if __name__ == "__main__":
    t0 = time.time()
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    resume_sessions = find_resume_sessions(store)
    print(f"[resume] {len(resume_sessions)} sessions still need (re)processing: "
          f"{resume_sessions[0] if resume_sessions else None} .. "
          f"{resume_sessions[-1] if resume_sessions else None}", flush=True)

    if resume_sessions:
        result = run_archive_attach(
            backlog=BACKLOG, data_root=DATA_ROOT,
            horizon=10, stop_atr_mult=1.0,
            progress_every=5, store=store,
            only_sessions=resume_sessions,
        )
        print(f"[resume] this pass processed {result['sessions_processed']} sessions, "
              f"{result['total_events']} events", flush=True)

    final = aggregate_from_disk()
    final["wall_clock_seconds_this_pass"] = round(time.time() - t0, 1)
    out_path = DATA_ROOT / "archive_attach_summary.json"
    out_path.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print("\n=== DONE (ground truth from disk) ===")
    print(json.dumps(final, indent=2))
