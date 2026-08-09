# sat10ic os — UX Patchwork and Horizon Framework Review

**Date:** 2026-07-13  
**Verdict:** **FAIL — the current patchwork is not a shippable UX overhaul.** The application builds and its component tests pass, but the live interface is visually broken and the compatibility layer masks an unfinished token migration.

## Scope and evidence

### Standing integration constraint

Gemini's recent working-tree changes are user-owned. Review them for UX fit and preserve functional/data improvements; do not overwrite them wholesale. Presentation changes that conflict with the frozen Round-4 source must be reconciled explicitly and verified in the live application.

This review separates three questions:

1. Does the current code compile and pass its existing automated checks?
2. Does the live product reconcile to the frozen Round-4 design source?
3. Which ideas in `Horizon_Quant_Frameworks_Consolidated.md` fit sat10ic os without turning it into a generic prediction engine?

Evidence used:

- Frozen design source: `design/bakeoff/round4/debate_merged_light.html`
- Current v5 application and styles in `desk/src/`
- Current correction and craft-review documents
- Git history for the patch waves
- Live browser captures at 1440 px for MARKET and SCANNERS
- Frontend test/build result
- `scripts/desk_gate.py`
- Supplied Horizon consolidated document

## Executive finding

**Certain:** The patchwork is incomplete. Commit `c3c859d1` added a compatibility stylesheet and review material; commit `b2d4ca9f` added a handoff for later waves rather than implementing those waves. The repository's own correction plan describes Waves B–D as pending.

**Certain:** The compatibility shim is still load-bearing. There are 71 live references to legacy aliases such as `--gap-*`, `--radius-*`, and Alpha aliases. That means the shim did not complete the migration; it made incomplete screens renderable enough to continue.

**Certain:** The live SCANNERS capture contains large black regions across the shell and content. The MARKET capture shows mismatched serif, sans-serif, and monospace typography; clipped ticker content; weak information hierarchy; and a crowded two-row header. These violate the light Round-4 source and are visible product defects.

**Certain:** The current screenshot harness cannot certify the app. `desk/screenshot-tabs.mjs` points at port 5174 and path routes such as `/shortlist` and `/alpha`, while the live app uses port 5173 and query navigation such as `?tab=ALPHA`. A green result from that harness is not evidence that the real tabs render correctly.

**Certain:** Existing frontend checks are necessary but insufficient: 37/37 component tests passed and the production build completed, while the live UI remained broken.

**Certain:** The repository gate fails because `MarketTab.v5.css` contains raw `#000`, contrary to the frozen v5 token rule. The gate also reports protected scanner-file changes in the dirty working tree; those need separate ownership review and must not be silently folded into a UI fix.

## What the patchwork did well

- It restored enough token aliases to prevent widespread unresolved-variable failures.
- It retained working application data and component behavior: the test suite and production build pass.
- The MARKET screen attempts a beginner workflow, a one-sentence verdict, a single decision question, and explicit daily risk law. Those are directionally correct product ideas.
- The SCANNERS screen groups practitioner methods rather than presenting one undifferentiated scan list.

These are salvageable product decisions, not evidence that the visual system is finished.

## What went wrong

### 1. A compatibility patch was treated as a design completion

The shim reintroduced legacy names rather than migrating each screen to the frozen primitives, semantic tokens, and component tokens. This creates a false sense of completion and lets each tab retain its own visual dialect.

### 2. Verification tested code health, not the user experience

The build and tests do not check black backgrounds, clipped tickers, mixed typography, empty card states, hierarchy, beginner comprehension, responsive behavior, or consistency with Round 4. The broken screenshot harness further weakens the claimed visual gate.

### 3. The shell is not treated as one designed component

Brand, status pills, ticker tape, date controls, search, mode toggle, update action, navigation, freshness and workflow rail compete for attention. The result is a header that feels assembled from patches rather than designed as a stable product frame.

### 4. Typography is uncontrolled

Serif display type, small monospace labels, uppercase sans-serif controls and dense body copy are mixed without a coherent role system. Small explanatory text is difficult to scan, while decorative headings receive disproportionate emphasis.

### 5. Beginner mode is mostly additive copy

The interface adds explanations but does not progressively disclose complexity. A beginner still sees dense regime acronyms, setup taxonomy and risk rules simultaneously. Beginner mode should change hierarchy and defaults, not merely add paragraphs.

## Required recovery sequence

This should be a reconciliation pass, not another CSS patch wave.

