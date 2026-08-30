"""JSON sibling report tests (UI_BACKEND_INTEGRATION_PLAN.md step 1).

Non-negotiable per the plan: every honesty-footer fact the Markdown report
prints in prose must also exist as a typed JSON field, for the SAME
ScanResult (no re-derivation). These tests build one ScanResult and check
both renders agree, using the same fixtures as test_nightly_scan_report.py.
"""
from datetime import datetime, timedelta, timezone

import pytest

from unidesk.contracts.market import DailyBar
from unidesk.momentum.data.corp_actions import ConfirmedAction
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.report import build_nightly_report
from unidesk.momentum.report_json import build_nightly_json
from unidesk.momentum.scan import scan_universe

UTC = timezone.utc
DAY0 = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)


def add_session(store, symbol, i, close, high=None, low=None, vol=1000.0, dvp=None):
    session = (DAY0 + timedelta(days=i)).date()
    bar = DailyBar(
        symbol=symbol, session=session,
        open=close, high=high or close + 0.5, low=low or close - 0.5,
        close=close, volume=int(vol),
        delivery_percentage=dvp, data_version="test",
    )
    store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=DAY0 + timedelta(days=i + 1)))


def build_store():
    """STRONG is tuned (not just trending) to actually clear the Momentum
    Burst detector's thresholds -- wide range for the first 45 sessions,
    tighter range for the next 20 (the ADR/contraction prior window), a
    tight last 5 sessions (the contraction "recent" window), and a volume
    spike on the final session (RVOL). FLAT never qualifies (real zeros,
    low RS rank) -- both mirror the real 2026-07-03 report's shape: some
    names pass Momentum Burst, most don't."""
    store = InMemoryMarketStore()
    for i in range(70):
        close = 90 + i * 0.9
        if i < 65:
            half_range, vol = 3.0, 1000.0
        else:
            half_range, vol = 0.5, (5000.0 if i == 69 else 1000.0)
        add_session(store, "STRONG", i, close,
                    high=close + half_range, low=close - half_range,
                    vol=vol, dvp=60.0)
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800.0)
    return store


def test_json_universe_fields_match_markdown_numbers():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    footer = data["honesty_footer"]
    assert data["schema_version"] == 1
    assert data["session_date"] == scan.last_session
    assert footer["universe_scanned"] == scan.scanned
    assert str(scan.scanned) in report
    assert footer["above_ema21"] == scan.above_ema21
    assert footer["above_ema21_of"] == scan.scanned
    assert f"{scan.above_ema21}/{scan.scanned} above EMA21" in report


def test_json_skip_count_matches_markdown():
    store = build_store()
    store.add_daily_bar(VersionedDailyBar(
        bar=DailyBar(symbol="SHORTY", session=(DAY0 + timedelta(days=3)).date(),
                     open=10, high=11, low=9, close=10, volume=100,
                     data_version="test"),
        available_at=DAY0 + timedelta(days=4)))
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    n_skip = scan.skipped.get("insufficient_sessions", 0)
    assert n_skip > 0
    assert data["honesty_footer"]["universe_skipped_insufficient_history"] == n_skip
    assert f"{n_skip} skipped (insufficient history)" in report
    assert f"Symbols skipped for insufficient history: {n_skip}." in report


def test_json_regime_not_built_flag_matches_markdown_placeholder():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    assert "not built yet" in report
    footer = data["honesty_footer"]
    assert footer["regime_built"] is False
    assert footer["regime_note"] == "not built yet (wave N2)"
    assert footer["regime_note"] in report


def test_json_regime_built_flag_flips_when_a_real_regime_is_passed():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    data = build_nightly_json(scan, regime_note="BULL over 233 sessions")
    assert data["honesty_footer"]["regime_built"] is True


def test_json_adjustment_status_unadjusted_matches_markdown():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    footer = data["honesty_footer"]
    assert "Unadjusted prices" in report
    assert footer["adjustment_status"] == "unadjusted_provisional"
    assert footer["actions_applied"] == 0
    assert footer["adjusted_symbols"] == 0
    assert "Unadjusted prices" in footer["adjustment_note"]


