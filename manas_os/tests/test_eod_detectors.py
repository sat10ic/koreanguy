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


def test_ipo_base_applies_four_percent_stop_cap():
    bars = [_bar(1, 100, high=110, low=95), _bar(2, 105, high=108, low=101), _bar(3, 106, high=107, low=103)]
    listing = {"is_ipo": True, "listing_status": "known", "days_since_listing": 3}

    result = ed.ipo_base(bars, listing)

    assert result is not None
    assert result["setup"] == "ipo_base"
    assert result["stop"] == 103
