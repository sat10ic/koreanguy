"""Byte-identical store equivalence — the gate for B2-3 task 4c, and 4b's missing proof.

WHY THIS EXISTS
Task 4c replaces ``InMemoryMarketStore``'s per-bar Python objects with contiguous arrays
(~4.5 GB live -> ~1-1.5 GB). That is the only change that addresses the binding RAM
constraint, and it rewrites the substrate every label in the archive is computed from.

Without a byte-identical proof you cannot tell a store bug from a data change. A label
that moves after the refactor is then unattributable, and every downstream experiment
inherits the ambiguity.

THE CONTRACT
For one session, two differently-built stores over the same corpus must produce
**identical frozen events** — not "close", not "same count". Same bytes.

WHAT THIS TESTS TODAY
Task 4b already ships a pickled store snapshot with nothing asserting the snapshot
reproduces the ingest. The same harness proves it: ``fresh ingest`` vs ``snapshot load``
must be byte-identical. That test is live now and closes a real gap.

WHEN 4c LANDS
Add the columnar builder to ``_BUILDERS`` and ``test_builders_agree`` gates the refactor
with no further work.

COST — READ BEFORE RUNNING
Each builder holds the full store (~4.5 GB today). These tests are OFF by default and
must never run beside a live remediation job; the box has ~1 GB free while one is in
flight. Enable deliberately:

    $env:UNIDESK_HEAVY_TESTS = "1"
    & C:\\Users\\satta\\Downloads\\koreanguy\\.venv-orderflow\\Scripts\\python.exe -m pytest unidesk/tests/test_store_equivalence.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BACKLOG = REPO / "data" / "bhavcopy"

HEAVY = os.environ.get("UNIDESK_HEAVY_TESTS") == "1"
heavy_only = pytest.mark.skipif(
    not HEAVY,
    reason="holds the full ~4.5 GB store; set UNIDESK_HEAVY_TESTS=1 and only when no "
           "archive-attach run is in flight",
)


def _fresh_ingest():
    from unidesk.momentum.data.bhavcopy import ingest_directory
    from unidesk.momentum.data.market_store import InMemoryMarketStore

    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    return store


def _snapshot_load():
    """Load the 4b pickle. Skips (never fails) when no snapshot exists yet."""
    import pickle

    snapshot = REPO / "data" / "market" / "store_snapshot.pkl"
    if not snapshot.exists():
        pytest.skip(f"no store snapshot at {snapshot} - run the resume driver once")
    with open(snapshot, "rb") as fh:
        return pickle.load(fh)


_BUILDERS = {
    "fresh_ingest": _fresh_ingest,
    "snapshot_load": _snapshot_load,
    # 4c: add "columnar": _columnar_ingest here. No other change is needed --
    # test_builders_agree picks it up and gates the refactor automatically.
}


def canonical_session_digest(store, session: date) -> tuple[str, int]:
    """Deterministic digest of one session's frozen events.

    Canonicalised with sorted keys and no whitespace so the digest reflects *content*,
    not dict ordering or serialiser incidentals. Returns (digest, event_count) — the
    count is reported alongside so a mismatch says whether events moved or merely
    changed.
    """
    from unidesk.momentum.scan import scan_universe
    from unidesk.research.candidates import config_hash_for, freeze_scan

    as_of = datetime.combine(session, datetime.min.time(), tzinfo=timezone.utc)
    scan = scan_universe(store, as_of, apply_universe_gates=True)
    events = freeze_scan(scan, config_hash=config_hash_for(scan))

    digest = hashlib.sha256()
    rows = []
    for event in events:
        row = event.to_dict() if hasattr(event, "to_dict") else event.__dict__
        rows.append(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str))
    for row in sorted(rows):
        digest.update(row.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest(), len(rows)


def _probe_session() -> date:
    """A recent session with a persisted partition, so the run is representative."""
    events_dir = REPO / "data" / "market" / "research" / "events"
    parts = sorted(d.name.removeprefix("date=") for d in events_dir.glob("date=*") if d.is_dir())
    if not parts:
        pytest.skip("no persisted partitions to pick a probe session from")
    return date.fromisoformat(parts[-1])


@heavy_only
def test_builders_agree():
    """Every store builder must produce byte-identical events for the same session."""
    session = _probe_session()
    results = {name: canonical_session_digest(build(), session)
               for name, build in _BUILDERS.items()}

    digests = {digest for digest, _ in results.values()}
    assert len(digests) == 1, (
        "store builders disagree on session "
        f"{session}: {json.dumps({k: {'digest': v[0], 'events': v[1]} for k, v in results.items()}, indent=2)}\n"
        "A differing digest means the substrate changed the data. Do NOT accept a "
        "refactor in this state -- every label computed afterwards would be "
        "unattributable."
    )


@heavy_only
def test_digest_is_deterministic():
    """The digest itself must be stable, or a mismatch above proves nothing."""
    session = _probe_session()
    store = _fresh_ingest()
    first = canonical_session_digest(store, session)
    second = canonical_session_digest(store, session)
    assert first == second, (
        "canonical_session_digest is not deterministic on one store; the equivalence "
        "test cannot be trusted until this is fixed"
    )


def test_source_fingerprint_changes_with_source():
    """4b hardening: the snapshot guard must key on code, not a hand-bumped string.

    Cheap, no store required, always runs.
    """
    from unidesk.contracts.base import ContractError
    from unidesk.momentum.data.store_fingerprint import snapshot_modules, store_source_hash

    baseline = store_source_hash()
    assert len(baseline) == 16
    assert store_source_hash() == baseline, "fingerprint must be stable for identical source"

    widened = store_source_hash(list(snapshot_modules()) + ["unidesk.momentum.scan"])
    assert widened != baseline, "fingerprint must change when the covered source changes"

    with pytest.raises(ContractError):
        store_source_hash(["unidesk.this_module_does_not_exist"])
