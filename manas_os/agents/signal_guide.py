"""Deterministic per-signal HOW-TO-TRADE guide.

No LLM involved. Turns a debated candidate/verdict + its (possibly absent)
plan numbers into a numbered, beginner-safe walkthrough: gap check -> wait
window -> entry trigger -> risk-free/day-0 test -> sizing -> live stop order
-> exit line, each templated per setup family and cited back to the lens
design doc it came from.

Sources (cited per step, see LENS_* files for full text):
- manas_os/design/agents/LENS_EP.md              (EP / earnings theme)
- manas_os/design/agents/LENS_STRONG_START.md     (Arora Strong Start / Busted)
- manas_os/design/agents/LENS_IPO.md              (IPO base)
- manas_os/design/knowledge/INDIA_PLAYBOOK.md     (risk & sizing law, §5)
- manas_os/design/agents/COACH_LINES.md           (discipline lines, reused)
"""
from __future__ import annotations

from typing import Any

EP_CITE = "design/agents/LENS_EP.md"
STRONG_START_CITE = "design/agents/LENS_STRONG_START.md"
IPO_CITE = "design/agents/LENS_IPO.md"
PLAYBOOK_CITE = "design/knowledge/INDIA_PLAYBOOK.md"
D2_CITE = "design/knowledge/TRADETM_NUANCES_COMPLETION.md"  # D2 Entry Q2/Q4 (B5b/B5c)

NO_PLAN_NOTE = (
    "No sized plan — this name is debate-only, not a trade. There is no "
    "entry/stop to act on tonight; treat it as a chart to watch, not an "
    "order to place."
)


def _num(value: Any) -> str:
    if value is None:
        return "(no number set)"
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _lens_key(candidate_or_verdict: dict[str, Any] | None, setup_family: str | None) -> str:
    """Fine-grained lens selection. `setup_family` here is whatever caller
    passes (scan_candidates.setup_type is the most specific signal; the
    coarse catalyst/momentum/base-pattern family is the fallback)."""
    candidate_or_verdict = candidate_or_verdict or {}
    text = " ".join(
        str(candidate_or_verdict.get(k) or "")
        for k in ("setup_type", "setup", "pattern_label", "family")
    ).lower()
    text = f"{text} {setup_family or ''}".lower()
    if "ep" in text.split() or "earnings power" in text or text.strip() == "ep":
        return "ep"
    if "ipo" in text:
        return "ipo_base"
    if "strong start" in text or "strong_start" in text or "busted" in text:
        return "strong_start"
    if "d2" in text or "day-2" in text or "day 2" in text or "episodic" in text:
        return "d2"
    return "generic"


def _step(n: int, title: str, instruction: str, check: str, source_cite: str) -> dict[str, Any]:
    return {"n": n, "title": title, "instruction": instruction, "check": check, "source_cite": source_cite}


def _no_plan_step(n: int, reason: str | None) -> dict[str, Any]:
    note = NO_PLAN_NOTE
    if reason:
        note = f"{NO_PLAN_NOTE} (near-miss: {reason})"
    return _step(
        n,
        "No sized plan yet",
        note,
        "Do you have a live entry/stop from tonight's plan? If not, stop reading — there is nothing to execute.",
        "manas_os/agents/debate.py (gate did not produce a trade_plan)",
    )


