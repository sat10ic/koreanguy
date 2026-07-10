"""scanner/gates.py — the deterministic refusal cascade (Manas 2.0, plan T1.1).

A candidate must pass EVERY gate to appear in the feed. The cascade is
fail-fast for HARD failures, but ALWAYS returns which gate failed and why (the
refusal ledger depends on it). No gate emits an additive score — pass/fail +
named evidence only.

WAVE_M M3 (user order 2026-07-11, CONSTRAINT_METHOD_FIRST_IA.md amendment 3 —
"the filter IS the defect"): three specific checks are no longer hard drops —
RS_FLOOR, 52w-high nearness (both inside gate_trend_template), and the
regime ALLOWED_FAMILIES family-kill (gate_regime, when the mode itself is
tradeable). Each instead produces a named, WEIGHTED objection recorded in the
gate's evidence (`evidence["objections"]`) — the candidate still passes that
gate and rides its objections into scan_candidates evidence/gates_json (or,
for a name that fails a LATER hard gate anyway, into the refusals ledger's
evidence_json). `scanner.candidates` subtracts the objection weight from the
ordinal rank and caps the grade; it never silently excludes on these grounds
alone. HARD gates unchanged: tradability, risk (risk.plan.validate — the
single writer of size/stop/target), NO_TRADE regime (0 cards stays 0), and
the structural parts of trend-template (enough history, confirmed uptrend,
EMA-Lead stacking).

Gate order: regime → tradability → trend-template → fresh-leg → participation
→ risk (risk delegates to risk.plan.validate — the single writer of size).
"""
from __future__ import annotations

import statistics
from typing import Any, Callable

from manas_os.engine.eod_detectors import ema, sma, _num, _closes
from manas_os.risk import plan as risk_plan

Bar = dict[str, Any]

# --- LOCKED tables --------------------------------------------------------------
ALLOWED_FAMILIES = {
    "RISK_ON":   {"catalyst", "base/pattern", "momentum", "accumulation"},
    "SELECTIVE": {"catalyst", "base/pattern"},          # ep, pullback, launch_pad, ipo_base(A)
    "DEFENSIVE": {"catalyst"},                          # ep only
    "NO_TRADE":  set(),
}
RS_FLOOR = 80.0
NEARNESS_ENTRY = 0.85
NEARNESS_ANTICHASE = 0.97

# --- M3 scored-objection weights ------------------------------------------------
# On the same rough scale as delivery_z (candidates.py's existing primary
# ordinal rank key, typically -3..+3) so an objection visibly moves a name
# down the rank without inventing a second, parallel scoring system.
# regime_family carries the heaviest weight — a whole-family policy
# disagreement is a bigger objection than either single numeric proximity
# miss. Not LOCKED like the tables above; tunable as objection-era evidence
# (survivor recall / expectancy by objection) comes in.
OBJECTION_WEIGHTS = {
    "rs_floor": 1.0,
    "nearness_52w": 0.75,
    "regime_family": 1.5,
}
MAX1_THRESHOLD = 18.0          # % single-day gain, 20 sessions
MAX1_MCAP_CR = 3000.0
LOTTERY_RATIO = 6.0            # MAX5(60d)/avg daily — flag only
PUMP_DELIVERY_Z = 3.0
PUMP_MCAP_CR = 1000.0
EXT21_FRESH = 6.0              # % above 21EMA — fresh
EXT21_STALE = 8.0              # % above 21EMA — stale/refuse
PIVOT_FRESH = 1.04
PIVOT_STALE = 1.08
BREAKOUT_AGE_FRESH = 7
PULLBACK_AGE_MAX = 15
VOL_CONFIRM = 1.2              # ×20d avg, breakout-day entries


def _gate(name: str, ok: bool, reason: str | None, **evidence: Any) -> dict[str, Any]:
    return {"gate": name, "pass": ok, "reason": None if ok else reason, "evidence": evidence}


