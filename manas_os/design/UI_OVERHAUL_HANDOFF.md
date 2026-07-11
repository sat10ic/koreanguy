# UI OVERHAUL HANDOFF — Claude/orchestrator entry point

Date: 2026-07-11  
Status: **AUDIT COMPLETE ENOUGH TO PLAN; FRESH RENDER BASELINE STILL REQUIRED BEFORE BUILD**  
Repo: `C:\Users\satta\Downloads\koreanguy`  
Branch/verified HEAD at audit: `emergent` / `9d717996`

This document is the controlling handoff for the UI-first work requested by the user. Read it
after `CODEX_HANDOFF.md` section 0 (PRODUCT MISSION). The old Q1 corpus-ledger executor was
stopped: **do the rendered UI baseline and approve this overhaul plan before resuming Q1-Q6.**

---

## 1. The actual goal (user-locked)

Make the shipped Manas OS a beautiful, dynamic, beginner-legible Indian swing-trading edge
workbench — not a reskinned admin dashboard.

- TradeTM is the context/operating backbone **and provides several native execution
  mechanisms**.
- Manas Arora/Strong Start is one parallel execution branch, not the only overlay.
- Stocksgeeks is another parallel specialist branch, especially IPO structures and MBI/breadth.
- After shared TradeTM context, every applicable source-supported mechanism runs independently;
  preserve provenance, evidence and disagreement before reconciliation.
- India-specific edge areas (EP, real catalyst-conditioned PEAD, IPO bases, Strong Start,
  persistent momentum, reversals, liquidity/circuits/regime) must be visible and honestly
  evidence-graded.
- Manual execution, deterministic money math, paper-first behaviour, freshness, traceability and
  regulated language remain hard constraints.
- The user must see work happening: downloads, stages, scans, agent branches, chart generation,
  watchlist mutations, failures and retries — without refreshing.
- Cheaper agents may do bounded mechanical reads/builds. Claude/orchestrator owns architecture,
  synthesis, source fidelity, code QC, rendered UX QC and final acceptance.

---

## 2. Evidence and audit limits

### Verified runtime facts

- Current API and repo matched at `9d717996`; `stale_build=false`.
- Latest real-data date: `2026-07-10`.
- Latest state: `SELECTIVE`, four-phase `Lack of Demand`, stance `CAUTION`.
- Current real-data shape: 26 pipeline stages, pool 237, actionable 0, one debate card, one
  shortlist/watchlist name, one open position and one journal trade.
- Scanner registry: 19 presets, 12 `LIVE`, 2 `BUILD`.
- Baseline: Python `650 passed, 1 known standing sector-downside failure`; desk Vitest `34/34`;
  desk production build clean.

### Verified structural facts

- `manas_os/desk/src/App.css` is 84 KB with about 680 selectors, 10 `!important` uses, 12 media
  rules and 12 animation declarations.
- Current JSX uses the generic `panel` idiom about 103 times, while there are only nine native
  `h1`–`h4` headings. There are about 239 `mono`/`font-mono` references and 35 literal `[B]`
  markers.
- Main components are monolithic: `MarketTab.jsx` ~1,184 lines, `DebateTab.jsx` ~983,
  `DeskTab.jsx` ~707, `ScannersTab.jsx` ~580 and `ChartDrawer.jsx` ~612.
- `App.jsx` polls pipeline status every three seconds but shows only a stage string. The MARKET
  `PipelineProgress` component fetches status once on mount, so its visible progress bar cannot
  advance while watched.
- MARKET's expert “Activity log” is a placeholder saying the full activity remains on the legacy
  feed; V4 does not deliver the promised live desk stream.
- Multiple primary tabs replace the complete surface with `Loading…` instead of preserving last
  confirmed data. Native `window.prompt` remains for position stop/quantity edits and shortlist
  removal reason.
- `tokens.css` defines the visual system as Helvetica/Segoe UI plus mono, 13 px body text, 11 px
  panel labels and `#666` faint text on `#141414`. That faint combination is only about 3.21:1
  contrast and is widely used at 10–11 px.