def _ep_steps(plan: dict[str, Any] | None, near_miss: dict[str, Any] | None) -> list[dict[str, Any]]:
    entry = plan.get("entry") if plan else None
    stop = plan.get("stop") if plan else None
    qty = plan.get("final_qty") if plan else None
    steps = [
        _step(
            1,
            "Check the gap first thing",
            "Look at the gap-up % and the opening-range extension. If gap% + opening-range% "
            "together exceed ~12% of yesterday's close, SKIP the Day-0 entry entirely — there is "
            "no circuit-safe room left to manage the trade.",
            "Is gap% + ORB% over 12%? If yes, stop here — do not take this trade today.",
            f"{EP_CITE} §1 (12% gap+ORB circuit skip)",
        ),
        _step(
            2,
            "Wait for the 5-minute opening range",
            "Do nothing until the first 5-minute candle (9:15-9:20) closes. The Day-0 trigger is "
            "the opening-range HIGH breakout, not the gap-up price itself.",
            "Has the 5-min opening-range candle actually closed?",
            f"{EP_CITE} §1 (5-min ORB proxy trigger)",
        ),
        _step(
            3,
            "Enter only on the ORB breakout with the low holding",
            f"Buy only if price breaks above the opening-range high AND the day's low is still "
            f"holding (not undercutting the stop level). Reference entry from tonight's plan: {_num(entry)}.",
            "Did price actually break above the opening-range high, with the low still intact?",
            f"{EP_CITE} §1 (ORB trigger, stop = day's low)",
        ),
        _step(
            4,
            "Run the day-0 risk-free test",
            "Before sizing up, ask whether the remaining intraday upside from here can realistically "
            "get your stop to breakeven (risk-free) before today's close. If there isn't enough room "
            "left, this is a weak Day-0 entry — better to wait for a 10/21 EMA pullback instead.",
            "Is there enough room left today to move your stop to breakeven?",
            f"{EP_CITE} §5 (day-0 practical test, W23)",
        ),
        _step(
            5,
            "Size off the conservative provisional stop",
            f"Size the position off the wide provisional stop first ({_num(stop)}), not a tighter "
            "stop you're hoping for. Add more only once the live reversal point reveals an actual "
            "tighter stop distance on a pullback.",
            "Are you sizing off the wide day-0 stop, not guessing a tighter one?",
            f"{EP_CITE} §5 (provisional-risk sizing, W11)",
        ),
        _step(
            6,
            "Place the stop-loss order now",
            f"Place a live stop-loss order at {_num(stop)} immediately after entry (day's low / "
            f"breakout-bar low). Final qty (sizer): {_num(qty)}. A stop only in your "
            "head does not count.",
            "Is the stop-loss a live order in your broker terminal right now?",
            f"{PLAYBOOK_CITE} §5 R12 (no mental stops)",
        ),
        _step(
            7,
            "Know your exit line",
            "If the trade holds, the exit trigger is a CLOSE below the 21 EMA (or the 50 DMA if the "
            "stock hasn't extended far) — not a fixed target. Every pullback to the 10/21 EMA is a "
            "chance to add, not a reason to exit.",
            "Do you know which EMA/DMA line you are trailing against?",
            f"{EP_CITE} §5 (21 EMA close-break / 50 DMA exit template)",
        ),
    ]
    if not plan:
        return [_no_plan_step(1, near_miss.get("reason") if near_miss else None)]
    return steps


