"""T2.3b expectancy loop: shrinkage math, trust ladder, loop separation."""
import json

from manas_os import db
from manas_os.scanner import expectancy


def _seed_outcome(conn, d, sym, family, r):
    conn.execute(
        "INSERT OR REPLACE INTO candidates (candidate_date, symbol, setup, source_payload_json) "
        "VALUES (?, ?, 'X', ?)", (d, sym, json.dumps({"setup_family": family})))
    conn.execute(
        "INSERT OR REPLACE INTO outcomes (candidate_date, symbol, setup, horizon, forward_r, status) "
        "VALUES (?, ?, 'X', 10, ?, 'complete')", (d, sym, r))


def test_shrinkage_hand_computed(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        conn.execute("INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) "
                     "VALUES ('2026-01-01', 'RISK_ON')")
        # family parent: 5 obs in RISK_ON cell only -> parent_mean == cell_mean -> posterior == mean
        for i, r in enumerate([2.0, 1.0, -1.0, 0.5, 0.5]):
            _seed_outcome(conn, "2026-01-05", f"S{i}", "catalyst", r)
        cells = expectancy.compute(conn, "2026-01-10")["system"]
        cell = next(c for c in cells if c["setup_family"] == "catalyst")
        assert cell["n"] == 5
        assert cell["mean_r"] == 0.6
        # posterior = 5/30*0.6 + 25/30*0.6 = 0.6 (single-cell family)
        assert cell["posterior_r"] == 0.6
        assert cell["hit_rate"] == 0.4  # 2 of 5 >= +1R
        assert cell["trust"] == "descriptive"
    finally:
        conn.close()


def test_shrinkage_pulls_toward_parent(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        conn.execute("INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) "
                     "VALUES ('2026-01-01', 'RISK_ON')")
        conn.execute("INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) "
                     "VALUES ('2026-02-01', 'DEFENSIVE')")
        # RISK_ON cell: 5 obs of +2R; DEFENSIVE cell: 5 obs of 0R -> parent mean = 1.0
        for i in range(5):
            _seed_outcome(conn, "2026-01-05", f"A{i}", "momentum", 2.0)
            _seed_outcome(conn, "2026-02-05", f"B{i}", "momentum", 0.0)
        cells = expectancy.compute(conn, "2026-03-01")["system"]
        risk_on = next(c for c in cells if c["regime"] == "RISK_ON")
        # posterior = 5/30*2.0 + 25/30*1.0 = 1.1667
        assert risk_on["posterior_r"] == round(5/30*2.0 + 25/30*1.0, 3)
    finally:
        conn.close()


def test_run_persists_and_chip_thin_personal_note(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        conn.execute("INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) "
                     "VALUES ('2026-01-01', 'SELECTIVE')")
        for i in range(3):
            _seed_outcome(conn, "2026-01-05", f"S{i}", "base/pattern", 1.5)
        # one personal closed trade with a decision snapshot
        from manas_os.scanner import outcomes as oc
        conn.execute("CREATE TABLE IF NOT EXISTS setup_decisions (scan_date TEXT, symbol TEXT, "
                     "decision TEXT, skip_reason TEXT, entry_price REAL, qty INTEGER, "
                     "snapshot_json TEXT, created_at TEXT, PRIMARY KEY(scan_date, symbol))")
        conn.execute("INSERT INTO setup_decisions (scan_date, symbol, decision, snapshot_json) "
                     "VALUES ('2026-01-05', 'S0', 'taken', ?)",
                     (json.dumps({"setup_family": "base/pattern"}),))
        conn.execute("INSERT INTO journal_trades (trade_date, symbol, setup, entry, exit, stop, r_result) "
                     "VALUES ('2026-01-05', 'S0', 'X', 100, 110, 95, 2.0)")
        res = expectancy.run(conn, "2026-03-01")
        assert res["status"] == "ok" and res["rows"] >= 2
        chip = expectancy.chip_for(conn, "base/pattern", "SELECTIVE")
        assert chip["system"]["n"] == 3
        assert chip["personal"]["n"] == 1
        assert "too thin" in chip["personal_note"]
    finally:
        conn.close()
