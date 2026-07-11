# CODEX HANDOFF — Manas OS delta rebuild (PLAN 3)

Written 2026-07-11 by the Opus/Fable main thread for Codex executors. Supersedes the
2026-07-07 "Manas 2.0 C-queue" version of this file (completed; recoverable from git).
Governing plan: `PLAN (3)` ("Approved Delta Execution Plan") — reviewed/approved in
`PLAN2_REVIEW.md`. This document is the bridge: verified current state, binding guardrails,
environment quirks, and the concrete task queue. **Improve the shipped V4 system; do not
rebuild it.**

## 0. PRODUCT MISSION — USER-LOCKED; EVERY WAVE MUST ADVANCE THIS

The queue below is implementation scaffolding, not the objective. The objective is to turn
Manas OS into an **aesthetic, dynamic, beginner-legible Indian swing-trading edge workbench**:

- **TradeTM is the operating backbone** for Indian market context, opportunity selection,
  execution, position management, and review, and it also supplies multiple native execution
  mechanisms. **Manas Arora is one execution branch** for his scans, setups, timing, entries,
  and Strong Start/watchlist method. **Stocksgeeks is another specialist execution branch**,
  especially for IPO behaviour and breadth/MBI. After the shared TradeTM context is established,
  every source-supported, setup-applicable TradeTM/Arora/Stocksgeeks mechanism runs in parallel;
  preserve their separate evidence and disagreements before reconciliation. Do not flatten the
  teachers into generic lenses or route every candidate through Arora as the sole overlay.
- The product must seek measurable India-specific edge/alpha in areas such as EP, genuine
  catalyst-conditioned PEAD, IPO bases, Strong Start, persistent momentum, reversals, and
  India-specific liquidity/circuit/regime behaviour. A teacher citation proves provenance,
  not alpha; expectancy and evidence labels must stay honest when samples are thin.
- Traditional US setup rules are hypotheses in India, not defaults. Adapt them only through
  Indian doctrine, point-in-time Indian data, liquidity/cost controls, and replay/live outcome
  evidence. Never market an unvalidated detector as proven edge.
- The environment is regulated and **manual-execution only**: no order routing, no disguised
  personalised-advice language, deterministic risk remains sovereign, paper-first behaviour,
  auditability, freshness, and explicit uncertainty are mandatory.
- The interface must feel alive: source downloads, pipeline stages, scanner narrowing, agent
  work, chart generation, watchlist mutations, disagreements, decisions, retries, and failures
  appear progressively without page refresh. Loading states retain confirmed data and explain
  what is happening; the product is visual (charts/graphs/state transitions), not text panels.
- Beginner-friendly means plain-language decision flow and progressive disclosure, not hiding
  safety or evidence. A user should understand Market → Discover → Watch → Decide → Plan →
  Manage → Learn without decoding jargon.
- **Cost routing:** cheaper/legacy models do bulk corpus reads, deduplication, extraction,
  classification, routine summaries, and first-pass implementation where suitable. Stronger
  judgment is reserved for architecture, conflict resolution, high-stakes synthesis, and final
  review. Model IDs are promoted only after representative shadow tests; cheap does not lower
  the quality bar.
- Every executor output is independently checked on two axes: **code correctness** and
  **rendered UX/data fidelity**. The orchestrator spot-checks delegated claims, runs tests,
  cross-checks UI numbers against API payloads, and performs real-data visual QC before a wave
  is certified.

Before accepting or sequencing any task, state how it advances this mission. Work that merely
adds machinery without improving edge discovery, beginner comprehension, live visibility, or
verified reliability is not priority work.

---

## 1. CURRENT STATE (verified against repo, not from memory)

Branch `emergent`, all pushed through `70706d5c`. 650+ tests green (1 known standing
failure: `test_sector_downside.py::test_walk_forward_..._beats_baseline` — pre-existing,
hyperparams invalidated by backfilled VIX data; IGNORE it, never "fix" it in passing).

