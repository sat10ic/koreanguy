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


def _atr(bars: list[Bar], window: int = 20) -> float | None:
    trs: list[float] = []
    for i, bar in enumerate(bars):
        high, low = _num(bar.get("high")), _num(bar.get("low"))
        prev_close = _num(bar.get("prev_close"))
        if prev_close is None and i > 0:
            prev_close = _num(bars[i - 1].get("close"))
        if high is None or low is None or prev_close is None:
            continue
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if len(trs) < window:
        return None
    return sum(trs[-window:]) / window


def trail_plan(bars: list[Bar], entry: float, stop: float, setup_family: str) -> dict[str, Any]:
    closes = _closes(bars)
    close = closes[-1] if closes else None
    risk = entry - stop
    if close is None or risk <= 0:
        return {"phase": "INITIATION", "r": None, "trail_stop": stop, "action": "HOLD — structure stop; wobble is normal", "why": ["missing close or invalid risk"]}
    r = (close - entry) / risk
    ema10 = ema(closes, 10)[-1]
    ema21 = ema(closes, 21)[-1]
    atr20 = _atr(bars, 20)
    why = [f"close {close:.2f}", f"entry {entry:.2f}", f"stop {stop:.2f}", f"open R {r:.2f}"]
    if r < 1.0:
        return {"phase": "INITIATION", "r": round(r, 2), "trail_stop": _round(stop), "action": "HOLD — structure stop; wobble is normal", "why": why}
    if r < 2.0:
        chosen_ema = ema10 if setup_family == "catalyst" else ema21
        ema_name = "EMA10" if setup_family == "catalyst" else "EMA21"
        trail = max(entry, chosen_ema if chosen_ema is not None else entry)
        why.append(f"{ema_name} {chosen_ema:.2f}" if chosen_ema is not None else f"{ema_name} unavailable")
        return {"phase": "TREND", "r": round(r, 2), "trail_stop": _round(trail), "action": f"MOVE STOP to breakeven; BOOK 1/3; trail {ema_name}", "why": why}
    two_bar_lows = [_num(b.get("low")) for b in bars[-2:]]
    two_bar_lows = [v for v in two_bar_lows if v is not None]
    two_bar_low = min(two_bar_lows) if two_bar_lows else stop
    trail = max(stop, two_bar_low)
    if ema21 is not None:
        why.append(f"EMA21 {ema21:.2f}")
    if ema10 is not None:
        why.append(f"EMA10 {ema10:.2f}")
    if atr20 is not None:
        why.append(f"ATR20 {atr20:.2f}")
    why.append(f"2-bar low {two_bar_low:.2f}")
    return {"phase": "EXTENSION", "r": round(r, 2), "trail_stop": _round(trail), "action": "BOOK 25-33% into strength; tighten to 2-bar low", "why": why}


