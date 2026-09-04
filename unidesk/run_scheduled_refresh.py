"""Scheduled-nightly wrapper (B2-7): run the desk refresh chain, log every
run to a dated file, and record the result in unidesk/last_run.json so the
server (/api/health) and the UI can show the last scheduled run's outcome.

A scheduled job that fails silently is worse than no scheduled job — this
wrapper exists so the failure is NAMED (stage + exit code), DATED, and
VISIBLE without the owner opening a log.

Exit code: 0 only when every step of the chain exited zero (B2-4 fail-fast
semantics come from unidesk.server.jobs.iter_job).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.server.jobs import iter_job  # noqa: E402

LOGS = REPO / "unidesk" / "logs"
LAST_RUN = REPO / "unidesk" / "last_run.json"


def main() -> int:
    started = datetime.now(timezone.utc)
    LOGS.mkdir(exist_ok=True)
    log_path = LOGS / f"nightly_{started.strftime('%Y%m%d_%H%M%S')}.log"
    log_lines: list[str] = []

    def tee(line: str) -> None:
        print(line, flush=True)
        log_lines.append(line)

    options = {
        "no_download": False,
        "exports_only": False,
        "skip_build": False,   # the scheduled run rebuilds the offline bundle too
        "allow_no_new_session": False,
        "job_id": "scheduled",
    }
    rc = 0
    failed_stage = None
    session = None
    warning = None
    # capture_output: the dated log is the ONLY evidence a scheduled failure
    # leaves — tonight's build failure carried no error text because the tail
    # was never captured. Full tails (20k cap) are tee'd into the log.
    for ev in iter_job(options, capture_output=True):
        kind = ev["event"]
        if kind == "stage_started":
            tee(f"[nightly {started.isoformat(timespec='seconds')}] — step: {ev['label']}")
        elif kind == "stage_cmd":
            tee(f"[nightly] $ {ev['cmd']}")
        elif kind == "stage_skipped":
            tee(f"[nightly] — step: {ev['label']} (skipped)")
        elif kind == "stage_finished":
            tee(f"[nightly] exit {ev['exit_code']} in {ev['duration_s']:.0f}s")
            if ev.get("output_tail", "").strip():
                tee("[nightly] ---- output (tail) ----")
                for ln in ev["output_tail"].splitlines()[-12:]:
                    tee(f"[nightly] {ln}")
        elif kind == "stage_failed":
            failed_stage = ev["name"]
            tee(f"[nightly] STEP FAILED: {ev['label']} "
                f"(exit {ev.get('exit_code')}) {('— ' + ev['error']) if ev.get('error') else ''}")
            if ev.get("output_tail"):
                tee("[nightly] ---- output tail ----")
                for ln in ev["output_tail"].splitlines()[-40:]:
                    tee(f"[nightly] {ln}")
            rc = 1
        elif kind == "job_failed":
            rc = 1
        elif kind == "job_finished":
            session = ev.get("session")
            warning = ev.get("warning")
            tee(f"[nightly] DONE — session {session}")
            if warning:
                tee(f"[nightly] WARNING: {warning}")

    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    # keep the log dir bounded: newest 30 nightly logs survive
    for old in sorted(LOGS.glob("nightly_*.log"))[:-30]:
        old.unlink(missing_ok=True)

    LAST_RUN.write_text(json.dumps({
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exit_code": rc,
        "status": "succeeded" if rc == 0 else "failed",
        "failed_stage": failed_stage,
        "session": session,
        "warning": warning,
        "log_file": str(log_path),
        "trigger": "scheduled",
    }, indent=2) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
