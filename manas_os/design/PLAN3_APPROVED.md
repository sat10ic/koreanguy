# Manas OS Rework — Approved Delta Execution Plan

## Summary

Improve the shipped V4 system rather than rebuilding it. Preserve the current workflow, deterministic engine, four-phase regime model, scored objections, living shortlist, progressive disclosure, agent records, and modern model roster.

Binding hierarchy:

1. **TradeTM:** market, opportunity, execution, management, and review spine.
2. **Manas Arora:** concrete scanner, setup, and entry overlay.
3. **Stocksgeeks:** specialist modules, particularly IPO structures and MBI/breadth.
4. **Indian outcome evidence:** determines confidence; teacher provenance alone does not prove alpha.

Run corpus completion alongside product work. Prioritize visible liveness and staged reasoning while the larger lifecycle engine develops in advisory/paper mode.

## Implementation Changes

### 1. Normalize the corpus ledger

Extend the verified map in `PLAN1_REVIEW.md`; do not regenerate the current-state audit.

Normalize all TradeTM coverage records to:

- `FULL`
- `DUP`
- `GAP`
- `PARTIAL`
- `SAMPLED`
- `META`

Requirements:

- Normalize case and synonyms before calculating coverage.
- Confirm `DUP` through content hashes or normalized-text comparison.
- Record why `PARTIAL` and `SAMPLED` sources remain incomplete.
- Read only unique `GAP`, `PARTIAL`, and `SAMPLED` sources.
- Maintain per-source checks for fidelity, doctrine extraction, conflicts, implementation mapping, and audit date.
- Prioritize execution, management, selling, prioritization, MAE/MFE, D2/EP, IPO, missed trades, and system construction.
- Allow verified findings to improve explanations and advisory prompts immediately.
- Do not let corpus findings change locked risk or live execution rules without replay evidence and approval.

### 2. Stage the existing agent reasoning

Restructure reasoning as:

1. TradeTM context and execution stage.
2. Arora setup/timing overlay where applicable.
3. Stocksgeeks specialist overlay where applicable.
4. Devil’s advocate.
5. Deterministic risk validation.

Keep the existing accuracy-weighted chair and tuned model seats. This is a context and prompt-structure change, not a roster replacement.

Cost controls:

- Run cheap context classification for all candidates.
- Invoke specialist stages only when relevant.
- Reserve the full debate, strong chair, and vision stack for disagreement cases and finalists.
- Persist which stages ran, which were skipped, their model, latency, tokens, and reason.
- Prevent agent outputs from writing or modifying deterministic entry, stop, target, or quantity.

### 3. Ship durable Live Work early

Wrap existing pipeline functions in persistent execution records:

- `jobs`
- `job_steps`
- `job_events`
- `job_artifacts`

Events cover:

- Bhavcopy and ChartsMaze acquisition;
- data validation and freshness;
- scanner progress and funnel counts;
- watchlist changes;
- agent queued/running/completed/failed states;
- partial debates;
- chart and vision artifacts;
- deterministic validation;
- coach, journal, lesson, and digest completion.

Interfaces:

- `POST /api/jobs`
- `GET /api/jobs/{id}`
- `GET /api/jobs/{id}/events`
- `GET /api/jobs/{id}/events/stream`
- `POST /api/jobs/{id}/cancel`
- `POST /api/jobs/{id}/steps/{step_id}/retry`

Use SSE with cursor-based polling fallback. Keep Fyers market ticks isolated to the later WebSocket/intraday layer.

Add a persistent Live Work drawer with:

- completed/total stages;
- current stage and agent;
- elapsed time and defensible ETA;
- source-download progress;
- expandable artifacts;
- warnings, degraded states, retry, and cancellation;
- replay after completion or reload.

Confirmed data stays visible while work runs. Remove refresh-dependent flows, generic whole-page loading, and native browser prompts.

### 4. Complete the evidence-status service

Use one statistical authority derived from existing expectancy data.

Statuses:

- `VALIDATED`
- `PROMISING`
- `EXPERIMENTAL`
- `UNPROVEN`
- `CONTRADICTED`

Each assessment includes:

- setup and regime;
- sample size;
- net-R result and horizon;
- liquidity treatment;
- point-in-time integrity;
- source doctrine;
- last evaluation date;
- status rationale;
- sample gap to the next status.

UI rules:

- Most initial states may correctly be `EXPERIMENTAL` or `UNPROVEN`.
- Frame this as earned confidence: “We do not claim evidence the journal has not earned.”
- Show the observations required to reach the next status.
- Never weaken thresholds to produce more positive labels.
- Display status consistently across Scanners, Shortlist, Debate, Trade Plan, Positions, and Journal.
- Keep practitioner provenance visually distinct from measured Indian expectancy.

