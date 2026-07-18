import json
from pathlib import Path

from manas_os import db
from manas_os.engine.universe_filter import GateConfig, evaluate_symbol
from manas_os.risk import plan as risk_plan
from manas_os.scanner import candidates, discovery, gates
from manas_os.tests.conftest import seed_regime


FIXTURE = Path(__file__).with_name("fixtures") / "practitioner_bars.json"

STRICT_SCAN = {
    "2026-07-15": {"JNKINDIA", "DIVISLAB", "RAYMONDREL", "NUVOCO"},
    "2026-07-16": {"AZAD", "HIRECT"},
}
SCAN_OR_OBJECTING = {"FCL", "DAMCAPITAL"}
WATCH = {"SKIPPER", "GENUSPOWER", "INOXINDIA", "LLOYDSENGG", "KSHINTL"}


def _seed_fixture(conn) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in payload["cases"].values():
        symbol = case["symbol"]
        conn.executemany(
            "INSERT OR REPLACE INTO daily_prices "
            "(trade_date, symbol, series, open, high, low, close, prev_close, volume, "
            "delivery_qty, delivery_pct) VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    bar["date"], symbol, bar["open"], bar["high"], bar["low"],
                    bar["close"], bar["prev_close"], bar["volume"],
                    bar["delivery_qty"], bar["delivery_pct"],
                )
                for bar in case["bars"]
            ],
        )
        quality = case["symbol_quality"]
        if quality:
            conn.execute(
                "INSERT OR REPLACE INTO symbol_quality "
                "(trade_date, symbol, market_cap_cr, asm_stage, eps_qoq, eps_yoy, "
                "sales_yoy, opm_yoy, is_fno, exchange) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(
                    quality.get(key)
                    for key in (
                        "trade_date", "symbol", "market_cap_cr", "asm_stage", "eps_qoq",
                        "eps_yoy", "sales_yoy", "opm_yoy", "is_fno", "exchange",
                    )
                ),
            )
    seed_regime(conn, "2026-07-15", "RISK_ON")
    seed_regime(conn, "2026-07-16", "RISK_ON")
    conn.commit()


def _has_objection(conn, scan_date: str, symbol: str) -> bool:
    row = conn.execute(
        "SELECT evidence_json FROM refusals WHERE scan_date=? AND symbol=?",
        (scan_date, symbol),
    ).fetchone()
    if not row or not row["evidence_json"]:
        return False
    evidence = json.loads(row["evidence_json"])
    return bool(evidence.get("objections"))


def test_real_practitioner_labels_surface_in_scan_or_watch(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "practitioner.db")
    try:
        _seed_fixture(conn)
        monkeypatch.setattr(candidates, "stock_rs_map", lambda *_: {})
        scans = {}
        for scan_date in ("2026-07-15", "2026-07-16"):
            result = candidates.scan_candidates(conn, scan_date)
            scans[scan_date] = {row["symbol"]: row for row in result["candidates"]}
            discovery_result = discovery.run(conn, scan_date)
            assert discovery_result["status"] == "ok"

        for scan_date, symbols in STRICT_SCAN.items():
            assert symbols <= scans[scan_date].keys()

        for symbol in SCAN_OR_OBJECTING:
            scan_date = "2026-07-15" if symbol == "FCL" else "2026-07-16"
            assert symbol in scans[scan_date] or _has_objection(conn, scan_date, symbol)

        watch_rows = {row["symbol"] for row in conn.execute(
            "SELECT symbol FROM discovery_bucket "
            "WHERE classification='WATCH' AND scan_date='2026-07-16'"
        ).fetchall()}
        assert WATCH <= watch_rows
    finally:
        conn.close()


def test_pure_downtrend_remains_hard_refused():
    bars = []
    for i in range(220):
        close = 320.0 - i
        bars.append({"open": close + 0.5, "high": close + 1.0, "low": close - 1.0,
                     "close": close, "volume": 200_000})
    result = gates.gate_trend_template(bars, "momentum", rs_rating=90)
    assert result["pass"] is False
    assert "not in a confirmed uptrend" in result["reason"]


def _delivery_bars(today_range: float):
    bars = [
        {"open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0,
         "volume": 200_000, "delivery_pct": 60.0}
        for _ in range(50)
    ]
    bars.append({
        "open": 100.0,
        "high": 100.0 + today_range / 2.0,
        "low": 100.0 - today_range / 2.0,
        "close": 100.0,
        "volume": 200_000,
        "delivery_pct": 20.0,
    })
    return bars


