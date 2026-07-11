from manas_os.engine import eod_detectors as ed


def _bar(i, close, open_=None, high=None, low=None, volume=1000, delivery=50):
    return {
        "date": f"2026-01-{i:02d}",
        "open": close if open_ is None else open_,
        "high": close + 1 if high is None else high,
        "low": close - 1 if low is None else low,
        "close": close,
        "prev_close": close - 1,
        "volume": volume,
        "delivery_pct": delivery,
    }


def test_exit_state_names_structural_break_rules():
    bars = [_bar(i, 120 + i, volume=1000) for i in range(1, 211)]
    bars[-2] = {**bars[-2], "close": 150, "volume": 1000}
    bars[-1] = {**bars[-1], "open": 151, "high": 153, "low": 80, "close": 90, "volume": 2000}

    state = ed.exit_state(bars)

    fired = {rule["rule"] for rule in state["fired_rules"]}
    assert state["state"] == "Broken"
    assert "below-50SMA" in fired
    assert "below-21EMA" in fired
    assert "distribution-days" in fired


def test_launch_pad_requires_clustered_rising_mas_and_volume():
    # Gentle rise so all three MAs stay within 3% of price, stacked and rising
    # (the "launch pad" coil where MAs have caught up to price).
    bars = []
    for i in range(1, 80):
        close = 100 + i * 0.08
        bars.append(_bar(i, close, volume=1000))
    bars[-1] = {**bars[-1], "volume": 1500}  # volume confirmation

    result = ed.launch_pad(bars)

    assert result is not None
    assert result["setup"] == "launch_pad"


def test_ants_accumulation_is_boolean_chip_input():
    # ~25% price gain + ~23% volume rise over 15 days, all up days, delivery
    # rising — satisfies the ANTS accumulation rule.
    bars = []
    for i in range(1, 17):
        close = 100.0 + i * 1.8
        bars.append(_bar(i, close, volume=1000 + i * 25, delivery=45 + i))

    result = ed.ants_accumulation(bars)

    assert result is not None
    assert result["filter"] == "ANTS"


def test_ep_skips_when_gap_plus_range_too_wide():
    bars = [_bar(i, 100 + i * 0.1, high=101 + i * 0.1, low=99 + i * 0.1) for i in range(1, 36)]
    bars[-1] = _bar(36, 112, open_=110, high=120, low=108, volume=2000)
    quality = {"eps_qoq": 40, "eps_yoy": 45, "sales_yoy": 35, "market_cap_cr": 1000, "asm_stage": None}

    assert ed.earnings_power(bars, quality) is None


def test_ep_accepts_quiet_pre_gap_base():
    bars = [_bar(i, 100, high=101, low=99) for i in range(1, 26)]
    bars.append({
        "date": "2026-01-26",
        "open": 106,
        "high": 108,
        "low": 105,
        "close": 107,
        "prev_close": 100,
        "volume": 2000,
        "delivery_pct": 50,
    })
    quality = {"eps_qoq": 35, "eps_yoy": 40, "sales_yoy": 35, "market_cap_cr": 1000}

    result = ed.earnings_power(bars, quality)

    assert result is not None
    assert "pre-gap band" in result["detail"]


def test_ep_rejects_pre_gap_runup_drift():
    bars = [_bar(i, 100 + (40 / 24) * (i - 1), high=101 + (40 / 24) * (i - 1), low=99 + (40 / 24) * (i - 1)) for i in range(1, 26)]
    bars.append({
        "date": "2026-01-26",
        "open": 148,
        "high": 150,
        "low": 147,
        "close": 149,
        "prev_close": 140,
        "volume": 2000,
        "delivery_pct": 50,
    })
    quality = {"eps_qoq": 35, "eps_yoy": 40, "sales_yoy": 35, "market_cap_cr": 1000}

    assert ed.earnings_power(bars, quality) is None