- The base `.panel` rule gives every section the same background, border, radius, shadow and
  padding. The first viewport is therefore structurally a stack/card system, contradicting the
  locked editorial-poster bar.

### Not yet verified

The in-app browser could not attach to `http://127.0.0.1:5174`; no fresh screenshots were
captured. Source proves structural debt, not final rendered gestalt. **Claude must not certify
visual claims from this document alone.** UI-0 below is mandatory before editing.

Two cheap read-only audit agents were attempted. Their repository reads were interrupted and
they returned no usable code-cited findings. Do not describe their work as an independent pass.

---

## 3. Verdict

### Preserve the product spine

1. Keep the workflow and behaviours: **MARKET → SCANNERS → SHORTLIST → DEBATE → TRADE PLAN →
   POSITIONS → JOURNAL**.
2. Keep freshness/offline/stale-build warnings, manual-execution boundaries and prominent
   paper-only refusal state.
3. Keep deterministic risk authorship: UI displays server values; it never invents stop, target,
   quantity or exposure.
4. Keep date replay, beginner/expert data availability, scanner builder/saved screens,
   watchlist mutation/event history, debate disagreement, weekly-first chart drawer, default
   10/21 EMA + purple-dot layers, urgent-position sorting, R thermometer and user-first journal.
5. Keep honest zero states: on the latest night, “0 actionable” must remain a valid useful answer,
   not be decorated into a fake opportunity.
6. Keep the existing API/data machinery unless the new visual behaviour requires a thin additive
   payload or the Q3 jobs/events layer.

### Replace the visual and interaction system

The current tool is function-rich but still aesthetically a compact terminal/card dashboard.
Most of the UI should be recomposed, not cosmetically patched.

#### P0 — blocks the desired product

1. **No actual live-work experience.** Polling a stage label and a one-shot progress fetch do not
   satisfy “watch it work.” Build persistent jobs/events and a streaming Live Work surface.
2. **No coherent visual hierarchy.** 103 panels and uniform border/radius/shadow treatment make
   evidence, verdicts, actions and secondary details compete equally.
3. **Teacher/mechanism hierarchy is wrong in UI.** SCANNERS groups owner cards and DEBATE groups
   model seats, but neither shows shared TradeTM context followed by parallel applicable
   TradeTM-native, Arora/Strong Start and Stocksgeeks execution mechanisms.
4. **Text dominates where evidence should be visual.** Setup-specific price/volume grammar,
   catalyst timelines, contraction/IPO-base shape, drift path and management state are not the
   primary language.
5. **Beginner mode is labels plus hiding.** Literal `[B]`, tiny captions, gloss-on-hover and
   tables still require the user to understand the system before the system teaches them.
6. **Full-surface loading destroys continuity.** Updating or navigating temporarily erases the
   answer the user was using.

#### P1 — high-friction/product-quality defects

- Tiny uniform typography; MANAS is 15 px and does not establish a premium product identity.
- Mono is used for prose, status and navigation rather than only numbers/time/code-like evidence.
- Faint small text fails an appropriate readability bar.
- Header is crowded: date, regime, XP, search, mode and update compete in one 56 px strip.
- Native prompts break the product illusion and provide weak validation/error recovery.
- MARKET contains a good verdict but then stacks law, choppy brake, funnel, stepper, evidence and
  expert blocks as separate panels rather than one composed market read.
- SCANNERS displays 19 presets as owner-card grids plus a wide result table; it does not teach
  when/why each mechanism belongs in the current Indian regime.
- SHORTLIST is a dense status/table implementation; confirmation, price story and next trigger
  are secondary.
- DEBATE is nearly 1,000 lines and remains model/text centric. Teacher mechanisms and source
  conflicts are not visual first-class objects.
- TRADE PLAN is functionally valuable but reads as a long form instead of a decisive manual
  execution ticket plus management contract.
- POSITIONS has strong safety ordering and R visuals, but card repetition, prompts and generic
  coach prose weaken it.
- JOURNAL has only one real trade. Large system-R&D tables can look authoritative despite thin
  evidence; the UI needs explicit maturity/sample-gap storytelling.
