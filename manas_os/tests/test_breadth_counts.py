"""Tests for manas_os.sources.breadth_counts.

Each case builds a seeded in-memory daily_prices table, runs compute_counts
(or run), and asserts hand-derived expected values. Hand arithmetic is shown
inline next to each assertion so the maintainer can verify without re-deriving.

These tests stand up the breadth_counts DDL themselves (db.init_db runs the
canonical schema.sql which does NOT yet include breadth_counts — the
maintainer wires that separately), then seed daily_prices directly.
"""
from __future__ import annotations

import sqlite3

from manas_os.sources import breadth_counts as bc

# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

_DAILY_PRICES_DDL = """\
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    series        TEXT DEFAULT 'EQ',
    open          REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price    REAL, avg_price REAL,
    volume        INTEGER,
    turnover      REAL,
    num_trades    INTEGER,
    delivery_qty  INTEGER,
    delivery_pct  REAL,
    source        TEXT,
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, series)
);
"""

_PIPELINE_RUNS_DDL = """\
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    stage       TEXT NOT NULL,
    source      TEXT,
    status      TEXT,
    rows_affected INTEGER DEFAULT 0,
    duration_s  REAL,
    detail      TEXT,
    ran_at      TEXT DEFAULT (datetime('now'))
);
"""

_BREADTH_DAILY_DDL = """\
CREATE TABLE breadth_daily (
    trade_date TEXT PRIMARY KEY,
    pct_10dma_gt_20dma REAL,
    pct_20dma_gt_40dma REAL,
    up_25pct_month INTEGER,
    down_25pct_month INTEGER,
    up_50pct_month INTEGER,
    down_50pct_month INTEGER
);
"""


