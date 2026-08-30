# TraderLog V2 — step-by-step build manual

Status: controlling rebuild manual  
Created: 2026-08-26  
Owner authorization: Full V2 execution, Phases 0 through 6, authorized on 2026-08-27.  
Production database: `traderlog/data/traderlog.db`  
Production API/UI: `traderlog/api/app.py` on port 8100 and `traderlog/ui/` on port 5180  
Acceptance viewport: 1920×1080 only

This is an execution manual, not a concept note. Follow it in order. Do not skip a task because a later task appears easier. Do not implement a downstream task when an upstream checkpoint is red.

---

## 0. What is being built

TraderLog V2 is an evidence engine for public statements made by followed traders. It answers four questions:

1. What deserves review now?
2. What trade event did a trader actually state?
3. What happened on the tape after the statement?
4. What repeatable, cited behaviour is visible for a symbol or trader?

TraderLog is not an order-entry system, a recommendation engine, a position-sizing tool, or a source of invented prices. It records and analyses what other traders publicly said.

The product has three permanent workspaces, one routed analytical page, and one delivery surface:

| Surface | Job | Permanent navigation? |
|---|---|---|
| Radar | Recent independent symbol/theme/market attention and what changed | Yes; default |
| Ledger | Latest accepted entry/add/stop/trim/close claims and lifecycle state | Yes |
| Traders | Evidence-backed timing, specialisation and recurring playbook behaviour | Yes |
| Symbol | Candles, claims, levels, tape and evidence for one NSE symbol | No; opened from search/Radar/Ledger |
| Telegram | High-confidence live event delivery with evidence links | No; operational output |

The old Feed remains available only as an archive/evidence route. Library and standalone Breadth cease to be primary navigation. Their useful information moves into Traders and Radar respectively.

---

## 1. Authority order and conflict resolution

Read these files before every implementation session, in this order:

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md`
6. `traderlog/design/CONTRACTS.md`
7. `traderlog/design/VISUAL_LANGUAGE.md`
8. `traderlog/design/WIREFRAMES.md`
9. This manual

When documents disagree, use this order:

1. Directly verified source evidence, database inspection and test output.
2. `AGENTS.md`, `CANONICAL.md` and `CONTRACTS.md` invariants.
3. Explicit owner decisions in `HANDOFF.md` and `design/DECISIONS.md`.
4. This V2 manual.
5. `VISUAL_LANGUAGE.md` for appearance.
6. Current `WIREFRAMES.md` only for elements not replaced by this manual.
7. Old completion reports and historical wave documents.

Never resolve a contradiction silently. Add a dated entry to `design/DECISIONS.md` and update the contradicted canonical document in the same change.

The following previous recommendations are explicitly rejected:

- Restoring the rejected scouting/wire UI from a historical copy.
- Treating the 305 deterministic-lifeline positions as accepted truth.
- Running `derive/reconcile_all.py` or any equivalent regex lifecycle rebuild.
- Creating seven permanent product tabs.
- Presenting `EARLY`, co-attention or attention score as a trade recommendation.
- Targeting zero unresolved records. Honest ambiguity is a valid state.
- Showing fabricated fallback values, fake KPIs, decorative charts or hidden failures.

`plan/v2.md` is retained as a historical incremental-v1 input, not as a second
controlling plan. Its freshness policy, stock tape/activity analytics,
disagreement surface, setup calibration, evidence sampling and attribution
requirements are incorporated below. Its stale 94-position baseline,
zero-unreconciled target, scouting/wire restoration, Library revival,
375px acceptance and executor commit/push steps are superseded.

---

## 2. Verified starting state

Record a new baseline at the beginning of each session. The 2026-08-26 baseline was:

- 17 traders.
- 3,395 real posts and zero mock posts.
- 2,588 media-bearing posts.
- 1,274 rows with non-null vision JSON; this means coverage, not proven accuracy.
- 305 positions and 436 events, all produced by `deterministic-lifeline-reconciler (2026-08-26)`.
- A pre-Gemini backup contains 94 positions and 110 events, including 71 DeepSeek-agentic reconciliations plus Nemotron, Terra-audited, human-Terra and explicit link records.
- 3,347 posts lack a conversation ID and 3,375 lack a parent ID; absence of ancestry must not be presented as a verified thread.
- `python traderlog/run_checks.py` is red: two Radar browser tests fail; ingest reports only 9/17 traders fresh.
- The repository worktree contains extensive unrelated user/parallel changes. Every implementation brief therefore requires an exact file allowlist.

These numbers are a dated baseline, not eternal constants. Recompute them before using them in a completion claim.

---

## 3. Non-negotiable data rules

1. Every populated claim field cites an archived post or archived media item.
2. Never infer a number that the source did not state or visibly display.
3. Missing values are `null` plus a named unresolved reason, never zero.
4. Vision output is evidence, not truth. It must remain attached to its image and source post.
5. A tape return is a market calculation, not the trader's claimed result.
6. A bare mention is not an entry. A partial exit is not a full close.
7. Unknown reply ancestry remains unknown. Candidate linkage is not accepted linkage.
8. Model output is provisional until it passes contract validation and the applicable review threshold.
9. No production mock data. Synthetic rows may exist only in a disposable database whose path is explicit.
10. Only one writer owns a table or derived field. Update `CANONICAL.md` when ownership changes.
11. Production writes require a pre-write SQLite backup, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, and a measured row-count delta.
12. No model call may silently spend money. Provider calls use a tier and remain behind the existing budget ledger.

---

## 4. Required executor protocol

Every executor follows all steps below. A completion report that omits one is rejected.

### Before editing

1. Read the nine documents in Section 1.
2. Run `git status --short`.
3. Run `python traderlog/run_checks.py` and save the exact baseline result in the handoff report.
4. Confirm the task's file allowlist. Do not edit any file outside it.
5. Use CodeGraph before grep or broad file reads:

   ```powershell
   codegraph explore "<task question and relevant symbols>"
   codegraph node <exact-symbol-or-file>
   ```

6. If a database write is involved, create a disposable database or an explicit production backup first.
7. State the task's pass/fail check before implementing.

### During implementation

1. Write or update a failing test first for logic changes.
2. Make the smallest change that passes that test.
3. Keep tasks to five files or fewer. Split larger tasks.
4. Do not edit generated `STATE.json` by hand.
5. Do not create scratch scripts in the repo. Delete any one-off probe before close.
6. Do not commit.

### Before closing

1. Run the focused tests named by the task.
2. Run `pytest traderlog/tests -q`.
3. Run `npm run build` from `traderlog/ui` when UI code changed.
4. Run `python traderlog/run_checks.py`.
5. Run `git diff --check`.
6. Inspect the real app at 1920×1080 when any screen or runtime path changed.
7. Verify zero document overflow, zero panel overflow, zero console errors, zero failed network requests and no raw error stack on screen.
8. Recompute critical database counts using both SQL and the public API.
9. Append the required record to `traderlog/design/MODEL_WORK_LOG.jsonl`.
10. Write a `_COMPLETED.md` report using the completion template and include the exact `Attribution-ID`.
11. Update `HANDOFF.md`, `TASKS.md`, contracts, wireframes and decisions where the task changed truth.
12. Stop without committing.

### Mandatory stop conditions

Stop the current task immediately when any of these occurs:

- A source value cannot be cited.
- The production DB path is not exactly resolved.
- A backup fails or `PRAGMA integrity_check` is not `ok`.
- A migration loses raw posts, media, classifications, prices or evidence.
- A focused test fails for an unexplained reason.
- A downstream task depends on a red checkpoint.
- The requested change would write to `manas_os/`.
- The work overlaps an unrelated dirty file outside the allowlist.

---

## 5. Target architecture

### 5.1 Data flow

```text
X/manual manifest
  -> immutable raw archive + media hash
  -> post row
  -> post classification
  -> text + vision evidence bundle
  -> provisional claim(s)
  -> contract validation
  -> accepted / unresolved / rejected claim
  -> accepted claim links
  -> lifecycle materialization
  -> Ledger, Symbol, Radar and Traders APIs
  -> UI and Telegram outbox