def range_expansion(bars: list[Bar]) -> dict[str, Any]:
    trs: list[float] = []
    for i, bar in enumerate(bars):
        high, low = _num(bar.get("high")), _num(bar.get("low"))
        prev_close = _num(bar.get("prev_close"))
        if prev_close is None and i > 0:
            prev_close = _num(bars[i - 1].get("close"))
        if high is None or low is None or prev_close is None:
            continue
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if not trs:
        return {"tr": None, "atr14": None, "expanded": False}
    tr = trs[-1]
    atr_window = trs[-14:]
    atr14 = sum(atr_window) / len(atr_window) if len(atr_window) == 14 else None
    return {"tr": tr, "atr14": atr14, "expanded": bool(atr14 is not None and tr >= 1.2 * atr14)}


# --- individual gates -------------------------------------------------------------

def gate_regime(setup_family: str, market_mode: str) -> dict[str, Any]:
    mode = (market_mode or "NO_TRADE").upper()
    if mode not in ALLOWED_FAMILIES or mode == "NO_TRADE":
        # M3: NO_TRADE (or any unrecognized mode, treated identically — there
        # is no family this cascade is willing to admit) stays a HARD
        # refusal. "0 cards stays 0" is a LOCKED invariant, not a per-family
        # objection like the family-kill case below.
        allowed = ALLOWED_FAMILIES.get(mode, set())
        return _gate("regime", False,
                     f"{mode}: no setups permitted (allowed: {sorted(allowed) or 'none'})",
                     market_mode=mode, setup_family=setup_family, hard=True)
    allowed = ALLOWED_FAMILIES[mode]
    if setup_family in allowed:
        return _gate("regime", True, None, market_mode=mode, setup_family=setup_family)
    # M3: a family ban is now a SCORED OBJECTION, not a hard drop (user order
    # 2026-07-11) — Arora trades individual strength even in a muted tape.
    # The candidate still passes this gate; the objection rides in evidence
    # and subtracts from the ordinal rank in candidates._assign_ranks.
    objection = {
        "code": "regime_family",
        "gate": "regime",
        "reason": f"{mode} does not typically allow {setup_family} setups (allowed: {sorted(allowed)})",
        "weight": OBJECTION_WEIGHTS["regime_family"],
    }
    return _gate("regime", True, None, market_mode=mode, setup_family=setup_family,
                 objections=[objection])


def max1_pct(bars: list[Bar], lookback: int = 20) -> float | None:
    """Largest single-day % gain over the trailing lookback sessions."""
    window = bars[-(lookback + 1):]
    gains = []
    for i in range(1, len(window)):
        c, pc = _num(window[i].get("close")), _num(window[i - 1].get("close"))
        if c is not None and pc:
            gains.append((c - pc) / pc * 100.0)
    return max(gains) if gains else None


def lottery_ratio(bars: list[Bar]) -> float | None:
    """MAX5 mean of top-5 daily gains (60d) / mean absolute daily move."""
    window = bars[-61:]
    moves = []
    for i in range(1, len(window)):
        c, pc = _num(window[i].get("close")), _num(window[i - 1].get("close"))
        if c is not None and pc:
            moves.append((c - pc) / pc * 100.0)
    if len(moves) < 20:
        return None
    top5 = sorted(moves, reverse=True)[:5]
    avg_abs = sum(abs(m) for m in moves) / len(moves)
    return (sum(top5) / 5.0) / avg_abs if avg_abs > 0 else None


def delivery_z(bars: list[Bar], window: int = 50) -> float | None:
    """(today's delivery% − 50d mean) / 50d std. None when history is thin."""
    vals = [_num(b.get("delivery_pct")) for b in bars[-(window + 1):]]
    vals = [v for v in vals if v is not None]
    if len(vals) < 20:
        return None
    today, hist = vals[-1], vals[:-1]
    mean = sum(hist) / len(hist)
    # 1pp dispersion floor: an ultra-stable delivery series must still flag a
    # collapse (60 -> 20 on zero historical std would otherwise z=0).
    std = max(statistics.pstdev(hist), 1.0)
    return (today - mean) / std


