# Gemini execution handoff — beginner-first Manas system rebuild

**Status:** READY FOR EXECUTION — not yet implemented  
**Date:** 2026-07-13  
**Repository:** `C:\Users\satta\Downloads\koreanguy`  
**Product:** sat10ic os  
**Design source of truth:** `manas_os/design/bakeoff/round4/debate_merged_light.html`

**Binding Horizon integration source:** `manas_os/design/HORIZON_INTEGRATION_REQUIREMENT.md`. Gemini must implement its delivery order and acceptance tests as part of Wave 7. Horizon is a first-class product input, not optional research commentary.

**Binding false-negative/learning audit:** `manas_os/design/DECISION_LEARNING_FAILURE_AUDIT_2026-07-13.md`. RAIN and STALLION are mandatory regression fixtures. Gemini must repair the upstream selection, two-pass debate and decision-aware outcome loop; changing prompt prose alone does not close the audit.

**Binding Debate output contract:** `manas_os/design/DEBATE_ANALYSIS_OUTPUT_CONTRACT.md`. The primary result must be a structured chart thesis with trigger, structural invalidation, expected sequence, contradiction, relative behaviour and provenance. LLM analysis and deterministic execution validation are separate records joined by the API/UI; votes or `TAKE`/`SKIP` alone do not close this handoff.

## 0. The outcome, in one sentence

Turn the current collection of screens into one observable beginner workflow:

```text
understand the market -> prepare 20–30 names -> focus on 5–7 ->
watch a real Strong Start / reversal / continuation trigger ->
size mechanically -> receive and confirm a Telegram alert ->
manage the position -> journal process and outcome -> improve the system
```

The user must never need to infer whether the data, live loop, Telegram path, risk profile, debate, or journal is working.

## 1. Binding executor rules

Follow these rules exactly.

1. Read `manas_os/design/ORCHESTRATOR_PLAYBOOK.md` and `manas_os/design/EXECUTOR_PLAYBOOK.md` before changing code.
2. Work through the waves below in order. Complete and verify one wave before starting the next.
3. Do **not** git commit. The maintainer reviews and commits each wave.
4. Gemini's current working-tree edits are user-owned. Preserve useful behavior and reconcile it; do not replace whole files from an older revision.
5. Do not touch or revert the current changes/deletions in `manas_os/design/study/`.
6. Do not fold the existing changes in `manas_os/scanner/candidates.py` or `manas_os/scanner/gates.py` into this UX wave. They currently make the protected-file gate fail and require separate owner review.
7. Risk math remains server-owned. UI code may display server values but must not calculate stop, quantity, rupee risk, portfolio heat, or allowed risk.
8. Telegram remains paper-gated. Do not enable `agents.telegram_live`; do not create a graduation document; do not send a real message during testing.
9. Alpha/ML remains shadow-only. It must not change eligibility, stop, quantity, or portfolio heat.
10. Use only frozen Round-4 v5 tokens, radius tokens, shadow tokens and type tokens. No raw hex in v5 CSS. `--v5-ink-faint` is decorative only.
11. Every data region must have five explicit states: loading, populated, honest empty, stale and failed.
12. Every claim of completion requires live browser evidence, not only a build or unit tests.
13. At the end of every wave, update a single completion ledger named `HANDOFF_GEMINI_BEGINNER_MANAS_SYSTEM_REBUILD_2026-07-13_COMPLETED.md` with files, screenshots, payload evidence, tests, failures and remaining work.
14. Read and apply `manas_os/design/HORIZON_INTEGRATION_REQUIREMENT.md` in full. Do not call Wave 7 complete until every extractable Horizon framework has a canonical record, job, API, UI surface and test, or is explicitly marked blocked on primary-source/OCR verification.

## 2. Source doctrine that the product must preserve

These requirements come from the supplied Manas material:

