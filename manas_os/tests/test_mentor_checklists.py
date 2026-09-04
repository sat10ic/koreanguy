from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import mentor_checklists


def test_load_checklists_contract():
    checklists = mentor_checklists.load_checklists()
    assert len(checklists) >= 1
    assert len(checklists[0]["items"]) >= 3


def test_checklist_response_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    checklist = mentor_checklists.load_checklists()[0]
    item = checklist["items"][0]
    res = client.post(
        f"/api/mentor/checklists/{checklist['id']}/responses",
        json={"date": "2026-07-06", "item_id": item["id"], "checked": True},
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    got = client.get(
        f"/api/mentor/checklists/{checklist['id']}/responses",
        params={"date": "2026-07-06"},
    )
    assert got.status_code == 200
    payload = got.json()
    assert payload["date"] == "2026-07-06"
    assert payload["responses"][item["id"]] is True


def test_checklist_missing_date_defaults_false(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    checklist = mentor_checklists.load_checklists()[0]
    got = client.get(
        f"/api/mentor/checklists/{checklist['id']}/responses",
        params={"date": "2026-07-07"},
    )
    assert got.status_code == 200
    payload = got.json()
    assert payload["date"] == "2026-07-07"
    assert set(payload["responses"]) == {item["id"] for item in checklist["items"]}
    assert all(checked is False for checked in payload["responses"].values())