- Responsive CSS prevents some overflow, but it mostly collapses grids. It is not a deliberately
  designed mobile/tablet workflow.

#### P2 — maintainability/performance debt

- One 84 KB stylesheet and huge tab components make visual changes unpredictable.
- Repeated bespoke chips/panels/disclosures create inconsistency.
- Several independent fetches and polling paths lack one shared request/state model.
- Reduced-motion coverage names only a subset of animations; it should disable every nonessential
  transition/animation centrally.

---

## 4. Locked art direction

> **⚠ SUPERSEDED (2026-07-11) — type/colour thesis only.** The dark-charcoal/Barlow-Condensed
> "newspaper" thesis below is REPLACED by the round-4 LIGHT dense-terminal direction, now the
> design of record: warm off-white `#f7f6f2` canvas, ink ramp, teal/amber/green/red semantic
> accents, **Fraunces** display / **Public Sans** UI / **IBM Plex Mono** numbers-only. Source of
> truth: `manas_os/design/bakeoff/round4/debate_merged_light.html` + `desk/src/styles/tokens.v5.css`
> + `UI_BUILD_DIRECTION.md`. **What still binds from §4/§5:** the composition rules (one dominant
> question/visual/action, cardless-by-default, verdict-before-metrics, evidence-attached-to-visual,
> plain labels not `[B]/[E]`, motion-marks-change-once) and the interaction thesis (progressive
> work, spatial continuity, in-place evidence). Only the palette/type flipped dark→light. See §11.

### Visual thesis (SUPERSEDED — see banner above)

**An Indian market intelligence newspaper fused with a live research desk:** editorial,
evidence-led and decisive; dark charcoal canvas, warm readable type, annotated charts and
restrained live cyan — never a neon terminal or generic SaaS grid.

### Type and colour

- Bundle a licensed condensed display face (preferred: **Barlow Condensed**) for product name,
  market verdicts and mechanism names.
- Use **Inter** or an equivalent bundled neutral sans for prose and controls.
- Use **JetBrains Mono** or the existing mono stack only for prices, time, R, quantities and
  compact evidence tables.
- Core palette: near-black charcoal, warm off-white, muted slate; cyan is system/live state;
  amber is caution; green/red are market/risk outcomes; purple is reserved for agent/vision
  interpretation. Avoid decorative gradients except a very restrained state wash.
- Minimum 14 px readable prose and WCAG-AA contrast for ordinary text. Do not use `--ink-faint`
  for essential copy.

### Composition rules

- One dominant question, one dominant visual and one primary action per screen state.
- Default to cardless sections, rails, bands, tables and annotated canvases. A card is allowed
  only when it is the actual interactive object (candidate, position, saved scan).
- Verdict and next action appear before metrics. Evidence is attached to the visual that proves
  it, not separated into a legend/card farm.
- Replace `[B]`/`[E]` markers with plain labels such as “Why this matters” and “Evidence & method.”
- Motion marks a real change once, then holds. Never animate P&L, stop, target, size or verdict.

### Interaction thesis

1. **Work arrives progressively:** stage rail fills, completed events insert, artifacts reveal.
2. **State changes have spatial continuity:** adding to shortlist visibly moves/copies the name
   into WATCH; debate promotion opens that symbol without losing origin context.
3. **Evidence expands in place:** chart/teacher/method detail opens as an inspector, not a route
   reset or page replacement.

---

## 5. Target experience by surface

### Shell

- Preserve routes but replace the crowded two-row header with:
  - compact workflow rail/navigation;
  - persistent freshness/regime/manual-mode command strip;
  - primary workspace;
  - right-side Live Work/evidence inspector.
- On narrow screens, workflow becomes a bottom/compact nav and the inspector becomes a sheet.
- URL/router state must preserve screen, symbol, date, filters and open inspector; browser
  back/forward must work.

### MARKET — “Can I take risk, and where?”

- Full-width editorial regime canvas: large verdict, four-phase path, breadth/MBI/XP history and
  risk law composed together.
