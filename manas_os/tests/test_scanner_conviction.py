"""WAVE E1 (manas_os/design/CONVICTION_RANK_SPEC_2026-07-21.md) — unit tests
for the conviction score + its five axis computations (scanner/conviction.py),
plus a candidates-level test that conviction reorders survivors without
touching the gate.
"""
import json

from manas_os import db
from manas_os.scanner import candidates, conviction
from manas_os.tests.conftest import insert_price_ramp, seed_confluent_symbol


# ---------------------------------------------------------------------------
# ud_ratio
# ---------------------------------------------------------------------------

def _bar(close, prev_close, volume):
    return {"close": close, "prev_close": prev_close, "volume": volume}


def test_ud_ratio_hand_math():
    # 3 up-days (volumes 100, 200, 300 = 600) and 2 down-days (volumes 400, 100 = 500).
    bars = [
        _bar(101, 100, 100),   # up
        _bar(99, 101, 400),    # down
        _bar(103, 99, 200),    # up
        _bar(98, 103, 100),    # down
        _bar(105, 98, 300),    # up
    ]
    assert conviction.ud_ratio(bars, n=5) == 600.0 / 500.0


def test_ud_ratio_insufficient_bars_is_none():
    bars = [_bar(101, 100, 100), _bar(102, 101, 100)]
    assert conviction.ud_ratio(bars, n=21) is None


def test_ud_ratio_no_down_volume_is_none_not_infinite():
    bars = [_bar(100 + i, 100 + i - 1, 100) for i in range(21)]  # every day up
    assert conviction.ud_ratio(bars, n=21) is None


# ---------------------------------------------------------------------------
# chart_fit_grade — synthetic choppy vs staircase
# ---------------------------------------------------------------------------

def test_chart_fit_grade_staircase_is_momentum_ideal():
    bars = [{"close": 100.0 + i} for i in range(120)]  # clean monotonic rise
    result = conviction.chart_fit_grade(bars)
    assert result["available"] is True
    assert result["crosses"] <= 3
    assert result["ma_direction"] == "up"
    assert result["momentum_grade"] == "ideal"
    assert result["reversion_grade"] == "poor"


def test_chart_fit_grade_choppy_is_momentum_poor():
    bars = [{"close": 100.0 + (3.0 if i % 2 == 0 else -3.0)} for i in range(120)]
    result = conviction.chart_fit_grade(bars)
    assert result["available"] is True
    assert result["crosses"] >= 7
    assert result["momentum_grade"] == "poor"
    assert result["reversion_grade"] == "ideal"


def test_chart_fit_grade_insufficient_bars_is_unavailable():
    bars = [{"close": 100.0 + i} for i in range(10)]
    result = conviction.chart_fit_grade(bars)
    assert result["available"] is False
    assert result["momentum_grade"] is None


# ---------------------------------------------------------------------------
# setup_tier
# ---------------------------------------------------------------------------

def test_setup_tier_a_named_initiation_types():
    for st in ("ep", "d2_episodic", "strong_start_ready", "ipo_base"):
        assert conviction.setup_tier(st, {}) == "A"


def test_setup_tier_a_fresh_base_breakout_by_evidence():
    evidence = {"breakout_age": 2, "close": 105.0, "pivot": 100.0}
    assert conviction.setup_tier("vcp", evidence) == "A"
    # Stale breakout (age > 3) does not qualify.
    assert conviction.setup_tier("vcp", {**evidence, "breakout_age": 10}) != "A"
    # Below pivot does not qualify even if the age is fresh.
    assert conviction.setup_tier("vcp", {**evidence, "close": 95.0}) != "A"


def test_setup_tier_b_velocity_continuation():
    assert conviction.setup_tier("pocket_pivot", {}) == "B"
    assert conviction.setup_tier("persistent_momentum", {}) == "B"


def test_setup_tier_b_near_pivot_only_when_leg_is_fresh():
    assert conviction.setup_tier("near_pivot", {"extension_21": 5.0}) == "B"
    assert conviction.setup_tier("near_pivot", {"extension_21": 8.0}) == "B"
    assert conviction.setup_tier("near_pivot", {"extension_21": 20.0}) == "C"
    assert conviction.setup_tier("near_pivot", {}) == "C"  # unknown extension -- not fresh by default


