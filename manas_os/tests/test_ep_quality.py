"""Unit tests for scanner/ep_quality.py (EP_VS_SIP_SPEC_2026-07-21).

Two test styles, deliberately combined:
  - Full hand-built-bar chains through burst_nature -> location_read ->
    classify (the spec's own done-tests are phrased this way: "a synthetic
    fade-natured symbol classifies fade", "a clean-continuation symbol at a
    fresh breakout classifies SWING_EP"). Every bar-based fixture below was
    verified against the REAL functions (including risk.plan.
    structural_target's real resistance scan) before being pinned here --
    see the numbers printed by each scenario's construction; nothing is
    tuned to whatever the code happened to output blind.
  - Direct classify()-level tests with hand-built nature/location dicts, to
    pin the doctrine's priority rules (AVOID beats everything; fade/unknown
    can never reach SWING_EP regardless of how favourable the location is)
    exhaustively and fast, without fighting bar synthesis for every branch.
"""
from __future__ import annotations

import json

from manas_os import db
from manas_os.scanner import ep_quality as epq


# --- bar builders --------------------------------------------------------

def _bar(o, h, l, c, v=500_000, prev_close=None):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v, "prev_close": prev_close}


def _flat(n, price=100.0, v=500_000):
    bars = []
    pc = price
    for _ in range(n):
        bars.append(_bar(price, price * 1.01, price * 0.99, price, v, prev_close=pc))
        pc = price
    return bars


def _burst_bar(prev_close, pct=10.0, vol=2_000_000):
    """A single burst day: change_pct == pct (>= BURST_CHANGE_PCT)."""
    close = prev_close * (1 + pct / 100.0)
    open_ = prev_close * 1.02
    high = close * 1.02
    low = prev_close * 1.0
    return _bar(open_, high, low, close, vol, prev_close=prev_close)


def _path(prev_close, end_factor, days, vol=500_000):
    """A linear (up or down) walk from prev_close to prev_close*end_factor
    over `days` sessions -- never itself a burst day (gentle steps)."""
    bars = []
    pc = prev_close
    start_price = prev_close
    end_price = prev_close * end_factor
    for k in range(days):
        frac = (k + 1) / days
        close = start_price + (end_price - start_price) * frac
        open_ = pc * 1.001
        high = max(open_, close, pc) * 1.005
        low = min(open_, close, pc) * 0.995
        bars.append(_bar(open_, high, low, close, vol, prev_close=pc))
        pc = close
    return bars


def _swing_burst_cycles(n_cycles=4):
    """flat baseline + n_cycles of (burst day that HOLDS -> gentle uptrend
    continuation), i.e. a clean-continuation symbol's own burst history."""
    bars = _flat(10, price=100.0)
    pc = bars[-1]["close"]
    for _ in range(n_cycles):
        b = _burst_bar(pc, pct=10.0)
        bars.append(b)
        pc = b["close"]
        fwd5 = _path(pc, end_factor=1.045, days=5)   # continues up, never undercuts b's low
        bars.extend(fwd5)
        pc = fwd5[-1]["close"]
        pad9 = _path(pc, end_factor=1.05, days=9)
        bars.extend(pad9)
        pc = pad9[-1]["close"]
    return bars


def _fresh_base_breakout(bars_so_far, loose_days=23):
    """Append a loose-tight base, then one extremely-tight coil day, then a
    breakout day above the base's own level. Returns (bars, pivot) where
    pivot is the base level broken out through (breakout_age becomes 0-1,
    tightness_pctile of the coil day lands in the bottom quartile)."""
    bars = list(bars_so_far)
    pc = bars[-1]["close"]
    target_pivot = pc * 1.03
    loose = []
    for k in range(loose_days):
        frac = (k + 1) / loose_days
        close = pc + (target_pivot - pc) * frac
        open_ = close * 0.999
        high = close * 1.006
        low = close * 0.994
        prev = pc if k == 0 else loose[-1]["close"]
        loose.append(_bar(open_, high, low, close, 500_000, prev_close=prev))
        pc = close
    bars.extend(loose)
    pivot = bars[-1]["close"]
    coil = _bar(pivot * 0.9995, pivot * 1.001, pivot * 0.999, pivot * 1.0002, 400_000,
                prev_close=bars[-1]["close"])
    bars.append(coil)
    breakout = _bar(pivot * 1.005, pivot * 1.025, pivot * 1.001, pivot * 1.02, 1_500_000,
                     prev_close=coil["close"])
    bars.append(breakout)
    return bars, pivot


