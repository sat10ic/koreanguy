from __future__ import annotations

import json

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES ('trader', 1, 0, ?)",
        (now_iso(),),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    test_conn = connect(path)
    yield test_conn
    test_conn.close()


def _post(conn, post_id: str, ts: str, *, conversation_id: str | None = None,
          in_reply_to: str | None = None, kind: str | None = None,
          confidence: float | None = None) -> None:
    conn.execute(
        "INSERT INTO posts "
        "(post_id, handle, conversation_id, in_reply_to, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (post_id, "trader", conversation_id or post_id, in_reply_to, ts, ts, post_id,
         f"https://x.com/trader/status/{post_id}", now_iso(), 0, now_iso()),
    )
    if kind is not None:
        conn.execute(
            "INSERT INTO post_class (post_id, kind, confidence, is_mock, ingested_at) VALUES (?,?,?,?,?)",
            (post_id, kind, confidence, 0, now_iso()),
        )


def _position(conn, position_id: str, *, confidence: float | None, opened_at: str,
              unresolved: list[str] | None = None) -> None:
    conn.execute(
        "INSERT INTO positions "
        "(position_id, handle, symbol, root_post_id, status, opened_at, confidence, state_json, evidence_json, unresolved_json, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (position_id, "trader", position_id, position_id, "open", opened_at, confidence,
         "{}", "{}", json.dumps(unresolved or []), 0, now_iso()),
    )


def test_feed_filters_before_limit_excludes_null_confidence_and_readds_root(api_db):
    _post(api_db, "root", "2026-08-20T09:00:00+00:00", kind="trade_event", confidence=0.8)
    _post(
        api_db, "reply", "2026-08-20T11:00:00+00:00", conversation_id="root",
        in_reply_to="root", kind="trade_event", confidence=0.9,
    )
    _post(api_db, "null-conf", "2026-08-20T12:00:00+00:00", kind="trade_event")
    _post(api_db, "other-kind", "2026-08-20T13:00:00+00:00", kind="breadth", confidence=1.0)
    api_db.commit()

    result = api_app.feed(kind="trade_event", min_confidence=0.0, limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["root", "reply"]
    assert all(post["confidence"] is not None for post in result["posts"])


def test_feed_supports_unclassified_before_limit(api_db):
    _post(api_db, "unclassified", "2026-08-20T09:00:00+00:00")
    _post(api_db, "classified", "2026-08-20T12:00:00+00:00", kind="noise", confidence=1.0)
    api_db.commit()

    result = api_app.feed(kind="unclassified", limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["unclassified"]


def test_feed_supports_unresolved_before_limit(api_db):
    _post(api_db, "unresolved", "2026-08-20T09:00:00+00:00", kind="trade_event", confidence=0.8)
    _post(api_db, "resolved", "2026-08-20T12:00:00+00:00", kind="trade_event", confidence=0.8)
    _position(api_db, "unresolved-position", confidence=0.8, opened_at="2026-08-20", unresolved=["stop missing"])
    _position(api_db, "resolved-position", confidence=0.8, opened_at="2026-08-20")
    api_db.executemany(
        "INSERT INTO position_events (position_id, post_id, kind, stated_at, is_mock, ingested_at) VALUES (?,?,?,?,?,?)",
        [
            ("unresolved-position", "unresolved", "entry", "2026-08-20T09:00:00+00:00", 0, now_iso()),
            ("resolved-position", "resolved", "entry", "2026-08-20T12:00:00+00:00", 0, now_iso()),
        ],
    )
    api_db.commit()

    result = api_app.feed(unresolved=True, limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["unresolved"]


def test_positions_min_confidence_filters_before_limit_and_excludes_null(api_db):
    _position(api_db, "low", confidence=0.8, opened_at="2026-08-20")
    _position(api_db, "null", confidence=None, opened_at="2026-08-21")
    api_db.commit()

    result = api_app.positions(min_confidence=0.0, limit=1)

    assert [position["position_id"] for position in result["positions"]] == ["low"]