def test_contracted_range_day_has_no_delivery_penalty():
    result = gates.gate_participation(_delivery_bars(2.0), setup_family="momentum")
    assert result["pass"] is True
    assert result["evidence"]["contracted_range"] is True
    assert "objections" not in result["evidence"]


def test_mover_weak_delivery_is_an_objection_not_a_refusal():
    result = gates.gate_participation(_delivery_bars(6.0), setup_family="momentum")
    assert result["pass"] is True
    assert result["evidence"]["objections"][0]["code"] == "weak_delivery"


def test_60_to_199_bar_non_base_template_is_waived_with_objection():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bars = fixture["cases"]["KSHINTL|2026-07-16"]["bars"]
    result = gates.gate_trend_template(bars, "momentum", rs_rating=90)
    assert result["pass"] is True
    assert result["evidence"]["objections"][0]["code"] == "downtrend_structure"


def test_near_high_leader_gets_leg_or_two_adr_projection():
    bars = [
        {"open": 100.0 + i, "high": 102.0 + i, "low": 98.0 + i,
         "close": 101.0 + i, "volume": 200_000}
        for i in range(30)
    ]
    projection = candidates.leader_measured_move_projection(
        bars, entry=131.0, stop=126.0, pivot=131.0,
    )
    assert projection is not None
    assert projection["target"] > 131.0
    assert "current-leg height" in projection["method"] or "2.0x ADR20" in projection["method"]


def test_nuvoco_setup_gap_uses_box_or_gap_day_range_projection():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bars = fixture["cases"]["NUVOCO|2026-07-15"]["bars"]
    entry = max(bar["high"] for bar in bars[-21:-1])
    projection = candidates.ep_box_projection(bars, entry, min_gap_pct=0.0)
    assert projection is not None
    assert projection["target"] > entry
    assert "box height" in projection["method"] or "gap-day range" in projection["method"]


def test_refused_coil_falls_back_to_watch_only_for_named_cascade_grounds(tmp_path):
    conn = db.init_db(tmp_path / "watch-fallback.db")
    try:
        candidates.ensure_refusals_schema(conn)
        conn.executemany(
            "INSERT INTO refusals (scan_date, symbol, failed_gate, reason) VALUES (?, ?, ?, ?)",
            [
                ("2026-07-16", "COIL", "risk", "R:R 1.20 below 1.5 floor"),
                ("2026-07-16", "KNIFE", "trend-template", "not in a confirmed uptrend"),
            ],
        )
        bucket = [
            {"symbol": symbol, "classification": "DISCOVERY",
             "archetypes": ["anticipation_watch", "persistent_momentum"],
             "metrics": {"watch": {"trigger": "armed"}}}
            for symbol in ("COIL", "KNIFE")
        ]
        reconciled = discovery.apply_cascade_watch_fallback(conn, "2026-07-16", bucket)
        classifications = {row["symbol"]: row["classification"] for row in reconciled}
        assert classifications == {"COIL": "WATCH", "KNIFE": "DISCOVERY"}
    finally:
        conn.close()


def test_participation_refused_anticipation_coil_falls_back_with_warning(tmp_path):
    conn = db.init_db(tmp_path / "participation-watch-fallback.db")
    try:
        candidates.ensure_refusals_schema(conn)
        reason = "delivery distribution into the trigger"
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate, reason) VALUES (?, ?, ?, ?)",
            ("2026-07-16", "WEAKVOL", "participation", reason),
        )
        bucket = [{
            "symbol": "WEAKVOL",
            "classification": "DISCOVERY",
            "archetypes": ["anticipation_watch"],
            "metrics": {},
        }]

        reconciled = discovery.apply_cascade_watch_fallback(conn, "2026-07-16", bucket)

        assert reconciled[0]["classification"] == "WATCH"
        assert reconciled[0]["metrics"]["watch_reason"] == reason
    finally:
        conn.close()


def test_stop_cap_refused_watch_metric_coil_falls_back_with_warning(tmp_path):
    conn = db.init_db(tmp_path / "stop-watch-fallback.db")
    try:
        candidates.ensure_refusals_schema(conn)
        reason = "stop 6.2% exceeds 5.0% cap (SELECTIVE)"
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate, reason) VALUES (?, ?, ?, ?)",
            ("2026-07-16", "WIDESTOP", "risk", reason),
        )
        bucket = [{
            "symbol": "WIDESTOP",
            "classification": "DISCOVERY",
            "archetypes": ["persistent_momentum"],
            "metrics": {"watch": {"trigger": "armed"}},
        }]

        reconciled = discovery.apply_cascade_watch_fallback(conn, "2026-07-16", bucket)

        assert reconciled[0]["classification"] == "WATCH"
        assert reconciled[0]["metrics"]["watch_reason"] == reason
    finally:
        conn.close()


