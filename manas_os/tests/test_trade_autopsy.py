"""One synthetic fixture trade per trade_autopsy tag, proving each tag fires
on an engineered positive case and does NOT fire on a matched negative/
control case. All fixtures live in a tmp sqlite DB (db.init_db(tmp_path)),
never the probe.db copy -- every price series here is hand-built so the
exact numeric threshold crossed (or not) is known ahead of time.
"""
from __future__ import annotations

import json

import pytest

from manas_os import db as manas_db
from manas_os.scanner.candidates import load_symbol_bars
from manas_os.tools import trade_autopsy
from manas_os.tools.import_broker import ensure_broker_schema

from manas_os.tests.conftest import trading_dates


# --- DB helpers --------------------------------------------------------------

def _conn(tmp_path):
    return manas_db.init_db(tmp_path / "manas.db")


def _insert_bars(conn, symbol, rows):
    """rows: list of [date, open, high, low, close, prev_close, volume, delivery_qty, delivery_pct]"""
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, close, "
        "prev_close, volume, delivery_qty, delivery_pct, source) "
        "VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, 'test')",
        [(symbol,) + tuple(row) for row in rows],
    )
    conn.commit()


def _insert_trade(conn, symbol, entry_date, entry_price, exit_date, exit_price, qty, pnl):
    ensure_broker_schema(conn)
    conn.execute(
        "INSERT INTO journal_trades (trade_date, exit_date, symbol, setup, entry, exit, qty, source, "
        "broker_realized_pnl, broker_return_pct, broker_holding_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (entry_date, exit_date, symbol, "Zerodha FIFO", entry_price, exit_price, qty, "zerodha_import",
         pnl, 0.0, 0),
    )
    conn.commit()
    return conn.execute(
        "SELECT trade_id, symbol, trade_date AS entry_date, entry AS entry_price, exit_date, "
        "exit AS exit_price, qty, broker_realized_pnl AS pnl, broker_return_pct AS return_pct, "
        "broker_holding_days AS holding_days FROM journal_trades WHERE symbol=? ORDER BY trade_id DESC LIMIT 1",
        (symbol,),
    ).fetchone()


# --- price-series builders ----------------------------------------------------

def _healthy_uptrend(n=260, start=100.0, step=0.15, base_range=1.0):
    """A smooth, genuinely-uptrending series: close>50SMA>200SMA, Lead EMA
    stack, mild ~1-1.5% 21EMA extension throughout (never >8%)."""
    dates = trading_dates(n)
    rows = []
    prev_close = None
    for i, d in enumerate(dates):
        close = start + i * step
        high, low = close + base_range / 2, close - base_range / 2
        rows.append([d, close - 0.05, high, low, close, prev_close, 500_000, 275_000, 55.0])
        prev_close = close
    return rows


def _falling_knife(n=260, start=200.0, step=0.15):
    """A monotonic decline: close<50SMA<200SMA -- a genuine hard-fail
    trend-template read (not a relaxed early-uptrend/reversal case)."""
    dates = trading_dates(n)
    rows = []
    prev_close = None
    for i, d in enumerate(dates):
        close = start - i * step
        high, low = close + 0.5, close - 0.5
        rows.append([d, close + 0.05, high, low, close, prev_close, 500_000, 275_000, 55.0])
        prev_close = close
    return rows


def _tighten_tail(rows, other_range, yday_range):
    """Override the 20-bar tightness window (bars[-21:-2] = 19 "other" bars,
    bars[-2] = "yesterday") so prev_day_tightness_pctile lands at a known
    value: below_or_equal(yday_range) / 20 * 100."""
    n = len(rows)
    for idx in range(n - 21, n - 2):
        close = rows[idx][4]
        rows[idx][2] = close + other_range / 2
        rows[idx][3] = close - other_range / 2
    yday_idx = n - 2
    yclose = rows[yday_idx][4]
    rows[yday_idx][2] = yclose + yday_range / 2
    rows[yday_idx][3] = yclose - yday_range / 2
    return rows