- Show opportunity mechanisms rewarded now, not just allowed-family text.
- One action: review the most relevant scan/mechanism. The 237→0 funnel is supporting evidence,
  not the hero.
- Live Work timeline occupies the inspector, not a placeholder panel.

### SCANNERS — “Which India mechanism is finding something?”

- Organize by TradeTM opportunity/execution stage, not equal owner-card grids.
- Within the relevant stage, show parallel mechanism lanes: TradeTM-native, Arora/Strong Start,
  Stocksgeeks specialist. Each lane has provenance, prerequisites, current hit count, evidence
  status and a setup-specific miniature visual.
- Builder remains a focused secondary workspace, not mixed with practitioner discovery.
- Results use a chart-led list with shortlist/debate actions; expert metrics open in an inspector.

### SHORTLIST — “What am I waiting for?”

- Living candidate rows/cards lead with chart thumbnail, mechanism provenance, catalyst/story,
  missing confirmation and next trigger.
- Show dated state evolution as a real timeline. Strong Start becomes one mechanism/view, not an
  isolated conceptual universe.
- Replace removal prompt with a structured, reversible action and inline result.

### DEBATE — “Why act or refuse?”

- First show shared TradeTM context.
- Then show parallel applicable mechanism columns/lanes with teacher, evidence and verdict.
- Visually surface convergence, conflicts and the decisive objection.
- Model identities are evidence providers within a mechanism, not the information architecture.
- Deterministic risk is a visually separate final authority. A zero-size result dominates any
  optimistic prose.

### TRADE PLAN — “Exactly what do I do manually?”

- One execution ticket: trigger/entry zone, invalidation/stop, server-authored quantity, rupee
  risk, broker checklist and do-not-trade conditions.
- Adjacent management contract states the selected trade type and what “normal” behaviour means.
- Paper-only/manual-execution state stays impossible to miss.
- Evidence and alternative scenarios live in the inspector.

### POSITIONS — “What needs action now?”

- Urgent EXIT/TRIM/MOVE STOP/HOLD is the first visual hierarchy.
- Combine price/R path, stop, thesis state and management-template conformance in one lifecycle
  canvas.
- Replace every native prompt with validated dialogs/sheets; keep previous confirmed position
  visible during mutation.

### JOURNAL — “Am I earning an edge?”

- User trades and equity/R path first.
- Every setup/mechanism shows evidence status, `n`, net-R horizon and sample gap to the next
  status. Thin samples look unfinished, not green or authoritative.
- Separate provenance (“TradeTM teaches this”) from measured Indian evidence (“Manas has n=…”).
- Advanced model/agent records stay available but cannot overwhelm personal learning.

### CHART / evidence inspector

- Preserve weekly-first scanner/shortlist behaviour and default 10/21 EMA + purple dots.
- Add source-attributed annotations and setup-specific overlays rather than more always-on layers.
- Keyboard-operable layer/timeframe controls, non-colour-only legends, visible selected states,
  honest unavailable state and no client invention of server metrics.

---

## 6. Executable work plan

Use **one code writer at a time**. Cheaper agents may audit/extract/build bounded slices; Claude
reviews every diff and performs the final runtime/visual acceptance.

### UI-0 — fresh rendered baseline (mandatory, no product edits)

1. Start API and desk at HEAD; prove `/api/desk/latest` has `build_sha == repo_head`.
2. Capture every route at 1470×900 in beginner and expert modes on real `2026-07-10` data.
3. Capture MARKET/SCANNERS/SHORTLIST/DEBATE/PLAN/POSITIONS/JOURNAL plus chart drawer.
4. Capture loading, empty, stale, error and mutation states where reproducible.
5. Cross-check headline/counts/position/trade-plan numbers against API payloads.
6. Append screenshot paths and a preserve/replace delta to this file. If fresh renders contradict
   this audit, the screenshots win and this plan is amended before coding.

### UI-1 — design foundation and navigable prototype

- Split tokens/type/motion/layout from feature styling; do not attempt a blind global reskin of
  the 84 KB stylesheet.
- Build the new shell, workflow navigation, inspector frame, typography and core primitives using
  fixture/current payloads.