def two_strike(bars: list[Bar], stop: float | None = None) -> dict[str, Any]:
    fired: list[str] = []
    if len(bars) < 2:
        return {"fired": fired, "exit_now": False}
    closes = _closes(bars)
    # Hard-stop breach is checked FIRST and independently of the softer
    # two-strike weakness rules below: if the live close is below the stop
    # the position's premise is already invalidated and it exits today,
    # regardless of how many of the other four weakness signals also fired.
    if stop is not None:
        last_close = closes[-1] if closes else None
        if last_close is not None and last_close < stop:
            fired.append("stop-breached")
    ema21 = ema(closes, 21)
    for idx in range(max(0, len(bars) - 5), len(bars)):
        close = closes[idx]
        if close is not None and ema21[idx] is not None and close < ema21[idx]:
            fired.append("below-21EMA")
            break
    for idx in range(max(0, len(bars) - 5), len(bars)):
        bar = bars[idx]
        open_, high, low, close = (_num(bar.get(k)) for k in ("open", "high", "low", "close"))
        volume = _num(bar.get("volume"))
        prior = [_num(b.get("volume")) for b in bars[max(0, idx - 20):idx]]
        prior = [v for v in prior if v is not None]
        avg_vol = sum(prior) / len(prior) if prior else None
        if None not in (open_, high, low, close, volume, avg_vol) and high > low:
            assert open_ is not None and high is not None and low is not None and close is not None and volume is not None and avg_vol is not None
            if close < open_ and (high - close) / (high - low) >= 0.6 and volume > 1.3 * avg_vol:
                fired.append("downside-reversal-bar")
                break
    dist = 0
    for idx in range(max(1, len(bars) - 5), len(bars)):
        c = _num(bars[idx].get("close"))
        pc = _num(bars[idx - 1].get("close"))
        v = _num(bars[idx].get("volume"))
        pv = _num(bars[idx - 1].get("volume"))
        if None not in (c, pc, v, pv) and c < pc * 0.998 and v > pv:
            dist += 1
    if dist >= 2:
        fired.append("distribution-days")
    if len(bars) >= 11:
        last_low = _num(bars[-1].get("low"))
        prior_lows = [_num(b.get("low")) for b in bars[-11:-1]]
        prior_lows = [v for v in prior_lows if v is not None]
        if last_low is not None and prior_lows and last_low < min(prior_lows):
            fired.append("fresh-10-day-low")
    latest_open = _num(bars[-1].get("open"))
    prev_low = _num(bars[-2].get("low"))
    if latest_open is not None and prev_low is not None and latest_open < prev_low:
        fired.append("gap-down-open")
    exit_now = "stop-breached" in fired or len(fired) >= 2
    return {"fired": fired, "exit_now": exit_now}


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
    if not quality or len(bars) < 26:
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
    # 'Neglected' = the stock was QUIET BEFORE the gap (base/consolidation), not
    # already running. Test the 25 bars BEFORE the gap day:
    pre = bars[-26:-1]
    pre_closes = [c for c in (_num(b.get("close")) for b in pre) if c]
    pre_highs = [h for h in (_num(b.get("high")) for b in pre) if h]
    pre_lows = [l for l in (_num(b.get("low")) for b in pre) if l]
    if len(pre_closes) < 20:
        return None
    band_pct = (max(pre_highs) - min(pre_lows)) / pre_closes[-1] * 100.0
    drift_pct = abs(pre_closes[-1] - pre_closes[0]) / pre_closes[0] * 100.0
    neglected_base = band_pct <= 25.0 and drift_pct <= 10.0
    if gap_pct > 0 and neglected_base and gap_pct + day_range_pct <= 12.0:
        return {"setup": "ep", "label": "EP", "detail": f"EPS and sales growth passed 30% checks, gap {gap_pct:.1f}%, range {day_range_pct:.1f}%, pre-gap band {band_pct:.0f}%, drift {drift_pct:.0f}%."}
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


def inside_bar_count(bars: list[Bar]) -> int:
    """Count of consecutive trailing inside bars ending at the latest bar
    (today's high < prior high AND today's low > prior low, walked
    backwards). Distinguishes "first" (count==1) vs "double" (count>=2)
    inside bar per STOCKGEEKS_NUANCES.md:195-200 CODEABLE note: "pattern
    detector: inside bar count; auto-flag when count=2". Reuses the same
    single-bar inside-bar test already used by ipo_base above."""
    count = 0
    idx = len(bars) - 1
    while idx >= 1:
        cur = bars[idx]
        prev = bars[idx - 1]
        c_high, c_low = _num(cur.get("high")), _num(cur.get("low"))
        p_high, p_low = _num(prev.get("high")), _num(prev.get("low"))
        if None in (c_high, c_low, p_high, p_low):
            break
        if c_high < p_high and c_low > p_low:
            count += 1
            idx -= 1
        else:
            break
    return count


def ipo_inside_bar(bars: list[Bar], listing: dict[str, Any] | None) -> dict[str, Any] | None:
    """STOCKGEEKS_NUANCES.md:52-57 "Fresh-listed IPO that makes first
    inside bar (consolidation after breakout) has highest success rate;
    immediate execution before gap closes" -- QUOTE (line 54): "First
    inside bar is a good trigger if stock is near IPO day level" --
    CODEABLE (line 57): "scan for IPOs + inside bar pattern; auto-rank by
    time-to-IPO and burst size". STOCKGEEKS_NUANCES.md:195-200 "For IPOs,
    when two inside-bar consolidations form in succession, take entry
    immediately -- waiting misses the move" -- CODEABLE (line 200):
    "pattern detector: inside bar count; auto-flag when count=2".

    Eligibility reuses the existing is_ipo/listing_status gate (no new
    recency number invented) -- the corpus's "near IPO day level" and
    "<10 days old" phrasing are not given an exact tolerance anywhere in
    the transcript digest, so no numeric proximity/recency filter is
    added here beyond the existing is_ipo (<=252 trading days) gate;
    count==1 -> "first inside bar", count>=2 -> "double inside bar" is
    the only numeric rule directly quotable from the corpus.
    """
    if not listing or not listing.get("is_ipo") or listing.get("listing_status") != "known" or len(bars) < 2:
        return None
    count = inside_bar_count(bars)
    if count <= 0:
        return None
    label = "IPO First Inside Bar" if count == 1 else "IPO Double Inside Bar"
    days = listing.get("days_since_listing")
    return {
        "setup": "ipo_inside_bar", "label": label, "inside_bar_count": count,
        "days_since_listing": days,
        "detail": f"{label} ({count} consecutive inside bar(s)) on a recent listing (day {days} since listing).",
    }


