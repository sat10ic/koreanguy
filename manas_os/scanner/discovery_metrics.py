"""WAVE K K3 — additive discovery metrics for the Stage-1 SENSITIVE BUCKET.

Pure functions over oldest-first OHLCV bar dicts (same shape as
`candidates.load_symbol_bars`: date/open/high/low/close/prev_close/volume/
delivery_qty/delivery_pct). One writer per metric, shadow-only this wave —
nothing here gates scan_candidates. Every threshold is corpus-cited per
`design/knowledge/PLAYBOOK_TO_TOOL_MAP.md` §B; do not invent or retune values
here (retuning is a separate, explicitly-scoped wave).

Reuses `engine/manas_indicators` where it already computes the thing
(purple_dot, persistency) rather than re-deriving.
"""
from __future__ import annotations

from typing import Any

from manas_os.engine import manas_indicators as mi

Bar = dict[str, Any]


def _num(bar: Bar, key: str) -> float | None:
    v = bar.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def adr20(bars: list[Bar]) -> float | None:
    """Average Daily Range over the trailing 20 sessions, % of close.

    Cite: TTM-H-III3 / WK groww2 — "ADR20 in top universe percentile; sort
    scan by ADR desc." Same (high-low)/close*100 formula candidates.py's
    symbol_timing already uses for its 14d display ADR (candidates.py L280-
    284); widened to the spec's 20d window and promoted from display-only to
    a scoreable metric (PLAYBOOK_TO_TOOL_MAP §B row 3).
    """
    window = bars[-20:]
    ranges = []
    for b in window:
        h, l, c = _num(b, "high"), _num(b, "low"), _num(b, "close")
        if h is not None and l is not None and c:
            ranges.append((h - l) / c * 100.0)
    if not ranges:
        return None
    return sum(ranges) / len(ranges)


def purple_dot_count_60d(bars: list[Bar]) -> int:
    """Count of >5% move on >5 lakh volume days over the trailing 60 sessions.

    Cite: WK groww2 / CH3.1 — "dot prints on >5% move (either direction) on
    >5 lakh volume; ZERO dots = skip regardless of setup." Reuses
    engine.manas_indicators.purple_dot (already ported); vol_floor is set to
    the corpus's ">5 lakh" (500,000 shares), not that function's own
    1,000,000-share default.
    """
    window = bars[-60:]
    flags = mi.purple_dot(window, vol_floor=500_000, pct=5)
    return sum(1 for f in flags if f)


def pct_up_from_65d_low(bars: list[Bar]) -> float | None:
    """% up from the trailing 65-session (3-month) low — Arora's buying-force
    "green number", measured off the LOW not off the 52w high.

    Cite: WK groww2 / CH3.1 — "stock up >=30-35% from its 3-month (65-day)
    low. His #1 momentum signal." PLAYBOOK_TO_TOOL_MAP §B row 2 (replaces the
    52w-high anchor as the buying-force test).
    """
    window = bars[-65:]
    lows = [_num(b, "low") for b in window if _num(b, "low") is not None]
    close = _num(bars[-1], "close") if bars else None
    if not lows or close is None:
        return None
    low65 = min(lows)
    if low65 <= 0:
        return None
    return (close - low65) / low65 * 100.0


