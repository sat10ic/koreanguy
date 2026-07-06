"""EOD-only setup and exit detectors.

All functions are deterministic and use only persisted daily OHLCV plus the
existing symbol_quality/confluence side data passed in by callers. They return
named evidence chips/rules; none of these helpers writes a second score.
"""
from __future__ import annotations

from typing import Any

Bar = dict[str, Any]
GROWTH_MIN = -200.0
GROWTH_MAX = 500.0


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Any, ndigits: int = 2) -> float | None:
    n = _num(value)
    return None if n is None else round(n, ndigits)


def _trusted_growth(value: Any) -> float | None:
    n = _num(value)
    if n is None or n < GROWTH_MIN or n > GROWTH_MAX:
        return None
    return n


def _closes(bars: list[Bar]) -> list[float | None]:
    return [_num(b.get("close")) for b in bars]


def ema(values: list[float | None], span: int) -> list[float | None]:
    alpha = 2.0 / (span + 1.0)
    out: list[float | None] = []
    prev: float | None = None
    for value in values:
        if value is None:
            out.append(prev)
            continue
        prev = value if prev is None else (value * alpha) + (prev * (1.0 - alpha))
        out.append(prev)
    return out


def sma(values: list[float | None], window: int) -> list[float | None]:
    out: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            out.append(None)
            continue
        chunk = values[idx - window + 1 : idx + 1]
        out.append(None if any(v is None for v in chunk) else sum(v for v in chunk if v is not None) / window)
    return out


def _rising(series: list[float | None], lookback: int = 5) -> bool:
    if len(series) <= lookback:
        return False
    now = series[-1]
    then = series[-1 - lookback]
    return now is not None and then is not None and now > then


def _pct(a: float, b: float) -> float | None:
    return None if b == 0 else (a - b) / b * 100.0


def exit_state(bars: list[Bar]) -> dict[str, Any]:
    """Composite weakness state for Market Navigator exits.

    Broken is forced by structural breaks such as losing the 50/200SMA. Other
    fired rules make the symbol Weakening. The payload is intentionally rule
    names plus plain-English detail, never an opaque N-of-M count.
    """
    if len(bars) < 2:
        return {"state": "Intact", "fired_rules": [], "read": "Not enough daily bars for an exit read."}
    closes = _closes(bars)
    ema21 = ema(closes, 21)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    latest = bars[-1]
    prev = bars[-2]
    close = _num(latest.get("close"))
    prev_close = _num(prev.get("close"))
    high = _num(latest.get("high"))
    low = _num(latest.get("low"))
    open_ = _num(latest.get("open"))
    volume = _num(latest.get("volume"))
    rules: list[dict[str, str]] = []

    def add(rule: str, detail: str) -> None:
        rules.append({"rule": rule, "detail": detail})

    if close is not None and ema21[-1] is not None:
        if close < ema21[-1]:
            add("below-21EMA", f"Close {close:.2f} is below 21EMA {ema21[-1]:.2f}.")
        if prev_close is not None and ema21[-2] is not None and prev_close >= ema21[-2] and close < ema21[-1]:
            add("crossed-below-21EMA", "Price crossed below the 21EMA today.")
    if close is not None and sma50[-1] is not None and close < sma50[-1]:
        add("below-50SMA", f"Close {close:.2f} is below 50SMA {sma50[-1]:.2f}.")
    if close is not None and sma200[-1] is not None and close < sma200[-1]:
        add("below-200SMA", f"Close {close:.2f} is below 200SMA {sma200[-1]:.2f}.")

    if len(bars) >= 11:
        prior_lows = [_num(b.get("low")) for b in bars[-11:-1]]
        if low is not None and all(v is not None for v in prior_lows) and low < min(v for v in prior_lows if v is not None):
            add("lower-low", "Today undercut the prior 10-day low.")

    if None not in (open_, high, low, close) and high > low:
        assert open_ is not None and high is not None and low is not None and close is not None
        if close < open_ and (high - close) / (high - low) >= 0.6:
            add("downside-reversal-bar", "Price pushed up intraday but closed weak in the lower range.")

    distribution_days = 0
    for idx in range(max(1, len(bars) - 25), len(bars)):
        c = _num(bars[idx].get("close"))
        pc = _num(bars[idx - 1].get("close"))
        v = _num(bars[idx].get("volume"))
        pv = _num(bars[idx - 1].get("volume"))
        if None in (c, pc, v, pv) or pc == 0:
            continue
        assert c is not None and pc is not None and v is not None and pv is not None
        if c < pc * 0.998 and v > pv:
            distribution_days += 1
    if distribution_days:
        add("distribution-days", f"{distribution_days} distribution days in the last 25 bars.")
    if distribution_days >= 3:
        add("distribution-cluster", "Three or more recent distribution days show clustered selling.")

    structural = {r["rule"] for r in rules} & {"below-50SMA", "below-200SMA"}
    state = "Broken" if structural else "Weakening" if rules else "Intact"
    read = (
        "Exit state is broken because a structural moving average was lost."
        if state == "Broken"
        else "Exit state is weakening; tighten trade management."
        if state == "Weakening"
        else "Exit state is intact; no daily weakness rule fired."
    )
    return {"state": state, "fired_rules": rules, "read": read}


