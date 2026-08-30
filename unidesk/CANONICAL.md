# CANONICAL — what is real in the unified desk build

**Read this before touching anything.** Last verified: 2026-08-29, branch
`emergent`. Rationale (inherited from TraderLog): this repo contains decoys
that "look alive"; a stale CANONICAL.md is worse than none, because it is
trusted.

Controlling manuals (authority order):

1. `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` — controlling design/build spec
   (EOD-first; as-built D14–D18). V1 is historical.
2. `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` — companion product/UI manual;
   on any wording-vs-data conflict the build manual wins.
3. `plan/SWING_EDGES_TECHNICAL_SPEC.md` — frozen research champion (D11).
4. `plan/PHASE0_DATA_BUILD_SPEC.md` — warehouse contract for N3–N4 (D14).
5. `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md` — AI rules; no
   predictive AI until Phase 0 acceptance.
6. `plan/ORDERFLOW_BUILD_MANUAL.md` — child reference for N7 internals only.
7. `plan/UNIFIED_DESK_INTEGRATION_PLAN.md` — task crosswalk + sequencing.

## 1. What is actually built today

| Thing | State | Evidence |
|---|---|---|
| `orderflow/` Phase-0 apparatus (schemas, FYERS adapter, websocket manager, capability auditor) | Built and offline-proven. 62 tests pass; boundary-enforced. | `orderflow/design/handoffs/P0.1_CAPABILITY_AUDIT_COMPLETED.md` |
| `orderflow/capability.json` | **SYNTHETIC ONLY** (`data_source: synthetic`). Not a measurement of the real feed. | regenerate with `--source live` after the owner-run session |
| Live FYERS transport (`run_live_session.py` + owner shim) | NOT BUILT — preparation only (protocol verified, venv `.venv-orderflow/` prepared, `reconnect=False` design fixed) | `orderflow/design/handoffs/N1_LIVE_SESSION_PREP_STOP.md` |
| U-P0.5 offline recorder core (Parquet writer, DuckDB views/replay, feed health, lifecycle/gap persistence, launcher integration) | Built and fixture-proven. **Live acceptance remains open**; no real FYERS session was recorded. | `orderflow/design/handoffs/N2_OFFLINE_RECORDER_CORE_COMPLETED.md` |
| U-P0.1 repository/data-authority inventory | Built and machine-checked: 20 logical persistent stores owned/classified, 12 unified fields single-authority checked, legacy lifecycle quarantine enforced in the manifest validator. | `unidesk/design/DATA_AUTHORITY.md`, `unidesk/design/handoffs/HANDOFF_U_P0_1_DATA_AUTHORITY_COMPLETED.md` |
| `unidesk/` governance + contracts | Built 2026-08-28. | `unidesk/design/handoffs/HANDOFF_U_P0_GOVERNANCE_AND_CONTRACTS_COMPLETED.md` |
| Momentum feature library + 8 setup detectors + geometry + nightly scan/report | Built. Gold fixtures (P2.3) frozen. | `unidesk/design/handoffs/HANDOFF_W_E_GOLD_FIXTURES_COMPLETED.md` |
| Clean-room `base_pattern` detector | Built as research detector (public BananaPatterns metrics, YASHHV-calibrated). Not in nightly registry. Not vendor parity. | `unidesk/momentum/detectors/base_pattern.py` |
| R0 regime classifier | Built. Midcap 150 vs SMA50 when ≥50 sessions (`breadth_and_midcap150_sma50`); else `breadth_only`. Nifty SMA200 computable, not yet in the label rule. | `regime.py` + D16/D17 |
| Phase 0 data primitives (calendar, costs, leakage, invariants, delivery lag) | Built. Phase 0 is not accepted. | D14 handoff |
| EOD archive | **D15:** `data/bhavcopy/` 1,004,896 bars, 2024-09-02 → 2026-08-28. Extractor folder is a stale subset. | nightly `--backlog` default |
| Chartsmaze event tables | IPO dates, circuit revisions (PIT), announcement review queue (no auto-adjust), vendor breadth. Provisional / SECONDARY_REPAIR. | `unidesk/momentum/data/events.py` |
| Confirmed CA table | 4 close-to-close 2:1 names applied as a derived scan view. Raw bhavcopy never rewritten. Official NSE CA feed still open. | `unidesk/config/confirmed_actions.csv` |
| Industry mapping | **D18:** Chartsmaze 2,423 + nexus fill 349 (Chartsmaze wins). Total 2,772. Vendor labels, not NSE official. | `data/market/reference/industry_mapping.parquet` |
| N4 research spine | Candidate freeze (includes negatives), parquet `date=` store, outcome attach (next-bar), expanding walk-forward, planted-bug leakage suite. 4y/1y folds and archive-wide attach still open. | `unidesk/research/{candidates,event_store,walkforward,leakage_suite}.py` |
| NSE index daily + India VIX | **D17** manas RO extract + **D16** overlay: Nifty 50 / VIX from 2021-06-01 (1,299 / 1,293); Midcap 150 / 500 / Smallcap 250 from 2024-07-08 (533). 18 PIT universe snapshots. Price index, not TRI. | `indices.parquet` via `manas_extract.py` |
| Judge, analogue engine, predictive AI | NOT STARTED. Constitution forbids AI until Phase 0 acceptance (D14). | — |
| Terminal UI | Parallel prototype in `unidesk_terminal/` on fixtures; does not fulfill W-H. | `unidesk_terminal/HANDOFF.md` |