def long_tail_candle(bars: list[Bar]) -> dict[str, Any] | None:
    """STOCKGEEKS_NUANCES.md:66-71 "Long-tail candle (large wick, small
    body) shows rejection at low; next candle often bounces powerfully if
    wick low holds" -- QUOTE (line 68): "Long tail shows someone bought at
    the low; strong bounce likely" -- TOOL IMPLICATION (line 70): "entry
    gate -- enter 1% above long-tail wick if MBI green" -- CODEABLE (line
    71): "detect tail length > 1.5x body; flag for entry if confirmed next
    candle".

    Only the two numbers directly quotable from the corpus are enforced:
    lower-wick length > 1.5x body, and the entry price = 1% above the
    wick low. The corpus-stated "if MBI green" gate is NOT applied -- this
    repo has no market-breadth-index (MBI) computation anywhere (checked
    engine/*.py and scanner/*.py); building one is out of scope for this
    detector, so it is honestly omitted rather than faked with a
    substitute regime signal.
    """
    if len(bars) < 1:
        return None
    latest = bars[-1]
    o, h, l, c = _num(latest.get("open")), _num(latest.get("high")), _num(latest.get("low")), _num(latest.get("close"))
    if None in (o, h, l, c) or h == l:
        return None
    assert o is not None and l is not None and c is not None
    body = abs(c - o)
    lower_wick = min(o, c) - l
    if body <= 0 or lower_wick <= 0:
        return None
    tail_ratio = lower_wick / body
    if tail_ratio <= 1.5:
        return None
    entry = _round(l * 1.01)
    return {
        "setup": "long_tail", "label": "Long-Tail Candle",
        "tail_body_ratio": _round(tail_ratio), "entry": entry, "stop": _round(l),
        "detail": f"Lower wick {tail_ratio:.1f}x body; entry 1% above wick low at {entry} (MBI-green gate unavailable in repo -- see docstring).",
    }


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
        "launch_pad": "Walk away if it closes back below the moving-average cluster.",
        "ep": "Walk away if the gap fades or the day's range blows past the planned risk.",
        "ipo_base": "Walk away if it breaks the IPO pattern low.",
    }.get(setup_type, "Walk away if it loses the stop or volume flips into distribution.")
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


