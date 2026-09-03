"""One-command desk refresh (owner-runnable; no credentials involved).

Closes the gap between "the pipeline works" and "the UI is current":
  1. download today's bhavcopy via the owner's public downloader
  2. run the nightly pipeline (ingest recent 600 files -> scan -> regime ->
     report -> freeze events), the same driver the cron/background flow uses
  3. assert the newest session actually ADVANCED (holidays are legitimate —
     pass --allow-no-new-session to skip this gate)
  4. rebundle: copy the newest report JSONs into the terminal's src/data,
     regenerate per-session stock histories, regime history, outcomes,
     sector mapping and the desk-said map
  5. run the published invariants and export the desk-checks snapshot, so
     the UI's "Desk self-checks" panel is produced by the SAME run that
     produced the data (B2-4 — previously this docstring was asserted of a
     wiring that did not exist)
  6. rebuild the static bundle (npm run build)

B2-4 fail-fast contract: the FIRST failed step aborts the whole refresh.
A failed download no longer bundles, rebuilds and prints "DONE — session
<old date>"; that was the silent stale-data path. There is no DONE line and
no rebuild unless every step exited zero.

Usage:
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py           # full
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py --no-download
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py --exports-only
    .venv-orderflow/Scripts/python.exe unidesk/run_desk_refresh.py --allow-no-new-session

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
    ap.add_argument(
        "--allow-no-new-session", action="store_true",
        help="do not fail when the nightly produced no session newer than the "
             "newest already on disk (holidays are legitimate)",
    )
    args = ap.parse_args()

    def step(title: str, cmd: list[str] | str, **kw) -> bool:
        """B2-4: run one step; a non-zero exit aborts the whole refresh."""
        print(f"[refresh] — step: {title}", flush=True)
        rc = run(cmd, **kw)
        if rc != 0:
            print(
                f"[refresh] STEP FAILED: {title} (exit {rc}) — aborting. "
                f"No bundle, no build, no DONE: the desk stays on its last "
                f"fully-verified state.",
                flush=True,
            )
        return rc == 0

    if not args.exports_only:
        before = newest_sessions(1)
        if not args.no_download:
            downloader = REPO / "bhavcopy_extractor" / "download_bhavcopy.py"
            if not step("download bhavcopy", [PY, str(downloader), "--days", "3"]):
                return 1
        # the proven nightly driver: recent-600 ingest, gates, regime, report, freeze
        if not step("nightly pipeline", [PY, str(REPO / "unidesk" / "run_nightly_background.py")]):
            return 1
        # B2-4.3: the nightly must actually advance the desk. A silent
        # "succeeded but nothing moved" run is the stale-data path too.
        after = newest_sessions(1)
        if before and after and after[0] <= before[0] and not args.allow_no_new_session:
            print(
                f"[refresh] STEP FAILED: session advance — newest report session "
                f"is still {after[0]} (was {before[0]}). The nightly produced no "
                f"newer session. If this is a holiday/flat run, pass "
                f"--allow-no-new-session. Aborting: no bundle, no build, no DONE.",
                flush=True,
            )
            return 1

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
    if not step("stock history export", [PY, str(REPO / "unidesk" / "run_stock_history_export.py")]):
        return 1
    if not step("regime history export", [PY, str(REPO / "unidesk" / "run_export_regime_history.py")]):
        return 1
    if not step("outcomes export", [PY, str(REPO / "unidesk" / "run_history_outcomes_export.py"), sessions[0]]):
        return 1
    if not step("broker trades export", [PY, str(REPO / "unidesk" / "run_export_broker_trades.py")]):
        return 1
    if not step("sector mapping export", [PY, str(REPO / "unidesk" / "run_export_sector_mapping.py")]):
        return 1

    # prune older bundled outcomes (History reads the newest only)
    for old in SRC_DATA.glob("outcomes_*.json"):
        if old.name != f"outcomes_{sessions[0]}.json":
            old.unlink()
            print(f"[refresh] pruned old bundle {old.name}")

    # B2-4.1: the self-checks are produced by the same run that produced the
    # data — the UI's desk-checks panel can no longer vouch for data the
    # chain never verified. A flagged invariant aborts before the build.
    if not step("published invariants", [PY, str(REPO / "unidesk" / "run_published_invariants.py")]):
        return 1
    if not step("export desk checks", [PY, str(REPO / "unidesk" / "run_export_desk_checks.py")]):
        return 1

    if not step("npm run build", ["npm", "run", "build"], shell=True):
        return 1

    print(f"[refresh] DONE — session {sessions[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
