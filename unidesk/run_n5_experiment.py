"""N5 experiment runner (wave C-1).

The N5 plan is to compare two competing candidate books (e.g. S_ep-ranked
candidates vs a pre-registered DUMB baseline) on the same session
window and emit an ``EdgeVerdict`` per the swing-edges spec §10.4
gates. The verdict engine (``research.experiments.compare_edge``) is
already landed in wave A; this runner is the piece that:
  1. loads the research event store,
  2. applies the snapshot-bindings scorers (wave C-1 = S_ep only;
     wave C-2 adds S_tight),
  3. constructs Trade books from scored candidates + measured outcomes,
  4. calls compare_edge and writes the verdict JSON.

Today only ``--experiment dry-run`` is real. The ``a`` and ``b`` paths
raise NotImplementedError with a precise list of what is missing
(net_bps writer fix, S_tight score coverage) so the next owner can
build the next wave without re-reading the design.

Usage (from repo root)::

    .venv-orderflow/Scripts/python.exe unidesk/run_n5_experiment.py --experiment dry-run
    .venv-orderflow/Scripts/python.exe unidesk/run_n5_experiment.py --experiment a --report-session 2026-08-28
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.contracts.base import ContractError
from unidesk.momentum.scoring._snapshot_bindings import (
    s_tight_status_from_snapshot, score_ep_from_snapshot,
)
from unidesk.research.event_store import load_events, session_of

DATA_ROOT = REPO_ROOT / "data" / "market"
OUT_DIR = REPO_ROOT / "unidesk" / "design" / "n5"

EXPERIMENT_LABELS = {
    "a": "Experiment A: S_ep-ranked candidates vs gap-and-go DUMB baseline",
    "b": "Experiment B: S_tight-ranked candidates vs volume-confirmed DUMB baseline",
}


def _coverage_report(events, *, only_valid_detector: bool) -> dict:
    """Walk every event and report per-detector S_ep coverage.

    The report is the done-test for wave C-1: the operator can see
    exactly how many events are scoreable today, which inputs are
    missing, and where the gaps are. No verdict; no filtering by
    candidate-vs-negative; that is the runner's job in C-3."""
    per_detector_ep: dict[str, dict] = {}
    per_detector_tight: dict[str, dict] = {}
    n_total = 0
    n_with_gap = 0
    n_with_full_ep_coverage = 0
    for ev in events:
        n_total += 1
        snap = ev.snapshot or {}
        dets = snap.get("detectors") or {}
        # The first detector that returned VALID is the candidate
        # identity for this event. If only_valid_detector is True,
        # skip negatives; if False, include them (so the report
        # shows the negative class too).
        fired = None
        for name, d in dets.items():
            if isinstance(d, dict) and d.get("detection") == "VALID":
                fired = name
                break
        if only_valid_detector and fired is None:
            continue
        identity = fired or "<no_valid_detector>"
        ep_bucket = per_detector_ep.setdefault(identity, {
            "n_events": 0, "scored": 0, "mean_s_ep": None,
            "mean_coverage": None, "unknowns": Counter(),
        })
        ep_bucket["n_events"] += 1
        decision = score_ep_from_snapshot(ev.symbol, session_of(ev), snap)
        ep_bucket["scored"] += 1 if decision.coverage > 0 else 0
        # Mean s_ep / coverage / unknowns
        prev_s = ep_bucket["mean_s_ep"]
        prev_c = ep_bucket["mean_coverage"]
        n = ep_bucket["n_events"]
        ep_bucket["mean_s_ep"] = (
            (prev_s or 0.0) * (n - 1) / n + decision.s_ep / n
        )
        ep_bucket["mean_coverage"] = (
            (prev_c or 0.0) * (n - 1) / n + decision.coverage / n
        )
        for u in decision.unknowns:
            ep_bucket["unknowns"][u] += 1
        # Tight status
        tight = s_tight_status_from_snapshot(snap)
        t_bucket = per_detector_tight.setdefault(identity, Counter())
        t_bucket[tight.get("status", "unknown")] += 1
        # Headline counters
        if "GAP_PCT_UNAVAILABLE" not in decision.unknowns:
            n_with_gap += 1
        if decision.coverage >= 0.99:  # all 5 components present
            n_with_full_ep_coverage += 1
    return {
        "n_total_events": n_total,
        "n_with_gap_pct": n_with_gap,
        "n_with_full_ep_coverage": n_with_full_ep_coverage,
        "n_with_full_ep_coverage_pct": (
            round(100 * n_with_full_ep_coverage / n_total, 2)
            if n_total else 0.0
        ),
        "only_valid_detector": only_valid_detector,
        "per_detector_ep": per_detector_ep,
        "per_detector_tight_status": {k: dict(v) for k, v in per_detector_tight.items()},
    }


def cmd_dry_run(report_session: Optional[str], only_valid_detector: bool) -> int:
    events = load_events(DATA_ROOT)
    if report_session:
        events = [ev for ev in events if session_of(ev) == report_session]
    report = {
        "experiment": "dry-run",
        "report_session_filter": report_session,
        "n_events_loaded": len(events),
        **_coverage_report(events, only_valid_detector=only_valid_detector),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"dry_run_{report_session or 'all'}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"[n5] dry-run -> {out_path}")
    print(
        f"  total events: {report['n_events_loaded']:,}, "
        f"with gap_pct: {report['n_with_gap_pct']:,}, "
        f"with full S_ep coverage: {report['n_with_full_ep_coverage']:,} "
        f"({report['n_with_full_ep_coverage_pct']}%)"
    )
    return 0


def cmd_not_implemented(letter: str) -> int:
    print(
        f"[n5] {EXPERIMENT_LABELS[letter]} -- NOT IMPLEMENTED.\n"
        f"  Two preconditions remain before this verdict is real:\n"
        f"  1. The net_bps writer fix (Wave E). compare_edge needs\n"
        f"     net-of-cost outcomes on disk; today 0 / 863,771 have one.\n"
        f"  2. The S_tight base_episode block (Wave C-2). The S_tight\n"
        f"     score is not scoreable on real data until the\n"
        f"     pullback-depth sequence and atrp_percentile fields are\n"
        f"     threaded into the freeze-scan snapshot.\n"
        f"  Run --experiment dry-run today for the coverage report.",
        file=sys.stderr,
    )
    return 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="N5 experiment runner (wave C-1)")
    p.add_argument("--experiment", choices=["a", "b", "dry-run"], required=True)
    p.add_argument("--report-session", default=None,
                   help="Restrict dry-run to one session (ISO date)")
    p.add_argument("--only-valid-detector", action="store_true",
                   help="Restrict dry-run to events that fired a VALID detector")
    args = p.parse_args(argv)
    if args.experiment == "dry-run":
        return cmd_dry_run(args.report_session, args.only_valid_detector)
    return cmd_not_implemented(args.experiment)


if __name__ == "__main__":
    sys.exit(main())
