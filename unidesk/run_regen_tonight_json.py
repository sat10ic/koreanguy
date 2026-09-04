"""Regenerate the terminal's tonight JSON with all new backend fields."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unidesk.momentum.data.bhavcopy import ingest_directory
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.data.corp_actions import load_confirmed_actions
from unidesk.momentum.scan import scan_universe
from unidesk.momentum.report_json import build_nightly_json
from datetime import datetime, timezone

t0 = time.time()
store = InMemoryMarketStore()
ingest_directory(store, Path(__file__).resolve().parent.parent / "data" / "bhavcopy")
actions = load_confirmed_actions()
scan = scan_universe(store, datetime(2026, 8, 28, 18, 30, tzinfo=timezone.utc), actions=actions, apply_universe_gates=True)
report = build_nightly_json(scan)
out = Path(__file__).resolve().parent.parent / "unidesk_terminal" / "src" / "data" / "tonight_2026-08-28.json"
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
elapsed = time.time() - t0
c = report["candidates"][0]
print(f"scan {scan.scanned} symbols in {elapsed:.1f}s")
print(f"candidate fields: {list(c.keys())}")
print(f"has activity_score: {'activity_score' in c}")
print(f"has stock_quality: {'stock_quality' in c}")
print(f"has breadth: {'breadth' in report['honesty_footer']}")
print(f"has detector_trust: {'detector_trust' in report}")
print(f"has base_episodes: {'base_episodes' in report}")
print(f"base_episodes count: {len(report.get('base_episodes', []))}")
if report["base_episodes"]:
    print(f"first episode keys: {list(report['base_episodes'][0].keys())}")
    print(f"has vcp_match: {'vcp_match' in report['base_episodes'][0]}")