### 5. Build the advisory trade-lifecycle engine

Classify plans as:

- persistent momentum;
- absolute momentum;
- velocity;
- magnitude;
- hybrid;
- EP;
- D2;
- IPO;
- reversal.

Attach a versioned management template to each plan and journal trade:

- entry confirmation;
- initial-risk behavior;
- risk-free transition;
- holding philosophy;
- mechanical stop rules;
- judgment-based profit-management principles;
- permitted pyramiding/re-entry behavior;
- thesis failure and structural-decay evidence.

Hard boundary:

- Mechanical stop and safety rules may be deterministic and numeric.
- Profit management remains `JUDGMENT` unless an Indian point-in-time outcome cohort has at least `PROMISING` status.
- Without that evidence, instructions such as “trail the 10 EMA,” “sell into strength,” or “ride persistent momentum” remain principles with visible evidence—not automatic numeric exits.
- A numeric profit target or automated profit trigger must cite its evidence assessment and validation version.
- Advisory templates cannot call or mutate deterministic risk writers.
- Locked sizing, stop caps, pyramiding defaults, and live alerts remain unchanged until replay and explicit approval.

Extend Coach and Journal to compare actual behavior with the original template and record MAE/MFE, conformance, overrides, and outcomes.

### 6. Visually refine the existing V4 shell

Keep:

**MARKET → SCANNERS → SHORTLIST → DEBATE → TRADE PLAN → POSITIONS → JOURNAL**

Refine:

- MARKET: dominant verdict, four-phase context, permitted opportunity types, risk budget, and primary breadth/leadership visualization.
- SCANNERS: organize presets under TradeTM opportunity stages while retaining Arora/Stocksgeeks ownership.
- SHORTLIST: emphasize missing confirmation, character change, next action, and event history.
- DEBATE: display staged reasoning, decisive disagreement, charts, and deterministic authorship.
- TRADE PLAN: make management type as prominent as entry, stop, and quantity.
- POSITIONS: lead with Coach action, template conformance, thesis state, ₹/R path, and hard-stop status.
- JOURNAL: lead with personal improvement, template outcomes, evidence progression, and carried-forward lessons.

Use contextual Evidence drawers rather than rebuilding the density system. Preserve the dark research-desk identity, but reduce terminal-like density through one dominant visualization per screen, setup-specific graphics, structured dialogs, retained-data loading states, and restrained state-change motion.

## Delivery Order

1. Normalize corpus statuses and extend the existing current-state review ledger.
2. Stage TradeTM → Arora → Stocksgeeks → devil’s advocate → deterministic validation.
3. Add durable jobs/events, SSE, and the Live Work drawer.
4. Add the unified evidence-status service and progression copy.
5. Specify and build lifecycle templates in advisory/paper mode.
6. Refine V4 screens around staged doctrine, evidence, and management.
7. Continue corpus delta closure throughout; integrate only verified findings.
8. Replay and paper-evaluate lifecycle behavior before proposing locked-rule changes.
9. Complete real-data, browser, source-fidelity, and beginner-workflow verification.

Fold current candidacy-relaxation, Strong Start/Arora focus work, and momentum measured-move work into this baseline; do not re-plan or duplicate them.

## Test Plan

- Normalize fixture coverage ledgers and verify stable counts independent of case or synonyms.
- Mechanically validate duplicate-source classifications.
- Verify staged prompts run only applicable specialist layers and preserve existing chair behavior.
- Confirm no agent or advisory template can mutate deterministic money math.
- Test SSE ordering, reconnect, cursor replay, duplicate suppression, retries, cancellation, restart recovery, and polling fallback.
- Confirm source downloads, scans, agents, charts, watchlist mutations, and failures appear live without refresh.
- Verify evidence statuses, next-status sample gaps, and contradictory cohorts.
- Fixture-test every management type and the numeric-versus-judgment boundary.
- Reject numeric profit triggers without a qualifying evidence record.
- Verify confirmed data remains visible during loading and failures.
- Run Market → Scanner → Shortlist → Debate → Paper Plan → Position → Exit → Journal using only primary UI copy.
- Cross-check rendered values against API payloads, deterministic writers, and source citations.
- Run real-data screenshot and interaction QC on every V4 surface.

## Assumptions

- Existing verified capabilities are retained.
- TradeTM is the doctrine of record; Arora is the practical overlay; Stocksgeeks is specialist.
- Corpus completion is parallel, not blocking.
- Live Work is prioritized before the slower lifecycle rollout.
- Lifecycle templates launch as advisory/paper behavior.
- Profit management remains judgment unless Indian outcome evidence supports numeric automation.
- Locked risk, sizing, pyramiding, and live-execution defaults require replay evidence and explicit approval.
- Separate local installations remain the initial deployment model.
