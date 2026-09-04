# HANDOFF Plan-folder design spec as-built refresh — COMPLETED

Date: 2026-08-29.

Attribution-ID: attr-unidesk-spec-asbuilt-design-grok46-20260829-002

## Outcome

Owner asked to update the design spec in `plan/` with all new changes
(D14–D17). The controlling spec is now a full as-built design of the
tool, not only a status overlay.

- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` rewritten: product, rules R-A–R-Q,
  data map, waves, plus **§12 as-built system design** (pipeline, store,
  gates, features, 8 detectors, quality stack, R0, events/splits, research
  spine, contracts, governance), **§13 how to run**, **§14 open work**,
  **§15 companion docs**.
- Companion plan files carry as-built pointers so they cannot be read as
  "already coded": swing-edges spec, Phase 0 spec, UI V2, constitution,
  north star, integration plan.
- V1 build + UI manuals marked SUPERSEDED in the visible status line.
- `unidesk/CANONICAL.md`, `GOAL.md`, `TASKS.md` now cite V2 (they still
  pointed at V1, which would have sent the next session to the live-first
  spec).

## Files changed

- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`
- `plan/UNIFIED_DESK_BUILD_MANUAL.md`
- `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`
- `plan/UNIFIED_DESK_UI_UX_MANUAL.md`
- `plan/UNIFIED_DESK_INTEGRATION_PLAN.md`
- `plan/SWING_EDGES_TECHNICAL_SPEC.md`
- `plan/PHASE0_DATA_BUILD_SPEC.md`
- `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md`
- `plan/AI_NATIVE_EDGES_NORTH_STAR.md`
- `unidesk/CANONICAL.md`
- `unidesk/GOAL.md`
- `unidesk/TASKS.md`
- `unidesk/HANDOFF.md`
- `unidesk/design/PHASE0_GAP.md`
- `unidesk/design/handoffs/HANDOFF_SPEC_AS_BUILT_DESIGN_REFRESH.md` (this file)

## Verification

Documentation of as-built. `python unidesk/run_checks.py` after the ledger
append. No code changes. Spec refresh does not close N3 remainder, N4
remainder, N5, or Phase 0 acceptance.

## Honest partials

- Nightly report still defaults regime to `not built yet (wave N2)` unless
  the caller passes `regime_note` — documented in V2 §12.1, not fixed here.
- Clean-room `base_pattern` landed in parallel (Codex); V2 §12.5 records it
  as research-only, not in the nightly registry. Not vendor-logic parity.
- manas `daily_prices` still inventoried, not adopted.
- Predictive AI still forbidden.