- The system is primarily a **behavior and process system**, not a signal vending machine.
- Post-market work creates a broad focus universe of roughly 20–30 names. The next-session actionable list is only 5–7 names.
- A stock should usually be tracked before its Strong Start; Strong Start is not a same-morning chase generated from a fresh scan.
- Strong Start: open above the previous close, hold the previous close, then clear the previous day high after the opening has had roughly 2–3 minutes to establish itself. Early relative volume is supporting evidence.
- Busted/reversal: breach support, then reclaim the breach-bar high within the next 2–3 15-minute bars.
- Continuation and reversal mechanisms run in parallel. Manas is an execution overlay, not the only doctrine. TradeTM mechanisms and StocksGeeks IPO mechanisms remain parallel lenses.
- A beginner risks roughly 0.10–0.20% per trade and earns the right to scale only after a meaningful sample of trades. The supplied transcript specifically emphasizes survival and approximately 50–60 learning trades.
- Quantity is derived from account risk divided by stop distance. The trader must always know open risk.
- One or two failed trades in a poor environment is feedback to stop. Positive market and trade feedback permits sequential adds; do not begin fully invested.
- A new trade often needs 3–4 sessions to work. Do not interfere with it on day 0–2 without invalidation.
- Young Stage-2 / early-base names deserve room and can be managed on a closing basis around the chosen moving average. Older/extended names use partials and tighter management.
- A stopped-out leader remains a high-priority re-entry candidate if the thesis reforms.
- The journal records the planned reason, trigger, time, entry, stop, execution, end-of-day plan adherence, emotional interference and what the market was doing—not only P&L.
- The desired payoff comes from sitting for large winners. A mechanically high win rate or repeated 4–6% profit-taking is not the objective.
- The user should be able to build a chart library/deep-dive habit: prior force, correction, consolidation length, trigger and subsequent behavior.

Horizon framework ideas are subordinate to this doctrine. Use them for regime/ranking research, multiple-testing discipline, decay monitoring, failure memory and independent evaluation—not as a generic next-price prediction engine.

## 3. Audit verdict

**FAIL — the build is code-healthy but not yet a cohesive beginner trading system.**

### What should be kept

- Round-4 light visual direction and v5 token system.
- MARKET's plain-language verdict, one-question framing and visible daily risk law.
- Real ChartsMaze sectors/themes, broader indices, multi-horizon RS/returns, FII/DII and stock/theme/index comparison payloads.
- Deterministic risk one-writer and explicit refusals.
- Existing Strong Start focus list, morning setup records and paper-gated live FSM foundation.
- Existing chart drawer with daily/weekly candles, volume, EMA layers, HMM/RMV expert layers and stock/theme/index comparison.
- Manual journal add/edit/delete plumbing.
- Position coach, original-thesis record and manual execution boundary.
- Debate context pack's chart-behavior facts and Manas indicators.
- Free OpenRouter seats and free vision model configuration.
- Shadow-only Alpha Lab, model registry, memory and anti-overfit infrastructure.
- Honest states such as WARMING, NEEDS-DATA and no-plan refusals.

### P0 — must fix before calling this beginner-safe

| ID | Defect | Evidence | Required result |
|---|---|---|---|
| P0-1 | Risk is actionable before the beginner has confirmed capital and experience mode. | Active config has no risk profile/capital. `risk/plan.py` therefore defaults to aggressive, Rs 1,000,000 capital and 0.50–0.75% risk in RISK_ON/SELECTIVE. The live MARKET screen calls this “TODAY'S LAW.” | No non-zero quantity until capital and experience mode are explicitly saved. Default experience mode is LEARNING with regime risk 0.20% RISK_ON, 0.15% SELECTIVE, 0.10% DEFENSIVE and 0% NO_TRADE. |
| P0-2 | The visible workflow is not the real trader workflow and its date can lie. | `/api/flow/today?date=2026-07-10` returns `as_of=2026-07-13`; `flow_today()` ignores the query date. Its steps are data/regime/positions/setup decisions/order ticket, omitting preparation, 5–7 focus, live trigger, Telegram and journal. | Date-honest PREP, LIVE and REVIEW workflows with one current action and visible system readiness. |
| P0-3 | Live operation is backend-only and currently broken. | The desk does not call `/api/live/status`, `/api/live/quotes` or `/api/live/stream`. `/api/live/status` returned HTTP 500 after about 32.8s in the audit. | Live status, quotes, FSM state, Telegram mode, last heartbeat and failures visible in the desk. Read endpoints respond below 500ms from a warm local DB. |
| P0-4 | Blank cards are caused by blocking endpoints, not merely CSS. | `/api/desk/focus?date=2026-07-10` took about 40.6s. MARKET lower content remained loading/absent in browser captures. | Persist the nightly focus result and make the read endpoint read-only and fast; render timeout/failure separately from empty. |
| P0-5 | Trade Plan blocks its safety-critical answer on expensive optional context. | `TradePlanTab` uses one `Promise.all` for signal guide, full debate, checklist evaluation and checklist catalog. The screen stayed “Loading trade plan…” although `/api/desk/signal-guide` itself returned immediately. | Render the deterministic plan/refusal first; stream or progressively add debate, checklists and chart evidence afterward. |
| P0-6 | Strong Start execution semantics are conflated. | Current live confirmation waits for first 15 minutes, OR-low/VWAP hold, <=33% gap fill and projected RVOL >=2. The supplied Manas entry is the prior-day-high break after roughly 2–3 minutes; the 15-minute bundle is an added conservative confirmation, not the same trigger. | Represent `MANAS_EARLY_TRIGGER` and optional `CONFIRMED_15M` as distinct states. Never label the second as the first. |
| P0-7 | No live Busted/reversal state machine exists. | Search of `manas_os/live` and `manas_os/alerts` found no reversal/busted execution path. | Add a replayable paper-only Busted FSM and Telegram event path, parallel to Strong Start. |
| P0-8 | Mobile beginner use is not viable. | At 390px, DEBATE and ALPHA remained tiny loading shells after 9–11s; content was visually compressed to an unreadable narrow strip. | Every primary beginner task usable at 390px with readable text, no page overflow and no hidden primary action. |

