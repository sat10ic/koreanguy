"""Tests for the universe tradeability gate (manas_os.engine.universe_filter)."""
from __future__ import annotations

from manas_os import db
from manas_os.engine.universe_filter import (
    GateConfig,
    circuit_locked,
    evaluate_symbol,
    filter_universe,
    is_probable_etf,
)


def _bar(date, close, volume, high=None, low=None, prev_close=None):
    """Build one synthetic bar dict; high/low default to a tiny range around close."""
    high = close * 1.01 if high is None else high
    low = close * 0.99 if low is None else low
    return {
        "trade_date": date,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "prev_close": prev_close if prev_close is not None else close,
        "volume": volume,
        "delivery_qty": None,
        "delivery_pct": None,
    }


def _bars(n=25, close=500.0, volume=2_000_000, start="2026-06-01"):
    """n ascending daily bars, deterministic, liquid/large-cap-like by default."""
    import datetime

    d0 = datetime.date.fromisoformat(start)
    out = []
    for i in range(n):
        d = (d0 + datetime.timedelta(days=i)).isoformat()
        out.append(_bar(d, close, volume))
    return out


# ---------------------------------------------------------------------------
# is_probable_etf
# ---------------------------------------------------------------------------

def test_is_probable_etf_matches_known_keywords():
    assert is_probable_etf("GOLDBEES") is True
    assert is_probable_etf("NIFTYBEES") is True
    assert is_probable_etf("LIQUIDBEES") is True
    assert is_probable_etf("SETFNIF50") is True
    assert is_probable_etf("SOMEIETF") is True


def test_is_probable_etf_false_for_plain_symbol():
    assert is_probable_etf("RELIANCE") is False
    assert is_probable_etf("TCS") is False


# ---------------------------------------------------------------------------
# circuit_locked
# ---------------------------------------------------------------------------

def test_circuit_locked_false_for_normal_bars():
    bars = _bars(5)
    assert circuit_locked(bars) is False


def test_circuit_locked_true_when_latest_bar_flat():
    bars = _bars(5)
    bars[-1]["high"] = bars[-1]["low"] = 500.0
    assert circuit_locked(bars) is True


def test_circuit_locked_true_when_3_of_5_flat():
    bars = _bars(5)
    for b in bars[:3]:
        b["high"] = b["low"] = b["close"]
    assert circuit_locked(bars) is True


def test_circuit_locked_true_when_latest_volume_zero_or_none():
    bars = _bars(5)
    bars[-1]["volume"] = 0
    assert circuit_locked(bars) is True

    bars2 = _bars(5)
    bars2[-1]["volume"] = None
    assert circuit_locked(bars2) is True


# ---------------------------------------------------------------------------
# evaluate_symbol
# ---------------------------------------------------------------------------

def test_evaluate_symbol_clean_liquid_symbol_is_tradeable():
    bars = _bars(25, close=500.0, volume=2_000_000)  # turnover ~10cr/day
    result = evaluate_symbol(bars, "RELIANCE", GateConfig())
    assert result["tradeable"] is True
    assert result["reasons_failed"] == []
    assert result["metrics"]["etf"] is False
    assert result["metrics"]["circuit_locked"] is False
    assert result["metrics"]["mcap_check"] == "skipped: mcap unavailable"


def test_evaluate_symbol_mcap_unavailable_is_skipped_not_passed():
    bars = _bars(25, close=500.0, volume=2_000_000)
    result = evaluate_symbol(bars, "RELIANCE", GateConfig(), market_cap_cr=None)
    assert result["tradeable"] is True
    assert result["metrics"]["mcap_check"] == "skipped: mcap unavailable"
    assert "market_cap_cr" not in result["metrics"]


def test_evaluate_symbol_microcap_fails_mcap_floor_when_known():
    bars = _bars(25, close=500.0, volume=2_000_000)
    result = evaluate_symbol(bars, "MICROCO", GateConfig(), market_cap_cr=250.0)
    assert result["tradeable"] is False
    assert any("market cap" in r and "floor" in r for r in result["reasons_failed"])
    assert result["metrics"]["mcap_check"] == "checked: 250cr"
    assert result["metrics"]["market_cap_cr"] == 250.0