def _leg_high(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """Highest high of the trailing `leg_lookback` sessions (the current "leg
    high") — ONE shared leg-high identification used by both
    `correction_depth_from_leg_high` and `leg_force_from_65d_low` (K4.1: do
    not re-derive the same concept twice)."""
    window = bars[-leg_lookback:]
    highs = [_num(b, "high") for b in window if _num(b, "high") is not None]
    if not highs:
        return None
    return max(highs)


def correction_depth_from_leg_high(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """% pullback of the latest close from the highest high of the trailing
    `leg_lookback` sessions (the current "leg high").

    Cite: WK groww2 — "pullback <=25-30% from leg high; >30% = avoid. Good
    examples 17/19/26%; bad 45%." Also SG-50%-Fall (reject >40-50% down-base
    reads as a distinct failure, not this metric's job to gate — K3 is
    shadow-only). leg_lookback=60 sessions (~3 months) matches the same
    "recent swing" window used by pct_up_from_65d_low above.
    """
    leg_high = _leg_high(bars, leg_lookback)
    close = _num(bars[-1], "close") if bars else None
    if leg_high is None or leg_high <= 0 or close is None:
        return None
    return (leg_high - close) / leg_high * 100.0


def leg_force_from_65d_low(bars: list[Bar], leg_lookback: int = 60) -> float | None:
    """% the PRIOR LEG's high sits above the trailing 65-session low —
    "did the leg that produced the current pullback itself show 30%+ buying
    force", re-anchored off the leg high instead of TODAY's close.

    Cite: WK groww2/CH3.1 — the same ">=30-35% up from 3-month low" test as
    `pct_up_from_65d_low`, but WAVE K6 found that anchoring it to the CURRENT
    close re-kills every reversal/pullback pick: Arora buys 3-5 red days INTO
    a correction, exactly when current-price force is at its lowest, but the
    LEG that preceded the pullback still shows the buying force groww2
    actually means. leg_high reuses `_leg_high` (correction_depth_from_
    leg_high's own leg-high identification, same leg_lookback default) —
    one definition, shared, not re-derived. low65 reuses the same trailing-65
    -session low window as `pct_up_from_65d_low`.
    """
    leg_high = _leg_high(bars, leg_lookback)
    lows = [_num(b, "low") for b in bars[-65:] if _num(b, "low") is not None]
    if leg_high is None or leg_high <= 0 or not lows:
        return None
    low65 = min(lows)
    if low65 <= 0:
        return None
    return (leg_high - low65) / low65 * 100.0


def pullback_volume_character(bars: list[Bar], leg_lookback: int = 60,
                               max_pullback_sessions: int = 10) -> dict:
    """Volume character of the pullback window (leg-high index -> now, capped
    to the last `max_pullback_sessions` bars): does it show a heavy-volume
    red-dot day (institutional distribution) and does up-close volume
    dominate down-close volume (supply drying up)?

    Cite: WK groww2/groww4 (WAVE_K_SPEC PART A) -- "no big red-dot (heavy-
    volume down) day in the pullback; up-volume >> down-volume." Already
    named in archetype-b's spec definition (WAVE_K_SPEC PART C) but never
    implemented until WAVE K8. `has_heavy_red_day` reuses the existing
    purple-dot down-variant numbers (>500,000 shares, <=-5% move) -- not new
    thresholds. leg_high reuses `_leg_high` (same leg_lookback default as
    correction_depth_from_leg_high / leg_force_from_65d_low -- one leg-high
    definition, not re-derived).

    Returns {"has_heavy_red_day": bool, "up_down_vol_ratio": float | None}
    (ratio is None when there are no down-close bars in the window).
    """
    window_all = bars[-leg_lookback:] if leg_lookback else bars
    leg_high = _leg_high(bars, leg_lookback)
    if leg_high is None:
        return {"has_heavy_red_day": False, "up_down_vol_ratio": None}
    leg_high_idx = None
    for i, b in enumerate(window_all):
        if _num(b, "high") == leg_high:
            leg_high_idx = i
    pullback_window = window_all[leg_high_idx:] if leg_high_idx is not None else window_all
    pullback_window = pullback_window[-max_pullback_sessions:]

    has_heavy_red_day = False
    up_vol = 0.0
    down_vol = 0.0
    for b in pullback_window:
        close = _num(b, "close")
        prev_close = _num(b, "prev_close")
        vol = _num(b, "volume")
        if close is None or prev_close is None or vol is None or prev_close == 0:
            continue
        pct_move = (close - prev_close) / prev_close * 100.0
        if close < prev_close:
            down_vol += vol
            if vol > 500_000 and pct_move <= -5:
                has_heavy_red_day = True
        elif close > prev_close:
            up_vol += vol
    ratio = (up_vol / down_vol) if down_vol > 0 else None
    return {"has_heavy_red_day": has_heavy_red_day, "up_down_vol_ratio": ratio}


def high_180d(bars: list[Bar]) -> float | None:
    """Highest high of the trailing 180 sessions -- WAVE K7 reversal-eligibility
    re-anchor: a 60d leg_lookback pre-dates month-long corrections (BSOFT,
    NCC, ZENTEC), so prior strength must be read off a longer window than the
    leg-force metrics above use.

    Cite: WK K7 fix / 6 Manas Entry (BSOFT/NCC/Zentec reversal buys)."""
    window = bars[-180:]
    highs = [_num(b, "high") for b in window if _num(b, "high") is not None]
    if not highs:
        return None
    return max(highs)


def low_252d(bars: list[Bar]) -> float | None:
    """Lowest low of the trailing 252 sessions (~1 year) -- denominator for the
    180d/252d prior-strength ratio test. Cite: WK K7 fix."""
    window = bars[-252:]
    lows = [_num(b, "low") for b in window if _num(b, "low") is not None]
    if not lows:
        return None
    return min(lows)


def correction_depth_from_180d_high(bars: list[Bar]) -> float | None:
    """% pullback of the latest close from `high_180d` -- the reversal
    archetype's correction test (15-40% from the 180d high), distinct from
    `correction_depth_from_leg_high`'s 60d leg window. Cite: WK K7 fix."""
    high = high_180d(bars)
    close = _num(bars[-1], "close") if bars else None
    if high is None or high <= 0 or close is None:
        return None
    return (high - close) / high * 100.0


def rolling_max_momentum_120d(bars: list[Bar], lookback: int = 120) -> float | None:
    """Max of the 63-session momentum computed at each session-end within the
    trailing `lookback` sessions -- "63d momentum was top-40pctile at ANY
    point in the last 120 sessions", computed cheaply as a raw rolling-max
    value rather than a per-historical-day universe percentile (the caller
    compares this against TODAY's population-derived momentum threshold).

    Cite: WK K7 fix / 6 Manas Entry (prior uptrend visible on a longer
    frame before the reversal buy)."""
    if len(bars) < 64:
        return None
    closes = [_num(b, "close") for b in bars]
    start = max(63, len(bars) - lookback)
    best = None
    for end_idx in range(start, len(bars)):
        now = closes[end_idx]
        then = closes[end_idx - 63]
        if now is None or then in (None, 0):
            continue
        mom = (now - then) / then * 100.0
        if best is None or mom > best:
            best = mom
    return best


def ema10_respect(bars: list[Bar], lookback: int = 60) -> dict[str, Any]:
    """How often this stock CLOSES above its 10EMA -- a per-stock character read.

    From the 2026-07-26 high-tight-flag transcripts: "the creme de la creme
    will find support, hold around, shake out UNDER their 10-day EMA. They will
    NOT close underneath their 10-day EMA." The stated reason is trade
    management, not entry: "the best indication of how a stock is going to act
    in the future is how did it act in the past" -- so a name that has
    historically respected its 10EMA can be trailed there, and one that has not
    cannot. That makes this a per-symbol trail SELECTOR, replacing a single
    global trail rule applied to every name regardless of character.

    Two numbers, because they mean different things:
      respect_pct    -- % of the last `lookback` sessions closing above the 10EMA
      shakeout_holds -- sessions whose LOW pierced the 10EMA but whose CLOSE
                        held above it. This is the signature the transcripts
                        single out ("shake out off the 10day" x3); it is a sign
                        of demand absorbing supply, NOT a sign of weakness, and
                        it must not be scored as a violation.

    Measured over our universe on 2026-07-24 (1,683 names, ADR >= 2%), this
    separates the user's own names far better than Stockbee up-day persistence
    does: SIS rank 14, CUPID 43, RAIN 53 (the ones that worked) versus NILKAMAL
    480, NUVOCO 481, EXICOM 375 (the choppy ones). Up-day persistence scattered
    the same names between rank 151 and 1570.

    SHADOW ONLY -- no gate, no rank. Returns None fields when history is short
    rather than defaulting, so a young listing cannot masquerade as disciplined.
    """
    out: dict[str, Any] = {"respect_pct": None, "shakeout_holds": None, "bars": 0}
    closes = [c for c in (_num(b, "close") for b in bars) if c is not None]
    if len(closes) < lookback + 12:  # +12 so the EMA has warmed up
        return out
    k = 2.0 / 11.0
    e = closes[0]
    ema_series = [e]
    for v in closes[1:]:
        e = v * k + e * (1 - k)
        ema_series.append(e)
    seg_c, seg_e = closes[-lookback:], ema_series[-lookback:]
    seg_l = [_num(b, "low") for b in bars[-lookback:]]
    above = sum(1 for cc, ee in zip(seg_c, seg_e) if cc > ee)
    holds = sum(1 for lo, cc, ee in zip(seg_l, seg_c, seg_e)
                if lo is not None and lo < ee and cc > ee)
    out.update({"respect_pct": round(above / lookback * 100.0, 1),
                "shakeout_holds": holds, "bars": lookback})
    return out


UP_DAY_WINDOWS = (5, 10, 15, 20, 40, 60, 126, 252, 504)


def up_day_persistence(bars: list[Bar], windows: tuple[int, ...] = UP_DAY_WINDOWS) -> dict[str, Any]:
    """Stockbee persistence: how MANY of the last N sessions closed up.

    TC2000 formula, from the user's 2026-07-25 screenshot of the Stockbee
    universe ladder: `CountTrue(c > c1, 252)`, sorted descending. The example
    row is CVNA at 152 up-days out of 252 -- rank #2 of 3,459 names -- with the
    stated use: "Buying a pullback on such stocks gives higher probability of
    working."

    This is a THIRD, distinct question from the two persistence-ish things the
    tool already has, and the distinction is the reason it is worth adding:
      persistency_counts  -> consecutive bars price has held above an EMA
                             (an unbroken RUN; breaks to zero on one close under)
      leg_linearity       -> R-squared of the path (SMOOTHNESS of the advance)
      up_day_persistence  -> FREQUENCY of up-closes over a window
    A stock can grind up in a line with few but large up-days, or rise on many
    small up-days with a messy path. Only the frequency read survives a pullback
    intact, which is exactly why Stockbee uses it to qualify pullback buys: the
    count barely moves during the pullback you are trying to buy, whereas
    linearity and EMA-persistency both degrade at that moment.

    Returns {"p5": n, "p10": n, ..., "p504": n, "pct252": 60.3, "windows_ok": [...]}
    with a window omitted (None) when history is too short, never zero-filled --
    a young listing must not look like a stock that simply never rallied.

    SHADOW ONLY, like leg_linearity/base_symmetry: no gate, no rank, no
    threshold. The 252-window count is not comparable across markets or eras
    without a universe-relative rank, and this project already carries ~68
    decision-path thresholds against ~11 independent evaluation dates.
    """
    out: dict[str, Any] = {"windows_ok": []}
    closes = [_num(b, "close") for b in bars]
    for w in windows:
        key = f"p{w}"
        out[key] = None
        # need w+1 closes to form w prior-close comparisons
        if len(closes) < w + 1:
            continue
        seg = closes[-(w + 1):]
        pairs = [(seg[i], seg[i - 1]) for i in range(1, len(seg))]
        usable = [(c, p) for c, p in pairs if c is not None and p is not None]
        if len(usable) < w * 0.8:  # too many gaps to trust the count
            continue
        out[key] = sum(1 for c, p in usable if c > p)
        out["windows_ok"].append(w)
    p252 = out.get("p252")
    out["pct252"] = round(p252 / 252.0 * 100.0, 2) if p252 is not None else None
    return out


def leg_linearity(bars: list[Bar], leg_lookback: int = 60) -> dict[str, Any]:
    """How STRAIGHT the current advance is: R-squared of log(close) regressed
    on time, measured from the leg low to today.

    User doctrine, 2026-07-25: what he screens on today is "Market Environment
    / Strong Sector / Strong Institutional Leg & Shallow Pullback / Liquidity
    Rush / Symmetry / Linearity" -- not the VCP + cup-and-handle pattern names
    he used ten years ago. An audit that day found the tool measured four of
    those six; linearity and symmetry had ZERO implementation (the 33 apparent
    "linearity" hits were all `persistency`, which counts how many BARS price
    held above an EMA -- duration, a different question from smoothness).

    Why R-squared on LOG price: a steady percentage advance is a straight line
    in log space but a curve in rupees, so a raw-price fit would score a fast
    compounder as "non-linear" purely for compounding. Why it matters: an
    institutional markup grinds up in a line; retail churn covers the same
    distance in a jagged mess. Same start, same end, same 21d return -- very
    different tradeability, and nothing in the tool could tell them apart.

    Returns r2 (0-1, higher = straighter), slope_pct_per_bar, the bar count and
    the anchor date, so the number is inspectable rather than a bare score.
    NOT a gate and NOT ranked: display-only until it has forward-return
    evidence, per the 68-thresholds-vs-11-evaluation-dates finding.
    """
    out: dict[str, Any] = {"r2": None, "slope_pct_per_bar": None, "bars": 0, "anchor_date": None}
    if not bars:
        return out
    window = bars[-leg_lookback:] if len(bars) > leg_lookback else list(bars)
    closes = [_num(b, "close") for b in window]
    # Anchor at the lowest close in the window -- the leg's origin. Measuring
    # from an arbitrary N bars ago would score a V-bottom as non-linear because
    # of the decline that preceded it.
    valid = [(i, c) for i, c in enumerate(closes) if c and c > 0]
    if len(valid) < 10:
        return out
    low_i = min(valid, key=lambda t: t[1])[0]
    leg = [(i, c) for i, c in valid if i >= low_i]
    if len(leg) < 10:
        return out

    import math
    xs = [float(i) for i, _ in leg]
    ys = [math.log(c) for _, c in leg]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return out
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else None

    anchor_bar = window[leg[0][0]]
    out.update({
        "r2": round(r2, 4) if r2 is not None else None,
        # exp(slope)-1 converts the log-space slope back to % per bar
        "slope_pct_per_bar": round((math.exp(slope) - 1.0) * 100.0, 4),
        "bars": n,
        "anchor_date": anchor_bar.get("trade_date") or anchor_bar.get("date"),
    })
    return out


def base_symmetry(bars: list[Bar], window: int = 20) -> dict[str, Any]:
    """How EVENLY the current consolidation formed: does the base contract on
    both sides, or is it one violent event plus a drift?

    Same user doctrine as `leg_linearity` above; also unimplemented before
    2026-07-25 (the single "symmetr" hit in the codebase was an unrelated use
    of the word inside a dead module).

    Method: split the trailing `window` in half and compare each half's
    high-low range, then its average volume.
        symmetry = 1 - |R_first - R_second| / (R_first + R_second)
    1.0 = both halves identical, 0.0 = one half carries the entire range. The
    volume twin answers the same question for participation, because a base
    can look symmetric in price while all the activity sits on one side.

    Why it matters for this trader specifically: his EP-vs-SIP doctrine says
    "price usually cannot break resistance without absorbing supply" -- an
    orderly two-sided contraction is what absorption looks like on the chart,
    whereas a gap-down-then-drift base is a single supply event that never got
    absorbed. Display-only, not gated, not ranked.
    """
    out: dict[str, Any] = {
        "price_symmetry": None, "volume_symmetry": None,
        "first_half_range_pct": None, "second_half_range_pct": None, "bars": 0,
    }
    win = bars[-window:] if len(bars) >= window else list(bars)
    if len(win) < 8:
        return out
    half = len(win) // 2
    first, second = win[:half], win[half:]

    def _range_pct(seg: list[Bar]) -> float | None:
        highs = [_num(b, "high") for b in seg]
        lows = [_num(b, "low") for b in seg]
        closes = [_num(b, "close") for b in seg]
        highs = [h for h in highs if h is not None]
        lows = [l for l in lows if l is not None]
        closes = [c for c in closes if c]
        if not highs or not lows or not closes:
            return None
        ref = sum(closes) / len(closes)
        return (max(highs) - min(lows)) / ref * 100.0 if ref else None

    def _avg_vol(seg: list[Bar]) -> float | None:
        vols = [_num(b, "volume") for b in seg]
        vols = [v for v in vols if v is not None]
        return sum(vols) / len(vols) if vols else None

    r1, r2 = _range_pct(first), _range_pct(second)
    v1, v2 = _avg_vol(first), _avg_vol(second)
    if r1 is not None and r2 is not None and (r1 + r2) > 0:
        out["price_symmetry"] = round(1.0 - abs(r1 - r2) / (r1 + r2), 4)
        out["first_half_range_pct"] = round(r1, 2)
        out["second_half_range_pct"] = round(r2, 2)
    if v1 is not None and v2 is not None and (v1 + v2) > 0:
        out["volume_symmetry"] = round(1.0 - abs(v1 - v2) / (v1 + v2), 4)
    out["bars"] = len(win)
    return out


def prev_day_tightness_pctile(bars: list[Bar]) -> float | None:
    """Percentile rank of YESTERDAY's daily range among the stock's own
    trailing 20-day ranges (0 = tightest range in the window, 100 = widest).

    Cite: WK Strong_Start_Tightness_Study.md — "prev-day range in bottom
    pctile of own 20d ranges + uptrend" (archetype a, Strong-Start-ready).
    Percentile is NATURE-RELATIVE by construction (own 20d history, not a
    universe-wide cutoff) per WK CH3.1's nature-relative principle.
    """
    if len(bars) < 2:
        return None
    prior = bars[:-1]
    window = prior[-20:]
    ranges = []
    for b in window:
        h, l = _num(b, "high"), _num(b, "low")
        if h is not None and l is not None:
            ranges.append(h - l)
    if len(ranges) < 5:
        return None
    yday = bars[-2]
    yh, yl = _num(yday, "high"), _num(yday, "low")
    if yh is None or yl is None:
        return None
    yday_range = yh - yl
    below_or_equal = sum(1 for r in ranges if r <= yday_range)
    return below_or_equal / len(ranges) * 100.0


def range_contraction_flag(bars: list[Bar]) -> bool:
    """VCP-coil flag: today's ATR20 sits in the bottom quartile of ATR20
    observed over the trailing 60 sessions AND the last 3 ATR20 readings are
    non-increasing (successive contraction), i.e. "100->70->80->90/95 then
    break" — a genuinely CONTRACTING coil, not just a currently-low ATR.

    Cite: WK groww4/groww2 — "contracting ranges... For me VCP is a
    principle, not a pattern." TTM-S14 — VCP tightness measured via ATR, not
    volume rules.
    """
    if len(bars) < 65:
        return False
    trs = mi._true_ranges(bars)
    atr20 = mi._rma(trs, 20)
    window = atr20[-60:]
    clean = [v for v in window if v is not None]
    if len(clean) < 20:
        return False
    latest = clean[-1]
    sorted_clean = sorted(clean)
    cutoff_idx = max(0, len(sorted_clean) // 4 - 1)
    bottom_quartile_ceiling = sorted_clean[cutoff_idx]
    in_bottom_quartile = latest <= bottom_quartile_ceiling
    last3 = [v for v in atr20[-3:] if v is not None]
    # strictly contracting (not merely flat) -- a flat-but-low ATR is a quiet
    # stock, not a coiling one; the corpus's "100->70->80->90/95" progression
    # requires genuine shrinkage.
    contracting = len(last3) == 3 and last3[0] > last3[1] >= last3[2] and last3[0] > last3[2]
    return bool(in_bottom_quartile and contracting)


def persistency_counts(bars: list[Bar]) -> dict[str, int | None]:
    """Latest persistency `count` for the 10/21/50/200 EMA persistency-state
    machines (ported manas_indicators.persistency), keyed to the P0 archetype
    "persistent-momentum": close >10EMA >=20d, >20EMA >=30d, >50EMA >=50d,
    >200EMA >=150d (TTM-H-III1/III2). manas_indicators ports 10/21/50/200 EMA
    lengths (persistency_ema_bundle); 21 stands in for the corpus's "20EMA"
    (already the ported indicator's convention — not re-derived here).
    """
    bundle = mi.persistency_ema_bundle(bars)
    out: dict[str, int | None] = {}
    for key, rows in bundle.items():
        out[key] = rows[-1]["count"] if rows else None
    return out


PERSISTENCY_THRESHOLDS = {
    # Cite: TTM-H-III1/III2 — close >10EMA>=20d, >20EMA>=30d, >50EMA>=50d,
    # >200EMA>=150d. manas_indicators' 21EMA persistency stands in for "20EMA".
    "ema10": 20,
    "ema21": 30,
    "ema50": 50,
    "ema200": 150,
}


def is_persistent_momentum(counts: dict[str, int | None]) -> bool:
    """True if ANY EMA leg's persistency count has reached its TTM-H-III1/2
    threshold (positive count = still above the MA in an unbroken run)."""
    for key, threshold in PERSISTENCY_THRESHOLDS.items():
        c = counts.get(key)
        if c is not None and c >= threshold:
            return True
    return False