### P1 — cohesion and comprehension defects

| ID | Defect | Required result |
|---|---|---|
| P1-1 | Beginner navigation exposes seven peer tabs, including research Alpha, with no phase hierarchy. | Keep route keys stable, but make the beginner navigation task-based: TODAY, PREPARE, WATCH, DECIDE, MANAGE, REVIEW. Place Alpha Lab and raw scanner construction under Expert/Research. |
| P1-2 | SCANNERS opens with a wall of practitioner methods and source citations. | Beginner sees three jobs: find strength, find reversals, find event/IPO bases. Advanced presets and citations expand on demand. |
| P1-3 | SHORTLIST mixes a broad personal watchlist, Alpha, Debate and Strong Start without enforcing the 5–7 next-session focus. | Separate Broad Focus (20–30) from Tomorrow/Live Focus (5–7). Show why each name is present, how long tracked, execution lens, readiness and invalidation. |
| P1-4 | DEBATE payload has 32 symbols while the workflow says only 4 displayed setups require review. | Beginner queue contains only the governor-approved/current-focus decisions. User-pushed and historical names move to a secondary queue with explicit provenance. Denominators must agree. |
| P1-5 | Vision review happens only after the text chair has already selected TAKE finalists. | Run chart observation before thesis synthesis for every governed candidate/focus name; feed the observation to independent thesis and evaluator roles. |
| P1-6 | The chart “brain” is hidden behind layers and lacks the full decision sequence. | Default beginner chart workspace shows W/D plus honest intraday availability, EMA10/21/50, volume character, RS/theme/index behavior, ADR, setup age and annotated trigger/invalidation. |
| P1-7 | Position origin/thesis and Telegram mirror are Expert-only. | Beginner position card shows “why I own this,” invalidation, today’s action, days held, young/old state, next review and latest alert state. Advanced evidence stays collapsible. |
| P1-8 | Journal form is transaction-oriented, not process-oriented. | Capture plan, trigger time/type, market regime, adherence, emotion/interference, day-0–2 interference, exit reason, re-entry state and screenshot/chart-review links. |
| P1-9 | Journal modal does not close with Escape. | Escape closes it and restores focus to the Add Trade button. Add focus trapping and accessible dialog semantics. |
| P1-10 | Beginner text is too small and mixes display serif, mono labels and dense body copy. | Essential explanations use the frozen readable body role; mono is limited to numbers/status/source metadata. No essential copy uses faint ink. |
| P1-11 | Loading can continue indefinitely without an owner or recovery action. | At 8s, replace generic loading with the named dependency, elapsed state and Retry/Continue-without-optional-evidence action. |

### P2 — future edge loop

- Alpha Lab is correctly shadow-labelled but currently has no registered models/experiments in the audited payload.
- Memory exists, but the beginner workflow does not visibly close decision -> outcome -> lesson -> next comparable decision.
- Setup health needs trial-aware promotion, rolling decay, failure categories and regime-conditioned evidence.
- HMM should remain regime context. Do not present it as a next-day direction prediction.

## 4. Target beginner information architecture

Do not rename backend tab keys. Add a beginner task layer over the existing routes.

| Beginner job | Existing route(s) | Default content | Exit condition |
|---|---|---|---|
| TODAY | MARKET | System readiness, market posture, open-position actions, one next step | User can say whether to press, be selective or sit out |
| PREPARE | SCANNERS | Broad focus construction, grouped into strength / reversal / event-IPO | 20–30 tracked names with reasons |
| WATCH | SHORTLIST | Tomorrow/live focus of 5–7, chart behavior, trigger state and alert readiness | Every focus name is armed, deliberately unarmed or removed |
| DECIDE | DEBATE + TRADE PLAN | Chart observation, practitioner theses, contradiction, deterministic plan/refusal | TAKE/SKIP/WATCH is logged |
| MANAGE | POSITIONS | Open risk first, position instructions, invalidation and next review | Every position acknowledged |
| REVIEW | JOURNAL | Plan adherence, market feedback, mistakes, lessons and re-entry candidates | Daily review complete |
| RESEARCH | ALPHA | Shadow evidence, experiments, failures, model health and promotion gates | Expert-only; never blocks daily workflow |