def _in_base_series(peak=150.0, start=100.0, pre_days=210, post_days=50):
    """Rally start->peak, then a mild pullback (~8%, <=15%) into a TIGHT
    final window -- both IN_BASE conditions (depth<=15%, tightness<=40)."""
    n = pre_days + post_days
    dates = trading_dates(n)
    rows = []
    prev_close = None
    for i in range(pre_days):
        frac = i / (pre_days - 1)
        close = start + frac * (peak - start)
        high, low = close + 0.5, close - 0.5
        rows.append([dates[i], close - 0.05, high, low, close, prev_close, 500_000, 275_000, 55.0])
        prev_close = close
    pullback_target = peak * 0.92
    for j in range(post_days):
        frac = j / (post_days - 1)
        close = peak - frac * (peak - pullback_target)
        high, low = close + 0.5, close - 0.5
        rows.append([dates[pre_days + j], close - 0.02, high, low, close, prev_close, 400_000, 220_000, 55.0])
        prev_close = close
    return _tighten_tail(rows, other_range=3.0, yday_range=0.2)


def _late_in_move_series(n_flat=40, n_rally=65, low_at_rally_start=100.0, target_pct_up=85.0):
    """40 flat/irrelevant days, then a 65-session rally window whose low is
    `low_at_rally_start` and whose close ends `target_pct_up`% above it."""
    n = n_flat + n_rally
    dates = trading_dates(n)
    rows = []
    prev_close = None
    for i in range(n_flat):
        close = 90.0
        high, low = close + 0.3, close - 0.3
        rows.append([dates[i], close - 0.02, high, low, close, prev_close, 300_000, 165_000, 55.0])
        prev_close = close
    close_end = low_at_rally_start * (1 + target_pct_up / 100.0)
    for j in range(n_rally):
        frac = j / (n_rally - 1)
        close = low_at_rally_start + frac * (close_end - low_at_rally_start)
        low = (low_at_rally_start - 0.5) if j == 0 else (close - 0.5)
        high = close + 0.5
        rows.append([dates[n_flat + j], close - 0.02, high, low, close, prev_close, 500_000, 275_000, 55.0])
        prev_close = close
    return rows


def _uptrend_then_crash(n_pre=250, start=100.0, step=0.16, crash_drop_frac=0.32, tail_after_crash=10):
    """A healthy uptrend, then one sharp crash day, then `tail_after_crash`
    more days drifting at the crashed level (Broken persists for a while)."""
    n = n_pre + 1 + tail_after_crash
    dates = trading_dates(n)
    rows = []
    prev_close = None
    close = start
    for i in range(n_pre):
        close = start + i * step
        high, low = close + 0.5, close - 0.5
        rows.append([dates[i], close - 0.05, high, low, close, prev_close, 500_000, 275_000, 55.0])
        prev_close = close
    crash_close = close * (1 - crash_drop_frac)
    rows.append([dates[n_pre], crash_close + 0.5, crash_close + 1.0, crash_close - 1.0,
                 crash_close, prev_close, 1_500_000, 900_000, 60.0])
    prev_close = crash_close
    for j in range(tail_after_crash):
        c = crash_close - j * 0.05
        high, low = c + 0.4, c - 0.4
        rows.append([dates[n_pre + 1 + j], c + 0.02, high, low, c, prev_close, 400_000, 220_000, 55.0])
        prev_close = c
    return rows


# --- ENTRY tags ----------------------------------------------------------------

