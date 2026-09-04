"""Run the bhavcopy downloader to backfill history + catch up to today.

Wraps bhavcopy_extractor/download_bhavcopy.py's tilak999/NSE-Data-bank source.
Downloads ALL available trading days. Skips existing files.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bhavcopy_extractor"))

from download_bhavcopy import download_bhavcopy_from_nse_databank

TARGET = REPO / "data" / "bhavcopy"
LOG = REPO / "data" / "market" / "reports" / "bhavcopy_backfill.log"

if __name__ == "__main__":
    import time
    t0 = time.time()
    print(f"[bhavcopy-backfill] starting download to {TARGET}", flush=True)
    print(f"[bhavcopy-backfill] source: tilak999/NSE-Data-bank (GitHub)", flush=True)

    d, s, f = download_bhavcopy_from_nse_databank(str(TARGET), days=9999)

    elapsed = round(time.time() - t0, 1)
    msg = f"downloaded={d}, skipped={s}, failed={f}, elapsed={elapsed}s"
    print(f"[bhavcopy-backfill] {msg}", flush=True)

    existing = len(list(TARGET.glob("*.csv")))
    print(f"[bhavcopy-backfill] total files now: {existing}", flush=True)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(msg + f"\ntotal_files={existing}\n", encoding="utf-8")