def test_evaluate_symbol_large_cap_passes_mcap_floor_when_known():
    bars = _bars(25, close=500.0, volume=2_000_000)
    result = evaluate_symbol(bars, "BIGCO", GateConfig(), market_cap_cr=5000.0)
    assert result["tradeable"] is True
    assert result["metrics"]["mcap_check"] == "checked: 5000cr"


def test_evaluate_symbol_penny_stock_fails_price_floor():
    bars = _bars(25, close=12.0, volume=2_000_000)
    result = evaluate_symbol(bars, "PENNYCO", GateConfig())
    assert result["tradeable"] is False
    assert any("price" in r and "floor" in r for r in result["reasons_failed"])


def test_evaluate_symbol_low_turnover_fails_turnover_floor():
    # ~1cr/day turnover: close * volume / 1e7 ≈ 1cr
    bars = _bars(25, close=100.0, volume=100_000)
    result = evaluate_symbol(bars, "THINSTOCK", GateConfig())
    assert result["tradeable"] is False
    assert any("avg turnover" in r and "floor" in r for r in result["reasons_failed"])


def test_evaluate_symbol_etf_symbol_fails_etf_gate():
    bars = _bars(25, close=500.0, volume=2_000_000)
    result = evaluate_symbol(bars, "GOLDBEES", GateConfig())
    assert result["tradeable"] is False
    assert any("ETF" in r for r in result["reasons_failed"])


def test_evaluate_symbol_circuit_locked_fails():
    bars = _bars(25, close=500.0, volume=2_000_000)
    # last 3 of 5 days flat -> circuit-locked heuristic trips
    for b in bars[-3:]:
        b["high"] = b["low"] = b["close"]
    result = evaluate_symbol(bars, "FROZEN", GateConfig())
    assert result["tradeable"] is False
    assert any("circuit-locked" in r for r in result["reasons_failed"])


# ---------------------------------------------------------------------------
# filter_universe (DB wrapper)
# ---------------------------------------------------------------------------

def test_filter_universe_splits_tradeable_and_excluded(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        as_of = "2026-06-25"
        rows = []
        for sym, close, vol in [
            ("GOODCO", 500.0, 2_000_000),
            ("PENNYCO", 12.0, 2_000_000),
            ("GOLDBEES", 500.0, 2_000_000),
        ]:
            for b in _bars(25, close=close, volume=vol, start="2026-06-01"):
                rows.append((sym, b["trade_date"], b["open"], b["high"], b["low"],
                             b["close"], b["prev_close"], b["volume"]))
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, "
            "prev_close, volume, series, source) VALUES (?,?,?,?,?,?,?,?, 'EQ', 'test')",
            rows,
        )
        conn.commit()

        result = filter_universe(conn, as_of)
        assert result["as_of"] == as_of
        assert "GOODCO" in result["tradeable"]
        excluded_syms = {e["symbol"] for e in result["excluded"]}
        assert "PENNYCO" in excluded_syms
        assert "GOLDBEES" in excluded_syms
        assert result["config"]["min_price"] == GateConfig().min_price
    finally:
        conn.close()


def test_filter_universe_applies_market_cap_lookup_when_supplied(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        as_of = "2026-06-25"
        rows = []
        for sym, close, vol in [
            ("GOODCO", 500.0, 2_000_000),
            ("MICROCO", 500.0, 2_000_000),
        ]:
            for b in _bars(25, close=close, volume=vol, start="2026-06-01"):
                rows.append((sym, b["trade_date"], b["open"], b["high"], b["low"],
                             b["close"], b["prev_close"], b["volume"]))
        conn.executemany(
            "INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, "
            "prev_close, volume, series, source) VALUES (?,?,?,?,?,?,?,?, 'EQ', 'test')",
            rows,
        )
        conn.commit()

        result = filter_universe(
            conn, as_of, market_cap_by_symbol={"GOODCO": 5000.0, "MICROCO": 250.0}
        )
        assert "GOODCO" in result["tradeable"]
        excluded_syms = {e["symbol"] for e in result["excluded"]}
        assert "MICROCO" in excluded_syms
    finally:
        conn.close()
