# HANDOFF D14 Phase 0 primitives — COMPLETED (first slice)

Date: 2026-08-29. Slice: adopt the research constitution + Phase 0
data-build spec, and implement the offline-provable primitives that do
not need missing official files.

Attribution-ID: attr-unidesk-d14-phase0-primitives-grok46-20260829-001

## Outcome

Owner documents adopted into `plan/` (canonical copies, D14):

- `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md`
- `plan/PHASE0_DATA_BUILD_SPEC.md`

Mapped onto the existing `unidesk/` tree (no parallel `src/` codebase).
Gap table: `unidesk/design/PHASE0_GAP.md`.

Primitives built and tested:

- trading calendar from *observed* sessions (not weekdays)
- conservative cash-delivery cost model (spec §1.4 defaults, versioned)
- decision-time contract + ±60-session same-symbol embargo
- OHLC / delivery invariants (violations named, never repaired)
- delivery same-session lag freeze (D14.3 / spec §14.2)
- provenance stamp (effective_date / available_at / built_at / source_version)

Predictive AI was not started. Constitution forbids it until Phase 0
acceptance.

## Files changed

- `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md`, `plan/PHASE0_DATA_BUILD_SPEC.md` (new canonical copies)
- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (research-program line)
- `unidesk/DECISIONS.md` (D14)
- `unidesk/research/{provenance,leakage,costs,delivery_lag}.py`
- `unidesk/momentum/data/{calendar,invariants}.py`
- `unidesk/momentum/DATA_POLICY.md`
- `unidesk/config/costs.yaml`
- `unidesk/design/PHASE0_GAP.md`
- `unidesk/tests/test_phase0_primitives.py`
- `unidesk/GOAL.md`, `unidesk/TASKS.md`, `unidesk/CANONICAL.md`, `unidesk/HANDOFF.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 245 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

Phase 0 is **not** complete. Still open (need official files or a longer
backlog, not more feature code): 2016-01-01 history; index daily + VIX;
PIT membership; official CA feed + known-split validation; security-master
ISIN/continuity_id; MTO delivery files; official price bands; F&O PIT
flag; `make rebuild` bit-identical hashes; 20-session availability ledger.
R0 remains breadth_only until the index series lands. Runner stubs
`leakage` / `provenance` stay `not_built_yet` — those names mean the P7
planted-bug suite, not these library primitives.