The left workflow rail must reflect these jobs and the current session phase. It must not repeat every tab.

## 5. Required canonical records

Use additive migrations only. Reuse existing tables where possible.

### Trader profile

Add one canonical record with:

- `account_capital`
- `experience_mode`: `LEARNING | STANDARD | AGGRESSIVE`
- `profile_confirmed_at`
- `completed_trade_count`
- `monthly_risk_budget_pct`
- `monthly_risk_used_pct`
- `drawdown_from_month_start_pct`
- `paper_mode`

Until `account_capital > 0` and `profile_confirmed_at` exists, server sizing returns a refusal reason `trader profile incomplete` and quantity zero.

For `LEARNING`, use fixed regime risk: RISK_ON 0.20%, SELECTIVE 0.15%, DEFENSIVE 0.10%, NO_TRADE 0%. Do not silently graduate the user. Graduation is a manual choice after at least 50 resolved trades; the UI may show eligibility but cannot change it.

### Focus membership

Each focus record must distinguish:

- `broad_focus` versus `session_focus`
- date added and sessions tracked
- source lens: TradeTM mechanism, Manas overlay, StocksGeeks IPO, user, Alpha shadow
- setup hypothesis
- trigger type
- armed/unarmed reason
- invalidation
- theme/sector and comparison benchmark
- readiness state

Enforce 5–7 as the default `session_focus` UI cap. An expert can view overflow but must explicitly replace a name to arm more than seven.

### Live execution state

Persist setup-specific state, not one generic label:

```text
PREPARED
-> OPEN_QUALIFIED
-> MANAS_EARLY_TRIGGER
-> ALERTED_PAPER
-> USER_CONFIRMED | USER_SKIPPED | EXPIRED
-> CONFIRMED_15M (optional evidence state, not a prerequisite label for early trigger)
```

For Busted:

```text
PREPARED
-> SUPPORT_BREACHED
-> RECLAIM_WINDOW_1_OF_3
-> RECLAIMED_TRIGGER
-> ALERTED_PAPER
-> USER_CONFIRMED | USER_SKIPPED | EXPIRED
```

Record every transition with event timestamp, bar timestamp, price, evidence, reason and paper/live mode. Replay must be idempotent and point-in-time safe.

### Journal process fields

Add:

- `planned_setup`, `planned_trigger`, `triggered_at`, `executed_at`
- `regime_at_entry`, `theme_at_entry`, `focus_sessions`
- `plan_adherence`: `YES | PARTIAL | NO`
- `emotion_tags`, `interference_note`
- `day_0_2_interference`
- `market_feedback_after_entry`
- `young_old_state`
- `reentry_candidate`, `reentry_of_trade_id`
- `chart_snapshot_ref`
- `eod_review`
- `lesson_category`: clean hit, clean miss, right-process loss, wrong-process win

## 6. API contract changes

### Fix existing contracts

1. Change `GET /api/flow/today` to accept `date`. Use that date consistently in prices, regime, positions, setup decisions and response `as_of`.
2. Add `phase=auto|prep|live|review`; `auto` derives NSE session phase but historical dates default to review/replay, never current live state.
3. Make `/api/desk/focus` a persisted read. Nightly pipeline owns computation.
4. Make `/api/live/status` and `/api/live/quotes` read-only. Move schema creation to DB initialization/migration and remove DDL from hot GET paths.
5. Keep `/api/desk/signal-guide` independent and fast. Trade Plan must not wait for `/api/desk/debate`.

### Add observable contracts

- `GET /api/trader-profile`
- `PUT /api/trader-profile`
- `GET /api/live/fsm?date=YYYY-MM-DD`
- `GET /api/live/alerts?date=YYYY-MM-DD`
- `GET /api/live/readiness` returning Fyers auth, market phase, live-loop heartbeat, quote freshness, Telegram configured, Telegram dry-run, halt state and last error
- `GET /api/focus/session?date=YYYY-MM-DD`
- `PUT /api/focus/session` for explicit 5–7 membership changes
- Extend existing job/SSE events to include `dependency`, `step`, `elapsed_ms`, `rows`, `warning` and `failure`.

Do not add a second endpoint that recomputes risk or setup eligibility.

## 7. Debate “brain” design

The LLM layer must observe first and argue second.

### Step A — deterministic evidence packet

For each governed candidate or 5–7 focus name, create one point-in-time packet containing:

- weekly and daily OHLCV; 60/16-minute and 15-minute only when real intraday data exists
- EMA10/21/50 and optional 200
- volume dry-up, expansion, up/down volume asymmetry and pocket-pivot evidence
- ADR20 and stop distance in ADR units
- RS rank and stock versus theme, sector and Nifty MidSmall 400 behavior
- prior force, correction depth, base duration, contraction sequence and base count/age
- event context: earnings gap/EP/PEAD or IPO listing age/base state
- Strong Start or reversal path state when relevant
- regime, breadth direction, sector/theme leadership and concentration
- three successful and three failed point-in-time analogues when memory has them
- missing-data list and timestamp provenance

### Step B — chart observer

Run a low-cost multimodal observer on the weekly/daily pair before the debate seats. It returns structured observations only:

- observed phase and sequence
- supply/demand behavior
- base age and quality
- volume behavior
- stock versus group behavior
- plausible setup hypotheses, not one forced classification
- confirming evidence
- strongest contradiction
- what must happen next
- what would invalidate the read

It must not return quantity, stop, target, score or final verdict.

### Step C — parallel practitioner theses

Run independent lenses in parallel:

- TradeTM continuation/EP/PEAD/regime mechanisms
- TradeTM reversal/failed-breakdown mechanisms
- Manas Strong Start / reversal / execution overlay
- StocksGeeks IPO-base mechanism when listing context qualifies

Do not slot every name into Manas Strong Start. Do not use one generic “momentum” prompt for all four.

Each thesis returns:

- `thesis`
- `expected_sequence`
- `trigger`
- `invalidation`
- `management_template`
- `evidence_used`
- `evidence_missing`
- `contradiction`

### Step D — independent evaluator

A different model/process evaluates timestamp validity, setup/regime fit, contradictions, analogue outcomes and whether the thesis described the actual chart. The proposal model never grades itself.

### Step E — deterministic governor and human decision

The deterministic governor and risk plan remain final. The visible beginner card is:

```text
WHAT I SEE
WHY IT MAY WORK
WHAT MUST HAPPEN NEXT
WHAT PROVES ME WRONG
PLAN / NO PLAN
```

Expert expansion contains model seats, prompts, provenance, analogues and raw feature detail.

## 8. Execution waves

### Wave 0 — freeze evidence and protect Gemini/user work

Files:

- `manas_os/design/handoffs/HANDOFF_GEMINI_BEGINNER_MANAS_SYSTEM_REBUILD_2026-07-13_COMPLETED.md` (new ledger)
- `manas_os/desk/screenshot-tabs.mjs` (extend, do not replace working query-tab behavior)
- new Playwright journey test under `manas_os/desk/tests/` or existing project convention

Tasks:

1. Record `git status --short` and the protected-file gate failure in the ledger.
2. Capture all seven tabs at 1440x1000 and 390x1000 for 2026-07-10.
3. Add a read-only journey harness covering MARKET -> SCANNERS -> SHORTLIST -> DEBATE -> TRADE PLAN -> POSITIONS -> JOURNAL.
4. Record console/page errors, endpoint timings, visible loading after 8s, missing primary content, focus restoration and page/local overflow.
5. Never click a mutating TAKE, watchlist, position, journal save or Telegram action in baseline capture.

Pass:

- The harness fails on the defects listed in this document. A falsely green baseline is a failure.

### Wave 1 — reliability and honest loading

Primary files:

- `manas_os/db/` schema initialization
- `manas_os/live/quotes.py`
- `manas_os/api/app.py`
- `manas_os/desk/src/api.js`
- `manas_os/desk/src/App.jsx`
- `manas_os/desk/src/TradePlanTab.jsx`
- loading-state v5 primitives/CSS

Tasks:

1. Move `live_quotes` schema creation to initialization; GET paths perform no CREATE/ALTER.
2. Reproduce and eliminate the 32s `/api/live/status` failure.
3. Persist nightly focus results; `/api/desk/focus` must not recompute the universe in a GET.
4. Split Trade Plan loading: signal guide first; debate/checklist/chart independently.
5. Abort stale requests on tab/date change with `AbortController`.
6. Add timeout state at 8s with named dependency and retry.
7. Keep optional failures from blanking the primary decision.

Pass:

- Warm local p95: health <200ms, live status <500ms, focus <1s, signal guide <1s.
- Trade Plan renders plan/refusal even if debate is deliberately delayed 30s.
- No unbounded spinner.

### Wave 2 — trader profile and beginner risk gate

Primary files:

- additive DB migration
- `manas_os/risk/plan.py`
- `manas_os/api/app.py`
- new v5 trader-profile/onboarding component
- MARKET and TRADE PLAN presentation
- risk tests

Tasks:

1. Add canonical trader profile and APIs.
2. Add LEARNING profile exactly as specified in section 5.
3. Require explicit capital/profile confirmation before non-zero sizing.
4. Show “why this size” using server fields: capital, risk %, rupee budget, stop distance, final qty, open risk before/after.
5. Show monthly risk budget and drawdown brake.
6. Keep STANDARD/AGGRESSIVE available only behind an explicit expert confirmation; do not default to either.