def _strong_start_steps(plan: dict[str, Any] | None, near_miss: dict[str, Any] | None) -> list[dict[str, Any]]:
    entry = plan.get("entry") if plan else None
    stop = plan.get("stop") if plan else None
    qty = plan.get("final_qty") if plan else None
    steps = [
        _step(
            1,
            "Check the low against yesterday's close",
            "At the open, confirm today's low has not clearly breached yesterday's close. A few-tick "
            "'touch and go' is fine; a real break into the prior range invalidates the setup.",
            "Is the low still holding at or above yesterday's close (not a clean breach)?",
            f"{STRONG_START_CITE} §1 (Strong Start recognition markers)",
        ),
        _step(
            2,
            "Wait 2-3 minutes after the open",
            "Do not buy at 9:15. Wait until roughly 9:17-9:18 before acting, even if price already "
            "looks strong.",
            "Has at least 2-3 minutes passed since the 9:15 open?",
            f"{STRONG_START_CITE} §1 (3-min rule)",
        ),
        _step(
            3,
            "Enter on the cross above yesterday's high",
            f"Buy only once price crosses above yesterday's high, after the 2-3 minute wait. "
            f"Reference entry from tonight's plan: {_num(entry)}.",
            "Did price cross above yesterday's high after (not before) the wait window?",
            f"{STRONG_START_CITE} §1 (entry trigger)",
        ),
        _step(
            4,
            "Check the gap is not too big",
            "If the open already gapped 5-6%+ above yesterday's close, walk away — the stop has to "
            "sit too far below to keep the risk-reward sane.",
            "Is the gap under roughly 5-6%?",
            f"{STRONG_START_CITE} §3 (gap-size disqualifier)",
        ),
        _step(
            5,
            "Optional tiebreaker: relative volume",
            "Not required, but if you're choosing between two similar setups, prefer the one that "
            "has already printed 8-10%+ of its average daily volume in the first 2-3 minutes.",
            "If choosing between two names, does one show clearly higher early volume?",
            f"{STRONG_START_CITE} §1 (RVOL bonus signal)",
        ),
        _step(
            6,
            "Place the stop-loss order now",
            f"Place a live stop-loss order at {_num(stop)} immediately after entry. Final qty (sizer): {_num(qty)}.",
            "Is the stop-loss a live order in your broker terminal right now?",
            f"{PLAYBOOK_CITE} §5 R12 (no mental stops)",
        ),
        _step(
            7,
            "Trail after the first strong day",
            "Once the first strong day confirms, move the stop to breakeven, then trail with the "
            "20-DMA on a closing basis. An emergency stop sits below the latest swing low.",
            "Do you know your breakeven level and the 20-DMA trail line?",
            f"{STRONG_START_CITE} §5 (exit / trail notes)",
        ),
    ]
    if not plan:
        return [_no_plan_step(1, near_miss.get("reason") if near_miss else None)]
    return steps


def _ipo_steps(plan: dict[str, Any] | None, near_miss: dict[str, Any] | None) -> list[dict[str, Any]]:
    entry = plan.get("entry") if plan else None
    stop = plan.get("stop") if plan else None
    qty = plan.get("final_qty") if plan else None
    steps = [
        _step(
            1,
            "Confirm a real right-side trigger today",
            "Look for an inside bar (fully inside yesterday's range) or, even better, a double "
            "inside bar. A double inside bar is an immediate trade — don't wait for a third "
            "confirmation candle.",
            "Is there an inside bar (or double inside bar) on the chart today?",
            f"{IPO_CITE} §1 (first/double inside bar triggers)",
        ),
        _step(
            2,
            "Check retracement on the key strong candle",
            "If the base's key strong candle has given back more than 50% of its own range, the "
            "demand read is broken — skip it, even if the pattern still looks tidy.",
            "Has the strong candle held under 50% retracement of its own range?",
            f"{IPO_CITE} §3 (excessive retracement disqualifier)",
        ),
        _step(
            3,
            "Confirm the daily frame agrees",
            "Before acting on a 75-min/15-min trigger, confirm the daily chart still shows the base "
            "intact. Daily beats 75-min beats 15-min when they disagree.",
            "Does the daily chart still show the base holding, not broken down?",
            f"{IPO_CITE} §1 (multi-timeframe confirmation rule)",
        ),
        _step(
            4,
            "Accept the wider stop as normal",
            f"IPO stops run wider than a normal swing trade — 4-6% is TIGHT here, not wide, because "
            f"you are buying the bottom of a completed reversal. Reference stop from tonight's plan: {_num(stop)}.",
            "Are you sizing for a 4-6% stop, not expecting a 1-2% velocity-trade stop?",
            f"{IPO_CITE} §1 (IPO stop width)",
        ),
        _step(
            5,
            "Place the stop-loss order now",
            f"Place a live stop-loss order at {_num(stop)} immediately after entry ({_num(entry)}). "
            f"Final qty (sizer): {_num(qty)}.",
            "Is the stop-loss a live order in your broker terminal right now?",
            f"{PLAYBOOK_CITE} §5 R12 (no mental stops)",
        ),
        _step(
            6,
            "Flag a late entry",
            "If getting to breakeven from here needs more than roughly 15% upside, this is a "
            "loose/late entry — size down rather than force full size onto it.",
            "Does breakeven require less than ~15% upside from here?",
            f"{IPO_CITE} §1 (fire-power vs entry quality)",
        ),
    ]
    if not plan:
        return [_no_plan_step(1, near_miss.get("reason") if near_miss else None)]
    return steps