- Preserve all existing routes/actions. No engine/API rewrite.
- Done: MARKET plus one representative candidate and position render in the new system at desktop
  and mobile; screenshot review passes before other screens migrate.

### UI-2 — durable Live Work foundation (CODEX_HANDOFF Q3 backend slice)

- Add persisted `jobs`, `job_steps`, `job_events`, `job_artifacts` around existing pipeline stages.
- Emit source-download, scan, agent/mechanism, chart, mutation, failure/retry and completion events.
- Add SSE with cursor polling fallback and restart-safe replay.
- Done: a fixture and one real update visibly progress without refresh; reconnect has no duplicate
  events; confirmed prior data remains on screen.

### UI-3 — MARKET + Live Work inspector

- Recompose MARKET into the editorial regime canvas and opportunity map.
- Replace the placeholder activity log and one-shot progress component with the real event stream.
- Done: new user can answer “risk on/off, why, what to inspect next, data age” in under 20 seconds.

### UI-4 — SCANNERS + SHORTLIST

- Reorganize scanner registry into TradeTM-stage/context plus parallel applicable execution lanes.
- Add setup-specific visual signatures and chart-led results.
- Rebuild shortlist around confirmation, next trigger, provenance and timeline.
- Replace native prompts and add explicit pending/success/failure mutation feedback.
- Done: add→watch→promote-to-debate is visible, reversible and survives reload.

### UI-5 — DEBATE + TRADE PLAN

- Integrate the corrected Q2 reasoning topology: shared TradeTM context, then parallel applicable
  TradeTM-native/Arora/Stocksgeeks mechanisms, then devil's advocate and deterministic risk.
- Recompose debate around mechanism convergence/conflict; models become attributed evidence.
- Rebuild plan as a manual execution ticket plus management contract.
- Done: provenance never disappears; zero-size cannot coexist visually with a live-take CTA;
  all money math matches server payload exactly.

### UI-6 — POSITIONS + JOURNAL + evidence maturity

- Build lifecycle canvas and validated mutation dialogs.
- Add unified evidence status and sample-gap UI over the existing expectancy authority.
- Recompose Journal around personal edge development and honest thin-data states.
- Done: user can manage and close a position without native prompts; one-trade data does not imply
  statistical proof.

### UI-7 — system hardening and replacement close-out

- Delete/archive superseded CSS/components the same wave their replacements become canonical.
- Verify keyboard/focus, contrast, reduced motion, mobile/tablet/desktop layouts, failure states,
  performance and offline/stale behaviour.
- Run the complete beginner walk: Market → Discover → Watch → Decide → Plan → Manage → Learn.
- Do not retire old code until parity and screenshot/payload QC pass; do not leave two live shells.

---

## 7. QC loop per slice

1. **Cheap executor:** bounded implementation against this exact slice; no architecture changes,
   no subagents, no locked files unless explicitly named.
2. **Code reviewer:** inspect diff for correctness, state ownership, tests, accessibility,
   performance and forbidden client math.
3. **UX reviewer:** compare fresh screenshot to the visual thesis and slice acceptance; inspect
   normal/empty/loading/error states and beginner comprehension.
4. **Claude/orchestrator:** spot-check both reviews against files/runtime; cross-check rendered
   numbers with APIs; run tests/build; write precise kickback defects.
5. On pass only: update this ledger and `SESSION_HANDOFF.md`, commit explicit paths, then proceed.

Required checks when relevant:

- `python -m pytest manas_os/tests -q` — baseline permits only the documented sector-downside fail.
- `npm test` and `npm run build` in `manas_os/desk`.
- API restart and `build_sha == repo_head`.
- Curl proof for changed endpoints.
- Real-data screenshots at 1470×900, 1024×768 and 390×844.
- Beginner/expert, normal/empty/stale/loading/error, keyboard and reduced-motion passes.

---

## 8. Immediate next action for Claude

