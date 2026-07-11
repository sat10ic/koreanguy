"""Unit tests for manas_os.alerts.live_fsm -- one test per transition, plus
the idempotency guarantee the whole live loop depends on.

Extended for Task #21 Stage 1: the W4.1 stub fired ALERTED on any tick that
merely crossed the trigger. LIVE_LOOP_FABLE.md §2.2/T4.1 require a fuller
live-confirmation bundle (first-15m holds OR-low/VWAP + gap-fill<=33% +
projected RVOL>=2) before ALERTED, a genuine confirm-time revalidation
(outside the pre-committed zone -> refuse), the per-day regime push cap, and
the /halt kill-switch (never blocking exit alerts). These tests replace the
old "any trigger cross alerts immediately" assertions with the new gated
behavior and add coverage for the new gates.
"""
from __future__ import annotations

from manas_os import db
from manas_os.alerts import live_fsm, replies as telegram_replies, telegram_engine
from manas_os.live import telegram_paper
from manas_os.tests.conftest import AS_OF


def _seed_armed(conn, symbol="ACME", trigger=101.0, stop=96.0, qty=100, rank=1):
    telegram_engine.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO armed_list "
        "(armed_date, symbol, trigger, stop, qty, setup_family, rank, ttl_date) "
        "VALUES (?, ?, ?, ?, ?, 'catalyst', ?, '2026-07-01')",
        (AS_OF, symbol, trigger, stop, qty, rank),
    )
    conn.commit()


def _confirmation_ok(price: float, ts: str) -> dict:
    return {
        "price": price, "ts": ts, "in_first_15m_complete": True,
        "holds_or_low_vwap": True, "gap_fill_pct": 0.2, "rvol_projected": 2.5,
    }