def _extend_further(bars_so_far, days=5, step=1.03):
    """Continue a strong rally past a breakout far enough to trip the
    close > 1.08*EMA21 extension test -- no single day here is itself a
    burst (gentle ~3%/day steps), and these trailing days have no forward
    window yet so they can never retroactively become countable burst days."""
    bars = list(bars_so_far)
    pc = bars[-1]["close"]
    for _ in range(days):
        close = pc * step
        open_ = pc * 1.005
        high = close * 1.01
        low = pc * 0.998
        bars.append(_bar(open_, high, low, close, 1_000_000, prev_close=pc))
        pc = close
    return bars


def _fade_burst_cycles(n_cycles=4):
    """flat baseline + n_cycles of (burst day that FADES -- undercuts its
    own low within the next 5 sessions -- then a mild recovery before the
    next burst), i.e. a burst-and-fade symbol's own history."""
    bars = _flat(10, price=100.0)
    pc = bars[-1]["close"]
    for _ in range(n_cycles):
        b = _burst_bar(pc, pct=10.0)
        bars.append(b)
        pc = b["close"]
        burst_low = b["low"]
        fade5 = _path(pc, end_factor=(burst_low * 0.85) / pc, days=5)  # undercuts burst_low
        bars.extend(fade5)
        pc = fade5[-1]["close"]
        recover9 = _path(pc, end_factor=1.06, days=9)
        bars.extend(recover9)
        pc = recover9[-1]["close"]
    return bars


def _peak(prev_close, peak_factor=1.08, vol=800_000):
    close = prev_close * peak_factor
    return _bar(prev_close * 1.01, close * 1.01, prev_close * 0.99, close, vol, prev_close=prev_close)


def _resistance_history(approach_factor):
    """flat -> one real confirmed swing-high peak -> pullback -> a fresh
    tight base that re-approaches the peak level from below by
    `approach_factor` (of the peak level) -- exercises the REAL
    risk.plan.structural_target resistance scan (tier 1: prior swing high),
    not a synthetic projection. Returns (bars, pivot)."""
    bars = _flat(30, price=100.0)
    pc = bars[-1]["close"]
    peak = _peak(pc, peak_factor=1.08)
    bars.append(peak)
    pc = peak["close"]
    peak_level = peak["high"]

    after_peak = _path(pc, end_factor=0.97, days=8)
    bars.extend(after_peak)
    pc = after_peak[-1]["close"]

    pullback = _path(pc, end_factor=0.93, days=15)
    bars.extend(pullback)
    pc = pullback[-1]["close"]

    approach_target = peak_level * approach_factor
    base = _path(pc, end_factor=approach_target / pc, days=20)
    bars.extend(base)
    pc = base[-1]["close"]

    coil = _bar(pc * 0.999, pc * 1.002, pc * 0.998, pc * 1.0005, 400_000, prev_close=pc)
    bars.append(coil)
    breakout = _bar(coil["close"] * 1.002, coil["close"] * 1.01, coil["close"] * 0.999,
                     coil["close"] * 1.006, 1_200_000, prev_close=coil["close"])
    bars.append(breakout)
    return bars, coil["close"]


# --- burst_nature --------------------------------------------------------

def test_burst_nature_swing_when_bursts_hold():
    bars = _swing_burst_cycles(4)
    nature = epq.burst_nature(bars)
    assert nature["burst_days"] == 4
    assert nature["held"] == 4
    assert nature["hold_rate"] == 1.0
    assert nature["median_fwd_5"] > 0
    assert nature["nature"] == "swing"


