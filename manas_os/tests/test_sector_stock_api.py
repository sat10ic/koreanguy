"""API tests for sector/theme stock drill-downs."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from manas_os.api import app as api_app
from manas_os.sources import chartsmaze

_REAL_DATE = "2026-07-04"
_LEGACY_CM = (
    Path(__file__).resolve().parents[2]
    / "legacy"
    / "SwingEdge"
    / "data"
    / "chartsmaze"
).resolve()
_REAL_FOLDER = _LEGACY_CM / _REAL_DATE


@pytest.fixture
def legacy_cm(monkeypatch):
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: _LEGACY_CM)


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_sector_stock_endpoint_returns_real_fixture_members(legacy_cm):
    client = TestClient(api_app.app)

    res = client.get("/api/regime/sectors/CAPITAL_GOODS/stocks", params={"date": _REAL_DATE})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["sector_key"] == "CAPITAL_GOODS"
    assert payload["count"] == len(payload["stocks"])
    assert payload["count"] > 0
    # Top RS is 99.0, tied across multiple tickers (e.g. BHAGYANGR, BATLIBOI);
    # don't assert which ticker wins the tie — just that the value and
    # membership are right, and that the tie-break (alphabetical) is stable.
    assert payload["stocks"][0]["rs"] == 99.0
    tickers = {s["ticker"] for s in payload["stocks"]}
    assert "BHAGYANGR" in tickers
    assert payload["stocks"] == sorted(
        payload["stocks"],
        key=lambda item: (item["rs"] is None, -(item["rs"] or 0), item["ticker"]),
    )


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_industry_stock_endpoint_contract_and_empty_state(legacy_cm):
    client = TestClient(api_app.app)

    res = client.get(
        "/api/regime/industries/Electrical%20-%20Power%20Equipment/stocks",
        params={"date": _REAL_DATE},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["industry"] == "Electrical - Power Equipment"
    assert payload["count"] == len(payload["stocks"])
    assert payload["count"] > 0
    assert payload["stocks"][0]["rs"] == 99.0

    empty = client.get("/api/regime/sectors/NOT_A_SECTOR/stocks", params={"date": _REAL_DATE})
    assert empty.status_code == 200
    assert empty.json() == {
        "available": False,
        "sector_key": "NOT_A_SECTOR",
        "stocks": [],
        "count": 0,
    }