1. **Repair the visual test harness first.** Use the real port and query-tab URLs; capture MARKET, SCANNERS, SHORTLIST/SS, DEBATE, ALPHA, POSITIONS and JOURNAL at desktop and narrow widths. Fail on page exceptions, black/transparent shell regions, missing primary content and horizontal clipping.
2. **Rebuild the shared shell against Round 4.** Consolidate brand/status, navigation, controls and freshness into a stable hierarchy. Remove duplicate or competing bands and fix ticker overflow deliberately.
3. **Establish one typography role map.** Map display, section, body, label, numeric and code/data roles to the frozen type tokens; remove per-screen font inventions.
4. **Migrate screen by screen off the shim.** Start with MARKET and SCANNERS, then SHORTLIST/SS, DEBATE, ALPHA, POSITIONS and JOURNAL. For each screen, replace legacy aliases with v5 tokens and visually compare with the locked source before moving on.
5. **Design honest data states.** Every data region needs loading, populated, empty, stale and failed states. Blank cards are failures unless the empty state explains why and what happens next.
6. **Make Beginner a true information mode.** Default to conclusion, why it matters, what to do next, freshness and risk. Put formulas, model diagnostics and dense evidence behind Expert expansion.
7. **Remove the compatibility shim only after its consumer count reaches zero.** Do not delete it early and do not certify the design while it remains load-bearing.
8. **Run the full gate and a cold visual audit.** Tests, build, token lint, contrast, reduced motion, keyboard flow, responsive captures and real-data smoke checks must all pass.

## Horizon ideas worth incorporating

The supplied document is most valuable as a discipline for **ranking, regime context, promotion and decay monitoring**—not as a reason to make short-horizon price predictions the centre of sat10ic os.

### Adopt now

#### A. Multiple-testing-aware experiment promotion

Add experiment lineage and the number of related trials to the Alpha Lab. Report a Deflated Sharpe Ratio or equivalent trial-aware score beside ordinary walk-forward metrics. This directly addresses research selection bias when many factors, parameters and cohorts have been tried.

**Product placement:** Alpha Lab → Research Bench → experiment detail and promotion gate.

#### B. Structural edge thesis

Require each setup or factor thesis to answer, in plain language:

- Why should this edge exist?
- Who or what behaviour creates it?
- Why should it be active in the current Indian regime?
- What observation would show that it has stopped working?

This makes EP/PEAD, IPO-base, long-base Stage-2, pocket-pivot, VCP and reversal ideas testable rather than merely named chart patterns.

**Product placement:** setup registry, Debate Alpha Card and experiment specification.

#### C. Anti-overfit promotion gates

Before promotion, require:

- ablation: does removing a feature materially hurt the result?
- parameter plateau: does the edge survive nearby settings?
- explicit complexity penalty;
- untouched out-of-sample and live-shadow results.

**Product placement:** model registry and experiment gate. A model that fails remains labelled research/shadow.

#### D. Edge-health and decay monitoring

Add a live health view by setup, ranking model and regime using rolling expectancy/Sharpe, drawdown depth, time under water, trade-level drift and a performance cone. This is more useful than a static historical score because Indian market leadership and participation rotate.

**Product placement:** Alpha Lab → “Is the edge still working?” Default copy should say healthy, weakening, uncertain or broken and show why.

#### E. Failure memory, not just outcome memory

For every TAKE/WATCH/SKIP and experiment, record the failure category, evidence that was misleading, missing context and the distilled rule learned. Retrieve those failures alongside successful analogues so debate agents do not repeatedly rediscover the same mistake.

**Product placement:** decision memory and Debate comparable episodes.

#### F. Separate generator from evaluator

Let one agent propose a chart-behaviour thesis from price, volume, RS, ADR, event and theme context. A separate evaluator checks timestamp validity, contradictions, comparable episodes, regime fit and risk. The proposing agent must not score its own idea.

**Product placement:** debate orchestration. Deterministic tradability and risk controls remain authoritative.

#### G. Use HMM as regime context

Surface state persistence and transition probabilities, not a “tomorrow up/down” prediction. Use the regime state to alter ranking priors, preferred setup families and risk budget.

**Product placement:** MARKET regime explanation, ranking context and Debate Alpha Card.

### Defer or reject

- Do not optimise agents directly on raw returns; it invites unstable and risky behaviour.
- Do not allow autonomous model deployment or automatic sizing changes.
- Do not turn HMM states into standalone buy/sell signals.
- Do not add more model families until the experiment registry, point-in-time data and promotion gates are trustworthy.
- Do not import exact framework details visible only in the document's image appendix without separately extracting and verifying those images.