def test_extended_entry_fires_and_not_on_control(tmp_path):
    conn = _conn(tmp_path)
    n = 260
    rows = _healthy_uptrend(n=n)
    jumped_close = rows[n - 1][4] * 1.15
    rows[n - 1][4] = jumped_close
    rows[n - 1][2] = jumped_close + 0.5
    rows[n - 1][3] = jumped_close - 0.5
    entry_date = rows[n - 1][0]
    _insert_bars(conn, "EXTPOS", rows)
    bars = load_symbol_bars(conn, "EXTPOS", entry_date, limit=300)
    result = trade_autopsy.entry_quality(bars, entry_date)
    assert result["ok"]
    assert result["extension_21"] > trade_autopsy.EXTENDED_ENTRY_PCT
    assert "EXTENDED_ENTRY" in result["tags"]

    control_rows = _healthy_uptrend(n=n)
    control_date = control_rows[n - 1][0]
    _insert_bars(conn, "EXTNEG", control_rows)
    control_bars = load_symbol_bars(conn, "EXTNEG", control_date, limit=300)
    control_result = trade_autopsy.entry_quality(control_bars, control_date)
    assert "EXTENDED_ENTRY" not in control_result["tags"]


def test_counter_trend_fires_and_not_on_control(tmp_path):
    conn = _conn(tmp_path)
    n = 260
    rows = _falling_knife(n=n)
    entry_date = rows[n - 1][0]
    _insert_bars(conn, "CTPOS", rows)
    bars = load_symbol_bars(conn, "CTPOS", entry_date, limit=300)
    result = trade_autopsy.entry_quality(bars, entry_date)
    assert result["ok"]
    assert result["trend_pass"] is False
    assert "COUNTER_TREND" in result["tags"]

    control_rows = _healthy_uptrend(n=n)
    control_date = control_rows[n - 1][0]
    _insert_bars(conn, "CTNEG", control_rows)
    control_bars = load_symbol_bars(conn, "CTNEG", control_date, limit=300)
    control_result = trade_autopsy.entry_quality(control_bars, control_date)
    assert control_result["trend_pass"] is True
    assert "COUNTER_TREND" not in control_result["tags"]


def test_no_base_fires_and_not_in_base(tmp_path):
    conn = _conn(tmp_path)
    n = 260
    rows = _tighten_tail(_healthy_uptrend(n=n), other_range=0.4, yday_range=6.0)
    entry_date = rows[n - 1][0]
    _insert_bars(conn, "NOBASE", rows)
    bars = load_symbol_bars(conn, "NOBASE", entry_date, limit=300)
    result = trade_autopsy.entry_quality(bars, entry_date)
    assert result["ok"]
    assert result["tightness_pctile"] > 60.0
    assert result["range_contraction"] is False
    assert "NO_BASE" in result["tags"]
    assert "IN_BASE" not in result["tags"]


def test_in_base_fires_and_not_no_base(tmp_path):
    conn = _conn(tmp_path)
    rows = _in_base_series()
    entry_date = rows[-1][0]
    _insert_bars(conn, "INBASE", rows)
    bars = load_symbol_bars(conn, "INBASE", entry_date, limit=300)
    result = trade_autopsy.entry_quality(bars, entry_date)
    assert result["ok"]
    assert result["correction_depth_pct"] <= 15.0
    assert result["tightness_pctile"] <= 40.0
    assert "IN_BASE" in result["tags"]
    assert "NO_BASE" not in result["tags"]


def test_late_in_move_fires_and_not_on_control(tmp_path):
    conn = _conn(tmp_path)
    rows = _late_in_move_series(target_pct_up=85.0)
    entry_date = rows[-1][0]
    _insert_bars(conn, "LATEPOS", rows)
    bars = load_symbol_bars(conn, "LATEPOS", entry_date, limit=300)
    result = trade_autopsy.entry_quality(bars, entry_date)
    assert result["ok"]
    assert result["pct_up_from_65d_low"] > 80.0
    assert "LATE_IN_MOVE" in result["tags"]

    control_rows = _late_in_move_series(target_pct_up=50.0)
    control_date = control_rows[-1][0]
    _insert_bars(conn, "LATENEG", control_rows)
    control_bars = load_symbol_bars(conn, "LATENEG", control_date, limit=300)
    control_result = trade_autopsy.entry_quality(control_bars, control_date)
    assert control_result["pct_up_from_65d_low"] <= 80.0
    assert "LATE_IN_MOVE" not in control_result["tags"]


