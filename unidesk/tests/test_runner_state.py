from __future__ import annotations

import json

from unidesk.checks import runner


def test_write_state_blocks_only_failures(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "STATE.json"
    monkeypatch.setattr(runner, "_STATE", state_path)

    runner.write_state(
        {
            "attribution": "6 records, 2 completed handoffs",
            "contracts": "12 contracts import",
            "leakage": "not_built_yet",
            "broken_check": "FAIL: deliberate regression fixture",
        }
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["blocked_on"] == ["broken_check: FAIL: deliberate regression fixture"]
