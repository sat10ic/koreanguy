from manas_os import db
from manas_os.agents import _shared, watchlist


D1 = "2026-06-28"
D2 = "2026-06-29"
D3 = "2026-06-30"


def _chair(conn, scan_date, symbol, verdict, conviction, tier="PASSED"):
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict, conviction, rank, tier) "
        "VALUES (?, ?, 'chair', ?, ?, 1, ?)",
        (scan_date, symbol, verdict, conviction, tier),
    )


def test_new_symbol_take_promotes(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "AAA", "TAKE", 4)
        conn.commit()

        result = watchlist.compute(conn, D1)
        assert result["status"] == "ok"
        row = conn.execute(
            "SELECT status, prev_status, tier FROM agent_watchlist WHERE scan_date = ? AND symbol = 'AAA'",
            (D1,),
        ).fetchone()
        assert row["status"] == "PROMOTE"
        assert row["prev_status"] is None
        assert row["tier"] == "PASSED"
    finally:
        conn.close()


def test_new_symbol_skip_holds(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "BBB", "SKIP", 2)
        conn.commit()
        watchlist.compute(conn, D1)
        row = conn.execute(
            "SELECT status FROM agent_watchlist WHERE scan_date = ? AND symbol = 'BBB'", (D1,)
        ).fetchone()
        assert row["status"] == "HOLD"
    finally:
        conn.close()


def test_conviction_increase_promotes_conviction_decrease_demotes(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "AAA", "TAKE", 3)
        _chair(conn, D1, "BBB", "TAKE", 5)
        conn.commit()
        watchlist.compute(conn, D1)

        _chair(conn, D2, "AAA", "TAKE", 5)  # conviction up -> promote
        _chair(conn, D2, "BBB", "TAKE", 2)  # conviction down -> demote
        conn.commit()
        watchlist.compute(conn, D2)

        rows = {
            r["symbol"]: dict(r)
            for r in conn.execute(
                "SELECT symbol, status, prev_status FROM agent_watchlist WHERE scan_date = ?", (D2,)
            ).fetchall()
        }
        assert rows["AAA"]["status"] == "PROMOTE"
        assert rows["AAA"]["prev_status"] == "PROMOTE"
        assert rows["BBB"]["status"] == "DEMOTE"
    finally:
        conn.close()


def test_unchanged_verdict_and_conviction_holds(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "AAA", "TAKE", 4)
        conn.commit()
        watchlist.compute(conn, D1)

        _chair(conn, D2, "AAA", "TAKE", 4)
        conn.commit()
        watchlist.compute(conn, D2)

        row = conn.execute(
            "SELECT status FROM agent_watchlist WHERE scan_date = ? AND symbol = 'AAA'", (D2,)
        ).fetchone()
        assert row["status"] == "HOLD"
    finally:
        conn.close()


def test_missing_one_night_holds_prior_status_then_drops_on_second_miss(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "AAA", "TAKE", 4)
        conn.commit()
        watchlist.compute(conn, D1)  # AAA -> PROMOTE (new)

        # D2: AAA not debated at all (no chair row) -> first miss, grace period
        watchlist.compute(conn, D2)
        row = conn.execute(
            "SELECT status, miss_streak FROM agent_watchlist WHERE scan_date = ? AND symbol = 'AAA'", (D2,)
        ).fetchone()
        assert row["status"] == "PROMOTE"  # carried forward, not dropped yet
        assert row["miss_streak"] == 1

        # D3: still not debated -> second consecutive miss -> DROP
        watchlist.compute(conn, D3)
        row = conn.execute(
            "SELECT status, miss_streak FROM agent_watchlist WHERE scan_date = ? AND symbol = 'AAA'", (D3,)
        ).fetchone()
        assert row["status"] == "DROP"
        assert row["miss_streak"] == 2
    finally:
        conn.close()


def test_already_dropped_symbol_is_not_resurrected(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        conn.execute(
            "INSERT INTO agent_watchlist (scan_date, symbol, tier, status, prev_status, reason, miss_streak) "
            "VALUES (?, 'ZZZ', 'PASSED', 'DROP', 'DEMOTE', 'missing 2 nights', 2)",
            (D1,),
        )
        conn.commit()
        result = watchlist.compute(conn, D2)
        assert result["status"] == "skip"
        row = conn.execute(
            "SELECT status FROM agent_watchlist WHERE scan_date = ? AND symbol = 'ZZZ'", (D2,)
        ).fetchone()
        assert row is None
    finally:
        conn.close()


def test_compute_is_idempotent_on_rerun(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _shared.ensure_agent_tables(conn)
        _chair(conn, D1, "AAA", "TAKE", 4)
        conn.commit()
        first = watchlist.compute(conn, D1)
        second = watchlist.compute(conn, D1)
        assert first["rows"] == second["rows"] == 1
        count = conn.execute(
            "SELECT COUNT(*) FROM agent_watchlist WHERE scan_date = ?", (D1,)
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()
