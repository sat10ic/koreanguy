"""Sequential driver: capture 2026 posts + self-replies for remaining traders.

Human-paced; long-running. One handle at a time (posts tab then with_replies
tab), with a pause between handles to avoid X throttling. Writes one combined
checkpoint per handle.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT))
from extract_manas_deep import deep  # noqa: E402

D = SCRIPT
REMAINING = [
    "tradinghustlr", "VCPSwing", "StocksNerd", "ChartistEdge",
    "iArpanK", "mystocks_in", "rpmrpm4", "thechartist26", "SakatasHomma",
    "Trading4Bucks", "wealthexpress21", "Setups_Swing",
    "investor_sr33", "multibaggerwala", "AdeptMarket",
]
DAYS = 235  # ~ all of 2026 (to 2026-01-01)
LIMIT = 120

summary = {}
for handle in REMAINING:
    posts_out = D / f"{handle.lower()}_2026_posts.json"
    replies_out = D / f"{handle.lower()}_2026_selfreplies.json"
    # Resume: skip handles whose both files already exist (completed earlier runs).
    if posts_out.exists() and replies_out.exists():
        print(f"=== {handle}: already captured (files exist), skipping ===", flush=True)
        summary[handle] = {"posts": "skipped", "self_replies": "skipped"}
        continue
    print(f"=== {handle}: posts ===", flush=True)
    try:
        posts = deep(handle, "posts", DAYS, posts_out, LIMIT, False)
        print(f"=== {handle}: posts done ({len(posts)}) ===", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"!! {handle} posts: {type(exc).__name__}: {exc}", flush=True)
        posts = {}
    time.sleep(20)
    print(f"=== {handle}: self-replies ===", flush=True)
    try:
        replies = deep(handle, "with_replies", DAYS, replies_out, LIMIT, True)
        print(f"=== {handle}: self-replies done ({len(replies)}) ===", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"!! {handle} replies: {type(exc).__name__}: {exc}", flush=True)
        replies = {}
    summary[handle] = {"posts": len(posts), "self_replies": len(replies)}
    # human-paced pause between traders
    time.sleep(75)

(D / "_remaining_summary.json").write_text(
    json.dumps(summary, indent=1), encoding="utf-8"
)
print("SUMMARY:", json.dumps(summary, indent=1))