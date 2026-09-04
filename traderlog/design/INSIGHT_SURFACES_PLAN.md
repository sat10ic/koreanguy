# TraderLog insight surfaces — execution plan

Status: owner directed planning and implementation on 2026-08-25.

## Product job

Turn the captured trader corpus into evidence-backed views of what is attracting
attention, how price behaved afterwards, and which repeatable methods traders
actually demonstrate. The product remains descriptive: it records public
statements and market data; it does not recommend trades or infer unstated
levels, direction, or results.

## Language guardrails

- Multiple traders naming a symbol is **co-attention**, not consensus, unless
  every included post has an explicit, compatible direction.
- Price after a mention is **tape after mention**, not proof that the author was
  right. Bare mentions have no direction and receive no win/loss label.
- Every derived statement links to the source posts and reports its eligible
  sample and missing-data count.
- Missing prices, classifications, directions, levels, and events remain
  unknown. They never become zero, neutral, or inferred.

## Information architecture

- **Radar** replaces Ideas. Modes: Symbols, Themes, Setups.
- **Playbooks** replaces Library. Modes: Methods, Timing, Audit.
- **Market** retains market internals and adds Market chorus.
- Symbol, trader, and position pages remain the evidence drill-downs rather
  than becoming more top-level tabs.

## Ordered feature plan

### INS-1 — Symbol co-attention radar

**User question:** Which NSE symbols are being independently discussed, by
whom, and how tightly in time?

**Inputs:** `posts`, the JSON array stored in `post_class.symbols`, and the
`daily_prices` symbol universe.
Use classified `trade_event`, `watch_idea`, and `theme` posts; keep each kind
visible. Do not treat `education`, `breadth`, or `noise` as scouting mentions.

**Output:** symbol, validated/unvalidated state, distinct traders, mention
count, first/last mention, strongest rolling seven-calendar-day cluster, and a
chronological evidence rail of source posts. Rank validated symbols by cluster
trader count, then recency; never by an invented composite score.

**Acceptance:** deterministic endpoint and UI; every displayed mention has a
post ID and source URL; author de-duplication is handle-normalized; symbols with
missing NSE coverage are separated from the ranked result; 1920×1080 has no
document overflow or console/network error.

**Kill condition:** if post-level symbol precision is too poor to make the
ranked list trustworthy, ship a review queue/coverage report before ranking.

### INS-2 — Tape after mention

**User question:** What did price do after a symbol first entered the corpus or
a new co-attention cluster formed?

**Inputs:** INS-1 clusters and `daily_prices` OHLC rows.

**Output:** explicitly labelled anchor session, base field/value, and forward
close returns at 1, 5, 10, and 20 trading sessions with eligible `n` and missing
counts. To avoid look-ahead, a pre-open post may anchor to that session's open;
an intraday/after-close post anchors to the next available session's open. The
implementation spec must lock and test the exact IST session boundary before
shipping.

**Acceptance:** returns recompute from displayed prices; market holidays use
actual price sessions, not calendar offsets; missing horizons are null; no
right/wrong or win/loss label appears without explicit direction and trigger.

**Kill condition:** if timestamp or price-session alignment cannot be made
unambiguous, show raw before/after prices only and omit return percentages.

### INS-3 — Theme rotation

**User question:** Which trader-described themes are emerging, broadening, or
going quiet?

**Inputs:** materialized `themes` plus their cited posts and validated symbols.

**Output:** theme timeline, distinct traders, constituent symbols, new versus
repeat mentions, and recent acceleration/deceleration described as counts over
fixed windows. Theme aliases require an evidence-backed canonical mapping.

**Acceptance:** every theme label resolves to cited posts; aliases are visible;
window counts include denominators; a single prolific trader cannot masquerade
as breadth.

**Dependency:** repair classifier materialization so `themes` is populated.

**Kill condition:** if alias precision is weak, show exact extracted labels
without merging them.

### INS-4 — Setup board

**User question:** Which explicitly named setups are forming or being traded?

**Inputs:** `post_class.play_type` for `trade_event`/`watch_idea`, source posts,
vision evidence where present.

**Output:** setup lanes (`ep`, `momentum_burst`, `breakout`, `pullback`, `vcp`,
`ipo_base`, `swing_range`) with symbol, trader, age, status, and cited evidence.
`unclear` stays visible as coverage debt and is never auto-filled from a
trader's historical style.

**Acceptance:** only contract-enum setup labels; all items cited; setup coverage
and unclear count shown; no lane ships as decorative emptiness.

**Dependency:** improve current play-type coverage against golden fixtures.

**Kill condition:** if labelled coverage remains too small, keep this as a
coverage report rather than a scouting screen.

### INS-5 — Level book

**User question:** Which exact prices have traders publicly marked for a symbol?

**Inputs:** text-stated levels and `post_media.vision_json.annotated_levels`.