def gate_tradability(
    bars: list[Bar],
    symbol: str,
    quality: dict[str, Any] | None,           # symbol_quality row (asm_stage, market_cap_cr)
    universe_verdict: dict[str, Any] | None,  # engine.universe_filter.evaluate_symbol output
    has_recent_disclosure: bool | None = None,  # None = disclosures not ingested yet (Phase 2)
) -> dict[str, Any]:
    q = quality or {}
    mcap = _num(q.get("market_cap_cr"))
    # existing universe gate (ETF/penny/illiquid/circuit-locked)
    if universe_verdict is not None and not universe_verdict.get("tradeable", True):
        return _gate("tradability", False,
                     "; ".join(universe_verdict.get("reasons_failed", ["universe gate failed"])))
    # ASM — any stage refuses
    if q.get("asm_stage") is not None:
        return _gate("tradability", False, f"ASM-flagged ({q['asm_stage']}) — surveillance risk")
    # MAX/lottery hard exclusion
    m1 = max1_pct(bars)
    if m1 is not None and m1 >= MAX1_THRESHOLD and mcap is not None and mcap <= MAX1_MCAP_CR:
        return _gate("tradability", False,
                     f"lottery profile: +{m1:.0f}% single-day move within 20 sessions on a "
                     f"Rs {mcap:.0f}cr small-cap — these underperform; refusing the trap",
                     max1=round(m1, 1), mcap=mcap)
    # pump signature (interim until disclosures ingested: skip the no-news leg when unknown)
    dz = delivery_z(bars)
    if (dz is not None and dz > PUMP_DELIVERY_Z and mcap is not None and mcap < PUMP_MCAP_CR
            and has_recent_disclosure is False):
        return _gate("tradability", False,
                     f"pump signature: delivery {dz:.1f}σ above normal on a Rs {mcap:.0f}cr "
                     f"micro-cap with NO disclosure in 5 sessions")
    lot = lottery_ratio(bars)
    return _gate("tradability", True, None,
                 max1=None if m1 is None else round(m1, 1),
                 delivery_z=None if dz is None else round(dz, 2),
                 lottery_flag=bool(lot is not None and lot >= LOTTERY_RATIO))


def gate_trend_template(bars: list[Bar], setup_family: str, rs_rating: float | None) -> dict[str, Any]:
    closes = _closes(bars)
    if len([c for c in closes if c is not None]) < 200:
        # not enough history for 200SMA — template can't be verified; EP/IPO exempt
        if setup_family in ("catalyst",):
            return _gate("trend-template", True, None, note="catalyst family: template waived (<200 bars)")
        return _gate("trend-template", False, "insufficient history for 50/200SMA trend template")
    close = closes[-1]
    s50, s200 = sma(closes, 50)[-1], sma(closes, 200)[-1]
    e9, e21, e50 = ema(closes, 9)[-1], ema(closes, 21)[-1], ema(closes, 50)[-1]
    highs = [_num(b.get("high")) for b in bars[-252:] if _num(b.get("high")) is not None]
    nearness = close / max(highs) if highs and close else None

    if None in (close, s50, s200, e9, e21, e50):
        return _gate("trend-template", False, "missing MA inputs")
    if not (close > s50 > s200):
        return _gate("trend-template", False,
                     f"not in a confirmed uptrend (close {close:.1f} / 50SMA {s50:.1f} / 200SMA {s200:.1f})")
    if not (e9 > e21 > e50):
        return _gate("trend-template", False,
                     "EMA stacking is not Lead (need 9EMA > 21EMA > 50EMA)")

    # M3: RS floor + 52w-high nearness are now SCORED OBJECTIONS (user order
    # 2026-07-11), not hard drops — they measure how STRONG a confirmed trend
    # is, not whether one exists (the structural checks above stay hard).
    objections: list[dict[str, Any]] = []
    if rs_rating is not None and rs_rating < RS_FLOOR:
        objections.append({
            "code": "rs_floor", "gate": "trend-template",
            "reason": f"RS {rs_rating:.0f} below {RS_FLOOR:.0f} floor",
            "weight": OBJECTION_WEIGHTS["rs_floor"],
        })
    if setup_family != "catalyst" and (nearness is None or nearness < NEARNESS_ENTRY):
        objections.append({
            "code": "nearness_52w", "gate": "trend-template",
            "reason": (f"only {nearness:.2f} of 52w high — a recovery rally, not a base breakout"
                       if nearness else "52w-high nearness unknown"),
            "weight": OBJECTION_WEIGHTS["nearness_52w"],
        })
    evidence: dict[str, Any] = {
        "nearness_52w": None if nearness is None else round(nearness, 3),
        "ema_stack": "Lead",
    }
    if objections:
        evidence["objections"] = objections
    return _gate("trend-template", True, None, **evidence)