def avwap_auto_anchor(
    bars: list[Bar],
    signals: list[dict[str, Any]] | None = None,
    prev_anchor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not bars:
        return {"anchor_date": None, "anchor_type": None, "significance": 0, "reason": "No bars.", "series": [], "kept": False}
    start = max(0, len(bars) - 120)
    candidates: dict[str, dict[str, Any]] = {}

    def date_at(idx: int) -> Any:
        return bars[idx].get("date") or bars[idx].get("trade_date")

    def avg_volume(idx: int) -> float | None:
        vols = [_num(b.get("volume")) for b in bars[max(0, idx - 20):idx]]
        vols = [v for v in vols if v is not None]
        return sum(vols) / len(vols) if len(vols) >= 20 else None

    def add_candidate(idx: int, anchor_type: str, base_sig: int, detail: str, avg_vol: float | None) -> None:
        volume = _num(bars[idx].get("volume"))
        significance = base_sig + (1 if avg_vol and volume and volume > 2.0 * avg_vol else 0)
        current = candidates.get(anchor_type)
        if current is None or idx > current["idx"]:
            candidates[anchor_type] = {
                "idx": idx,
                "anchor_date": date_at(idx),
                "anchor_type": anchor_type,
                "significance": significance,
                "detail": detail,
                "avg_vol": avg_vol,
                "volume": volume,
            }

    for idx in range(start, len(bars)):
        avg_vol = avg_volume(idx)
        if idx > 0 and avg_vol:
            open_ = _num(bars[idx].get("open"))
            prev_close = _num(bars[idx].get("prev_close")) or _num(bars[idx - 1].get("close"))
            volume = _num(bars[idx].get("volume"))
            if open_ is not None and prev_close and volume is not None:
                gap_pct = (open_ / prev_close - 1.0) * 100.0
                if gap_pct >= 4.0 and volume > 1.5 * avg_vol:
                    add_candidate(idx, "earnings-gap", 3, f"earnings gap +{gap_pct:.1f}% on {volume / avg_vol:.1f}x vol", avg_vol)
        if idx >= 20 and avg_vol:
            close = _num(bars[idx].get("close"))
            prior_highs = [_num(b.get("high")) for b in bars[idx - 20:idx]]
            prior_highs = [h for h in prior_highs if h is not None]
            volume = _num(bars[idx].get("volume"))
            if close is not None and prior_highs and volume is not None and close > max(prior_highs) and volume > 1.5 * avg_vol:
                add_candidate(idx, "breakout", 2, f"breakout on {volume / avg_vol:.1f}x vol", avg_vol)
        if idx >= 4 and idx + 4 < len(bars):
            neighbor_lows = [_num(b.get("low")) for b in bars[idx - 4:idx + 5]]
            low = _num(bars[idx].get("low"))
            others = [v for i, v in enumerate(neighbor_lows) if v is not None and i != 4]
            # STRICTLY below both sides — on flat data `low == min` made every
            # bar a "swing low" and the newest won (QC 2026-07-06).
            if low is not None and others and low < min(others):
                add_candidate(idx, "swing-low", 1, "confirmed swing low", avg_vol)

    ranked = sorted(candidates.values(), key=lambda c: (c["significance"], c["idx"]), reverse=True)
    chosen = ranked[0] if ranked else {"idx": max(0, len(bars) - 1), "anchor_date": date_at(max(0, len(bars) - 1)), "anchor_type": "fallback", "significance": 0, "detail": "fallback latest bar"}
    kept = False
    reason = f"Anchored: {chosen['detail']}."

    if prev_anchor:
        prev_date = prev_anchor.get("anchor_date")
        prev_idx = next((idx for idx, bar in enumerate(bars) if date_at(idx) == prev_date), None)
        if prev_idx is not None:
            type_sig = {"earnings-gap": 3, "breakout": 2, "swing-low": 1, "fallback": 0}
            prev_sig = int(prev_anchor.get("significance") or type_sig.get(str(prev_anchor.get("anchor_type")), 0))
            age = len(bars) - 1 - prev_idx
            can_replace = (
                chosen["idx"] > prev_idx
                and chosen["significance"] > prev_sig
                and age >= 15
                and abs(chosen["idx"] - prev_idx) > 5
            )
            if can_replace:
                reason = (
                    f"Re-anchored: {chosen['detail']} supersedes "
                    f"{prev_anchor.get('anchor_type', 'prior anchor')} (held {age} bars)"
                )
            else:
                kept = True
                chosen = {
                    "idx": prev_idx,
                    "anchor_date": prev_date,
                    "anchor_type": prev_anchor.get("anchor_type"),
                    "significance": prev_sig,
                    "detail": prev_anchor.get("reason") or "prior anchor",
                }
                reason = f"Kept prior {chosen['anchor_type']} anchor; stability default."

    pv = 0.0
    vol = 0.0
    series = []
    for bar in bars[chosen["idx"]:]:
        close = _num(bar.get("close"))
        volume = _num(bar.get("volume"))
        if close is None or volume is None:
            value = None
        else:
            pv += close * volume
            vol += volume
            value = round(pv / vol, 2) if vol else None
        series.append({"date": bar.get("date") or bar.get("trade_date"), "value": value})
    return {
        "anchor_date": chosen["anchor_date"],
        "anchor_type": chosen["anchor_type"],
        "significance": chosen["significance"],
        "reason": reason,
        "series": series,
        "kept": kept,
    }


# ---------------------------------------------------------------------------
# M7 — EOD "ready" detectors for intraday strong-start / D2 entries.
#
# These are NOT fired signals. Strong-start and D2 are INTRADAY setups whose
# trigger only exists at the 9:15 open (WAVE_M_CONFORMANCE gap #2 ENTRY:
# "EOD only; strong-start/D2 exist ONLY as lens text"). Run tonight on today's
# closed bar + history, they flag names that CLOSED SET UP for such an entry
# tomorrow. The output is a 9:07-9:30 handoff checklist for the human to verify
# at the open -- the tool owns discovery+planning EOD, execution cedes to the
# open ("surface tonight -> execute 9:07-9:30", their own working-professional
# design; WAVE_M_CONFORMANCE "HONEST EOD PROXIES", LENS_EP.md F11).
# Every numeric threshold below carries its corpus cite; none is invented.
# ---------------------------------------------------------------------------

# LENS_STRONG_START.md §1: ">80% of good Strong Start results had an extremely
# tight previous day"; Arora explicitly declines to quantify ("memorize the
# pictures... compare the size of the current day with the previous days").
# Bottom QUARTILE (25th pctile of the name's own trailing-20d ranges) mirrors
# discovery.py TIGHTNESS_BOTTOM_PCTILE / range_contraction_flag's own-history
# bottom-quartile read rather than inventing a fresh number.
STRONG_START_TIGHTNESS_MAX_PCTILE = 25.0
# LENS_STRONG_START.md §1: "avoid it if the gap is already some 5-6%" (RR
# destroyed); INDIA_PLAYBOOK.md §3.3: "don't chase >10% gap". Tomorrow's gap
# -> resolve_at_open, not an EOD gate.
STRONG_START_GAP_CAUTION_PCT = 6.0
STRONG_START_GAP_CHASE_PCT = 10.0
# LENS_STRONG_START.md §1 bonus/tiebreaker: "8-10%+ of average daily volume
# already printed in the first 2-3 minutes". INTRADAY -> resolve_at_open only;
# there is NO EOD RVOL number in the corpus, so day_rvol below is evidence, not
# a gate.
STRONG_START_EARLY_RVOL_PCT = 8.0

# D2 Entry Q2: "Moves of 10%+ are generally preferred... Ideally 20% circuit
# stocks emerging from consolidations". Matches discovery.D2_EXPANSION_PCT /
# D2_CIRCUIT_PCT.
D2_DAY1_EXPANSION_PCT = 10.0
D2_CIRCUIT_PCT = 20.0
# D2 Entry Q4a/Q4b: "closing near its highs" = the strong-close branch. No
# exact fraction is given; top-40% of the day's range (>=0.6) is the "near its
# highs" cut, reusing the same 40% "top" band the discovery layer uses.
D2_STRONG_CLOSE_POS = 0.6
# INDIA_PLAYBOOK.md gate U5 / TRADETM_NUANCES A1: ">12% gap+ORB EP skip".
D2_GAP_ORB_SKIP_PCT = 12.0


def _range_pctile(bars: list[Bar], window: int = 20) -> float | None:
    """Percentile rank (0-100) of the LAST bar's high-low range within the
    trailing `window` sessions. Lower = tighter. Self-contained fallback used
    only when the caller does not pass its own tuned tightness value."""
    if len(bars) < window + 1:
        return None
    ranges: list[float] = []
    for b in bars[-window:]:
        hi, lo = _num(b.get("high")), _num(b.get("low"))
        if hi is None or lo is None:
            return None
        ranges.append(hi - lo)
    last = ranges[-1]
    below = sum(1 for r in ranges if r < last)
    return below / len(ranges) * 100.0


def _close_position(bar: Bar) -> float | None:
    """Where the bar closed within its range: 1.0 = at the high, 0.0 = at low."""
    hi, lo, close = _num(bar.get("high")), _num(bar.get("low")), _num(bar.get("close"))
    if hi is None or lo is None or close is None or hi == lo:
        return None
    return (close - lo) / (hi - lo)


def _day_rvol(bars: list[Bar], window: int = 20) -> float | None:
    """Today's volume / trailing-20d average volume. EOD proxy ONLY -- the
    corpus RVOL rule (8-10% of avg daily volume in the first 2-3 min) is
    intraday and cannot be evaluated tonight (LENS_STRONG_START.md §1)."""
    if len(bars) < window + 1:
        return None
    vols = [v for v in (_num(b.get("volume")) for b in bars[-window - 1:-1]) if v is not None]
    today = _num(bars[-1].get("volume"))
    if not vols or today is None:
        return None
    avg = sum(vols) / len(vols)
    return None if avg == 0 else today / avg


def strong_start_ready(
    bars: list[Bar],
    uptrend: bool | None = None,
    tightness_pctile: float | None = None,
) -> dict[str, Any]:
    """EOD strong-start-READY detector (LENS_STRONG_START.md §1; INDIA_PLAYBOOK
    §3.3). Flags a name that closed today with the two EOD-knowable strong-start
    preconditions -- an extremely TIGHT day (bottom quartile of its own 20d
    range) inside an existing UPTREND -- so that tomorrow's gap-up open would be
    the actual trigger. The power itself (gap direction/size, the 2-3-min hold,
    the cross above today's high, first-2-3-min RVOL) is INTRADAY and lands in
    resolve_at_open -- it cannot be gated tonight.

    `uptrend` / `tightness_pctile` may be supplied by the discovery layer (its
    already-computed, tuned values); when omitted they are derived here so the
    detector is testable standalone.

    Returns {ready, setup, label, branch=None, evidence, resolve_at_open,
    entry_rule, stop_rule}.
    """
    today = bars[-1] if bars else {}
    if tightness_pctile is None:
        tightness_pctile = _range_pctile(bars)
    if uptrend is None:
        closes = _closes(bars)
        s50 = sma(closes, 50)
        c = closes[-1] if closes else None
        uptrend = bool(
            c is not None and s50 and s50[-1] is not None
            and c > s50[-1] and _rising(s50, 10)
        )
    tight = tightness_pctile is not None and tightness_pctile <= STRONG_START_TIGHTNESS_MAX_PCTILE
    ready = bool(len(bars) >= 22 and tight and uptrend)

    high = _num(today.get("high"))   # today's high == tomorrow's "prev-day high"
    close = _num(today.get("close"))
    evidence = {
        "prev_day_tightness_pctile": _round(tightness_pctile),
        "uptrend": bool(uptrend),
        "close_position_in_range": _round(_close_position(today)),
        "day_rvol": _round(_day_rvol(bars)),
        "prev_day_high": _round(high),   # tomorrow's entry reference
        "prev_close": _round(close),
    }
    resolve_at_open = [
        "Gap-up opens at/above today's high, or at minimum clears & HOLDS above today's close -- LENS_STRONG_START.md §1",
        "Low does not breach today's close (minor ~20-30 ticks tolerated; a clear breach invalidates) -- LENS_STRONG_START.md §1",
        "Wait 2-3 min after the open (9:15->9:17/9:18); do NOT buy at 9:15 -- LENS_STRONG_START.md §1",
        "ENTRY TRIGGER: price crosses above today's high AFTER that 2-3-min window -- LENS_STRONG_START.md §1",
        "Pass if the gap is already 5-6%+ at open; don't chase a >10% gap -- LENS_STRONG_START.md §1 / INDIA_PLAYBOOK.md §3.3",
        "Bonus tiebreaker: 8-10%+ of avg daily volume printed in the first 2-3 min (early RVOL) -- LENS_STRONG_START.md §1",
    ]
    return {
        "ready": ready,
        "setup": "strong_start_ready",
        "label": "Strong-Start Ready",
        "branch": None,
        "evidence": evidence,
        "resolve_at_open": resolve_at_open,
        "entry_rule": "Buy the cross above today's high after a 2-3-min wait (NOT the 9:15 gap price) -- LENS_STRONG_START.md §1.",
        "stop_rule": "Day's low / breakout-bar low (reduce toward day-low ~2-2.5% with experience) -- LENS_STRONG_START.md §5, day-low stop TRADETM_NUANCES E2.",
    }


# ---------------------------------------------------------------------------
# STRONG START / RVOL FOCUS LIST -- finallynitin SS RVOL Pine port (© finally-
# nitin; personal-use port only, DO NOT redistribute) + Manas Arora CH3.1
# watchlist-elimination scans. design/STRONG_START_FOCUS_SPEC.md pins these
# numbers verbatim; nothing below is invented or retuned.
# ---------------------------------------------------------------------------

# finallynitin SS RVOL Pine "SS" flag: open > prev_close AND day_low >=
# prev_close * 0.995 -- STRONG_START_FOCUS_SPEC.md line 11. SS_LOWMULT is the
# Pine's own constant.
SS_LOWMULT = 0.995


def strong_start_today(bars: list[Bar]) -> bool:
    """finallynitin SS RVOL Pine "SS" flag computed from EOD OHLC: today's
    open cleared yesterday's close AND today's low never fell meaningfully
    back below it (gap-up-and-hold). Uses the LAST bar's open/low and the
    PRIOR bar's close (falls back to bars[-2]['close'] when prev_close is
    unset on the last bar, same convention as exit_state/two_strike above)."""
    if len(bars) < 2:
        return False
    today = bars[-1]
    prev = bars[-2]
    open_ = _num(today.get("open"))
    low = _num(today.get("low"))
    prev_close = _num(today.get("prev_close"))
    if prev_close is None:
        prev_close = _num(prev.get("close"))
    if open_ is None or low is None or prev_close is None or prev_close == 0:
        return False
    return bool(open_ > prev_close and low >= prev_close * SS_LOWMULT)


def rvol20(bars: list[Bar], window: int = 20) -> float | None:
    """finallynitin SS RVOL Pine "RVOL" = today's volume / SMA(volume, 20)
    over the TRAILING 20 sessions (today excluded) -- STRONG_START_FOCUS_
    SPEC.md line 14. None when there is not a full trailing window of volume
    data or the trailing average is zero (divide-by-zero guard)."""
    if len(bars) < window + 1:
        return None
    trailing = [v for v in (_num(b.get("volume")) for b in bars[-window - 1:-1]) if v is not None]
    today = _num(bars[-1].get("volume"))
    if len(trailing) < window or today is None:
        return None
    avg = sum(trailing) / len(trailing)
    return None if avg == 0 else today / avg


def d2_ready(
    bars: list[Bar],
    pre_move_tightness_pctile: float | None = None,
) -> dict[str, Any]:
    """EOD D2-READY detector (D2 Entry Q2/Q4; TTM-B5b). Today closed as the
    Day-1 burst (>=10% move, or a 20% circuit, out of a tight consolidation --
    "first day of expansion"); tomorrow is the Day-2 entry day. D2 is "three
    setups within a setup, depending on how Day 1 closed AND how Day 2 opens"
    (Q4b). EOD we can read how Day-1 CLOSED and pre-classify the EXPECTED
    branch; the FINAL branch depends on tomorrow's gap (only the 9:15 open
    resolves it), and branch (c) gap-down reversal is always UNDETERMINED
    tonight (needs overnight news + an actual gap-down).

    Branches (D2 Entry Q4b):
      (a) strong_close_gap_up -- "Strong close near highs: Probability of a
          gap-up open is high" -> gap-up continuation technique.
      (b) wick_play -- "Weak close with a wick due to market pressure: look for
          a strong open with a slight gap-up on Day 2" -> pent-up-demand play.
      (c) gap_down_reversal -- "Negative overnight news... look for a gap-down
          reversal" -> UNDETERMINED at EOD (in resolve_at_open).

    `pre_move_tightness_pctile` may be supplied by the discovery layer; derived
    here (from bars excluding today) when omitted.
    """
    base = {
        "ready": False, "setup": "d2_ready", "label": "D2 Ready", "branch": None,
        "evidence": {}, "resolve_at_open": [],
        "entry_rule": "Intraday breakout of the first 5-min opening-range high / day-high (NOT the gap price) -- D2 Entry Q4c.",
        "stop_rule": "Day's / morning low = maximum-pressure anchor, tight ~1.5-2% stop -- TRADETM_NUANCES_SHARDS #13, day-low stop TRADETM_NUANCES E2.",
    }
    if len(bars) < 22:
        return base
    today = bars[-1]
    close = _num(today.get("close"))
    prev_close = _num(today.get("prev_close"))
    if prev_close is None and len(bars) > 1:
        prev_close = _num(bars[-2].get("close"))
    if close is None or not prev_close:
        return base
    day_change = (close - prev_close) / prev_close * 100.0
    is_circuit = day_change >= D2_CIRCUIT_PCT
    big_day1 = day_change >= D2_DAY1_EXPANSION_PCT
    if pre_move_tightness_pctile is None:
        pre_move_tightness_pctile = _range_pctile(bars[:-1])
    from_consolidation = (
        pre_move_tightness_pctile is not None
        and pre_move_tightness_pctile <= STRONG_START_TIGHTNESS_MAX_PCTILE
    )
    ready = bool(big_day1 and from_consolidation)

    close_pos = _close_position(today)
    if close_pos is not None and close_pos >= D2_STRONG_CLOSE_POS:
        branch = "strong_close_gap_up"
        branch_note = "Strong close near highs -> high probability of a gap-up open; handle with gap-up entry technique (D2 Entry Q4b-a)."
    else:
        branch = "wick_play"
        branch_note = "Weak/wick close (dragged by market pressure) -> Wick Play: look for a strong slight-gap-up open on pent-up demand (D2 Entry Q4b-b/Q6)."

    evidence = {
        "day1_change_pct": _round(day_change),
        "is_20pct_circuit": bool(is_circuit),
        "close_position_in_range": _round(close_pos),
        "day_rvol": _round(_day_rvol(bars)),
        "pre_move_tightness_pctile": _round(pre_move_tightness_pctile),
        "day1_high": _round(_num(today.get("high"))),
        "day1_low": _round(_num(today.get("low"))),
    }
    resolve_at_open = [
        f"EOD-expected branch: {branch} -- {branch_note}",
        "Branch (c) GAP-DOWN REVERSAL is undetermined tonight: needs negative overnight news + an actual gap-down open; if it gaps down, play the reversal off the (unbreached) morning low as a tight anchor -- D2 Entry Q4b-c/Q6, TRADETM_NUANCES_SHARDS #13",
        "Final branch depends on tomorrow's gap direction/size -- only the 9:15 open resolves it -- D2 Entry Q4b",
        "Entry via intraday structure: 5-min ORB / opening-range / day-high breakout -- D2 Entry Q4c",
        "Skip if gap-up% + first-5min-ORB% > 12% of prior close (circuit blocks a same-day risk-free trade) -- INDIA_PLAYBOOK.md gate U5 / TRADETM_NUANCES A1",
    ]
    return {
        "ready": ready,
        "setup": "d2_ready",
        "label": "D2 Ready",
        "branch": branch if ready else None,
        "evidence": evidence,
        "resolve_at_open": resolve_at_open,
        "entry_rule": base["entry_rule"],
        "stop_rule": base["stop_rule"],
    }


def resample_daily_to_weekly(daily_bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import datetime
    if not daily_bars:
        return []
    
    weekly_groups = []
    current_key = None
    current_group = []
    
    for bar in daily_bars:
        dt_str = bar.get("date") or bar.get("trade_date")
        if not dt_str:
            continue
        try:
            if isinstance(dt_str, datetime.date):
                dt = dt_str
            else:
                dt = datetime.datetime.strptime(str(dt_str)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        
        iso_year, iso_week, _ = dt.isocalendar()
        key = (iso_year, iso_week)
        
        if key != current_key:
            if current_group:
                weekly_groups.append(current_group)
            current_key = key
            current_group = [bar]
        else:
            current_group.append(bar)
            
    if current_group:
        weekly_groups.append(current_group)
        
    weekly_bars = []
    for group in weekly_groups:
        first_bar = group[0]
        last_bar = group[-1]
        
        high_vals = [_num(b.get("high")) for b in group if b.get("high") is not None]
        low_vals = [_num(b.get("low")) for b in group if b.get("low") is not None]
        vols = [_num(b.get("volume")) for b in group if b.get("volume") is not None]
        deliv_qtys = [_num(b.get("delivery_qty")) for b in group if b.get("delivery_qty") is not None]
        
        open_val = _num(first_bar.get("open"))
        close_val = _num(last_bar.get("close"))
        
        high_val = max(high_vals) if high_vals else _num(last_bar.get("high"))
        low_val = min(low_vals) if low_vals else _num(last_bar.get("low"))
        vol_val = sum(vols) if vols else _num(last_bar.get("volume"))
        deliv_qty_val = sum(deliv_qtys) if deliv_qtys else _num(last_bar.get("delivery_qty"))
        
        deliv_pct_val = None
        if vol_val and deliv_qty_val is not None:
            deliv_pct_val = (deliv_qty_val / vol_val) * 100.0
            
        weekly_bars.append({
            "date": last_bar.get("date") or last_bar.get("trade_date"),
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": vol_val,
            "delivery_qty": deliv_qty_val,
            "delivery_pct": deliv_pct_val
        })
        
    for i in range(1, len(weekly_bars)):
        weekly_bars[i]["prev_close"] = weekly_bars[i - 1]["close"]
        
    return weekly_bars


def detect_weekly_breakout(daily_bars: list[dict[str, Any]]) -> bool:
    weekly_bars = resample_daily_to_weekly(daily_bars)
    if len(weekly_bars) < 21:
        return False
    
    w_last = weekly_bars[-1]
    w_prior = weekly_bars[-21:-1]
    
    prior_highs = [_num(w.get("high")) for w in w_prior if w.get("high") is not None]
    if not prior_highs:
        return False
    pivot = max(prior_highs)
    
    close = _num(w_last.get("close"))
    high = _num(w_last.get("high"))
    low = _num(w_last.get("low"))
    volume = _num(w_last.get("volume"))
    
    if close is None or high is None or low is None or volume is None:
        return False
        
    is_breakout = close > pivot
    
    prior_vols = [_num(w.get("volume")) for w in w_prior if w.get("volume") is not None]
    if not prior_vols:
        return False
    avg_vol = sum(prior_vols) / len(prior_vols)
    volume_confirm = volume >= 1.2 * avg_vol
    
    rng = high - low
    close_in_upper = (close - low) / rng >= 0.7 if rng > 0 else True
    
    return bool(is_breakout and volume_confirm and close_in_upper)