def test_ipo_base_applies_four_percent_stop_cap():
    bars = [_bar(1, 100, high=110, low=95), _bar(2, 105, high=108, low=101), _bar(3, 106, high=107, low=103)]
    listing = {"is_ipo": True, "listing_status": "known", "days_since_listing": 3}

    result = ed.ipo_base(bars, listing)

    assert result is not None
    assert result["setup"] == "ipo_base"
    assert result["stop"] == 103


def _trail_bars(last_close):
    bars = [_bar(i, 100 + i * 0.1, high=101 + i * 0.1, low=99 + i * 0.1) for i in range(1, 60)]
    bars[-1] = {**bars[-1], "open": last_close - 1, "high": last_close + 1, "low": last_close - 2, "close": last_close}
    return bars


def test_trail_plan_phases_by_open_r():
    trend = ed.trail_plan(_trail_bars(115), entry=100, stop=90, setup_family="base/pattern")
    assert trend["phase"] == "TREND"
    assert trend["trail_stop"] >= 100

    extension = ed.trail_plan(_trail_bars(125), entry=100, stop=90, setup_family="base/pattern")
    assert extension["phase"] == "EXTENSION"

    initiation = ed.trail_plan(_trail_bars(102), entry=100, stop=90, setup_family="base/pattern")
    assert initiation["phase"] == "INITIATION"


def test_two_strike_requires_two_rules():
    bars = [_bar(i, 100, high=101, low=99, volume=1000) for i in range(1, 31)]
    bars[-1] = {**bars[-1], "open": 95, "high": 96, "low": 88, "close": 90, "volume": 1000}
    result = ed.two_strike(bars)
    assert result["exit_now"] is True
    assert {"below-21EMA", "fresh-10-day-low"} <= set(result["fired"])

    one_rule = [_bar(i, 100, high=101, low=90, volume=1000) for i in range(1, 31)]
    one_rule[-1] = {**one_rule[-1], "open": 98, "high": 100, "low": 97, "close": 98, "volume": 1000}
    assert ed.two_strike(one_rule)["exit_now"] is False


def test_two_strike_hard_stop_breach_exits_alone():
    # Only the stop-breach rule fires (price is otherwise unremarkable vs the
    # other four soft weakness rules) -- a single hard-stop breach must still
    # force exit_now, since the stop itself has already been violated.
    bars = [_bar(i, 100, high=101, low=99, volume=1000) for i in range(1, 31)]
    bars[-1] = {**bars[-1], "open": 99.5, "high": 100, "low": 98.5, "close": 99, "volume": 1000}
    result = ed.two_strike(bars, stop=100)
    assert result["exit_now"] is True
    assert "stop-breached" in result["fired"]

    # Same bars, stop below close: no breach and (as before) fewer than two
    # soft rules fired, so no exit.
    result_no_breach = ed.two_strike(bars, stop=90)
    assert "stop-breached" not in result_no_breach["fired"]


def _avwap_bars(n=60, swing_idx=30, earnings_idx=None):
    bars = []
    for i in range(n):
        bars.append({
            "date": f"d{i}",
            "open": 100,
            "high": 101,
            "low": 100,
            "close": 100,
            "prev_close": 100,
            "volume": 1000,
        })
    bars[swing_idx].update({"low": 90, "close": 95})
    if earnings_idx is not None:
        bars[earnings_idx].update({
            "open": 106,
            "high": 108,
            "low": 105,
            "close": 107,
            "prev_close": 100,
            "volume": 2300,
        })
    return bars


def test_avwap_auto_anchor_picks_swing_low():
    bars = _avwap_bars(swing_idx=30)
    result = ed.avwap_auto_anchor(bars)
    assert result["anchor_type"] == "swing-low"
    assert result["anchor_date"] == "d30"


def test_avwap_auto_anchor_replaces_aged_lower_significance_anchor():
    bars = _avwap_bars(swing_idx=30, earnings_idx=55)
    prev = {"anchor_date": "d30", "anchor_type": "swing-low", "significance": 1}
    result = ed.avwap_auto_anchor(bars, prev_anchor=prev)
    assert result["anchor_type"] == "earnings-gap"
    assert "supersedes" in result["reason"]


