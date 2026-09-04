"""Intraday live loop — Stage 1 (Task #21).

Architecture of record: manas_os/design/LIVE_LOOP_FABLE.md (Fable, 2026-07-06)
and its T4.1 restatement in the build plan. This package is the backend-only
Fyers-WS-driven FSM that turns tonight's armed_list (already built by
alerts.telegram_engine — the single writer of trigger/stop/qty; this package
never recomputes risk) into TRIGGERED -> ALERTED -> CONFIRM_PENDING ->
CONFIRMED/EXPIRED transitions, paper-gated Telegram pushes, and a replay
harness that drives the identical FSM code with zero network calls.

PAPER MODE ONLY. agents.telegram_live stays false; nothing here flips it.
"""
