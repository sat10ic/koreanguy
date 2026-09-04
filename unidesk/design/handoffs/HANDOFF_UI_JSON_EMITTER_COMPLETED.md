# HANDOFF — Tonight JSON emitter (backend half only) — COMPLETED

Date: 2026-08-30. Executing session (Claude Sonnet 5) hit the account
session-limit rate limit mid-task and died before writing this report,
appending its attribution record, or committing. This file and the record
below were completed by a following orchestrator session (same model,
Claude Sonnet 5) after independently verifying the executing session's actual
diff, output file, and test results — not from the dead session's own claims,
since it left none. Everything stated here is orchestrator-verified.

Attribution-ID: attr-unidesk-ui-json-emitter-claude-sonnet5-20260830-001

## Scope — corrected down from the original task

The original task (per `unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md`) asked
for both the JSON emitter AND wiring the Tonight/Candidates screens in
`unidesk_terminal/`. **Only the JSON emitter was completed.**
`git status --porcelain unidesk_terminal` is empty — no frontend file was
touched. The frontend wiring is still fully open; see "Still open" below.

## What was actually built (verified)

- New module `unidesk/momentum/report_json.py`, wired into
  `unidesk/momentum/nightly.py:run_nightly()` alongside the existing
  Markdown report — same in-memory `ScanResult`/`SymbolScan` the Markdown
  renderer already builds, not a re-derivation.
- **Corrected the integration plan's own factual premise before writing
  code**, and documented the correction in the module's own docstring: the
  plan claimed `report.py` "already builds the typed objects it renders to
  Markdown ... `contracts.*.to_dict()`". Verified false — `report.py` and
  `scan_universe()` work off the lighter `ScanResult`/`SymbolScan`
  dataclasses, not the frozen `contracts.candidate`/`contracts.setup`
  objects (those require fields — `snapshot_id`, `geometry_snapshot_id`,
  `config_hash`, quality scores — that `scan_universe` never computes).
  Constructing fake contract instances just to call `to_dict()` would have
  meant inventing data. Instead `report_json.py` builds its dict directly
  from the same scan objects the Markdown renderer uses, reusing only
  `contracts.base.to_dict()`'s datetime/enum serialization helpers. This is
  the right call — flagging it here so `UI_BACKEND_INTEGRATION_PLAN.md` gets
  corrected too rather than staying wrong for the next session.
- Output verified real, not synthetic: `data/market/reports/tonight_2026-08-28.json`
  exists on disk (183,710 bytes), produced by running the actual nightly
  pipeline against the real `data/bhavcopy/` archive.
- Honesty-footer requirement (non-negotiable per the integration plan) is
  met: the JSON's `honesty_footer` object carries structured fields — orchestrator
  verified directly by reading the file — including `regime_built: false`,
  `regime_note`, `universe_scanned: 2710`, and the skip count, as real JSON
  fields a UI can branch on, not prose to parse.
- Top-level shape: `schema_version`, `session_date`, `as_of`,
  `honesty_footer`, `setups` (per-detector candidate groups), `candidates`
  (flat list). Sample candidate record (real, from BIL,
  `base_breakout` detector): `symbol`, `close`, `adr_pct`, `rs_rank`, `rvol`,
  `contraction`, `delivery_ratio`, `trend`, `sessions`, `adjusted`,
  `detector`, `setup_title` — exactly the fields the existing Markdown table
  already prints per candidate; nothing invented.
- New test file `unidesk/tests/test_report_json.py`, included in the
  orchestrator-verified combined run below.

## Still open (not started)

- **Frontend wiring is entirely undone.** `unidesk_terminal/src/screens/Tonight.tsx`
  and `Candidates.tsx` still read only `src/data/fixtures.ts`. No fetch/import
  of the new JSON exists anywhere in `unidesk_terminal/`.
- The `dataSource: "illustrative"` fallback-labelling requirement from the
  integration plan (real vs. illustrative data must render with a visibly
  different treatment, never silently blended) has not been implemented on
  the frontend, because the frontend was not touched at all.
- No frontend test/build/lint command was run for this slice.
- `UI_BACKEND_INTEGRATION_PLAN.md` should be corrected to match the
  `ScanResult`/`SymbolScan`-not-`contracts.*` finding above; not yet done.

## Files

- `unidesk/momentum/report_json.py` (new)
- `unidesk/momentum/nightly.py` (JSON sibling wiring)
- `unidesk/tests/test_report_json.py` (new)
- `unidesk/design/handoffs/HANDOFF_UI_JSON_EMITTER_COMPLETED.md` (this file)
- `unidesk/design/MODEL_WORK_LOG.jsonl` (attribution record appended by the
  orchestrator)

## Verification (orchestrator-run, combined with the concurrent
split-detector-fix slice, since both landed in the same working tree)

```text
python -m pytest unidesk/tests orderflow/tests -q
→ 325 passed, 22 skipped
  (baseline before both slices: 314 passed, 22 skipped — +11, no regressions,
  no new skips)

python unidesk/run_checks.py
→ [attribution] pass, [contracts] pass, [data_authority] pass, [leakage] pass
  [stale_state]/[provenance] not_built_yet (pre-existing, unrelated)
  unidesk checks: all green
```

`data/market/reports/tonight_2026-08-28.json` opened and inspected directly
by the orchestrator; top-level keys and one candidate record shown above are
copied from that direct read, not from the dead session's unwritten claims.

## Risks

- None introduced by the backend half — it is additive, does not modify
  `report.py`'s existing Markdown output, and the new module is read-only
  with respect to `research/`/`momentum/data/` internals other slices were
  concurrently touching.
- The real risk is scope perception: this file's title says "UI JSON
  emitter," and it would be easy for a future session to assume the UI is
  therefore wired. It is not. Treat "Still open" above as the actual state.
