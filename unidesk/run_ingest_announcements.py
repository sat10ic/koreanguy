"""E-2 ingest — corporate announcements master CSV -> partitioned store.

    .venv-orderflow/Scripts/python.exe unidesk/run_ingest_announcements.py \
        [--source SwingEdge/data/chartsmaze/corporate-announcements-master.csv]

Idempotent: re-ingesting the same master produces the same store (records are
deduped by (symbol, announced_date, subject) at parse time and the partition
write is a full rewrite per date). The store doubles as the Phase 0
availability ledger (gate item #26): every row carries ``first_seen_at``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from unidesk.research.announcements import (  # noqa: E402
    parse_announcements_master_csv, persist_announcements,
)

DEFAULT_SOURCE = REPO_ROOT / "SwingEdge" / "data" / "chartsmaze" / "corporate-announcements-master.csv"
STORE_ROOT = REPO_ROOT / "data" / "reference" / "announcements"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    args = ap.parse_args()
    src = Path(args.source)
    if not src.exists():
        print(f"[announcements] source not found: {src}")
        return 1
    records = parse_announcements_master_csv(src)
    index = persist_announcements(records, STORE_ROOT)
    payload = index.read_text(encoding="utf-8")
    print(f"[announcements] {len(records)} records from {src.name}")
    print(f"[announcements] store -> {STORE_ROOT}")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
