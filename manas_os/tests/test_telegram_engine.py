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
