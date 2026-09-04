"""W7 — traderlog/adopted/telegram_outbox.py.

The transactional outbox adopted from manas_os: enqueue idempotency, dry-run
send that marks rows sent with no network call, failure path recording the
error text, and the real-send path exercised with the network monkeypatched.
All tests run on disposable init_db() databases (the db.connect production-DB
guard applies; nothing here touches traderlog/data).
"""
from __future__ import annotations

import json
from urllib import parse

import pytest

from traderlog.adopted import telegram_outbox as outbox
from traderlog.db import init_db

IN_FLIGHT = outbox._IN_FLIGHT_SENTINEL


class _FakeConfig:
    """Config stub for send_pending/_send_telegram_message reads."""

    def __init__(self, *, dry_run: bool = True, chat_id: str = "", token: str | None = None):
        self._dry_run = dry_run
        self._chat_id = chat_id
        self._token = token

    def get(self, dotted: str, default=None):
        if dotted == "telegram.dry_run":
            return self._dry_run
        if dotted == "telegram.chat_id":
            return self._chat_id
        return default

    def env(self, name: str, default=None):
        return self._token if name == "TELEGRAM_BOT_TOKEN" else default


def _stub_config(monkeypatch, **kwargs):
    fake = _FakeConfig(**kwargs)
    monkeypatch.setattr(outbox, "config", fake)
    return fake


def _enqueue(conn, kind="trade_event", payload=None, ref_id=None, commit=True):
    payload = payload or {"handle": "alice", "symbol": "FOO", "event": "entry", "kind": kind}
    result = outbox.enqueue(conn, kind, payload, ref_id=ref_id)
    if commit:
        conn.commit()
    return result


def _row(conn, dedupe_key):
    return conn.execute(
        "SELECT * FROM telegram_outbox WHERE dedupe_key = ?", (dedupe_key,)
    ).fetchone()


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------


