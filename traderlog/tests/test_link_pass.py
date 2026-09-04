"""Disposable-database tests for the W3 runtime producer pass (run_link_pass).

Every test pins one audited contract of the pass: structural idempotency (a
second pass over processed data makes zero provider calls and zero writes),
rejected posts are never re-queued, ineligible posts never reach the provider,
and per-post failures are isolated without ever raising outward.  Every
database here is a disposable tmp_path one; the production DB is never opened.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.link import run_link_pass
from traderlog.llm.provider import ProviderResult
from traderlog.llm.reconcile import apply_verified_reconciliation
from traderlog.tests.test_link import _candidate, _open_position, _post, _proposal


def _open_position_as(conn, root_post_id: str, *, handle: str, symbol: str) -> str:
    """_open_position for a second trader; the shared helper hardcodes 'root'."""
    _post(conn, root_post_id, handle, f"LONG {symbol} at 100")
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        (root_post_id, "trade_event", 1.0, json.dumps([symbol]), 0, now_iso()),
    )
    conn.commit()
    apply_verified_reconciliation(
        conn,
        root_post_id,
        {
            "symbol": symbol,
            "status": "open",
            "entries": [{"price": 100, "post_id": root_post_id}],
            "adds": [], "stop": None, "targets": [], "exits": [],
            "net_result_pct": None, "holding_days": None, "confidence": 1.0,
            "unresolved": [],
            "evidence": {"symbol": root_post_id, f"entries[0].price": root_post_id},
        },
    )
    return conn.execute(
        "SELECT position_id FROM positions WHERE root_post_id=?", (root_post_id,)
    ).fetchone()[0]


def _candidate_as(conn, post_id: str, *, handle: str, symbol: str) -> None:
    """_candidate for a second trader; the shared helper hardcodes 'link-post'."""
    _post(conn, post_id, handle, f"Booked {symbol} at 120")
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        (post_id, "trade_event", 1.0, json.dumps([symbol]), 0, now_iso()),
    )
    conn.commit()


def _proposal_for(post_id: str, position_id: str, confidence: float = 0.8) -> dict:
    """_proposal for an arbitrary post; the shared helper hardcodes 'link-post'."""
    return {
        "post_id": post_id,
        "proposed_position_id": position_id,
        "proposed_event": {"kind": "exit", "price": 120, "qty_pct": 100},
        "confidence": confidence,
        "reasoning": "same handle and symbol; the post states a full booking",
        "alternatives": ["could refer to a different same-day trade"],
    }


@pytest.fixture
def pass_db(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    position_id = _open_position(conn)
    _candidate(conn)
    yield conn, position_id
    conn.close()


def test_below_floor_queues_once_then_second_pass_is_a_no_op(pass_db):
    conn, position_id = pass_db
    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(content=_proposal(position_id, 0.79), model="test/smart", provider="test", run_id=1)

    first = run_link_pass(conn, chat_fn=chat_fn)

    assert (first.eligible, first.queued, first.applied, first.failures) == (1, 1, 0, ())
    assert len(calls) == 1
    row = conn.execute("SELECT kind,status,resolved_by,resolved_at FROM review_queue").fetchone()
    assert row["kind"] == "link_event"
    assert row["status"] == "open"
    assert row["resolved_by"] is None and row["resolved_at"] is None
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0

    calls.clear()
    second = run_link_pass(conn, chat_fn=chat_fn)

    assert (second.eligible, second.queued, second.applied, second.failures) == (0, 0, 0, ())
    assert calls == []
    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0


def test_at_floor_applies_once_then_second_pass_is_a_no_op(pass_db):
    conn, position_id = pass_db
    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(content=_proposal(position_id, 0.8), model="test/smart", provider="test", run_id=1)

    first = run_link_pass(conn, chat_fn=chat_fn)

    assert (first.eligible, first.queued, first.applied, first.failures) == (1, 0, 1, ())
    assert len(calls) == 1
    row = conn.execute("SELECT status,resolved_by,resolved_at FROM review_queue").fetchone()
    assert row["status"] == "accepted"
    assert row["resolved_by"] == "auto" and row["resolved_at"] is not None
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 1

    calls.clear()
    second = run_link_pass(conn, chat_fn=chat_fn)

    assert (second.eligible, second.queued, second.applied, second.failures) == (0, 0, 0, ())
    assert calls == []
    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 1


def test_rejected_post_is_never_requeued(pass_db):
    conn, position_id = pass_db

    def chat_fn(**kwargs):
        return ProviderResult(content=_proposal(position_id, 0.79), model="test/smart", provider="test", run_id=1)

    first = run_link_pass(conn, chat_fn=chat_fn)
    assert first.queued == 1

    conn.execute(
        "UPDATE review_queue SET status='rejected', resolved_by='test', resolved_at=?",
        (now_iso(),),
    )
    conn.commit()

    calls: list[dict] = []

    def chat_fn_2(**kwargs):
        calls.append(kwargs)
        return ProviderResult(content=_proposal(position_id, 0.79), model="test/smart", provider="test", run_id=2)

    second = run_link_pass(conn, chat_fn=chat_fn_2)

    assert (second.eligible, second.queued, second.applied, second.failures) == (0, 0, 0, ())
    assert calls == []
    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == 1
    assert conn.execute("SELECT status FROM review_queue").fetchone()[0] == "rejected"
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0


@pytest.mark.parametrize(
    "gate",
    [
        "reply",
        "non_trade_event",
        "empty_symbols",
        "null_symbols",
        "no_open_like_position",
        "already_backs_event",
        "existing_open_review",
    ],
)
def test_ineligible_posts_never_reach_the_provider(pass_db, gate):
    conn, position_id = pass_db
    if gate == "reply":
        conn.execute("UPDATE posts SET conversation_id='root', in_reply_to='root' WHERE post_id='link-post'")
    elif gate == "non_trade_event":
        conn.execute("UPDATE post_class SET kind='breadth' WHERE post_id='link-post'")
    elif gate == "empty_symbols":
        conn.execute("UPDATE post_class SET symbols='[]' WHERE post_id='link-post'")
    elif gate == "null_symbols":
        conn.execute("UPDATE post_class SET symbols=NULL WHERE post_id='link-post'")
    elif gate == "no_open_like_position":
        conn.execute("UPDATE positions SET status='closed' WHERE position_id=?", (position_id,))
    elif gate == "already_backs_event":
        conn.execute(
            "INSERT INTO position_events (position_id,post_id,kind,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
            (position_id, "link-post", "exit", "2026-08-02T15:30:00+05:30", 0, now_iso()),
        )
    else:  # existing_open_review
        conn.execute(
            "INSERT INTO review_queue (kind,post_id,position_id,question,proposed_json,confidence,status,is_mock,ingested_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("link_event", "link-post", position_id, "queued earlier?", "{}", 0.5, "open", 0, now_iso()),
        )
    conn.commit()

    review_before = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    events_before = conn.execute("SELECT COUNT(*) FROM position_events").fetchone()[0]

    def chat_fn(**kwargs):
        raise AssertionError("ineligible post must not reach the provider")

    result = run_link_pass(conn, chat_fn=chat_fn)

    assert (result.eligible, result.queued, result.applied, result.failures) == (0, 0, 0, ())
    assert conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0] == review_before
    assert conn.execute("SELECT COUNT(*) FROM position_events").fetchone()[0] == events_before


def test_per_post_failure_is_isolated_and_the_pass_never_raises(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    try:
        _open_position(conn)  # alice / ALPHA
        _candidate(conn)      # alice's eligible candidate post 'link-post'
        bob_position = _open_position_as(conn, "root2", handle="bob", symbol="BETA")
        _candidate_as(conn, "link-post2", handle="bob", symbol="BETA")
        calls: list[dict] = []

        def chat_fn(**kwargs):
            calls.append(kwargs)
            if kwargs["ref_id"] == "link-post":
                raise RuntimeError("smart tier exploded")
            return ProviderResult(content=_proposal_for("link-post2", bob_position, 0.8), model="test/smart", provider="test", run_id=2)

        result = run_link_pass(conn, chat_fn=chat_fn)  # must not raise

        assert result.eligible == 2
        assert result.applied == 1 and result.queued == 0
        assert len(result.failures) == 1
        assert result.failures[0][0] == "link-post"
        assert "smart tier exploded" in result.failures[0][1]
        assert len(calls) == 2  # both eligible posts reached the provider
        assert conn.execute("SELECT COUNT(*) FROM review_queue WHERE post_id='link-post'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM review_queue WHERE post_id='link-post2' AND status='accepted'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM position_events WHERE post_id='link-post2'").fetchone()[0] == 1
    finally:
        conn.close()