> **⚠ OUTDATED — see §11 for current status/sequence (2026-07-11).** UI-0 content baseline is done
> (§9), the overhaul is approved-in-practice (UI-1 foundation + DEBATE shipped), so the "do UI-0
> only / hold until approval" instruction below is historical. The live next-step decision is in §11.

Do **UI-0 only**. Do not start Q1 corpus normalization or visual coding first. The owner asked for
a deep review before an overhaul, and the missing artifact is the fresh rendered baseline.

If the in-app browser still cannot attach, ask the user to open `http://127.0.0.1:5174` in the
in-app browser or provide a supported browser surface. Do not silently substitute source review
for screenshot QC. Once captures exist, append the screenshot ledger here, amend any contradicted
finding, and launch one UI-1 executor slice.

---

## 9. UI-0 BASELINE LEDGER (orchestrator, 2026-07-11, HEAD `bd24e29f`)

**Environment proven:** API restarted on HEAD; `/api/desk/latest` → `build_sha == repo_head ==
bd24e29f`, `stale_build=false`, data_as_of `2026-07-10`. Desk vite up on :5174; in-app browser
attaches and the app RENDERS + loads data. **Pixel/image screenshot capture TIMES OUT in this
sandbox** (`computer:screenshot` and `preview_screenshot` both 30s-timeout; the renderer and
JS/DOM read work, the image grab does not). So this baseline is a RENDERED-CONTENT + NUMBER
cross-check, NOT a pixel-gestalt capture. Per §8 the visual/aesthetic certification is NOT made
here — it needs the user (see "ASK" below).

### Number cross-check vs API (UI-0 step 5) — with corrections to §2 audit
| Surface | API (live) | §2 audit said | Delta |
|---|---|---|---|
| pool_total | 237 | 237 | ✓ |
| actionable | 0 | 0 | ✓ |
| stance / regime | CAUTION / SELECTIVE / Lack of Demand | same | ✓ |
| **debate cards** | **13** (4 paper-only + 9 near-miss) | "one debate card" | ✗ CORRECTED — a rescan after the candidacy-relax + momentum fixes regenerated it |
| **watchlist rows** | **34** | "one shortlist/watchlist name" | ✗ CORRECTED |
| positions | 1 (HUDCO) | 1 | ✓ |
| journal trades | 1 (HUDCO open) | 1 | ✓ |
| scanner presets | 19 (12 LIVE / 5 DATA_READY / 2 BUILD) | "19, 12 LIVE, 2 BUILD" | ✓ (5 DATA_READY were uncounted) |

### Rendered-content baseline per route (1470×900, real 2026-07-10 data)
- **MARKET** — 4 `.panel`, **1** heading. Verdict-first "Sit out — nothing to take live tonight",
  `[B]` marker live, "0 actionable · 34 shortlisted · 237 in tonight's pool". Beginner 958 chars →
  Expert 1794 chars (expert adds R10/R20/R50/R4.5, four-phase detail, HMM). **CONFIRMS** P0-2
  (heading-thin/panel-uniform) and P0-5 (`[B]`, mode = data-density).
- **Expert ACTIVITY LOG is a literal placeholder** — verbatim: *"Full nightly activity remains on
  the legacy desk feed; V4-T1 keeps the hook here without adding backend reads."* **CONFIRMS P0-1**
  (no live-work experience).
- **SCANNERS** — **NOT RENDERED** in this pass: after 3.5s the tab shows only the "PRACTITIONER
  SCANNERS | CUSTOM BUILDER" segment control, **0 preset cards** (browser `fetch()` to :8000 hung
  for `/api/scanners/presets` — the intermittent sandbox network issue; curl confirms 19 presets
  exist). **SCANNERS rendered-verification is INCOMPLETE — recapture needed on a working browser.**
- **SHORTLIST** — 6 panels, 4 headings. SHORTLIST | STRONG START segments both present; curator
  delta "promoted 1 · added 1 · demoted 2 since last night" renders; dense table/status idiom
  (**CONFIRMS** P1 shortlist finding).
- **DEBATE** — **15 `.panel`**, verdict "0 live trades · 4 paper-only · 9 near-misses", THE GATE
  funnel 2370→1768→958→237→"0 live". **CONFIRMS P0-2/P1** (panel farm, ~1000-line model-centric
  tab) and P0-3 (owner/model grouping, not TradeTM-context-first mechanism lanes).
