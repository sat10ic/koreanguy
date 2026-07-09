import base64
import json

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import lessons
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates
from manas_os.tests.conftest import insert_price_ramp, trading_dates


AS_OF = "2026-06-30"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def test_desk_chart_serves_png_and_404s_when_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    chart_dir = tmp_path / "data" / "agent_charts" / AS_OF
    chart_dir.mkdir(parents=True)
    (chart_dir / "AAA_daily.png").write_bytes(PNG_1X1)

    client = _client(db_path, monkeypatch)
    ok = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "daily"})
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/png"
    assert ok.content == PNG_1X1

    missing = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "weekly"})
    assert missing.status_code == 404
    assert missing.json() == {"available": False, "date": AS_OF, "symbol": "AAA", "tf": "weekly"}


def test_desk_chart_rejects_bad_symbol_and_date(tmp_path, monkeypatch):
    """AUDIT-2: path-traversal / injection-shaped symbol or date must 4xx
    before touching the filesystem, not fall through to a 404 file lookup."""
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    for bad_symbol in ("../evil", "a b", "AAA/../../etc"):
        resp = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": bad_symbol, "tf": "daily"})
        assert resp.status_code == 400, bad_symbol

    for bad_date in ("2026-13-99", "..", "2026/06/30", "not-a-date"):
        resp = client.get("/api/desk/chart", params={"date": bad_date, "symbol": "AAA", "tf": "daily"})
        assert resp.status_code == 400, bad_date


def test_desk_track_record_aggregates_agent_family_outcomes(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        for idx, outcome in enumerate([1.2, -0.5, 2.0], start=1):
            symbol = f"A{idx}"
            conn.execute(
                "INSERT OR REPLACE INTO scan_candidates "
                "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
                "VALUES (?, ?, 'Pullback', 'base/pattern', 80, 'A', 100, 95, 2.0, 10)",
                (AS_OF, symbol),
            )
            conn.execute(
                "INSERT OR REPLACE INTO agent_verdicts "
                "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, ?, 'mock/model-a', 'TAKE', ?)",
                (AS_OF, symbol, outcome),
            )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
            "VALUES (?, 'B1', 'Breakout', 'catalyst', 80, 'A', 100, 95, 2.0, 10)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, 'B1', 'chair', 'SKIP', -1.0)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/track-record")
    assert resp.status_code == 200
    records = resp.json()["records"]
    model = next(r for r in records if r["agent"] == "mock/model-a" and r["family"] == "base/pattern")
    assert model["n"] == 3
    assert model["hit_rate"] == 2 / 3
    assert abs(model["avg_r"] - 0.9) < 1e-9
    assert model["thin"] is True
    chair = next(r for r in records if r["agent"] == "chair" and r["family"] == "catalyst")
    assert chair["n"] == 1
    assert chair["hit_rate"] == 0
    assert chair["avg_r"] == -1.0


def test_desk_lessons_lists_markdown_and_digest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    lesson_dir = tmp_path / "lessons"
    lesson_dir.mkdir()
    (lesson_dir / "2026-06-30_AAA.md").write_text(
        "[clean-hit] AAA followed through.\nSecond line.", encoding="utf-8"
    )
    (lesson_dir / "2026-06-29_BBB.md").write_text(
        "BBB was a right-process-loss after tape rolled over.", encoding="utf-8"
    )
    (lesson_dir / "_digest.md").write_text("Carry forward the clean base lesson.", encoding="utf-8")
    monkeypatch.setattr(lessons, "LESSON_DIR", lesson_dir)

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/lessons", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["digest"] == "Carry forward the clean base lesson."
    assert body["lessons"] == [
        {
            "filename": "2026-06-30_AAA.md",
            "tag": "clean-hit",
            "first_line": "[clean-hit] AAA followed through.",
        }
    ]