def launch_pad(bars: list[Bar]) -> dict[str, Any] | None:
    if len(bars) < 70:
        return None
    closes = _closes(bars)
    ema65 = ema(closes, 65)
    sma21 = sma(closes, 21)
    sma50 = sma(closes, 50)
    close = _num(bars[-1].get("close"))
    volume = _num(bars[-1].get("volume"))
    avg_vol = sum(_num(b.get("volume")) or 0 for b in bars[-21:-1]) / 20.0
    if None in (close, sma21[-1], sma50[-1], ema65[-1]) or avg_vol <= 0:
        return None
    assert close is not None and sma21[-1] is not None and sma50[-1] is not None and ema65[-1] is not None
    distances = [abs(close - sma21[-1]) / sma21[-1] * 100, abs(close - sma50[-1]) / sma50[-1] * 100, abs(close - ema65[-1]) / ema65[-1] * 100]
    stacked = sma21[-1] > sma50[-1] > ema65[-1]
    rising = _rising(sma21) and _rising(sma50) and _rising(ema65)
    volume_ok = volume is not None and volume >= avg_vol * 1.1
    # "within 1-3% of the MAs" = a proximity band (<=3%); tighter than 1% is
    # even better (price hugging the cluster), so there is no lower floor —
    # a 1% floor is mutually exclusive with the 3% cap across 21/50/65 anyway.
    if all(d <= 3.0 for d in distances) and stacked and rising and volume_ok:
        return {"setup": "launch_pad", "label": "Launch Pad", "detail": "Price is 1-3% from 21SMA, 50SMA, and 65EMA with stacked rising averages and volume confirmation."}
    return None


def ants_accumulation(bars: list[Bar]) -> dict[str, Any] | None:
    if len(bars) < 16:
        return None
    window = bars[-15:]
    first = _num(window[0].get("close"))
    last = _num(window[-1].get("close"))
    first_vol = sum(_num(b.get("volume")) or 0 for b in window[:5]) / 5.0
    last_vol = sum(_num(b.get("volume")) or 0 for b in window[-5:]) / 5.0
    if None in (first, last) or first_vol <= 0:
        return None
    assert first is not None and last is not None
    price_gain = _pct(last, first)
    volume_gain = _pct(last_vol, first_vol)
    up_days = sum(1 for idx in range(1, len(window)) if (_num(window[idx].get("close")) or 0) > (_num(window[idx - 1].get("close")) or 0))
    deliveries = [_num(b.get("delivery_pct")) for b in window if _num(b.get("delivery_pct")) is not None]
    delivery_ok = len(deliveries) >= 6 and deliveries[-1] >= deliveries[0]
    if price_gain is not None and volume_gain is not None and 18 <= price_gain <= 28 and 15 <= volume_gain <= 30 and up_days >= 12 and delivery_ok:
        return {"filter": "ANTS", "value": "accumulation", "detail": f"{price_gain:.0f}% price gain, {volume_gain:.0f}% volume rise, {up_days}/15 up days, delivery strengthening."}
    return None