def _d2_steps(plan: dict[str, Any] | None, near_miss: dict[str, Any] | None) -> list[dict[str, Any]]:
    entry = plan.get("entry") if plan else None
    stop = plan.get("stop") if plan else None
    qty = plan.get("final_qty") if plan else None
    steps = [
        _step(
            1,
            "Confirm yesterday was a real Day-1 burst",
            "This is a Day-2 trade: yesterday must have been a strong first day of expansion — a "
            "10%+ move (ideally a 20% circuit) on high volume, out of a consolidation, closing near "
            "its highs. A 4-6% day is too weak to follow up.",
            "Was yesterday a 10%+ (or 20% circuit) expansion day out of a base, not the 2nd/3rd day of a move?",
            f"{D2_CITE} (D2 Entry Q2/Q4a: Day-1 quality)",
        ),
        _step(
            2,
            "Read the open to pick the branch",
            "Day-2 is three setups in one, decided by the open: (a) STRONG close near highs -> expect "
            "a gap-up, use gap-up entry technique; (b) WEAK/wick close -> Wick Play, look for a strong "
            "slight gap-up on pent-up demand; (c) GAP-DOWN on overnight news -> gap-down reversal off "
            "the morning low. Tonight's card names the expected branch, but the open decides.",
            "Which branch did the open actually produce (gap-up continuation, wick play, or gap-down reversal)?",
            f"{D2_CITE} (D2 Entry Q4b: three branches)",
        ),
        _step(
            3,
            "Enter on intraday structure, not the gap",
            f"Take the entry on a 5-min opening-range-high / day-high breakout — never the gap price "
            f"itself. Reference entry from tonight's plan: {_num(entry)}.",
            "Are you entering on an ORB / day-high breakout rather than chasing the gap?",
            f"{D2_CITE} (D2 Entry Q4c: intraday ORB/range/day-high)",
        ),
        _step(
            4,
            "Skip if gap + ORB is too extended",
            "If the gap-up % plus the first 5-min opening-range % exceeds 12% of the prior close, skip "
            "it — the 5% circuit prevents the trade going risk-free the same day.",
            "Is gap% + opening-range% under 12%?",
            f"{PLAYBOOK_CITE} gate U5 (>12% gap+ORB skip)",
        ),
        _step(
            5,
            "Place the stop at the day's low",
            f"The morning/day low is the maximum-pressure anchor: place a live stop just below it "
            f"(~1.5-2% tight). Reference stop from tonight's plan: {_num(stop)}. Final qty (sizer): {_num(qty)}.",
            "Is a live stop-loss set just below the morning/day low?",
            f"{PLAYBOOK_CITE} §5 R12 (no mental stops); day-low anchor (TRADETM_NUANCES_SHARDS #13)",
        ),
    ]
    if not plan:
        return [_no_plan_step(1, near_miss.get("reason") if near_miss else None)]
    return steps