def test_setup_tier_c_mean_reversion_continuation():
    for st in ("pullback", "long_tail", "watchlist_timing", "some_unknown_setup"):
        assert conviction.setup_tier(st, {}) == "C"


# ---------------------------------------------------------------------------
# featured_in — family dedupe across screener_hits / scan_candidates / discovery_bucket
# ---------------------------------------------------------------------------

def test_featured_in_dedupes_by_family_and_stamps_newest(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidates.ensure_schema(conn)
        scan_date = "2026-07-17"

        # Two screener hits sharing the SAME family (base/pattern) at
        # different dates -- must count as ONE family, newest date wins.
        conn.execute(
            "INSERT INTO screener_hits (trade_date, symbol, screener, bearish) "
            "VALUES (?, 'FEATTEST', 'vcp', 0)", (scan_date,),
        )
        conn.execute(
            "INSERT INTO screener_hits (trade_date, symbol, screener, bearish) "
            "VALUES ('2026-07-14', 'FEATTEST', 'vcp-loose', 0)",
        )
        # A distinct family (momentum) one day earlier.
        conn.execute(
            "INSERT INTO screener_hits (trade_date, symbol, screener, bearish) "
            "VALUES ('2026-07-16', 'FEATTEST', 'momentum-scanner', 0)",
        )
        # Our own detector tag from a persisted scan_candidates history row
        # (distinct family: catalyst).
        conn.execute(
            "INSERT INTO scan_candidates (scan_date, symbol, setup, setup_family) "
            "VALUES ('2026-07-15', 'FEATTEST', 'Earnings Power', 'catalyst')",
        )
        # A discovery_bucket archetype tag (distinct family: weekly_base_breakout).
        conn.execute(
            "INSERT INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
            "VALUES ('2026-07-12', 'FEATTEST', ?, '{}')",
            (json.dumps(["weekly_base_breakout"]),),
        )
        conn.commit()

        result = conviction.featured_in(conn, "FEATTEST", scan_date, lookback_days=10)
        families = {f["family"] for f in result["families"]}
        assert families == {"base/pattern", "momentum", "catalyst", "weekly_base_breakout"}
        assert result["count"] == 4  # DISTINCT families, never raw hit count
        assert result["newest"] == scan_date
        base_pattern_entry = next(f for f in result["families"] if f["family"] == "base/pattern")
        assert base_pattern_entry["newest"] == scan_date  # the LATER of the two same-family hits
    finally:
        conn.close()


def test_featured_in_empty_when_nothing_hit(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        candidates.ensure_schema(conn)
        result = conviction.featured_in(conn, "NOBODY", "2026-07-17")
        assert result == {"families": [], "count": 0, "newest": None}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# theme_membership — defensive read of another lane's (possibly-absent) table
# ---------------------------------------------------------------------------

def test_theme_membership_none_when_table_absent(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        assert conviction.theme_membership(conn, "ANY", "2026-07-17") is None
    finally:
        conn.close()


def test_theme_membership_reads_persisted_theme_when_table_exists(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        from manas_os.scanner import theme_pulse
        theme_pulse.ensure_schema(conn)
        conn.execute(
            "INSERT INTO theme_pulse (scan_date, industry, sector_key, member_symbols_json, "
            "avg_5d_pct, lanes_json) VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-07-17", "Water Supply & Management", "WATER",
             json.dumps(["WABAG", "EIEL", "DENTA"]), 6.2, json.dumps({"scan": ["WABAG"]})),
        )
        conn.commit()
        member = conviction.theme_membership(conn, "wabag", "2026-07-17")
        assert member == {
            "member": True,
            "theme": {
                "industry": "Water Supply & Management", "sector_key": "WATER",
                "sector_label": member["theme"]["sector_label"],
                "member_symbols": ["WABAG", "EIEL", "DENTA"],
                "member_count": 3, "avg_5d_pct": 6.2,
                "lanes": {"scan": ["WABAG"]},
            },
        }
        non_member = conviction.theme_membership(conn, "RANDOMCO", "2026-07-17")
        assert non_member == {"member": False, "theme": None}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# conviction_score — composition + missing-axis honesty
# ---------------------------------------------------------------------------

def test_conviction_score_full_components_weights_and_why():
    components = {
        "setup_type": "ep",
        "tier_evidence": {},
        "day_rvol": 2.0,          # normalizes to 0.5
        "ud_ratio": 2.0,          # normalizes to 1.0
        "nearness_52w": 0.9,      # normalizes to 0.9
        "pct_up_from_65d_low": 40.0,  # normalizes to 0.8
        "featured_in": {"families": [{"family": "momentum", "newest": "2026-07-17"}], "count": 1, "newest": "2026-07-17"},
        "theme": {"member": True, "theme": {"sector_label": "Water", "industry": "Water", "member_count": 3}},
    }
    result = conviction.conviction_score(components)
    axes = result["axes"]
    assert axes["tier"]["raw"] == "A" and axes["tier"]["normalized"] == 1.0
    assert axes["participation"]["normalized"] == round((0.5 + 1.0) / 2, 4)
    assert axes["location"]["normalized"] == round((0.9 + 0.8) / 2, 4)
    assert axes["confluence"]["normalized"] == round(1.0 / 3.0, 4)
    assert axes["theme"]["normalized"] == 1.0
    expected = (
        1.0 * conviction.AXIS_WEIGHTS["tier"]
        + axes["participation"]["normalized"] * conviction.AXIS_WEIGHTS["participation"]
        + axes["location"]["normalized"] * conviction.AXIS_WEIGHTS["location"]
        + (1.0 / 3.0) * conviction.AXIS_WEIGHTS["confluence"]
        + 1.0 * conviction.AXIS_WEIGHTS["theme"]
    ) * 100.0
    assert result["score"] == round(expected, 2)
    assert len(result["why"]) == 5
    assert all(a["available"] for a in axes.values())


def test_conviction_score_missing_axes_contribute_zero_and_are_named():
    components = {"setup_type": "pullback"}  # everything else missing
    result = conviction.conviction_score(components)
    axes = result["axes"]
    assert axes["tier"]["available"] is True  # tier always resolves (defaults to C)
    for name in ("participation", "location", "confluence", "theme"):
        assert axes[name]["available"] is False
        assert axes[name]["contribution"] == 0.0
        assert axes[name]["normalized"] is None
    # tier C contributes 0 too (normalized 0.0), so the WHOLE score is 0 --
    # a pullback with nothing else known must not silently inherit a
    # positive score from a fabricated axis.
    assert result["score"] == 0.0
    why_text = " | ".join(result["why"])
    assert "unavailable" in why_text
    assert "Participation unavailable" in why_text
    assert "Location unavailable" in why_text
    assert "Confluence unavailable" in why_text
    assert "Theme unavailable" in why_text


def test_conviction_score_late_in_move_penalty():
    strong = conviction.conviction_score({"setup_type": "pocket_pivot", "pct_up_from_65d_low": 40.0})
    late = conviction.conviction_score({"setup_type": "pocket_pivot", "pct_up_from_65d_low": 95.0})
    assert late["axes"]["location"]["normalized"] < strong["axes"]["location"]["normalized"]


# ---------------------------------------------------------------------------
# candidates-level: conviction reorders survivors; the gate is unchanged
# ---------------------------------------------------------------------------

def test_conviction_score_reorders_survivors_above_the_old_tiebreak_ranking(tmp_path, monkeypatch):
    """A fresh initiation (tier A, forced via a discovery d2_episodic archetype)
    with WEAKER old-style tiebreak inputs must outrank a plain continuation
    (near_pivot, tier B/C) with STRONGER old-style inputs (delivery_z-boosting
    late-history delivery spike) once conviction_score is the primary ordinal
    key. The gate must be unchanged: both names still survive (neither is
    refused)."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = "2026-06-30"
        # STRONGOLD: elevated delivery% in its final sessions -> a genuinely
        # positive delivery_z under the PRE-conviction tiebreak. Plain ramp,
        # no discovery tag -> setup_type stays "near_pivot" (tier B/C).
        insert_price_ramp(
            conn, symbol="STRONGOLD", n=210,
            delivery=lambda i: 90.0 if i > 195 else 55.0,
        )
        seed_confluent_symbol(conn, symbol="STRONGOLD", scan_date=scan_date)
        # FRESHINIT: flat delivery (delivery_z ~ 0), but tagged by discovery
        # as a d2_episodic initiation -> tier A.
        insert_price_ramp(conn, symbol="FRESHINIT", n=210, delivery=55.0)
        seed_confluent_symbol(conn, symbol="FRESHINIT", scan_date=scan_date)

        real_build_bucket = candidates.discovery.build_bucket

        def fake_build_bucket(conn_, price_date):
            bucket = [e for e in real_build_bucket(conn_, price_date) if e["symbol"] != "FRESHINIT"]
            bucket.append({
                "symbol": "FRESHINIT", "classification": "DISCOVERY",
                "archetypes": ["d2_episodic"], "metrics": {},
            })
            return bucket

        monkeypatch.setattr(candidates.discovery, "build_bucket", fake_build_bucket)
        # Neutralize price_action's TOUCH/POCKET_PIVOT/SHAKEOUT signal overrides
        # (uniformly, for BOTH symbols) so the discovery archetype override's
        # eligibility condition -- baseline setup_type in {"watchlist_timing",
        # "near_pivot"} -- actually holds; a smooth price ramp otherwise touches
        # its own moving average often enough to land on "pullback" first,
        # which the override does NOT replace (by design -- see candidate_for_
        # symbol's discovery-override comment on reversal-context precedence).
        monkeypatch.setattr(
            candidates.price_action, "signals_for_symbol",
            lambda conn_, symbol_, as_of_, max_bars=180: {"recent_signals": []},
        )

        result = candidates.scan_candidates(conn, scan_date)
        dropped_symbols = {r["symbol"] for r in result["dropped"]}
        assert "STRONGOLD" not in dropped_symbols
        assert "FRESHINIT" not in dropped_symbols  # rails: gate unchanged, both survive

        by_symbol = {c["symbol"]: c for c in result["candidates"]}
        assert set(by_symbol) >= {"STRONGOLD", "FRESHINIT"}

        strong = by_symbol["STRONGOLD"]
        fresh = by_symbol["FRESHINIT"]
        assert fresh["conviction_axes"]["tier"]["raw"] == "A"
        assert strong["conviction_axes"]["tier"]["raw"] != "A"
        # the OLD tiebreak really does favor STRONGOLD (its delivery_z beats FRESHINIT's).
        assert (strong["score_breakdown"]["delivery_z"] or 0) > (fresh["score_breakdown"]["delivery_z"] or 0)
        # yet conviction_score promotes FRESHINIT to the top.
        assert fresh["conviction_score"] > strong["conviction_score"]
        assert fresh["rank"] < strong["rank"]
        assert fresh["conviction_rank"] == 1
    finally:
        conn.close()


def test_conviction_columns_persist_and_round_trip(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date="2026-06-30")
        run_result = candidates.run(conn, "2026-06-30")
        assert run_result["status"] == "ok"

        row = conn.execute(
            "SELECT conviction_score, conviction_axes_json, conviction_rank "
            "FROM scan_candidates WHERE scan_date = '2026-06-30' AND symbol = 'ACME'"
        ).fetchone()
        assert row["conviction_score"] is not None
        assert row["conviction_rank"] == 1  # only survivor -> top of its own top-15
        payload = json.loads(row["conviction_axes_json"])
        assert set(payload["axes"]) == {"tier", "participation", "location", "confluence", "theme"}
        assert len(payload["why"]) == 5

        loaded = candidates.load_persisted_candidates(conn, "2026-06-30")
        card = loaded["candidates"][0]
        assert card["conviction_score"] == row["conviction_score"]
        assert card["conviction_axes"]["tier"]["raw"] in ("A", "B", "C")
        assert card["conviction_rank"] == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WAVE E1 union leaderboard (coordinator correction 2026-07-22): a top-15
# built only from gate-passed scan survivors structurally excludes the WATCH
# lane, which practitioner-leaders evidence showed materially outperforming
# the SCAN lane. watch_lane_conviction/conviction_leaderboard union both
# lanes for DISPLAY only -- the gate and risk/plan.py sizing are untouched.
# ---------------------------------------------------------------------------

def test_watch_lane_conviction_never_touches_scan_candidates_or_refusals(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = "2026-06-30"
        insert_price_ramp(conn, symbol="WATCHME", n=210)

        monkeypatch.setattr(
            candidates.discovery, "build_bucket",
            lambda conn_, price_date: [{
                "symbol": "WATCHME", "classification": "WATCH",
                "archetypes": ["anticipation_watch"], "metrics": {},
            }],
        )

        entries = candidates.watch_lane_conviction(conn, scan_date)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["symbol"] == "WATCHME"
        assert entry["lane"] == "watch"
        assert entry["action"] == "armed, waiting for trigger -- no size until it triggers"
        assert isinstance(entry["conviction_score"], float)
        assert set(entry["conviction_axes"]) == {"tier", "participation", "location", "confluence", "theme"}

        candidates.ensure_schema(conn)
        candidates.ensure_refusals_schema(conn)
        assert conn.execute("SELECT COUNT(*) FROM scan_candidates").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM refusals").fetchone()[0] == 0
    finally:
        conn.close()


def test_conviction_leaderboard_unions_scan_and_watch_lanes(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        scan_date = "2026-06-30"
        insert_price_ramp(conn, symbol="ACME", n=210)
        seed_confluent_symbol(conn, symbol="ACME", scan_date=scan_date)
        insert_price_ramp(conn, symbol="WATCHME", n=210)
        # No screener_hits seeded (confluence pool) and, per WAVE_M M2's own
        # nearness>=0.85 pre-filter, an old far-above-current high keeps
        # WATCHME OUT of detector_shortlist too -- its ONLY route into
        # anything must be the fake WATCH bucket tag below, exactly like a
        # real pre-trigger name that hasn't cleared any gate-pool test yet.
        conn.execute(
            "UPDATE daily_prices SET high = 400.0 WHERE symbol='WATCHME' "
            "AND trade_date = (SELECT MIN(trade_date) FROM daily_prices WHERE symbol='WATCHME')"
        )
        conn.commit()

        real_build_bucket = candidates.discovery.build_bucket

        def fake_build_bucket(conn_, price_date):
            bucket = [e for e in real_build_bucket(conn_, price_date) if e["symbol"] != "WATCHME"]
            bucket.append({
                "symbol": "WATCHME", "classification": "WATCH",
                "archetypes": ["anticipation_watch"], "metrics": {},
            })
            return bucket

        monkeypatch.setattr(candidates.discovery, "build_bucket", fake_build_bucket)

        run_result = candidates.run(conn, scan_date)
        assert run_result["status"] == "ok"

        board = candidates.conviction_leaderboard(conn, scan_date)
        lanes = {e["symbol"]: e["lane"] for e in board["entries"]}
        actions = {e["symbol"]: e["action"] for e in board["entries"]}
        assert lanes.get("ACME") == "scan"
        assert lanes.get("WATCHME") == "watch"
        assert actions["ACME"] == "sized plan available"
        assert actions["WATCHME"] == "armed, waiting for trigger -- no size until it triggers"
        # ranked strictly by conviction_score desc, across both lanes
        scores = [e["conviction_score"] for e in board["entries"]]
        assert scores == sorted(scores, reverse=True)
        assert all(e["leaderboard_rank"] is not None for e in board["top"])
        assert len(board["top"]) <= 15
        # WATCHME must never have leaked into the gate tables
        assert conn.execute("SELECT COUNT(*) FROM scan_candidates WHERE symbol='WATCHME'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM refusals WHERE symbol='WATCHME'").fetchone()[0] == 0
    finally:
        conn.close()


def test_conviction_rank_marks_only_top_fifteen():
    cands = []
    for i in range(20):
        cands.append({
            "symbol": f"S{i:02d}",
            "rank_inputs": (0.0, 0.0, 0),
            "conviction_score": float(20 - i),  # S00 highest, S19 lowest
            "score_breakdown": {},
        })
    candidates._assign_ranks(cands)
    ranked_by_symbol = {c["symbol"]: c for c in cands}
    top15 = [c for c in cands if c["conviction_rank"] is not None]
    assert len(top15) == 15
    assert {c["conviction_rank"] for c in top15} == set(range(1, 16))
    assert ranked_by_symbol["S00"]["conviction_rank"] == 1
    assert ranked_by_symbol["S00"]["rank"] == 1
    assert ranked_by_symbol["S19"]["conviction_rank"] is None
    assert ranked_by_symbol["S19"]["rank"] == 20  # still has an ordinal rank -- "keeps a rank"
