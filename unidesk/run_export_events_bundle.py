"""E-lane bundle exporter — listing calendar + announcements for the UI.

Writes ``unidesk_terminal/src/data/events_bundle.json`` (a build-time
snapshot, like every bundled domain). The Events screen reads this bundle;
the announcements store stays the source of record.

    .venv-orderflow/Scripts/python.exe unidesk/run_export_events_bundle.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.listing_calendar import load_listing_calendar  # noqa: E402
from dataclasses import asdict

from unidesk.momentum.data.lockin import derive_lockins  # noqa: E402
from unidesk.research.announcements import load_announcements  # noqa: E402

LISTING_PARQUET = REPO_ROOT / "data" / "market" / "reference" / "listing_calendar.parquet"
ANNOUNCEMENTS_ROOT = REPO_ROOT / "data" / "reference" / "announcements"
OUT = REPO_ROOT / "unidesk_terminal" / "src" / "data" / "events_bundle.json"


def main() -> int:
    listings_raw = load_listing_calendar(LISTING_PARQUET)
    listings = {
        sym: {
            "listing_date": d.isoformat(),
            "lockins": [asdict(r) for r in derive_lockins(d)],
        }
        for sym, d in sorted(listings_raw.items())
    }
    announcements = sorted(
        (
            {
                "symbol": r["symbol"],
                "announced_date": r["announced_date"],
                "broadcast_at": r["broadcast_at"],
                "catalyst_type": r["catalyst_type"],
                "subject": r["subject"],
            }
            for r in load_announcements(ANNOUNCEMENTS_ROOT)
        ),
        key=lambda r: r["announced_date"],
        reverse=True,
    )
    payload = {
        "generated_at": datetime_now_iso(),
        "listings": listings,
        "announcements": announcements,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[events-bundle] {len(listings)} listings, {len(announcements)} announcements -> {OUT}")
    return 0


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