```

No UI may read directly from raw model output. It reads validated database projections returned by named API functions.

### 5.2 Claim model

The atomic analytical unit is a claim. One post may produce zero, one or several claims.

Required claim types:

- `entry`
- `add`
- `stop_set`
- `stop_move`
- `target`
- `partial_exit`
- `full_exit`
- `result_statement`
- `watch`
- `theme`
- `market_view`
- `lesson`

Required review states:

- `provisional`
- `accepted`
- `unresolved`
- `rejected`
- `superseded`

Proposed `claims` fields:

| Field | Rule |
|---|---|
| `claim_id` | Deterministic ID from source post/media, claim type and ordinal |
| `post_id` | Required FK to archived source post |
| `media_idx` | Nullable; present when an image is the cited source |
| `handle` | Exact source author |
| `subject_type` | `symbol`, `theme`, `market`, or `education` |
| `subject` | NSE symbol or cited label; null only when genuinely absent |
| `claim_type` | Enum above |
| `stated_at` | Source timestamp, never model time |
| `direction` | `long`, `short`, or null when unstated/inapplicable |
| `price` | Exact stated/displayed value or null |
| `price_from` / `price_to` | Exact old/new stop or ranged level values |
| `quantity_pct` | Exact stated percentage or null |
| `result_pct` | Exact stated percentage or null |
| `size_note` | Verbatim stated phrase or null |
| `text_quote` | Verbatim source excerpt; never paraphrased |
| `confidence` | Finite 0..1 extraction confidence |
| `review_state` | Enum above |
| `source_kind` | `human`, `model`, `deterministic`, or `migration` |
| `source_model` | Exact documented model/source; never guessed |
| `evidence_json` | Field-to-post/media citation map |
| `unresolved_json` | Named missing/ambiguous facts |
| `supersedes_claim_id` | Nullable accepted correction chain |
| `created_at` / `updated_at` | Audit timestamps |
| `is_mock` | Must be zero in production |

Proposed `claim_links` fields:

- `link_id`
- `from_claim_id`
- `to_claim_id`
- `relation`: `same_lifecycle`, `updates`, `partially_closes`, `fully_closes`, `supports`, `contradicts`
- `review_state`
- `confidence`
- `reason`
- `alternatives_json`
- `source_model`
- audit timestamps

Only accepted claims and accepted links may feed lifecycle materialization.

### 5.3 Lifecycle projection

`positions` and `position_events` become a read model derived from accepted claims. They are not written directly by regex classifiers.

Rules:

- An accepted `entry` starts a lifecycle.
- An accepted `add` may attach only to a same-handle, same-symbol open-like lifecycle through an accepted link.
- An accepted `partial_exit` changes the lifecycle to `partial` but does not set `closed_at`.
- An accepted `full_exit` or accepted complete close changes it to `closed`.
- A stop breach observed from market data does not close the trader's stated position.
- Ambiguous closes remain unresolved and appear in the review queue.
- Every materialized event stores its originating `claim_id` and source `post_id`.

### 5.4 API target

Keep one named frontend fetch function per endpoint.

Required V2 endpoints:

- `GET /api/health`
- `GET /api/radar`
- `GET /api/ledger`
- `GET /api/ledger/{lifecycle_id}`
- `GET /api/traders`
- `GET /api/traders/{handle}`
- `GET /api/symbol/{symbol}`
- `GET /api/review`
- `POST /api/review/{id}`
- archive-only `GET /api/feed`

Every response carries `is_mock`, coverage/staleness metadata where relevant, and stable empty arrays rather than changing shape.

---

# Phase 0 — contain fabricated lifecycle data and recover evidence

Goal: no user-facing surface treats the deterministic 305-position rebuild as accepted truth, and audited pre-Gemini lifecycle evidence is recoverable without replacing the raw corpus.

## Task P0.1 — freeze the forensic baseline

Description: Create an auditable record of current database identity, backup candidates and provenance before changing lifecycle data.

Dependencies: none.

Files allowed:

- `traderlog/design/AUDIT_LEDGER.md`
- `traderlog/design/handoffs/HANDOFF_V2_P0_forensic_baseline_COMPLETED.md`
- `traderlog/design/MODEL_WORK_LOG.jsonl`
- `traderlog/HANDOFF.md`
- `traderlog/TASKS.md`

Steps:

1. Resolve `traderlog/data/traderlog.db` to an absolute path and record file size and SHA-256.
2. Run `PRAGMA integrity_check` and `PRAGMA foreign_key_check` read-only.
3. Record counts for posts, post_media, post_class, positions, position_events, review_queue, daily_prices, breadth_daily, regime_daily, alpha_activity_signals and llm_runs.
4. Group positions and events by `reconcile_model`/model provenance.
5. Inventory every `traderlog.db.backup-*` file with size, SHA-256, integrity result, position/event counts and model mix.
6. Independently verify the selected audited backup by querying it through a second connection.
7. Add a dated audit entry naming the selected recovery source and why.

Acceptance criteria:

- [ ] Current production SHA-256 and integrity results are recorded.
- [ ] Every candidate backup is listed or explicitly excluded with reason.
- [ ] Selected recovery backup counts agree through two independent SQL queries.
- [ ] No database file was modified.

Verification:

```powershell
python traderlog/run_checks.py
git diff --check
```

## Task P0.2 — remove the destructive reconciler from executable code

Description: Make the deterministic lifeline reconciler impossible to run accidentally while retaining an audit trail of what happened.

Dependencies: P0.1.

Files allowed:

- `traderlog/derive/reconcile_all.py`
- `traderlog/tests/test_reconcile_safety.py`
- `traderlog/design/AUDIT_LEDGER.md`
- `traderlog/CANONICAL.md`
- `traderlog/design/DECISIONS.md`

Steps:

1. Use CodeGraph to prove whether anything imports or calls `derive/reconcile_all.py`.
2. Record the dangerous behaviours: blanket deletion, broad exit matching and deterministic model stamp.
3. Delete the executable module if it has no legitimate caller. Do not move it to another importable Python path.
4. Add a regression test that fails if an importable production module contains a blanket `DELETE FROM positions` or `DELETE FROM position_events` lifecycle rebuild outside an explicitly named test fixture.
5. Add a decision stating that regex/deterministic parsing may propose provisional claims but may never author canonical lifecycle rows.
6. Update the single-writer map.

Acceptance criteria:

- [ ] Importing or executing `traderlog.derive.reconcile_all` fails because the production module no longer exists.
- [ ] No production caller references it.
- [ ] Safety regression test passes.
- [ ] No production database write occurred.

Verification:

```powershell
pytest traderlog/tests/test_reconcile_safety.py -q
pytest traderlog/tests -q
```

## Task P0.3 — build a disposable V2 recovery database

Description: Copy safe non-lifecycle tables from current production and audited positions/events from the selected pre-Gemini backup into a new staging database.

Dependencies: P0.1 and P0.2.

Files allowed:

- `traderlog/maintenance/build_v2_staging.py`
- `traderlog/tests/test_build_v2_staging.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/CANONICAL.md`
- `traderlog/design/DECISIONS.md`

Required CLI:

```powershell
python traderlog/maintenance/build_v2_staging.py `
  --source traderlog/data/traderlog.db `
  --audited-backup <selected-backup> `
  --dest traderlog/data/traderlog_v2_staging.db `
  --dry-run
