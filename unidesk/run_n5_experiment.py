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

Experiments ``a`` and ``b`` fail closed until their source events carry
pre-computed arm outcomes, a single CA-table hash, and an explicit exchange
calendar.  The runner never fills any of those missing facts with placeholders.

Usage (from repo root)::

    .venv-orderflow/Scripts/python.exe unidesk/run_n5_experiment.py --experiment dry-run
    .venv-orderflow/Scripts/python.exe unidesk/run_n5_experiment.py --experiment a --calendar-sessions sessions.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.contracts.base import ContractError, require_float
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.calendar import TradingCalendar, from_sessions
from unidesk.momentum.scoring._snapshot_bindings import (
    s_tight_status_from_snapshot, score_ep_from_snapshot,
)
from unidesk.research.event_store import load_events, session_of
from unidesk.research.experiments import BookStats, EdgeVerdict, Trade, compare_edge
from unidesk.research.leakage import embargo_overlapping_events
from unidesk.research.significance import block_bootstrap_ci, deflated_sharpe_ratio
from unidesk.research.walkforward import expanding_folds, session_in

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


_DSR_PROMOTION_FLOOR = 0.90
_N_TRIALS = 9


def _stats_dict(stats: BookStats) -> dict:
    return {
        "n": stats.n,
        "net_expectancy_bps": stats.net_expectancy_bps,
        "win_rate": stats.win_rate,
        "profit_factor": stats.profit_factor,
        "avg_win_bps": stats.avg_win_bps,
        "avg_loss_bps": stats.avg_loss_bps,
    }


def _experiment_value(event: ResearchEvent, letter: str, arm: str) -> float:
    """Read one pre-computed, net-of-cost arm outcome without inventing it."""
    values = event.outcome_labels.get("experiment_net_bps")
    if not isinstance(values, dict):
        raise ContractError(f"{event.event_id}: experiment_net_bps is missing")
    by_experiment = values.get(letter)
    if not isinstance(by_experiment, dict) or arm not in by_experiment:
        raise ContractError(f"{event.event_id}: {letter}/{arm} net_bps is missing")
    value = by_experiment[arm]
    if value is None:
        raise ContractError(f"{event.event_id}: {letter}/{arm} net_bps is unavailable")
    return require_float(value, f"{event.event_id}:{letter}:{arm}:net_bps")


def _in_arm(event: ResearchEvent, letter: str, arm: str) -> bool:
    arms = event.snapshot.get("experiment_arms")
    if not isinstance(arms, dict) or not isinstance(arms.get(letter), dict):
        raise ContractError(f"{event.event_id}: experiment arm metadata is missing for {letter}")
    value = arms[letter].get(arm)
    if not isinstance(value, bool):
        raise ContractError(f"{event.event_id}: {letter}/{arm} arm flag must be boolean")
    return value


def _ca_table_hash(events: Sequence[ResearchEvent]) -> str:
    hashes = {event.snapshot.get("ca_table_hash") for event in events}
    if None in hashes or not hashes or not all(
        isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())
        for value in hashes
    ):
        raise ContractError("every test-window event needs a 64-character ca_table_hash")
    if len(hashes) != 1:
        raise ContractError("test-window events span multiple ca_table_hash values")
    return next(iter(hashes))


@dataclass(frozen=True)
class ExperimentRun:
    """Fixture- and archive-ready N5 result with its coverage and PIT basis."""

    hypothesis: str
    edge_verdict: EdgeVerdict
    dsr: float
    ci90: tuple[float, float]
    promoted: bool
    verdict: str
    coverage: dict
    candidate_sessions: tuple[str, ...]
    baseline_sessions: tuple[str, ...]
    ca_table_hash: str
    date: str

    def to_dict(self) -> dict:
        return {
            "hypothesis": self.hypothesis,
            "arms": {
                "candidate": _stats_dict(self.edge_verdict.candidate_stats),
                "baseline": _stats_dict(self.edge_verdict.baseline_stats),
            },
            "n": {
                "candidate": self.edge_verdict.candidate_stats.n,
                "baseline": self.edge_verdict.baseline_stats.n,
            },
            "coverage": self.coverage,
            "dsr": round(self.dsr, 4),
            "dsr_floor": _DSR_PROMOTION_FLOOR,
            "ci90": [round(self.ci90[0], 4), round(self.ci90[1], 4)],
            "verdict": self.verdict,
            "edge_verdict": self.edge_verdict.verdict,
            "promoted": self.promoted,
            "date": self.date,
            "ca_table_hash": self.ca_table_hash,
            "notes": list(self.edge_verdict.notes),
        }


