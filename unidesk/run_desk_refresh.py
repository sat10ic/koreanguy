"""One-command desk refresh (owner-runnable; no credentials involved).

Closes the gap between "the pipeline works" and "the UI is current":
  1. download today's bhavcopy via the owner's public downloader
  2. run the nightly pipeline (ingest recent 600 files -> scan -> regime ->
     report -> freeze events), the same driver the cron/background flow uses
  3. rebundle: copy the newest report JSONs into the terminal's src/data,
     regenerate per-session stock histories, regime history, outcomes,
     sector mapping and the desk-said map
  4. rebuild the static bundle (npm run build)

Usage:
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py           # full
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py --no-download
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py --exports-only

Honest limits: this is an EOD desk over NSE bhavcopy — "live" means
"current as of the last post-close run", never intraday (that would need a
real-time feed, which is the separate owner-gated orderflow workstream).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
UI = REPO / "unidesk_terminal"
REPORTS = REPO / "data" / "market" / "reports"
SRC_DATA = UI / "src" / "data"


def run(cmd: list[str] | str, **kw) -> int:
    print(f"[refresh] $ {cmd if isinstance(cmd, str) else ' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=str(REPO), **kw)
    print(f"[refresh] exit {rc} in {time.time() - t0:.0f}s", flush=True)
    return rc


def newest_sessions(n: int) -> list[str]:
    sessions = []
    for p in sorted(REPORTS.glob("tonight_*.json"), reverse=True):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        sess = raw.get("session_date")
        if sess and sess not in sessions:
            sessions.append(sess)
        if len(sessions) >= n:
            break
    return sessions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--exports-only", action="store_true")
    args = ap.parse_args()

    failures = 0

    if not args.exports_only:
        if not args.no_download:
            downloader = REPO / "bhavcopy_extractor" / "download_bhavcopy.py"
            failures += run([PY, str(downloader), "--days", "3"])
        # the proven nightly driver: recent-600 ingest, gates, regime, report, freeze
        failures += run([PY, str(REPO / "unidesk" / "run_nightly_background.py")])

    sessions = newest_sessions(2)
    if not sessions:
        print("[refresh] no reports found — aborting bundle step")
        return 1
    print(f"[refresh] bundling sessions: {sessions}")

    # rebundle reports (keep the newest 2; prune older bundled copies)
    keep = set()
    for sess in sessions:
        src = REPORTS / f"tonight_{sess}.json"
        if src.exists():
            shutil.copy2(src, SRC_DATA / f"tonight_{sess}.json")
            keep.add(f"tonight_{sess}.json")
    for old in SRC_DATA.glob("tonight_*.json"):
        if old.name not in keep:
            old.unlink()
            print(f"[refresh] pruned old bundle {old.name}")

    # per-session stock histories + regime + outcomes + desk-said
    failures += run([PY, str(REPO / "unidesk" / "run_stock_history_export.py")])
    failures += run([PY, str(REPO / "unidesk" / "run_export_regime_history.py")])
    failures += run([PY, str(REPO / "unidesk" / "run_history_outcomes_export.py"), sessions[0]])
    failures += run([PY, str(REPO / "unidesk" / "run_export_broker_trades.py")])
    failures += run([PY, str(REPO / "unidesk" / "run_export_sector_mapping.py")])

    # prune older bundled outcomes (History reads the newest only)
    for old in SRC_DATA.glob("outcomes_*.json"):
        if old.name != f"outcomes_{sessions[0]}.json":
            old.unlink()
            print(f"[refresh] pruned old bundle {old.name}")

    failures += run(["npm", "run", "build"], shell=True)

    print(f"[refresh] DONE — session {sessions[0]} (failures: {failures})")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