def test_avwap_auto_anchor_keeps_recent_prior_anchor():
    bars = _avwap_bars(swing_idx=49, earnings_idx=55)
    prev = {"anchor_date": "d49", "anchor_type": "swing-low", "significance": 1}
    result = ed.avwap_auto_anchor(bars, prev_anchor=prev)
    assert result["kept"] is True
    assert result["anchor_date"] == "d49"


def test_avwap_auto_anchor_idempotent_same_data():
    bars = _avwap_bars(swing_idx=30, earnings_idx=55)
    first = ed.avwap_auto_anchor(bars)
    second = ed.avwap_auto_anchor(bars)
    assert first["anchor_date"] == second["anchor_date"]
    assert first["anchor_type"] == second["anchor_type"]


# --- M7: strong_start_ready ------------------------------------------------
def test_strong_start_ready_fires_on_tight_day_in_uptrend():
    # rising closes (uptrend) with wide daily ranges, then a very tight last bar
    bars = [_bar(i, 100 + i, high=100 + i + 3, low=100 + i - 3) for i in range(1, 61)]
    bars[-1] = {**bars[-1], "high": bars[-1]["close"] + 0.2, "low": bars[-1]["close"] - 0.2}
    res = ed.strong_start_ready(bars)
    assert res["ready"] is True
    assert res["setup"] == "strong_start_ready"
    assert res["branch"] is None
    assert res["resolve_at_open"]  # the 9:15-open checklist is populated
    assert res["evidence"]["prev_day_high"] is not None  # tomorrow's entry ref
    assert "cross above today's high" in res["entry_rule"].lower()


def test_strong_start_ready_not_ready_in_downtrend():
    # falling closes -> no uptrend context -> not a strong-start continuation
    bars = [_bar(i, 200 - i, high=200 - i + 3, low=200 - i - 3) for i in range(1, 61)]
    bars[-1] = {**bars[-1], "high": bars[-1]["close"] + 0.2, "low": bars[-1]["close"] - 0.2}
    res = ed.strong_start_ready(bars)
    assert res["ready"] is False
    assert res["evidence"]["uptrend"] is False


def test_strong_start_ready_not_ready_when_last_day_wide():
    # uptrend but the last day is the WIDEST of its window -> not tight
    bars = [_bar(i, 100 + i, high=100 + i + 0.3, low=100 + i - 0.3) for i in range(1, 61)]
    bars[-1] = {**bars[-1], "high": bars[-1]["close"] + 8, "low": bars[-1]["close"] - 8}
    res = ed.strong_start_ready(bars)
    assert res["ready"] is False


# --- M7: d2_ready ----------------------------------------------------------
def _d2_base():
    # 29 flat, tight days forming the pre-move consolidation
    return [_bar(i, 100, high=101, low=99) for i in range(1, 30)]


def test_d2_ready_strong_close_branch_and_circuit_flag():
    bars = _d2_base()
    # Day-1 burst: +24% (a 20% circuit), closing near the high
    bars.append(_bar(30, 124, open_=101, high=125, low=100))
    bars[-1] = {**bars[-1], "prev_close": 100}
    res = ed.d2_ready(bars)
    assert res["ready"] is True
    assert res["setup"] == "d2_ready"
    assert res["branch"] == "strong_close_gap_up"
    assert res["evidence"]["is_20pct_circuit"] is True
    assert round(res["evidence"]["day1_change_pct"]) == 24
    assert any("undetermined" in c.lower() for c in res["resolve_at_open"])  # branch (c) pending open


def test_d2_ready_wick_play_branch():
    bars = _d2_base()
    # Day-1 +10% but a weak/wick close (closes low in a wide range)
    bars.append(_bar(30, 110, open_=101, high=118, low=108))
    bars[-1] = {**bars[-1], "prev_close": 100}
    res = ed.d2_ready(bars)
    assert res["ready"] is True
    assert res["branch"] == "wick_play"


