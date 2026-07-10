"""Chartink-style screener (WAVE_M amendment, user order 2026-07-11 ~09:30)."""
from manas_os import db
from manas_os.scanner import screener


def _seed(conn, symbol, closes, volumes=None, delivery=50.0):
    volumes = volumes or [500_000] * len(closes)
    prev = None
    for i, (close, vol) in enumerate(zip(closes, volumes)):
        d = f"2026-01-{i + 1:02d}" if i < 31 else f"2026-02-{i - 30:02d}"
        conn.execute(
            "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, "
            "close, prev_close, volume, delivery_qty, delivery_pct) VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, d, close, close + 1, close - 1, close, prev, vol, 100, delivery),
        )
        prev = close
    conn.commit()
    return d


def test_metrics_for_symbol_computes_pct_change_and_ema_flags(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        closes = [100.0] * 40 + [130.0]  # a sharp last-day burst above every EMA
        as_of = _seed(conn, "BURST", closes, volumes=[500_000] * 40 + [2_000_000])
        m = screener.metrics_for_symbol(conn, "BURST", as_of)
        assert m is not None
        assert m["symbol"] == "BURST"
        assert m["pct_change_1d"] == 30.0
        assert m["volume"] == 2_000_000
        assert m["above_ema10"] is True
        assert m["above_ema21"] is True
        assert m["above_ema50"] is True
        assert m["pct_off_52w_high"] == 0.76  # today's high IS the 52w high (close is 1 below it)
    finally:
        conn.close()


def test_apply_conditions_ands_and_ignores_unknown_field():
    rows = [
        {"symbol": "A", "pct_change_1d": 6.0, "volume": 2_000_000, "adr20": 5.0},
        {"symbol": "B", "pct_change_1d": 2.0, "volume": 2_000_000, "adr20": 5.0},
        {"symbol": "C", "pct_change_1d": 6.0, "volume": 500_000, "adr20": 5.0},
    ]
    conditions = [
        {"field": "pct_change_1d", "op": "gte", "value": 5.0},
        {"field": "volume", "op": "gte", "value": 1_000_000},
    ]
    out = screener.apply_conditions(rows, conditions)
    assert [r["symbol"] for r in out] == ["A"]

    # unknown field / bad op never matches (never raises)
    bad = screener.apply_conditions(rows, [{"field": "nope", "op": "gte", "value": 1}])
    assert bad == []


def test_todays_movers_preset_present_and_applies():
    assert "TODAYS_MOVERS" in screener.PRESETS
    conditions = screener.PRESETS["TODAYS_MOVERS"]["conditions"]
    rows = [
        {"symbol": "MOVER", "pct_change_1d": 8.0, "volume": 3_000_000, "adr20": 5.0},
        {"symbol": "FLAT", "pct_change_1d": 1.0, "volume": 3_000_000, "adr20": 5.0},
    ]
    out = screener.apply_conditions(rows, conditions)
    assert [r["symbol"] for r in out] == ["MOVER"]