### Shipped and working (do NOT re-plan or duplicate — PLAN 3 says fold these in)
| Capability | Where | Commit(s) |
|---|---|---|
| V4 trader-flow IA: MARKET · SCANNERS · SHORTLIST · DEBATE · POSITIONS · JOURNAL + TRADE PLAN route | `desk/src/App.jsx` + per-tab files | V4 slices T1-T16 |
| Four-phase classifier (all 4 phases) + choppy brake | `regime/four_phase.py`, `regime/choppy_brake.py`, wired into run_card | `aaf3b02a` |
| Scored-objection cascade: RS floor, 52w nearness, regime family-kill, **and** (new) fresh-leg extension / above-pivot / early-uptrend trend-template / weak-delivery for mover families | `scanner/gates.py` (OBJECTION_WEIGHTS + family frozensets), `scanner/candidates.py` | M3 + `d236b5ef` |
| Momentum measured-move: trailed +15% continuation target (corpus 15-20% checkpoint) so open-ended setups compute R:R; `TRAIL_CONTINUATION_PCT = 0.15` in `risk/plan.py` (tier-4 fallback, additive only) | `risk/plan.py`, `candidates.py` | `2fc37dd6` |
| Candidate pool: 11 → 44 → **237** for 2026-07-10 after the two fixes above. Intentional (user: "hundreds of stocks doing 10%+ daily"). Debate pool stays capped ~10 (gate-diverse round-robin, `agents/debate.py`) | — | — |
| Discovery bucket feeds live pool (M2); 11 archetypes incl. `long_tail`, `ipo_inside_bar` (corpus-cited, quotes verified) | `scanner/discovery.py`, `engine/eod_detectors.py` | `ca7cd3fa`, `83b97b9c` |
| Strong Start / Arora focus list: `strong_start_today` (open>prev_close AND low>=prev_close*0.995), `rvol20`, `arora_strong_start_qualifies` (4 conditions; ADR-scaled extension ceiling `min(3*adr20, 25%)`), `focus_list` table, endpoints w/ llm-push **hard-gated** on qualify (422 otherwise) | `scanner/focus_list.py`, `api/app.py` | `a50dccaa` |
| SS-RVOL STRONG START sub-tab in SHORTLIST + ⚡SS+ buttons on SHORTLIST/SCANNERS rows | `desk/src/ShortlistTab.jsx`, `ScannersTab.jsx`, `api.js` | `70706d5c` |
| Scanner preset registry (21 presets: archetypes, Arora baseline, TODAYS_MOVERS, 5 ChartsMaze trader templates, BUILD placeholders) + run endpoints + Chartink-style conditions engine + saved user screens + push-to-debate (idempotent, 409 in-flight) | `scanner/scanner_presets.py`, `scanner/screener.py`, `api/app.py` | `0d55a4da`, `0bce154c` |
| Living watchlist w/ dated PROMOTE/HOLD/DEMOTE/DROP events, curator_delta, user add/remove (input-guarded: regex + daily_prices existence) | `agents/watchlist.py`, `api/app.py` | `35f27411`, `4c39e38d` |
| Positions: verdict-first, ₹P&L, R-thermometer, stop-breach → EXIT (`two_strike(bars, stop)` hard-stop fix), stale-advisor suppression | `PositionsTab.jsx`, `engine/eod_detectors.py` | `ae82ef25` + |
| TRADE PLAN route: capital→risk-band→qty live math, R-ladder, PAPER ONLY when sizer refuses, server-side risk_checks | `TradePlanTab.jsx`, signal_guide | `5bb462b4`, `4c39e38d` |
| Honest build stamp (`build_sha` vs `repo_head`, `stale_build`), offline-fallback banner, pipeline progress fields (stage x/26, ETA) — **poll-based**, SSE not built | `api/app.py`, `App.jsx`, `api.js` | `ca7cd3fa`, `0bce154c` |
| Evidence: `setup_expectancy` trust ladder (n<20 descriptive → operational) in `scanner/expectancy.py`; UI labels only EXPERIMENTAL/UNPROVEN — the 5-status service is **not built** (PLAN 3 §4) | — | — |
| Knowledge layer: `design/knowledge/` (TRADETM_NUANCES* incl HINDI/COMPLETION/SHARDS, ARORA_SHARDS, STOCKGEEKS, INDIA_PLAYBOOK, PLAYBOOK_TO_TOOL_MAP, PRACTITIONER_SCREENERS); study/ deduped 170→139 (`study/DEDUP_MANIFEST.md`; 2 cited files restored after a bad removal — every cite resolves) | — | `471de4d4`, `a9e3360d` |
| Reviews of record: `PLAN1_REVIEW.md` (done-vs-greenfield map — the current-state contract; EXTEND, don't regenerate), `PLAN2_REVIEW.md` (approval + 3 refinements, folded into PLAN 3) | design/ | `a3dfbc97`, `17724d9b` |

### Architecture invariants (violating these = rejected work)
- **One writer per metric.** `risk/plan.py` is the ONLY writer of stop/size/R:R. Agents and
  advisory templates may never mutate deterministic entry/stop/target/qty (PLAN 3 §2/§5).
- **Adopt, never import from `legacy/`** — one-way door; copy + rename + test.
- **No dormant code**: a module ships only wired into the pipeline AND surfaced in UI.
- **Refusal is visible, never silent**: hard refusals → `refusals` ledger (named gate+reason);
  soft disqualifiers → weighted `objections` in evidence.
- **Judgment stays JUDGMENT**: no converting doctrine (tightness, structural decay, "sell into
  strength") into numeric triggers without an Indian outcome cohort ≥ PROMISING (PLAN 3 §5).

---

## 2. LOCKED / SAFETY (cannot change without explicit user approval + replay evidence)
- Money math: stop caps (5% SELECTIVE etc.), R:R floor 1.5, risk-per-trade bands, open-risk
  caps, max positions, NO_TRADE ⇒ 0 cards. Proposals go to `WAVE_L_RISK_PROPOSAL.md`
  (awaiting user sign-off — do not implement).
- Tradability hard gates (ASM/pump/liquidity/circuit) stay hard. NBIFIN-class must always refuse.
- `agents.telegram_live: false` (dry-run) until the user flips it. Telegram bot token + Fyers
  creds live in gitignored `config.yaml` — NEVER commit or echo them; repo is currently PUBLIC.
- Manual execution only; no order routing, ever.
- Pine ports (© finallynitin / Triyambak) are personal-use — do not redistribute.

---

## 3. ENVIRONMENT QUIRKS (these cost hours if unknown)
- Windows 11, Git Bash + PowerShell. `python` on PATH in the main shell; some sandboxes need
  `py` or a full venv path. Codex sandboxes historically had **no python and a read-only
  `.git`** — if `git add/commit` fails with `index.lock: Permission denied`: make the edits,
  keep the tree clean of unrelated files, report; the orchestrator commits. Never `git add -A`
  (parallel agents share the tree).
- API :8000 runs `run_manas_api.py` with `reload=False` — EVERY backend change needs a manual
  restart: kill the PID on :8000, `Start-Process python run_manas_api.py` (detached, repo
  root), then verify `/api/desk/latest` shows `build_sha == repo_head` BEFORE any "verified
  live" claim. Desk :5174 = vite (HMR usually fine).
- The in-app browser sandbox cannot `fetch()` to `127.0.0.1:8000` (hangs) — UI data-loading
  verification needs the user's real browser or curl-level proof; state the limitation
  honestly rather than skipping the check.
- `PYTHONIOENCODING=utf-8` for scripts printing payloads (σ/₹ break cp1252). Never print `₹`
  to the Windows console from python ('Rs' in prints; the glyph is fine inside code/JSON).
- Full pytest ~95-110s; a full-scan rerun (`candidates.run` for a date) takes minutes and
  LOCKS the sqlite DB — don't run it concurrently with API writes, and don't chain it after
  pytest inside one timeout window.
- DB `manas_os/data/manas.db` is PROD and point-in-time. Tests must never touch it without an
  explicit path (`db.connect()` raises under pytest without one). Scratch DBs → session
  scratchpad. After ANY historical price backfill, recall/expectancy numbers must be re-scored
  (K7's "5/12" was a stale-data artifact; the rule is recorded in LEARNINGS.md).
- Data cadence: bhavcopy ~19:00 IST; nightly pipeline = 26 stages; `run_daily_update.bat`;
  schtasks registration still blocked-on-user. Direct-NSE fallback when mirrors lag:
  `nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv` (browser UA + Referer).

---

## 4. TASK QUEUE (PLAN 3 delivery order, made concrete)

### Q1 — Normalize the corpus ledger (PLAN 3 §1) — cheap-model work
`knowledge/TRADETM_INDEX.md` mixes case/synonyms (DIGESTED/Digested, FULL/Full/full, Gap/gap).
Canonicalize every record to {FULL, DUP, GAP, PARTIAL, SAMPLED, META}; confirm DUPs by hash
(reconcile against `study/DEDUP_MANIFEST.md`); recount coverage (~66 FULL / ~38 GAP / 8
PARTIAL / 14 SAMPLED pre-normalization); record WHY each PARTIAL/SAMPLED is incomplete. Then
queue gap-reading (priority: execution, management, selling, prioritization, MAE/MFE, D2/EP,
IPO, missed trades, system construction) as parallel extraction feeding
`TRADETM_NUANCES_COMPLETION.md`. Findings may update lenses/prompts immediately; never locked risk.

### Q2 — Stage context, then run applicable execution mechanisms in parallel (PLAN 3 §2, user-corrected)
Prompt/orchestration change in `agents/` (debate.py, context_pack.py,
design/agents/LENS_*.md): first establish the shared TradeTM market/opportunity/management
context. A cheap applicability pass then selects every source-supported execution mechanism
that fits the candidate and runs those branches in parallel:
- TradeTM-native mechanisms (including the applicable EP/D2/persistent-vs-absolute/
  velocity-magnitude-hybrid/entry-management mechanisms documented in the corpus);
- Manas Arora mechanisms, including Strong Start/watchlist and applicable scan/setup/entry rules;
- Stocksgeeks specialist mechanisms, especially IPO structures and MBI/breadth.
Each branch retains its teacher, mechanism, evidence, verdict, latency, and token use. The
chair reconciles agreements/conflicts across branches; the devil's advocate challenges the
combined case; deterministic risk validates last. Keep the accuracy-weighted chair + current
seats (deepseek-v4-pro, glm-5, kimi-k2-thinking, qwen3.5-plus). Persist per-branch
{ran/skipped, reason, teacher, mechanism, model, latency, tokens, verdict}; DebateTab exposes
branch provenance and disagreement. Tests: TradeTM context first; all and only applicable
mechanisms run; independent branch outputs survive reconciliation; inapplicable branches skip
with reasons; chair remains regression-free; no branch can mutate deterministic money math.

### Q3 — Durable Live Work: jobs/events + SSE + drawer (PLAN 3 §3) — ship EARLY (felt value)
New tables `jobs/job_steps/job_events/job_artifacts` (additive schema per db/__init__.py
conventions); wrap the existing 26-stage pipeline (cli/__init__.py) so each stage emits
ordered events; endpoints `POST /api/jobs`, `GET /api/jobs/{id}`, `/events`,
`/events/stream` (SSE), `/cancel`, `/steps/{id}/retry`. SSE with cursor-based polling
fallback; state lives in the DB so it survives API restart. Frontend: persistent Live Work
drawer (completed/total, current stage+agent, elapsed, defensible ETA, source-download
progress, expandable artifacts, warnings, retry/cancel, replay after reload); confirmed data
stays visible while work runs; remove refresh-dependent flows and whole-page loading. Keep
Fyers ticks OUT (separate later wave — `FYERS_LIVE_LOOP_PLAN.md`; note: legacy ssrvol is
REST-poll, there is NO WebSocket client to adopt). Tests per PLAN 3 (ordering, reconnect,
cursor replay, dup suppression, retries, cancellation, restart recovery, fallback).

### Q4 — Evidence-status service (PLAN 3 §4)
One service over `setup_expectancy` (map the existing trust ladder in — do NOT create a
second statistical authority): statuses VALIDATED/PROMISING/EXPERIMENTAL/UNPROVEN/CONTRADICTED,
each w/ {setup, regime, n, net-R + horizon, liquidity treatment, point-in-time integrity,
source doctrine, last eval date, rationale, sample-gap-to-next-status}. Expect mostly
EXPERIMENTAL/UNPROVEN initially — UI copy frames it as earned confidence ("we do not claim
evidence the journal has not earned") + shows the n-gap. Surface on Scanners, Shortlist,
Debate, Trade Plan, Positions, Journal. Practitioner provenance visually distinct from
measured Indian expectancy. NEVER weaken thresholds for greener labels.

### Q5 — Advisory trade-lifecycle engine (PLAN 3 §5) — paper mode, the big build
Classify plans {persistent momentum, absolute momentum, velocity, magnitude, hybrid, EP, D2,
IPO, reversal}; versioned management_template per plan + journal trade {entry confirmation,
initial-risk behavior, risk-free transition, holding philosophy, mechanical stop rules,
JUDGMENT profit principles, pyramiding/re-entry, thesis-failure evidence}. HARD BOUNDARY:
stops mechanical/numeric OK; profit management stays JUDGMENT unless its cohort ≥ PROMISING
(via Q4 — a numeric profit trigger must cite its evidence assessment + validation version).
Templates are advisory-only: architecturally unable to call/mutate the risk writers. Extend
Coach/Journal: template-vs-actual conformance, MAE/MFE, overrides, outcomes. Fixture-test
every type + the numeric-vs-judgment boundary + rejection of uncited numeric triggers.

### Q6 — Visual refinement of V4 (PLAN 3 §6)
Keep the workflow. Per screen: MARKET dominant verdict + primary breadth/leadership viz;
SCANNERS presets grouped under TradeTM opportunity stages (keep owner attribution); SHORTLIST
missing-confirmation + character-change emphasis; DEBATE staged-reasoning display; TRADE PLAN
management-type as prominent as entry/stop/qty; POSITIONS coach action + template conformance;
JOURNAL personal improvement + evidence progression. One dominant visual per screen; Evidence
drawers (reuse DensityContext — do NOT rebuild the density system). Constraints of record:
`VISUAL_AUDIT_V4.md` (animation language: motion marks change only; decision numbers never
animate; ECharts REJECTED — existing stack only), `WIREFRAMES_V4.md`, and the standing
screenshot-vs-spec done-test on real data.

### Q-CHARTINK — pending integration (fetch report complete; user pasting 2 clauses)
From the completed fetch (8/9 clauses recovered verbatim off the rendered pages):
- **Encode now, no new metric:** NR7 (classic 7-bar narrowest range) and NR7+Inside-Bar
  (`high<prior_high AND low>prior_low` + NR7) — pure OHLC; add detectors + presets.
- **Encode w/ one new metric** (rolling N-day-high-with-offset): short-term-breakouts
  (`Max(5,close) > Max(120,close) 6d-ago * 1.05` + vol>SMA(vol,5) + up-day) and
  potential-breakouts (`close*1.05 > Max(200,high)` + no-new-high-in-30d tightness +
  vol>SMA(vol,50) + close>90).
- **Confirm fields first:** NSE-universe by Chhirag Kedia (needs market_cap + turnover —
  turnover exists in tradability; check mcap), NKS-best-buy (needs weekly/monthly resampled
  bars — ChartDrawer resamples client-side; backend needs a resampler, else defer).
- **Skip or relabel:** "manas-arora-vcp-pattern" is NOT a real VCP (trend + near-52w band +
  price/mcap bounds); true VCP already exists. If added, label honestly ("Arora trend filter
  (Chartink)"), never as VCP.
- **BLOCKED ON USER:** #1 stocksgeeks-fund-flow-tightness (author hid the filters on the
  page — non-recoverable) and #9 copy-dssja-2 (rows visible; AND/OR nesting ambiguous).
  Encode ONLY what the user pastes; NEVER infer a plausible clause (source-fidelity rule).
- Dashboard ideas parked: Pocket Pivot (a detector already exists — check before duplicating),
  3-week-tight-consolidation (new detector candidate).

### Q-SMALL — carried-over loose ends
- SS-RVOL STRONG START tab: rendered-with-data screenshot still owed (sandbox fetch
  limitation) — capture on the next real-data session; attach to the QC ledger.
- 237-candidate pool: user judges breadth on Monday's first real night (~19:00 IST). If the
  top-of-rank feels noisy, add a rank/quality surfacing threshold — do NOT re-tighten risk math.
- `focus_list` LLM-push: the backend gate exists (422 for non-qualifying); no agent calls it
  yet — wire the curator/debate path to push Arora-matching names.
- Old-IA task-list leftovers (#1 regime UX rework, #17 guru checklists, #29 beginner-toggle
  depth, #37 focus-center mismatch) — fold into Q6 or close as obsolete during Q1's ledger pass.

---

## 5. VERIFICATION PROTOCOL (every task, non-negotiable)
1. `python -m pytest manas_os/tests -q` — green except the 1 known standing failure.
2. Frontend: `cd manas_os/desk && npm run build` clean; `npm test` (vitest, incl. the glossary
   auto-discovery test) green.
3. Restart the API; prove `build_sha == repo_head` BEFORE any "verified live" claim.
4. Curl-level proof for every new/changed endpoint on real data; rendered screenshot on real
   data for every UI change (standing QC rule: "does it render" is NOT QC — every value
   correct and complete is).
5. Commit per wave, explicit paths only, message says what+why, ends with a
   `Co-Authored-By:` line for the executing model. Do not push unless instructed — the
   orchestrator pushes after its own verification pass.
6. Report honestly: failures/skips in the first lines; numbers recomputed at point of use,
   never copied forward; anything uncheckable marked "Unverified:".

## 6. WHO DECIDES WHAT
- **Codex/executors:** implement, test, report. Deviations from spec → note and flag; don't
  silently re-decide.
- **Orchestrator (Claude main thread):** reconciles reviews, verifies, commits/pushes, sequences.
- **USER (blocked-on-user list):** flip repo private; WAVE_L risk sign-off; schtasks
  registration; Fyers live-loop go; telegram_live flip; the 2 hidden Chartink clauses;
  Monday's verdict on pool breadth.