def test_enqueue_creates_one_row_and_commits_with_caller(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    result = _enqueue(conn, ref_id="pos-1")
    assert result == {"created": True, "dedupe_key": "trade_event:pos-1"}

    row = _row(conn, "trade_event:pos-1")
    assert row is not None
    assert row["state"] == "pending"
    assert row["attempts"] == 0
    assert row["last_error"] is None
    assert row["created_at"]  # NOT NULL per schema
    envelope = json.loads(row["body"])
    assert envelope["kind"] == "trade_event"
    assert envelope["ref_id"] == "pos-1"
    assert envelope["payload"]["symbol"] == "FOO"


def test_enqueue_is_idempotent_per_ref_id(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    assert _enqueue(conn, ref_id="pos-1")["created"] is True
    # Same ref_id, even with a different payload, is the same intended
    # notification -> safe no-op on the second call.
    second = outbox.enqueue(
        conn, "trade_event",
        {"handle": "bob", "symbol": "BAR", "event": "exit", "kind": "trade_event"},
        ref_id="pos-1",
    )
    conn.commit()
    assert second == {"created": False, "dedupe_key": "trade_event:pos-1"}
    total = conn.execute("SELECT COUNT(*) FROM telegram_outbox").fetchone()[0]
    assert total == 1


def test_enqueue_dedupes_by_payload_when_no_ref_id(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    payload = {"handle": "alice", "symbol": "FOO", "event": "entry", "kind": "trade_event"}
    first = _enqueue(conn, payload=payload)
    second = outbox.enqueue(conn, "trade_event", payload)
    conn.commit()
    assert second["created"] is False
    assert second["dedupe_key"] == first["dedupe_key"]
    assert conn.execute("SELECT COUNT(*) FROM telegram_outbox").fetchone()[0] == 1

    outbox.enqueue(
        conn, "trade_event",
        {"handle": "alice", "symbol": "BAR", "event": "entry", "kind": "trade_event"},
    )
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM telegram_outbox").fetchone()[0] == 2


def test_enqueue_rejects_bad_input(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    with pytest.raises(ValueError):
        outbox.enqueue(conn, "", {"a": 1})
    with pytest.raises(ValueError):
        outbox.enqueue(conn, "kind", "not-a-dict")


# ---------------------------------------------------------------------------
# send_pending
# ---------------------------------------------------------------------------


def test_dry_run_send_marks_sent_without_network(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    _stub_config(monkeypatch, dry_run=True)
    # If dry_run ever touched the network this guard fails the test loudly.
    def _network_guard(message):
        raise AssertionError("dry_run must never call the sender")
    monkeypatch.setattr(outbox, "_send_telegram_message", _network_guard)

    _enqueue(conn, ref_id="pos-1")
    _enqueue(conn, ref_id="pos-2")

    result = outbox.send_pending(conn)
    assert set(result["delivered"]) == {"trade_event:pos-1", "trade_event:pos-2"}
    assert result["failed"] == []
    assert result["ambiguous"] == []

    for key in ("trade_event:pos-1", "trade_event:pos-2"):
        row = _row(conn, key)
        assert row["state"] == "sent"
        assert row["last_error"] == "dry_run"
        assert row["sent_at"]  # 'marked sent' carries a timestamp


def test_dry_run_default_comes_from_config(tmp_path, monkeypatch):
    """Without a config stub, telegram.dry_run: true (config.example.yaml)
    means send_pending dry-runs: rows marked sent, no network."""
    conn = init_db(tmp_path / "traderlog.db")
    _enqueue(conn, ref_id="pos-1")

    def _network_guard(message):
        raise AssertionError("network must not be called")
    monkeypatch.setattr(outbox, "_send_telegram_message", _network_guard)
    result = outbox.send_pending(conn)
    assert result["delivered"] == ["trade_event:pos-1"]
    assert _row(conn, "trade_event:pos-1")["last_error"] == "dry_run"


def test_failure_path_records_error_text(tmp_path, monkeypatch):
    conn = init_db(tmp_path / "traderlog.db")
    _stub_config(monkeypatch, dry_run=False, chat_id="CHAT", token="fake-token")

    def _boom(message):
        raise RuntimeError("permission denied")
    monkeypatch.setattr(outbox, "_send_telegram_message", _boom)

    _enqueue(conn, ref_id="pos-1")
    result = outbox.send_pending(conn)
    assert result["failed"] == ["trade_event:pos-1"]
    assert result["delivered"] == []

    row = _row(conn, "trade_event:pos-1")
    assert row["state"] == "failed"
    assert row["last_error"] == "permission denied"
    assert row["attempts"] == 1

    # A failed row is terminal -- the next pass must not re-send it.
    outbox.send_pending(conn)
    row = _row(conn, "trade_event:pos-1")
    assert row["state"] == "failed"


class _FakeResponse:
    """Minimal urllib response sufficient for the Bot API sender."""

    def __init__(self, payload: str, status: int = 200):
        self.status = status
        self._payload = payload.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


def test_real_send_path_posts_via_bot_api_without_network(tmp_path, monkeypatch):
    """The real _send_telegram_message runs end to end; only urlopen is
    faked. Proves: token comes from env(), chat_id from config, the request
    hits the Bot API sendMessage endpoint, and success marks the row sent."""
    conn = init_db(tmp_path / "traderlog.db")
    _stub_config(monkeypatch, dry_run=False, chat_id="CHAT123", token="fake-token")

    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["data"] = req.data.decode("utf-8")
        assert timeout > 0
        return _FakeResponse('{"ok": true, "result": {"message_id": 42}}')

    monkeypatch.setattr(outbox.request, "urlopen", fake_urlopen)

    _enqueue(conn, ref_id="pos-1")
    result = outbox.send_pending(conn)
    assert result["delivered"] == ["trade_event:pos-1"]
    assert result["failed"] == []

    assert captured["url"] == "https://api.telegram.org/botfake-token/sendMessage"
    fields = parse.parse_qs(captured["data"])
    assert fields["chat_id"] == ["CHAT123"]
    text = fields["text"][0]
    assert "FOO" in text and "ENTRY" in text and "alice" in text

    row = _row(conn, "trade_event:pos-1")
    assert row["state"] == "sent"
    assert row["last_error"] is None  # live success clears the error column
    assert row["sent_at"]


def test_real_send_records_telegram_api_error(tmp_path, monkeypatch):
    """Telegram reports API errors (bad token, wrong chat) as HTTP 200 with
    {"ok": false}; the description must become the recorded error text."""
    conn = init_db(tmp_path / "traderlog.db")
    _stub_config(monkeypatch, dry_run=False, chat_id="CHAT", token="fake-token")

    monkeypatch.setattr(
        outbox.request, "urlopen",
        lambda req, timeout: _FakeResponse('{"ok": false, "description": "Unauthorized"}'),
    )
    _enqueue(conn, ref_id="pos-1")
    result = outbox.send_pending(conn)
    assert result["failed"] == ["trade_event:pos-1"]
    row = _row(conn, "trade_event:pos-1")
    assert row["state"] == "failed"
    assert "Unauthorized" in (row["last_error"] or "")


def test_recover_in_flight_marks_delivery_ambiguous(tmp_path, monkeypatch):
    """A row left holding the pre-send marker (crashed process, outcome never
    recorded) is surfaced as delivery_ambiguous -- never silently re-sent."""
    conn = init_db(tmp_path / "traderlog.db")
    _stub_config(monkeypatch, dry_run=True)
    conn.execute(
        "INSERT INTO telegram_outbox (dedupe_key, body, state, attempts, last_error, created_at) "
        "VALUES (?, ?, 'pending', 1, ?, '2026-08-25 10:00:00')",
        ("trade_event:pos-1", '{"kind": "trade_event", "payload": {}}', IN_FLIGHT),
    )
    conn.commit()

    result = outbox.send_pending(conn)
    assert result["ambiguous"] == ["trade_event:pos-1"]
    assert result["delivered"] == []
    row = _row(conn, "trade_event:pos-1")
    assert row["state"] == "delivery_ambiguous"


# ---------------------------------------------------------------------------
# producer helper
# ---------------------------------------------------------------------------


def test_event_for_status_maps_contract_statuses():
    # CONTRACTS.md §3 statuses; only entry/exit-like statuses notify.
    assert outbox.event_for_status("open") == "entry"
    assert outbox.event_for_status("added") == "entry"
    assert outbox.event_for_status("partial") == "entry"
    assert outbox.event_for_status("unclear") == "entry"
    assert outbox.event_for_status("closed") == "exit"
    assert outbox.event_for_status("scratched") == "exit"
    assert outbox.event_for_status("bogus") is None
    assert outbox.event_for_status(None) is None


def test_enqueue_trade_event_payload_and_floor(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")

    # Below the floor: skipped, no row.
    skipped = outbox.enqueue_trade_event(
        conn, handle="alice", symbol="FOO", event="entry",
        ref_id="pos-1", confidence=0.4,
    )
    conn.commit()
    assert skipped["created"] is False
    assert conn.execute("SELECT COUNT(*) FROM telegram_outbox").fetchone()[0] == 0

    # High confidence: one row; payload is handle/symbol/event/kind/post_url.
    created = outbox.enqueue_trade_event(
        conn, handle="alice", symbol="FOO", event="entry",
        post_url="https://x.com/alice/status/1", ref_id="pos-1", confidence=0.9,
    )
    conn.commit()
    assert created == {"created": True, "dedupe_key": "trade_event:pos-1"}
    envelope = json.loads(_row(conn, "trade_event:pos-1")["body"])
    assert envelope["payload"] == {
        "handle": "alice",
        "symbol": "FOO",
        "event": "entry",
        "kind": "trade_event",
        "post_url": "https://x.com/alice/status/1",
    }

    # Same ref_id again is a no-op (idempotent per unique key).
    again = outbox.enqueue_trade_event(
        conn, handle="alice", symbol="FOO", event="entry", ref_id="pos-1", confidence=0.9,
    )
    conn.commit()
    assert again["created"] is False
    assert conn.execute("SELECT COUNT(*) FROM telegram_outbox").fetchone()[0] == 1


def test_enqueue_trade_event_validation(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    with pytest.raises(ValueError):
        outbox.enqueue_trade_event(conn, handle="", symbol="FOO", event="entry")
    with pytest.raises(ValueError):
        outbox.enqueue_trade_event(conn, handle="alice", symbol="", event="entry")
    with pytest.raises(ValueError):
        outbox.enqueue_trade_event(conn, handle="alice", symbol="FOO", event="slam")
    with pytest.raises(ValueError):
        outbox.enqueue_trade_event(
            conn, handle="alice", symbol="FOO", event="entry", confidence=1.4,
        )