def test_trigger_cross_alone_does_not_alert_without_confirmation_bundle(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        r = live_fsm.on_tick(conn, AS_OF, {"symbol": "ACME", "ts": f"{AS_OF}T09:20:00", "price": 101.2})
        assert r["applied"] is True
        assert r["to_state"] == "TRIGGERED"
        state = live_fsm.states(conn, AS_OF)[0]
        assert state["state"] == "TRIGGERED"
    finally:
        conn.close()


def test_live_fsm_replay_confirms_once_and_dedupes_second_replay(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        events = [
            {"type": "tick", "symbol": "ACME", "ts": f"{AS_OF}T09:20:00", "price": 100.5,
             "in_first_15m_complete": False, "holds_or_low_vwap": False, "gap_fill_pct": None, "rvol_projected": None},
            {"type": "tick", "symbol": "ACME", **_confirmation_ok(101.2, f"{AS_OF}T09:25:00")},
            {"type": "tick", "symbol": "ACME", **_confirmation_ok(101.2, f"{AS_OF}T09:25:00")},
            {"type": "confirm", "symbol": "ACME", "ts": f"{AS_OF}T09:30:00", "price": 101.4},
        ]

        first = live_fsm.replay_events(conn, AS_OF, events, regime_mode="RISK_ON")
        second = live_fsm.replay_events(conn, AS_OF, events, regime_mode="RISK_ON")
        state = live_fsm.states(conn, AS_OF)[0]
        transitions = live_fsm.transitions(conn, AS_OF)

        assert first["alert_count"] == 1
        assert second["transitions_created"] == 0
        assert second["alert_count"] == 1
        assert state["state"] == "CONFIRMED"
        assert [t["to_state"] for t in transitions] == [
            "ARMED",
            "TRIGGERED",
            "ALERTED",
            "CONFIRM_PENDING",
            "CONFIRMED",
        ]
        assert state["paper_mode"] == 1

        # 1-push-per-symbol-per-day: exactly one entry push was logged despite
        # the duplicate tick and the full second replay pass.
        pushes = conn.execute(
            "SELECT COUNT(*) AS n FROM live_pushes_log WHERE trade_date=? AND symbol='ACME'", (AS_OF,)
        ).fetchone()
        assert pushes["n"] == 1
    finally:
        conn.close()


def test_live_fsm_replay_expires_after_25_minute_ttl(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        events = [
            {"type": "tick", "symbol": "ACME", **_confirmation_ok(101.2, f"{AS_OF}T09:25:00")},
            {"type": "expire", "ts": f"{AS_OF}T09:49:59"},
            {"type": "expire", "ts": f"{AS_OF}T09:50:00"},
        ]

        result = live_fsm.replay_events(conn, AS_OF, events, regime_mode="RISK_ON")
        state = live_fsm.states(conn, AS_OF)[0]
        transitions = live_fsm.transitions(conn, AS_OF)

        assert result["alert_count"] == 1
        assert state["state"] == "EXPIRED"
        assert state["expires_at"] == f"{AS_OF}T09:50"
        assert [t["to_state"] for t in transitions] == [
            "ARMED",
            "TRIGGERED",
            "ALERTED",
            "EXPIRED",
        ]
    finally:
        conn.close()


def test_confirm_outside_zone_refuses_and_never_confirms(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn, trigger=100.0)  # zone = [100, 100.6] at the default 0.6% width
        live_fsm.on_tick(conn, AS_OF, {"symbol": "ACME", "ts": f"{AS_OF}T09:20:00", "price": 100.2})
        live_fsm.on_tick(conn, AS_OF, {"symbol": "ACME", **_confirmation_ok(100.3, f"{AS_OF}T09:35:00")})
        r = live_fsm.on_confirm(conn, AS_OF, {"symbol": "ACME", "ts": f"{AS_OF}T09:40:00", "price": 102.5})
        assert r["ok"] is False
        assert r["reason"] == "outside_zone"
        assert r["state"] == "EXPIRED_MOVED"
        state = live_fsm.states(conn, AS_OF)[0]
        assert state["state"] == "EXPIRED_MOVED"
    finally:
        conn.close()


def test_regime_cap_blocks_the_nth_plus_one_qualifying_alert(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        # DEFENSIVE caps pushes at 1 (telegram_engine.DIGEST_CAPS).
        _seed_armed(conn, symbol="CAPA", trigger=100.0, rank=1)
        _seed_armed(conn, symbol="CAPB", trigger=200.0, rank=2)
        live_fsm.on_tick(conn, AS_OF, {"symbol": "CAPA", "ts": f"{AS_OF}T09:20:00", "price": 100.5})
        live_fsm.on_tick(conn, AS_OF, {"symbol": "CAPB", "ts": f"{AS_OF}T09:21:00", "price": 200.5})

        first = live_fsm.on_tick(conn, AS_OF, {"symbol": "CAPA", **_confirmation_ok(100.3, f"{AS_OF}T09:35:00")},
                                  regime_mode="DEFENSIVE")
        second = live_fsm.on_tick(conn, AS_OF, {"symbol": "CAPB", **_confirmation_ok(200.3, f"{AS_OF}T09:36:00")},
                                   regime_mode="DEFENSIVE")

        assert first["applied"] is True
        assert first["to_state"] == "ALERTED"
        assert second["applied"] is False
        assert second["reason"] == "regime_cap_reached"
        states_by_symbol = {s["symbol"]: s["state"] for s in live_fsm.states(conn, AS_OF)}
        assert states_by_symbol["CAPA"] == "ALERTED"
        assert states_by_symbol["CAPB"] == "TRIGGERED"
    finally:
        conn.close()


def test_halt_blocks_new_alerts_but_exit_alerts_still_push(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        live_fsm.on_tick(conn, AS_OF, {"symbol": "ACME", "ts": f"{AS_OF}T09:20:00", "price": 101.2})
        telegram_replies.set_halt(conn, True, reason="/halt test")

        r = live_fsm.on_tick(conn, AS_OF, {"symbol": "ACME", **_confirmation_ok(101.3, f"{AS_OF}T09:35:00")})
        assert r == {"applied": False, "reason": "entries_halted", "symbol": "ACME"}
        assert live_fsm.states(conn, AS_OF)[0]["state"] == "TRIGGERED"

        exit_push = telegram_paper.push_exit_alert(conn, AS_OF, "ACME", "EXIT ACME stop hit")
        assert exit_push["ok"] is True
        assert exit_push["paper"] is True
    finally:
        conn.close()


def test_unarmed_symbol_tick_is_a_clean_noop(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        live_fsm.ensure_schema(conn)
        r = live_fsm.on_tick(conn, AS_OF, {"symbol": "NEVER_ARMED", "ts": f"{AS_OF}T09:20:00", "price": 1.0})
        assert r == {"applied": False, "reason": "terminal_or_not_armed", "symbol": "NEVER_ARMED"}
    finally:
        conn.close()