def test_d2_ready_not_ready_on_small_day():
    bars = [_bar(i, 100, high=101, low=99) for i in range(1, 31)]  # last day ~+1%
    res = ed.d2_ready(bars)
    assert res["ready"] is False
    assert res["branch"] is None


# --- long_tail_candle (STOCKGEEKS_NUANCES.md:66-71) ----------------------

def test_long_tail_candle_flags_wick_over_1p5x_body():
    # body = |close-open| = 1, lower wick = open(101)-low(90) = 11 -> 11x body
    bars = [_bar(i, 100, high=101, low=99) for i in range(1, 10)]
    bars.append({"date": "2026-01-10", "open": 101, "high": 102, "low": 90, "close": 102,
                 "prev_close": 100, "volume": 1000, "delivery_pct": 50})

    result = ed.long_tail_candle(bars)

    assert result is not None
    assert result["setup"] == "long_tail"
    assert result["tail_body_ratio"] > 1.5
    assert result["entry"] == round(90 * 1.01, 2)


def test_long_tail_candle_rejects_short_wick():
    # body = 5, lower wick = 100-97 = 3 -> 0.6x body, below 1.5x threshold
    bars = [_bar(i, 100, high=101, low=99) for i in range(1, 10)]
    bars.append({"date": "2026-01-10", "open": 100, "high": 106, "low": 97, "close": 105,
                 "prev_close": 100, "volume": 1000, "delivery_pct": 50})

    assert ed.long_tail_candle(bars) is None


def test_long_tail_candle_rejects_no_lower_wick():
    # close/open both sit AT the low -- no rejection wick to measure
    bars = [_bar(i, 100, high=101, low=99) for i in range(1, 10)]
    bars.append({"date": "2026-01-10", "open": 95, "high": 102, "low": 95, "close": 101,
                 "prev_close": 100, "volume": 1000, "delivery_pct": 50})

    assert ed.long_tail_candle(bars) is None


# --- inside_bar_count / ipo_inside_bar (STOCKGEEKS_NUANCES.md:52-57, 195-200) --

def test_inside_bar_count_counts_consecutive_trailing_inside_bars():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=105, low=95),   # inside bar 1 of bar 1
        _bar(3, 100, high=103, low=97),   # inside bar 2 of bar 2
    ]
    assert ed.inside_bar_count(bars) == 2


def test_inside_bar_count_stops_at_first_non_inside_bar():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=105, low=95),   # inside
        _bar(3, 100, high=112, low=88),   # NOT inside (breaks out both sides)
    ]
    assert ed.inside_bar_count(bars) == 0


def test_ipo_inside_bar_flags_first_inside_bar():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=105, low=95),  # first inside bar
    ]
    listing = {"is_ipo": True, "listing_status": "known", "days_since_listing": 5}

    result = ed.ipo_inside_bar(bars, listing)

    assert result is not None
    assert result["setup"] == "ipo_inside_bar"
    assert result["inside_bar_count"] == 1
    assert result["label"] == "IPO First Inside Bar"


def test_ipo_inside_bar_flags_double_inside_bar():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=105, low=95),   # inside bar 1
        _bar(3, 100, high=103, low=97),   # inside bar 2 -> double
    ]
    listing = {"is_ipo": True, "listing_status": "known", "days_since_listing": 8}

    result = ed.ipo_inside_bar(bars, listing)

    assert result is not None
    assert result["inside_bar_count"] == 2
    assert result["label"] == "IPO Double Inside Bar"


def test_ipo_inside_bar_none_when_not_recent_listing():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=105, low=95),
    ]
    listing = {"is_ipo": False, "listing_status": "known", "days_since_listing": 400}

    assert ed.ipo_inside_bar(bars, listing) is None


def test_ipo_inside_bar_none_when_no_inside_bar():
    bars = [
        _bar(1, 100, high=110, low=90),
        _bar(2, 100, high=115, low=85),  # not inside -- wider range
    ]
    listing = {"is_ipo": True, "listing_status": "known", "days_since_listing": 3}

    assert ed.ipo_inside_bar(bars, listing) is None
