from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.link import (
    LinkValidationError,
    propose_link,
    route_link_proposal,
    validate_link_proposal,
)
from traderlog.llm.provider import ProviderResult
from traderlog.llm.reconcile import (
    _write_position,
    apply_verified_reconciliation,
    reconcile_thread,
    validate_reconciliation,
)


def _post(conn, post_id: str, handle: str, text: str, *, reply_to: str | None = None) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, 0, now_iso()),
    )
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
        "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            post_id, handle, post_id if reply_to is None else reply_to, reply_to,
            f"2026-08-{1 if post_id == 'root' else 2:02d}T10:00:00+00:00",
            f"2026-08-{1 if post_id == 'root' else 2:02d}T15:30:00+05:30",
            text, f"https://x.com/{handle}/status/{post_id}", now_iso(), 0, now_iso(),
        ),
    )


def _open_position(conn, *, handle: str = "alice", symbol: str = "ALPHA") -> str:
    _post(conn, "root", handle, f"LONG {symbol} at 100")
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        ("root", "trade_event", 1.0, json.dumps([symbol]), 0, now_iso()),
    )
    conn.commit()
    apply_verified_reconciliation(
        conn,
        "root",
        {
            "symbol": symbol,
            "status": "open",
            "entries": [{"price": 100, "post_id": "root"}],
            "adds": [], "stop": None, "targets": [], "exits": [],
            "net_result_pct": None, "holding_days": None, "confidence": 1.0,
            "unresolved": [], "evidence": {"symbol": "root", "entries[0].price": "root"},
        },
    )
    return conn.execute("SELECT position_id FROM positions WHERE root_post_id='root'").fetchone()[0]


def _candidate(conn, *, handle: str = "alice", symbol: str = "ALPHA") -> None:
    _post(conn, "link-post", handle, f"Booked {symbol} at 120")
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        ("link-post", "trade_event", 1.0, json.dumps([symbol]), 0, now_iso()),
    )
    conn.commit()


def _proposal(position_id: str, confidence: float = 0.8) -> dict:
    return {
        "post_id": "link-post",
        "proposed_position_id": position_id,
        "proposed_event": {"kind": "exit", "price": 120, "qty_pct": 100},
        "confidence": confidence,
        "reasoning": "same handle and symbol; the post states a full booking",
        "alternatives": ["could refer to a different same-day trade"],
    }


@pytest.fixture
def linked_db(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    pos_id = _open_position(conn)
    _candidate(conn)
    yield conn, pos_id
    conn.close()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda proposal: proposal["proposed_event"].update(kind="entry"), "kind"),
        (lambda proposal: proposal["proposed_event"].update(price=float("nan")), "finite"),
        (lambda proposal: proposal.update(confidence=1.01), "confidence"),
        (lambda proposal: proposal.update(extra="no"), "unknown"),
    ],
)
def test_link_validation_rejects_adversarial_proposals_without_writes(linked_db, mutate, message):
    conn, pos_id = linked_db
    proposal = _proposal(pos_id)
    mutate(proposal)

    with pytest.raises(LinkValidationError, match=message):
        validate_link_proposal(conn, proposal)

    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("gate", "message"),
    [
        ("cross_handle", "handle"),
        ("cross_symbol", "symbol"),
        ("missing_class", "classified"),
        ("not_trade_event", "trade_event"),
        ("reply", "standalone"),
        ("already_linked", "already backs"),
        ("closed_position", "open-like"),
    ],
)
def test_link_validation_rejects_candidate_boundary_violations_without_writes(linked_db, gate, message):
    conn, pos_id = linked_db
    if gate == "cross_handle":
        conn.execute("INSERT INTO traders (handle,active,is_mock,ingested_at) VALUES ('mallory',1,0,?)", (now_iso(),))
        conn.execute("UPDATE posts SET handle='mallory' WHERE post_id='link-post'")
    elif gate == "cross_symbol":
        conn.execute("UPDATE post_class SET symbols=? WHERE post_id='link-post'", (json.dumps(["BETA"]),))
    elif gate == "missing_class":
        conn.execute("DELETE FROM post_class WHERE post_id='link-post'")
    elif gate == "not_trade_event":
        conn.execute("UPDATE post_class SET kind='breadth' WHERE post_id='link-post'")
    elif gate == "reply":
        conn.execute("UPDATE posts SET conversation_id='root', in_reply_to='root' WHERE post_id='link-post'")
    elif gate == "already_linked":
        conn.execute(
            "INSERT INTO position_events (position_id,post_id,kind,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (pos_id, "link-post", "exit", "2026-08-02T15:30:00+05:30", 0, now_iso()),
        )
    else:
        conn.execute("UPDATE positions SET status='closed' WHERE position_id=?", (pos_id,))
    conn.commit()
    event_count_before = conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0]

    with pytest.raises(LinkValidationError, match=message):
        validate_link_proposal(conn, _proposal(pos_id))

    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == event_count_before


