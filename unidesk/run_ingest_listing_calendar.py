"""IPO listing-calendar ingest: pulls NSE's own official equity master list
(``archives.nseindia.com/content/equities/EQUITY_L.csv`` -- the ``DATE OF
LISTING`` column NSE publishes for every listed symbol) and freezes a
dated, content-hashed, immutable snapshot under
``data/market/reference/listing_calendar/<snapshot_date>/``, then refreshes
the "latest" table at ``data/market/reference/listing_calendar.parquet``
that ``unidesk.momentum.data.listing_calendar.load_listing_calendar()``
reads.

This does NOT touch ``unidesk/momentum/detectors/trust.py``. ``ipo_base``
stays BLOCKED (``listing_age_is_not_verified``) until the owner reviews the
snapshot and decides to wire it in and re-audit -- that trust-status change
is owner-gated (see ``trust.py``'s module docstring), not something an
ingest script should flip on its own.

Idempotent: running twice against identical NSE content produces the same
``content_hash`` and reuses the original ``first_seen_at`` from that
snapshot's manifest (never overwritten to "now" on a re-run). The "latest"
parquet is a full reference-master replace each run, not an append log --
running twice never duplicates rows in it.

If NSE is unreachable, or the response no longer parses to at least one
``(symbol, listing_date)`` row under the expected column names, this stops
and prints why -- it never substitutes a guess (e.g. "first bhavcopy
appearance") for a real listing date.

Usage:
  python unidesk/run_ingest_listing_calendar.py
  python unidesk/run_ingest_listing_calendar.py --dry-run   # fetch+parse only, no writes
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from unidesk.momentum.data.events import parse_ipo_listings
from unidesk.momentum.data.listing_calendar import (
    DEFAULT_LATEST_PARQUET,
    DEFAULT_SNAPSHOT_ROOT,
    NSE_EQUITY_MASTER_URL,
    SOURCE_TIER,
    content_hash,
    fetch_nse_equity_master,
    normalize_nse_equity_master,
    persist_listing_calendar,
    write_normalized_csv,
)


def _existing_first_seen_at(snapshot_dir: Path, content_hash_value: str) -> Optional[str]:
    """If this exact content was already ingested for this snapshot_date,
    reuse its recorded first_seen_at instead of overwriting it to now."""
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("content_hash") == content_hash_value:
        return manifest.get("first_seen_at")
    return None


def run(*, dry_run: bool = False, snapshot_date: Optional[date] = None,
       raw_bytes: Optional[bytes] = None) -> int:
    """``raw_bytes`` lets tests/callers skip the live network fetch while
    exercising the identical parse/hash/persist path."""
    snapshot_date = snapshot_date or date.today()

    if raw_bytes is None:
        print(f"[listing_calendar] fetching {NSE_EQUITY_MASTER_URL}")
        try:
            raw_bytes = fetch_nse_equity_master()
        except Exception as exc:  # noqa: BLE001 -- report plainly, don't fabricate
            print(f"[listing_calendar] FETCH FAILED: {exc!r}")
            print("[listing_calendar] stopping -- not substituting a guessed "
                  "or partial listing calendar.")
            return 1

    norm_rows, norm_stats = normalize_nse_equity_master(raw_bytes)
    if norm_stats["kept"] == 0:
        print("[listing_calendar] SCHEMA MISMATCH: 0 usable (SYMBOL, DATE OF "
              "LISTING) rows found -- NSE's column layout may have changed.")
        print(f"[listing_calendar] raw response head: {raw_bytes[:300]!r}")
        print("[listing_calendar] stopping -- not writing a snapshot from an "
              "unverified schema.")
        return 1

    h = content_hash(raw_bytes)
    snapshot_dir = DEFAULT_SNAPSHOT_ROOT / snapshot_date.isoformat()
    now = datetime.now(timezone.utc).isoformat()
    first_seen_at = _existing_first_seen_at(snapshot_dir, h) or now

    print(f"[listing_calendar] snapshot_date={snapshot_date.isoformat()} "
          f"content_hash={h} rows_normalized={norm_stats['kept']} "
          f"rows_skipped={norm_stats['skipped']}")

    if dry_run:
        print("[listing_calendar] --dry-run: no files written")
        return 0

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "EQUITY_L.csv").write_bytes(raw_bytes)
    normalized_path = write_normalized_csv(norm_rows, snapshot_dir / "ipo_listings_normalized.csv")

    # Reuse events.parse_ipo_listings unchanged (see listing_calendar.py's
    # module docstring) -- then relabel provenance from its Chartsmaze
    # default to this module's NSE-official tier.
    parsed_rows, parsed_stats = parse_ipo_listings(normalized_path)
    for row in parsed_rows:
        row["source_tier"] = SOURCE_TIER
        row["source_file"] = "EQUITY_L.csv"
        row["content_hash"] = h
        row["snapshot_date"] = snapshot_date.isoformat()
        row["first_seen_at"] = first_seen_at

    manifest = {
        "source_url": NSE_EQUITY_MASTER_URL,
        "snapshot_date": snapshot_date.isoformat(),
        "fetched_at": now,
        "first_seen_at": first_seen_at,
        "content_hash": h,
        "raw_bytes": len(raw_bytes),
        "normalized_kept": norm_stats["kept"],
        "normalized_skipped": norm_stats["skipped"],
        "parsed_kept": parsed_stats["kept"],
        "parsed_skipped": parsed_stats["skipped"],
    }
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    out_path = persist_listing_calendar(parsed_rows, DEFAULT_LATEST_PARQUET)

    print(f"[listing_calendar] snapshot dir: {snapshot_dir}")
    print(f"[listing_calendar] first_seen_at={first_seen_at}")
    print(f"[listing_calendar] {parsed_stats['kept']} symbols with a listing "
          f"date -> {out_path} ({parsed_stats['skipped']} rows skipped in "
          f"final parse)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and parse only; write nothing to disk")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