def test_desk_feed_orders_events_and_composes_lines(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'mock/model-a', 'mock/model-a', 500, "
            "1, 'ok', NULL, '2026-06-30 18:33:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'gemma', 'gemma', NULL, 0, NULL, NULL, "
            "'2026-06-30 18:41:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO scan_agent_logs (run_date, agent, model, latency_ms, parsed_ok, "
            "validation, error, created_at) VALUES (?, 'qwen', 'qwen', 900, 0, 'bad json', "
            "'429', '2026-06-30 18:35:00')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
            "duration_s, detail, ran_at) VALUES (?, 'scan_candidates', 'candidates', 'ok', "
            "14, 1.2, '1,029 -> 259 -> 34 -> 14 shortlist', '2026-06-30 18:31:00')",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/feed", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == AS_OF
    events = body["events"]
    assert [e["actor"] for e in events] == ["gemma", "qwen", "mock/model-a", "scan_candidates"]
    assert events[0]["state"] == "running"
    assert "in flight" in events[0]["line"]
    assert events[1]["state"] == "failed"
    assert "failed" in events[1]["line"]
    assert events[2]["state"] == "done"
    assert "parsed ok" in events[2]["line"]
    assert events[3]["state"] == "done"
    assert "shortlist" in events[3]["line"]
    assert events[3]["expand"]["stage"] == "scan_candidates"


def test_desk_debate_returns_shaped_payload_for_seeded_night(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        conn.execute(
            "INSERT INTO regime_snapshots (snapshot_date, market_mode) VALUES (?, 'SELECTIVE')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, target, rr, "
            "suggested_qty, gates_json) "
            "VALUES (?, 'KPIL', 'Pullback', 'base/pattern', 80, 'A', 892.0, 861.5, 953.0, 2.0, 34, ?)",
            (AS_OF, json.dumps([{"gate": "regime", "pass": True, "reason": None, "evidence": {}}])),
        )
        scanner_candidates.ensure_refusals_schema(conn)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason) "
            "VALUES (?, 'ZZZ', 'base/pattern', 'tradability', 'illiquid')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning) "
            "VALUES (?, 'KPIL', 'nemotron', 'TAKE', 4, 1, 'quiet base + delivery surge', 'gap-fill overhead', 'take it')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, bull_case, bear_case, reasoning) "
            "VALUES (?, 'KPIL', 'gemma', 'TAKE', 3, 2, 'tight VCP', 'third pullback, RR only 1.8', 'ok')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, reasoning, lens_scores_json) "
            "VALUES (?, 'KPIL', 'chair', 'TAKE', 4, 1, 'models 2T/0S, spread 1', ?)",
            (AS_OF, json.dumps({"disagreement": True, "conviction_spread": 1})),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, reasoning) "
            "VALUES (?, 'KPIL', 'vision', 'PROMOTE', 'pivot clean, volume dry-up')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, reasoning, lens_scores_json) "
            "VALUES (?, 'KPIL', 'sizer', 'TAKE', 'split debate, fresh regime', ?)",
            (AS_OF, json.dumps({"multiplier": 0.75, "final_qty": 25, "validated": True})),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["scan_date"] == AS_OF
    assert body["regime_mode"] == "SELECTIVE"
    assert len(body["symbols"]) == 1
    sym = body["symbols"][0]
    assert sym["symbol"] == "KPIL"
    assert sym["family"] == "base/pattern"
    assert sym["chair"]["verdict"] == "TAKE"
    assert sym["chair"]["conviction_spread"] == 1
    assert {m["agent"] for m in sym["models"]} == {"nemotron", "gemma"}
    assert sym["vision"]["verdict"] == "PROMOTE"
    assert sym["sizer"]["multiplier"] == 0.75
    assert sym["sizer"]["final_qty"] == 25
    assert sym["plan"]["entry"] == 892.0
    assert sym["plan"]["rr"] == 2.0
    assert sym["gates"] == [{"gate": "regime", "pass": True, "reason": None, "evidence": {}}]

    funnel = body["funnel"]
    assert funnel["shortlist"] == 1
    assert funnel["debated"] == 1
    assert funnel["by_gate"] == {"tradability": 1}
    assert funnel["screeners"] == 2
    assert funnel["gates"] == 1


