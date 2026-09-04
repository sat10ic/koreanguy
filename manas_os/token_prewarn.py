"""Fyers token pre-warning check — 08:45 IST scheduled task.

Defect #8b (manas_os/design/RELIABILITY_AUDIT_FABLE_2026-07-19.md): the Fyers
token expires daily at 06:00 IST, and the first the user hears about it is
usually a degraded panel after 09:15 when it's already too late to paste a
fresh token before the open. This script runs 30 minutes ahead of the open
(08:45 IST, registered as the "ManasOS-TokenPrewarn" scheduled task — see
manas_os/register_token_prewarn.ps1) and, if the token is not ready, writes
an ops log line and — only when Telegram is configured for live sends
(bot_token + chat_id set, dry_run false) — pushes a warning so the user can
reconnect before the market opens.

Reads token state via manas_os.providers.fyers_auth directly, NOT via the
running API/app.py (app.py is intentionally not imported or touched here —
this script must work even if the API process is down or between restarts).

Safe to run by hand: python -m manas_os.token_prewarn
"""
from __future__ import annotations

from manas_os import config
from manas_os.ops_logging import configure_ops_logger
from manas_os.providers import fyers_auth

WARNING_MESSAGE = "Fyers token expires/expired — paste today's token before 9:15"


def token_ready() -> bool:
    """True when a live Fyers access token is available right now.

    Delegates to fyers_auth.get_access_token() — the same source of truth
    /api/fyers/status uses (app.py:4569) — but imported directly so this
    check never depends on app.py or the API process being up.
    """
    return bool(fyers_auth.get_access_token())


def should_warn() -> bool:
    """Warn whenever the token is not ready. Covers both the daily-expiry
    case (app_id/secret already set, token gone — the common 6am ambush)
    and the rarer case where app_id/secret themselves are unset."""
    return not token_ready()


def telegram_live_configured() -> bool:
    """True only when Telegram is set up for *live* sends: bot_token AND
    chat_id present, and dry_run explicitly false. Mirrors
    app.py::_telegram_config / the /api/live/readiness telegram_configured
    check so this script never fires a real send the operator hasn't
    opted into."""
    bot_token = str(
        config.get("telegram.bot_token", config.get("alerts.telegram_token", "")) or ""
    ).strip()
    chat_id = str(
        config.get("telegram.chat_id", config.get("alerts.telegram_chat_id", "")) or ""
    ).strip()
    dry_run = bool(config.get("telegram.dry_run", config.get("alerts.dry_run", True)))
    return bool(bot_token) and bool(chat_id) and not dry_run


def send_warning(sender=None) -> None:
    """Send WARNING_MESSAGE via the shared telegram_engine sender.

    `sender` is injectable for tests; production calls import
    telegram_engine lazily so this module has zero import-time dependency
    on the alerts package (matches the "if configured" contract — a repo
    with no telegram section configured must not even import the engine
    at prewarn-decision time, only at send time).
    """
    if sender is None:
        from manas_os.alerts.telegram_engine import get_sender

        sender = get_sender()
    sender(WARNING_MESSAGE)


def run(logger=None, sender=None) -> int:
    """Core decision logic, isolated from __main__ so tests can call it
    directly with mocked logger/sender. Returns 0 on a completed check
    (token ready OR not-ready-but-handled), non-zero only if the check
    itself blew up unexpectedly — Task Scheduler failure history should
    reflect "the prewarn script broke", not "the token was expired"
    (that's the expected, common case this script exists to surface)."""
    logger = logger or configure_ops_logger("token_prewarn")

    if token_ready():
        logger.info("token_prewarn: Fyers token ready — no action")
        return 0

    status = fyers_auth.token_status()
    logger.warning(
        f"token_prewarn: Fyers token NOT ready (status={status}) — {WARNING_MESSAGE}"
    )

    if telegram_live_configured():
        try:
            send_warning(sender=sender)
            logger.info("token_prewarn: warning sent via Telegram")
        except Exception as exc:  # noqa: BLE001 — never let a send failure look like a crash
            logger.exception(f"token_prewarn: Telegram send failed: {exc}")
    else:
        logger.info(
            "token_prewarn: Telegram not live-configured (dry_run or missing "
            "bot_token/chat_id) — log-only, no send attempted"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        configure_ops_logger("token_prewarn").exception("token_prewarn crashed")
        raise
