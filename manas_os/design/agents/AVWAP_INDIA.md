# LENS: Anchored VWAP (AVWAP) — NSE/India

Source: Brian Shannon's Anchored VWAP methodology (*Maximum Trading Gains with Anchored VWAP*),
adapted to NSE mechanics. Every rule below is meant to be followed verbatim by the debate model.
The deterministic engine (`engine/eod_detectors.py :: avwap_auto_anchor`) is the fallback and the
validator: the model may override the auto anchor but only by picking from the supplied candidate
list, never by inventing a date.

## 0. WHAT AVWAP IS (grounding, 3 lines)
- VWAP re-started from ONE chosen event bar: cumulative Σ(close×vol)/Σ(vol) from anchor to today.
- It marks the average price every share-holder paid since that event = the crowd's break-even.
- Price relative to a rising/falling AVWAP reveals who is in profit (support) vs. underwater (supply).

## 1. ANCHOR TYPE STRINGS (must match engine exactly)
Auto-detected by the engine — always present as candidates when their trigger fires:
- `earnings-gap` — significance 3. Engine trigger: gap ≥ +4% AND volume > 1.5× avg20 (+1 sig if > 2×).
- `breakout`     — significance 2. Engine trigger: close > max(high) of prior 20 bars AND vol > 1.5× avg20.
- `swing-low`    — significance 1. Engine trigger: bar low strictly < both 4-bar neighbours (9-bar confirm).
- `fallback`     — significance 0. Latest bar; used only when nothing above fired. NEVER a thesis anchor.

India-specific / Shannon types NOT yet auto-detected (the model may name them ONLY if the candidate
list supplies a matching bar; otherwise do not use — see §7 tension note):
- `ipo-listing`  — first trading bar of a fresh listing.
- `high-volume`  — highest-volume session of the last 60 bars (institutional footprint).
- `block-deal`   — disclosure-backed bulk/block-deal print (NSE bulk-deal feed).
- `post-circuit` — the FIRST normal session AFTER a circuit-limit day (never the circuit bar itself).