# --- EXIT tags -------------------------------------------------------------------

def test_panic_exit_fires_and_not_on_gain_control(tmp_path):
    conn = _conn(tmp_path)
    n = 260
    rows = _healthy_uptrend(n=n)
    entry_date, exit_date = rows[100][0], rows[n - 1][0]
    _insert_bars(conn, "PANIC", rows)
    row = _insert_trade(conn, "PANIC", entry_date, rows[100][4], exit_date, rows[n - 1][4], 10, pnl=-150.0)
    tr = trade_autopsy.autopsy_trade(conn, row)
    assert tr.exit.get("ok")
    assert tr.exit["exit_state"] == "Intact"
    assert tr.exit["fired_rules"] == []
    assert "PANIC_EXIT" in tr.tags
    assert "SOLD_WINNER_EARLY" not in tr.tags

    rows2 = _healthy_uptrend(n=n)
    entry_date2, exit_date2 = rows2[100][0], rows2[n - 1][0]
    _insert_bars(conn, "GAINCTRL", rows2)
    row2 = _insert_trade(conn, "GAINCTRL", entry_date2, rows2[100][4], exit_date2, rows2[n - 1][4], 10, pnl=150.0)
    tr2 = trade_autopsy.autopsy_trade(conn, row2)
    assert tr2.exit["exit_state"] == "Intact"
    assert "PANIC_EXIT" not in tr2.tags
    assert "SOLD_WINNER_EARLY" in tr2.tags


def test_structure_exit_fires_and_not_on_control(tmp_path):
    conn = _conn(tmp_path)
    rows = _uptrend_then_crash()
    n_pre = 250
    crash_date = rows[n_pre][0]
    entry_date = rows[100][0]
    _insert_bars(conn, "STRUCT", rows)
    row = _insert_trade(conn, "STRUCT", entry_date, rows[100][4], crash_date, rows[n_pre][4], 10, pnl=-400.0)
    tr = trade_autopsy.autopsy_trade(conn, row)
    assert tr.exit.get("ok")
    assert tr.exit["exit_state"] in ("Broken", "Weakening")
    assert len(tr.exit["fired_rules"]) >= 2
    assert "STRUCTURE_EXIT" in tr.tags

    control_rows = _healthy_uptrend(n=260)
    entry_date2, exit_date2 = control_rows[100][0], control_rows[259][0]
    _insert_bars(conn, "STRUCTNEG", control_rows)
    row2 = _insert_trade(conn, "STRUCTNEG", entry_date2, control_rows[100][4], exit_date2, control_rows[259][4], 10, pnl=-50.0)
    tr2 = trade_autopsy.autopsy_trade(conn, row2)
    assert "STRUCTURE_EXIT" not in tr2.tags


def test_late_exit_fires_on_persisted_break_not_on_first_break_day(tmp_path):
    conn = _conn(tmp_path)
    rows = _uptrend_then_crash(tail_after_crash=10)
    n_pre = 250
    crash_date = rows[n_pre][0]
    late_exit_date = rows[-1][0]
    entry_date = rows[100][0]
    _insert_bars(conn, "LATEEXIT", rows)

    late_row = _insert_trade(conn, "LATEEXIT", entry_date, rows[100][4], late_exit_date, rows[-1][4], 10, pnl=-500.0)
    tr_late = trade_autopsy.autopsy_trade(conn, late_row)
    assert tr_late.exit.get("ok")
    assert tr_late.exit["exit_state"] == "Broken"
    assert tr_late.exit["first_broken_gap_sessions"] >= 3
    assert "LATE_EXIT" in tr_late.tags

    early_row = _insert_trade(conn, "LATEEXIT", entry_date, rows[100][4], crash_date, rows[n_pre][4], 10, pnl=-400.0)
    tr_early = trade_autopsy.autopsy_trade(conn, early_row)
    assert tr_early.exit["exit_state"] == "Broken"
    assert tr_early.exit["first_broken_gap_sessions"] == 0
    assert "LATE_EXIT" not in tr_early.tags