def test_named_refused_coil_survives_anticipation_size_control(tmp_path):
    conn = db.init_db(tmp_path / "capped-watch-fallback.db")
    try:
        candidates.ensure_refusals_schema(conn)
        reason = "delivery -1.5σ below own norm — distribution into the trigger"
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate, reason) VALUES (?, ?, ?, ?)",
            ("2026-07-16", "CAPPED", "participation", reason),
        )
        bucket = [
            {
                "symbol": f"COIL{i:02d}",
                "classification": "WATCH",
                "archetypes": ["anticipation_watch"],
                "metrics": {"watch": {"pivot_distance_pct": i / 100, "stop_pct": 1.0}},
            }
            for i in range(discovery.CAP_PER_ARCHETYPE)
        ]
        bucket.append({
            "symbol": "CAPPED",
            "classification": "DISCOVERY",
            "archetypes": ["anticipation_watch"],
            "metrics": {"watch": {"pivot_distance_pct": 99.0, "stop_pct": 4.0}},
        })

        reconciled = discovery._size_control_with_cascade_watch_fallback(
            conn, "2026-07-16", bucket,
        )

        capped = next(row for row in reconciled if row["symbol"] == "CAPPED")
        assert len(reconciled) == discovery.CAP_PER_ARCHETYPE + 1
        assert capped["classification"] == "WATCH"
        assert capped["metrics"]["watch_reason"] == reason
    finally:
        conn.close()


def test_non_coil_participation_refusal_stays_refused(tmp_path):
    conn = db.init_db(tmp_path / "non-coil-participation-refusal.db")
    try:
        candidates.ensure_refusals_schema(conn)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate, reason) VALUES (?, ?, ?, ?)",
            ("2026-07-16", "NOCOIL", "participation", "delivery z -1.5 below own norm"),
        )
        bucket = [{
            "symbol": "NOCOIL",
            "classification": "DISCOVERY",
            "archetypes": ["persistent_momentum"],
            "metrics": {},
        }]

        reconciled = discovery.apply_cascade_watch_fallback(conn, "2026-07-16", bucket)

        assert reconciled[0]["classification"] == "DISCOVERY"
        assert "watch_reason" not in reconciled[0]["metrics"]
        refusal = conn.execute(
            "SELECT failed_gate FROM refusals WHERE scan_date=? AND symbol=?",
            ("2026-07-16", "NOCOIL"),
        ).fetchone()
        assert refusal["failed_gate"] == "participation"
    finally:
        conn.close()


def test_fcl_absolute_reversal_family_is_independent_of_bucket_membership():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bars = fixture["cases"]["FCL|2026-07-15"]["bars"]

    archetypes = candidates._candidate_discovery_archetypes(bars, discovery_entry=None)

    assert discovery.absolute_reversal_archetype(bars) is True
    assert candidates.setup_type_from_discovery_archetypes(archetypes) == "reversal"
    assert candidates._candidate_discovery_archetypes(
        bars, {"archetypes": ["persistent_momentum"]},
    ) == ["persistent_momentum"]


def test_under_5000_share_average_volume_remains_untradeable():
    bars = [
        {"open": 1000.0, "high": 1010.0, "low": 990.0, "close": 1000.0, "volume": 4_000}
        for _ in range(20)
    ]
    verdict = evaluate_symbol(bars, "ILLIQUID", GateConfig())
    assert verdict["tradeable"] is False
    assert any("avg turnover" in reason for reason in verdict["reasons_failed"])


def test_stop_over_eight_percent_remains_refused():
    result = risk_plan.validate(
        entry=100.0,
        stop=91.0,
        measured_move=120.0,
        regime="RISK_ON",
        setup_family="momentum",
        profile="learning",
        account_capital=1_000_000.0,
    )
    assert result["pass"] is False
    assert result["stop_pct"] == 9.0
    assert result["stop_cap_applied"] <= risk_plan.STOP_CAP_ABSOLUTE
    assert any("exceeds" in reason and "cap" in reason for reason in result["reasons"])