## 2. ANCHOR SELECTION HIERARCHY (ranked; objective triggers)
Rank order when several candidates exist (higher wins):
1. `earnings-gap`  — gap > +4% AND vol > 2× avg20 (Shannon's strongest re-rating event).
2. `breakout`      — close over a valid pivot (prior 20-bar high) AND vol > 1.5× avg20.
3. `ipo-listing`   — listing day, only for names < ~90 sessions old.
4. `swing-low`     — confirmed major low: bar low is the lowest of a 9-bar window (3-5 bars each side).
5. `high-volume`   — highest-volume bar of last 60 sessions when 1-4 absent.
6. `block-deal`    — disclosure-backed institutional print (India-specific, §6).
7. `post-circuit`  — anchor the session AFTER a circuit day; the circuit bar's price is distorted.
- TIE-BREAK / OVERRIDE RULE: among candidates, prefer the MOST RECENT anchor that price has
  RESPECTED — defined as ≥ 2 touches (within 1% of AVWAP) that HELD (closed back on the trend side).
  A respected lower-rank anchor beats an untested higher-rank one.
- NEVER anchor to `fallback` or to a circuit bar as a thesis anchor.

## 3. STATE READS (price vs AVWAP; use % bands)
Let d% = (close / avwap − 1) × 100.
- ABOVE a RISING AVWAP (d% > +1, slope up): institutions in profit → support / bullish bias.
- RECLAIM after a loss (was below ≥ 3 bars, now d% > +1 closing): FAILED BREAKDOWN → strongest long bias.
- AT-ANCHOR TEST (|d%| ≤ 1): decision zone — the crowd's break-even is being tested right here.
- HUGGING / FLAT AVWAP (|d%| ≤ 1 for ≥ 5 bars, slope ~0): balance → WAIT, no edge.
- BELOW a FALLING AVWAP (d% < −1, slope down): net holders underwater = supply overhead → AVOID longs.

## 4. ACTIONS PER STATE
- ENTRY: only on a pullback-to-AVWAP hold (|d%| ≤ 1 then close back above) CONFIRMED by
  delivery% ≥ its own 20-day average on the touch bar (genuine accumulation, not a churn bounce).
- ADD / PYRAMID: on each subsequent pullback that holds the rising AVWAP with delivery% confirmation.
- TRAIL: AVWAP is an ADVISORY dynamic reference for bias only. It NEVER overrides the risk engine's
  hard stop. Report AVWAP as "trail bias" context; the plan's SL number remains authoritative.
- EXIT BIAS: 2 consecutive CLOSES below an `earnings-gap` anchor AVWAP = re-rating thesis broken →
  strong exit bias. For other anchor types, 2 closes below = downgrade to neutral/avoid.

## 5. INDIA SPECIFICS
- DELIVERY%-WEIGHTED READ: an AVWAP touch that holds on HIGH delivery% (≥ 20-day avg) = real
  institutional accumulation; a hold on low delivery% (intraday churn) is weak — discount it.
- ASM/GSM CAVEAT: for names in NSE ASM/GSM surveillance, price discovery is throttled → AVWAP is
  unreliable. DECLINE to use AVWAP; output "no actionable anchor".
- CIRCUIT BANDS: a session that hit an upper/lower circuit is a distorted print. Do NOT anchor to it;
  use `post-circuit` (the next normal session) instead.
- T+1 SETTLEMENT: NSE is T+1, so delivery/holding data settles fast — a delivery%-confirmed AVWAP hold
  reflects real positioning within a day, making the delivery filter more trustworthy than in T+2 markets.
- BULK/BLOCK-DEAL ANCHOR: an NSE-disclosed bulk (>0.5% of equity) or block deal is a datable
  institutional print → valid `block-deal` anchor when supplied in candidates.

## 6. BLOCK-DEAL ANCHOR RULE
Use `block-deal` only when the candidate list carries a disclosure-backed date (buyer/seller + qty).
A buy-side institutional print near price = accumulation floor (bullish AVWAP support). A sell-side
print = distribution ceiling (bearish). Never infer a block deal from price/volume alone.

## 7. OUTPUT CONTRACT (for the debate model)
- Choose the anchor ONLY from the supplied candidate list. Never invent or guess a date.
- Emit exactly:
  `{anchor_type, anchor_date, read, action_bias, why}` where
  `anchor_type` ∈ the strings in §1, `read` ∈ {support, reclaim, at-anchor, hugging, supply},
  `action_bias` ∈ {enter, add, hold, trail, avoid, exit}, `why` = one line ≤ 20 words.
- If overriding the engine's auto anchor, state which supplied candidate you chose and why (§2 rule).
- If no valid anchor exists (only `fallback`, or ASM/GSM name, or only a circuit bar): output
  `"no actionable anchor"` — do not force a read.

## 8. TENSION WITH CURRENT ENGINE (implementer note, not for the model)
- Engine `avwap_auto_anchor` currently detects ONLY `earnings-gap`, `breakout`, `swing-low`,
  `fallback`. `ipo-listing`, `high-volume`, `block-deal`, `post-circuit` in §1-2 are Shannon/India
  extensions NOT yet emitted — until added, they will simply never appear as candidates (safe).
- Threshold mismatch: this doc's §2 rank-1 says earnings-gap vol > 2×; the ENGINE gates at vol > 1.5×
  and only adds a significance bonus at > 2×. The engine is the validator, so a 1.5-2× gap still
  qualifies as `earnings-gap` — treat > 2× as "high-conviction," not a hard gate.
- Engine has no ASM/GSM, circuit, or delivery% awareness — those §4-5 filters live in this lens and
  the context_pack, applied by the model, not the auto-anchor.
