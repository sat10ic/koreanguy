from __future__ import annotations

import json
from pathlib import Path

from traderlog.checks import runner


def _record(**overrides):
    record = {
        "id": "attr-w3-ui-001",
        "completed_at": "2026-08-23",
        "wave": "W3",
        "deliverable": "review UI",
        "role": "executor",
        "model": "unknown",
        "host_tool": "unknown",
        "identity_basis": "unknown",
        "scope": "FEED review controls",
        "files": ["ui/src/screens/Feed.jsx"],
        "completion_report": "handoffs/HANDOFF_W3_link_COMPLETED.md",
        "status": "completed",
        "verification_status": "unverified",
        "notes_limitations": "Exact implementation-model identity was not documented.",
    }
    record.update(overrides)
    return record


def _write_case(tmp_path: Path, records: list[dict], report_text: str) -> None:
    (tmp_path / "MODEL_ATTRIBUTION.md").write_text("# Attribution\n", encoding="utf-8")
    ledger = tmp_path / "MODEL_WORK_LOG.jsonl"
    ledger.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    report = tmp_path / "handoffs" / "HANDOFF_W3_link_COMPLETED.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(report_text, encoding="utf-8")


def test_attribution_check_accepts_matching_append_only_ledger(tmp_path: Path, monkeypatch):
    record = _record()
    _write_case(tmp_path, [record], "# Completed\n\n## Attribution\n\nAttribution-ID: attr-w3-ui-001\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert runner.check_attribution() == runner.CheckResult("attribution", runner.PASS, "1 records, 1 completed handoffs")


def test_attribution_check_rejects_duplicate_ids(tmp_path: Path, monkeypatch):
    record = _record()
    _write_case(tmp_path, [record, record], "Attribution-ID: attr-w3-ui-001\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert "duplicate id" in runner.check_attribution().status


def test_attribution_check_rejects_malformed_jsonl_and_invalid_enum(tmp_path: Path, monkeypatch):
    _write_case(tmp_path, [_record(role="not-a-role")], "Attribution-ID: attr-w3-ui-001\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert "invalid role" in runner.check_attribution().status
    (tmp_path / "MODEL_WORK_LOG.jsonl").write_text("not json\n", encoding="utf-8")
    assert "malformed JSONL" in runner.check_attribution().status


def test_attribution_check_accepts_historical_date_only_but_rejects_timezone_less_datetime(tmp_path: Path, monkeypatch):
    _write_case(tmp_path, [_record()], "Attribution-ID: attr-w3-ui-001\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert runner.check_attribution().status == runner.PASS
    _write_case(
        tmp_path,
        [_record(completed_at="2026-08-23T10:00:00")],
        "Attribution-ID: attr-w3-ui-001\n",
    )
    assert "completed_at has no timezone" in runner.check_attribution().status


def test_attribution_check_rejects_completed_handoff_without_an_id(tmp_path: Path, monkeypatch):
    _write_case(tmp_path, [_record()], "# Completed\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert "completed handoff has no attribution ID" in runner.check_attribution().status


def test_attribution_check_rejects_unknown_completed_handoff_id(tmp_path: Path, monkeypatch):
    _write_case(
        tmp_path,
        [_record()],
        "Attribution-ID: attr-w3-ui-001\nAttribution-ID: attr-not-in-ledger\n",
    )
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    assert "unknown attribution id" in runner.check_attribution().status


def test_attribution_check_rejects_report_path_mismatch_and_missing_required_field(tmp_path: Path, monkeypatch):
    record = _record(completion_report="handoffs/OTHER_COMPLETED.md")
    _write_case(tmp_path, [record], "Attribution-ID: attr-w3-ui-001\n")
    monkeypatch.setattr(runner, "_ATTRIBUTION_DOC", tmp_path / "MODEL_ATTRIBUTION.md")
    monkeypatch.setattr(runner, "_ATTRIBUTION_LOG", tmp_path / "MODEL_WORK_LOG.jsonl")
    monkeypatch.setattr(runner, "_HANDOFFS_DIR", tmp_path / "handoffs")
    monkeypatch.setattr(runner, "_ROOT", tmp_path)

    result = runner.check_attribution()
    assert result.status.startswith("fail")
    assert "report-path mismatch" in result.status

    record.pop("host_tool")
    _write_case(tmp_path, [record], "Attribution-ID: attr-w3-ui-001\n")
    assert "missing required fields" in runner.check_attribution().status
