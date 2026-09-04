"""Replay harness (plan T0.2): aggregation math + look-ahead guard.

Unit boundary: replay's job is session iteration, outcome joining, and
family x regime aggregation. The candidate GENERATOR is pluggable, so these
tests register a deterministic fake generator instead of driving the whole
legacy scanner (whose output shape is tested elsewhere).
"""
from datetime import date, timedelta

from manas_os import db
import manas_os.backtest.replay as replay_mod


def _dates(n, start="2026-03-02"):
    d0 = date.fromisoformat(start)
    out, d = [], d0
    while len(out) < n:
        if d.weekday() < 5:  # trading days only
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _seed_prices(conn, symbol, closes_by_date):
    rows = [(symbol, d, "EQ", c, c + 0.5, c - 0.5, c, c - 0.1, 500000, 100, 60.0, "test")
            for d, c in closes_by_date.items()]
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
        "close, prev_close, volume, delivery_qty, delivery_pct, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def _fake_generator(candidates_by_session):
    def gen(conn, session_date):
        return list(candidates_by_session.get(session_date, []))
    return gen


def test_replay_aggregates_hand_computed_hit_rate(monkeypatch, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(20)
        # flat 100 closes, but T+10 close differs per candidate session
        closes = {d: 100.0 for d in days}
        # sessions 0,1,2 -> their T+10 (10th close AFTER session) indices are 10,11,12
        closes[days[10]] = 110.0   # session days[0]: R = (110-100)/(100-95) = +2.0 -> hit
        closes[days[11]] = 104.0   # session days[1]: R = +0.8 -> miss
        closes[days[12]] = 108.0   # session days[2]: R = +1.6 -> hit
        _seed_prices(conn, "AAA", closes)
        conn.execute("INSERT OR REPLACE INTO regime_snapshots (snapshot_date, market_mode) "
                     "VALUES (?, 'RISK_ON')", (days[0],))
        conn.commit()

        cand = {"symbol": "AAA", "setup": "Pullback-to-EMA", "entry": 100.0, "stop": 95.0}
        monkeypatch.setitem(replay_mod.GENERATORS, "fake",
                            _fake_generator({days[0]: [cand], days[1]: [cand], days[2]: [cand]}))
        monkeypatch.setattr(replay_mod, "THIN_N", 1)

        result = replay_mod.replay(conn, days[0], days[2], "fake")
        assert result["sessions"] == 3
        cell = result["cells"][0]
        assert cell["n"] == 3
        assert round(cell["hit_rate"], 4) == round(2 / 3, 4)
        assert cell["regime"] == "RISK_ON"
        assert cell["median_stop_pct"] == 5.0
    finally:
        conn.close()


def test_replay_lookahead_guard(monkeypatch, tmp_path):
    """A future price row beyond the measured horizon must not change output."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(20)
        closes = {d: 100.0 for d in days}
        closes[days[10]] = 110.0
        _seed_prices(conn, "AAA", closes)
        cand = {"symbol": "AAA", "setup": "EP", "entry": 100.0, "stop": 95.0}
        monkeypatch.setitem(replay_mod.GENERATORS, "fake",
                            _fake_generator({days[0]: [cand]}))
        monkeypatch.setattr(replay_mod, "THIN_N", 1)

        before = replay_mod.replay(conn, days[0], days[0], "fake")
        _seed_prices(conn, "AAA", {"2026-12-31": 999.0})
        after = replay_mod.replay(conn, days[0], days[0], "fake")
        assert after == before
    finally:
        conn.close()


def test_replay_unknown_config_raises(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        import pytest
        with pytest.raises(ValueError):
            replay_mod.replay(conn, "2026-01-01", "2026-01-02", "nope")
    finally:
        conn.close()


def test_thin_cells_suppressed(monkeypatch, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        days = _dates(15)
        _seed_prices(conn, "AAA", {d: 100.0 for d in days})
        cand = {"symbol": "AAA", "setup": "EP", "entry": 100.0, "stop": 95.0}
        monkeypatch.setitem(replay_mod.GENERATORS, "fake",
                            _fake_generator({days[0]: [cand]}))
        result = replay_mod.replay(conn, days[0], days[0], "fake")  # THIN_N=20 default
        cell = result["cells"][0]
        assert cell["hit_rate"] is None and "thin" in cell["note"]
    finally:
        conn.close()