```

Then repeat without `--dry-run` only after the dry-run report is correct.

Steps:

1. Refuse when source, audited backup or destination resolve to the same file.
2. Refuse to overwrite an existing destination unless `--replace-staging` is passed and the destination filename is not `traderlog.db`.
3. Copy the source DB to the destination using SQLite backup API.
4. On the destination only, delete the 305 deterministic positions/events.
5. Attach the audited backup read-only.
6. Copy audited position/event rows only when every referenced post exists in the destination.
7. Reject a row when any evidence post is missing, any JSON is malformed, or any FK fails.
8. Preserve rejected rows in a recovery report, not in canonical tables.
9. Run integrity and foreign-key checks before closing.
10. Emit a machine-readable JSON report with before/after counts and row-level exclusions.

Acceptance criteria:

- [ ] Production SHA-256 is identical before and after.
- [ ] Staging preserves all current raw posts, media, classifications, vision, prices, breadth and activity rows.
- [ ] Staging contains only audited lifecycle rows, with zero deterministic-lifeline model rows.
- [ ] Every restored position/event citation resolves to an archived post.
- [ ] Re-running with a fresh destination produces byte-equivalent logical counts and the same exclusion report.

Verification:

```powershell
pytest traderlog/tests/test_build_v2_staging.py -q
python traderlog/maintenance/build_v2_staging.py --source ... --audited-backup ... --dest ... --dry-run
```

## Task P0.4 — make lifecycle provenance visible to APIs

Description: Prevent user-facing APIs from returning quarantined or unaccepted lifecycle rows.

Dependencies: P0.3.

Files allowed:

- `traderlog/api/app.py`
- `traderlog/tests/test_api_lifecycle_provenance.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/checks/check_parse.py`
- `traderlog/tests/test_checks.py`

Steps:

1. Define the accepted model/provenance rule in one helper rather than duplicating SQL predicates.
2. Apply it to position list, position detail, feed event joins and trader summaries.
3. Add coverage metadata reporting accepted, provisional, quarantined and unresolved counts.
4. Change `check_parse` so “all cited” is insufficient; it must reject deterministic-lifeline provenance as canonical.
5. Test against a disposable DB containing one accepted row and one quarantined row.

Acceptance criteria:

- [ ] Public APIs return the accepted row and exclude the quarantined row.
- [ ] Health/coverage reports both counts honestly.
- [ ] `check_parse` fails when only deterministic rows exist.
- [ ] Empty accepted lifecycle data returns stable empty arrays, not a server error.

## Phase 0 checkpoint

Do not enter Phase 1 unless every box is checked:

- [ ] The destructive reconciler is not executable.
- [ ] Production has a verified recoverable backup.
- [ ] A disposable V2 staging DB contains raw/current evidence plus audited lifecycle rows.
- [ ] Production was not replaced.
- [ ] Quarantined lifecycle rows cannot appear through public APIs.
- [ ] Focused tests pass and unrelated baseline failures are unchanged or reduced.
- [ ] Phase 0 completion report and attribution exist.

---

# Phase 1 — runtime truth and visual stability

Goal: the actual instance identifies its code/DB/build, renders without runtime crashes and never conceals missing data.

## Task P1.1 — add runtime identity

Description: Make it impossible to confuse stale UI assets, the wrong DB or the wrong API process with the current build.

Dependencies: Phase 0 checkpoint.

Files allowed:

- `traderlog/api/app.py`
- `traderlog/ui/src/App.jsx`
- `traderlog/ui/src/api.js`
- `traderlog/ui/src/styles/app.css`
- `traderlog/ui/vite.config.js`
- `traderlog/tests/test_runtime_identity.py`
- `traderlog/design/CONTRACTS.md`

Required health fields:

- `runtime.commit`
- `runtime.build_id`
- `runtime.db_path_hash`
- `runtime.db_updated_at`
- `runtime.api_started_at`
- `runtime.ui_contract_version`

Never expose the full local DB path.

Steps:

1. Generate a deterministic source-tree build ID in `vite.config.js`, inject the
   same immutable value into the UI bundle, and make the API compute the same
   identifier at process start. The hash input and ordering must be identical in
   JavaScript and Python so stale API, stale UI and unrebuilt source are visible.
2. Return runtime identity from `/api/health`.
3. Show a compact “Data / API / UI” identity disclosure in the shell.
4. Add a browser test that deliberately serves mismatched UI/API build IDs and verifies a visible warning.

Acceptance criteria:

- [ ] Browser-visible runtime identity matches `/api/health`.
- [ ] A mismatch cannot look healthy.
- [ ] No filesystem path or secret is exposed.

## Task P1.2 — migrate Lightweight Charts to the installed API

Description: Fix the Symbol/Radar chart crash against the installed Lightweight Charts 5 dependency.

Dependencies: P1.1.

Files allowed:

- `traderlog/ui/src/components/TradingViewChart.jsx`
- `traderlog/ui/src/components/PanelErrorBoundary.jsx`
- `traderlog/ui/src/styles/app.css`
- `traderlog/tests/test_tradingview_chart_runtime.py`
- `traderlog/ui/package.json`

Steps:

1. Keep Lightweight Charts 5 unless official API inspection proves migration is impossible.
2. Replace removed series/marker APIs with the installed version's supported APIs.
3. Resolve all chart colours from CSS tokens; remove component raw hex values.
4. Add cleanup for series, subscriptions, resize observers and chart instances.
5. Add a panel error boundary with one compact factual failure message.
6. Feed a disposable symbol with real-looking test OHLC rows and markers.
7. Assert the chart panel renders and the rest of the page survives an injected chart error.

Acceptance criteria:

- [ ] Candles and event markers render with the installed dependency.
- [ ] No console exception is produced.
- [ ] An injected chart failure does not take down Radar or Symbol.
- [ ] No raw colour literal remains outside `tokens.css`.

## Task P1.3 — reconcile Radar API and UI contracts

Description: Make the evidence rail use the exact fields returned by `/api/radar`.

Dependencies: P1.2.

Files allowed:

- `traderlog/ui/src/screens/Radar.jsx`
- `traderlog/ui/src/api.js`
- `traderlog/tests/test_radar_browser.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/design/WIREFRAMES.md`

Steps:

1. Use `evidence`, `first_mention_ts`, `last_mention_ts` and `coverage_debt` exactly as contracted.
2. Remove reads of nonexistent `cluster.traders`, `first_seen`, `posts` or `coverage` fields.
3. Render exact evidence text and source links in chronological order.
4. Show missing coverage explicitly.
5. Test mouse selection, keyboard selection and the symbol route.

Acceptance criteria:

- [ ] The current 30-day payload renders non-empty evidence for every returned row.
- [ ] Coverage debt is visible and numerically matches the payload.
- [ ] Existing two failing Radar acceptance tests pass without weakening assertions.

## Task P1.4 — remove every UI lie

Description: Audit the currently implemented Radar and Ledger workspaces plus
the shell for fabricated fallbacks, truthy rendering mistakes and misleading
empty states. The routed Symbol workspace does not exist until Phase 3; carry
the same honesty rules into its P3.4/P3.6 acceptance rather than creating a
misleading Phase-1 stub.

Dependencies: P1.3.

Files allowed per subtask: one screen, its CSS file, one focused test, and required spec files only. Do not audit all screens in one edit.

Search patterns:

```powershell
rg "\|\||&&|fallback|mock|placeholder|Math\.random|Date\.now" traderlog/ui/src traderlog/api
```

Rules:

- `0` is a valid value and must not be hidden by truthiness.
- `null` is unknown and must not render as zero.
- Stale data states its last available date.
- Empty data uses one compact explanatory line.
- No future-wave empty chart frame is rendered.

Acceptance criteria:

- [ ] Focused regression exists for every removed lie.
- [ ] Radar and Ledger show honest zero/null/stale/loading/error states.
- [ ] P3.4/P3.6 explicitly inherit the same acceptance for the future Symbol
      workspace; no Phase-1 placeholder screen is created.
- [ ] No unrelated screen was restyled.

## Phase 1 checkpoint

- [ ] Runtime identity is visible and correct.
- [ ] Lightweight Charts renders without crashing.
- [ ] Radar evidence contract matches the API.
- [ ] The two baseline Radar browser failures are green.
- [ ] Full tests and `run_checks.py` are green except an explicitly documented live-ingest freshness warning.
- [ ] Real instance passes 1920×1080 console/network/overflow inspection.

---

# Phase 2 — canonical claim layer and newest-first reconciliation

Goal: transform text plus vision evidence into validated, reviewable claims and accepted lifecycle links without inventing threads or prices.

## Task P2.1 — specify and migrate claim tables

Description: Add the claim and link schema described in Section 5 without changing production data.

Dependencies: Phase 1 checkpoint.

Files allowed:

- `traderlog/db/schema.sql`
- `traderlog/db/__init__.py`
- `traderlog/tests/test_claim_schema.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/CANONICAL.md`

Steps:

1. Add complete CREATE statements for fresh databases.
2. Add idempotent migration for existing databases.
3. Add indexes only after migrated columns exist.
4. Add FKs to posts/media/claims where SQLite permits.
5. Add CHECK constraints for enums and numeric confidence bounds.
6. Name exactly one writer for claims, claim links and lifecycle projection.

Acceptance criteria:

- [ ] Fresh DB and migrated DB have identical schema shape.
- [ ] Running init twice is idempotent.
- [ ] Invalid enum/confidence/FK inserts fail.
- [ ] Existing tables and counts are unchanged.

## Task P2.2 — build claim validation and single-writer persistence

Description: Validate claim payloads against source posts and media before any write.

Dependencies: P2.1.

Files allowed:

- `traderlog/claims/models.py`
- `traderlog/claims/validate.py`
- `traderlog/claims/store.py`
- `traderlog/tests/test_claim_validation.py`
- `traderlog/tests/test_claim_store.py`

Validation rules:

- Claim keys are exact; unknown keys fail.
- Handle and stated time must match the source post.
- Text quote must be verbatim in the post or vision transcription.
- Symbol must appear in cited text/vision or be explicitly unresolved.
- Numeric fields must exist visibly in cited evidence.
- A post/media citation must resolve.
- Accepted claim writes are idempotent.
- A changed accepted claim creates a superseding claim; it does not silently overwrite history.

Acceptance criteria:

- [ ] Unsupported assertions fail before transaction start.
- [ ] Same payload twice creates one logical claim.
- [ ] Correction creates a traceable supersession chain.

## Task P2.3 — combine text and vision into claim candidates

Description: Build one evidence bundle per post and ask the configured provider tier for provisional claims.

Dependencies: P2.2.

Files allowed:

- `traderlog/claims/extract.py`
- `traderlog/llm/prompts/claims.md`
- `traderlog/tests/test_claim_extract.py`
- `traderlog/tests/golden/claims/`
- `traderlog/design/CONTRACTS.md`

Steps:

1. Load the exact post text and all archived vision JSON for the post.
2. Preserve contradictions between text and image as unresolved.
3. Request zero or more claims using a tier, never a named model.
4. Validate every proposed claim.
5. Store validated output as provisional unless it matches an audited golden case or passes an explicit acceptance route.
6. Process newest posts first: `ORDER BY ts_ist DESC, post_id DESC`.
7. Ensure unchanged evidence costs zero provider calls through an evidence hash.

Acceptance criteria:

- [ ] Entry, add, stop, partial exit and full exit fixtures pass.
- [ ] A chart-only price can be cited through its media/post.
- [ ] An unreadable image produces no numeric claim.
- [ ] A symbol-less close remains unresolved rather than attached automatically.

## Task P2.4 — verified author identity and link candidates

Description: Propose relationships between claims without pretending missing X ancestry is known.

Dependencies: P2.3.

Files allowed:

- `traderlog/claims/link.py`
- `traderlog/tests/test_claim_link.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/design/DECISIONS.md`

Candidate evidence priority:

1. Exact conversation/parent relationship.
2. Explicit permalink/reference in source text.
3. Same verified handle and symbol with one compatible open lifecycle.
4. Same verified handle, missing symbol, explicit close language, and a single compatible candidate.
5. Anything else is unresolved with alternatives.

Never use time proximity alone as proof.

Acceptance criteria:

- [ ] Exact reply link is accepted deterministically.
- [ ] Ambiguous same-symbol candidates enter review.
- [ ] Unverified author identity excludes the claim from trader scoring.
- [ ] Link creation is idempotent.

## Task P2.5 — materialize lifecycle from accepted claims

Description: Rebuild position read models only from accepted claims and links.

Dependencies: P2.4.

Files allowed:

- `traderlog/derive/claim_lifecycle.py`
- `traderlog/tests/test_claim_lifecycle.py`
- `traderlog/checks/check_parse.py`
- `traderlog/CANONICAL.md`
- `traderlog/design/CONTRACTS.md`

Steps:

1. Select accepted trade claims and accepted lifecycle links only.
2. Fold them in chronological order with deterministic tie-breaking.
3. Preserve exact source price/quantity fields.
4. Compute status from accepted event kinds only.
5. Write `claim_id` and `post_id` on every materialized event.
6. Replace only the one affected lifecycle per transaction; never blanket-delete all positions.
7. Prove unchanged input produces byte-identical projection.

Acceptance criteria:

- [ ] Partial exit remains partial.
- [ ] Full exit closes and sets the accepted close timestamp.
- [ ] A later explanation does not reopen a closed lifecycle.
- [ ] Missing stop remains unresolved.
- [ ] No market price is written as a claimed trade result.

## Task P2.6 — build the recent Manas gold set

Description: Establish a human-verifiable end-to-end acceptance set from recent Manas posts, replies and images.

Dependencies: P2.5.

Files allowed:

- `traderlog/tests/golden/claims/manas_recent.jsonl`
- `traderlog/tests/test_manas_claim_gold.py`
- `traderlog/design/AUDIT_LEDGER.md`
- `traderlog/design/handoffs/HANDOFF_V2_P2_manas_gold_COMPLETED.md`
- `traderlog/design/MODEL_WORK_LOG.jsonl`

Required coverage:

- Text entry with stated price.
- Chart/image-only level.
- Add.
- Stop set or moved.
- Partial exit.
- Full close.
- Explanation reply that is not a new event.
- Ambiguous or symbol-less close routed to review.

Every fixture must be read against the archived source by the orchestrator. Model self-report is not verification.

Acceptance criteria:

- [ ] Every expected field has source evidence.
- [ ] No fixture is derived from the deterministic 305-position rebuild.
- [ ] Full gold set passes twice from a clean disposable DB.

## Task P2.7 — migrate audited legacy events into accepted claims

Description: Convert only audited staging lifecycle evidence into claims, then compare the new projection with the audited source.

Dependencies: P2.6.

Files allowed:

- `traderlog/maintenance/migrate_audited_claims.py`
- `traderlog/tests/test_migrate_audited_claims.py`
- `traderlog/design/AUDIT_LEDGER.md`
- `traderlog/HANDOFF.md`
- `traderlog/TASKS.md`

Rules:

- Each migrated claim must cite its original post.
- Position-only values with no event/source citation are excluded and reported.
- The migration writes to V2 staging first.
- Production promotion is a separate explicitly backed-up transaction.

Acceptance criteria:

- [ ] Migrated claim count equals accepted source-event count minus named exclusions.
- [ ] Reprojected lifecycle agrees field-by-field with each accepted audited event.
- [ ] Exclusions are visible, not silently dropped.

## Phase 2 checkpoint

- [ ] Claim schema and writer are canonical.
- [ ] Newest-first text+vision extraction is working.
- [ ] Missing ancestry remains unresolved.
- [ ] Lifecycle projection uses accepted claims only.
- [ ] Recent Manas gold set passes twice.
- [ ] Audited legacy events are migrated or explicitly excluded.
- [ ] Full suite and checks are green on staging.

---

# Phase 3 — ship the Ledger and Symbol vertical slice

Goal: the real instance shows the latest accepted trade moves and a useful, evidence-backed stock workbench.

## Task P3.1 — build the V2 Ledger API

Description: Add a newest-event-first Ledger projection without breaking the archive endpoints.

Dependencies: Phase 2 checkpoint.

Files allowed:

- `traderlog/api/app.py`
- `traderlog/tests/test_ledger_v2_api.py`
- `traderlog/design/CONTRACTS.md`
- `traderlog/ui/src/api.js`

Required list fields:

- lifecycle ID
- handle and symbol
- current state
- latest accepted event kind/time
- entry/add/stop/exit fields when stated
- confidence and unresolved count
- evidence count
- data/provenance status

Default order: latest accepted event descending, then symbol, then lifecycle ID. Never default to original entry date.

Required filters:

- open-like / recently closed / all
- trader
- symbol
- accepted-event kind
- unresolved only
- minimum confidence

Acceptance criteria:

- [ ] A recent close sorts above an old open position.
- [ ] Partial and full closes are distinct.
- [ ] Quarantined/provisional claims are excluded by default.
- [ ] Detail returns exact claims, links, posts and media.

## Task P3.2 — rebuild the Ledger UI

Description: Replace the stale position table experience with a latest-moves evidence workspace.

Dependencies: P3.1.

Files allowed:

- `traderlog/ui/src/screens/Ledger.jsx`
- `traderlog/ui/src/styles/ledger.css`
- `traderlog/ui/src/components/LifecycleRail.jsx`
- `traderlog/tests/test_ledger_v2_browser.py`
- `traderlog/design/WIREFRAMES.md`

Layout at 1920×1080:

- Left/main: latest accepted lifecycle rows with event kind/time prominent.
- Right rail: selected lifecycle claim/evidence chain.
- Compact filters above the main list.
- Evidence thumbnails beside the claims they support.
- Unresolved shown as `N unresolved` with disclosure.

No generic card grid and no decorative timeline.

Acceptance criteria:

- [ ] Manas's newest accepted move is visible without changing sort.
- [ ] Selecting a row shows exact source evidence.
- [ ] Full closes are visibly closed.
- [ ] Unknown values read “not stated”, never zero.
- [ ] No document/panel/image overflow at 1920×1080.

## Task P3.3 — expand the Symbol API

Description: Return one source-backed analytical payload for a validated NSE symbol.

Dependencies: P3.1.

Files allowed:

- `traderlog/api/app.py`
- `traderlog/derive/tape.py`
- `traderlog/tests/test_symbol_v2_api.py`
- `traderlog/design/CONTRACTS.md`

Required payload groups:

- identity and validation
- ascending daily OHLCV rows
- accepted claims and lifecycle events
- co-attention chronology
- tape-after-claim at fixed 1/5/10/20-session horizons
- existing `tape_metrics` stock diagnostics, with each metric's date and
  availability state
- recent `alpha_activity_signals` flags with their exact source session and
  deterministic inputs
- exact image/text levels
- coverage and staleness metadata
- evidence references

Acceptance criteria:

- [ ] Missing price history returns `validated:false` and empty prices.
- [ ] Missing forward session returns null, never zero.
- [ ] Every level retains source post/media and original label.
- [ ] Conflicting levels remain separate.
- [ ] Tape metrics and activity flags are absent/null with a named reason when
      their source tables have no valid row; they never fall back to zero.

## Task P3.4 — build the Symbol price pane

Description: Render real NSE candles, volume and accepted event markers using Lightweight Charts.

Dependencies: P3.3 and P1.2.

Files allowed:

- `traderlog/ui/src/screens/Symbol.jsx`
- `traderlog/ui/src/components/TradingViewChart.jsx`
- `traderlog/ui/src/styles/symbol.css`
- `traderlog/tests/test_symbol_chart_browser.py`
- `traderlog/design/WIREFRAMES.md`

Rules:

- Candles come only from `daily_prices` for the validated symbol.
- Marker labels distinguish entry/add/stop/partial/full exit.
- Marker hover/click opens evidence; it does not invent tooltips.
- Missing candles render one compact reason.
- The chart has an accessible textual finding.

Acceptance criteria:

- [ ] RATEGAIN and FCL render real candles when price rows exist.
- [ ] Accepted claim markers align to their session policy.
- [ ] No provisional or quarantined marker appears.
- [ ] Resize and cleanup produce no console error.
- [ ] Numeric zero remains visible; null is labelled unknown/not available and
      never rendered as zero.
- [ ] The exact last available candle date is visible; loading, empty and error
      states are compact and factual.
- [ ] A late response for a prior symbol cannot replace the current Symbol pane.

## Task P3.5 — build the Level Book

Description: Surface exact text/image-stated support, resistance, entry, stop and target levels.

Dependencies: P3.3.

Files allowed:

- `traderlog/derive/levels.py`
- `traderlog/tests/test_levels.py`
- `traderlog/ui/src/components/LevelBook.jsx`
- `traderlog/ui/src/styles/symbol.css`
- `traderlog/design/CONTRACTS.md`

Rules:

- Do not merge, average or convert levels into zones.
- Show author, time, level kind, exact value, source phrase/image note and confidence.
- Contradictions are a feature: label them as separate claims.
- Audit a sample of vision levels against actual pixels before production display.

Acceptance criteria:

- [ ] Every rendered level opens its source evidence.
- [ ] Conflicting values remain separate.
- [ ] Unreadable vision contributes no level.
- [ ] Price precision follows the binding visual rule.

## Task P3.6 — add tape and evidence rails

Description: Complete the Symbol workbench with tape-after-claim and chronological evidence.

Dependencies: P3.4 and P3.5.

Files allowed:

- `traderlog/ui/src/screens/Symbol.jsx`
- `traderlog/ui/src/components/TapeStrip.jsx`
- `traderlog/ui/src/components/EvidenceRail.jsx`
- `traderlog/tests/test_symbol_evidence_browser.py`
- `traderlog/design/WIREFRAMES.md`

Acceptance criteria:

- [ ] Tape numbers match API values exactly.
- [ ] Tape is labelled as market movement after the claim, not trader result.
- [ ] Chronology includes posts, replies, accepted claims and images.
- [ ] Source links and archived thumbnails work.
- [ ] Null tape/evidence fields retain a named unknown reason; empty evidence is
      one compact line and no future-wave chart or fabricated fallback appears.

## Task P3.7 — change primary navigation and complete acceptance

Description: Make Radar, Ledger and Traders the permanent tabs; route Symbol and archive Feed without losing deep links.

Dependencies: P3.2 and P3.6.

Files allowed:

- `traderlog/ui/src/App.jsx`
- `traderlog/ui/src/styles/app.css`
- `traderlog/tests/test_v2_navigation_browser.py`
- `traderlog/design/WIREFRAMES.md`
- `traderlog/design/DECISIONS.md`

Required behaviour:

- Default route: Radar.
- Visible tabs: Radar, Ledger, Traders.
- `?tab=SYMBOL&symbol=X` remains deep-linkable.
- Old Feed/Today, Breadth/Market and Library links redirect to the closest truthful V2 destination or an explicit archive route.
- Review count remains visible and opens Ledger review work.

Acceptance criteria:

- [ ] Refresh preserves deep link and selected symbol/trader/lifecycle.
- [ ] No dead tab or empty future screen remains in navigation.
- [ ] 1920×1080 shell aligns to the centered 1680px grid.
- [ ] Zero console/network/overflow defects on Radar, Ledger, Traders and two Symbol cases.

## Phase 3 checkpoint

- [ ] Real instance defaults to Radar.
- [ ] Ledger is newest-accepted-event-first and shows genuine closes.
- [ ] Symbol shows real candles, accepted markers, Level Book, tape and evidence.
- [ ] Manas recent acceptance cases are visible end to end.
- [ ] Full tests, build and checks are green.
- [ ] Orchestrator personally verifies all screens at 1920×1080.
- [ ] Phase 3 completion and attribution records exist.

---

# Phase 4 — Radar, themes and trader intelligence

## P4.1 Radar change stream

- Show new, strengthening, fading and contradicted attention since the prior successful run.
- Keep raw attention separate from accepted trade commitment.
- Show freshness, distinct-trader independence and coverage debt.
- Do not display an unvalidated composite predictive score.

## P4.2 Disagreement stream

- Wire the existing cited disagreement derivation through a named API payload.
- Show same-symbol opposing claims and materially different stated levels.
- Keep disagreement evidence beside the claim; never turn it into a sentiment
  score or winner/loser label.

## P4.3 Theme rotation

- Repair cited theme materialization.
- Preserve exact source labels and an alias review table.
- Show trader breadth, symbol breadth and fixed-window acceleration.
- Link every theme to its constituent evidence.

## P4.4 Market chorus and freshness

- Fold breadth and cited trader market views into Radar's Market mode.
- Show disagreement, not a simplistic right/wrong score.
- Label XP/MBI agreement as model agreement, never correctness.
- Show last price/breadth/derivation session and a named stale state.

## P4.5 Trader timing profile

- Use accepted entry/add/trim/close claims only.
- Show distributions with `n`, missing coverage and session definitions.
- Separate stated results from tape outcomes.

## P4.6 Setup calibration

- Compare explicit `play_type` labels with tape metrics at the claim timestamp.
- Publish sample size, missing coverage and classifier confusion examples.
- Do not publish per-setup rates until the labelled sample passes its fixture
  quality gate.

## P4.7 Evidence-backed Playbook

- Derive candidate rules from repeated exact phrases plus accepted behaviour.
- Show supporting posts, counterexamples, confidence and sample size.
- Fall back to a cited vocabulary index when evidence is too weak for a rule.
- Never produce a composite credibility score.

Phase 4 gate: a reader can answer what is gaining attention, what market state traders are discussing, and what a trader repeatedly does—with citations and without a recommendation.

---

# Phase 5 — production live ingestion and Telegram

## P5.1 Official X adapter

- Implement behind `fetch_timeline(handle, since)`.
- Include replies, conversation/reference fields and media expansions.
- Use per-handle `since_id` watermarks advanced only after archive/media/DB success.
- Enforce configured market calendar and daily read ceiling.
- Never depend on Chrome cookies in production.

## P5.2 Live market-hours loop

- Prefer filtered stream when entitled; otherwise fair 30–60 second polling.
- Catch up at startup, market open, reconnect, periodically and shutdown.
- Handle 401/403/429/5xx and half-open connections.
- Preserve reply capture and media hashing.

## P5.3 Fast claim path

- Explicit text entries: provisional claim and cited outbox item within 60 seconds of receipt.
- Image-dependent entries: immediate evidence notice, later vision-enriched amendment.
- Ambiguous posts: review queue, no confirmed-entry language.

## P5.4 Telegram outbox

- Remain dry-run until owner enables sending.
- Idempotency key prevents duplicate alerts.
- Corrections supersede earlier messages rather than silently editing history.
- Every message links to source evidence and TraderLog detail.

Phase 5 gate: three real traders over seven market sessions, forced reconnect recovery, zero duplicate alerts, no paid overage, archive/hash parity, and measured source-to-outbox latency.

---

# Phase 6 — release hardening

1. Run the full suite twice from clean processes.
2. Run checks twice and compare `STATE.json` outputs.
3. Rebuild UI from a clean `dist` and verify runtime identity.
4. Audit every screen at 1920×1080.
5. Save one final 1920×1080 screenshot per accepted surface under a dated
   `traderlog/output/playwright/v2-release/` directory and review it against the
   binding V2 wireframe.
6. Sample-audit vision levels against image pixels.
7. Sample-audit Ledger lifecycle chains against posts.
8. Verify backup/restore and staging promotion procedure.
9. Verify no production mock rows and no quarantined lifecycle visibility.
10. Verify secrets are absent from source, SQLite, logs and UI payloads.
11. Update `CANONICAL.md`, `CONTRACTS.md`, `WIREFRAMES.md`, `DECISIONS.md`, `AUDIT_LEDGER.md`, `HANDOFF.md`, `TASKS.md` and `STATE.json` through checks.

Release is blocked if any assertion is skipped, any screen crashes, any number lacks evidence or any lifecycle row has unapproved provenance.

---

## 6. Visual acceptance checklist for every V2 screen

- [ ] 1920×1080 viewport only for acceptance.
- [ ] Centered 1680px content grid at x=120.
- [ ] Warm-neutral light canvas and token-only colours.
- [ ] Radius zero.
- [ ] One 1px structural rule per major region.
- [ ] No nested bordered boxes.
- [ ] No gradient, glow, blurred shadow, pure black or raw component hex.
- [ ] Sentence case except compact navigation and single-word column labels.
- [ ] Mono only for numbers, dates, confidence and identifiers.
- [ ] One dominant number at most.
- [ ] Every percentage/average shows `n`.
- [ ] Every chart has a scale or direct labels and an accessible sentence.
- [ ] No decorative chart.
- [ ] Empty data is one compact factual line.
- [ ] Images are contained and never enlarge a grid.
- [ ] Zero document and panel overflow.
- [ ] Keyboard navigation and visible focus work.
- [ ] Zero console errors and failed requests.

---

## 7. Completion report template for each task

```markdown
# HANDOFF_<TASK>_COMPLETED

