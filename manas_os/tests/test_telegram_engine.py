from manas_os import db
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
        assert result["sent"] is False
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


def test_telegram_send_failure_logs_fail_and_does_not_raise(tmp_path):
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

        assert result["status"] == "fail"
        assert "telegram down" in result["detail"]
        run = conn.execute(
            "SELECT status, rows_affected, detail FROM pipeline_runs WHERE stage = ? ORDER BY rowid DESC LIMIT 1",
            (telegram_engine.STAGE,),
        ).fetchone()
        assert run["status"] == "fail"
        assert run["rows_affected"] == 0
        assert "telegram down" in run["detail"]
    finally:
        conn.close()
