"""N3 CA-ratio review-queue artifact (directive-4, 2026-08-30).

Producing this queue is NOT owner-gated -- only the ratio SOURCE is
(``design/CONTEXT`` / HANDOFF directive-1e: "do not infer ratios from price
gaps"). This script only lists what the conservative bar-shape detector
flagged as an unconfirmed open-gap split candidate; it infers no real
factor. The owner (or a future ingestor backed by an official NSE/BSE
corporate-action feed) confirms each row against an authoritative source,
then adds a corrected row to ``config/confirmed_actions.csv`` -- this file
never writes to that one.

    python unidesk/run_ca_review_queue.py

Writes ``unidesk/config/ca_review_queue.csv`` (committed -- small, curated,
owner-facing, unlike the generated event store under data/market/, which
is gitignored).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.corp_actions import (  # noqa: E402
    DEFAULT_CONFIRMED_CSV, ConfirmedAction,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402
from unidesk.momentum.data.splits import (  # noqa: E402
    scan_store_for_splits, unconfirmed_candidate_sessions,
)

BACKLOG = REPO_ROOT / "data" / "bhavcopy"
OUT_PATH = REPO_ROOT / "unidesk" / "config" / "ca_review_queue.csv"

FIELDS = [
    "symbol", "session", "prev_close", "open", "implied_factor",
    "nearest_clean", "clean_distance_pct",
]


def _load_confirmed(path: Path) -> list[ConfirmedAction]:
    if not path.exists():
        return []
    out = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(ConfirmedAction(
                symbol=row["symbol"],
                ex_date=__import__("datetime").date.fromisoformat(row["ex_date"]),
                factor=float(row["factor"]),
                source=row["source"],
            ))
    return out


def build_queue() -> list[dict]:
    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)
    candidates = scan_store_for_splits(store)
    confirmed = _load_confirmed(DEFAULT_CONFIRMED_CSV)
    unconfirmed = unconfirmed_candidate_sessions(candidates, confirmed)
    unconfirmed_keys = {
        (sym, sess) for sym, sessions in unconfirmed.items() for sess in sessions
    }
    rows = [
        {
            "symbol": c.symbol,
            "session": c.session.isoformat(),
            "prev_close": c.prev_close,
            "open": c.open,
            "implied_factor": c.implied_factor,
            "nearest_clean": round(c.nearest_clean, 6),
            "clean_distance_pct": c.clean_distance_pct,
        }
        for c in candidates
        if (c.symbol, c.session) in unconfirmed_keys
    ]
    rows.sort(key=lambda r: (r["symbol"], r["session"]))
    return rows


if __name__ == "__main__":
    rows = build_queue()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ca-review-queue] {len(rows)} unconfirmed candidates written to {OUT_PATH}")
