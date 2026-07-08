from manas_os import db
from manas_os.alerts import live_fsm, telegram_engine
from manas_os.tests.conftest import AS_OF


def _seed_armed(conn, symbol="ACME", trigger=101.0, stop=96.0, qty=100):
    telegram_engine.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO armed_list "
        "(armed_date, symbol, trigger, stop, qty, setup_family, rank, ttl_date) "
        "VALUES (?, ?, ?, ?, ?, 'catalyst', 1, '2026-07-01')",
        (AS_OF, symbol, trigger, stop, qty),
    )
    conn.commit()


def test_live_fsm_replay_confirms_once_and_dedupes_second_replay(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        events = [
            {"type": "tick", "symbol": "ACME", "ts": f"{AS_OF}T09:20:00", "price": 100.5},
            {"type": "tick", "symbol": "ACME", "ts": f"{AS_OF}T09:25:00", "price": 101.2},
            {"type": "tick", "symbol": "ACME", "ts": f"{AS_OF}T09:25:00", "price": 101.2},
            {"type": "confirm", "symbol": "ACME", "ts": f"{AS_OF}T09:30:00", "price": 101.4},
        ]

        first = live_fsm.replay_events(conn, AS_OF, events)
        second = live_fsm.replay_events(conn, AS_OF, events)
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
    finally:
        conn.close()


def test_live_fsm_replay_expires_after_25_minute_ttl(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_armed(conn)
        events = [
            {"type": "tick", "symbol": "ACME", "ts": f"{AS_OF}T09:25:00", "price": 101.2},
            {"type": "expire", "ts": f"{AS_OF}T09:49:59"},
            {"type": "expire", "ts": f"{AS_OF}T09:50:00"},
        ]

        result = live_fsm.replay_events(conn, AS_OF, events)
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

