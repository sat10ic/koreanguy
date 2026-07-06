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
