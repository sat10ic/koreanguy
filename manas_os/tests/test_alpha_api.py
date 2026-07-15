from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.alpha import schema as alpha_schema


def _client(db_path, monkeypatch):
    original = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: original(db_path))
    return TestClient(api_app.app)


def test_alpha_routes_are_honest_while_warming(tmp_path, monkeypatch):
    path = tmp_path / "alpha.db"
    db.init_db(path).close()
    client = _client(path, monkeypatch)

    assert client.get("/api/alpha/overview").json()["state"] == "warming"
    assert client.get("/api/alpha/leaders").json()["rows"] == []
    activity = client.get("/api/alpha/activity").json()
    assert activity["state"] == "warming"
    assert activity["shadow_only"] is True
    assert client.get("/api/alpha/activity/RELIANCE").json()["state"] == "warming"
    assert client.get("/api/alpha/factors/health").json()["state"] == "warming"
    transition = client.get("/api/alpha/regime-transition").json()
    assert transition["state"] == "warming"
    quality = client.get("/api/alpha/research-quality").json()
    assert quality["shadow_only"] is True
    assert any(card["key"] == "dsr" and card["state"] == "not_implemented" for card in quality["cards"])
    assert client.get("/api/alpha/models").json()["shadow_only"] is True
    assert client.get("/api/alpha/experiments").json()["state"] == "warming"
    symbol = client.get("/api/alpha/symbol/RELIANCE").json()
    assert symbol["state"] == "warming"
    assert symbol["shadow_only"] is True
    memory = client.get("/api/alpha/memory/RELIANCE").json()
    assert memory["rows"] == []


def test_alpha_leaders_resolve_latest_snapshot_on_or_before_requested_date(tmp_path, monkeypatch):
    path = tmp_path / "alpha.db"
    conn = db.init_db(path)
    try:
        alpha_schema.ensure_schema(conn)
        conn.execute(
            "INSERT INTO alpha_feature_snapshots "
            "(as_of_date,symbol,feature_version,sector,universe,source_max_date,"
            "source_denominator,momentum_zscore,momentum_percentile,features_json) "
            "VALUES ('2026-06-30','KPIL','v1','CAPITAL_GOODS','NSE_EQ','2026-06-30',"
            "100,1.5,95.0,'{}')"
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(path, monkeypatch)
    response = client.get("/api/alpha/leaders", params={"date": "2026-07-01"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ready"
    assert body["requested_date"] == "2026-07-01"
    assert body["as_of"] == "2026-06-30"
    assert [row["symbol"] for row in body["rows"]] == ["KPIL"]