def test_propose_link_uses_smart_complete_prompt_and_audited_provider_result(linked_db):
    conn, pos_id = linked_db
    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(content=_proposal(pos_id), model="test/smart", provider="test", run_id=7)

    proposal = propose_link(conn, "link-post", chat_fn=chat_fn)

    assert proposal.proposed_position_id == pos_id
    assert calls[0]["tier"] == "smart"
    assert calls[0]["task"] == "link"
    assert calls[0]["json_schema"] is True
    assert "LINK PROPOSAL" in calls[0]["system"]


@pytest.mark.parametrize("gate", ["reply", "already_linked"])
def test_propose_link_rejects_invalid_candidate_before_provider_call(linked_db, gate):
    conn, pos_id = linked_db
    if gate == "reply":
        conn.execute("UPDATE posts SET conversation_id='root', in_reply_to='root' WHERE post_id='link-post'")
    else:
        conn.execute(
            "INSERT INTO position_events (position_id,post_id,kind,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (pos_id, "link-post", "exit", "2026-08-02T15:30:00+05:30", 0, now_iso()),
        )
    conn.commit()
    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        raise AssertionError("invalid candidate must not reach smart tier")

    with pytest.raises(LinkValidationError):
        propose_link(conn, "link-post", chat_fn=chat_fn)
    assert calls == []


def test_point_seventy_nine_queues_exact_proposal_without_position_mutation(linked_db):
    conn, pos_id = linked_db
    proposal = _proposal(pos_id, 0.79)

    routed = route_link_proposal(conn, proposal)

    assert routed.status == "open"
    assert routed.applied is False
    queued = conn.execute("SELECT * FROM review_queue").fetchone()
    assert queued["status"] == "open"
    assert queued["resolved_by"] is None and queued["resolved_at"] is None
    assert json.loads(queued["proposed_json"]) == proposal
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0


def test_point_eighty_applies_and_duplicate_routing_is_idempotent(linked_db):
    conn, pos_id = linked_db
    proposal = _proposal(pos_id, 0.8)

    first = route_link_proposal(conn, proposal)
    second = route_link_proposal(conn, proposal)

    assert first.status == second.status == "accepted"
    assert first.applied is second.applied is True
    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 1
    audit = conn.execute("SELECT resolved_by,resolved_at FROM review_queue").fetchone()
    assert audit["resolved_by"] == "auto" and audit["resolved_at"] is not None
    position = conn.execute("SELECT status,state_json,evidence_json FROM positions WHERE position_id=?", (pos_id,)).fetchone()
    assert position["status"] == "closed"
    assert json.loads(position["state_json"])["exits"][-1]["price"] == 120.0
    assert json.loads(position["evidence_json"])["exits[0].price"] == "link-post"


def test_accepted_link_survives_unchanged_future_reconciliation_without_provider_call(linked_db):
    conn, pos_id = linked_db
    route_link_proposal(conn, _proposal(pos_id, 0.8))

    result = reconcile_thread(
        conn,
        "root",
        chat_fn=lambda **_: (_ for _ in ()).throw(AssertionError("unchanged link must not call provider")),
    )

    assert result.status == "closed"
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE position_id=? AND post_id='link-post'", (pos_id,)).fetchone()[0] == 1


def test_pre_entry_link_is_rejected_without_writes(linked_db):
    conn, pos_id = linked_db
    conn.execute(
        "UPDATE posts SET ts_utc='2026-07-31T10:00:00+00:00', ts_ist='2026-07-31T15:30:00+05:30' WHERE post_id='link-post'"
    )
    conn.commit()

    with pytest.raises(LinkValidationError, match="before position opened"):
        route_link_proposal(conn, _proposal(pos_id, 0.8))

    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0


def test_writer_anchors_open_and_close_times_to_cited_posts_not_post_order(linked_db):
    conn, pos_id = linked_db
    conn.execute(
        "UPDATE posts SET ts_utc='2026-07-31T10:00:00+00:00', ts_ist='2026-07-31T15:30:00+05:30' WHERE post_id='link-post'"
    )
    conn.commit()
    posts = conn.execute("SELECT * FROM posts ORDER BY ts_utc ASC").fetchall()
    result = validate_reconciliation(
        {
            "symbol": "ALPHA", "status": "closed",
            "entries": [{"price": 100, "post_id": "root"}],
            "adds": [], "stop": None, "targets": [],
            "exits": [{"price": 120, "qty_pct": 100, "post_id": "link-post"}],
            "net_result_pct": None, "holding_days": None, "confidence": 0.8,
            "unresolved": [],
            "evidence": {
                "symbol": "root", "entries[0].price": "root",
                "exits[0].price": "link-post", "exits[0].qty_pct": "link-post",
            },
        },
        posts,
    )
    _write_position(
        conn, handle="alice", root_post_id="root", result=result, posts=posts,
        thread_hash_value="writer-timestamp-test", model="test", is_mock=0,
    )

    row = conn.execute("SELECT opened_at,closed_at FROM positions WHERE position_id=?", (pos_id,)).fetchone()
    assert row["opened_at"] == "2026-08-01T15:30:00+05:30"
    assert row["closed_at"] == "2026-07-31T15:30:00+05:30"