**Output:** per-symbol level rail grouped by entry, stop, target, support,
resistance, and other contract-backed kinds; price, date, trader, source image
thumbnail, transcription confidence, and superseded/current state. Conflicting
levels coexist; they are evidence, not a merged target.

**Acceptance:** every number cites a post and the precise image/text evidence;
unreadable images contribute nothing; duplicate levels retain distinct authors;
no average or inferred zone is created.

**Dependency:** vision completion and a contract extension for any new level
kinds before code.

**Kill condition:** if vision precision cannot be audited, show thumbnails and
transcribed labels without a numeric aggregate.

### INS-6 — Playbook evidence

**User question:** What repeatable process does each trader demonstrate across
many posts and trades?

**Inputs:** education posts, trade events, reconciled positions, exact recurring
phrases and stated numbers.

**Output:** a small set of candidate rules per trader, each with supporting
posts, counterexamples, eligible `n`, and confidence. Exact phrase families are
shown before any LLM-authored summary. A candidate rule is not promoted to a
playbook until the evidence threshold defined in its implementation spec is met.

**Acceptance:** no uncited rule; at least one counterexample search per rule;
sample size adjacent to every rate; user can open the underlying posts.

**Dependency:** education materialization and substantially more reconciled
positions.

**Kill condition:** if phrase mining produces generic or contradictory rules,
ship a searchable vocabulary/evidence index instead of summaries.

### INS-7 — Timing fingerprints

**User question:** Where does each trader act relative to the observed move?

**Inputs:** cited entry/add/trim/exit events plus `daily_prices`.

**Output:** entry timing relative to an explicitly defined setup trigger,
holding-session distribution, first-trim timing, and stop-to-cost timing. Show
distributions and raw observations, not a single quality score.

**Acceptance:** computations use trading sessions; every event traces to a
position and post; medians include `n`; missing trigger definitions exclude the
observation rather than becoming zero lag.

**Dependency:** reconciled event coverage and a validated trigger definition.

**Kill condition:** if triggers are rarely explicit, limit the feature to hold
and trim timing, which remain directly observable.

### INS-8 — Claim audit

**User question:** When a trader states a result, how does that claim compare
with the archived event record and market tape?

**Inputs:** stated result text, cited entries/exits, and `daily_prices`.

**Output:** claim, independently reproducible tape calculation, method, coverage,
and discrepancy explanation. Deletions remain visible evidence. No composite
credibility score in the first version.

**Acceptance:** compare only like-for-like periods and explicit direction;
corporate-action or missing-price cases are unknown; calculations are
reproducible from displayed inputs; discrepancies are neutral audit findings.

**Dependency:** reliable reconciliation, direction, and corporate-action policy.

**Kill condition:** if the comparison cannot distinguish stated partial exits
or adjusted prices, display the claim beside the tape without judging it.

### INS-9 — Market chorus

**User question:** How are tracked traders describing the current market, and
where do their public stances differ?

**Inputs:** `breadth_notes`, source posts, `regime_daily`/`breadth_daily`.

**Output:** recent stance timeline, counts of risk-on/risk-off/neutral by
distinct trader, cited dissent, and comparison with the existing XP/MBI model.
This comparison measures agreement with one model, not market-reading skill.

**Acceptance:** every stance cited; counts use distinct traders; no stance is
inferred from silence; existing Market model caveat remains adjacent.

**Dependency:** repair `breadth_notes` materialization.

**Kill condition:** if stance coverage is too sparse, keep a chronological
commentary rail rather than drawing an aggregate.

## Delivery order

1. **Now:** INS-1 backend contract and deterministic derivation, then its Radar
   UI at 1920×1080.
2. **Next:** INS-2 price alignment and tape-after-mention, added to the same
   Radar symbol view.
3. **Data repair:** materialize themes, education, breadth notes, and improve
   setup labels; then ship INS-3, INS-4, and INS-9 only where coverage passes.
4. **Vision:** complete audited chart transcription, then INS-5.
5. **Reconciliation depth:** after event coverage is credible, ship INS-6 and
   INS-7.
6. **Audit last:** INS-8 after claim/tape comparability and corporate-action
   handling are explicit.

## Not doing

- No composite credibility, hotness, consensus, or trader-quality score.
- No recommendation, target aggregation, or inferred direction.
- No decorative charts or empty future panels.
- No new top-level tabs for Levels, Timing, or Claims; they are drill-down modes.
- No dependency on W9's unvalidated attention score for the first Radar.

## Verification checkpoints

- After INS-1 backend: focused unit/API tests plus `python traderlog/run_checks.py`.
- After each UI slice: Vite build and a live 1920×1080 browser pass with zero
  overflow, console errors, and failed requests.
- After any extraction/prompt change: the full golden fixtures and pytest suite.
- At every close: update `TASKS.md`, the relevant contracts/wireframe, completion
  handoff, and `MODEL_WORK_LOG.jsonl` with executor and orchestrator records.
