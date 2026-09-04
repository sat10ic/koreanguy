"""Fixture-only tests for the N5 walk-forward experiment runner."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

import unidesk.run_n5_experiment as runner
from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.calendar import from_sessions


UTC = timezone.utc
CA_HASH = "c" * 64


def _event(
    symbol: str,
    session: date,
    *,
    candidate_bps: float | None,
    baseline_bps: float | None,
    letter: str = "b",
) -> ResearchEvent:
    return ResearchEvent(
        event_id=f"{symbol}:{session.isoformat()}",
        candidate_id=f"{symbol}:{session.isoformat()}",
        symbol=symbol,
        timestamp=datetime(session.year, session.month, session.day, 12, tzinfo=UTC),
        snapshot={
            "ca_table_hash": CA_HASH,
            "experiment_arms": {letter: {"candidate": True, "baseline": True}},
        },
        config_hash="fixture-config",
        research_schema_version="research-event-v1",
        outcome_labels={
            "experiment_net_bps": {
                letter: {"candidate": candidate_bps, "baseline": baseline_bps},
            },
        },
    )


def _fixture_events(*, null_signal: bool = False, letter: str = "b") -> tuple[list[ResearchEvent], tuple[date, ...]]:
    sessions = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(160))
    events = []
    for index, session in enumerate(sessions):
        candidate = (10.0 if index % 2 == 0 else -10.0) if null_signal else 100.0 + (index % 3)
        baseline = -20.0 if null_signal else 10.0
        events.append(_event(f"S{index}", session, candidate_bps=candidate, baseline_bps=baseline, letter=letter))
    return events, sessions


def test_fixture_run_uses_test_folds_embargo_and_aligned_sessions():
    events, sessions = _fixture_events()
    duplicate_session = sessions[69]  # inside the first default test fold
    events.append(_event("S68", duplicate_session, candidate_bps=101.0, baseline_bps=10.0))

    result = runner.evaluate_experiment(
        events,
        from_sessions(sessions),
        letter="b",
        label="fixture EP",
        min_n=10,
    )

    assert result.edge_verdict.verdict == "KEEP_CANDIDATE"
    assert result.promoted is True
    assert result.candidate_sessions == result.baseline_sessions
    assert result.coverage["n_embargoed"] == 1
    assert result.coverage["n_test_window"] == 64
    assert result.ca_table_hash == CA_HASH
    payload = result.to_dict()
    assert {"hypothesis", "arms", "n", "coverage", "dsr", "verdict", "date", "ca_table_hash"} <= payload.keys()


def test_missing_net_bps_fails_closed_instead_of_becoming_zero():
    events, sessions = _fixture_events()
    events[70] = _event("S70", sessions[70], candidate_bps=None, baseline_bps=10.0)

    with pytest.raises(ContractError, match="net_bps"):
        runner.evaluate_experiment(events, from_sessions(sessions), letter="b", label="fixture", min_n=10)


def test_null_signal_fails_dsr_promotion_gate():
    events, sessions = _fixture_events(null_signal=True)

    result = runner.evaluate_experiment(
        events,
        from_sessions(sessions),
        letter="b",
        label="fixture null",
        min_n=10,
    )

    assert result.edge_verdict.verdict == "KEEP_CANDIDATE"
    assert result.promoted is False
    assert result.verdict == "NO_EDGE_DSR"


def test_cli_writes_error_and_returns_nonzero_when_calendar_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "OUT_DIR", tmp_path)
    monkeypatch.setattr(runner, "load_events", lambda _root: [])

    code = runner.cmd_experiment("b", None, "fixture", None)

    assert code == 1
    payload = json.loads((tmp_path / "experiment_b_all.json").read_text(encoding="utf-8"))
    assert payload["status"].startswith("error:")


def test_cli_writes_a_fixture_verdict(monkeypatch, tmp_path):
    events, sessions = _fixture_events()
    calendar_path = tmp_path / "sessions.json"
    calendar_path.write_text(json.dumps({"sessions": [session.isoformat() for session in sessions]}), encoding="utf-8")
    monkeypatch.setattr(runner, "OUT_DIR", tmp_path)
    monkeypatch.setattr(runner, "load_events", lambda _root: events)

    code = runner.cmd_experiment("b", None, "fixture", str(calendar_path))

    assert code == 0
    payload = json.loads((tmp_path / "experiment_b_all.json").read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["edge_verdict"] == "KEEP_CANDIDATE"


def test_cli_experiment_a_exits_zero_with_real_verdict(monkeypatch, tmp_path):
    """Work-order acceptance, verbatim: '--experiment a exits 0 on fixtures
    with a real verdict'. Arm letter b is covered above; this pins a."""
    events, sessions = _fixture_events(letter="a")
    calendar_path = tmp_path / "sessions.json"
    calendar_path.write_text(json.dumps({"sessions": [session.isoformat() for session in sessions]}), encoding="utf-8")
    monkeypatch.setattr(runner, "OUT_DIR", tmp_path)
    monkeypatch.setattr(runner, "load_events", lambda _root: events)

    code = runner.cmd_experiment("a", None, "fixture a", str(calendar_path))

    assert code == 0
    payload = json.loads((tmp_path / "experiment_a_all.json").read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["verdict"] in ("KEEP_CANDIDATE", "REJECT_CANDIDATE", "NO_EDGE_DSR")
    assert payload["verdict"] == "KEEP_CANDIDATE", "the fixture's real signal must promote"
