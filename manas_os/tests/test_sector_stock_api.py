"""API contracts for persisted sector/industry stock RS drill-downs."""
import pytest
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app


@pytest.fixture
def stock_rs_client(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    conn.executemany(
        "INSERT INTO stock_industry_rs (snapshot_date, ticker, industry, rs) "
        "VALUES (?, ?, ?, ?)",
        [
            ("2026-07-17", "POWERLOW", "Electrical - Power Equipment", 71.0),
            ("2026-07-18", "POWERB", "Electrical - Power Equipment", 88.0),
            ("2026-07-18", "POWERA", "Electrical - Power Equipment", 88.0),
            ("2026-07-18", "RAILCO", "Railways", 92.0),
            ("2026-07-18", "HDFCBANK", "Private Banks", 95.0),
        ],
    )
    conn.commit()
    conn.close()
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def test_sector_stock_endpoint_uses_reverse_map_and_latest_fixture(stock_rs_client):
    response = stock_rs_client.get(
        "/api/regime/sectors/CAPITAL_GOODS/stocks",
        params={"date": "2026-07-19"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "available": True,
        "sector_key": "CAPITAL_GOODS",
        "stocks": [
            {"ticker": "RAILCO", "rs": 92.0},
            {"ticker": "POWERA", "rs": 88.0},
            {"ticker": "POWERB", "rs": 88.0},
        ],
        "count": 3,
    }


def test_industry_stock_endpoint_contract_and_unavailable_state(stock_rs_client):
    response = stock_rs_client.get(
        "/api/regime/industries/Electrical%20-%20Power%20Equipment/stocks",
        params={"date": "2026-07-18"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "available": True,
        "industry": "Electrical - Power Equipment",
        "stocks": [
            {"ticker": "POWERA", "rs": 88.0},
            {"ticker": "POWERB", "rs": 88.0},
        ],
        "count": 2,
    }

    unavailable = stock_rs_client.get(
        "/api/regime/industries/Electrical%20-%20Power%20Equipment/stocks",
        params={"date": "2026-07-16"},
    )
    assert unavailable.status_code == 200
    assert unavailable.json() == {
        "available": False,
        "industry": "Electrical - Power Equipment",
        "stocks": [],
        "count": 0,
    }


def test_sector_stock_endpoint_never_returns_blank_success(stock_rs_client):
    response = stock_rs_client.get(
        "/api/regime/sectors/NOT_A_SECTOR/stocks",
        params={"date": "2026-07-18"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "sector_key": "NOT_A_SECTOR",
        "stocks": [],
        "count": 0,
    }