Pass:

- Missing profile -> qty 0 and named refusal.
- LEARNING SELECTIVE -> 0.15% risk exactly.
- UI and Telegram display the same server quantity and rupee risk.
- NO_TRADE remains zero in every profile.

### Wave 3 — real daily workflow and task-based beginner shell

Primary files:

- `manas_os/api/app.py::flow_today`
- `manas_os/desk/src/App.jsx`
- `GuidedFlowRail.jsx`
- `TabPurposeHeader.jsx`
- shell/nav v5 CSS

Tasks:

1. Honor the requested date.
2. Return PREP, LIVE and REVIEW steps.
3. Make one current action visually dominant.
4. Add beginner labels TODAY/PREPARE/WATCH/DECIDE/MANAGE/REVIEW while preserving route keys and expert labels.
5. Move ALPHA to Expert/Research in beginner mode.
6. Put live readiness and risk-profile completeness before setup review.
7. Do not show “done for tonight” during a live session with armed or open states.

Pass:

- Historical 2026-07-10 response says `as_of=2026-07-10`.
- A novice can identify current phase, system readiness and next action from MARKET without opening another tab.
- Mobile has a compact phase strip, not a compressed desktop rail.

### Wave 4 — broad focus, 5–7 session focus, Strong Start and Busted live paths

Primary files:

- focus persistence/services
- `manas_os/alerts/live_fsm.py` or setup-specific sibling FSM modules
- `manas_os/live/session.py`
- `manas_os/live/confirmation.py`
- Telegram paper/reply modules
- SHORTLIST/WATCH UI
- live replay tests

Tasks:

1. Separate broad focus from 5–7 session focus.
2. Show tracking age and prevent same-day scanner hits from silently becoming Strong Start-ready.
3. Implement distinct Strong Start early trigger and 15-minute confirmation states.
4. Implement Busted reversal FSM using 15-minute bars and a maximum three-bar reclaim window.
5. Display live timeline per symbol: prepared, open qualified, trigger crossed, alert sent, reply, expired.
6. Add Telegram readiness, dry-run badge, halt state, last heartbeat and last error.
7. Telegram text includes setup, observed trigger, invalidation, server quantity/risk or explicit “not sized,” data time and paper mode.

Pass:

- Replay tests cover early trigger, failed open hold, late reclaim expiry, duplicate ticks, restart and stale bars.
- Busted and Strong Start can run in parallel without sharing the wrong state.
- No real Telegram network call in tests.

### Wave 5 — chart workspace and debate brain

Primary files:

- `manas_os/agents/chart_behavior.py`
- `manas_os/agents/context_pack.py`
- `manas_os/agents/vision.py`
- debate orchestration/prompts
- `manas_os/desk/src/ChartDrawer.jsx`
- `DebateTab.jsx`, `DebateLivePanel.jsx`, Trade Plan evidence area

Tasks:

1. Build the evidence packet from section 7 with timestamp tests.
2. Run chart observation before thesis seats.
3. Run parallel TradeTM, Manas and StocksGeeks lenses only where applicable.
4. Add independent evaluator and failure analogue retrieval.
5. Make the beginner card sequence-first, not model-seat-first.
6. Default chart comparison to visible for DECIDE/WATCH, with a plain sentence describing stock versus group behavior.
7. Show W/D and only show intraday intervals when real bars exist; otherwise show what data/provider is needed.
8. Remove fabricated council placeholder names; connecting state is neutral until real seats arrive.
9. Split debate into a gate-blind chart observer, teacher-specific execution lenses and a later deterministic risk critic. The observer never receives `PASSED`, `NEAR_MISS`, refusal reason or scanner grade.
10. Add persistent user theses with first mention, reiteration count, source/chart provenance, archetype hypotheses, trigger and invalidation. Repeated mention guarantees review and outcome tracking, never a trade.

Pass:

- Removing deterministic filter labels from a fixture does not remove the chart observer's ability to describe a visible VCP/flag/reversal sequence.
- Observer cannot output quantity/stop/target.
- Evaluator sees observer output, raw evidence and provenance.
- Beginner sees strongest contradiction before TAKE.
- RAIN remains a visible long-base/reversal thesis when the live risk layer blocks a 5.4% stop.
- STALLION reaches the IPO/StocksGeeks lane without requiring 200 sessions of history.
- A user-nominated symbol absent from `scan_candidates` receives an honest eligibility state, not a fabricated `PASSED` tier.

### Wave 6 — positions, journal and learning loop

Primary files:

- position/journal additive schema and APIs
- `PositionsTab.jsx`
- `LedgerTab.jsx`
- lessons/memory services

