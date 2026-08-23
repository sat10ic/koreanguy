from __future__ import annotations

import json
from pathlib import Path

from traderlog.checks.__main__ import _mock_data_notice
from traderlog.checks import runner
from traderlog.checks.runner import CheckResult, NOT_BUILT, PASS, _counts, check_parse
from traderlog.db import init_db, now_iso


def test_mock_only_notice_preserves_the_existing_warning():
    state = {"showing_mock_data": True, "counts": {"posts_real": 0}}

    assert _mock_data_notice(state) == (
        "  NOTE: database contains MOCK data. Nothing here has been ingested."
    )


def test_mixed_real_and_mock_notice_does_not_deny_live_ingest():
    state = {"showing_mock_data": True, "counts": {"posts_real": 12}}

    assert _mock_data_notice(state) == (
        "  NOTE: database also contains MOCK data; real posts have been ingested. "
        "Mock rows are excluded from live ingest validation."
    )


def test_check_counts_expose_real_post_evidence_separately_from_mock_posts(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    conn.executemany(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        [("real", 1, 0, now_iso()), ("mock", 1, 1, now_iso())],
    )
    conn.executemany(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,fetched_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        [
            ("1", "real", now_iso(), now_iso(), now_iso(), 0, now_iso()),
            ("2", "mock", now_iso(), now_iso(), now_iso(), 1, now_iso()),
        ],
    )
    conn.commit()

    assert _counts(conn)["posts_real"] == 1
    assert _counts(conn)["posts_mock"] == 1
    conn.close()


def _write_golden_fixtures(root: Path, count: int) -> None:
    golden = root / "tests" / "golden"
    golden.mkdir(parents=True)
    for index in range(count):
        (golden / f"fixture_{index}.json").write_text("{}\n", encoding="utf-8")


def test_partial_golden_corpus_runs_tests_but_remains_w2_not_built(monkeypatch, tmp_path: Path):
    _write_golden_fixtures(tmp_path, 1)
    calls = []
    monkeypatch.setattr(runner, "_ROOT", tmp_path)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs))
        or type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )

    result = runner.check_golden()

    target = runner._GOLDEN_FIXTURE_TARGET
    assert result == CheckResult("golden", NOT_BUILT, f"1/{target} fixtures verified")
    assert len(calls) == 1
    assert runner._current_wave([CheckResult("ingest", PASS), result]) == "W2"


def test_full_golden_corpus_passes_after_its_fixture_tests(monkeypatch, tmp_path: Path):
    target = runner._GOLDEN_FIXTURE_TARGET
    _write_golden_fixtures(tmp_path, target)
    monkeypatch.setattr(runner, "_ROOT", tmp_path)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Proc", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )

    assert runner.check_golden() == CheckResult(
        "golden", PASS, f"{target} fixtures, prompts current"
    )


def test_golden_reports_stale_when_a_fixture_predates_a_prompt_edit(tmp_path, monkeypatch):
    """A prompt edit must make its fixtures report stale, not silently pass.

    This is the anti-drift mechanism's actual job. Before 2026-08-23 the check
    compared fixtures only against their own stored expectations, so a model
    could edit a prompt and every fixture would still pass while testing against
    a prompt that no longer existed.
    """
    _write_golden_fixtures(tmp_path, runner._GOLDEN_FIXTURE_TARGET)
    stale = tmp_path / "tests" / "golden" / "stale_one.json"
    stale.write_text(
        json.dumps({"prompt_versions": {"reconcile": "0000deadbeef"}}), encoding="utf-8"
    )
    monkeypatch.setattr(runner, "_ROOT", tmp_path)
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Proc", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )

    result = runner.check_golden()
    assert result.status.startswith("stale_prompts_")
    assert "stale_one" in result.detail


def _insert_position(conn, *, is_mock: int, confidence: float | None = None) -> None:
    handle = f"trader_{is_mock}_{confidence is not None}"
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, is_mock, now_iso()),
    )
    conn.execute(
        "INSERT INTO positions "
        "(position_id,handle,symbol,root_post_id,status,confidence,state_json,evidence_json,"
        "is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            f"position_{is_mock}_{confidence is not None}",
            handle,
            "RATEGAIN",
            "root",
            "open",
            confidence,
            "{}",
            "{}",
            is_mock,
            now_iso(),
        ),
    )
    conn.commit()


def test_parse_check_keeps_mock_only_positions_w2_not_built(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_position(conn, is_mock=1)

    assert check_parse(conn) == CheckResult(
        "parse", NOT_BUILT, "0 real positions reconciled; 1 mock-only positions (W2)"
    )
    conn.close()


def test_parse_check_passes_once_a_real_position_is_reconciled(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_position(conn, is_mock=0)

    assert check_parse(conn) == CheckResult("parse", PASS, "1 real positions, all cited")
    conn.close()


def test_parse_check_still_rejects_uncited_mock_positions_before_readiness(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_position(conn, is_mock=1, confidence=0.7)

    result = check_parse(conn)

    assert result.status.startswith("fail")
    assert "confidence but no evidence" in result.status
    conn.close()
