"""Parquet-partitioned research event store (N4 / P7.1 remainder).

Layout::

    <root>/research/events/date=YYYY-MM-DD/events.parquet

One writer: this module. A date partition is replaced as a whole (same-day
re-scan is a rewrite, not an append of mixed config hashes). Nested snapshot
and outcome_labels are stored as JSON strings so the parquet schema stays
stable when detector fields grow.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent

SCHEMA_VERSION = "research-event-v1"
PARTITION_ROOT = ("research", "events")

EVENT_SCHEMA = pa.schema([
    ("event_id", pa.string()),
    ("candidate_id", pa.string()),
    ("symbol", pa.string()),
    ("session", pa.string()),
    ("timestamp", pa.string()),
    ("config_hash", pa.string()),
    ("research_schema_version", pa.string()),
    ("snapshot_json", pa.string()),
    ("outcome_json", pa.string()),
])


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def session_of(event: ResearchEvent) -> str:
    """Partition key: the freeze session, never 'today'."""
    if ":" in event.event_id:
        return event.event_id.rsplit(":", 1)[-1]
    return event.timestamp.date().isoformat()


def partition_dir(root: Path, session: str) -> Path:
    return Path(root).joinpath(*PARTITION_ROOT, f"date={session}")


def partition_file(root: Path, session: str) -> Path:
    return partition_dir(root, session) / "events.parquet"


def encode_event(event: ResearchEvent) -> dict:
    return {
        "event_id": event.event_id,
        "candidate_id": event.candidate_id,
        "symbol": event.symbol,
        "session": session_of(event),
        "timestamp": event.timestamp.isoformat(),
        "config_hash": event.config_hash,
        "research_schema_version": event.research_schema_version,
        "snapshot_json": _json(dict(event.snapshot)),
        "outcome_json": _json(dict(event.outcome_labels)),
    }


def decode_event(row: dict) -> ResearchEvent:
    ts = datetime.fromisoformat(row["timestamp"])
    snapshot = json.loads(row["snapshot_json"])
    outcomes = json.loads(row["outcome_json"] or "{}")
    if not isinstance(snapshot, dict) or not snapshot:
        raise ContractError("snapshot_json must decode to a non-empty object")
    if not isinstance(outcomes, dict):
        raise ContractError("outcome_json must decode to an object")
    return ResearchEvent(
        event_id=row["event_id"],
        candidate_id=row["candidate_id"],
        symbol=row["symbol"],
        timestamp=ts,
        snapshot=snapshot,
        config_hash=row["config_hash"],
        research_schema_version=row["research_schema_version"],
        outcome_labels=outcomes,
    )


def persist_events(events: Sequence[ResearchEvent], root: Path) -> dict:
    """Write events grouped by session. Empty input is a no-op."""
    if not events:
        return {"partitions": 0, "rows": 0, "path": str(Path(root).joinpath(*PARTITION_ROOT))}
    by_session: dict[str, list] = {}
    for event in events:
        by_session.setdefault(session_of(event), []).append(encode_event(event))
    for session, rows in by_session.items():
        path = partition_file(root, session)
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=EVENT_SCHEMA), path)
    return {
        "partitions": len(by_session),
        "rows": len(events),
        "sessions": sorted(by_session),
        "path": str(Path(root).joinpath(*PARTITION_ROOT)),
    }


def load_events(root: Path, *, session: Optional[str] = None) -> list[ResearchEvent]:
    """Read one partition or every date=* partition under the store."""
    base = Path(root).joinpath(*PARTITION_ROOT)
    if session is not None:
        path = partition_file(root, session)
        if not path.exists():
            return []
        rows = pq.read_table(path).to_pylist()
        return [decode_event(r) for r in rows]
    if not base.exists():
        return []
    out: list[ResearchEvent] = []
    for part in sorted(base.glob("date=*")):
        path = part / "events.parquet"
        if path.exists():
            out.extend(decode_event(r) for r in pq.read_table(path).to_pylist())
    return out
