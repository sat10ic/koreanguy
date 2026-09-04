from __future__ import annotations

from datetime import date, timedelta

import pytest

from manas_os import db
from manas_os.screeners import calibrate
from manas_os.sources import chartsmaze


_RUN_DATE = "2026-02-02"


def _build_dump(tmp_path, rows: str, run_date: str = _RUN_DATE):
    root = tmp_path / "cm"
    folder = root / run_date / "scanners"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "volume-spike.csv").write_text(rows, encoding="utf-8")
    return root


def _insert_bars(conn, symbol, dates, close=1000.0, base_volume=100_000, final_volume=100_000):
    for d in dates[:-1]:
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol, trade_date, series, open, high, low, close, volume) "
            "VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?)",
            (symbol, d, close - 1, close + 1, close - 2, close, base_volume),
        )
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, volume) "
        "VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?)",
        (symbol, dates[-1], close - 1, close + 1, close - 2, close, final_volume),
    )


def _seed_prices(conn, run_date: str = _RUN_DATE):
    start = date(2026, 1, 5)
    symbols = ("AAA", "BBB", "CCC")
    dates = [(start + timedelta(days=i)).isoformat() for i in range(20)] + [run_date]
    for sym, vol in (("AAA", 300_000), ("BBB", 150_000), ("CCC", 250_000)):
        _insert_bars(conn, sym, dates, final_volume=vol)
    conn.commit()


@pytest.fixture
def fake_cm(tmp_path, monkeypatch):
    root = _build_dump(
        tmp_path,
        "Stock Name,RS Rating,Basic Industry\n"
        "AAA,91,Test Industry\n"
        "BBB,82,Test Industry\n",
    )
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    return root


def test_load_their_hits_preserves_dynamic_columns(fake_cm):
    hits, frame = calibrate.load_their_hits("volume-spike", _RUN_DATE)

    assert hits == {"AAA", "BBB"}
    assert "RS Rating" in frame.columns
    assert set(frame["symbol"]) == {"AAA", "BBB"}


def test_calibrate_reports_known_jaccard(fake_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_prices(conn)
    finally:
        conn.close()

    result = calibrate.calibrate(
        "volume-spike",
        calibrate.volume_spike_compute_fn(2.0),
        _RUN_DATE,
        _RUN_DATE,
        db_path=tmp_path / "manas.db",
    )

    assert result["summary"]["median_raw_jaccard"] == pytest.approx(1 / 3)
    assert result["summary"]["median_universe_jaccard"] == pytest.approx(1 / 2)
    assert result["summary"]["dates_n"] == 1
    row = result["rows"][0]
    assert row["dump_date"] == _RUN_DATE
    assert row["trade_date"] == _RUN_DATE
    assert row["ours_n"] == 2
    assert row["theirs_n"] == 2
    assert row["raw_jaccard"] == pytest.approx(1 / 3)
    assert row["universe_jaccard"] == pytest.approx(1 / 2)
    assert row["only_ours"] == ["CCC"]
    assert row["only_theirs"] == ["BBB"]


def test_calibrate_maps_weekend_dump_to_prior_trade_date_and_dedupes(tmp_path, monkeypatch):
    friday = "2026-02-06"
    saturday = "2026-02-07"
    sunday = "2026-02-08"
    root = _build_dump(
        tmp_path,
        "Stock Name,RS Rating,Basic Industry\nAAA,91,Test Industry\n",
        run_date=friday,
    )
    _build_dump(
        tmp_path,
        "Stock Name,RS Rating,Basic Industry\nAAA,91,Test Industry\n",
        run_date=saturday,
    )
    _build_dump(
        tmp_path,
        "Stock Name,RS Rating,Basic Industry\nAAA,91,Test Industry\n",
        run_date=sunday,
    )
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _seed_prices(conn, friday)
    finally:
        conn.close()

    result = calibrate.calibrate(
        "volume-spike",
        lambda _conn, trade_date: {"AAA"} if trade_date == friday else set(),
        friday,
        sunday,
        db_path=tmp_path / "manas.db",
    )

    assert [r["dump_date"] for r in result["rows"]] == [friday]
    assert result["rows"][0]["trade_date"] == friday
    assert result["rows"][0]["raw_jaccard"] == pytest.approx(1.0)
    assert result["skipped"] == [
        {"dump_date": saturday, "trade_date": friday, "reason": "duplicate mapped trade_date"},
        {"dump_date": sunday, "trade_date": friday, "reason": "duplicate mapped trade_date"},
    ]


def test_volume_spike_compute_applies_tradeable_universe_filter(tmp_path):
    run_date = "2026-02-02"
    conn = db.init_db(tmp_path / "manas.db")
    try:
        start = date(2026, 1, 5)
        dates = [(start + timedelta(days=i)).isoformat() for i in range(20)] + [run_date]
        _insert_bars(conn, "GOODCO", dates, close=1000.0, base_volume=100_000, final_volume=300_000)
        _insert_bars(conn, "PENNYCO", dates, close=20.0, base_volume=1_000_000, final_volume=3_000_000)
        _insert_bars(conn, "THINCO", dates, close=100.0, base_volume=10_000, final_volume=30_000)
        _insert_bars(conn, "GOLDBEES", dates, close=1000.0, base_volume=100_000, final_volume=300_000)
        conn.commit()

        hits = calibrate.volume_spike_compute_fn(2.0)(conn, run_date)
    finally:
        conn.close()

    assert hits == {"GOODCO"}


def test_value_calibrate_abs_error_summary(tmp_path, monkeypatch):
    root = _build_dump(
        tmp_path,
        "Stock Name,Custom Value\n"
        "AAA,10\n"
        "BBB,20\n",
    )
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol, trade_date, series, open, high, low, close, volume) "
            "VALUES ('AAA', ?, 'EQ', 100, 101, 99, 100, 100000)",
            (_RUN_DATE,),
        )
        conn.commit()
    finally:
        conn.close()

    values = {"AAA": 12, "BBB": 17}

    result = calibrate.value_calibrate(
        "volume-spike",
        "Custom Value",
        lambda _conn, _run_date, symbol: values[symbol],
        _RUN_DATE,
        _RUN_DATE,
        db_path=tmp_path / "manas.db",
    )

    assert result["summary"]["n"] == 2
    assert result["summary"]["median_abs_error"] == pytest.approx(2.5)
    assert result["summary"]["p90_abs_error"] == pytest.approx(2.9)