def test_desk_debate_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/debate", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"available": False, "scan_date": "2020-01-01", "symbols": []}


def test_desk_feed_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/feed", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"run_date": "2020-01-01", "events": []}


def test_desk_positions_seeded_open_trade_shapes_lifecycle_card(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        insert_price_ramp(conn, symbol="HUDCO", n=210, end=AS_OF)
        dates = trading_dates(20, AS_OF)
        trade_date = dates[0]
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE symbol = 'HUDCO' AND trade_date = ?",
            (trade_date,),
        ).fetchone()
        entry = float(row["close"])
        stop = entry - 5.0
        conn.execute(
            "INSERT INTO journal_trades (trade_date, symbol, setup, entry, stop) "
            "VALUES (?, 'HUDCO', 'Pullback', ?, ?)",
            (trade_date, entry, stop),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, bull_case, reasoning) "
            "VALUES (?, 'HUDCO', 'nemotron', 'TAKE', 4, 'quiet base + delivery surge', 'take it')",
            (trade_date,),
        )
        from manas_os.agents import signals as agents_signals

        agents_signals.ensure_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO agent_signals (scan_date, symbol, channel, message, sent) "
            "VALUES (?, 'HUDCO', 'coach', 'HUDCO coach: HOLD.', 1)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_date"] == AS_OF
    assert len(body["positions"]) == 1
    pos = body["positions"][0]
    assert pos["symbol"] == "HUDCO"
    assert pos["trade_date"] == trade_date
    assert pos["phase"] in {"INITIATION", "TREND", "EXTENSION"}
    assert isinstance(pos["r_path"], list) and len(pos["r_path"]) > 0
    for point in pos["r_path"]:
        assert trade_date <= point["date"] <= AS_OF
    assert pos["original_thesis"]["agent"] == "nemotron"
    assert pos["original_thesis"]["bull_case"] == "quiet base + delivery surge"
    assert pos["coach"]["message"] == "HUDCO coach: HOLD."
    assert pos["coach"]["sent"] is True
    assert pos["urgent"] is False


def test_desk_positions_no_open_trades_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/positions", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    assert resp.json() == {"run_date": "2020-01-01", "positions": []}