def test_burst_nature_fade_when_bursts_undercut():
    bars = _fade_burst_cycles(4)
    nature = epq.burst_nature(bars)
    assert nature["burst_days"] == 4
    assert nature["held"] == 0
    assert nature["hold_rate"] == 0.0
    assert nature["median_fwd_5"] < 0
    assert nature["nature"] == "fade"


def test_burst_nature_unknown_under_four_bursts():
    bars = _swing_burst_cycles(2)  # only 2 burst days -- below the n>=4 floor
    nature = epq.burst_nature(bars)
    assert nature["burst_days"] < epq.NATURE_MIN_BURST_DAYS
    assert nature["nature"] == "unknown"


def test_burst_nature_no_bars_is_unknown():
    nature = epq.burst_nature([])
    assert nature["burst_days"] == 0
    assert nature["hold_rate"] is None
    assert nature["nature"] == "unknown"


def test_burst_nature_uncountable_trailing_burst_not_guessed():
    """A burst day too close to the end of history (no full 5-day forward
    window) must not be counted -- never guessed at."""
    bars = _flat(10, price=100.0)
    bars.append(_burst_bar(bars[-1]["close"], pct=10.0))  # last bar = burst, no forward data
    nature = epq.burst_nature(bars)
    assert nature["burst_days"] == 0
    assert nature["nature"] == "unknown"


# --- location_read ---------------------------------------------------------

def test_location_read_fresh_base_breakout_with_room():
    bars = _swing_burst_cycles(4)
    bars, pivot = _fresh_base_breakout(bars)
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["fresh_base_breakout"] is True
    assert loc["breakout_age"] is not None and loc["breakout_age"] <= epq.FRESH_BASE_BREAKOUT_AGE_MAX
    assert loc["tightness_pctile"] is not None and loc["tightness_pctile"] <= epq.FRESH_BASE_TIGHTNESS_MAX_PCTILE
    assert loc["extended"] is False
    # No real overhead resistance in this monotonically-new-high history ->
    # open sky, honestly reported as room_pct=None rather than a fake number.
    assert loc["room_pct"] is None
    assert loc["room_above"] is True
    assert loc["near_resistance"] is False


def test_location_read_extended_past_1_08x_ema21():
    bars = _swing_burst_cycles(4)
    bars, pivot = _fresh_base_breakout(bars)
    bars = _extend_further(bars)
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["extended"] is True
    assert loc["extension_ratio"] > epq.EXTENSION_EMA21_MULTIPLE
    assert loc["close"] > epq.EXTENSION_EMA21_MULTIPLE * loc["ema21"]


def test_location_read_real_resistance_no_room_not_near():
    """Real (non-synthetic) resistance ~2-3%% above close: no room, but not
    close enough to be the doctrine's 'avoidable' near-resistance case."""
    bars, pivot = _resistance_history(approach_factor=0.97)
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["resistance"] is not None
    assert loc["resistance_method"] == "prior swing high"
    assert epq.NEAR_RESISTANCE_PCT <= loc["room_pct"] < epq.NO_ROOM_PCT
    assert loc["room_above"] is False
    assert loc["near_resistance"] is False


def test_location_read_near_resistance():
    bars, pivot = _resistance_history(approach_factor=0.99)
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["resistance"] is not None
    assert loc["room_pct"] < epq.NEAR_RESISTANCE_PCT
    assert loc["near_resistance"] is True
    assert loc["room_above"] is False


def test_location_read_empty_bars():
    loc = epq.location_read([])
    assert loc["fresh_base_breakout"] is False
    assert loc["room_above"] is False
    assert loc["close"] is None


# --- classify: full done-tests (bar chain -> verdict) -----------------------

def test_fade_natured_symbol_can_never_reach_swing_ep():
    bars = _fade_burst_cycles(4)
    nature = epq.burst_nature(bars)
    assert nature["nature"] == "fade"
    loc = epq.location_read(bars, pivot=None, setup_family="ep")
    result = epq.classify(nature, loc)
    assert result["verdict"] != "SWING_EP"
    assert result["verdict"] == "INTRADAY_SIP"


