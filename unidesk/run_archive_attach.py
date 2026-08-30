"""One-off driver invocation for directive-1f (archive-wide outcome attach).
Not part of the package import surface; run directly:

    python unidesk/run_archive_attach.py

Writes progress to stdout and a final JSON summary to
data/market/archive_attach_summary.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.research.archive_attach import run_archive_attach  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    result = run_archive_attach(
        backlog=REPO_ROOT / "data" / "bhavcopy",
        data_root=REPO_ROOT / "data" / "market",
        horizon=10,
        stop_atr_mult=1.0,
        session_step=1,
        progress_every=5,
    )
    result["wall_clock_seconds"] = round(time.time() - t0, 1)
    out_path = REPO_ROOT / "data" / "market" / "archive_attach_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("\n=== DONE ===")
    print(json.dumps(result, indent=2))
