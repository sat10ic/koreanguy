"""Backfill historical bhavcopy from 2016 to 2024-09-02 using the existing
downloader (tilak999/NSE-Data-bank GitHub repo).

The D15 archive (`data/bhavcopy/`) currently has 503 files from 2024-09-02
→ 2026-08-28. The gap is 2016-01-01 → 2024-09-01 (~8.5 years of data).

Uses the existing `bhavcopy_extractor/download_bhavcopy.py` which fetches
from `tilak999/NSE-Data-bank` (sec_bhavdata_full_*.csv format). The
downloader already skips existing files, so it's safe to run.

After download, the nightly pipeline's ingest_directory will automatically
pick up the new files (the parser handles both cm and sec_bhavdata formats).

    .venv-orderflow/Scripts/python.exe unidesk/run_backfill_bhavcopy.py --dry-run
    .venv-orderflow/Scripts/python.exe unidesk/run_backfill_bhavcopy.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOWNLOADER = REPO / "bhavcopy_extractor" / "download_bhavcopy.py"
# Target the repo's own D15 archive, not the extractor's stale copy
TARGET_DIR = REPO / "data" / "bhavcopy"


def main():
    import argparse
    p = argparse.ArgumentParser(description="Backfill historical bhavcopy from 2016")
    p.add_argument("--dry-run", action="store_true", help="Print what would be done without downloading")
    p.add_argument("--source", default="tilak", choices=["tilak", "girish", "both"],
                   help="GitHub source (default: tilak999/NSE-Data-bank)")
    args = p.parse_args()

    # Count existing files
    existing = list(TARGET_DIR.glob("*.csv"))
    # Find earliest date to estimate gap
    oldest = min(f.name for f in existing) if existing else "unknown"
    newest = max(f.name for f in existing) if existing else "unknown"
    print(f"[bhavcopy-backfill] {len(existing)} files in {TARGET_DIR}", flush=True)
    print(f"[bhavcopy-backfill] current range: {oldest} .. {newest}", flush=True)
    print(f"[bhavcopy-backfill] gap: ~2016-01-01 to 2024-09-01 (~8.5 years)", flush=True)
    print(f"[bhavcopy-backfill] source: {args.source} (NSE-Data-bank GitHub)", flush=True)

    if args.dry_run:
        print(f"[bhavcopy-backfill] DRY-RUN: would run downloader with --all --source {args.source}", flush=True)
        print(f"[bhavcopy-backfill] target dir: {TARGET_DIR}", flush=True)
        return 0

    print(f"[bhavcopy-backfill] starting download via {DOWNLOADER.name}", flush=True)
    print(f"[bhavcopy-backfill] this may take a while (3000+ files over network)", flush=True)

    result = subprocess.run(
        [sys.executable, str(DOWNLOADER), "--all", "--source", args.source],
        cwd=str(REPO),
        capture_output=True, text=True, timeout=7200,  # 2h timeout
    )

    # Print the downloader's output
    if result.stdout:
        for line in result.stdout.splitlines():
            print(f"  {line}", flush=True)
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"  [stderr] {line}", flush=True)

    new_count = len(list(TARGET_DIR.glob("*.csv")))
    print(f"[bhavcopy-backfill] done. Files now: {new_count} (was {len(existing)})", flush=True)
    print(f"[bhavcopy-backfill] next: run nightly pipeline to ingest the new files", flush=True)
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())