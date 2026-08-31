"""Start a full archive re-run with the expanded CA table (55 actions).

Reads the bhavcopy store once, re-scans every eligible session with the
current confirmed_actions.csv, freezes, attaches outcomes (now with the
adv_series threaded for net_bps), and persists. Overwrites stale partitions.

This is safe to run concurrently with nightly.py (which writes to
data/market/reports/, not data/market/research/events/).

Logs to data/market/reports/regen_ca55.log. Check progress with:

    tail -f data/market/reports/regen_ca55.log
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
LOG = REPO / "data" / "market" / "reports" / "regen_ca55.log"

if __name__ == "__main__":
    t0 = time.time()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(LOG, "a", encoding="utf-8")

    def log(msg: str):
        ts = time.strftime("%H:%M:%S", time.gmtime())
        line = f"[{ts}] {msg}\n"
        print(line, end="", flush=True)
        log_fh.write(line)
        log_fh.flush()

    log(f"starting full archive re-run with {len(list(BACKLOG.glob('*bhav*.csv')))} backlog files")
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    log(f"ingested {len(store._daily)} bars")

    result = run_archive_attach(
        backlog=BACKLOG, data_root=DATA_ROOT,
        horizon=10, stop_atr_mult=1.0,
        progress_every=5, store=store,
    )
    elapsed = round(time.time() - t0, 1)
    log(f"done: {result['sessions_processed']} sessions, {result['total_events']} events in {elapsed}s")
    log(f"  status: {result['status_counts']}")
    log(f"  unconfirmed CA: {result['unconfirmed_ca_symbols']} symbols / {result['unconfirmed_ca_sessions']} sessions")
    log_fh.close()