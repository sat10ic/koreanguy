"""Regenerate the two UI-bundled nightly reports (2026-08-28, 2026-08-31)
with the CURRENT pipeline: B-01 liveness-filtered RS universe + per-symbol
liveness detail, B-02 symbol-grain dedupe, B-03 numeric history depth +
universe_symbols, B-07 prior-session comparison fields, and the real R0
regime classifier.

Uses ``momentum.nightly.run_nightly`` -- the production entry point -- so
each file is exactly what the nightly would emit for that session (same
ingest, same gates, same regime-state handling, same event freeze).

The full archive regen (run_regen_full.py) may run concurrently: it walks
sessions oldest-first and rewrites the same event partitions hours later
with identical code, so there is no divergence -- only redundant work on
the last two partitions.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.momentum.nightly import run_nightly

IST = timezone(timedelta(hours=5, minutes=30))

if __name__ == "__main__":
    for day in ("2026-08-28", "2026-08-31"):
        as_of = datetime.fromisoformat(day).replace(hour=18, minute=0, tzinfo=IST)
        print(f"[regen-ui-reports] nightly pipeline as of {day} 18:00 IST", flush=True)
        out = run_nightly(
            data_root=REPO / "data" / "market",
            backlog=REPO / "data" / "bhavcopy",
            reports_dir=REPO / "data" / "market" / "reports",
            download_days=0,
            as_of=as_of,
        )
        print(f"[regen-ui-reports] wrote {out}", flush=True)
