"""One-command desk refresh (owner-runnable; no credentials involved).

Closes the gap between "the pipeline works" and "the UI is current".

E-1: the step table lives in unidesk/server/jobs.py (refresh_steps) and is
shared with the localhost server's POST /api/refresh — the CLI and the
server cannot drift apart. This script consumes the job events and prints
the same operator output as before.

B2-4 fail-fast contract (enforced in jobs.py): the FIRST failed step aborts
the whole refresh. A failed download no longer bundles, rebuilds and prints
"DONE — session <old date>"; that was the silent stale-data path. There is
no DONE line and no rebuild unless every step exited zero. The published
invariants and the desk-checks export run inside the chain, so the UI's
self-check panel is always produced by the same run that produced the data.

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
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.server.jobs import iter_job  # noqa: E402


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

    options = {
        "no_download": args.no_download,
        "exports_only": args.exports_only,
        "skip_build": False,
        "allow_no_new_session": args.allow_no_new_session,
    }

    rc = 0
    for ev in iter_job(options):
        kind = ev["event"]
        if kind == "stage_started":
            print(f"[refresh] — step: {ev['label']}", flush=True)
        elif kind == "stage_cmd":
            print(f"[refresh] $ {ev['cmd']}", flush=True)
        elif kind == "stage_skipped":
            print(f"[refresh] — step: {ev['label']} (skipped)", flush=True)
        elif kind == "stage_finished":
            print(f"[refresh] exit {ev['exit_code']} in {ev['duration_s']:.0f}s", flush=True)
        elif kind == "stage_failed":
            detail = f": {ev['error']}" if ev.get("error") else ""
            print(
                f"[refresh] STEP FAILED: {ev['label']} "
                f"(exit {ev['exit_code'] if ev.get('exit_code') is not None else '—'}){detail} — "
                f"aborting. No bundle, no build, no DONE: the desk stays on its "
                f"last fully-verified state.",
                flush=True,
            )
            rc = 1
        elif kind == "job_failed":
            rc = 1
        elif kind == "job_finished":
            print(f"[refresh] DONE — session {ev['session']}", flush=True)
            if ev.get("warning"):  # B2-7: no-new-session is a loud warning, not an abort
                print(f"[refresh] WARNING: {ev['warning']}", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