def _fresh_db() -> sqlite3.Connection:
    """In-memory DB with daily_prices, pipeline_runs, and breadth_counts."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_DAILY_PRICES_DDL)
    conn.executescript(_PIPELINE_RUNS_DDL)
    conn.executescript(bc.DDL)
    conn.executescript(_BREADTH_DAILY_DDL)
    return conn


def _price(conn, symbol, trade_date, *, series="EQ", open_=None, high, low, close,
           prev_close=None, volume=None):
    """Insert one daily_prices row. open defaults to close when not given."""
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (symbol, trade_date, series, open_ if open_ is not None else close,
         high, low, close, prev_close, volume),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pure-helper unit tests (no DB)
# ─────────────────────────────────────────────────────────────────────────────

def test_ema_seeded_by_sma_then_recurses():
    # flat 12-value series at 100 -> seed=SMA(10)=100, recursion stays 100
    assert bc.ema([100.0] * 12, 10) == 100.0
    # fewer than period -> None (unstable seed)
    assert bc.ema([100.0, 101.0], 10) is None
    # period 3 on [2,4,6,8]: seed SMA=4, alpha=2/4=0.5, then 0.5*8+0.5*4=6
    assert bc.ema([2.0, 4.0, 6.0, 8.0], 3) == 6.0


def test_net_change_divides_by_prev_close():
    # decision 1: (close-prev)/prev, NOT (close-prev)/close
    # close=104, prev=100 -> 0.04
    assert bc.net_change_pct(104.0, 100.0) == 0.04
    # the buggy workbook form would be (104-100)/104 = 0.03846; we use /prev
    assert bc.net_change_pct(104.0, 100.0) != (104 - 100) / 104
    assert bc.net_change_pct(104.0, None) is None
    assert bc.net_change_pct(104.0, 0.0) is None


# ─────────────────────────────────────────────────────────────────────────────
# Case 1: 4% advance/decline + breakout/breakdown sustained/failed
# ─────────────────────────────────────────────────────────────────────────────

def test_case1_advance_decline_breakout_breakdown():
    """3 symbols on 2026-07-10.

    SYM_A: prev=100, close=104 (+4%) -> up_4pct. High=105 >= 100*1.04=104 ->
           breakout. Range 105-104=1 on low=104 -> rng=0.0096 (<3% contraction,
           NOT expansion). close 104 vs high 105: span=1, threshold=0.4*1=0.4,
           105-0.4=104.6 -> close 104 < 104.6 -> breakout FAILED.
           chg=+4% is >= 0.04 so up_4pct counts (boundary inclusive).
    SYM_B: prev=100, close=96  (-4%) -> down_4pct. Low=95 <= 100*0.96=96 ->
           breakdown. Range 97-95=2 on low=95 -> rng=0.0211 (<3% contraction).
           close 96 vs low 95: span=2, low+0.4*2=95.8, close 96 > 95.8 ->
           breakdown FAILED (closed above the bottom-40% band).
    SYM_C: prev=100, close=100 (0%) flat. No 4%, no BO/BD.

    Expected: total_universe=3, up_4pct=1, down_4pct=1, breakouts=1,
    breakout_failed=1, breakdowns=1, breakdown_failed=1.
    (range_contraction=3 since all three ranges < 3%.)
    """
    conn = _fresh_db()
    # SYM_A
    _price(conn, "SYM_A", "2026-07-09", high=100, low=99, close=100)  # prior
    _price(conn, "SYM_A", "2026-07-10", high=105, low=104, close=104, prev_close=100)
    # SYM_B
    _price(conn, "SYM_B", "2026-07-09", high=100, low=99, close=100)
    _price(conn, "SYM_B", "2026-07-10", high=97, low=95, close=96, prev_close=100)
    # SYM_C
    _price(conn, "SYM_C", "2026-07-09", high=100, low=99, close=100)
    _price(conn, "SYM_C", "2026-07-10", high=100, low=99.5, close=100, prev_close=100)
    conn.commit()

    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["total_universe"] == 3
    assert counts["up_4pct"] == 1      # SYM_A
    assert counts["down_4pct"] == 1    # SYM_B
    assert counts["breakouts"] == 1    # SYM_A high 105 >= 104
    assert counts["breakout_failed"] == 1
    assert counts["breakout_sustained"] == 0
    assert counts["breakdowns"] == 1   # SYM_B low 95 <= 96
    assert counts["breakdown_failed"] == 1
    assert counts["breakdown_sustained"] == 0
    conn.close()


def test_case1b_breakout_sustained_close_in_top_band():
    """A breakout that closes within the top 40% of range counts as sustained.

    prev=100, high=108 (>=104 BO), low=100, close=107. span=8, high-0.4*8=104.8.
    close 107 >= 104.8 -> sustained. Range 8/100=8% (>=5.01% expansion), and
    close 107 >= mid 104 -> close_upper_half.
    """
    conn = _fresh_db()
    _price(conn, "X", "2026-07-09", high=100, low=99, close=100)
    _price(conn, "X", "2026-07-10", high=108, low=100, close=107, prev_close=100)
    conn.commit()
    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["breakouts"] == 1
    assert counts["breakout_sustained"] == 1
    assert counts["breakout_failed"] == 0
    assert counts["range_expansion"] == 1   # 8% range
    assert counts["close_upper_half"] == 1
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Case 2: volume high/low + range expansion/contraction + close half
# ─────────────────────────────────────────────────────────────────────────────

def test_case2_volume_and_range_bands():
    """Volume thresholds use the trailing 20 sessions EXCLUDING today (decision 4).

    VOL_HI: 20 prior sessions at volume=1000 -> avg=1000. Today volume=2000
            -> 2000 > 1.5*1000=1500 -> high_vol.
    VOL_LO: 20 prior at 1000. Today=400 -> 400 < 0.5*1000=500 -> low_vol.
    VOL_NO: 20 prior at 1000. Today=1000 -> neither band.

    Range: VOL_HI day high=110 low=100 -> rng=10% (>=5.01% expansion); close=109
           >= mid 105 -> close_upper_half.
           VOL_LO day high=100.5 low=100 -> rng=0.5% (<=3% contraction), and NOT
           expansion so close half counts for neither.

    Expected: high_vol=1, low_vol=1, range_expansion=1, range_contraction=1,
    close_upper_half=1, close_lower_half=0.
    """
    conn = _fresh_db()
    dates = [f"2026-06-{d:02d}" for d in range(1, 20)] + ["2026-07-01", "2026-07-10"]
    # 20 prior sessions (2026-06-01..2026-07-01) at vol=1000 for all three syms
    prior_dates = dates[:20]
    today = "2026-07-10"
    for sym in ("VOL_HI", "VOL_LO", "VOL_NO"):
        for d in prior_dates:
            _price(conn, sym, d, high=100, low=99, close=100, volume=1000)
    # today rows
    _price(conn, "VOL_HI", today, high=110, low=100, close=109, prev_close=100, volume=2000)
    _price(conn, "VOL_LO", today, high=100.5, low=100, close=100, prev_close=100, volume=400)
    _price(conn, "VOL_NO", today, high=100, low=99.5, close=100, prev_close=100, volume=1000)
    conn.commit()

    counts = bc.compute_counts(conn, today)
    assert counts["high_vol"] == 1          # VOL_HI 2000 > 1500
    assert counts["low_vol"] == 1           # VOL_LO 400 < 500
    assert counts["range_expansion"] == 1   # VOL_HI 10%
    assert counts["range_contraction"] == 2  # VOL_LO 0.5% + VOL_NO 0.5%
    assert counts["close_upper_half"] == 1  # VOL_HI close 109 >= mid 105
    assert counts["close_lower_half"] == 0
    conn.close()


def test_case2b_insufficient_volume_history_excludes_symbol():
    """A symbol with <20 prior sessions is excluded from high_vol/low_vol
    (decision 4: don't fabricate a partial average)."""
    conn = _fresh_db()
    # only 5 prior sessions — not enough for a 20-day average
    for i, d in enumerate(["2026-07-05", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09"]):
        _price(conn, "SHORT", d, high=100, low=99, close=100, volume=1000)
    _price(conn, "SHORT", "2026-07-10", high=100, low=99, close=100, prev_close=100, volume=99999)
    conn.commit()
    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["high_vol"] == 0  # excluded despite huge volume
    assert counts["low_vol"] == 0
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Case 3: 52-week high/low + distance band + DEMA
# ─────────────────────────────────────────────────────────────────────────────

def test_case3_52wk_and_dema():
    """Short synthetic history (NOT a full 252 days — decision 10 assumption
    notes partial history still computes, so early stocks can trivially set
    "new highs"; that caveat is accepted for this test).

    HISTORICAL_HIGH: 12 flat days at close=100 (high=101, low=99). Today makes
      a new window high: high=102 >= max prior high 101 -> new_52wk_high.
      close=102. high_52=102, so within 15%: 102 >= 102*0.85=86.7 -> yes.
      EMA10 on 12 closes ending 102: seed SMA(first 10 = all 100)=100,
      alpha=2/11; ema after 11th(100)=0.1818*100+0.8182*100=100; after 12th
      (102)=0.1818*102+0.8182*100=100.3636. close 102 vs 100.3636*1.10=110.4
      -> NOT 10% above. close 102 > 100.3636 -> above_10dema=1.

    HISTORICAL_LOW: 12 flat days at close=100. Today low=98 <= min prior low 99
      -> new_52wk_low. close=100. low_52=98: within 15% of low means
      close <= 98*1.15=112.7 -> 100 <= 112.7 yes -> from_52wl_15pct=1.

    Expected: new_52wk_high=1, new_52wk_low=1, from_52wh_15pct>=1,
    from_52wl_15pct>=1, above_10dema>=1.
    """
    conn = _fresh_db()
    # 12 prior flat days for both symbols
    prior = [f"2026-06-{d:02d}" for d in range(1, 13)]
    for d in prior:
        _price(conn, "HI_NEW", d, high=101, low=99, close=100)
        _price(conn, "LO_NEW", d, high=101, low=99, close=100)
    # today
    _price(conn, "HI_NEW", "2026-07-10", high=102, low=100, close=102, prev_close=100)
    _price(conn, "LO_NEW", "2026-07-10", high=100, low=98, close=100, prev_close=100)
    conn.commit()

    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["new_52wk_high"] == 1     # HI_NEW high 102 > prior max 101
    assert counts["new_52wk_low"] == 1      # LO_NEW low 98 < prior min 99
    # BOTH symbols are within 15% of their own 52wk high:
    #   HI_NEW close 102 vs high_52 102 -> 102 >= 86.7 yes
    #   LO_NEW close 100 vs high_52 101 -> 100 >= 85.85 yes
    assert counts["from_52wh_15pct"] == 2
    # BOTH within 15% of their own 52wk low:
    #   HI_NEW close 102 vs low_52 99 -> 102 <= 113.85 yes
    #   LO_NEW close 100 vs low_52 98 -> 100 <= 112.7 yes
    assert counts["from_52wl_15pct"] == 2
    # only HI_NEW closes above its ema10 (~100.36); LO_NEW close 100 == ema10
    # (strict >), so not counted.
    assert counts["above_10dema"] == 1
    conn.close()


def test_case3b_dema_deviation_band():
    """A stock 10%+ above its 10-EMA registers in above_10pct_10dema.

    12 flat days at 100, then today close=120. ema10 seed=100, recursion:
    after 11th(100)=100, after 12th(120)=0.1818*120+0.8182*100=103.636.
    103.636*1.10=114.0 -> close 120 >= 114.0 -> above_10pct_10dema.
    Also above_10dema (120 > 103.636).
    """
    conn = _fresh_db()
    for d in [f"2026-06-{i:02d}" for i in range(1, 13)]:
        _price(conn, "DEV", d, high=100, low=99, close=100)
    _price(conn, "DEV", "2026-07-10", high=120, low=100, close=120, prev_close=100)
    conn.commit()
    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["above_10pct_10dema"] == 1
    assert counts["above_10dema"] == 1
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Case 4: idempotency — run() twice, exactly one row
# ─────────────────────────────────────────────────────────────────────────────

def test_case4_idempotent_upsert():
    conn = _fresh_db()
    _price(conn, "S", "2026-07-09", high=100, low=99, close=100)
    _price(conn, "S", "2026-07-10", high=105, low=100, close=104, prev_close=100)
    conn.commit()

    r1 = bc.run(conn, "2026-07-10")
    assert r1["status"] == "ok"
    assert r1["rows_affected"] == 1
    r2 = bc.run(conn, "2026-07-10")
    assert r2["status"] == "ok"

    total = conn.execute(
        "SELECT COUNT(*) FROM breadth_counts WHERE trade_date='2026-07-10'"
    ).fetchone()[0]
    assert total == 1  # upsert, not duplicate insert

    # values unchanged on re-run
    row = conn.execute(
        "SELECT up_4pct, breakouts FROM breadth_counts WHERE trade_date='2026-07-10'"
    ).fetchone()
    assert row["up_4pct"] == 1
    assert row["breakouts"] == 1
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Case 5: skip path — no daily_prices rows for the date
# ─────────────────────────────────────────────────────────────────────────────

def test_case5_skip_when_no_universe():
    conn = _fresh_db()
    # a row exists, but for a different date
    _price(conn, "S", "2026-07-09", high=100, low=99, close=100)
    conn.commit()

    result = bc.run(conn, "2026-07-10")
    assert result["status"] == "skip"
    assert result["rows_affected"] == 0

    # no breadth_counts row written
    n = conn.execute("SELECT COUNT(*) FROM breadth_counts").fetchone()[0]
    assert n == 0

    # a skip pipeline_runs row WAS logged
    pr = conn.execute(
        "SELECT status, stage FROM pipeline_runs WHERE stage='breadth_counts'"
    ).fetchone()
    assert pr["status"] == "skip"
    assert pr["stage"] == "breadth_counts"
    conn.close()


def test_run_logs_ok_to_pipeline_runs():
    """Successful run writes an 'ok' pipeline_runs row with stage=breadth_counts."""
    conn = _fresh_db()
    _price(conn, "S", "2026-07-09", high=100, low=99, close=100)
    _price(conn, "S", "2026-07-10", high=105, low=100, close=104, prev_close=100)
    conn.commit()
    bc.run(conn, "2026-07-10")
    pr = conn.execute(
        "SELECT status, rows_affected, stage FROM pipeline_runs WHERE stage='breadth_counts'"
    ).fetchone()
    assert pr["status"] == "ok"
    assert pr["rows_affected"] == 1
    conn.close()


def test_zero_range_excluded_from_sustained_failed():
    """Decision 7: high==low (zero range) is excluded from sustained/failed,
    not force-classified. A BO with high==low==close==prev*1.04 still counts
    as a breakout, but neither sustained nor failed (undefined ratio)."""
    conn = _fresh_db()
    _price(conn, "Z", "2026-07-09", high=100, low=99, close=100)
    # high=low=104, prev=100 -> high 104 >= 104 BO; zero range
    _price(conn, "Z", "2026-07-10", high=104, low=104, close=104, prev_close=100)
    conn.commit()
    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["breakouts"] == 1
    assert counts["breakout_sustained"] == 0
    assert counts["breakout_failed"] == 0
    conn.close()


def test_52wk_bands_are_inclusive_nested_not_mutually_exclusive():
    """Decision 11: a stock within 15% of its high is ALSO within 30/50/70%.
    Each band is counted independently — these are not exclusive buckets."""
    conn = _fresh_db()
    # 3 prior days establishing high_52=100
    for d in ["2026-07-07", "2026-07-08", "2026-07-09"]:
        _price(conn, "N", d, high=100, low=90, close=95)
    # today close=95 -> within 15% of 100? 95 >= 85 yes -> also within 30/50/70
    _price(conn, "N", "2026-07-10", high=96, low=94, close=95, prev_close=95)
    conn.commit()
    counts = bc.compute_counts(conn, "2026-07-10")
    assert counts["from_52wh_15pct"] == 1
    assert counts["from_52wh_30pct"] == 1
    assert counts["from_52wh_50pct"] == 1
    assert counts["from_52wh_70pct"] == 1
    # and NOT in the strict complement (>70% below)
    assert counts["from_52wh_70pct_plus"] == 0
    conn.close()


def test_wave2_metrics_use_smas_and_actual_bar_21_rows_back():
    conn = _fresh_db()
    dates = [f"2026-06-{d:02d}" for d in range(1, 23)]
    for index, trade_date in enumerate(dates):
        # A rises from 100 to 160; B falls from 100 to 40. Both have 22 bars,
        # so the monthly comparison is exactly row[-22] versus row[-1].
        _price(conn, "A", trade_date, high=161, low=99, close=100 + index * (60 / 21))
        _price(conn, "B", trade_date, high=101, low=39, close=100 - index * (60 / 21))
    conn.execute("INSERT INTO breadth_daily (trade_date) VALUES (?)", (dates[-1],))

    metrics = bc.compute_wave2_metrics(conn, dates[-1])

    assert metrics["pct_10dma_gt_20dma"] == 50.0
    assert metrics["pct_20dma_gt_40dma"] is None  # neither symbol has 40 bars
    assert metrics["up_25pct_month"] == 1
    assert metrics["down_25pct_month"] == 1
    assert metrics["up_50pct_month"] == 1
    assert metrics["down_50pct_month"] == 1


def test_wave2_backfill_is_recent_and_idempotent():
    conn = _fresh_db()
    dates = [f"2026-05-{d:02d}" for d in range(1, 29)]
    for index, trade_date in enumerate(dates):
        _price(conn, "A", trade_date, high=200, low=90, close=100 + index * 2)
        conn.execute("INSERT INTO breadth_daily (trade_date) VALUES (?)", (trade_date,))

    first = bc.backfill_wave2_metrics(conn, sessions=3)
    second = bc.backfill_wave2_metrics(conn, sessions=3)

    assert first == second == 3
    rows = conn.execute(
        "SELECT COUNT(*) FROM breadth_daily WHERE up_25pct_month IS NOT NULL"
    ).fetchone()[0]
    assert rows == 3
