import json
from datetime import date as _date

from fastapi.testclient import TestClient

from manas_os import db, market_calendar
from manas_os.api import app as api_app
from manas_os.regime import snapshot


def _breadth_row(**overrides):
    row = {
        "trade_date": "2026-07-04",
        "advances": 1200,
        "declines": 500,
        "up_4pct": 120,
        "down_4pct": 30,
        "up_25pct_month": 0,
        "down_25pct_month": 0,
        "up_50pct_month": 0,
        "down_50pct_month": 0,
        "pct_above_10dma": 60.0,
        "pct_above_20dma": 58.0,
        "pct_above_40dma": 57.0,
        "pct_10dma_gt_20dma": 62.0,
        "pct_20dma_gt_40dma": 59.0,
        "nifty": 25000.0,
        "nifty_chg_pct": 0.7,
    }
    row.update(overrides)
    return row


def _insert_breadth(conn, trade_date="2026-07-04", **overrides):
    row = _breadth_row(trade_date=trade_date, **overrides)
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, up_4pct, down_4pct, "
        "up_25pct_month, down_25pct_month, up_50pct_month, down_50pct_month, "
        "pct_above_10dma, pct_above_20dma, pct_above_40dma, pct_10dma_gt_20dma, "
        "pct_20dma_gt_40dma, nifty, nifty_chg_pct) "
        "VALUES (:trade_date, :advances, :declines, :up_4pct, :down_4pct, "
        ":up_25pct_month, :down_25pct_month, :up_50pct_month, :down_50pct_month, "
        ":pct_above_10dma, :pct_above_20dma, :pct_above_40dma, :pct_10dma_gt_20dma, "
        ":pct_20dma_gt_40dma, :nifty, :nifty_chg_pct)",
        row,
    )


def test_mbi_ratio_banding_boundaries():
    assert snapshot.band_ratio(75.0) == "GREEN"
    assert snapshot.band_ratio(50.0) == "WHITE"
    assert snapshot.band_ratio(49.99) == "RED"
    assert snapshot.band_r4p5(49.99) == "RED"
    assert snapshot.band_r4p5(50.0) == "WHITE"
    assert snapshot.band_r4p5(200.0) == "GREEN"
    assert snapshot.band_r4p5(400.0) == "ORANGE"


def test_day_color_scoring_and_warning_trigger():
    green = snapshot.compute_mbi(_breadth_row(pct_above_10dma=60, pct_above_20dma=58, up_4pct=120, down_4pct=30))
    assert green["mbi_day_color"] == "GREEN"
    assert green["warning_day"] is False

    red = snapshot.compute_mbi(_breadth_row(pct_above_10dma=25, pct_above_20dma=30, up_4pct=10, down_4pct=40))
    assert red["mbi_day_color"] == "RED"
    assert red["warning_day"] is True

    mixed = snapshot.compute_mbi(_breadth_row(pct_above_10dma=35, pct_above_20dma=55, up_4pct=60, down_4pct=60))
    assert mixed["mbi_day_color"] == "WHITE"
    assert mixed["warning_day"] is False


def test_market_mode_mapping_from_constructed_breadth_rows():
    bullish = snapshot.build_snapshot(_breadth_row(), "2026-07-04", "2026-07-04", 31.2, 36.2)
    # Volatility is unknown with today's schema, so even a bullish breadth day
    # cannot honestly become RISK_ON yet.
    assert bullish["market_mode"] == "SELECTIVE"
    assert bullish["pillars_passed"] == 3
    assert bullish["mbi_day_color"] == "GREEN"

    bearish = snapshot.build_snapshot(
        _breadth_row(
            pct_above_10dma=25,
            pct_above_20dma=30,
            pct_above_40dma=35,
            pct_10dma_gt_20dma=30,
            pct_20dma_gt_40dma=30,
            up_4pct=10,
            down_4pct=40,
            nifty_chg_pct=-1.1,
        ),
        "2026-07-04",
        "2026-07-04",
        8.0,
        20.0,
    )
    assert bearish["market_mode"] == "NO_TRADE"
    assert bearish["mbi_day_color"] == "RED"
    assert bearish["warning_day"] == 1

    mixed = snapshot.build_snapshot(
        _breadth_row(pct_above_10dma=45, pct_above_20dma=55, up_4pct=50, down_4pct=50, nifty_chg_pct=0),
        "2026-07-04",
        "2026-07-04",
        20.0,
        25.0,
    )
    assert mixed["market_mode"] == "SELECTIVE"


def test_stale_data_hard_degrades_risk_on():
    snap = snapshot.build_snapshot(_breadth_row(), "2026-07-04", "2026-07-02", 31.2, 36.2)
    assert snap["data_stale"] == 1
    assert snap["market_mode"] == "SELECTIVE"
    # explanation_text is now the plain-English primary read; the old
    # var=value audit trail (incl. this exact phrase) moved to
    # technical_detail, kept for traceability but not shown by default.
    # BUG FIX (JOB 1): a stale read must lead with the staleness and never
    # assert "breadth is green / checks favourable" as an actionable claim —
    # that directly contradicted a STALE posture badge. It must not claim
    # today's checks are favourable outright; last-known values are labelled
    # as such.
    assert "Data is" in snap["explanation_text"]
    assert "old" in snap["explanation_text"]
    assert "last-known" in snap["explanation_text"]
    assert "not today's read" in snap["explanation_text"]
    assert "cannot be RISK_ON" in snap["technical_detail"]


