# HANDOFF — Settings config surfacing + per-detector trust + leak-guard wiring — COMPLETED

Date: 2026-08-30. Continues the build loop after the Stock real-chart wiring
slice. The junction audit (recorded in TASKS.md) found the research event store
label-mixed and under concurrent regeneration; History wiring is held until it
settles. This pass closes the store-free safe slices.

Attribution-ID: attr-unidesk-settings-trust-leakguard-cline-20260830-001

## What was built

1. **Settings real config surfacing** (UI_BACKEND_INTEGRATION_PLAN.md row 6):
   - `unidesk/run_settings_export.py` — pure read of committed config and code
     constants; emits `unidesk_terminal/src/data/settings_2026-08-28.json`.
   - `unidesk_terminal/src/data/settings.ts` — typed loader.
   - `unidesk_terminal/src/screens/Settings.tsx` — shows real cost model,
     outcome labels version, research schema, universe gates, and the full
     detector trust table (8 detectors, 6 not rankable).
2. **Per-detector trust chip** (audit finding UI): `detectorTrust` added to
   `Candidate`, populated from the report's `detector_trust` map; non-rankable
   detectors show a "Blocked"/"Review" chip on cards and Tonight group headers.
3. **Leak-guard production wiring**: `same_event_collision` is now a
   scanner-side guard in `scan_universe` (duplicate detector verdicts on one
   symbol raise ContractError, which the scan loop already catches).
   `assert_feature_not_after_decision` deliberately NOT wired at scan level
   (scanner-before-publication is normal cadence; the PIT guarantee is at the
   store level). `embargo_overlapping_events` remains a research/freeze-layer
   concern.
4. **Plan doc correction**: `report_json.py` does NOT use
   `contracts.*.to_dict()`; it builds directly from `ScanResult`/`SymbolScan`.
   Constructing fake contract instances to call `to_dict()` would invent data.

## Verification (measured)

```text
run_settings_export.py: 8 detectors, 6 not-rankable, costs costs-v1-spec-1.4,
  labels outcome-labels-v4-net-cost
npx tsc -p tsconfig.app.json --noEmit: clean
npx vite build: clean (bundle emitted)
npx oxlint: 0 errors (1 pre-existing unrelated warning)
pytest scan+leakage+detector subset: 70/70 pass
```

## Junction audit finding (recorded, held)

Direct read of `data/market/research/events/date=*` shows 162,962 events
(~19%) still on `outcome-labels-v2-stop-aware` (newest 63 sessions including
2026-08-28). Two concurrent regen processes (PIDs 31472, 5036) are writing
the same partition dir. `archive_attach_summary.json` never reads
`label_version`, so it cannot detect this skew. History wiring is held until
the store verifies all-v4 from disk. `run_history_outcomes_export.py` is
scaffolded with a refusing gate.

## Files

`unidesk/run_settings_export.py`, `unidesk/run_history_outcomes_export.py`,
`unidesk_terminal/src/data/settings.ts`, `unidesk_terminal/src/data/settings_2026-08-28.json`,
`unidesk_terminal/src/screens/Settings.tsx`, `unidesk_terminal/src/screens/Tonight.tsx`,
`unidesk_terminal/src/components/widgets/CandidateCard.tsx`,
`unidesk_terminal/src/data/fixtures.ts`, `unidesk_terminal/src/data/tonight.ts`,
`unidesk/momentum/scan.py`, `unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md`,
`unidesk/TASKS.md`, `unidesk/HANDOFF.md`.

## Next slice (blocked on store settle)

History screen real-data wiring (UI plan row 4) once the archive regen
completes and every partition verifies `outcome-labels-v4-net-cost` from disk.