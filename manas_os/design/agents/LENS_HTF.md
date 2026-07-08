# LENS: High Tight Flag (HTF)

Source coverage: **THIN, now with named-doctrine context from `design/Feedback/*`** (added on
this pass — the original THIN verdict only checked `design/study/*`). No source in the study
folders teaches a High Tight Flag setup as its own methodology. The term appears exactly once
there, in `design/study/Tradetm/Creating a Setups Playbook for Smarter Trading_text.txt`, used as
a **rhetorical example warning against backtesting chart patterns** — not as a taught entry
system. A related, unnamed "Flag" case study with real numbers appears in `design/study/Tradetm/
Position Sizing_ The Key to Better Trading Results_text.txt`. The `design/Feedback/*` research
briefs (`manas v2 claude.md` Part B, `manas 2.0 - gpt 2.0.md`) separately reference the **named
O'Neil/Soreide HTF definition** and an **evidence-tier verdict for India** — real content, but it
is literature framing/evidence-grading, not a taught entry system either; it is added below as
its own subsection, clearly separated from the two study-folder passages. Do NOT let the debate
agent substitute the O'Neil/Minervini numeric thresholds as if they were validated on this
system's own data — they are cited here only as "what the global literature calls an HTF," and
the India verdict on them is explicitly weak/cautionary (see §1b, §2b below).

## 1. RECOGNITION markers (price/volume/chart, concrete) — **NEEDS SOURCE**

The only recognition-adjacent content available:
- The one direct mention (`Creating a Setups Playbook...`) treats "high-tight flag" purely as a
  *label* example: "A high-tight flag is just one variation [of a flag]... there are many other
  techniques where people trade similar patterns with different names." No entry criteria,
  no tightness definition, no run-up percentage or timeframe is given.
- The Position Sizing case study (Prakash Industries, entered 21 Aug 2023) describes the setup
  only as: "moving alongside the 10 EMA and now basing after decent results. Momentum Burst,
  Velocity trade, Flag, VCP — call it whatever you want" — the author explicitly treats the
  pattern *name* as interchangeable/unimportant, i.e. this source does not consider "HTF" a
  distinct, separately-defined pattern from VCP/momentum-burst.
- No specific price/volume markers (e.g. minimum prior run-up %, flagpole length, pullback depth,
  volume dry-up threshold) are stated anywhere in these sources for a "high-tight flag" as such.

**Everything else a debate agent would need for concrete HTF recognition (flagpole magnitude,
consolidation depth/duration, volume signature) is NOT SOURCED here — mark any such claim
NEEDS SOURCE if it surfaces in a debate transcript.**

### 1b. The named literature definition (from `design/Feedback/*` — cite as literature, not as
this system's validated rule)

- **`manas v2 claude.md` (Part B.2, "Flags & tight continuation")** gives the actual textbook
  definition the study-folder sources deliberately withheld: **high-tight flag (O'Neil/Soreide)
  = roughly a 90-100% price move in 4-8 weeks, followed by a shallow, tight flag/consolidation.**
  It is grouped with bull flags, VCP (volatility contraction), tight-range coils, and Darvas boxes
  as the same family of "flags & tight continuation" patterns.
- **`manas 2.0 - gpt 2.0.md` (Part B.1, evidence-quality ranking)** ranks **"High-tight flags /
  high-ADR discretionary momentum" as evidence tier 7 of 7 — the weakest formal evidence** of all
  setup families surveyed, explicitly described as "most operator-prone and regime-dependent; the
  'doubled in 8 weeks' names sit in the low-float tier."
- These two sources are literature/evidence-grading, not a taught step-by-step system — they
  supply the *name and magnitude* the study-folder sources lacked, but not entry triggers, stop
  rules, or a validated India backtest.

## 2. CONTEXT requirements — **NEEDS SOURCE**, with one caveat

- The `Creating a Setups Playbook` passage makes a *methodological* point relevant to context:
  "A flag forming as a follow-through to an early-stage EP setup will likely have a completely
  different outcome compared to one forming during a climactic move." This is the one
  concrete, sourced context rule available: **judge a flag/HTF-shaped consolidation by what stage
  of the move it's forming in** (early-stage/EP follow-through vs. late/climactic), not by the
  shape alone.
- No sector, liquidity, or regime requirements specific to HTF are given anywhere in the
  study-folder sources.

### 2b. India context/verdict (from `design/Feedback/*`)

- **The defining trait is itself the warning**: "the high-tight flag's defining trait (double in
  weeks) selects for the low-float / surveillance / operator tier where the tight stop is least
  reliable" (`manas v2 claude.md` — Part B.2, "Flags & tight continuation", Caveat).