Status: complete | partial | blocked
Attribution-ID: <exact ledger ID>

## Goal
<one sentence>

## Files changed
- <absolute/relative path and purpose>

## Baseline
- `python traderlog/run_checks.py`: <exact result>
- pre-existing failures: <exact list>

## Implementation
1. <specific change>
2. <specific change>

## Acceptance evidence
- Criterion 1: PASS/FAIL — <command, query or browser measurement>
- Criterion 2: PASS/FAIL — <command, query or browser measurement>

## Verification
- focused tests: <exact command/output>
- whole suite: <exact command/output>
- UI build: <exact command/output or n/a>
- checks: <exact command/output>
- git diff --check: <result>
- 1920×1080 browser: <result or n/a>

## Database impact
- DB path: <absolute resolved path or n/a>
- backup: <path, size, hash or n/a>
- before counts: <table counts>
- after counts: <table counts>
- integrity/FK: <results>

## Unresolved
- <honest remainder, or none>

## Prohibited actions confirmation
- no commit made
- no `manas_os/` write
- no file outside allowlist changed
- no mock production data
```

---

## 8. Program-level Definition of Done

TraderLog V2 is complete only when all statements below are true:

- The default screen answers what deserves review now.
- Ledger shows the latest accepted moves, including genuine closes, with evidence.
- Symbol pages show real NSE candles, accepted claim markers, exact levels and tape-after-claim.
- Trader pages show cited behavioural patterns with sample size and counterexamples.
- Missing ancestry, values and coverage remain visibly unresolved.
- No deterministic or provisional lifecycle is presented as accepted truth.
- Live ingestion captures replies/media and recovers after restarts within the owner-approved quota.
- Telegram sends only after explicit enablement and never duplicates an event.
- Full tests, checks, build and 1920×1080 browser acceptance pass.
- Canonical docs, contracts, backlog, handoff and model attribution agree with the running instance.
- No commit is made by an executor; the maintainer performs QC and commits verified slices.

Risks:

- The audited backup can contain valid rows whose schema or evidence shape no longer matches current code. Recovery must exclude them explicitly rather than coerce them.
- Non-null vision JSON does not prove accurate visual transcription. Level Book remains blocked until sampled pixel verification passes.
- Missing X ancestry limits automatic lifecycle linkage. More review work is preferable to false closes.
- Tape-after-claim measures subsequent market movement, not causality, skill or a recommendation.
- The worktree is already heavily dirty. File allowlists and per-task diffs are mandatory to avoid overwriting parallel work.
- Official X live ingestion and Telegram sending remain separately gated operational work.
