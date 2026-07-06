"""Tests for the MARS ingest stage (regime/mars_ingest.py).

Two paths: the success path with a fake provider (deterministic history), and
the graceful-skip path when no provider is available (the no-Fyers-token case).
"""
from manas_os import db
from manas_os.providers.base import DailyBar
from manas_os.regime import mars_ingest
from manas_os.regime.sectors import BENCHMARK, MA_LENGTH, SECTOR_INDICES


def _fake_bars(endpoint_offset=0.0):
    """80 bars rising gently, last bar nudged by endpoint_offset (in pp above)."""
    from datetime import date, timedelta
    d0 = date.fromisoformat("2026-01-01")
    bars = []
    for i in range(80):
        bars.append(DailyBar((d0 + timedelta(days=i)).isoformat(), 0, 0, 0,
                             round(100.0 + i * 0.05, 2), 0))
    # Move the last close to create a known outperformance.
    last = bars[-1]
    bars[-1] = DailyBar(last.date, 0, 0, 0, round(last.close + endpoint_offset, 2), 0)
    return bars


class _FakeProvider:
    """Deterministic provider; is_available True; returns canned history."""

    def __init__(self, available=True):
        self._available = available

    def is_available(self):
        return self._available

    def get_index_history(self, symbol, lookback_days=80):
        if not self._available:
            return []
        # Benchmark flat-ish; each sector gets a distinct endpoint offset.
        if symbol == BENCHMARK:
            return _fake_bars(endpoint_offset=2.0)
        idx = SECTOR_INDICES.index(symbol) if symbol in SECTOR_INDICES else 0
        return _fake_bars(endpoint_offset=2.0 + idx)  # +1pp per sector rank


def test_run_skips_when_provider_unavailable(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        result = mars_ingest.run(conn, "2026-07-04", provider=_FakeProvider(available=False))
        assert result["status"] == "skip"
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_mars'"
        ).fetchone()
        assert row["status"] == "skip"
        # Nothing written.
        assert conn.execute("SELECT COUNT(*) FROM sector_index_prices").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM sector_metrics WHERE mars_score IS NOT NULL"
        ).fetchone()[0] == 0
    finally:
        conn.close()


def test_run_populates_prices_and_mars(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        result = mars_ingest.run(conn, "2026-07-04", provider=_FakeProvider(available=True))
        assert result["status"] == "ok"
        assert result["sectors"] == len(SECTOR_INDICES)

        # sector_index_prices: one symbol per sector + the benchmark.
        n_symbols = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM sector_index_prices"
        ).fetchone()[0]
        assert n_symbols == len(SECTOR_INDICES) + 1

        # Each sector has a MARS row, all positive (each outruns the benchmark).
        mars_rows = conn.execute(
            "SELECT sector_key, mars_score, mars_state FROM sector_metrics "
            "WHERE mars_score IS NOT NULL ORDER BY mars_score DESC"
        ).fetchall()
        assert len(mars_rows) == len(SECTOR_INDICES)
        assert all(r["mars_score"] is not None for r in mars_rows)
        assert all(r["mars_state"] in {
            "ABSOLUTE_OUT", "GROSS_OUT", "RELATIVE_OUT",
            "ABSOLUTE_UNDER", "GROSS_UNDER", "RELATIVE_UNDER",
        } for r in mars_rows)

        run = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_mars'"
        ).fetchone()
        assert run["status"] == "ok"
    finally:
        conn.close()


def test_run_skips_when_benchmark_too_short(tmp_path):
    """A provider that returns < MA_LENGTH bars for the benchmark → skip."""

    class _ShortProvider(_FakeProvider):
        def get_index_history(self, symbol, lookback_days=80):
            return _fake_bars()[: MA_LENGTH - 5]  # 45 bars, too short for SMA50

    conn = db.init_db(tmp_path / "manas.db")
    try:
        result = mars_ingest.run(conn, "2026-07-04", provider=_ShortProvider(available=True))
        assert result["status"] == "skip"
        assert "too short" in result["detail"]
    finally:
        conn.close()
