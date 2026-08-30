"""Stock-screen point-in-time OHLCV export (UI_BACKEND_INTEGRATION_PLAN.md
row 3, "Stock" screen) -- unblocked now that U-P0.3
(``InMemoryMarketStore.get_market_state``) is confirmed built and tested.

The frontend chart (``unidesk_terminal/src/components/widgets/StockChart.tsx``)
currently renders `generateOhlc()` -- entirely synthetic, seeded from a price
and a symbol string, not real data. This script emits real daily OHLCV
history for every symbol in the current Tonight report, strictly at-or-before
that report's session date (no future leakage: it reads the same
bhavcopy backlog the scan itself reads, and every bar's session is <= the
report's own session_date by construction of the ingest).

    python unidesk/run_stock_history_export.py

Writes ``unidesk_terminal/src/data/stock_history_<date>.json`` -- committed,
same convention as ``tonight_<date>.json`` (a static Vite build-time
snapshot; this is a nightly EOD desk with no live fetch, per the
integration plan).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402

BACKLOG = REPO_ROOT / "data" / "bhavcopy"
TONIGHT_JSON = REPO_ROOT / "unidesk_terminal" / "src" / "data" / "tonight_2026-08-28.json"
OUT_PATH = REPO_ROOT / "unidesk_terminal" / "src" / "data" / "stock_history_2026-08-28.json"

# Real history, but capped: the frontend chart reads a bounded lookback, and
# the fixture generateOhlc() it replaces used 180 synthetic bars -- 130
# (~6 months) is real, plenty for a base/breakout chart, without ballooning
# the committed JSON (a dict-per-bar shape at 260 bars * 235 symbols was
# 5.2MB; this column-array shape at 130 bars is well under 2MB).
MAX_BARS = 130


def build_history() -> dict[str, list[dict]]:
    tonight = json.loads(TONIGHT_JSON.read_text(encoding="utf-8"))
    session_date = tonight["session_date"]
    symbols = sorted({c["symbol"] for c in tonight["candidates"]})

    store = InMemoryMarketStore()
    ingest_directory(store, BACKLOG)

    by_symbol: dict[str, list] = {}
    for item in store._daily:
        if item.bar.symbol in symbols and item.bar.session.isoformat() <= session_date:
            by_symbol.setdefault(item.bar.symbol, []).append(item.bar)

    # Column-array shape ([sessions], [opens], [highs], [lows], [closes],
    # [volumes]) rather than a dict per bar -- same data, far less JSON key
    # repetition over 235 symbols x up to 130 bars each.
    out: dict[str, dict[str, list]] = {}
    missing = []
    for sym in symbols:
        bars = sorted(by_symbol.get(sym, []), key=lambda b: b.session)
        if not bars:
            missing.append(sym)
            continue
        bars = bars[-MAX_BARS:]
        out[sym] = {
            "sessions": [b.session.isoformat() for b in bars],
            "opens": [b.open for b in bars],
            "highs": [b.high for b in bars],
            "lows": [b.low for b in bars],
            "closes": [b.close for b in bars],
            "volumes": [b.volume for b in bars],
        }
    if missing:
        print(f"[stock-history] {len(missing)} symbols had no bhavcopy bars "
              f"as of {session_date} (skipped, not fabricated): {missing[:10]}"
              f"{'...' if len(missing) > 10 else ''}")
    return out


if __name__ == "__main__":
    history = build_history()
    OUT_PATH.write_text(json.dumps(history, separators=(",", ":")), encoding="utf-8")
    total_bars = sum(len(v["sessions"]) for v in history.values())
    print(f"[stock-history] {len(history)} symbols, {total_bars} total bars "
          f"written to {OUT_PATH}")
