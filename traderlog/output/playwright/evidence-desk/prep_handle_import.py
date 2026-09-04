"""Per-handle import pipeline: merge posts + self-replies capture files,
dry-run the strict importer, and print the decision-ready report.

Usage: python prep_handle_import.py <handle>
Produces <handle>_2026_combined.json + runs the dry-run; apply is a separate,
explicit step after the orchestrator reviews counts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
DB = ROOT / "traderlog" / "data" / "traderlog.db"


def main() -> int:
    handle = sys.argv[1]
    posts_p = D / f"{handle.lower()}_2026_posts.json"
    replies_p = D / f"{handle.lower()}_2026_selfreplies.json"
    if not posts_p.exists() and not replies_p.exists():
        print(f"no capture files for {handle}; driver may not have finished it")
        return 2
    merged: dict = {}
    for p in (posts_p, replies_p):
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            for h, recs in data.items():
                merged.setdefault(h, {})
                for pid, rec in recs.items():
                    merged[h][pid] = rec
    out = D / f"{handle.lower()}_2026_combined.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    handles = list(merged)
    print(f"combined: {len(handles)} handle(s), {sum(len(v) for v in merged.values())} posts -> {out.name}")
    if not handles:
        return 2
    cmd = [
        sys.executable, str(ROOT / "traderlog" / "run_import_provisional.py"),
        "--dry-run", "--handles", *handles,
        "--source", str(out), "--db", str(DB),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout or res.stderr)
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())