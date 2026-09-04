"""Does a CA-basis change actually move candidate sets? Measure before assuming.

THE QUESTION THIS SETTLES
~2,300 sessions were never attached (the B2-3 backfill). At a full re-scan per session
that is a multi-day job. A tempting shortcut exists, and it is *not* obviously safe:

The current confirmed table is **4 actions on 4 symbols** (AGIIL, ANANDRATHI, ANUHPHR,
BEML). The rejected table carried 55. So ~51 symbols' adjusted series differ between
bases and every other symbol's series is identical.

That invites "re-stamp the partitions containing none of the 51 and skip the re-scan".

**Why that is not provably safe:** ``rs_rank`` is a percentile against the whole
universe. Changing 51 symbols' returns shifts the return distribution, which shifts every
symbol's rank slightly, which can move ``deriveState``, which can move the candidate set.
A partition can therefore change without containing any affected symbol.

It is cheap to TEST, which is what this script does: fully re-scan a sample of stale
partitions on the current basis and diff against what is stored.

  * **Only the hash differs** -> the fast re-stamp path is justified by evidence, and the
    backfill collapses from days to hours.
  * **Candidate sets move** -> a full re-scan is required, and that is now proved rather
    than assumed.

A negative result is a real result. Do not tune the sample until it says what you want.

SCOPE — READ THIS
This script **only measures**. It never writes to the archive and never re-stamps
anything. Acting on the result is a separate, owner-gated decision.

COST
Holds the full store (~4.5 GB today). **Never run beside a live archive-attach job** —
the box has ~1 GB free while one is in flight. Wait for it to finish.

USAGE
    & C:\\Users\\satta\\Downloads\\koreanguy\\.venv-orderflow\\Scripts\\python.exe \\
        unidesk/run_ca_basis_sample_diff.py --sample 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DATA_ROOT = REPO / "data" / "market"
EVENTS_DIR = DATA_ROOT / "research" / "events"
BACKLOG = REPO / "data" / "bhavcopy"

CURRENT_BASIS = "d1b585eb60fd4f82"


def _canonical(rows: list[dict], drop_keys: set[str]) -> str:
    """Order-independent digest of a session's events, ignoring `drop_keys`.

    The basis hash itself is dropped: we are asking whether anything *else* changed.
    """
    out = hashlib.sha256()
    payload = []
    for row in rows:
        pruned = {k: v for k, v in row.items() if k not in drop_keys}
        payload.append(json.dumps(pruned, sort_keys=True, separators=(",", ":"), default=str))
    for line in sorted(payload):
        out.update(line.encode("utf-8"))
        out.update(b"\0")
    return out.hexdigest()[:16]


def _stored_rows(session: str) -> tuple[list[dict], set[str]]:
    import pyarrow.parquet as pq

    table = pq.read_table(EVENTS_DIR / f"date={session}" / "events.parquet")
    cols = table.to_pydict()
    rows, hashes = [], set()
    for i in range(table.num_rows):
        snapshot = json.loads(cols["snapshot_json"][i])
        hashes.add(snapshot.get("ca_table_hash"))
        rows.append({
            "symbol": cols["symbol"][i],
            "session": str(cols["session"][i]),
            "config_hash": cols["config_hash"][i],
            "snapshot": snapshot,
            "outcome": json.loads(cols["outcome_json"][i]) if cols["outcome_json"][i] else None,
        })
    return rows, hashes


def _rescanned_rows(store, session: str) -> list[dict]:
    from unidesk.momentum.scan import scan_universe
    from unidesk.research.candidates import config_hash_for, freeze_scan

    as_of = datetime.combine(date.fromisoformat(session), datetime.min.time(), tzinfo=timezone.utc)
    scan = scan_universe(store, as_of, apply_universe_gates=True)
    events = freeze_scan(scan, config_hash=config_hash_for(scan))
    rows = []
    for event in events:
        d = event.to_dict() if hasattr(event, "to_dict") else dict(event.__dict__)
        rows.append({
            "symbol": d.get("symbol"),
            "session": str(d.get("session")),
            "config_hash": d.get("config_hash"),
            "snapshot": d.get("snapshot"),
            "outcome": d.get("outcome"),
        })
    return rows


def stale_sessions(limit: int) -> list[str]:
    """Evenly spread across the stale range, not the newest N — a clustered sample
    would only prove something about one market regime."""
    import pyarrow.parquet as pq

    stale = []
    for part in sorted(EVENTS_DIR.glob("date=*")):
        table = pq.read_table(part / "events.parquet", columns=["snapshot_json"])
        found = {json.loads(s).get("ca_table_hash") for s in table.column("snapshot_json").to_pylist()}
        if found - {CURRENT_BASIS}:
            stale.append(part.name.removeprefix("date="))
    if not stale or limit >= len(stale):
        return stale
    step = len(stale) / limit
    return [stale[int(i * step)] for i in range(limit)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=10, help="stale partitions to re-scan")
    args = ap.parse_args()

    sessions = stale_sessions(args.sample)
    if not sessions:
        print("[sample-diff] no stale partitions remain -- nothing to test")
        return 0
    print(f"[sample-diff] sampling {len(sessions)} stale partitions: {sessions}")

    from unidesk.momentum.data.bhavcopy import ingest_directory
    from unidesk.momentum.data.market_store import InMemoryMarketStore

    print("[sample-diff] ingesting store (~4.5 GB, several minutes) ...", flush=True)
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)

    identical, moved, failed = [], [], []
    for session in sessions:
        try:
            stored, stored_hashes = _stored_rows(session)
            rescanned = _rescanned_rows(store, session)
        except Exception as exc:  # noqa: BLE001 - report, never silently pass
            failed.append((session, repr(exc)))
            print(f"  {session}: FAILED {exc!r}", flush=True)
            continue

        drop = {"ca_table_hash"}
        a = _canonical([r["snapshot"] for r in stored], drop)
        b = _canonical([r["snapshot"] for r in rescanned], drop)
        same_symbols = {r["symbol"] for r in stored} == {r["symbol"] for r in rescanned}
        verdict = "IDENTICAL" if (a == b and same_symbols) else "MOVED"
        (identical if verdict == "IDENTICAL" else moved).append(session)
        print(f"  {session}: {verdict}  stored={len(stored)} rescanned={len(rescanned)} "
              f"basis={sorted(stored_hashes)}", flush=True)

    print("\n[sample-diff] RESULT")
    print(f"  identical apart from the basis stamp : {len(identical)}")
    print(f"  candidate content moved              : {len(moved)}")
    print(f"  failed                               : {len(failed)}")
    if moved:
        print("\n  VERDICT: a CA-basis change DOES move candidate content. The backfill "
              "requires a full re-scan. Re-stamping would corrupt the archive.")
    elif identical and not failed:
        print("\n  VERDICT: no content moved in this sample. A fast re-stamp path is "
              "SUPPORTED BY EVIDENCE -- but this is a sample, not a proof. Widen it "
              "before acting, and treat the decision as owner-gated.")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