def test_sold_winner_early_fires_and_not_on_loss_control(tmp_path):
    # Reuses the same construction as PANIC_EXIT: Intact, mild (<8%) 21EMA
    # extension at exit; only the pnl sign differs, proving the two tags are
    # each other's negative control.
    conn = _conn(tmp_path)
    n = 260
    rows = _healthy_uptrend(n=n)
    entry_date, exit_date = rows[100][0], rows[n - 1][0]
    _insert_bars(conn, "WINEARLY", rows)
    row = _insert_trade(conn, "WINEARLY", entry_date, rows[100][4], exit_date, rows[n - 1][4], 10, pnl=75.0)
    tr = trade_autopsy.autopsy_trade(conn, row)
    assert tr.exit.get("ok")
    assert tr.exit["exit_state"] == "Intact"
    assert tr.exit["extension_21_at_exit"] < trade_autopsy.SOLD_WINNER_EXTENSION_PCT
    assert "SOLD_WINNER_EARLY" in tr.tags
    assert "PANIC_EXIT" not in tr.tags

    rows2 = _healthy_uptrend(n=n)
    entry_date2, exit_date2 = rows2[100][0], rows2[n - 1][0]
    _insert_bars(conn, "LOSSCTRL", rows2)
    row2 = _insert_trade(conn, "LOSSCTRL", entry_date2, rows2[100][4], exit_date2, rows2[n - 1][4], 10, pnl=-75.0)
    tr2 = trade_autopsy.autopsy_trade(conn, row2)
    assert "SOLD_WINNER_EARLY" not in tr2.tags
    assert "PANIC_EXIT" in tr2.tags


# --- end-to-end wiring -------------------------------------------------------

def test_build_autopsy_and_report_and_json_round_trip(tmp_path):
    conn = _conn(tmp_path)
    n = 260
    rows = _healthy_uptrend(n=n)
    entry_date, exit_date = rows[100][0], rows[n - 1][0]
    _insert_bars(conn, "E2E", rows)
    _insert_trade(conn, "E2E", entry_date, rows[100][4], exit_date, rows[n - 1][4], 10, pnl=-150.0)
    conn.close()

    db_path = tmp_path / "manas.db"
    trade_rows, warnings = trade_autopsy.build_autopsy(db_path)
    assert len(trade_rows) == 1
    assert trade_rows[0].symbol == "E2E"
    assert "PANIC_EXIT" in trade_rows[0].tags
    assert warnings == []

    report_text = trade_autopsy.render_report(trade_rows, warnings)
    assert "TAXONOMY" in report_text
    assert "HONEST CAVEATS" in report_text
    assert "PANIC_EXIT" in report_text

    out_path = tmp_path / "AUTOPSY.md"
    rc = trade_autopsy.main(["--db", str(db_path), "--out", str(out_path)])
    assert rc == 0
    assert out_path.exists()
    json_path = out_path.with_suffix(".json")
    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert "PANIC_EXIT" in payload[0]["tags"]


def test_skips_trade_with_no_point_in_time_bar_match(tmp_path):
    conn = _conn(tmp_path)
    # No daily_prices rows inserted for this symbol at all.
    row = _insert_trade(conn, "NODATA", "2026-01-05", 100.0, "2026-01-10", 105.0, 5, pnl=25.0)
    tr = trade_autopsy.autopsy_trade(conn, row)
    assert tr.entry.get("ok") is False
    assert tr.exit.get("ok") is False
    assert tr.skip_reason is not None
    assert tr.tags == []
