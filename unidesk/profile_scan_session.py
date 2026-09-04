"""4a profiler — find where ONE point-in-time session scan actually spends
its time, before building any cache.

Run AFTER the B2-3 remediation has finished (this needs the full ~4.5GB
ingested store; running it concurrently would thrash the box):

    .venv-orderflow/Scripts/python.exe unidesk/profile_scan_session.py [--sessions 3]

Profiles the last N eligible sessions with cProfile, prints the top
cumulative-time functions, and separates: ingest/fingerprint (excluded),
adjust_ohlcv, detectors, gates, RS/breadth, attach. The 4a cache is built
against whatever dominates — not against a guess.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402
from unidesk.research.archive_attach import archive_sessions, run_archive_attach  # noqa: E402

BACKLOG = REPO_ROOT / "data" / "bhavcopy"
DATA_ROOT = REPO_ROOT / "data" / "market"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=3)
    args = ap.parse_args()

    t0 = time.time()
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    print(f"[profile] ingest: {time.time() - t0:.0f}s "
          f"(bars={len(store._daily)})", flush=True)

    eligible = archive_sessions(store)
    probe = eligible[-args.sessions:]  # the newest sessions = realistic universe size
    print(f"[profile] probing {len(probe)} sessions: "
          f"{probe[0]} .. {probe[-1]}", flush=True)

    profiler = cProfile.Profile()
    t1 = time.time()
    profiler.enable()
    run_archive_attach(
        backlog=BACKLOG, data_root=DATA_ROOT, horizon=10, stop_atr_mult=1.0,
        store=store, only_sessions=probe,
    )
    profiler.disable()
    wall = time.time() - t1
    print(f"[profile] {len(probe)} sessions in {wall:.0f}s "
          f"({wall / len(probe):.1f}s/session)\n", flush=True)

    out = io.StringIO()
    stats = pstats.Stats(profiler, stream=out).sort_stats("cumulative")
    stats.print_stats(35)
    text = out.getvalue()
    print(text[:8000])
    (REPO_ROOT / "unidesk" / "_profile_scan_session.txt").write_text(text, encoding="utf-8")
    print("[profile] full output -> unidesk/_profile_scan_session.txt", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
