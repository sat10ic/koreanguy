"""One definition of the nightly desk chain (PART E-1).

Both fronts execute THIS step table so they cannot drift apart:
  * the CLI — ``unidesk/run_desk_refresh.py`` (prints the same operator
    output as before), and
  * the localhost server — ``unidesk/server/app.py`` (``POST /api/refresh``,
    SSE progress via ``iter_job`` events).

B2-4 semantics live here, once: steps run in order, the FIRST failed step
aborts the job (no bundling, no build, no DONE on stale data), the newest
report session must actually advance (unless ``allow_no_new_session``), and
the published invariants + desk-checks export run inside the chain, before
the build.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
REPORTS = REPO / "data" / "market" / "reports"          # authoritative reports
SRC_DATA = REPO / "unidesk_terminal" / "src" / "data"   # derived UI-bundled exports

OUTPUT_TAIL_CAP = 20_000  # chars retained per step, so a long run cannot exhaust memory


class StepFailure(RuntimeError):
    """Raised by in-process steps; carries the operator-facing reason."""


def newest_report_sessions(n: int, reports_dir: Path = REPORTS) -> list[str]:
    """Newest first, by session_date parsed from the JSON — never glob order.

    Filenames and the embedded session_date can disagree (misnamed copy,
    clock skew); the embedded date is authoritative, so every report is
    parsed and the results sorted by date — the answer cannot depend on
    directory enumeration order (the C-2 bug class).
    """
    dates: set[str] = set()
    for p in Path(reports_dir).glob("tonight_*.json"):
        try:
            sess = json.loads(p.read_text(encoding="utf-8")).get("session_date")
        except Exception:
            continue
        if sess:
            dates.add(sess)
    return sorted(dates, reverse=True)[:n]


def newest_derived_session(data_dir: Path = SRC_DATA) -> Optional[str]:
    """Newest session among the UI-bundled tonight_*.json (by filename date)."""
    dates = sorted(
        (p.stem.removeprefix("tonight_") for p in Path(data_dir).glob("tonight_*.json")),
        reverse=True,
    )
    return dates[0] if dates else None


@dataclass(frozen=True)
class Step:
    name: str
    label: str
    argv: Optional[list[str]] = None
    argv_fn: Optional[Callable[[dict], list[str]]] = None
    shell: bool = False
    fn: Optional[Callable[[dict], None]] = None
    skip_when: tuple[str, ...] = ()


# ---------------------------------------------------------------- in-process steps

def _gate_session_advance(ctx: dict) -> None:
    """B2-4.3: the nightly must actually advance the desk. A silent
    "succeeded but nothing moved" run is the stale-data path too."""
    opts = ctx["options"]
    before, after = ctx["before_sessions"], newest_report_sessions(1)
    ctx["sessions"] = after
    if not before or not after:
        return  # nothing to compare against (first run / empty dir): let downstream fail loudly
    if after[0] <= before[0]:
        if opts.get("allow_no_new_session"):
            print(f"[jobs] session advance skipped (--allow-no-new-session): still {after[0]}", flush=True)
            return
        raise StepFailure(
            f"session advance — newest report session is still {after[0]} (was {before[0]}). "
            f"The nightly produced no newer session. If this is a holiday/flat run, pass "
            f"--allow-no-new-session."
        )


def _bundle_reports(ctx: dict) -> None:
    sessions = ctx.get("sessions") or newest_report_sessions(2)
    ctx["sessions"] = sessions
    if not sessions:
        raise StepFailure("no reports found in data/market/reports — nothing to bundle")
    keep = set()
    for sess in sessions:
        src = REPORTS / f"tonight_{sess}.json"
        if src.exists():
            shutil.copy2(src, SRC_DATA / f"tonight_{sess}.json")
            keep.add(f"tonight_{sess}.json")
    for old in SRC_DATA.glob("tonight_*.json"):
        if old.name not in keep:
            old.unlink()
            print(f"[jobs] pruned old bundle {old.name}", flush=True)


def _prune_outcomes(ctx: dict) -> None:
    sessions = ctx.get("sessions") or newest_report_sessions(1)
    newest = sessions[0] if sessions else None
    for old in SRC_DATA.glob("outcomes_*.json"):
        if newest is None or old.name != f"outcomes_{newest}.json":
            old.unlink()
            print(f"[jobs] pruned old bundle {old.name}", flush=True)


# ---------------------------------------------------------------- the chain

def refresh_steps() -> list[Step]:
    return [
        Step("download", "download bhavcopy",
             argv=[PY, str(REPO / "bhavcopy_extractor" / "download_bhavcopy.py"), "--days", "3"],
             skip_when=("no_download", "exports_only")),
        Step("nightly", "nightly pipeline",
             argv=[PY, str(REPO / "unidesk" / "run_nightly_background.py")],
             skip_when=("exports_only",)),
        Step("session_gate", "session advance check", fn=_gate_session_advance,
             skip_when=("exports_only",)),
        Step("bundle_reports", "bundle reports into src/data", fn=_bundle_reports),
        Step("stock_history", "stock history export",
             argv=[PY, str(REPO / "unidesk" / "run_stock_history_export.py")]),
        Step("regime_history", "regime history export",
             argv=[PY, str(REPO / "unidesk" / "run_export_regime_history.py")]),
        Step("outcomes", "outcomes export",
             argv_fn=lambda ctx: [PY, str(REPO / "unidesk" / "run_history_outcomes_export.py"),
                                  (ctx.get("sessions") or newest_report_sessions(1))[0]]),
        Step("broker_trades", "broker trades export",
             argv=[PY, str(REPO / "unidesk" / "run_export_broker_trades.py")]),
        Step("sector_mapping", "sector mapping export",
             argv=[PY, str(REPO / "unidesk" / "run_export_sector_mapping.py")]),
        Step("prune_outcomes", "prune old bundled outcomes", fn=_prune_outcomes),
        Step("checks", "governance checks (run_checks)",
             argv=[PY, str(REPO / "unidesk" / "run_checks.py")]),
        Step("invariants", "published invariants",
             argv=[PY, str(REPO / "unidesk" / "run_published_invariants.py")]),
        Step("desk_checks", "export desk checks",
             argv=[PY, str(REPO / "unidesk" / "run_export_desk_checks.py")]),
        Step("build", "npm run build", argv=["npm", "run", "build"], shell=True,
             skip_when=("skip_build",)),
    ]


def iter_job(options: dict, *, capture_output: bool = False) -> Iterator[dict]:
    """Execute REFRESH_STEPS in order, yielding structured events.

    Aborts on the first failed step (B2-4): after a ``stage_failed`` the
    iterator yields ``job_failed`` and stops — later steps never run.
    ``capture_output`` merges each step's stdout/stderr into the events
    (tail-capped) so the server can surface a failure's output; the CLI
    leaves it off to inherit the console streams live.
    """
    job_id = options.get("job_id", "")
    steps = refresh_steps()
    total = len(steps)
    t0 = time.time()
    ctx: dict = {"options": options, "before_sessions": newest_report_sessions(1), "sessions": None}
    yield {"event": "job_started", "job_id": job_id,
           "started_at": datetime.now(timezone.utc).isoformat(), "options": options}
    for i, step in enumerate(steps):
        if any(options.get(f) for f in step.skip_when):
            yield {"event": "stage_skipped", "name": step.name, "label": step.label,
                   "index": i, "total": total}
            continue
        yield {"event": "stage_started", "name": step.name, "label": step.label,
               "index": i, "total": total}
        ts = time.time()
        exit_code: Optional[int] = 0
        output_tail = ""
        error = ""
        try:
            if step.fn is not None:
                step.fn(ctx)
            else:
                argv = step.argv_fn(ctx) if step.argv_fn else step.argv
                assert argv is not None
                yield {"event": "stage_cmd", "name": step.name, "cmd": " ".join(argv) if isinstance(argv, list) else str(argv)}
                if capture_output:
                    proc = subprocess.run(
                        argv, cwd=str(REPO), shell=step.shell,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    )
                    exit_code = proc.returncode
                    output_tail = (proc.stdout or "")[-OUTPUT_TAIL_CAP:]
                else:
                    exit_code = subprocess.call(argv, cwd=str(REPO), shell=step.shell)
        except StepFailure as exc:
            exit_code, error = None, str(exc)
        except Exception as exc:  # noqa: BLE001 — a step crash is a failed step
            exit_code, error = None, f"{type(exc).__name__}: {exc}"
        duration = round(time.time() - ts, 1)
        base = {"name": step.name, "label": step.label, "index": i, "total": total,
                "duration_s": duration}
        if (exit_code is not None and exit_code != 0) or error:
            yield {"event": "stage_failed", "exit_code": exit_code, "error": error,
                   "output_tail": output_tail, **base}
            yield {"event": "job_failed", "job_id": job_id, "failed_stage": step.name,
                   "exit_code": exit_code, "error": error,
                   "duration_s": round(time.time() - t0, 1),
                   "finished_at": datetime.now(timezone.utc).isoformat()}
            return
        yield {"event": "stage_finished", "exit_code": exit_code,
               "output_tail": output_tail, **base}
    sessions = ctx.get("sessions") or newest_report_sessions(1)
    yield {"event": "job_finished", "job_id": job_id,
           "session": sessions[0] if sessions else None,
           "duration_s": round(time.time() - t0, 1),
           "finished_at": datetime.now(timezone.utc).isoformat()}