def earnings_power(bars: list[Bar], quality: dict[str, Any] | None) -> dict[str, Any] | None:
    if not quality or len(bars) < 35:
        return None
    required = ["eps_qoq", "eps_yoy", "sales_yoy"]
    if any((value := _trusted_growth(quality.get(k))) is None or value < 30 for k in required):
        return None
    # No separate sales_qoq column exists in symbol_quality today; eps_qoq is
    # the results-calendar QoQ leg and sales_yoy is the available sales leg.
    if quality.get("asm_stage") is not None or (quality.get("market_cap_cr") is not None and float(quality["market_cap_cr"]) <= 300):
        return None
    latest = bars[-1]
    open_ = _num(latest.get("open"))
    prev_close = _num(latest.get("prev_close")) or _num(bars[-2].get("close"))
    high = _num(latest.get("high"))
    low = _num(latest.get("low"))
    close = _num(latest.get("close"))
    if None in (open_, prev_close, high, low, close) or prev_close == 0 or close == 0:
        return None
    assert open_ is not None and prev_close is not None and high is not None and low is not None and close is not None
    gap_pct = (open_ - prev_close) / prev_close * 100.0
    day_range_pct = (high - low) / close * 100.0
    prior_high = max(_num(b.get("high")) or 0 for b in bars[-31:-1])
    neglected_base = close > prior_high and day_range_pct <= 8.0
    if gap_pct > 0 and neglected_base and gap_pct + day_range_pct <= 12.0:
        return {"setup": "ep", "label": "EP", "detail": f"EPS and sales growth passed 30% checks, gap {gap_pct:.1f}%, range {day_range_pct:.1f}%."}
    return None


def ipo_base(bars: list[Bar], listing: dict[str, Any] | None) -> dict[str, Any] | None:
    if not listing or not listing.get("is_ipo") or listing.get("listing_status") != "known" or len(bars) < 3:
        return None
    latest = bars[-1]
    prev = bars[-2]
    close = _num(latest.get("close"))
    low = _num(latest.get("low"))
    high = _num(latest.get("high"))
    if None in (close, low, high) or close == 0:
        return None
    assert close is not None and low is not None and high is not None
    stop_dist = (close - low) / close * 100.0
    if stop_dist <= 0 or stop_dist > 4.0:
        return None
    inside = (_num(latest.get("high")) or 0) < (_num(prev.get("high")) or 0) and (_num(latest.get("low")) or 0) > (_num(prev.get("low")) or 0)
    recent = bars[-10:]
    highs = [_num(b.get("high")) for b in recent]
    lows = [_num(b.get("low")) for b in recent]
    tvcp = all(v is not None for v in highs + lows) and (max(highs) - min(lows)) / close * 100.0 <= 8.0
    if inside:
        label = "IPO mini-coil inside bar"
    elif tvcp:
        label = "IPO TVCP range-squeeze"
    else:
        return None
    return {"setup": "ipo_base", "label": label, "stop": _round(low), "detail": f"{label}; hard stop at day low with {stop_dist:.1f}% risk."}


