"""Unit tests for the Fyers token pre-warning decision logic (defect #8b,
manas_os/design/RELIABILITY_AUDIT_FABLE_2026-07-19.md). token_prewarn.py is
imported directly -- these tests mock fyers_auth/config/telegram, never
hitting a real network or real Fyers token cache."""
from __future__ import annotations

import logging

from manas_os import token_prewarn
from manas_os.providers import fyers_auth


class _ListLogger:
    """Minimal stand-in for the ops logger that records calls instead of
    writing to disk."""

    def __init__(self):
        self.records: list[tuple[str, str]] = []

    def info(self, msg):
        self.records.append(("info", msg))

    def warning(self, msg):
        self.records.append(("warning", msg))

    def exception(self, msg):
        self.records.append(("exception", msg))

    def has(self, level, substring):
        return any(level == lvl and substring in msg for lvl, msg in self.records)


def test_token_ready_true_when_access_token_present(monkeypatch):
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: "tok123")
    assert token_prewarn.token_ready() is True
    assert token_prewarn.should_warn() is False


def test_token_ready_false_when_no_access_token(monkeypatch):
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    assert token_prewarn.token_ready() is False
    assert token_prewarn.should_warn() is True


def test_run_logs_ready_and_does_not_send_when_token_ready(monkeypatch):
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: "tok123")
    sent = []
    logger = _ListLogger()

    rc = token_prewarn.run(logger=logger, sender=lambda msg: sent.append(msg))

    assert rc == 0
    assert sent == []
    assert logger.has("info", "token ready")


def test_run_daily_expiry_case_warns_and_sends_when_telegram_live(monkeypatch):
    """The core defect-#8b case: app_id + secret ARE set (so token_status()
    would report something other than missing_app_id), token is gone, and
    Telegram is configured for live sends -- must log AND send."""
    monkeypatch.setattr(fyers_auth, "app_id", lambda: "app-123")
    monkeypatch.setattr(fyers_auth, "secret_key", lambda: "secret-456")
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(fyers_auth, "token_status", lambda: "missing_token")
    monkeypatch.setattr(token_prewarn, "telegram_live_configured", lambda: True)

    sent = []
    logger = _ListLogger()
    rc = token_prewarn.run(logger=logger, sender=lambda msg: sent.append(msg))

    assert rc == 0
    assert sent == [token_prewarn.WARNING_MESSAGE]
    assert logger.has("warning", "NOT ready")
    assert logger.has("warning", "missing_token")
    assert logger.has("info", "sent via Telegram")


def test_run_not_ready_but_telegram_dry_run_logs_only_no_send(monkeypatch):
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(fyers_auth, "token_status", lambda: "missing_token")
    monkeypatch.setattr(token_prewarn, "telegram_live_configured", lambda: False)

    sent = []
    logger = _ListLogger()
    rc = token_prewarn.run(logger=logger, sender=lambda msg: sent.append(msg))

    assert rc == 0
    assert sent == []
    assert logger.has("info", "log-only")


def test_run_send_failure_is_caught_and_logged_not_raised(monkeypatch):
    """A broken Telegram send must not crash the scheduled task -- it should
    be logged and the run should still complete with rc 0."""
    monkeypatch.setattr(fyers_auth, "get_access_token", lambda: None)
    monkeypatch.setattr(fyers_auth, "token_status", lambda: "missing_token")
    monkeypatch.setattr(token_prewarn, "telegram_live_configured", lambda: True)

    def _boom(msg):
        raise RuntimeError("network down")

    logger = _ListLogger()
    rc = token_prewarn.run(logger=logger, sender=_boom)

    assert rc == 0
    assert logger.has("exception", "Telegram send failed")


def test_telegram_live_configured_requires_token_chat_id_and_not_dry_run(monkeypatch):
    monkeypatch.setattr(
        token_prewarn.config,
        "get",
        lambda key, default=None: {
            "telegram.bot_token": "bot-tok",
            "alerts.telegram_token": "",
            "telegram.chat_id": "chat-1",
            "alerts.telegram_chat_id": "",
            "telegram.dry_run": False,
            "alerts.dry_run": True,
        }.get(key, default),
    )
    assert token_prewarn.telegram_live_configured() is True


def test_telegram_live_configured_false_when_dry_run_true(monkeypatch):
    monkeypatch.setattr(
        token_prewarn.config,
        "get",
        lambda key, default=None: {
            "telegram.bot_token": "bot-tok",
            "telegram.chat_id": "chat-1",
            "telegram.dry_run": True,
        }.get(key, default),
    )
    assert token_prewarn.telegram_live_configured() is False


def test_telegram_live_configured_false_when_chat_id_missing(monkeypatch):
    monkeypatch.setattr(
        token_prewarn.config,
        "get",
        lambda key, default=None: {
            "telegram.bot_token": "bot-tok",
            "telegram.chat_id": "",
            "telegram.dry_run": False,
        }.get(key, default),
    )
    assert token_prewarn.telegram_live_configured() is False