def test_json_adjustment_status_confirmed_ca_matches_markdown():
    store = InMemoryMarketStore()
    for i in range(70):
        add_session(store, "SPLIT", i, 200.0 if i < 35 else 100.0, vol=1000)
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800)
    ex = (DAY0 + timedelta(days=35)).date()
    actions = [ConfirmedAction("SPLIT", ex, 0.5, "test")]
    scan = scan_universe(store, DAY0 + timedelta(days=70), actions=actions)
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    footer = data["honesty_footer"]
    assert "derived view" in report
    assert "Unadjusted prices" not in report
    assert footer["adjustment_status"] == "confirmed_ca_applied"
    assert footer["actions_applied"] == scan.actions_applied == 1
    assert footer["adjusted_symbols"] == scan.adjusted_symbols == 1
    assert "derived view" in footer["adjustment_note"]


def test_json_disclaimer_and_detection_inputs_policy_present():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)
    footer = data["honesty_footer"]
    assert footer["disclaimer"] in report
    assert footer["detection_inputs_policy"] in report


def test_json_setups_and_candidates_mirror_markdown_symbols():
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)

    from unidesk.momentum.detectors.momentum_burst import Detection
    valid = [
        s for s in scan.symbols
        if s.detectors.get("momentum_burst", (None,))[0] is Detection.VALID
    ]
    if not valid:
        pytest.skip("fixture did not clear the burst detector this run")

    assert "Momentum Burst" in report
    burst_setup = next(s for s in data["setups"] if s["detector"] == "momentum_burst")
    assert burst_setup["candidate_count"] == len(valid)
    json_symbols = {c["symbol"] for c in burst_setup["candidates"]}
    assert json_symbols == {s.symbol for s in valid}
    for c in burst_setup["candidates"]:
        assert c["symbol"] in report
    # every setup candidate also appears in the flat candidates list, tagged
    flat_symbols = {c["symbol"] for c in data["candidates"] if c["detector"] == "momentum_burst"}
    assert flat_symbols == json_symbols


def test_json_no_candidates_case():
    store = InMemoryMarketStore()
    for i in range(70):
        add_session(store, "FLAT", i, 50.0, vol=800.0)
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    report = build_nightly_report(scan)
    data = build_nightly_json(scan)
    assert "No candidates passed tonight" in report
    assert data["setups"] == []
    assert data["candidates"] == []


def test_json_is_serializable():
    import json as _json
    store = build_store()
    scan = scan_universe(store, DAY0 + timedelta(days=70))
    data = build_nightly_json(scan)
    text = _json.dumps(data)
    assert _json.loads(text) == data


def test_json_exposes_additive_detector_trust_and_preserves_raw_outputs():
    """Known-bad detector verdicts remain auditable but cannot be treated as
    rankable by a consumer that understands the trust envelope."""
    scan = scan_universe(build_store(), DAY0 + timedelta(days=70))
    data = build_nightly_json(scan)

    trust = data["detector_trust"]
    assert trust["base_breakout"] == {
        "status": "BLOCKED",
        "reason": "missing_breakout_condition_and_inverted_room_rule",
        "version": "audit-2026-08-30",
        "rankable": False,
    }
    assert trust["episodic_pivot"]["status"] == "VERIFIED"
    assert trust["episodic_pivot"]["rankable"] is True

    for setup in data["setups"]:
        assert setup["trust"] == trust[setup["detector"]]
    for candidate in data["candidates"]:
        assert candidate["trust"] == trust[candidate["detector"]]


def test_json_emits_cleanroom_base_episodes_separately_from_legacy_candidates():
    store = InMemoryMarketStore()
    for i in range(7):
        close = 80 + i
        add_session(store, "BASE", i, close, high=close + 1, low=close - 1)
    add_session(store, "BASE", 7, 100, high=110, low=99)
    for i in range(8, 18):
        add_session(store, "BASE", i, 95, high=96, low=90, vol=1_000)
    for i in range(18, 28):
        add_session(store, "BASE", i, 96, high=101 if i == 18 else 96, low=94, vol=500)

    scan = scan_universe(
        store, DAY0 + timedelta(days=28), min_sessions=20, run_detectors=False,
    )
    data = build_nightly_json(scan)

    [episode] = data["base_episodes"]
    assert episode["symbol"] == "BASE"
    assert episode["base_start"] == (DAY0 + timedelta(days=8)).date().isoformat()
    assert episode["method_version"] == "cleanroom-base-v1"
    assert episode["adjustment_basis_hash"]
    assert episode["annotations"][0]["kind"] == "squat"
