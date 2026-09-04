"""F7: fii_dii ingest — parse/upsert logic + failure-safe skip, no network."""
import json

from manas_os import db
from manas_os.sources import fii_dii

AS_OF = "2026-07-08"


def _fixture_html(rows):
    payload = {"props": {"pageProps": {"initialData": rows}}}
    return (
        "<html><head></head><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
        "</body></html>"
    )


def _rows():
    return [
        {
            "date": "2026-07-08",
            "fii": {"grossBuy": 17463.95, "grossSell": 15501.15, "netBuySell": 1962.8},
            "dii": {"grossBuy": 19165.13, "grossSell": 18374.97, "netBuySell": 790.16},
        },
        {
            "date": "2026-07-07",
            "fii": {"grossBuy": 18414.01, "grossSell": 18020.82, "netBuySell": 393.19},
            "dii": {"grossBuy": 18897.44, "grossSell": 19280.87, "netBuySell": -383.43},
        },
    ]


def test_parse_groww_html_extracts_next_data_rows():
    html = _fixture_html(_rows())
    parsed = fii_dii.parse_groww_html(html)
    assert len(parsed) == 2
    assert parsed[0]["trade_date"] == "2026-07-08"
    assert parsed[0]["fii_net"] == 1962.8
    assert parsed[0]["dii_net"] == 790.16
    assert parsed[0]["source"] == "groww_fii_dii"
    assert parsed[1]["trade_date"] == "2026-07-07"
    assert parsed[1]["dii_net"] == -383.43


def test_parse_groww_html_raises_when_next_data_missing():
    try:
        fii_dii.parse_groww_html("<html><body>no data here</body></html>")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_run_upserts_fetched_rows_and_logs_ok(tmp_path):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        rows = fii_dii.parse_groww_html(_fixture_html(_rows()))
        n = fii_dii.run(conn, AS_OF, fetcher=lambda: rows)
        assert n == 2

        got = conn.execute(
            "SELECT trade_date, fii_net, dii_net, source FROM fii_dii_daily ORDER BY trade_date"
        ).fetchall()
        assert len(got) == 2
        assert got[1]["trade_date"] == "2026-07-08"
        assert got[1]["fii_net"] == 1962.8
        assert got[1]["source"] == "groww_fii_dii"

        run_row = conn.execute(
            "SELECT status, rows_affected, stage, source FROM pipeline_runs "
            "WHERE stage='ingest_fii_dii' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run_row["status"] == "ok"
        assert run_row["rows_affected"] == 2
        assert run_row["source"] == "groww_fii_dii"
    finally:
        conn.close()


def test_run_is_idempotent_on_rerun(tmp_path):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        rows = fii_dii.parse_groww_html(_fixture_html(_rows()))
        fii_dii.run(conn, AS_OF, fetcher=lambda: rows)
        n2 = fii_dii.run(conn, AS_OF, fetcher=lambda: rows)
        assert n2 == 2
        count = conn.execute("SELECT COUNT(*) c FROM fii_dii_daily").fetchone()["c"]
        assert count == 2  # upsert, not duplicate rows
    finally:
        conn.close()


def test_run_skips_and_never_raises_on_fetch_error(tmp_path):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        def boom():
            raise ConnectionError("network unreachable")

        n = fii_dii.run(conn, AS_OF, fetcher=boom)
        assert n == 0

        count = conn.execute("SELECT COUNT(*) c FROM fii_dii_daily").fetchone()["c"]
        assert count == 0

        run_row = conn.execute(
            "SELECT status, detail FROM pipeline_runs "
            "WHERE stage='ingest_fii_dii' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run_row["status"] == "skip"
        assert "fetch failed" in run_row["detail"]
    finally:
        conn.close()


def test_run_skips_on_empty_rows(tmp_path):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        n = fii_dii.run(conn, AS_OF, fetcher=lambda: [])
        assert n == 0
        run_row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_fii_dii' ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        assert run_row["status"] == "skip"
    finally:
        conn.close()
