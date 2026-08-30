# GOAL — the unified desk build, driven to completion

Set 2026-08-29 by owner direction ("go on until the entire tool build is
done"). This file is the standing goal, wave queue, and checkpoint/elevation
protocol. Controlling manuals:
`plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` + `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`.
V1 manuals are historical (D13).

## The goal, in one line

**Every component of the unified desk that can be honestly built and tested
offline is built, tested, and recorded — with hard stops only at the points
the manuals reserve for the owner (live session, data accumulation, phase
gates) — so that when live data lands, the desk is assembly, not construction.**

## Non-negotiable reading of "done"

- "Done" per component = manual acceptance boxes checked WITH evidence
  (tests, measured numbers), not code-written.
- Hard stops (cannot be engineered around, owner-gated):
  1. Live FYERS session (U-P0.4 live half) — next market day, Mon 2026-08-31.
  2. Depth recording accumulating (U-P0.5 full acceptance needs a real session).
  3. Phase 0 checkpoint → Phase 1+ promotion is an OWNER decision.
  4. TraderLog claim-inference decision (blocks U-P4.x only).
  5. Ablation (U-P3.10/U-P7) needs recorded live outcomes over weeks.
- What is NOT a stop: momentum (U-P1) and setup/geometry (U-P2) are EOD-data
  deterministic work; they are built offline with gold fixtures in parallel,
  and their PRODUCTION promotion still waits at the Phase 0 checkpoint.

## Wave queue (autonomous, in order)

| Wave | Content | Depends on |
|---|---|---|
| W-A | U-P0.5 offline core: parquet writer, DuckDB repo, feed-health state machine, replay — all fixture-proven | Offline core complete; owner live session still required for full U-P0.5 acceptance |
| W-B | U-P0.3 point-in-time market store (`get_market_state`) | data-home decision (owner, cheap) |
| W-C | U-P1.1–P1.9 momentum engine (trend, RS, participation, ADR/ATR, AVWAP, sector, circuit, stock quality) | W-B |
| W-D | U-P1.10 Model A baseline harness (labels, metrics) | W-C |
| W-E | U-P2.1–P2.8 setup primitives, detectors, geometry, entry quality | W-C |
| W-F | U-P3 offline: subscription tiers, trigger state machine, slow-feed-safe features, flow confidence, validity window, replay — built against fixtures, PROMOTED only after N1 gate | W-A + N1 |
| W-G | U-P7 research spine (event store, leakage suite, ablation ladder scaffolding) | W-D |
| W-H | U-P6 terminal (UI manual) — shell only until data exists | W-F data |

Each wave closes with: tests green, TASKS.md evidence, ledger record,
`run_checks.py` exit 0, CANONICAL §1 refreshed if reality changed.

## Checkpoints & model-elevation protocol

Elevation = a fresh-context independent pass at the defined gate. Two forms,
both recorded in the ledger with honest identity basis:

- **Subagent elevation** (executor-invoked): a reviewer subagent with zero
  prior context re-audits the wave against its acceptance list. Identity is
  `self_reported` (model not selectable from inside the harness).
- **Owner elevation ★** (owner-invoked): the owner opens a fresh session on
  the full GLM 5.3 model (or any other model) pointed at the wave's handoff.
  This is the stronger form and is REQUIRED at the ★ gates below, because
  same-model review shares blind spots exactly where these waves are risky.

| Checkpoint | When | Elevation |
|---|---|---|
| CP-1 ★ | Phase 0 complete (live session done, recorder running) | owner-model review of all Phase 0 handoffs + owner signs the Phase 0 checkpoint |
| CP-2 | After W-A/W-B (recorder + market store) | subagent code-reviewer: single-writer, null, point-in-time claims |
| CP-3 ★ | After Model A baseline exists (W-D) | owner-model leakage audit — leakage bugs are systematic; this is the highest-risk gate in the build |
| CP-4 | After setups/geometry (W-E) | subagent audit: gold fixtures, deterministic-validity discipline |
| CP-5 | Flow features built (W-F) | subagent audit + owner decision integrating the N1 capability gate |
| CP-6 ★ | Pre-production advisory (manual P7.9) | owner-model promotion review against the full promotion checklist |

Rule: a checkpoint pass does not self-certify. The reviewer's findings land as
ledger records; open findings block the next wave.

## Status

- W-A: offline core complete; U-P0.5 remains partial at the owner/live gate.
- U-P0.1: repository/data-authority inventory complete and machine-checked.
- W-B: blocked on the owner data-home decision; do not invent a writer or store.
- CP-2: **done 2026-08-29** — subagent review PASSED both targets; 1 MAJOR
  (manifest store path) fixed, minors 3/4/5/6/8 fixed, minor 7 (DuckDB
  replay ORDER BY tiebreaker) accepted as recorded debt under U-P0.5.
  See HANDOFF_CP2_REVIEW_COMPLETED.md.
- W-C: **COMPLETE 2026-08-29** — trend, participation, ADR/ATR, RS, AVWAP,
  circuit risk, and the P1.9 stock-quality snapshot (decomposable
  weighted-mean score; nulls reduce coverage, never zeroed; hard gates ride
  beside the score; weights are caller-supplied config, R14/R15).
- W-D: **started** — P7.2 outcome labels landed (MFE/MAE, R-multiples,
  stop-hit first-touch, breakout hold/fail with an honest UNRESOLVED state).
- W-E: **COMPLETE 2026-08-29 including P2.3 gold fixtures** — all 8 setup
  detectors via a shared rule engine; each detector separately disableable;
  geometry + entry-quality as before. Gold fixtures: 32 frozen real cases
  (2 positive + 2 negative per detector) harvested from the bhavcopy
  backlog across 2025-11-14 … 2026-07-03. Optional GBT/similarity
  (P2.9/P2.10) remain deferred until data justifies.
- N2: **COMPLETE 2026-08-29** — universe gates (adopted by copy), spec
  feature-library primitives, R0 regime classifier (breadth_only mode) —
  real breadth history computed (233 sessions; Jun/Jul 2026 = BULL).
  222 tests.
- N1: **report ran on real data 2026-08-29** — 2,563 symbols scanned,
  65.9% above EMA50, burst candidates named; report renderer + universe
  scan + nightly CLI landed (209 tests).
- MANUALS V2 (D13): Build + UI/UX manuals reworked for the EOD-first
  product; wave queue re-planned as N1-N8 (W-F live parts deferred to the
  optional live module N7). See plan/UNIFIED_DESK_BUILD_MANUAL_V2.md.
- RESEARCH PROGRAM ADOPTED (D11 + D14): swing-edges spec = deterministic
  champion; constitution = AI testing rules (L0–L5, L1.5 before any
  encoder, 3-D promotion); Phase 0 data-build spec = N3–N4 warehouse
  contract. Predictive AI is forbidden until Phase 0 acceptance. Gap
  table: `unidesk/design/PHASE0_GAP.md`.
- PHASE 0 PRIMITIVES (D14): trading calendar, cost model, decision-time +
  embargo, OHLC/delivery invariants, delivery lag freeze.
- N3 this session (D15): extended EOD archive `data/bhavcopy/` — 1,004,896
  bars / 477 sessions / 2024-09-02 → 2026-08-28; Chartsmaze event tables;
  known-split close-to-close confirmation on four real 2:1 names. Not
  Phase 0 complete — 2016 history, official CA-with-ratios, membership
  before Jul 2026 still open.
- REAL DATA UNLOCKED 2026-08-29: D9 extractor subset (646k) superseded as
  ingest default by D15 archive (1.00M bars). Publication policy unchanged.
- D16 this session: NSE index daily (nse-archives `ind_close_all`) — 59
  sessions overlay; R0 Midcap-150-vs-SMA50 gate. Finstack MCP was not
  connected. niftyindices.com historical path failed Cloudflare.
- D17 this session: manas.db RO extract (no `import manas_os`). Nifty 50 /
  VIX from 2021-06-01 (1,299 / 1,293); Midcap 150 / 500 / Smallcap 250 from
  2024-07-08 (533); 18 dated universe snapshots. manas `daily_prices`
  inventoried, not adopted. Build Manual V2 rewritten as the as-built
  design spec (§0.1–§15).
- D18 this session: Chartsmaze is the primary industry map; nexus CSV
  fills 349 unmapped names only (total 2,772). Taxonomies must not mix.
- N3 CA this session: four confirmed 2:1 names applied as a derived scan
  view; raw bhavcopy untouched; official CA-with-ratios still open.
- N4 this session: candidate freeze (includes negatives), parquet `date=`
  event store, nightly freeze, outcome attach (next-bar fill; UNRESOLVED
  if no future). Expanding walk-forward + 5-session embargo, planted-bug
  leakage suite. 4y/1y folds refused on the short calendar (honest).
  Archive-wide attach and ablation still open.
- Everything else: queued behind its stated dependency or phase gate.