- **POSITIONS** — verdict-first EXIT: "EXIT TODAY — 2 exit rules fired (stop-breached,
  below-21EMA)… ₹-1104 (-5.1%)", HUDCO entry 218 / SL 210.84. Safety ordering intact (matches §3
  keep-list).
- **JOURNAL** — user-trades-first ("TRADES 1, WIN% —, AVG R —"), honest empty equity curve ("Not
  enough closed trades yet — appears from trade 2"), R&D behind ▸ disclosure. Matches §5 target.

### Verdict on the audit
The §2 structural findings are CONFIRMED by live content (panel farm, heading-thin, `[B]`,
placeholder activity log, mode=data-density). Two COUNTS were stale (debate 1→13, watchlist 1→34)
and are corrected above — the overhaul plan is unaffected (breadth grew; hierarchy debt unchanged).
The preserve/replace plan in §3-§6 stands.

### ASK (blocks full UI-0 close, per §8 — no silent substitution)
1. **Pixel screenshots for the aesthetic-gestalt call.** I cannot produce images here (capture
   times out). Either: (a) open `http://127.0.0.1:5174` yourself and confirm you'll judge the
   visual gestalt against §4 art direction, or (b) drop screenshots of the 7 routes into the repo
   and I'll append them to this ledger. The content/number QC above I CAN and DID do.
2. **SCANNERS recapture** — its presets didn't load in the sandbox browser; confirm it renders on
   your machine (curl proves the data is there).
3. **Approve the overhaul plan (§3-§6) to start UI-1** — the design-foundation slice (tokens/type/
   motion split + new shell + MARKET + one candidate/position in the new system, fixtures only, no
   engine changes). I hold here until you approve, per §8.

---

## 10. WAVE-2 LEDGER — DEBATE rebuilt to round-4 (2026-07-11)

**Files changed**
- `manas_os/api/app.py` — new `_symbol_returns()` helper (EOD/3D/7D/1M/3M + 30-bar spark
  from `daily_prices`, mirrors `_index_returns` offset convention); `desk_debate` injects
  `returns`/`spark` per symbol and now derives `struck`/`pre_strike_verdict`/`strike_reason`
  from persisted chair lens (fixes fragile `"struck" in reasoning` that flagged every
  "struck: no" row, e.g. BLUEJET).
- `manas_os/agents/chair.py` — `_persist` records `base_verdict`/`struck`/`strike_reason`
  in `lens_scores_json` (first-class strike transition).
- `manas_os/agents/run_card.py` — `_sizer_chair_consistency()` build-time guard: any sized
  symbol must be chair TAKE or struck, else a `chair_sizer_consistency` error is logged.
- `manas_os/desk/src/DebateTab.jsx` — rebuilt to the round-4 composition, composing the
  Wave-1 v5 primitives; `manas_os/desk/src/DebateTab.v5.css` (layout-only, `.v5`-scoped).
- Tests: `tests/test_symbol_returns.py`, `tests/test_sizer_chair_consistency.py`,
  `test_agent_chair.py::test_chair_persists_strike_transition_in_lens`.

**Verification (real 2026-07-10 data)**
- `npm run build` clean; `npx vitest run` 34/34 green; `pytest` 658 pass (1 pre-existing
  unrelated failure: `test_sector_downside::…beats_baseline`, a data-dependent ML baseline,
  touches none of these files).
- Curl `/api/desk/debate?date=2026-07-10` (new code): every symbol carries `returns`+`spark`;
  GROWW carries `pre_strike_verdict:"TAKE"`+`strike_reason`+`struck:true`; BLUEJET `struck:false`.
- DOM check (all 13 rows): GROWW renders `4T/0S → *SKIP → GATE-PASS·PAPER`, deep-dive
  StruckNote "TAKE → SKIP (conviction 3)" + SizerStamp 0×/0/0; CORDELIA short-history
  returns render "—"; RELIANCE "no chair (1-model)"; 4× "GATE-PASS · PAPER", 0 live.

**Waived vs round-4 mockup (with reason)**
- ECharts breadth gauges → plain value tiles (no-new-chart-deps guardrail); breadth ratios
  are real (`regime.ratios`).
- GROWW synthetic candlestick SVG → real `ChartImg` daily chart via existing chart route
  (no synthetic series in production, direction §5).
- Command strip / ticker tape are shell-owned (Wave 1) — not duplicated in the tab.
- Local clock, token-cost ledger figures: omitted (decorative / not in payload).

---

## 11. RECONCILIATION + CORRECTED SEQUENCE (2026-07-11, controlling)

This section reconciles §6/§8 with what was actually built and re-sequences the remainder. It is
the current plan of record; where it conflicts with §4/§6/§8, §11 wins.

### What the design-pass / "bake-off" IS, and where it belongs
The 3-skill design bake-off is NOT a parallel track outside this plan — it is the **"design the
slice" step** that produces a screen's composition *before* its UIx build, now constrained to the
LOCKED v5 light language (§4 banner). Round-4 was that step for DEBATE. Rule: a design pass runs
**for the slice that is next in the sequence below**, not ahead of it, and feeds the §7 QC loop.

### Slice status
| Slice | Scope | Status |
|---|---|---|
| UI-0 | fresh rendered baseline | **DONE (content/number)** §9; pixel-gestalt + SCANNERS recapture = user's, still open |
| UI-1 | tokens/type/motion split + new shell + core primitives + one screen in new system | **FOUNDATION DONE** (Wave 1: v5 light tokens, 19 primitives, shell CommandStrip/TickerTape w/ real VIX). Deviations: representative-screen done-test met by DEBATE (not MARKET); shell CommandStrip sits ABOVE the still-present old header — full shell/nav/inspector recompose NOT yet done |
| UI-2 | durable Live Work: jobs/job_steps/job_events/job_artifacts + SSE + replay | **IN PROGRESS — UI-2a + UI-2b built and fixture-tested (durable rail, polling, SSE replay/heartbeat/done, orphan recovery, cooperative cancel, append-only retry); UI-2c inspector next. Known handoff: POST /api/jobs must return its reserved job_id before inspector wiring** |
| UI-3 | MARKET editorial regime canvas + Live Work inspector | NOT STARTED (needs design pass) |
| UI-4 | SCANNERS (TradeTM-stage + parallel mechanism lanes) + SHORTLIST | NOT STARTED (needs design pass; fixture prep in flight) |
| UI-5 | DEBATE + TRADE PLAN | **DEBATE DONE** (Wave 2); TRADE PLAN not started (needs design pass) |
| UI-6 | POSITIONS + JOURNAL + evidence maturity | NOT STARTED (needs design pass) |
| UI-7 | hardening, delete superseded CSS, full a11y/mobile/beginner walk | NOT STARTED |

### Corrected remaining sequence (handoff-priority order)
1. **Close UI-0's open asks** (cheap, unblocks certification): user confirms the pixel-gestalt of
   DEBATE + shell against the v5 direction; SCANNERS render recapture. These are user actions.
2. **UI-2 — durable Live Work** (P0-1). No new screen design needed; it's the jobs/events/SSE
   backend + a streaming Live Work surface. The handoff ranks this the top blocker, ahead of
   further screen recomposition, because "watch it work" is the missing product experience and
   UI-3's MARKET inspector depends on it.
3. **UI-3 — MARKET** (design pass → build), consuming UI-2's event stream.
4. **UI-4 — SCANNERS + SHORTLIST** (design pass → build). ← the SCANNERS bake-off belongs HERE.
5. **UI-5 remainder — TRADE PLAN** (DEBATE already shipped).
6. **UI-6 — POSITIONS + JOURNAL.**
7. **UI-7 — hardening + old-CSS deletion.**

### Resolved sequencing decision
The user explicitly authorized the orchestration handoff on 2026-07-11. **UI-2 Live Work is the
active slice**; screen migration resumes after its durable event stream and inspector are working.
