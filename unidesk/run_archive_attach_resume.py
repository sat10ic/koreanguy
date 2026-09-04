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


def find_resume_sessions(store: InMemoryMarketStore, *, existing_partitions_only: bool = False) -> list:
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
    if existing_partitions_only:
        # B2-3 scope flag: only sessions that ALREADY have a partition (the
        # wrong-basis + label-pending remediation the handoff measures). The
        # never-attached backfill (~2,300 sessions) is a separate, explicitly
        # run pass -- processing it changes the archive's coverage shape
        # (Research and History denominators), which is an owner decision,
        # not a side effect of a remediation.
        needs_iso &= existing_iso
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


def _corpus_fingerprint() -> tuple:
    """What identifies an ingest as 'the same data': file count + sizes +
    newest mtime in data/bhavcopy, plus the confirmed-actions table hash.
    A snapshot is only reused when EVERYTHING matches."""
    from unidesk.momentum.data.corp_actions import confirmed_actions_content_hash
    from unidesk.momentum.data.store_fingerprint import store_source_hash

    files = sorted(BACKLOG.glob("*.csv"))
    total_size = sum(f.stat().st_size for f in files)
    newest_mtime = max((f.stat().st_mtime for f in files), default=0)
    return (
        len(files), total_size, round(newest_mtime, 0),
        confirmed_actions_content_hash(),
        store_source_hash(),
    )

SNAPSHOT = DATA_ROOT / "store_snapshot.pkl"


def _load_or_ingest_store() -> InMemoryMarketStore:
    """4b: the full ingest (~1M bars, 4,035 CSVs) produces byte-identical
    state for an identical corpus — so pay for it once, then load the
    snapshot in seconds on every restart. A fingerprint mismatch (new
    bhavcopy file, changed confirmed table, format change) silently falls
    back to the real ingest and overwrites the snapshot."""
    import pickle

    fp = _corpus_fingerprint()
    sidecar = SNAPSHOT.with_suffix(".fingerprint.json")
    if SNAPSHOT.exists() and sidecar.exists():
        try:
            if json.loads(sidecar.read_text(encoding="utf-8"))["fingerprint"] == list(fp):
                print("[resume] loading ingested store snapshot ...", flush=True)
                with open(SNAPSHOT, "rb") as fh:
                    store = pickle.load(fh)
                print("[resume] snapshot loaded.", flush=True)
                return store
        except Exception as exc:  # noqa: BLE001 — a bad snapshot is just a slow start
            print(f"[resume] snapshot unusable ({exc}); re-ingesting", flush=True)
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    try:
        print("[resume] saving store snapshot for fast restarts ...", flush=True)
        with open(SNAPSHOT, "wb") as fh:
            pickle.dump(store, fh, protocol=5)
        sidecar.write_text(json.dumps({"fingerprint": list(fp)}), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — no snapshot is never a failure
        print(f"[resume] snapshot save skipped ({exc})", flush=True)
    return store


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stale-partitions-only", action="store_true",
        help="process ONLY sessions whose existing partition is stale or "
             "label-pending; skip the never-attached backfill (B2-3 scope)",
    )
    ap.add_argument(
        "--fresh-ingest", action="store_true",
        help="ignore any stored snapshot and re-ingest from the CSV corpus",
    )
    args = ap.parse_args()

    t0 = time.time()
    if args.fresh_ingest:
        store = InMemoryMarketStore()
        ingest_directory(store, BACKLOG)
    else:
        store = _load_or_ingest_store()
    resume_sessions = find_resume_sessions(
        store, existing_partitions_only=args.stale_partitions_only,
    )
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
