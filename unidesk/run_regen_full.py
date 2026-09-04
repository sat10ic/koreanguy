"""Start a full archive re-run with CORRECTED CA table (4 verified) + gates.
Auto-confirmed 51 actions quarantined. Universe gates enabled (excludes ETFs).
"""
from __future__ import annotations
import sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from unidesk.momentum.data.bhavcopy import ingest_directory
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.research.archive_attach import run_archive_attach

BACKLOG = REPO / "data" / "bhavcopy"
DATA_ROOT = REPO / "data" / "market"
LOG = REPO / "data" / "market" / "reports" / "regen_v4_gated.log"

if __name__ == "__main__":
    t0 = time.time()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(LOG, "a", encoding="utf-8")
    def log(msg):
        ts = time.strftime("%H:%M:%S", time.gmtime())
        line = f"[{ts}] {msg}\n"; print(line, end="", flush=True); log_fh.write(line); log_fh.flush()
    log("gated archive re-run: 4 CA actions, apply_universe_gates=True")
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    log(f"ingested {len(store._daily)} bars")
    result = run_archive_attach(backlog=BACKLOG, data_root=DATA_ROOT, horizon=10, stop_atr_mult=1.0, progress_every=5, store=store)
    elapsed = round(time.time() - t0, 1)
    log(f"done: {result['sessions_processed']} sessions, {result['total_events']} events, {elapsed}s")
    log(f"status: {result['status_counts']}")
    log_fh.close()