def test_desk_market_seeded_index_history_hand_checked_returns(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        dates = trading_dates(25, AS_OF)  # ascending, dates[-1] == AS_OF
        for i, d in enumerate(dates, start=1):
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY 50", d, 100.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY BANK", d, 200.0 + i * 2),
            )
        conn.execute(
            "INSERT INTO industry_metrics (snapshot_date, name, perf_1d, perf_1w, perf_1m, num_stocks) "
            "VALUES (?, 'Pharmaceuticals', 3.5, 5.0, 8.0, 12)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO industry_metrics (snapshot_date, name, perf_1d, perf_1w, perf_1m, num_stocks) "
            "VALUES (?, 'Auto Ancillaries', -1.2, -2.0, -3.0, 9)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO sector_metrics (snapshot_date, sector_key, setup_count_a, setup_count_b, setup_count_c) "
            "VALUES (?, 'BANK', 3, 2, 1)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
            "VALUES (?, 'ACME', 'bulk_deal', ?)",
            (AS_OF, json.dumps({"qty": "10000", "price": "123.4", "buyer": "Foo Fund"})),
        )
        conn.execute(
            "INSERT INTO disclosures (trade_date, symbol, kind, detail_json) "
            "VALUES (?, 'ACME', 'insider', ?)",
            (AS_OF, json.dumps({"person": "Jane Doe", "type": "Buy", "qty": "500"})),
        )
        conn.execute(
            "INSERT INTO fii_dii_daily "
            "(trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source) "
            "VALUES (?, 17463.95, 15501.15, 1962.8, 19165.13, 18374.97, 790.16, 'groww_fii_dii')",
            (AS_OF,),
        )
        conn.execute(
            "INSERT INTO fii_dii_daily "
            "(trade_date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net, source) "
            "VALUES ('2026-06-29', 18414.01, 18020.82, 393.19, 18897.44, 19280.87, -383.43, 'groww_fii_dii')",
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/market", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["as_of"] == AS_OF
    fii_dii = body["fii_dii"]
    assert fii_dii["latest"]["trade_date"] == AS_OF
    assert fii_dii["latest"]["fii_net"] == 1962.8
    assert fii_dii["latest"]["dii_net"] == 790.16
    assert len(fii_dii["last_10"]) == 2
    assert fii_dii["last_10"][0]["trade_date"] == AS_OF
    assert fii_dii["net_trend"]["fii_net_sum"] == 1962.8 + 393.19
    assert fii_dii["net_trend"]["dii_net_sum"] == 790.16 + (-383.43)

    by_symbol = {row["symbol"]: row for row in body["indices"]}
    n50 = by_symbol["NIFTY 50"]
    # last close 125 (i=25), 1d prior close 124 (i=24): (125-124)/124*100
    assert n50["returns"]["1d"] == round((125.0 - 124.0) / 124.0 * 100.0, 2)
    # 1w = 5 sessions back, i=20 close=120
    assert n50["returns"]["1w"] == round((125.0 - 120.0) / 120.0 * 100.0, 2)
    assert len(n50["spark"]) == 25
    assert n50["spark"][-1] == 125.0
    # NIFTY 50 is first in indices (broad-first ordering).
    assert body["indices"][0]["symbol"] == "NIFTY 50"

    bank = by_symbol["NIFTY BANK"]
    assert bank["returns"]["1d"] == round((250.0 - 248.0) / 248.0 * 100.0, 2)

    movers = body["movers"]
    assert set(movers.keys()) == {"d1", "w1", "m1"}
    d1 = movers["d1"]
    assert any(s["symbol"] == "NIFTY BANK" for s in d1["sectors_up"])
    bank_up = next(s for s in d1["sectors_up"] if s["symbol"] == "NIFTY BANK")
    assert bank_up["num_stocks"] == 6  # setup_count_a+b+c = 3+2+1
    assert d1["themes_up"][0]["name"] == "Pharmaceuticals"

    sectors = body["sectors"]
    assert any(s["symbol"] == "NIFTY BANK" and s["num_stocks"] == 6 for s in sectors)
    assert all(s["symbol"] != "NIFTY 50" for s in sectors)  # broad index excluded

    deals = body["deals"]
    assert deals["block_bulk"][0]["symbol"] == "ACME"
    assert deals["block_bulk"][0]["detail"]["buyer"] == "Foo Fund"
    assert deals["insider"][0]["detail"]["person"] == "Jane Doe"


def test_desk_market_empty_date_is_honest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/market", params={"date": "2020-01-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["indices"] == []
    assert body["deals"] == {"block_bulk": [], "insider": []}
    assert body["fii_dii"] is None
    assert body["vix"] is None


def test_classify_index_spot_checks():
    """Name-pattern classifier — see comment above BROAD_INDEX_LADDER in
    manas_os/api/app.py for the precedence rules."""
    classify = api_app.classify_index
    broad = [
        "NIFTY 50", "Nifty 100", "NIFTY 200", "Nifty 500", "Nifty Next 50",
        "NIFTY MIDCAP 150", "Nifty Smallcap 250", "NIFTY MICROCAP 250",
        "NIFTY LargeMidcap 250",
    ]
    for name in broad:
        assert classify(name) == "BROAD", name

    sectoral = [
        "Nifty Bank", "NIFTY IT", "Nifty Auto", "Nifty Metal", "Nifty FMCG",
        "Nifty Energy", "Nifty Realty", "Nifty PSU Bank", "Nifty Private Bank",
        "Nifty Financial Services", "Nifty Healthcare Index", "Nifty Media",
        "Nifty Infrastructure", "Nifty Consumer Durables", "Nifty Oil & Gas",
        "Nifty Commodities", "Nifty CPSE", "Nifty India Defence",
        "Nifty500 Healthcare",  # "500" prefix has no strategy marker word
    ]
    for name in sectoral:
        assert classify(name) == "SECTORAL", name

    thematic = [
        "NIFTY Alpha Low-Volatility 30", "NIFTY100 Quality 30", "Nifty500 Value 50",
        "Nifty50 Equal Weight", "Nifty50 Shariah", "Nifty Dividend Opportunities 50",
        "Nifty 10 yr Benchmark G-Sec", "Nifty BHARAT Bond Index - April 2030",
        "Nifty 50 Arbitrage", "Nifty50 PR 2x Leverage", "Nifty50 USD",
        "Nifty MidSmall Healthcare",  # blend, not plain sector
        "Nifty IPO", "Nifty SME EMERGE", "Nifty Total Market",
    ]
    for name in thematic:
        assert classify(name) == "THEMATIC_STRATEGY", name


def test_desk_market_taxonomy_and_vix(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        dates = trading_dates(25, AS_OF)
        for i, d in enumerate(dates, start=1):
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY 50", d, 100.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("Nifty Bank", d, 200.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("NIFTY100 Quality 30", d, 300.0 + i),
            )
            conn.execute(
                "INSERT INTO sector_index_prices (symbol, trade_date, close) VALUES (?, ?, ?)",
                ("India VIX", d, 14.5),
            )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)

    resp = client.get("/api/desk/market", params={"date": AS_OF})
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True

    # VIX is extracted, not listed as an index.
    assert body["vix"] == {"value": 14.5, "band": "normal"}
    symbols = {row["symbol"] for row in body["indices"]}
    assert "India VIX" not in symbols
    assert all(s["symbol"] != "India VIX" for s in body["sectors"])

    # Default payload: BROAD + SECTORAL only, no thematic index.
    assert "NIFTY 50" in symbols
    assert "Nifty Bank" in symbols
    assert "NIFTY100 Quality 30" not in symbols

    # Treemap/sectors set is SECTORAL only.
    sector_symbols = {s["symbol"] for s in body["sectors"]}
    assert sector_symbols == {"Nifty Bank"}

    resp2 = client.get("/api/desk/market", params={"date": AS_OF, "include_thematic": "true"})
    body2 = resp2.json()
    symbols2 = {row["symbol"] for row in body2["indices"]}
    assert "NIFTY100 Quality 30" in symbols2


