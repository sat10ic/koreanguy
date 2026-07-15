"""V4-T4/T5: /api/scanners/presets + /api/scanners/run (WIREFRAMES_V4.md
Section 2A). Registry shape, arora_baseline on real seeded data, a
chartsmaze DATA-READY preset path, and the run-contract row shape."""
import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import scanner_presets
from manas_os.tests.conftest import AS_OF, insert_price_ramp


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def test_preset_registry_shape():
    assert scanner_presets.PRESET_REGISTRY, "registry must not be empty"
    statuses = set()
    for key, definition in scanner_presets.PRESET_REGISTRY.items():
        for field in ("owner", "label", "recipe_line", "cite", "status", "kind"):
            assert field in definition, f"{key} missing {field}"
        assert definition["status"] in ("LIVE", "DATA_READY", "BUILD")
        statuses.add(definition["status"])
    # all three statuses represented per STATUS vocabulary
    assert {"LIVE", "DATA_READY", "BUILD"} <= statuses
    # the 5 ChartsMaze trader templates are present and DATA_READY
    for k in ("chhirag", "himanshu", "hiren", "nitin", "shashank"):
        assert scanner_presets.PRESET_REGISTRY[k]["status"] == "DATA_READY"
    assert scanner_presets.PRESET_REGISTRY["arora_baseline"]["status"] == "LIVE"
    assert scanner_presets.PRESET_REGISTRY["todays_movers"]["status"] == "LIVE"


