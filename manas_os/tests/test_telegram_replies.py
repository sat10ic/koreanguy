from manas_os import db
from manas_os.alerts import replies
from manas_os.scanner import candidates as cand
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def _seed_candidate(conn, symbol="TR0"):
    insert_price_ramp(conn, symbol=symbol, n=210, start=100)
    seed_confluent_symbol(conn, symbol=symbol, scan_date=AS_OF)
    conn.execute(
        "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'RISK_ON')",
        (AS_OF,),
    )
    assert cand.run(conn, AS_OF)["status"] == "ok"


def test_take_reply_reuses_setup_decision_and_journal_capture(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_candidate(conn)

        result = replies.handle_reply(conn, "TAKE TR0", AS_OF)
        repeated = replies.handle_reply(conn, "TAKE TR0", AS_OF)

        assert result["ok"] is True
        assert result["decision"] == "taken"
        assert result["trade_id"] is not None
        assert repeated["ok"] is True
        assert "trade_id" not in repeated

        decision = conn.execute(
            "SELECT decision, snapshot_json FROM setup_decisions WHERE scan_date = ? AND symbol = 'TR0'",
            (AS_OF,),
        ).fetchone()
        assert decision["decision"] == "taken"
        assert "TR0" in decision["snapshot_json"]

        trades = conn.execute(
            "SELECT symbol, notes FROM journal_trades WHERE trade_date = ? AND symbol = 'TR0'",
            (AS_OF,),
        ).fetchall()
        assert len(trades) == 1
        assert trades[0]["notes"] == "auto-captured from telegram reply"
    finally:
        conn.close()


def test_skip_reply_captures_skip_reason_without_journal_trade(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_candidate(conn, "TS0")

        result = replies.handle_reply(conn, "SKIP TS0 earnings tomorrow", AS_OF)

        assert result == {"ok": True, "decision": "skipped", "symbol": "TS0"}
        decision = conn.execute(
            "SELECT decision, skip_reason FROM setup_decisions WHERE scan_date = ? AND symbol = 'TS0'",
            (AS_OF,),
        ).fetchone()
        assert dict(decision) == {"decision": "skipped", "skip_reason": "earnings tomorrow"}
        trade_count = conn.execute("SELECT COUNT(*) AS n FROM journal_trades").fetchone()["n"]
        assert trade_count == 0
    finally:
        conn.close()


def test_halt_blocks_entry_pushes_but_not_exit_alerts(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        first = replies.record_push(conn, AS_OF, "TH0")
        duplicate = replies.record_push(conn, AS_OF, "TH0")
        halted = replies.handle_reply(conn, "/halt no entries", AS_OF)
        blocked = replies.record_push(conn, AS_OF, "TH1")

        assert first["ok"] is True
        assert duplicate == {"ok": False, "reason": "duplicate_push", "symbol": "TH0", "kind": "entry"}
        assert halted == {"ok": True, "entries_halted": True}
        assert blocked == {"ok": False, "reason": "entries_halted", "symbol": "TH1", "kind": "entry"}
        assert replies.entries_halted(conn) is True
        assert replies.exit_alerts_allowed(conn) is True
    finally:
        conn.close()