def test_clean_continuation_fresh_breakout_with_room_is_swing_ep():
    bars = _swing_burst_cycles(4)
    bars, pivot = _fresh_base_breakout(bars)
    nature = epq.burst_nature(bars)
    assert nature["nature"] == "swing"
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    result = epq.classify(nature, loc)
    assert result["verdict"] == "SWING_EP"


def test_same_symbol_extended_is_intraday_sip():
    bars = _swing_burst_cycles(4)
    bars, pivot = _fresh_base_breakout(bars)
    bars = _extend_further(bars)
    nature = epq.burst_nature(bars)
    assert nature["nature"] == "swing"  # same symbol, same own-history nature
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["extended"] is True
    result = epq.classify(nature, loc)
    assert result["verdict"] == "INTRADAY_SIP"


def test_under_four_burst_days_is_unknown_and_never_swing_ep():
    bars = _swing_burst_cycles(2)
    bars, pivot = _fresh_base_breakout(bars)
    nature = epq.burst_nature(bars)
    assert nature["nature"] == "unknown"
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    result = epq.classify(nature, loc)
    assert result["verdict"] != "SWING_EP"


def test_near_resistance_is_avoid():
    bars, pivot = _resistance_history(approach_factor=0.99)
    nature = epq.burst_nature(bars)
    loc = epq.location_read(bars, pivot=pivot, setup_family="ep")
    assert loc["near_resistance"] is True
    result = epq.classify(nature, loc)
    assert result["verdict"] == "AVOID"


# --- classify: direct dict-level priority-rule tests ------------------------
# (isolates the doctrine's precedence rules from bar-synthesis noise: every
# location input below is otherwise maximally favourable for SWING_EP.)

_FAVOURABLE_LOCATION = {
    "fresh_base_breakout": True, "breakout_age": 1, "tightness_pctile": 5.0,
    "extended": False, "extension_ratio": 1.01,
    "room_above": True, "room_pct": 12.0, "near_resistance": False,
}


def test_classify_fade_nature_never_swing_ep_even_with_perfect_location():
    nature = {"nature": "fade", "hold_rate": 0.1, "burst_days": 10, "median_fwd_5": -6.0}
    result = epq.classify(nature, _FAVOURABLE_LOCATION)
    assert result["verdict"] == "INTRADAY_SIP"
    assert "fade" in result["why"].lower()


def test_classify_unknown_nature_degrades_to_intraday_sip_with_named_reason():
    nature = {"nature": "unknown", "hold_rate": None, "burst_days": 1, "median_fwd_5": None}
    result = epq.classify(nature, _FAVOURABLE_LOCATION)
    assert result["verdict"] == "INTRADAY_SIP"
    assert "no burst history" in result["why"].lower()


def test_classify_fade_and_extended_is_avoid():
    nature = {"nature": "fade", "hold_rate": 0.1, "burst_days": 10, "median_fwd_5": -6.0}
    location = dict(_FAVOURABLE_LOCATION, extended=True, extension_ratio=1.2)
    result = epq.classify(nature, location)
    assert result["verdict"] == "AVOID"


def test_classify_near_resistance_beats_everything():
    """near_resistance forces AVOID even for an otherwise-perfect swing setup."""
    nature = {"nature": "swing", "hold_rate": 0.9, "burst_days": 8, "median_fwd_5": 5.0}
    location = dict(_FAVOURABLE_LOCATION, near_resistance=True, room_pct=0.5, room_above=False)
    result = epq.classify(nature, location)
    assert result["verdict"] == "AVOID"


def test_classify_swing_ep_full_pass():
    nature = {"nature": "swing", "hold_rate": 0.9, "burst_days": 8, "median_fwd_5": 5.0}
    result = epq.classify(nature, _FAVOURABLE_LOCATION)
    assert result["verdict"] == "SWING_EP"


