# Unified desk — integration plan & task crosswalk

Created 2026-08-28. **Refreshed 2026-08-29** to V2/D10–D17 (EOD-first).
Companion to `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (controlling design/build
spec, including §12 as-built system design; V1 is historical) and
`plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`. This file is the one-page answer to
"which unified task maps to what already exists, what's done, and what runs
next". Statuses live in `unidesk/TASKS.md`; this file holds the mapping,
not the status.

## Task-numbering crosswalk (DECISIONS D3)

| Unified task | Meaning | Existing asset | Status home |
|---|---|---|---|
| U-P0.1 | repo + data-authority map | `unidesk/design/DATA_AUTHORITY.json` + `.md`; machine-checked | TASKS COMPLETED |
| U-P0.2 | shared contracts | `unidesk/contracts/*` (scaffolded, schema-only) | TASKS COMPLETED (slice) |
| U-P0.3 | point-in-time market store | in-memory store + D15 bhavcopy ingest; persistent adapter still owner-gated | TASKS `[~]` |
| U-P0.4 | FYERS capability audit | = orderflow's "P0.1". Offline half done; live half owner-gated; **demoted off EOD critical path (D10)** | TASKS `[~]`, N7 only |
| U-P0.5 | continuous depth recorder | offline recorder fixture-proven; live session open; **N7 only (D10)** | TASKS `[~]` |
| U-P1.x–U-P2.x | momentum + setups + geometry | built: feature library, 8 detectors, gold fixtures, geometry, entry/stock quality | N1–N3 in TASKS; U-P1/P2 placeholders are stale |
| U-P3.x | orderflow integration | apparatus exists; **deferred to N7** | DROPPED/DEFERRED in TASKS |
| U-P4.x | TraderLog Lite | `traderlog/` (own chain) | OUTSTANDING |
| U-P5.x | Context Judge + deterministic policy | nothing built | OUTSTANDING |
| U-P6.x | unified terminal (UI manual V2) | `unidesk_terminal/` fixture prototype; does not fulfill N8 | TASKS N8 `[~]` |
| U-P7.x | research spine + promotion gates | N4 first slice: freeze, expanding walk-forward, planted-bug leakage | TASKS N4 `[~]` |
| U-P8.x | discipline/journal | nothing built | explicitly later |
| UI-P1–UI-P4 | UI implementation sequence | Home screen + shell in `unidesk_terminal/` | parallel track, not W-H |

Rule-number crosswalk (for reading old records): orderflow R1–R9 ≈ unified
R8, R9, R10, R11, R12 + the no-routing/nulls invariants, which the unified
manual restates as R3/R12.

## Sequencing (EOD-first, D10/D13)

```
N1 nightly report on real bhavcopy     ← DONE enough to run; live download untested
N2 gates + primitives + R0             ← DONE; midcap SMA50 gate added D16/D17
N3 files (CA-with-ratios, 2016 bars, PIT membership, MTO/F&O)
   industry map: Chartsmaze + D18 nexus fill (2,772) — done; not PIT
N4 remainder (archive-wide outcome attach, ablation, 4y/1y when calendar allows)
   parquet event store + attach helper — done; not 1M-bar attach
N5 experiments A/B                     ← blocked on applied CA series
N6 presets + AI analogue               ← AI forbidden until Phase 0 acceptance (D14)
N7 live module                         ← owner request only
N8 terminal                            ← data on every panel; prototype exists
```

The old live-FYERS-first sequence is retained only for N7. It does not gate
N1–N5. Predictive AI does not start before Phase 0 acceptance (constitution).

## Where records live

| Kind | Location |
|---|---|
| Unified task status | `unidesk/TASKS.md` |
| Next-session intent | `unidesk/HANDOFF.md` |
| Locked calls | `unidesk/DECISIONS.md` |
| Unified-build work log | `unidesk/design/MODEL_WORK_LOG.jsonl` (14-key, machine-checked) |
| Orderflow-slice work log | `orderflow/design/MODEL_WORK_LOG.jsonl` |
| Machine gate | `python unidesk/run_checks.py` (exit 0 required at wave close) |

## Known risks / open seams

- **Numbering collision** between the two manuals' `P0.x` — resolved by the
  `U-` prefix (D3); old records keep their historical meaning.
- **`desk/` naming** — resolved by `unidesk/` (D2); decoy warnings live in
  DESK.md and CANONICAL.md.
- **`desk/contracts` boundary evolution** — when other packages start
  consuming contracts, keep the FYERS-names-in-one-file rule absolute and
  keep imports one-way (D4); the orderflow boundary tests must stay green.
- **Root `MODEL_WORK_LOG.jsonl`** diverges from the validated schema — legacy,
  left untouched (D5).
- **Everything feed-related is Unverified** until the owner-run live session
  (cadence, TBT provisioning, subscription limits, optional fields,
  `exch_feed_time` semantics, depth-size scaling — see N1 stop report).