Tasks:

1. Put open risk and urgent actions before per-position detail.
2. Show original thesis, invalidation, young/old state, day held, today action and next review in beginner mode.
3. Add day-0–2 “give it time unless invalidated” state.
4. Add re-entry linkage for stopped-out leaders.
5. Extend journal fields from section 5.
6. Make right-process loss and wrong-process win visible categories.
7. Add manual lesson writing without bypassing source/decision IDs.
8. Fix Add Trade modal Escape, focus trap and focus restoration.
9. On close, prompt for plan adherence and market feedback before presenting performance statistics.
10. Resolve every TAKE, WATCH, SKIP, user thesis and gate block into the same path-dependent outcome shape; include false negatives and no-trigger cases.
11. Wire `alpha.resolver.resolve_all_outcomes` into the production nightly pipeline with run-card counts and failure isolation.
12. Replace undirected `outcome_r >= 1` model weighting with verdict-aware calibration by regime and archetype. A SKIP on +1R is a false negative; a TAKE on +1R is a true positive.
13. Generate lessons for false positives, false negatives, right-process losses and wrong-process wins. Do not train only on chair TAKE rows.

Pass:

- A manually entered trade, a setup-decision trade and a Telegram-confirmed paper trade all resolve into the same canonical journal shape.
- Future outcomes cannot leak into retrieved analogues.
- Nightly resolution changes the next debate's traceable analogue evidence; it never silently edits hard risk rules.
- Model/lens weights remain neutral while samples are thin and expose sample, calibration and last-updated state.
- Every acceptance test in `manas_os/design/DECISION_LEARNING_FAILURE_AUDIT_2026-07-13.md` passes.
- Journal can answer “Did I follow the plan?” independently of “Did I make money?”

### Wave 7 — Alpha Lab as future edge governance

Primary files:

- Alpha services/model registry/experiment records
- `AlphaLab.jsx` and CSS
- memory and outcome services

Tasks:

1. Execute the seven-step delivery order in `manas_os/design/HORIZON_INTEGRATION_REQUIREMENT.md`.
2. Keep Alpha out of the beginner daily path.
3. Add hypothesis-family lineage and structural edge thesis: why it exists, who is the other side, why active now and what means decay.
4. Record every related trial, including rejects. Implement DSR only from a separately verified primary formula/library; otherwise show `NOT IMPLEMENTED`, never an invented value.
5. Add factor IC/Rank-IC evaluation for 5/10/20-session horizons, with point-in-time and universe denominators.
6. Persist HMM transition matrix, full state probabilities, state age, persistence and asymmetric transition risk; never call it tomorrow-price prediction.
7. Add ablation, ±10/20% parameter plateau grids and versioned complexity state on top of the existing walk-forward/placebo/regime/subsample battery.
8. Add bounded generator/evaluator/selector orchestration: at most three variants, deterministic evaluator, independent OOS verifier and immutable failure memory.
9. Add live shadow observations, block-bootstrap performance cones, rolling-Sharpe percentile, drawdown depth/duration, time underwater and trade-level drift.
10. Add Alpha Lab research-loop, overfit-gauntlet and edge-health views plus compact MARKET/DEBATE linkage.
11. Build experiments from frozen decision-aware error cohorts. Do not treat raw next-day return or an undirected symbol outcome as model correctness.

Pass:

- No model can promote itself.
- No shadow model changes ranking/eligibility/sizing unless all promotion gates and human promotion are recorded.
- Empty model registry remains honest and useful rather than blank.
- Every acceptance test in `manas_os/design/HORIZON_INTEGRATION_REQUIREMENT.md` passes or is recorded as a named source-verification blocker.
- Generator cannot change the universe, costs, OOS period, fitness definition or risk rules.
- Trial count cannot exclude rejected sibling variants.
- Live health distinguishes normal variance, regime mismatch and possible decay without automatically changing deterministic size.
- No Alpha experiment begins from unresolved or verdict-agnostic labels.

### Wave 8 — final visual, accessibility and end-to-end certification

Primary files:

- all touched desk components/CSS
- screenshot/journey harness
- completion ledger

Tasks:

1. Reconcile every screen to Round 4; do not add a new visual dialect.
2. Apply one type-role map. Serif only for limited editorial headlines; Public Sans for essential prose/actions; IBM Plex Mono for numbers/status/provenance.
3. Remove remaining compatibility aliases only after consumer count reaches zero.
4. Verify keyboard shortcuts outside and inside dialogs.
5. Verify reduced motion, focus visibility, contrast and screen-reader labels.
6. Run the complete beginner journey with real local data and paper-only live replay.

Pass:

