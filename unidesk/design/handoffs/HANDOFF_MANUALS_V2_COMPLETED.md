# HANDOFF Manuals V2 — COMPLETED

Date: 2026-08-29.

Attribution-ID: attr-unidesk-manuals-v2-glm53flash-20260829-001

## Outcome

Build Manual V2 (`plan/UNIFIED_DESK_BUILD_MANUAL_V2.md`) and UI/UX Manual V2
(`plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`) adopted as controlling documents
(D13), superseding V1 (headers added to the V1 files; orderflow manual
re-scoped to the optional live module). V2 encodes: EOD-first product
(D10), real data foundation (D9), the research program (D11), the
Chartsmaze reference sources, the BananaPatterns preset pack + validation
answer key (D12), the built inventory (so nothing is re-planned), the
N1–N8 wave queue, the seven research edges, the validation protocol
(adopted wholesale), the dropped/moved V1 items, and the whole-build
definition of done.

## Files changed

- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (new), `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` (new)
- `plan/UNIFIED_DESK_BUILD_MANUAL.md`, `plan/UNIFIED_DESK_UI_UX_MANUAL.md`,
  `plan/ORDERFLOW_BUILD_MANUAL.md` — supersession/status headers
- `unidesk/DECISIONS.md` (D13), `unidesk/TASKS.md` (N-waves + W-F deferral),
  `unidesk/GOAL.md`, `unidesk/HANDOFF.md` (To continue rewritten)
- `unidesk/design/handoffs/HANDOFF_MANUALS_V2_COMPLETED.md` (this file)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 204 passed
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
```

## Honest partials

- V2 manuals are the contract, not the build: waves N2–N8 are planned, not
  coded. N1 remains partially open (download step + report renderer).
- The V1 manual's deep task detail (detector specs, acceptance boxes) that
  V2 does not reproduce remains governed by the adopted research spec and
  the already-built tested code.
