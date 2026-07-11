from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app


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
    assert client.get("/api/alpha/models").json()["shadow_only"] is True
    assert client.get("/api/alpha/experiments").json()["state"] == "warming"
    symbol = client.get("/api/alpha/symbol/RELIANCE").json()
    assert symbol["state"] == "warming"
    assert symbol["shadow_only"] is True
    memory = client.get("/api/alpha/memory/RELIANCE").json()
    assert memory["rows"] == []