def gate_fresh_leg(
    bars: list[Bar],
    pivot: float | None,
    breakout_age: int | None,      # bars since breakout; None = unknown
    rvol_declining: bool = False,
    enforce_staleness: bool = False,  # WAVE_J J6: shadow mode — see below
) -> dict[str, Any]:
    """WAVE_J J6 (evidence-only latent-bug fix, LOCKED thresholds unchanged):
    the cascade previously always passed breakout_age=None, which silently
    disabled the staleness check below (`breakout_age is not None and
    breakout_age > PULLBACK_AGE_MAX`) and the FRESH_BREAKOUT/FRESH_PULLBACK
    state machine — the tool's only anti-staleness/anti-chase machinery was
    dead code in production. candidates.py now computes a real breakout_age
    and passes it here, but `enforce_staleness` defaults to False so the
    staleness branch is recorded in evidence as `would_refuse_stale` WITHOUT
    actually refusing — this gate still passes every name it used to pass.
    Real leg-age starts flowing into the refusal ledger with ZERO behavior
    change; a later, separate decision flips enforce_staleness after the
    refusal-ledger evidence is reviewed (design/WAVE_J_SPEC.md J6/§4.6).
    """
    closes = _closes(bars)
    close = closes[-1]
    e21 = ema(closes, 21)[-1]
    if close is None or e21 is None or e21 <= 0:
        return _gate("fresh-leg", False, "missing close/21EMA")
    ext21 = (close / e21 - 1.0) * 100.0
    highs = [_num(b.get("high")) for b in bars[-252:] if _num(b.get("high")) is not None]
    nearness = close / max(highs) if highs else None

    would_refuse_stale = bool(breakout_age is not None and breakout_age > PULLBACK_AGE_MAX)

    # STALE conditions (LOCKED) — unconditional
    if ext21 > EXT21_STALE:
        return _gate("fresh-leg", False, f"extended: {ext21:.1f}% above 21EMA (> {EXT21_STALE:.0f}%)")
    if pivot and close > pivot * PIVOT_STALE:
        return _gate("fresh-leg", False,
                     f"chasing: {((close/pivot)-1)*100:.1f}% above pivot (> {int((PIVOT_STALE-1)*100)}%)")
    if would_refuse_stale and enforce_staleness:
        return _gate("fresh-leg", False, f"leg is {breakout_age} bars old (> {PULLBACK_AGE_MAX})")
    # anti-chase: parabolic near the high with fading volume
    if (nearness is not None and nearness >= NEARNESS_ANTICHASE and ext21 > EXT21_FRESH
            and rvol_declining):
        return _gate("fresh-leg", False,
                     f"parabolic: {nearness:.2f} of 52w high, {ext21:.1f}% above 21EMA on "
                     f"declining volume — this is where you sell, not buy")

    state = "FRESH"
    if breakout_age is not None and pivot:
        if breakout_age <= BREAKOUT_AGE_FRESH and close <= pivot * PIVOT_FRESH and ext21 <= EXT21_FRESH:
            state = "FRESH_BREAKOUT"
        elif 3 <= breakout_age <= PULLBACK_AGE_MAX:
            state = "FRESH_PULLBACK"
    return _gate("fresh-leg", True, None, state=state, extension_21=round(ext21, 1),
                 breakout_age=breakout_age, leg_age=breakout_age,
                 would_refuse_stale=would_refuse_stale)