- **Part B.3 comparative synthesis** groups HTF with IPO bases as "**likely overhyped /
  least-measured** — glamorous, promoted, survivorship-inflated, operator-prone" — the weakest
  category in the entire India evidence survey, contrasted directly against PEAD and momentum
  (ranked strongest).
- `manas 2.0 - gpt 2.0.md` (Executive Summary and setup table) independently reaches the same
  verdict: "flag/pennant trades are useful tactically, but with smaller sizing and stricter
  confirmation rules because their Indian evidence base is thinner," and recommends flag/pennant
  setups be sized at "half or quarter size relative to PEAD or liquid-stock reversal baskets."
- **Net effect for the debate lens**: these sources reinforce, rather than contradict, the
  study-folder's own skepticism-of-pattern-labels stance (§3 below) — independently, from a
  different angle (evidence-tier grading vs. anecdotal caution about backtesting patterns).

## 3. DISQUALIFIERS — **NEEDS SOURCE**

- No named disqualifiers for HTF specifically exist in these sources.
- The one usable, generalizable caution: the same author's broader argument (same file) is that
  claimed pattern "win rates" (e.g. "a flag has a 65% win rate") are unreliable without fixing
  the definition of the pattern, the definition of a win, and the stop-loss used — i.e. treat any
  claimed HTF statistical edge with skepticism rather than as a rule to act on.
- Reinforced independently by `design/Feedback/*` (§2b above): the low-float/operator-tier
  concentration and the weakest-evidence-tier ranking function as de facto disqualifying context
  even though neither Feedback source states a formal numeric disqualifier for HTF specifically.

## 4. GOOD vs BAD example (in words)

**Only concrete numeric example available** — Prakash Industries (Position Sizing doc), described
as a Flag/VCP/Momentum-Burst (author's own hedge on naming), NOT explicitly called an HTF by the
author, so use with caution as a proxy example only:
- Setup: stock moving alongside the 10 EMA, basing after decent results, uptrend not new
  (swing/short-term trade classification).
- Entry 21 Aug 2023. Tight stop variant: entry 92, stop 2% (~90.2, day low), position size 25%.
  Moderate stop variant: entry 94.4, stop 4% (~90.6), size 12.5%.
- Sell rule: sell 50% of the position when strong at 4R, trail the remainder using the 10 EMA or
  21 EMA depending on the stock's behavior.

No BAD example of an HTF/flag failure is present in either source.

## 5. Exit / failure notes

Only the Prakash Industries case gives exit mechanics, and it is a general trend-following
trail (10/21 EMA, partial at 4R), not an HTF-specific rule — cite it as generic momentum-trade
management, not HTF doctrine.

**Overall recommendation for the debate prompt** (updated with `design/Feedback/*` context):
present HTF to the debate agents as a thin-coverage lens whose one addition from the Feedback
briefs is a name/magnitude for the pattern (O'Neil/Soreide ~90-100% in 4-8 weeks) plus an
explicit India evidence-tier verdict — **weakest of the surveyed setup families, low-float/
operator-tier concentrated, sized down accordingly**. It should lean on the study-folder CONTEXT
rule (stage-of-move matters more than pattern shape), the general skepticism-of-pattern-labels
principle, AND the Feedback evidence-tier caution (§2b) together, rather than asserting specific
HTF price/volume thresholds this repo has not actually sourced.
