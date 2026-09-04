"""test_derive_tape_metrics.py -- hand-math coverage for derive/tape_metrics.py.

Disposable-DB pattern (same as test_adopted_activity.py): every test builds its
own tmp_path traderlog.db via ``init_db()`` and inserts synthetic
``daily_prices`` rows (``series='EQ'`` unless the test is about series
filtering), then asserts hand-computed values. No shared fixtures, no
production data -- and every expected number below is worked out by hand from
the inserted rows, not copied from the implementation.

Coverage per the foundation brief: exact session math for every function,
weekend/holiday gaps, insufficient-history nulls (never partial guesses), the
``series='EQ'`` filter, and determinism (same input twice -> identical).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from traderlog.db import init_db, now_iso
from traderlog.derive.tape_metrics import (
    ADR_DEFAULT_N,
    MOMENTUM_MOVE_PCT_MIN,
    adr,
    gap_marker,
    inside_bars,
    location,
    momentum_burst,
    snapshot,
    tightness,
    vcp_proxy,
    volume_character,
)


# ---------------------------------------------------------------------------
# Seeding helpers (synthetic daily_prices rows, series='EQ' by default)
# ---------------------------------------------------------------------------

def _insert_eq(conn, symbol, trade_date, *, open_, high, low, close,
               volume=100000, series="EQ"):
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, "
        "turnover, num_trades, delivery_pct, source, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol, trade_date, series, open_, high, low, close, close, volume,
         1, 1, 50.0, "test", now_iso()),
    )


def _seed(conn, rows):
    """rows: list of dicts {symbol, d, o, h, l, c, v?, series?}."""
    for row in rows:
        _insert_eq(
            conn, row["symbol"], row["d"],
            open_=row["o"], high=row["h"], low=row["l"], close=row["c"],
            volume=row.get("v", 100000), series=row.get("series", "EQ"),
        )
    conn.commit()


def _indexed(conn, symbol, n, start="2025-01-01", *, c0, step, h_off, l_off,
             volume=20000, today_volume=None):
    """n sessions one per calendar day: close=c0+step*i, high=close+h_off,
    low=close+l_off, open=close. Optional different volume on the last day."""
    base = date.fromisoformat(start)
    for i in range(n):
        close = c0 + step * i
        vol = today_volume if (i == n - 1 and today_volume is not None) else volume
        _insert_eq(
            conn, symbol, (base + timedelta(days=i)).isoformat(),
            open_=close, high=close + h_off, low=close + l_off, close=close,
            volume=vol,
        )
    conn.commit()


def _fresh_db(tmp_path, rows):
    conn = init_db(tmp_path / "traderlog.db")
    _seed(conn, rows)
    return conn


# ---------------------------------------------------------------------------
# adr
# ---------------------------------------------------------------------------

def test_adr_constant_ranges_hand_math(tmp_path):
    # Every session: (high-low)/close = (110-90)/100 = 0.2 -> ADR 20.0 (%).
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(20):
        _insert_eq(conn, "ADR1", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=110.0, low=90.0, close=100.0)
    conn.commit()
    assert adr(conn, "ADR1", "2025-01-20") == pytest.approx(20.0)


def test_adr_trailing_window_exact_session_math(tmp_path):
    # 25 sessions: indices 0..4 range 0.01, 5..19 range 0.06, 20..24 range 0.02.
    rows = []
    for i in range(25):
        if i < 5:
            h, l = 100.5, 99.5
        elif i < 20:
            h, l = 103.0, 97.0
        else:
            h, l = 101.0, 99.0
        rows.append({"symbol": "ADR2", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": h, "l": l, "c": 100.0})
    conn = _fresh_db(tmp_path, rows)

    # as_of = last session: last 20 = 15 x 0.06 + 5 x 0.02
    # mean = (15*0.06 + 5*0.02)/20 = 1.0/20 = 0.05 -> 5.0%.
    assert adr(conn, "ADR2", "2025-01-25") == pytest.approx(5.0)

    # as_of mid-series (22nd session): last 20 = 3 x 0.01 + 15 x 0.06 + 2 x 0.02
    # mean = (0.03 + 0.90 + 0.04)/20 = 0.97/20 = 0.0485 -> 4.85%.
    # Sessions after as_of must NOT leak in (they are higher-range).
    assert adr(conn, "ADR2", "2025-01-22") == pytest.approx(4.85)


def test_adr_weekend_and_holiday_as_of_use_actual_sessions(tmp_path):
    # Four Mon-Fri weeks, 2025-01-06..2025-01-31, with 2025-01-14 dropped
    # (market holiday): 19 real sessions of range 0.02 each.
    dates = []
    d = date(2025, 1, 6)
    while d <= date(2025, 1, 31):
        if d.weekday() < 5 and d.isoformat() != "2025-01-14":
            dates.append(d.isoformat())
        d += timedelta(days=1)
    assert len(dates) == 19  # 20 weekdays minus the holiday

    conn = init_db(tmp_path / "traderlog.db")
    for trade_date in dates:
        _insert_eq(conn, "WKEN", trade_date,
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.commit()

    # Friday as_of: all 19 sessions -> insufficient for n=20 -> None.
    assert adr(conn, "WKEN", "2025-01-31") is None
    # The missing holiday is a real session gap, not a fabricated zero-range day:
    # as_of just before it (13th) sees exactly 6 sessions -> still None.
    assert adr(conn, "WKEN", "2025-01-13") is None

    # A full 20-session series with weekend gaps BETWEEN sessions: as_of on a
    # Saturday/Sunday must equal as_of on the Friday (last session used).
    conn3 = init_db(tmp_path / "traderlog3.db")
    week = ["2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10",
            "2025-01-13", "2025-01-15", "2025-01-16", "2025-01-17", "2025-01-20",
            "2025-01-21", "2025-01-22", "2025-01-23", "2025-01-24", "2025-01-27",
            "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-03"]
    for trade_date in week:
        _insert_eq(conn3, "WK20", trade_date,
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn3.commit()
    assert adr(conn3, "WK20", "2025-02-03") == pytest.approx(2.0)  # last session
    assert adr(conn3, "WK20", "2025-02-08") == pytest.approx(2.0)  # Saturday
    assert adr(conn3, "WK20", "2025-02-09") == pytest.approx(2.0)  # Sunday


def test_adr_insufficient_history_is_null_never_partial(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(19):
        _insert_eq(conn, "SHORT", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.commit()
    assert adr(conn, "SHORT", "2025-01-19") is None

    conn2 = init_db(tmp_path / "traderlog2.db")
    for i in range(25):
        _insert_eq(conn2, "LONG", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn2.commit()
    assert adr(conn2, "LONG", "2025-01-25", n=30) is None  # asks for 30


def test_adr_ignores_non_eq_series(tmp_path):
    # The daily_prices primary key is (symbol, trade_date), so a non-EQ row can
    # only exist on a date with NO EQ row for the symbol.
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(20):
        _insert_eq(conn, "EQONLY", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    for i in range(5):  # BE rows on later dates with wild prices
        _insert_eq(conn, "EQONLY", f"2025-02-{i + 1:02d}",
                   open_=150.0, high=200.0, low=100.0, close=150.0,
                   series="BE")
    conn.commit()
    assert adr(conn, "EQONLY", "2025-02-05") == pytest.approx(2.0)


def test_adr_rejects_malformed_as_of_and_n(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for bad in (None, "", "not-a-date", "2025-13-01", "2025-01-32"):
        with pytest.raises(ValueError):
            adr(conn, "ANY", bad)
    with pytest.raises(ValueError):
        adr(conn, "ANY", "2025-01-01", n=0)


def test_adr_deterministic_twice(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(25):
        _insert_eq(conn, "DET", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.5, low=98.5, close=100.0)
    conn.commit()
    assert adr(conn, "DET", "2025-01-25") == adr(conn, "DET", "2025-01-25")


# ---------------------------------------------------------------------------
# tightness
# ---------------------------------------------------------------------------

def test_tightness_ratio5v20_hand_math(tmp_path):
    # 19 sessions range 0.02, then a final session range 0.01 (24 total):
    # five-mean = (4*0.02 + 0.01)/5 = 0.018; adr20 = (19*0.02 + 0.01)/20 =
    # 0.0195 -> ratio = 0.018/0.0195 = 12/13 = 0.92307692.
    rows = []
    for i in range(24):
        h, l = (101.0, 99.0) if i < 23 else (100.5, 99.5)
        rows.append({"symbol": "TG", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": h, "l": l, "c": 100.0})
    conn = _fresh_db(tmp_path, rows)
    t = tightness(conn, "TG", "2025-01-24")
    assert t["ratio5v20"] == pytest.approx(12.0 / 13.0)
    assert t["nr7"] is True    # today's 0.01 < all of the trailing 6 (0.02)
    assert t["nr4"] is True


def test_tightness_nr_flags_need_strictly_narrower_range(tmp_path):
    # Ties do NOT count: today's range equal to the prior 6 -> False/False.
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(8):
        _insert_eq(conn, "TIE", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.commit()
    t = tightness(conn, "TIE", "2025-01-08")
    assert t["nr7"] is False
    assert t["nr4"] is False


def test_tightness_null_fields_by_window(tmp_path):
    # 19 sessions (only today narrower: 0.01, the rest 0.02): ratio5v20 needs
    # 20 -> None, but nr7/nr4 still compute (today < all prior ranges).
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(19):
        h, l = (100.5, 99.5) if i == 18 else (101.0, 99.0)
        _insert_eq(conn, "PART", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=h, low=l, close=100.0)
    conn.commit()
    t = tightness(conn, "PART", "2025-01-19")
    assert t["ratio5v20"] is None
    assert t["nr7"] is True
    assert t["nr4"] is True

    # 3 sessions: nr4 needs 4 -> None as well.
    conn2 = init_db(tmp_path / "traderlog2.db")
    for i in range(3):
        _insert_eq(conn2, "TINY", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn2.commit()
    t2 = tightness(conn2, "TINY", "2025-01-03")
    assert t2 == {"ratio5v20": None, "nr7": None, "nr4": None}


def test_tightness_unusable_row_nulls_every_window_touching_it(tmp_path):
    # A NULL low inside the trailing windows must null the fields, never skip.
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(20):
        _insert_eq(conn, "DIRT", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.execute("UPDATE daily_prices SET low = NULL "
                 "WHERE symbol='DIRT' AND trade_date='2025-01-19'")
    conn.commit()
    t = tightness(conn, "DIRT", "2025-01-20")
    assert t == {"ratio5v20": None, "nr7": None, "nr4": None}


# ---------------------------------------------------------------------------
# volume_character
# ---------------------------------------------------------------------------

def test_volume_character_dry_up_hand_math(tmp_path):
    # 45 sessions vol 2000, then 5 sessions vol 1000:
    # 5d avg = 1000; 50d avg = (45*2000 + 5*1000)/50 = 1900;
    # dry_up = 1000/1900 = 0.526315789...
    base = date(2025, 1, 1)
    rows = []
    for i in range(50):
        rows.append({"symbol": "VOL",
                     "d": (base + timedelta(days=i)).isoformat(),
                     "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0,
                     "v": 1000 if i >= 45 else 2000})
    conn = _fresh_db(tmp_path, rows)
    v = volume_character(conn, "VOL", (base + timedelta(days=49)).isoformat())
    assert v["dry_up"] == pytest.approx(1000.0 / 1900.0)


def test_volume_character_surge_and_flag_hand_math(tmp_path):
    # 22 sessions: indices 0..20 vol 20000, today vol 100000.
    # 20d avg (today included) = (19*20000 + 100000)/20 = 24000;
    # surge = 100000/24000 = 4.1667 -> flag True.
    rows = []
    for i in range(22):
        rows.append({"symbol": "SURGE", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0,
                     "v": 100000 if i == 21 else 20000})
    conn = _fresh_db(tmp_path, rows)
    v = volume_character(conn, "SURGE", "2025-01-22")
    assert v["surge"] == pytest.approx(100000.0 / 24000.0)
    assert v["surge_flag"] is True
    assert v["dry_up"] is None  # only 22 sessions < the 50 needed


def test_volume_character_surge_boundary_inclusive(tmp_path):
    # Prior 19 sessions vol 90000; today vol 190000 ->
    # 20d avg = (19*90000 + 190000)/20 = 95000 -> surge = exactly 2.0 -> flag.
    rows = []
    for i in range(21):
        rows.append({"symbol": "BND", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0,
                     "v": 190000 if i == 20 else 90000})
    conn = _fresh_db(tmp_path, rows)
    v = volume_character(conn, "BND", "2025-01-21")
    assert v["surge"] == pytest.approx(2.0)
    assert v["surge_flag"] is True

    # Just below 2.0 -> flag False.
    rows2 = [{**row, "symbol": "BELOW"} for row in rows]
    rows2[-1]["v"] = 189999
    conn2 = init_db(tmp_path / "traderlog2.db")
    _seed(conn2, rows2)
    v2 = volume_character(conn2, "BELOW", "2025-01-21")
    assert v2["surge"] < 2.0
    assert v2["surge_flag"] is False


def test_volume_character_nulls_and_weekend_as_of(tmp_path):
    # 19 sessions -> surge AND dry_up both null, flag False.
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(19):
        _insert_eq(conn, "VSHORT", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0, volume=20000)
    conn.commit()
    v = volume_character(conn, "VSHORT", "2025-01-19")
    assert v == {"dry_up": None, "surge": None, "surge_flag": False}

    # Weekend as_of on a 21-session Mon-Fri series lands on Friday's own bar.
    week = ["2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10",
            "2025-01-13", "2025-01-14", "2025-01-15", "2025-01-16", "2025-01-17",
            "2025-01-20", "2025-01-21", "2025-01-22", "2025-01-23", "2025-01-24",
            "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
            "2025-02-03"]
    conn3 = init_db(tmp_path / "traderlog3.db")
    for i, trade_date in enumerate(week):
        _insert_eq(conn3, "WK", trade_date, open_=100.0, high=101.0, low=99.0,
                   close=100.0, volume=100000 if i == len(week) - 1 else 20000)
    conn3.commit()
    fri = volume_character(conn3, "WK", "2025-02-03")
    sat = volume_character(conn3, "WK", "2025-02-08")
    assert sat == fri
    assert fri["surge"] == pytest.approx(100000.0 / 24000.0)
    assert fri["surge_flag"] is True


# ---------------------------------------------------------------------------
# vcp_proxy
# ---------------------------------------------------------------------------

_VCP_CONTRACTING = [
    #            d           o     h     l     c
    ("2025-01-01", 88.0, 90.0, 88.0, 89.0),
    ("2025-01-02", 90.0, 92.0, 89.0, 90.0),
    ("2025-01-03", 93.0, 95.0, 90.0, 92.0),
    ("2025-01-04", 110.0, 120.0, 110.0, 112.0),   # swing high 1
    ("2025-01-05", 95.0, 100.0, 80.0, 90.0),     # deep pullback low
    ("2025-01-06", 100.0, 105.0, 95.0, 102.0),
    ("2025-01-07", 98.0, 102.0, 92.0, 96.0),
    ("2025-01-08", 105.0, 118.0, 100.0, 110.0),  # swing high 2 (lower)
    ("2025-01-09", 110.0, 115.0, 105.0, 112.0),
    ("2025-01-10", 108.0, 112.0, 100.0, 105.0),
    ("2025-01-11", 112.0, 116.0, 108.0, 113.0),
    ("2025-01-12", 100.0, 108.0, 95.0, 97.0),    # shallower pullback low
]


def test_vcp_proxy_depths_and_contracting_hand_math(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, o, h, l, c in _VCP_CONTRACTING:
        _insert_eq(conn, "VCPC", d, open_=o, high=h, low=l, close=c)
    conn.commit()

    v = vcp_proxy(conn, "VCPC", "2025-01-12")
    assert v is not None
    # Swing highs at 120 and 118 (K=3 left+right confirmation).
    # depth1 = (120 - min(low 01-05..01-08)) / 120 = (120-80)/120 = 33.3333%
    # depth2 = (118 - min(low 01-09..01-12)) / 118 = (118-95)/118 = 19.4915%
    assert v["depths"] == pytest.approx([100.0 / 3.0, 2300.0 / 118.0])
    assert v["contracting"] is True  # 19.49 < 33.33


def test_vcp_proxy_non_contracting_is_false(tmp_path):
    rows = [
        ("2025-02-01", 78.0, 80.0, 78.0, 79.0),
        ("2025-02-02", 82.0, 85.0, 80.0, 83.0),
        ("2025-02-03", 84.0, 88.0, 82.0, 85.0),
        ("2025-02-04", 96.0, 100.0, 95.0, 97.0),   # swing high 1
        ("2025-02-05", 91.0, 92.0, 90.0, 91.0),
        ("2025-02-06", 93.0, 95.0, 93.0, 94.0),
        ("2025-02-07", 92.0, 96.0, 91.0, 93.0),
        ("2025-02-08", 98.0, 102.0, 98.0, 100.0),  # swing high 2
        ("2025-02-09", 95.0, 98.0, 94.0, 96.0),
        ("2025-02-10", 94.0, 97.0, 93.0, 94.0),
        ("2025-02-11", 96.0, 99.0, 92.0, 95.0),
        ("2025-02-12", 90.0, 95.0, 88.0, 89.0),    # DEEPER pullback low
    ]
    conn = init_db(tmp_path / "traderlog.db")
    for d, o, h, l, c in rows:
        _insert_eq(conn, "VCPN", d, open_=o, high=h, low=l, close=c)
    conn.commit()

    v = vcp_proxy(conn, "VCPN", "2025-02-12")
    assert v is not None
    # depth1 = (100-90)/100 = 10.0%; depth2 = (102-88)/102 = 13.7255%
    assert v["depths"] == pytest.approx([10.0, 1400.0 / 102.0])
    assert v["contracting"] is False


def test_vcp_proxy_insufficient_history_is_null(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, o, h, l, c in _VCP_CONTRACTING[:6]:  # only 6 sessions
        _insert_eq(conn, "VCP6", d, open_=o, high=h, low=l, close=c)
    conn.commit()
    assert vcp_proxy(conn, "VCP6", "2025-01-06") is None


def test_vcp_proxy_single_pivot_is_honest_without_contraction(tmp_path):
    # 8 sessions, one confirmed swing high at index 3: depths has one element
    # and contracting is False (nothing to compare) -- never a partial guess.
    rows = [
        ("2025-03-01", 80.0, 82.0, 78.0, 80.0),
        ("2025-03-02", 84.0, 86.0, 82.0, 84.0),
        ("2025-03-03", 86.0, 88.0, 83.0, 85.0),
        ("2025-03-04", 95.0, 100.0, 92.0, 96.0),   # swing high
        ("2025-03-05", 90.0, 93.0, 88.0, 91.0),
        ("2025-03-06", 92.0, 94.0, 90.0, 92.0),
        ("2025-03-07", 93.0, 95.0, 91.0, 93.0),
        ("2025-03-08", 91.0, 92.0, 86.0, 88.0),    # later low -> depth window end
    ]
    conn = init_db(tmp_path / "traderlog.db")
    for d, o, h, l, c in rows:
        _insert_eq(conn, "VCP1", d, open_=o, high=h, low=l, close=c)
    conn.commit()
    v = vcp_proxy(conn, "VCP1", "2025-03-08")
    assert v is not None
    # depth = (100 - min(88, 90, 91, 86)) / 100 = (100-86)/100 = 14.0%
    assert v["depths"] == pytest.approx([14.0])
    assert v["contracting"] is False


# ---------------------------------------------------------------------------
# momentum_burst
# ---------------------------------------------------------------------------

def test_momentum_burst_fired_hand_math(tmp_path):
    # Closes 100 -> 104 (+4.0%); volumes 20000 x19 then 100000 -> multiple
    # = 100000 / ((19*20000 + 100000)/20) = 100000/24000 = 4.1667 -> fired.
    rows = []
    for i in range(22):
        rows.append({"symbol": "BURST", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0,
                     "c": 104.0 if i == 21 else 100.0,
                     "v": 100000 if i == 21 else 20000})
    conn = _fresh_db(tmp_path, rows)
    b = momentum_burst(conn, "BURST", "2025-01-22")
    assert b["move_pct"] == pytest.approx(4.0)
    assert b["vol_multiple"] == pytest.approx(100000.0 / 24000.0)
    assert b["fired"] is True


def test_momentum_burst_move_below_threshold_not_fired(tmp_path):
    rows = []
    for i in range(22):
        rows.append({"symbol": "SLOW", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0,
                     "c": 102.0 if i == 21 else 100.0,
                     "v": 100000 if i == 21 else 20000})
    conn = _fresh_db(tmp_path, rows)
    b = momentum_burst(conn, "SLOW", "2025-01-22")
    assert b["move_pct"] == pytest.approx(2.0)      # < X=3.0
    assert b["vol_multiple"] == pytest.approx(100000.0 / 24000.0)
    assert b["fired"] is False


def test_momentum_burst_volume_below_multiple_not_fired(tmp_path):
    rows = []
    for i in range(22):
        rows.append({"symbol": "QUIET", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0,
                     "c": 104.0 if i == 21 else 100.0,
                     "v": 25000 if i == 21 else 20000})
    conn = _fresh_db(tmp_path, rows)
    b = momentum_burst(conn, "QUIET", "2025-01-22")
    assert b["move_pct"] == pytest.approx(4.0)
    # multiple = 25000 / ((19*20000 + 25000)/20) = 25000/20250 = 1.2346 < 2
    assert b["vol_multiple"] == pytest.approx(25000.0 / 20250.0)
    assert b["fired"] is False


def test_momentum_burst_boundaries_are_inclusive(tmp_path):
    # move exactly 3.0 (X default) AND vol_multiple exactly 2.0 -> fired.
    rows = []
    for i in range(21):
        rows.append({"symbol": "EDGE", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0,
                     "c": 103.0 if i == 20 else 100.0,
                     "v": 190000 if i == 20 else 90000})
    conn = _fresh_db(tmp_path, rows)
    b = momentum_burst(conn, "EDGE", "2025-01-21")
    assert b["move_pct"] == pytest.approx(3.0)
    assert b["vol_multiple"] == pytest.approx(2.0)
    assert b["fired"] is True

    # move 2.9999 -> below X -> not fired.
    rows[-1]["c"] = 102.9999
    conn2 = init_db(tmp_path / "traderlog2.db")
    _seed(conn2, rows)
    assert momentum_burst(conn2, "EDGE", "2025-01-21")["fired"] is False


def test_momentum_burst_custom_threshold(tmp_path):
    # move 2.5% with move_pct_min=2.0 -> fired (vol multiple 2.0).
    rows = []
    for i in range(21):
        rows.append({"symbol": "CUST", "d": f"2025-01-{i + 1:02d}",
                     "o": 100.0, "h": 101.0, "l": 99.0,
                     "c": 102.5 if i == 20 else 100.0,
                     "v": 190000 if i == 20 else 90000})
    conn = _fresh_db(tmp_path, rows)
    b = momentum_burst(conn, "CUST", "2025-01-21", move_pct_min=2.0)
    assert b["move_pct"] == pytest.approx(2.5)
    assert b["fired"] is True
    # The default X is documented as 3.0 and would NOT fire here.
    assert MOMENTUM_MOVE_PCT_MIN == 3.0
    assert momentum_burst(conn, "CUST", "2025-01-21")["fired"] is False


def test_momentum_burst_insufficient_is_null_and_unfired(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_eq(conn, "SOLO", "2025-01-01", open_=100.0, high=101.0,
               low=99.0, close=104.0, volume=100000)
    conn.commit()
    b = momentum_burst(conn, "SOLO", "2025-01-01")
    assert b == {"move_pct": None, "vol_multiple": None, "fired": False}

    conn2 = init_db(tmp_path / "traderlog2.db")
    for i in range(19):
        _insert_eq(conn2, "NINETEEN", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0,
                   close=104.0 if i == 18 else 100.0, volume=20000)
    conn2.commit()
    b2 = momentum_burst(conn2, "NINETEEN", "2025-01-19")
    assert b2["move_pct"] == pytest.approx(4.0)  # computable with 2 closes
    assert b2["vol_multiple"] is None            # needs 20 volumes
    assert b2["fired"] is False


# ---------------------------------------------------------------------------
# inside_bars
# ---------------------------------------------------------------------------

def test_inside_bars_consecutive_count(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, h, l in (("2025-01-01", 10.0, 2.0),
                    ("2025-01-02", 9.0, 3.0),
                    ("2025-01-03", 8.0, 4.0)):
        _insert_eq(conn, "IB", d, open_=h, high=h, low=l, close=(h + l) / 2)
    conn.commit()
    # 01-03 inside 01-02 (8<9, 4>3); 01-02 inside 01-01 (9<10, 3>2) -> 2.
    assert inside_bars(conn, "IB", "2025-01-03") == 2


def test_inside_bars_zero_when_today_not_inside(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, h, l in (("2025-01-01", 10.0, 2.0),
                    ("2025-01-02", 9.0, 3.0),
                    ("2025-01-03", 11.0, 3.0)):  # wider than prior
        _insert_eq(conn, "IB", d, open_=h, high=h, low=l, close=(h + l) / 2)
    conn.commit()
    assert inside_bars(conn, "IB", "2025-01-03") == 0


def test_inside_bars_ties_do_not_count(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, h, l in (("2025-01-01", 10.0, 2.0),
                    ("2025-01-02", 9.0, 3.0),
                    ("2025-01-03", 9.0, 4.0)):  # high equal to prior -> not strict
        _insert_eq(conn, "IB", d, open_=h, high=h, low=l, close=(h + l) / 2)
    conn.commit()
    assert inside_bars(conn, "IB", "2025-01-03") == 0


def test_inside_bars_chain_breaks_at_first_failure(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for d, h, l in (("2025-01-01", 10.0, 2.0),
                    ("2025-01-02", 9.0, 3.0),   # inside 01-01 (would count)
                    ("2025-01-03", 12.0, 1.0),  # breakout bar: chain breaks
                    ("2025-01-04", 11.0, 4.0)):  # inside 01-03 only
        _insert_eq(conn, "IB", d, open_=h, high=h, low=l, close=(h + l) / 2)
    conn.commit()
    assert inside_bars(conn, "IB", "2025-01-04") == 1


def test_inside_bars_insufficient_is_null(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_eq(conn, "IB", "2025-01-01", open_=10.0, high=10.0,
               low=2.0, close=6.0)
    conn.commit()
    assert inside_bars(conn, "IB", "2025-01-01") is None


# ---------------------------------------------------------------------------
# gap_marker
# ---------------------------------------------------------------------------

def test_gap_marker_earnings_style_flag_hand_math(tmp_path):
    # 20 identical sessions (range 0.02) + today: open 104 vs prior high 101.
    # gap_ratio = (104-101)/100 = 0.03; ADR20 (today included) =
    # (19*0.02 + (104-102)/104)/20 = (0.38 + 2/104)/20 = 0.01996153846.
    # 0.03 >= 1.0 * ADR -> flag True. gap_pct = 3.0.
    rows = []
    for i in range(21):
        if i == 20:
            rows.append({"symbol": "GAP", "d": "2025-01-21",
                         "o": 104.0, "h": 104.0, "l": 102.0, "c": 104.0})
        else:
            rows.append({"symbol": "GAP", "d": f"2025-01-{i + 1:02d}",
                         "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0})
    conn = _fresh_db(tmp_path, rows)
    g = gap_marker(conn, "GAP", "2025-01-21")
    assert g["gap_pct"] == pytest.approx(3.0)
    assert g["gap_flag"] is True


def test_gap_marker_below_adr_or_not_above_prior_high(tmp_path):
    def build(today_open):
        rows = []
        for i in range(21):
            if i == 20:
                rows.append({"symbol": "GAP", "d": "2025-01-21",
                             "o": today_open, "h": max(today_open, 101.0),
                             "l": min(today_open - 2.0, 99.0), "c": 104.0})
            else:
                rows.append({"symbol": "GAP", "d": f"2025-01-{i + 1:02d}",
                             "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0})
        return rows

    # open 101.5: above prior high (101) but gap 0.5% < ADR ~2.0% -> no flag.
    conn = _fresh_db(tmp_path, build(101.5))
    g = gap_marker(conn, "GAP", "2025-01-21")
    assert g["gap_pct"] == pytest.approx(0.5)
    assert g["gap_flag"] is False

    # open 100.5: NOT above the prior high at all -> no flag.
    conn2 = init_db(tmp_path / "traderlog2.db")
    _seed(conn2, build(100.5))
    g2 = gap_marker(conn2, "GAP", "2025-01-21")
    assert g2["gap_pct"] == pytest.approx(-0.5)
    assert g2["gap_flag"] is False


def test_gap_marker_insufficient_is_null(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(19):
        _insert_eq(conn, "GAP", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.commit()
    assert gap_marker(conn, "GAP", "2025-01-19") == {"gap_pct": None,
                                                     "gap_flag": None}


# ---------------------------------------------------------------------------
# location
# ---------------------------------------------------------------------------

def test_location_52w_high_and_sma_flags_uptrend(tmp_path):
    # 252 sessions, close = 100 + 0.5*i, high = close + 1, low = close - 1.
    # 52w high = 100 + 251*0.5 + 1 = 226.5; today close = 225.5;
    # pct = (225.5/226.5 - 1)*100 = (-2/453)*100 = -200/453.
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(252):
        close = 100.0 + 0.5 * i
        _insert_eq(conn, "UP", f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                   open_=close, high=close + 1.0, low=close - 1.0, close=close)
    conn.commit()
    loc = location(conn, "UP", "2025-12-31")  # covers every session
    assert loc["pct_from_52w_high"] == pytest.approx(-200.0 / 453.0)
    assert loc["above_sma10"] is True
    assert loc["above_sma20"] is True
    assert loc["above_sma50"] is True
    assert loc["above_sma200"] is True


def test_location_downtrend_sma_flags_false_and_52w_null_below_252(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(200):
        close = 300.0 - i
        _insert_eq(conn, "DOWN", f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                   open_=close, high=close + 1.0, low=close - 1.0, close=close)
    conn.commit()
    loc = location(conn, "DOWN", "2025-12-31")  # covers every session
    assert loc["pct_from_52w_high"] is None  # only 200 sessions < 252
    assert loc["above_sma10"] is False
    assert loc["above_sma20"] is False
    assert loc["above_sma50"] is False
    assert loc["above_sma200"] is False


def test_location_null_by_window(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(8):
        _insert_eq(conn, "NEW", f"2025-01-{i + 1:02d}",
                   open_=100.0, high=101.0, low=99.0, close=100.0)
    conn.commit()
    loc = location(conn, "NEW", "2025-01-08")
    assert loc["pct_from_52w_high"] is None
    assert loc["above_sma10"] is None   # needs 10 sessions
    assert loc["above_sma20"] is None
    assert loc["above_sma50"] is None
    assert loc["above_sma200"] is None


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def _snapshot_series(conn, symbol, n, *, today_volume):
    for i in range(n):
        close = 100.0 + 0.5 * i
        vol = today_volume if i == n - 1 else 20000
        _insert_eq(conn, symbol, f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                   open_=close, high=close + 1.5, low=close - 1.0,
                   close=close, volume=vol)
    conn.commit()


def test_snapshot_combines_all_metrics(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _snapshot_series(conn, "SNAP", 260, today_volume=100000)
    s = snapshot(conn, "SNAP", "2025-12-31")  # as_of covers every session

    assert s["symbol"] == "SNAP"
    assert s["series"] == "EQ"
    assert s["session_count"] == 260
    assert s["insufficient_history"] is False
    # 260 sessions seeded as 28-day pseudo-months: i=259 -> month 10, day 8.
    assert s["as_of_session"] == "2025-10-08"

    # Hand values.
    assert s["adr_pct"] == adr(conn, "SNAP", "2025-12-31")
    # 52w high = close(259) + 1.5 = 229.5 + 1.5 = 231.0; today close 229.5.
    assert s["location"]["pct_from_52w_high"] == pytest.approx(-150.0 / 231.0)
    # Today volume 100000 vs 20d avg (19*20000 + 100000)/20 = 24000.
    assert s["volume_character"]["surge"] == pytest.approx(100000.0 / 24000.0)
    assert s["volume_character"]["surge_flag"] is True
    # Monotone-rising highs: today's high > prior high -> no inside bar.
    assert s["inside_bars"] == 0
    # Closes 229.0 -> 229.5: move 0.218% < 3.0 -> no burst despite volume.
    assert s["momentum_burst"]["move_pct"] == pytest.approx(
        (229.5 / 229.0 - 1.0) * 100.0)
    assert s["momentum_burst"]["fired"] is False
    # Today's open equals its close, prior high = 229.0 + 1.5 = 230.5:
    # not above the prior high -> no gap.
    assert s["gap_marker"]["gap_flag"] is False
    assert s["gap_marker"]["gap_pct"] == pytest.approx(
        (229.5 - 230.5) / 229.0 * 100.0)
    # Structural sanity for the shape metrics.
    assert set(s["tightness"]) == {"ratio5v20", "nr7", "nr4"}
    assert isinstance(s["vcp_proxy"], dict)
    assert set(s["vcp_proxy"]) == {"depths", "contracting"}
    assert set(s["location"]) == {"pct_from_52w_high", "above_sma10",
                                  "above_sma20", "above_sma50", "above_sma200"}


def test_snapshot_insufficient_history_marker_and_nulls(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_eq(conn, "SOLO", "2025-01-01", open_=100.0, high=101.0,
               low=99.0, close=100.0, volume=20000)
    conn.commit()
    s = snapshot(conn, "SOLO", "2025-01-01")
    assert s["insufficient_history"] is True
    assert s["session_count"] == 1
    assert s["as_of_session"] == "2025-01-01"
    assert s["adr_pct"] is None
    assert s["tightness"] == {"ratio5v20": None, "nr7": None, "nr4": None}
    assert s["volume_character"] == {"dry_up": None, "surge": None,
                                     "surge_flag": False}
    assert s["vcp_proxy"] is None
    assert s["momentum_burst"] == {"move_pct": None, "vol_multiple": None,
                                   "fired": False}
    assert s["inside_bars"] is None
    assert s["gap_marker"] == {"gap_pct": None, "gap_flag": None}
    assert s["location"]["pct_from_52w_high"] is None
    assert s["location"]["above_sma10"] is None

    # No rows at all: honest empty read, never invented prices.
    s0 = snapshot(conn, "GHOST", "2025-01-01")
    assert s0["session_count"] == 0
    assert s0["as_of_session"] is None
    assert s0["insufficient_history"] is True


def test_snapshot_deterministic_twice(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _snapshot_series(conn, "DETSNAP", 120, today_volume=50000)
    first = snapshot(conn, "DETSNAP", "2025-05-01")
    second = snapshot(conn, "DETSNAP", "2025-05-01")
    assert first == second


def test_snapshot_malformed_as_of_raises(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    with pytest.raises(ValueError):
        snapshot(conn, "X", "2025-13-01")


# ---------------------------------------------------------------------------
# determinism across every public function
# ---------------------------------------------------------------------------

def test_all_functions_deterministic_same_input_twice(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _snapshot_series(conn, "DETALL", 260, today_volume=100000)
    as_of = "2025-09-10"
    funcs = [
        lambda: adr(conn, "DETALL", as_of),
        lambda: tightness(conn, "DETALL", as_of),
        lambda: volume_character(conn, "DETALL", as_of),
        lambda: vcp_proxy(conn, "DETALL", as_of),
        lambda: momentum_burst(conn, "DETALL", as_of),
        lambda: inside_bars(conn, "DETALL", as_of),
        lambda: gap_marker(conn, "DETALL", as_of),
        lambda: location(conn, "DETALL", as_of),
    ]
    for fn in funcs:
        assert fn() == fn(), f"non-deterministic result from {fn}"
    assert ADR_DEFAULT_N == 20