def test_arora_baseline_preset_returns_rows_on_seeded_data(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    # steep ramp: >30% over 63d, liquid enough (avg vol 30d > 200k)
    last_date = insert_price_ramp(conn, symbol="ROCKET", n=210, start=100.0, step=2.5,
                                   volume=500_000, end=AS_OF)
    conn.commit()
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/scanners/presets", params={"date": last_date})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    by_key = {p["key"]: p for p in body["presets"]}
    assert by_key["arora_baseline"]["hits"] is not None
    assert by_key["arora_baseline"]["hits"] >= 1

    run_resp = client.get("/api/scanners/run", params={"key": "arora_baseline", "date": last_date})
    assert run_resp.status_code == 200
    run_body = run_resp.json()
    assert run_body["available"] is True
    symbols = {h["symbol"] for h in run_body["hits"]}
    assert "ROCKET" in symbols
    row = next(h for h in run_body["hits"] if h["symbol"] == "ROCKET")
    for field in ("pct_up_65d_low", "adr20", "rs", "purple_dot_count", "pct_chg",
                  "volume", "in_watchlist", "in_debate"):
        assert field in row


def test_todays_movers_preset_run_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    last_date = insert_price_ramp(conn, symbol="MOVER", n=40, start=100.0, step=0.1,
                                   volume=2_000_000, end=AS_OF)
    # force a >=5% day-1 burst on the last bar so TODAYS_MOVERS conditions hit
    conn.execute(
        "UPDATE daily_prices SET close = close * 1.08, high = high * 1.08 "
        "WHERE symbol='MOVER' AND trade_date = ?", (last_date,),
    )
    conn.commit()
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/scanners/run", params={"key": "todays_movers", "date": last_date})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["kind"] == "conditions"
    if body["hits"]:
        row = body["hits"][0]
        assert "in_watchlist" in row and "in_debate" in row


def test_chartsmaze_preset_reads_ingested_table(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    insert_price_ramp(conn, symbol="CHHI", n=40, end=AS_OF)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS screener_hits ("
        "trade_date TEXT, symbol TEXT, screener TEXT, bearish INTEGER, "
        "rs_rating REAL, basic_industry TEXT, ingested_at TEXT, "
        "PRIMARY KEY (trade_date, symbol, screener))"
    )
    conn.execute(
        "INSERT INTO screener_hits (trade_date, symbol, screener, bearish, rs_rating, basic_industry) "
        "VALUES (?, 'CHHI', 'chhirag', 0, 91.0, 'Chemicals')",
        (AS_OF,),
    )
    conn.commit()
    client = _client(db_path, monkeypatch)

    presets_resp = client.get("/api/scanners/presets", params={"date": AS_OF})
    by_key = {p["key"]: p for p in presets_resp.json()["presets"]}
    assert by_key["chhirag"]["status"] == "DATA_READY"
    assert by_key["chhirag"]["hits"] == 1

    run_resp = client.get("/api/scanners/run", params={"key": "chhirag", "date": AS_OF})
    body = run_resp.json()
    assert body["available"] is True
    assert body["kind"] == "chartsmaze"
    assert body["hits"][0]["symbol"] == "CHHI"
    assert body["hits"][0]["rs"] == 91.0


def test_build_preset_returns_no_fake_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    insert_price_ramp(conn, symbol="ANY", n=40, end=AS_OF)
    conn.commit()
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/scanners/run", params={"key": "lf_jump", "date": AS_OF})
    body = resp.json()
    assert body["available"] is False
    assert body["hits"] == []

    presets_resp = client.get("/api/scanners/presets", params={"date": AS_OF})
    by_key = {p["key"]: p for p in presets_resp.json()["presets"]}
    assert by_key["lf_jump"]["status"] == "BUILD"
    assert by_key["lf_jump"]["hits"] is None


def test_saved_user_screen_runs_through_scanners_run_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    from manas_os.scanner import screener as scanner_screener
    scanner_screener.ensure_screens_schema(conn)
    last_date = insert_price_ramp(conn, symbol="SAVEDX", n=40, start=100.0, step=0.1,
                                   volume=2_000_000, end=AS_OF)
    conn.execute(
        "INSERT INTO user_screens (name, conditions_json) VALUES ('my movers', ?)",
        (json.dumps([{"field": "volume", "op": "gte", "value": 1_000_000}]),),
    )
    conn.commit()
    client = _client(db_path, monkeypatch)

    resp = client.get("/api/scanners/run", params={"key": "user:my movers", "date": last_date})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["kind"] == "user"
    assert any(h["symbol"] == "SAVEDX" for h in body["hits"])


def test_scanner_presets_hits_lazy(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    last_date = insert_price_ramp(conn, symbol="LAZY", n=40, start=100.0, step=0.1,
                                   volume=2_000_000, end=AS_OF)
    # force a >=5% day-1 burst on the last bar so TODAYS_MOVERS conditions hit
    conn.execute(
        "UPDATE daily_prices SET close = close * 1.08, high = high * 1.08 "
        "WHERE symbol='LAZY' AND trade_date = ?", (last_date,),
    )
    conn.commit()
    client = _client(db_path, monkeypatch)

    # test include_hits=false -> all hits are None
    resp = client.get("/api/scanners/presets", params={"date": last_date, "include_hits": "false"})
    assert resp.status_code == 200
    body = resp.json()
    for p in body["presets"]:
        assert p["hits"] is None

    # test cheap hit count endpoint for todays_movers
    hits_resp = client.get("/api/scanners/preset-hits", params={"key": "todays_movers", "date": last_date})
    assert hits_resp.status_code == 200
    hits_body = hits_resp.json()
    assert hits_body["key"] == "todays_movers"
    assert hits_body["hits"] == 1
    assert hits_body["as_of"] == last_date


def test_preset_card_counts_use_persisted_bucket_without_live_rebuild(tmp_path, monkeypatch):
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    scanner_candidates.ensure_schema(conn)
    last_date = insert_price_ramp(conn, symbol="PERSIST", n=70, end=AS_OF)
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
        "VALUES (?, 'PERSIST', ?, '{}')",
        (last_date, json.dumps(["persistent_momentum", "vcp_coil"])),
    )
    conn.commit()
    monkeypatch.setattr(
        scanner_candidates,
        "discovery_bucket_map",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live rebuild invoked")),
    )

    counts = scanner_presets.preset_hit_counts(conn, last_date)
    assert counts["persistent_momentum"] == 1
    assert counts["vcp_tightness"] == 1
    conn.close()
