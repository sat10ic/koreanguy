"""ROTATION R-0.1 — canonicalise the index store: one row per
(session, index_id), legacy MANAS name spellings normalised, tier duplicates
dropped (NSE_ARCHIVES preferred). Idempotent — run any time; the invariant
assertion fails loudly if the store cannot be made unique.

    .venv-orderflow/Scripts/python.exe unidesk/run_canonicalise_indices.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.momentum.data.indices import (  # noqa: E402
    canonicalise_index_rows, load_index_rows, persist_index_rows,
)

INDEX_PATH = REPO / "data" / "market" / "reference" / "indices.parquet"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = load_index_rows(INDEX_PATH)
    out, stats = canonicalise_index_rows(rows)
    print(f"[indices] {stats}")
    by_id: dict = {}
    for row in out:
        by_id.setdefault(row["index_id"], set()).add(row["session"])
    print(f"[indices] canonical indices: {len(by_id)}")
    for index_id, sessions in sorted(by_id.items()):
        depth = min(sessions), max(sessions)
        print(f"  {index_id:24} {len(sessions):4d} sessions  {depth[0]} -> {depth[1]}")
    if args.dry_run:
        print("[indices] dry-run: store not written")
        return 0
    persist_index_rows(out, INDEX_PATH)
    print(f"[indices] wrote {len(out)} canonical rows -> {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