def gate_participation(bars: list[Bar], breakout_day_entry: bool = False) -> dict[str, Any]:
    dz = delivery_z(bars)
    evidence: dict[str, Any] = {"delivery_z": None if dz is None else round(dz, 2)}
    if dz is not None and dz < 0:
        return _gate("participation", False,
                     f"delivery {dz:.1f}σ BELOW its own norm — distribution into the trigger")
    if breakout_day_entry:
        vols = [_num(b.get("volume")) for b in bars[-21:-1] if _num(b.get("volume"))]
        v = _num(bars[-1].get("volume"))
        if vols and v is not None and v < (sum(vols) / len(vols)) * VOL_CONFIRM:
            return _gate("participation", False,
                         f"breakout volume {v/ (sum(vols)/len(vols)):.2f}x below {VOL_CONFIRM}x confirm")
        # range-expansion confirm: a real breakout bar EXPANDS. TR of the last bar
        # must be >= 1.2 x ATR14, else flag (not refuse) as narrow-range breakout.
        expansion = range_expansion(bars)
        if expansion["atr14"] is not None and not expansion["expanded"]:
            evidence["narrow_range_breakout"] = True
    return _gate("participation", True, None, **evidence)


def gate_risk(plan_result: dict[str, Any]) -> dict[str, Any]:
    ok = bool(plan_result.get("pass"))
    return _gate("risk", ok, "; ".join(plan_result.get("reasons", [])) or "risk math failed",
                 stop_pct=plan_result.get("stop_pct"), rr=plan_result.get("rr"),
                 qty=plan_result.get("qty"))


# --- the cascade --------------------------------------------------------------------

def _collect_objections(gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """M3: flatten every gate's `evidence["objections"]` into one ordered
    list. Collected regardless of overall pass/fail so a name that carries an
    objection but is THEN hard-refused by a later gate still shows the
    objection in the refusals ledger's evidence_json — visible either way."""
    out: list[dict[str, Any]] = []
    for r in gate_results:
        out.extend((r.get("evidence") or {}).get("objections") or [])
    return out


def run_cascade(ctx: dict[str, Any]) -> dict[str, Any]:
    """ctx keys: bars, symbol, setup_family, market_mode, quality, universe_verdict,
    rs_rating, pivot, breakout_age, rvol_declining, breakout_day_entry, plan_result,
    has_recent_disclosure. Fail-fast on HARD failures only, but the failing gate +
    reason is always recorded; SCORED OBJECTIONS (M3) never fail-fast — they ride
    along in `objections` on both the pass and fail outcome.
    """
    steps: list[Callable[[], dict[str, Any]]] = [
        lambda: gate_regime(ctx["setup_family"], ctx["market_mode"]),
        lambda: gate_tradability(ctx["bars"], ctx["symbol"], ctx.get("quality"),
                                 ctx.get("universe_verdict"), ctx.get("has_recent_disclosure")),
        lambda: gate_trend_template(ctx["bars"], ctx["setup_family"], ctx.get("rs_rating")),
        lambda: gate_fresh_leg(ctx["bars"], ctx.get("pivot"), ctx.get("breakout_age"),
                               ctx.get("rvol_declining", False),
                               ctx.get("enforce_staleness", False)),
        lambda: gate_participation(ctx["bars"], ctx.get("breakout_day_entry", False)),
        lambda: gate_risk(ctx.get("plan_result") or {}),
    ]
    results: list[dict[str, Any]] = []
    for step in steps:
        r = step()
        results.append(r)
        if not r["pass"]:
            return {"passed": False, "failed_at": r["gate"], "reasons": [r["reason"]],
                    "gates": results, "objections": _collect_objections(results)}
    return {"passed": True, "failed_at": None, "reasons": [], "gates": results,
            "objections": _collect_objections(results)}