- All seven tabs + Trade Plan at 1440 and 390, beginner and expert, populated/empty/stale/failure fixtures.
- No black/transparent islands, clipped controls, missing primary content or page overflow.
- Essential beginner body copy is readable without zoom.
- The novice task test in section 9 passes.

## 9. Required novice task test

Give the tester no repository knowledge. They must answer and perform:

1. Is the system ready, stale or broken?
2. Is the market permissive, selective, defensive or no-trade, and why?
3. What is the one next action?
4. Which 5–7 stocks are being watched tomorrow, and why is each there?
5. Has a Strong Start/reversal merely been prepared, actually triggered, or expired?
6. Is Telegram in paper or live mode, and was the alert sent?
7. What invalidates the idea?
8. How many shares are allowed, what rupee risk does that represent, and why?
9. After entry, what should be done today and when is the next review?
10. In the journal, did the trader follow the plan even if the trade lost?

Pass only if all ten can be answered in beginner mode without opening raw JSON, reading source citations, interpreting model names or asking what a backend process is doing.

## 10. Mandatory verification commands

Run after every relevant wave:

```powershell
cd C:\Users\satta\Downloads\koreanguy
python scripts/desk_gate.py
python -m pytest -q manas_os/tests/test_live_fsm.py manas_os/tests/test_risk_gates_governor.py manas_os/tests/test_alpha_memory_gates.py

cd C:\Users\satta\Downloads\koreanguy\manas_os\desk
npm test -- --run
npm run build
```

Add and run new tests for the new contracts. Do not delete or weaken existing tests to get green.

Expected current baseline:

- Desk tests: 37/37 pass.
- Focused live/risk/alpha tests: 46 pass (the audit run ended with a Windows pytest temp-cleanup warning after successful tests).
- Production build: passes with an existing large-chunk warning.
- `desk_gate.py`: hardcode and contrast pass; locked-files fails because of pre-existing changes in `scanner/candidates.py` and `scanner/gates.py`.

## 11. Completion evidence format

For every wave, append:

```markdown
## Wave N completion

- Status: PASS | PARTIAL | BLOCKED
- Files changed:
- Existing user/Gemini changes preserved:
- API before/after timings:
- Tests and exact counts:
- Browser URLs exercised:
- Desktop screenshots:
- Mobile screenshots:
- Populated/empty/stale/failure states checked:
- Money-math provenance checked:
- Telegram paper gate checked:
- Known failures:
- Next wave allowed: YES | NO
```

Do not write “done” while any P0 remains open. Do not use build success as evidence of user-flow success.

## 12. Audit evidence retained for the maintainer

- `/api/flow/today?date=2026-07-10` returned `as_of=2026-07-13`, `current_step=setups` and six administrative steps.
- `/api/desk/market?date=2026-07-10` returned real indices, sectors, ChartsMaze sectors/themes, movers, deals, FII/DII and VIX.
- `/api/desk/focus-list?date=2026-07-10` returned two rows.
- `/api/desk/debate?date=2026-07-10` returned 32 symbols.
- `/api/desk/positions?date=2026-07-10` returned zero positions, while the shell's current-date workflow reported open-position state; this is another symptom of mixed dates.
- `/api/journal` returned zero trades.
- `/api/alpha/leaders?date=2026-07-10&limit=20` returned 20 shadow rows; Alpha overview returned zero registered models.
- `/api/desk/focus?date=2026-07-10` took about 40.6s.
- `/api/live/status` returned 500 after about 32.8s.
- Trade Plan navigation worked through `?plan=GROWW`, but the screen remained loading because optional debate/checklist reads were joined to the primary guide.
- Add Trade opened with seven fields. Escape did not close the modal in the live browser audit.
- At 390px, SCANNERS rendered a very long technical preset wall; DEBATE and ALPHA did not produce usable primary content within the audit wait.
- One browser capture briefly showed black shell regions during a stalled Trade Plan load; an immediate repeat rendered white. Treat this as intermittent/unverified until the state-matrix harness reproduces or disproves it.

## Risks

- **Certain:** Changing only CSS will not fix the blank screens; slow/blocked API composition is a root cause.
- **Certain:** Current default aggressive sizing is unsuitable as a silent beginner default.
- **Certain:** The current Strong Start live confirmation is a conservative 15-minute variant, not the supplied Manas early trigger.
- **Likely:** DDL in live quote read paths contributes to SQLite lock/failure behavior; prove this with a concurrency regression test before closing P0-3.
- **Likely:** More features added as peer tabs will increase black-box feel; new capability must attach to the task workflow above.
- **Unverified:** Fyers intraday coverage and token readiness were not available during this audit. Intraday UI must state actual coverage and never synthesize bars.
- **Unverified:** Real Telegram delivery was intentionally not tested because paper gating is binding.