def _generic_steps(plan: dict[str, Any] | None, near_miss: dict[str, Any] | None) -> list[dict[str, Any]]:
    entry = plan.get("entry") if plan else None
    stop = plan.get("stop") if plan else None
    qty = plan.get("final_qty") if plan else None
    steps = [
        _step(
            1,
            "Confirm it's a pullback, not a chase",
            "Check that price is pulling back toward support (10/21 EMA or the prior base) rather "
            "than being bought on an already-extended breakout.",
            "Is this a pullback-to-support entry, not a chase into an extended move?",
            f"{PLAYBOOK_CITE} §3.4 (pullback-near-support > breakout)",
        ),
        _step(
            2,
            "Let the pullback hold",
            "A shakeout (a brief undercut of support that recovers the same day) is fine and often "
            "cleaner than no shakeout at all. A clean breakdown through support is not — stand aside.",
            "Did support hold (or a shakeout recover), rather than a clean breakdown?",
            f"{PLAYBOOK_CITE} §3.4 (10/20 MA undercut-and-recover)",
        ),
        _step(
            3,
            "Enter at the plan's level",
            f"Enter at or above tonight's plan entry: {_num(entry)}. Don't pre-empt it on a guess.",
            "Are you entering at the plan's level, not ahead of it?",
            f"{PLAYBOOK_CITE} §5 (R1: position size = risk / stop distance)",
        ),
        _step(
            4,
            "Place the stop-loss order now",
            f"Place a live stop-loss order at {_num(stop)} immediately after entry. Final qty (sizer): {_num(qty)}. There is no such thing as a mental stop.",
            "Is the stop-loss a live order in your broker terminal right now?",
            f"{PLAYBOOK_CITE} §5 R12 (no mental stops)",
        ),
        _step(
            5,
            "Trail per the plan's template, don't over-manage",
            "Manage this the way its family is meant to be managed: a quick velocity trade gets a "
            "tight trailing stop and quick profit-taking; a magnitude/theme trade gets a wider "
            "structural stop and is sold into weakness, not strength. Don't mix the two.",
            "Do you know whether this is a velocity or magnitude trade, and are you managing it that way?",
            f"{PLAYBOOK_CITE} §6 (trade-management templates by setup type)",
        ),
    ]
    if not plan:
        return [_no_plan_step(1, near_miss.get("reason") if near_miss else None)]
    return steps


_TEMPLATES = {
    "ep": _ep_steps,
    "strong_start": _strong_start_steps,
    "d2": _d2_steps,
    "ipo_base": _ipo_steps,
    "generic": _generic_steps,
}


def _step_zero_refusal(sizer_reasoning: str | None) -> dict[str, Any]:
    reason = sizer_reasoning or "no reasoning recorded"
    return _step(
        0,
        "DO NOT place a live order tonight",
        f"The sizer refused this trade (final qty 0). Reason: {reason} Paper-trade the steps "
        "below to build the sample instead of risking live capital.",
        "Have you confirmed the sizer's final qty is 0 before reading any further step?",
        "manas_os/agents/sizer.py (final_qty authority over plan.suggested_qty)",
    )


def build_guide(
    candidate_or_verdict: dict[str, Any] | None,
    setup_family: str | None,
    plan: dict[str, Any] | None,
    regime: str | None = None,
    sizer: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic, LLM-free numbered walkthrough for one debated symbol.

    `candidate_or_verdict` carries whatever identifying fields are available
    (setup_type/setup/pattern_label/near_miss); `setup_family` is the best
    family hint the caller has; `plan` is the entry/stop/target dict (or
    None/near-miss when the gate never produced a sized trade) — sizing
    language inside each template reads `plan["final_qty"]`, which the
    sizer has final authority over (NEVER plan.suggested_qty); `regime` is
    the current market_mode, reserved for future regime-specific sizing
    language (not currently branched on — the family template already
    carries the sizing discipline). `sizer` is the debate card's sizer
    block ({"multiplier", "final_qty", "reasoning"}) — when final_qty is 0,
    a "step 0" live-order refusal is injected ahead of the normal steps.
    """
    candidate_or_verdict = candidate_or_verdict or {}
    near_miss = candidate_or_verdict.get("near_miss")
    has_plan = bool(plan) and any(plan.get(k) is not None for k in ("entry", "stop"))
    lens = _lens_key(candidate_or_verdict, setup_family)
    builder = _TEMPLATES.get(lens, _generic_steps)
    steps = builder(plan if has_plan else None, near_miss)

    final_qty = (sizer or {}).get("final_qty")
    sizer_refused = has_plan and sizer is not None and final_qty == 0
    if sizer_refused:
        steps = [_step_zero_refusal((sizer or {}).get("reasoning"))] + steps
    return steps


def guide_family_label(candidate_or_verdict: dict[str, Any] | None, setup_family: str | None) -> str:
    return _lens_key(candidate_or_verdict, setup_family)
