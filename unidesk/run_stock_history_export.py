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
UI_DATA = REPO_ROOT / "unidesk_terminal" / "src" / "data"
# Every bundled report session gets its own point-in-time history snapshot
# (bars strictly at-or-before that session -- no future leakage between
# sessions). One store ingest serves all of them. Sessions are derived
# dynamically: the NEWEST report sessions on disk (refresh driver keeps
# this in sync with what gets bundled).
def newest_report_sessions(n: int = 2) -> list[str]:
    import json as _json
    reports = sorted((REPO_ROOT / "data" / "market" / "reports").glob("tonight_*.json"))
    sessions = []
    for p_ in reversed(reports):
        try:
            raw = _json.loads(p_.read_text(encoding="utf-8"))
        except Exception:
            continue
        sess = raw.get("session_date")
        if sess and sess not in sessions:
            sessions.append(sess)
        if len(sessions) >= n:
            break
    return sessions


SESSIONS = newest_report_sessions(2)

# Real history, but capped: the frontend chart reads a bounded lookback, and
# the fixture generateOhlc() it replaces used 180 synthetic bars -- 130
# (~6 months) is real, plenty for a base/breakout chart, without ballooning
# the committed JSON (a dict-per-bar shape at 260 bars * 235 symbols was
# 5.2MB; this column-array shape at 130 bars is well under 2MB).
MAX_BARS = 130
RECENT_FILES = 210  # ~1.5x the 130-session window, margin for gaps


def build_history(store, session_date: str, symbols: list[str]) -> dict[str, list[dict]]:
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
    # Low-memory ingest: MAX_BARS=130 needs only the most recent ~135
    # sec_bhavdata_full sessions. Ingesting the full 4,034-file corpus
    # costs ~6 GB of RAM for data this export never reads -- and this box
    # co-runs the multi-hour archive regen. Same output, bounded footprint.
    store = InMemoryMarketStore()
    sec_files = sorted(
        (p_ for p_ in BACKLOG.iterdir()
         if p_.suffix.lower() == ".csv" and "sec_bhavdata_full" in p_.name),
        key=lambda p_: p_.stem.split("_")[-1][4:8] + p_.stem.split("_")[-1][2:4] + p_.stem.split("_")[-1][0:2],
    )
    from unidesk.momentum.data.bhavcopy import parse_bhavcopy_file, load_into_store
    seen: set = set()
    for path in sec_files[-RECENT_FILES:]:
        try:
            rows, _stats = parse_bhavcopy_file(path)
            load_into_store(store, rows, seen=seen)
        except Exception:
            continue
    reports_dir = REPO_ROOT / "data" / "market" / "reports"
    for session_date in SESSIONS:
        # Read the SOURCE reports (data/market/reports), not the bundled
        # src/data copies -- the bundles are outputs of this pipeline and
        # may lag a regeneration.
        tonight_path = reports_dir / f"tonight_{session_date}.json"
        tonight = json.loads(tonight_path.read_text(encoding="utf-8"))
        symbols = sorted({c["symbol"] for c in tonight["candidates"]})
        history = build_history(store, session_date, symbols)
        out_path = UI_DATA / f"stock_history_{session_date}.json"
        out_path.write_text(json.dumps(history, separators=(",", ":")), encoding="utf-8")
        total_bars = sum(len(v["sessions"]) for v in history.values())
        print(f"[stock-history] {session_date}: {len(history)} symbols, "
              f"{total_bars} total bars -> {out_path}")