def evaluate_experiment(
    events: Sequence[ResearchEvent],
    calendar: TradingCalendar,
    *,
    letter: str,
    label: str,
    min_n: int = 30,
) -> ExperimentRun:
    """Evaluate pre-computed arms only on walk-forward test-fold events.

    The function intentionally refuses to reconstruct a baseline, treat a
    missing outcome as zero, or infer a calendar from event dates.  Those would
    turn incomplete archive data into a research claim.
    """
    if letter not in EXPERIMENT_LABELS:
        raise ContractError(f"unknown experiment {letter!r}")
    folds = expanding_folds(calendar)
    test_events: list[ResearchEvent] = []
    for event in events:
        session = date.fromisoformat(session_of(event))
        if calendar.get(session) is None:
            raise ContractError(f"{event.event_id}: event session is absent from supplied calendar")
        if any(session_in(session, fold.test_start, fold.test_end) for fold in folds):
            test_events.append(event)
    if not test_events:
        raise ContractError("no events fall inside walk-forward test folds")

    ca_hash = _ca_table_hash(test_events)
    kept, embargoed = embargo_overlapping_events(test_events, calendar)
    candidate_by_session: dict[str, list[Trade]] = {}
    baseline_by_session: dict[str, list[Trade]] = {}
    for event in kept:
        session = session_of(event)
        if _in_arm(event, letter, "candidate"):
            candidate_by_session.setdefault(session, []).append(Trade(
                symbol=event.symbol,
                entry_session=session,
                net_bps=_experiment_value(event, letter, "candidate"),
            ))
        if _in_arm(event, letter, "baseline"):
            baseline_by_session.setdefault(session, []).append(Trade(
                symbol=event.symbol,
                entry_session=session,
                net_bps=_experiment_value(event, letter, "baseline"),
            ))

    aligned_sessions = tuple(sorted(set(candidate_by_session) & set(baseline_by_session)))
    if not aligned_sessions:
        raise ContractError("candidate and baseline arms have no aligned test sessions")
    candidate_book = [trade for session in aligned_sessions for trade in candidate_by_session[session]]
    baseline_book = [trade for session in aligned_sessions for trade in baseline_by_session[session]]
    if not candidate_book or not baseline_book:
        raise ContractError("candidate and baseline books must both contain aligned trades")

    edge_verdict = compare_edge(candidate_book, baseline_book, label=label, min_n=min_n)
    candidate_returns = [trade.net_bps for trade in candidate_book]
    dsr = deflated_sharpe_ratio(candidate_returns, n_trials=_N_TRIALS)
    ci90 = block_bootstrap_ci(candidate_returns, ci=0.90)
    promoted = edge_verdict.verdict == "KEEP_CANDIDATE" and dsr >= _DSR_PROMOTION_FLOOR
    verdict = edge_verdict.verdict if edge_verdict.verdict != "KEEP_CANDIDATE" or promoted else "NO_EDGE_DSR"
    return ExperimentRun(
        hypothesis=label,
        edge_verdict=edge_verdict,
        dsr=dsr,
        ci90=ci90,
        promoted=promoted,
        verdict=verdict,
        coverage={
            "n_input": len(events),
            "n_test_window": len(test_events),
            "n_embargoed": len(embargoed),
            "n_kept_after_embargo": len(kept),
            "n_candidate_selected": sum(len(rows) for rows in candidate_by_session.values()),
            "n_baseline_selected": sum(len(rows) for rows in baseline_by_session.values()),
            "n_aligned_sessions": len(aligned_sessions),
        },
        candidate_sessions=aligned_sessions,
        baseline_sessions=aligned_sessions,
        ca_table_hash=ca_hash,
        date=max(aligned_sessions),
    )


def _load_calendar(path: Optional[str]) -> TradingCalendar:
    if path is None:
        raise ContractError("--calendar-sessions is required; event dates are not an exchange calendar")
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    sessions = raw.get("sessions") if isinstance(raw, dict) else raw
    if not isinstance(sessions, list):
        raise ContractError("calendar JSON must be a list or an object with a sessions list")
    if any(not isinstance(value, str) for value in sessions):
        raise ContractError("calendar sessions must be ISO date strings")
    return from_sessions([date.fromisoformat(value) for value in sessions])


def cmd_experiment(
    letter: str,
    report_session: Optional[str],
    label: str,
    calendar_sessions: Optional[str],
) -> int:
    """Run an N5 experiment or write a failure artifact and return non-zero."""
    result: dict
    try:
        events = load_events(DATA_ROOT)
        if report_session:
            events = [event for event in events if session_of(event) == report_session]
        result = {"status": "completed", "experiment": letter, **evaluate_experiment(
            events, _load_calendar(calendar_sessions), letter=letter, label=label,
        ).to_dict()}
        exit_code = 0
    except Exception as exc:
        result = {"status": f"error: {exc}", "experiment": letter, "hypothesis": label, "verdict": None}
        exit_code = 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"experiment_{letter}_{report_session or 'all'}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"[n5] {label} -> {out_path}")
    print(f"  Verdict: {result.get('verdict', 'N/A')}")
    return exit_code


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="N5 experiment runner (wave C-1)")
    p.add_argument("--experiment", choices=["a", "b", "dry-run"], required=True)
    p.add_argument("--report-session", default=None,
                   help="Restrict the loaded events to one session (ISO date)")
    p.add_argument("--calendar-sessions", default=None,
                   help="JSON exchange-calendar sessions required for experiments a/b")
    p.add_argument("--only-valid-detector", action="store_true",
                   help="Restrict dry-run to events that fired a VALID detector")
    args = p.parse_args(argv)
    if args.experiment == "dry-run":
        return cmd_dry_run(args.report_session, args.only_valid_detector)
    label = EXPERIMENT_LABELS[args.experiment]
    return cmd_experiment(args.experiment, args.report_session, label, args.calendar_sessions)


if __name__ == "__main__":
    sys.exit(main())