**The EOD critical path is N3 remainder** (apply CA-with-ratios to bars;
optional D-decision to adopt manas `daily_prices` 2021–; PIT membership
before Jul 2026) then N4 remainder. Index series and a short PIT window
already landed (D16/D17). The live FYERS session remains owner-gated and
applies only to the optional live module (D10/D13). Predictive AI is
forbidden until Phase 0 acceptance (D14).

## 2. Single-writer map

| Store | Sole writer |
|---|---|
| `orderflow/capability.json` | `orderflow/checks/capability_audit.py` |
| `orderflow/data/raw/**` (Parquet) | `orderflow/storage/recorder.py` through `orderflow/storage/parquet_writer.py`; owner launcher integration exists, but only fixture writes are proven |
| `orderflow/design/MODEL_WORK_LOG.jsonl` | orderflow sessions (append-only) |
| `unidesk/STATE.json` | `unidesk/checks/runner.py` (machine-written; humans read it) |
| `unidesk/design/DATA_AUTHORITY.json` | U-P0.1 governance wave only; later changes require evidence + validator pass + ledger record |
| `unidesk/design/MODEL_WORK_LOG.jsonl` | unidesk sessions (append-only) |
| `unidesk/TASKS.md`, `HANDOFF.md`, `DECISIONS.md`, `CANONICAL.md` | the session executing a unidesk wave, per the rules at the top of each file |
| `traderlog/**`, `manas_os/**`, `backend/**`, `legacy/**` | NOT OURS. Read-only for reference. Never modified from this chain. |

Rule: if you need to write a store that is not yours, you are probably
building the wrong thing — say so in `HANDOFF.md`.

## 3. Decoys — names that look like this and are not

| Name | What it actually is |
|---|---|
| `DESK.md` (root) | The repo map. A document, not a package. |
| `manas_os/desk/` | The retired Manas OS UI. Legacy. Do not extend. |
| root `MODEL_WORK_LOG.jsonl` | ONE legacy record in a schema that predates and diverges from the validated 14-key schema (no `id`, absolute paths). Do not append to it; do not "fix" it (D5). |
| `orderflow/capability.json` | Synthetic until regenerated `--source live`. |
| `plan/codex.md`, `gemini.md`, `glm.md`, `ox.md`, `v2.md` | Per-model session manuals from earlier waves. Historical. |

## 4. Package boundaries

- `unidesk` → `orderflow`: allowed, ONE-WAY (D4). The governance/contracts
  layer may read orderflow code and outputs.
- `orderflow` → anything cross-project: BANNED (its own tests enforce this).
- Anything → `traderlog` / `manas_os`: BANNED. Adopt by copying with a
  provenance header (`traderlog/adopted/activity.py` is the worked example).
- FYERS wire vocabulary lives in exactly one file:
  `orderflow/market_data/fyers_adapter.py`.
- The live-session owner shim (which imports `fyers_apiv3` and sees env
  credentials) lives OUTSIDE `orderflow/` — repo-root `scripts/` — by design.

## 5. Where things belong

| Artifact | Home |
|---|---|
| Unified-build task status | `unidesk/TASKS.md` |
| Persistent-store and field authority | `unidesk/design/DATA_AUTHORITY.json` (machine source) + `DATA_AUTHORITY.md` (human guide) |
| Session intent for the next runner | `unidesk/HANDOFF.md` |
| Irreversible/expensive calls | `unidesk/DECISIONS.md` (append-only) |
| Completed-work reports | `unidesk/design/handoffs/HANDOFF_*_COMPLETED.md` (+ orderflow's own for orderflow-slice work) |
| Model-work records | the owning package's `design/MODEL_WORK_LOG.jsonl` (14-key schema, machine-checked) |
| Scratch/probe scripts | nowhere permanent — delete them when done (CANONICAL hygiene inherited from TraderLog) |
