from manas_os import db
from manas_os.agents import _shared as agents_shared
from manas_os.alerts import telegram_engine
from manas_os.scanner import candidates as cand
from manas_os.tests.conftest import AS_OF, insert_price_ramp, seed_confluent_symbol


def test_telegram_digest_caps_and_persists_armed_list(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        for i in range(6):
            symbol = f"TG{i}"
            insert_price_ramp(conn, symbol=symbol, n=210, start=100 + i)
            seed_confluent_symbol(conn, symbol=symbol, scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        scan = cand.run(conn, AS_OF)
        assert scan["status"] == "ok"
        assert scan["rows"] > telegram_engine.DIGEST_CAPS["SELECTIVE"]

        result = telegram_engine.run(conn, AS_OF)
        digest = telegram_engine.build_digest(conn, AS_OF)

        assert result == {"status": "ok", "armed_count": telegram_engine.DIGEST_CAPS["SELECTIVE"]}
        assert digest["market_mode"] == "SELECTIVE"
        assert len(digest["digest"]) <= telegram_engine.DIGEST_CAPS["SELECTIVE"]
        assert "and " in digest["summary"] and " names refused" in digest["summary"]

        armed = conn.execute(
            "SELECT symbol, trigger, stop, qty, setup_family, rank, ttl_date "
            "FROM armed_list WHERE armed_date = ? ORDER BY rank",
            (AS_OF,),
        ).fetchall()
        assert [r["symbol"] for r in armed] == [c["symbol"] for c in digest["digest"]]
        for row, card in zip(armed, digest["digest"], strict=True):
            assert row["trigger"] == card["entry"]
            assert row["stop"] == card["stop"]
            assert row["qty"] == card["suggested_qty"]
            assert row["setup_family"] == card["setup_family"]
            assert row["rank"] == card["rank"]
            assert row["ttl_date"] == "2026-07-01"

        run = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs WHERE stage = ?",
            (telegram_engine.STAGE,),
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == len(digest["digest"])
    finally:
        conn.close()


def test_telegram_send_digest_dry_run_renders_single_message(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        for i in range(6):
            symbol = f"TD{i}"
            insert_price_ramp(conn, symbol=symbol, n=210, start=100 + i)
            seed_confluent_symbol(conn, symbol=symbol, scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        scan = cand.run(conn, AS_OF)
        assert scan["status"] == "ok"

        sent = []
        result = telegram_engine.send_digest(
            conn,
            AS_OF,
            dry_run=True,
            sender=lambda message: sent.append(message),
        )

        assert result["status"] == "ok"
        assert result["dry_run"] is True
        # RELIABILITY_AUDIT_2026-07-19 #8 / outbox: dry_run delivers to the
        # paper log and marks the outbox row 'sent' -- the state machine is
        # identical in paper and live, so "sent" reflects paper delivery,
        # not a real network call.
        assert result["sent"] is True
        assert sent == []
        assert result["armed_count"] == telegram_engine.DIGEST_CAPS["SELECTIVE"]
        assert "Manas armed list |" in result["message"]
        assert "Armed: 3/3" in result["message"]
        assert "Refusals:" in result["message"]

        run = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = ? ORDER BY rowid DESC LIMIT 1",
            (telegram_engine.STAGE,),
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == telegram_engine.DIGEST_CAPS["SELECTIVE"]
        assert "dry_run=True" in run["detail"]
    finally:
        conn.close()


def test_telegram_send_failure_leaves_digest_ok_and_outbox_row_pending_for_retry(tmp_path):
    """RELIABILITY_AUDIT_2026-07-19 #8: a Telegram send failure must never
    roll back or re-flag the (already idempotent, already committed)
    armed-list build -- it is purely a retryable delivery concern now,
    tracked in telegram_outbox, not a pipeline-stage failure. This replaces
    the old assertion that a send failure marked the whole stage 'fail'
    (that was the bug: it meant a transient Telegram outage looked like a
    digest-build failure and offered no durable retry)."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        insert_price_ramp(conn, symbol="TF0", n=210, start=100)
        seed_confluent_symbol(conn, symbol="TF0", scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'RISK_ON')",
            (AS_OF,),
        )
        assert cand.run(conn, AS_OF)["status"] == "ok"

        def fail_sender(_message):
            raise RuntimeError("telegram down")

        result = telegram_engine.send_digest(conn, AS_OF, dry_run=False, sender=fail_sender)

        assert result["status"] == "ok"
        assert result["sent"] is False
        run = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = ? ORDER BY rowid DESC LIMIT 1",
            (telegram_engine.STAGE,),
        ).fetchone()
        assert run["status"] == "ok"
        assert run["rows_affected"] == 1

        outbox_row = conn.execute(
            "SELECT state, attempts, last_error FROM telegram_outbox WHERE kind = 'telegram_digest' "
            "AND alert_key = ?",
            (f"telegram_digest:{AS_OF}",),
        ).fetchone()
        assert outbox_row is not None
        assert outbox_row["state"] == "pending"
        assert outbox_row["attempts"] == 1
        assert "telegram down" in outbox_row["last_error"]

        # Retrying (a later scheduler run calling send_digest again for the
        # same night, once the backoff window has elapsed) must not create a
        # second outbox row and must retry delivery of the existing one --
        # once the transient failure clears, it is finally marked sent.
        from datetime import datetime, timedelta, timezone
        later = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)).isoformat(timespec="seconds")
        result2 = telegram_engine.send_digest(conn, AS_OF, dry_run=False, sender=lambda _m: None, now=later)
        assert result2["sent"] is True
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM telegram_outbox WHERE kind = 'telegram_digest'"
        ).fetchone()["n"]
        assert count == 1
    finally:
        conn.close()


def test_telegram_digest_includes_watchlist_section(tmp_path):
    """SHIP-1 #10: digest text carries a Watchlist section with PROMOTE/DEMOTE
    lines and the hard-near-miss count, seeded from agent_watchlist."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        insert_price_ramp(conn, symbol="TW0", n=210, start=100)
        seed_confluent_symbol(conn, symbol="TW0", scan_date=AS_OF)
        conn.execute(
            "INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        assert cand.run(conn, AS_OF)["status"] == "ok"

        agents_shared.ensure_agent_tables(conn)
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'TW0', 'PASSED', 'PROMOTE', 'HOLD', 'chair verdict SKIP -> TAKE', 0)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'TW1', 'PASSED', 'DEMOTE', 'PROMOTE', 'chair verdict TAKE -> SKIP', 0)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'TW2', 'NEAR_MISS(hard:regime)', 'HOLD', NULL, 'hard gate failure: regime', 0)",
            (AS_OF,),
        )
        conn.commit()

        digest = telegram_engine.build_digest(conn, AS_OF)
        assert digest["watchlist"]["near_miss_hard_count"] == 1
        assert len(digest["watchlist"]["promotions"]) == 1
        assert len(digest["watchlist"]["demotions"]) == 1

        message = telegram_engine.render_digest_message(digest)
        assert "Watchlist:" in message
        assert "PROMOTE TW0 — chair verdict SKIP -> TAKE" in message
        assert "DEMOTE TW1 — chair verdict TAKE -> SKIP" in message
        assert "Hard near-misses: 1" in message
    finally:
        conn.close()
