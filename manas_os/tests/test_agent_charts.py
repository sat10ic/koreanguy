from pathlib import Path

from manas_os import db
from manas_os.agents import charts
from manas_os.tests.conftest import insert_price_ramp


def test_render_charts_writes_daily_and_weekly_pngs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = insert_price_ramp(conn, symbol="ACME", n=210)

        result = charts.render_charts(conn, scan_date, ["ACME"])

        assert set(result["ACME"]) == {"daily", "weekly"}
        daily = Path(result["ACME"]["daily"])
        weekly = Path(result["ACME"]["weekly"])
        assert daily == Path("data") / "agent_charts" / scan_date / "ACME_daily.png"
        assert weekly == Path("data") / "agent_charts" / scan_date / "ACME_weekly.png"
        assert daily.exists()
        assert weekly.exists()
        assert daily.stat().st_size > 5_000
        assert weekly.stat().st_size > 5_000
    finally:
        conn.close()


def test_render_charts_skips_thin_symbol_without_raising_or_writing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = insert_price_ramp(conn, symbol="THIN", n=10)

        result = charts.render_charts(conn, scan_date, ["THIN"])

        assert result == {"THIN": {"note": "skipped: only 10 daily bars (<30)"}}
        assert not (Path("data") / "agent_charts" / scan_date / "THIN_daily.png").exists()
        assert not (Path("data") / "agent_charts" / scan_date / "THIN_weekly.png").exists()
    finally:
        conn.close()


def test_weekly_resample_caps_two_year_window_at_about_110_candles(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = insert_price_ramp(conn, symbol="ACME", n=520)

        weekly = charts._weekly_frame(conn, "ACME", scan_date)

        assert 90 <= len(weekly) <= 110
    finally:
        conn.close()