## Recommended product synthesis

The best sat10ic os interpretation is:

```text
Regime and participation context
→ ranked opportunity set
→ chart-behaviour thesis from parallel practitioner lenses
→ independent contradiction and analogue check
→ deterministic tradability and risk governor
→ human decision
→ path-dependent outcome plus failure memory
→ trial-aware, decay-aware promotion review
```

That preserves the user's intended centre of gravity: better regime detection, ranking and risk sizing, while giving the debate agents a richer chart-reading brain without granting them unbounded discretion.

## Done criteria for the UX recovery

The UX is not “done” until all of the following are true:

- all seven primary tabs render real data or an honest state on the actual live URL;
- no black voids, transparent shell failures, clipped primary controls or horizontal page overflow;
- typography and tokens reconcile to Round 4;
- zero live compatibility-shim consumers;
- screenshot harness exercises the real navigation contract;
- beginner mode passes a task test: a new user can explain the market state, identify the next action and understand why a stock is shortlisted without opening Expert mode;
- reduced-motion, keyboard, contrast, token, test and production-build gates pass;
- a final cold review is recorded with captures and known exceptions.

## Repair wave — 2026-07-13

**Status: UI repair PASS; repository-wide gate PARTIAL because unrelated protected scanner files remain modified.**

Implemented and verified:

- Replaced the invalid screenshot script with a real query-tab harness covering all seven tabs, configurable date/URL/viewport, settled fonts, disabled capture animation, console/page errors and page-level overflow detection.
- Made the shell canvas, type family, width and content shrink rules explicit; removed the touched raw colour violations.
- Fixed SCANNERS expanding to 1,955 px: practitioner columns now use zero-minimum grid tracks and long source/recipe text wraps. TradeTM, Arora/Strong Start and StocksGeeks lanes remain intact.
- Added informative, stable loading surfaces to DEBATE and SHORTLIST instead of blank space or a lone loading word.
- Coalesced concurrent identical debate reads and reused the shell's completed date-scoped debate payload in the main Debate tab. No response is cached after completion.
- Fixed Alpha Card memory retrieval crashing on mixed timezone-aware and legacy naive timestamps by normalising both to UTC. Added a regression test.
- At 390 px, the persistent beginner rail now yields to the tab-purpose guidance and all seven tabs pass the page-level overflow check. Wide tables remain locally scrollable rather than widening the page.
- Restarted the stale local API so the current CORS and Alpha code are the code actually serving the desk.

Verification evidence:

- Real 1,440 px browser captures: MARKET, SCANNERS, SHORTLIST, DEBATE, ALPHA, POSITIONS and JOURNAL — PASS, no page overflow or console/page error.
- Real 390 px browser captures: all seven tabs — page-width PASS after responsive repair.
- Frontend tests: 37/37 PASS.
- Frontend production build: PASS; existing bundle-size warning remains.
- Alpha memory regression suite: 6/6 PASS.
- Previously broken `/api/alpha/symbol/LENSKART?date=2026-07-10`: HTTP 200.
- Hardcode lint: PASS.
- Contrast gate: PASS.
- Locked-file gate: FAIL only because `scanner/candidates.py` and `scanner/gates.py` contain pre-existing/user-owned changes outside this UX repair. They were not modified or reverted in this wave.

Gemini fit assessment after repair:

- **Keep:** guided beginner flow, journal manual add-trade, position-origin/thesis handling, chart comparison, scanner hit loading, StocksGeeks lane and weekly-base scanner presentation.
- **Reconciled:** guided rail becomes non-persistent on phone; scanner lane layout now respects the frozen canvas; Debate shares the shell payload instead of multiplying reads; loading states use the Round-4 token/type language.
- **Not silently accepted:** Gemini's protected scanner-engine edits remain outside this UX certification until their owner reviews or explicitly includes them in a separate engine wave.

## Risks

- **Likely:** More local patching will increase visual inconsistency and make removal of the shim harder.
- **Certain:** Passing component tests alone will continue to miss the current class of UX failures.
- **Unverified:** The remaining tabs may contain defects more severe than MARKET and SCANNERS; the existing capture harness cannot establish otherwise until repaired.
- **Assumption:** Horizon concepts will be implemented over sat10ic's canonical point-in-time records rather than introduced as a parallel research data path.