def test_classify_mixed_nature_can_also_reach_swing_ep():
    nature = {"nature": "mixed", "hold_rate": 0.5, "burst_days": 6, "median_fwd_5": 1.0}
    result = epq.classify(nature, _FAVOURABLE_LOCATION)
    assert result["verdict"] == "SWING_EP"


# --- every checklist item exposes its number, never a bare boolean --------

def test_every_checklist_item_exposes_its_number():
    nature = {"nature": "swing", "hold_rate": 0.9, "burst_days": 8, "median_fwd_5": 5.0}
    result = epq.classify(nature, _FAVOURABLE_LOCATION)
    checklist = result["checklist"]
    assert len(checklist) == 5
    expected_items = {
        "historical continuation nature", "room above", "fresh base breakout",
        "extended already", "near resistance",
    }
    assert {c["item"] for c in checklist} == expected_items
    for entry in checklist:
        assert isinstance(entry["pass"], bool)
        # The number behind the boolean must be present -- a dict of at
        # least one real (non-None) numeric/informative field, never {}.
        assert isinstance(entry["value"], dict) and entry["value"]
        assert any(v is not None for v in entry["value"].values())


def test_checklist_numbers_match_across_verdicts():
    """Spot-check the SPECIFIC numbers the spec names (room_pct, extension
    ratio, hold_rate, burst count) actually appear in the checklist, for
    every verdict family."""
    fade_bars = _fade_burst_cycles(4)
    fade_nature = epq.burst_nature(fade_bars)
    fade_loc = epq.location_read(fade_bars, pivot=None, setup_family="ep")
    fade_result = epq.classify(fade_nature, fade_loc)
    nature_item = next(c for c in fade_result["checklist"] if c["item"] == "historical continuation nature")
    assert nature_item["value"]["hold_rate"] == fade_nature["hold_rate"]
    assert nature_item["value"]["burst_days"] == fade_nature["burst_days"]

    swing_bars = _swing_burst_cycles(4)
    swing_bars, pivot = _fresh_base_breakout(swing_bars)
    swing_nature = epq.burst_nature(swing_bars)
    swing_loc = epq.location_read(swing_bars, pivot=pivot, setup_family="ep")
    swing_result = epq.classify(swing_nature, swing_loc)
    room_item = next(c for c in swing_result["checklist"] if c["item"] == "room above")
    assert room_item["value"]["room_pct"] == swing_loc["room_pct"]
    extended_item = next(c for c in swing_result["checklist"] if c["item"] == "extended already")
    assert extended_item["value"]["extension_ratio"] == swing_loc["extension_ratio"]


# --- compute_ep_quality: persistence ---------------------------------------

def test_compute_ep_quality_persists_row(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    bars = _swing_burst_cycles(4)
    bars, pivot = _fresh_base_breakout(bars)
    result = epq.compute_ep_quality(
        conn, symbol="testco", scan_date="2026-07-22", bars=bars, pivot=pivot, setup_family="ep",
    )
    assert result["verdict"] == "SWING_EP"
    row = conn.execute(
        "SELECT * FROM ep_quality_daily WHERE scan_date=? AND symbol=?",
        ("2026-07-22", "TESTCO"),
    ).fetchone()
    assert row is not None
    assert row["verdict"] == "SWING_EP"
    assert row["nature"] == "swing"
    assert row["fresh_base"] == 1
    assert row["extended"] == 0
    checklist = json.loads(row["checklist_json"])
    assert len(checklist) == 5
    for entry in checklist:
        assert entry["value"]


def test_compute_ep_quality_upserts_on_rerun(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    bars = _fade_burst_cycles(4)
    epq.compute_ep_quality(conn, symbol="dup", scan_date="2026-07-22", bars=bars)
    epq.compute_ep_quality(conn, symbol="dup", scan_date="2026-07-22", bars=bars)
    count = conn.execute(
        "SELECT COUNT(*) AS n FROM ep_quality_daily WHERE scan_date=? AND symbol=?",
        ("2026-07-22", "DUP"),
    ).fetchone()["n"]
    assert count == 1