def test_vix_band_tiers():
    band = api_app._vix_band
    assert band(11.9) == "low"
    assert band(12.0) == "normal"
    assert band(19.9) == "normal"
    assert band(20.0) == "elevated"
    assert band(24.9) == "elevated"
    assert band(25.0) == "danger"
    assert band(30.0) == "danger"


def test_desk_latest_reports_run_card_and_scan_dates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    for scan_date in ("2026-06-25", "2026-06-30"):
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, readiness, grade) VALUES (?, 'AAA', 'ep', 80, 'A')",
            (scan_date,),
        )
    conn.commit()
    conn.close()
    run_card_dir = tmp_path / "data" / "run_cards"
    run_card_dir.mkdir(parents=True)
    (run_card_dir / "2026-06-28.json").write_text("{}")
    (run_card_dir / "2026-06-29.json").write_text("{}")

    from manas_os.agents import run_card as run_card_module

    monkeypatch.setattr(run_card_module, "RUN_CARD_ROOT", run_card_dir)
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/latest")
    assert resp.status_code == 200
    assert resp.json() == {
        "latest_run_card_date": "2026-06-29",
        "latest_scan_date": "2026-06-30",
    }


def test_desk_latest_empty_db_returns_nulls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    from manas_os.agents import run_card as run_card_module

    monkeypatch.setattr(run_card_module, "RUN_CARD_ROOT", tmp_path / "data" / "run_cards")
    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/latest")
    assert resp.status_code == 200
    assert resp.json() == {"latest_run_card_date": None, "latest_scan_date": None}