def test_run_smoke_writes_snapshot_and_pipeline_row(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_breadth(conn)
        result = snapshot.run(conn, "2026-07-04")
        assert result["status"] == "ok"
        row = conn.execute("SELECT * FROM regime_snapshots WHERE snapshot_date='2026-07-04'").fetchone()
        assert row["market_mode"] == "SELECTIVE"
        assert row["xp_value"] is not None
        assert row["mbi_day_color"] == "GREEN"
        assert json.loads(row["quadrant_json"])["swing"]["state"] == "UP"

        run = conn.execute("SELECT status FROM pipeline_runs WHERE stage='regime_snapshot'").fetchone()
        assert run["status"] == "ok"
    finally:
        conn.close()


def test_run_skips_and_does_not_write_snapshot_when_no_breadth_row_for_run_date(tmp_path):
    """Phantom-snapshot guard: an eod run on a day with no fresh breadth_daily
    row for run_date itself must not write a regime_snapshots row for that
    date, even if an older breadth_daily row exists (which would otherwise get
    silently duplicated under the new date's snapshot)."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _insert_breadth(conn, trade_date="2026-04-22")
        result = snapshot.run(conn, "2026-07-05")
        assert result["status"] == "skip"
        assert result["rows_affected"] == 0

        row = conn.execute(
            "SELECT * FROM regime_snapshots WHERE snapshot_date='2026-07-05'"
        ).fetchone()
        assert row is None

        run = conn.execute(
            "SELECT status, detail FROM pipeline_runs WHERE stage='regime_snapshot' "
            "AND run_date='2026-07-05'"
        ).fetchone()
        assert run["status"] == "skip"
        assert "breadth_daily" in run["detail"]
    finally:
        conn.close()


def test_regime_summary_api_returns_real_snapshot_json(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_breadth(conn)
        snapshot.run(conn, "2026-07-04")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)
    res = client.get("/api/regime/summary", params={"date": "2026-07-04"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["as_of"] == "2026-07-04"
    assert payload["market_mode"] == "SELECTIVE"
    assert isinstance(payload["preferred_setups"], list)
    assert isinstance(payload["avoid_setups"], list)
    assert payload["quadrant"]["trend"]["state"] == "UP"


def test_regime_history_api_returns_limited_ascending_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        rows = [
            ("2026-07-01", 18.0, "DEFENSIVE", "RED", 1),
            ("2026-07-02", 21.5, "SELECTIVE", "WHITE", 0),
            ("2026-07-03", 28.0, "RISK_ON", "GREEN", 0),
        ]
        conn.executemany(
            "INSERT INTO regime_snapshots "
            "(snapshot_date, xp_value, market_mode, mbi_day_color, warning_day) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)
    res = client.get("/api/regime/history", params={"date": "2026-07-03", "days": 2})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert [r["snapshot_date"] for r in payload["rows"]] == ["2026-07-02", "2026-07-03"]
    assert len(payload["rows"]) == 2
    assert all(
        set(r) == {
            "snapshot_date", "xp_value", "market_mode", "mbi_day_color", "warning_day",
            "r4p5", "r10", "r20", "r50",
        }
        for r in payload["rows"]
    )


def test_regime_breadth_history_api_returns_limited_ascending_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_breadth(conn, trade_date="2026-07-01", pct_above_20dma=51.0, advances=900, declines=700)
        _insert_breadth(conn, trade_date="2026-07-02", pct_above_20dma=54.5, advances=1000, declines=650)
        _insert_breadth(conn, trade_date="2026-07-03", pct_above_20dma=53.0, advances=950, declines=720)
        conn.commit()
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)
    res = client.get("/api/regime/breadth-history", params={"date": "2026-07-03", "days": 2})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert [r["trade_date"] for r in payload["rows"]] == ["2026-07-02", "2026-07-03"]
    assert len(payload["rows"]) == 2
    assert all(
        set(r) == {"trade_date", "pct_above_20dma", "pct_above_40dma", "pct_above_50dma", "advances", "declines"}
        for r in payload["rows"]
    )


def test_saturday_with_friday_snapshot_is_not_stale(tmp_path, monkeypatch):
    """JOB 3: a weekend/holiday alone must never trip the stale banner. A
    snapshot dated Friday 2026-07-03, viewed as of Saturday 2026-07-04 (no
    trading day missed in between), must read data_stale=0 and days_behind=0
    — the old calendar-day math would have falsely flagged this as 1 day
    stale."""
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _insert_breadth(conn, trade_date="2026-07-03")
        snapshot.run(conn, "2026-07-03")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))

    class _FixedDate(_date):
        @classmethod
        def today(cls):
            return _date(2026, 7, 4)  # Saturday

    monkeypatch.setattr(api_app, "_date", _FixedDate)

    client = TestClient(api_app.app)
    res = client.get("/api/regime/summary", params={"date": "2026-07-04"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["snapshot_date"] == "2026-07-03"
    assert payload["days_behind"] == 0
    assert payload["data_stale"] == 0


def test_market_calendar_trading_days_between_skips_weekend():
    friday = _date(2026, 7, 3)
    saturday = _date(2026, 7, 4)
    monday = _date(2026, 7, 6)
    assert market_calendar.trading_days_between(friday, saturday) == 0
    # Friday -> Monday: Sat/Sun are the only days strictly between, both
    # non-trading, so still 0 trading days behind.
    assert market_calendar.trading_days_between(friday, monday) == 0
    assert market_calendar.last_trading_day(saturday) == friday
    assert market_calendar.last_trading_day(friday) == friday
