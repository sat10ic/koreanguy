from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from traderlog.api import app as api_app
from traderlog.db import connect, init_db
from traderlog.llm.link import route_link_proposal
from traderlog.tests.test_link import _candidate, _open_position, _proposal


@pytest.fixture
def api_db(tmp_path: Path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    position_id = _open_position(conn)
    _candidate(conn)
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    yield conn, position_id
    conn.close()


def test_review_acceptance_delegates_apply_and_is_explicitly_idempotent(api_db):
    conn, position_id = api_db
    queued = route_link_proposal(conn, _proposal(position_id, 0.79))

    accepted = api_app.resolve_review(queued.id, "accepted")
    repeated = api_app.resolve_review(queued.id, "accepted")

    assert accepted == {"ok": True, "id": queued.id, "status": "accepted", "applied": True, "already_resolved": False}
    assert repeated == {"ok": True, "id": queued.id, "status": "accepted", "applied": True, "already_resolved": True}
    assert conn.execute("SELECT status FROM review_queue WHERE id=?", (queued.id,)).fetchone()[0] == "accepted"
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 1


def test_review_rejection_only_resolves_queue_and_missing_is_explicit(api_db):
    conn, position_id = api_db
    queued = route_link_proposal(conn, _proposal(position_id, 0.79))

    rejected = api_app.resolve_review(queued.id, "rejected")
    repeated = api_app.resolve_review(queued.id, "rejected")

    assert rejected["applied"] is False and repeated["already_resolved"] is True
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0
    with pytest.raises(HTTPException, match="no review item"):
        api_app.resolve_review(9999, "accepted")


def test_review_acceptance_rolls_back_queue_resolution_when_reconcile_rejects(api_db, monkeypatch):
    conn, position_id = api_db
    queued = route_link_proposal(conn, _proposal(position_id, 0.79))

    def fail_apply(*_args, **_kwargs):
        raise ValueError("simulated reconcile rejection")

    monkeypatch.setattr(api_app, "apply_accepted_link", fail_apply)
    with pytest.raises(ValueError, match="simulated"):
        api_app.resolve_review(queued.id, "accepted")

    assert conn.execute("SELECT status FROM review_queue WHERE id=?", (queued.id,)).fetchone()[0] == "open"
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0