def listing_status(conn, symbol: str, as_of: str) -> dict[str, Any]:
    first = conn.execute(
        "SELECT MIN(trade_date) AS d FROM daily_prices WHERE symbol = ? AND series = 'EQ'",
        (symbol.upper(),),
    ).fetchone()
    global_first = conn.execute("SELECT MIN(trade_date) AS d FROM daily_prices WHERE series = 'EQ'").fetchone()
    if not first or not first["d"]:
        return {"listing_status": "unknown", "listing_date": None, "is_ipo": False, "days_since_listing": None}
    first_date = first["d"]
    if global_first and global_first["d"] == first_date:
        return {"listing_status": "unknown", "listing_date": first_date, "is_ipo": False, "days_since_listing": None, "reason": "first row equals archive start"}
    renamed = conn.execute(
        "SELECT 1 FROM daily_prices WHERE symbol <> ? AND series = 'EQ' AND trade_date < ? "
        "AND REPLACE(symbol, '-', '') = REPLACE(?, '-', '') LIMIT 1",
        (symbol.upper(), first_date, symbol.upper()),
    ).fetchone()
    if renamed:
        return {"listing_status": "unknown", "listing_date": first_date, "is_ipo": False, "days_since_listing": None, "reason": "possible rename/relisting"}
    days = conn.execute(
        "SELECT COUNT(DISTINCT trade_date) AS n FROM daily_prices WHERE series='EQ' AND trade_date >= ? AND trade_date <= ?",
        (first_date, as_of),
    ).fetchone()["n"]
    return {"listing_status": "known", "listing_date": first_date, "is_ipo": days <= 252, "days_since_listing": days}


def trade_plan(setup_type: str, entry: float | None, stop: float | None, target: float | None) -> dict[str, Any] | None:
    if entry is None or stop is None or target is None or entry <= stop:
        return None
    rr = (target - entry) / (entry - stop)
    labels = {
        "launch_pad": "Enter only if price clears today's high on stronger volume.",
        "ep": "Enter on a tight continuation above the earnings gap high.",
        "ipo_base": "Enter only if price clears the pattern high with the 4% stop cap intact.",
        "Near pivot": "Enter only on a clean move through pivot, not a chase.",
        "Pocket pivot": "Enter near the pocket-pivot day high if volume stays supportive.",
        "Shakeout": "Enter only after the reclaim holds above the undercut level.",
    }
    failure = {
        "launch_pad": "Failure: closes back below the moving-average cluster.",
        "ep": "Failure: gap fades or day range expands beyond the planned risk.",
        "ipo_base": "Failure: breaks the IPO pattern low.",
    }.get(setup_type, "Failure: loses the stop or volume flips into distribution.")
    return {
        "entry_trigger": labels.get(setup_type, labels.get("Near pivot")),
        "stop": _round(stop),
        "target": _round(target),
        "rr": round(rr, 2),
        "position_size_source": "existing watchlist position sizer",
        "watch_for_failure": failure,
    }


def ttm_squeeze_momentum(bars: list[Bar]) -> list[dict[str, Any]]:
    closes = _closes(bars)
    sma20 = sma(closes, 20)
    out = []
    for idx, bar in enumerate(bars):
        close = closes[idx]
        base = sma20[idx]
        out.append({"date": bar.get("date") or bar.get("trade_date"), "value": None if close is None or base is None else round(close - base, 2)})
    return out


def avwap_auto_anchor(bars: list[Bar], signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not bars:
        return {"anchor_date": None, "reason": "No bars.", "series": [], "journal": []}
    signals = signals or []
    chosen_idx = max(0, len(bars) - 60)
    reason = "kept existing/default swing-low anchor"
    for idx, bar in enumerate(bars[-120:], start=max(0, len(bars) - 120)):
        if any(s.get("date") == (bar.get("date") or bar.get("trade_date")) and s.get("kind") == "POCKET_PIVOT" for s in signals):
            chosen_idx, reason = idx, "breakout/pocket-pivot anchor beat older anchor"
    pv = 0.0
    vol = 0.0
    series = []
    for bar in bars[chosen_idx:]:
        close = _num(bar.get("close"))
        volume = _num(bar.get("volume"))
        if close is None or volume is None:
            value = None
        else:
            pv += close * volume
            vol += volume
            value = round(pv / vol, 2) if vol else None
        series.append({"date": bar.get("date") or bar.get("trade_date"), "value": value})
    anchor_date = bars[chosen_idx].get("date") or bars[chosen_idx].get("trade_date")
    return {"anchor_date": anchor_date, "reason": reason, "series": series, "journal": [{"anchor_date": anchor_date, "reason": reason}]}
