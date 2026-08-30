# HANDOFF split-detector index bug fix — COMPLETED (this slice)

Date: 2026-08-30.

Attribution-ID: attr-unidesk-split-detector-fix-claude-sonnet5-20260830-001

## Scope

Fix `momentum/data/corp_actions.py:detect_split_candidates_bars`'s
`closes.index(cand.prev_close)` bar-relocation bug (flagged, not fixed, by
the prior 2026-08-30 N4-leakage-guards slice), add a regression test, and
re-derive the real unconfirmed-candidate count/date list against the full
real archive now that the fix is in. Out of scope (per explicit
constraint): `unidesk/research/candidates.py`, `unidesk/research/labels.py`,
`unidesk/research/event_store.py`, `unidesk/research/leakage.py`; the
archive-wide outcome attach (directive-1(f)) or any N5 work.

## The bug

`detect_split_candidates(closes, opens, volumes, ...)` loops `for i in
range(1, len(closes))`. When a candidate is flagged it builds a
`SplitCandidate` with a placeholder `session=date(1970, 1, 1)` and never
carries the loop index `i` out. `detect_split_candidates_bars` then
re-derives which bar a candidate came from via `idx =
closes.index(cand.prev_close)` — `list.index()` returns the FIRST matching
value, so on flat or repeating pre-gap closes (common in illiquid NSE
smallcaps, and present even in the pre-existing test fixture
`test_split_candidate_detected_on_half_split`, whose `closes[0] ==
closes[1] == 200.0`) this silently returns the wrong bar, mis-dating
`SplitCandidate.session`/`.symbol`.

This mattered concretely: `momentum/data/splits.py:
unconfirmed_candidate_sessions()` consumes `detect_split_candidates_bars`'s
output to build the set of sessions `research.candidates.attach_outcomes`
must refuse to label (the unconfirmed-corporate-action guard landed in the
prior N4 slice). A wrong session date lets the guard block a harmless day
for no reason while leaving the REAL gap day unprotected — silently
defeating the exact protection it exists to provide.

## The fix

`SplitCandidate` gained `gap_index: Optional[int] = None`, defaulting so
none of the existing four tests in `test_corp_actions.py` (which check
`== []` or read `.implied_factor`/`.nearest_clean`, not positionally
constructed) are affected. `detect_split_candidates` now populates it with
the loop variable `i` (the gap-day index into the input series).
`detect_split_candidates_bars` now uses `cand.gap_index` directly —
`bars[idx].bar.session` / `bars[idx].bar.symbol` — instead of re-deriving
the bar by value.

Checked `grep -rn "SplitCandidate("` and `grep -rn "detect_split_candidates\b"`
across the repo first: only two construction sites exist, both inside
`corp_actions.py` itself, both keyword-argument construction — no
positional-construction breakage risk anywhere else in the repo.

## Regression test

`test_split_candidate_bars_dates_the_correct_gap_day_on_flat_pre_gap_closes`
in `unidesk/tests/test_corp_actions.py`: 5 bars, sessions 0-2 all close at
200.0 (repeating on purpose, not a monotonic ramp that would sidestep the
bug), real gap at index 3. Asserts `detect_split_candidates_bars` reports
`cand.session == sessions[3]` (the real gap day) and NOT `sessions[1]`
(what the pre-fix `closes.index(200.0) == 0, bars[0 + 1]` logic would have
reported).

## Real-archive re-derivation

Ingested the actual `data/bhavcopy/` archive (503 files, 1,004,896 bars,
`bhavcopy.py:ingest_directory`, ~29s) into an `InMemoryMarketStore` and ran
`splits.py:scan_store_for_splits` (~2.6s) + `unconfirmed_candidate_sessions`
against `config/confirmed_actions.csv`'s 4 confirmed names — this is the
same real path `attach_outcomes`'s unconfirmed-CA guard is driven from, not
a synthetic stand-in.

- **194 total detector candidates** — matches the previously-cited "194"
  figure (TASKS.md, PHASE0_GAP.md, D15), now confirmed by direct
  measurement post-fix rather than carried forward unverified.
- **4 confirmed matches** (by `(symbol, ex_date)`).
- **190 unconfirmed candidate-sessions across 185 symbols** — this is the
  number `unconfirmed_candidate_sessions()` actually returns and the one
  that should be used wherever "the unconfirmed backlog size" is meant;
  "194" is the raw detector count and includes the 4 already-confirmed
  names.

**Direct old-vs-new comparison** (ran both the pre-fix `closes.index()`
relocation and the post-fix `gap_index` relocation over the same 194
real-archive candidates): **8 of 194 (4%) were genuinely mis-dated by the
old code.** Full list (symbol, old/buggy session → new/correct session):

| Symbol | Old (buggy) | New (correct) |
|---|---|---|
| AMIORG | 2025-04-24 | 2025-04-25 |
| ASHOKLEY | 2025-07-10 | 2025-07-16 |
| DEVIT | 2025-03-20 | 2025-08-21 |
| KOTAKBANK | 2025-04-04 | 2026-01-14 |
| LALPATHLAB | 2025-05-05 | 2025-12-19 |
| FILATFASH | 2026-02-23 | 2026-08-11 |
| HEADSUP | 2024-11-07 | 2025-06-20 |
| RHETAN | 2026-01-28 | 2026-08-14 |

KOTAKBANK and HEADSUP were off by roughly 9 and 7 months respectively —
not a rounding-error-scale bug. This confirms the bug was real and would
have silently corrupted the unconfirmed-CA guard's refuse-list for these 8
names had directive-1(f) (archive-wide outcome attach) run before this fix
landed.

Directive-1(f) itself was **not** run — explicitly out of scope for this
slice, per its own constraint (no archive-wide outcome attach or N5 work).
Only detection and re-derivation were exercised.

## Fixture review — `test_unconfirmed_ca_guard.py`

Reviewed `_build_store_with_a_real_unconfirmed_gap`'s claim (its docstring
said the ramping pre-gap closes were a required workaround for the
relocation bug). Re-ran all 6 tests in that file after the fix: all still
pass, unmodified. The fixture's *behaviour* was already correct — ramping
closes never produced a wrong result, they just happened to sidestep the
bug incidentally. The docstring's claim that the ramp is *required* is now
stale (a flat-close fixture would work correctly too, as proven by the new
regression test in `test_corp_actions.py`), so it was corrected in place to
explain the fix and point at the new regression test, with no change to
the fixture's actual construction or any test assertion.

## Files

- `unidesk/momentum/data/corp_actions.py` (`SplitCandidate.gap_index`,
  `detect_split_candidates`, `detect_split_candidates_bars`)
- `unidesk/tests/test_corp_actions.py` (new regression test + imports)
- `unidesk/tests/test_unconfirmed_ca_guard.py` (docstring correction only,
  no behavioural change)
- `unidesk/HANDOFF.md` (To-continue block overwritten, log appended, stale
  "194" references corrected to distinguish total-detected vs. unconfirmed)
- `unidesk/design/handoffs/HANDOFF_SPLIT_DETECTOR_INDEX_FIX_COMPLETED.md`
  (this file)
- `unidesk/design/MODEL_WORK_LOG.jsonl` (attribution record appended)

## Verification

```text
python -m pytest unidesk/tests -q
→ 246 passed, 21 skipped

python -m pytest unidesk/tests orderflow/tests -q
→ 315 passed, 22 skipped
  (baseline was 314 passed, 22 skipped; +1 for the new regression test,
  no regressions)

python unidesk/run_checks.py
→ [attribution] pass — 36 records, 23 completed handoffs
  [contracts] pass — 12 contracts import; flow+decision round-trip; enums fail closed
  [data_authority] pass — 20 stores owned/classified; 12 unified fields single-authority checked
  [leakage] pass — planted future-bar leak is caught; pytest is the full suite
  [stale_state] not_built_yet (owed by U-P3, pre-existing)
  [provenance] not_built_yet (owed by U-P7, pre-existing)
  unidesk checks: all green (stubs honestly not_built_yet)
```

**Correction (orchestrator, same day):** the sentence that stood here —
claiming a second `run_checks.py` run confirmed `[attribution] pass` after
the `MODEL_WORK_LOG.jsonl` record was appended — was written before that
step actually happened. The executing session hit the account session limit
immediately after writing this file and died before appending the record or
committing. Independently re-checked by a following session: at that point
`MODEL_WORK_LOG.jsonl` contained no matching record and
`python unidesk/run_checks.py` reported `[attribution] FAIL — cites unknown
id attr-unidesk-split-detector-fix-claude-sonnet5-20260830-001`. The
record has now been appended (below) and the round trip re-verified for
real; see the orchestrator's own combined-slice numbers in
`HANDOFF_UI_JSON_EMITTER_COMPLETED.md` / the final `HANDOFF.md` log entry
for the true, current test/check output. The code and regression test
described above were independently verified and are accurate; only this
one Verification claim was premature.

## Honest partials / out of scope

- Directive-1(f) (archive-wide outcome attach over the full 1M-bar corpus)
  was NOT run — explicitly out of scope for this slice. The real 194/190
  numbers above come from running detection + backlog-grouping only, not a
  full outcome-attach pass.
- `unidesk/research/candidates.py`, `labels.py`, `event_store.py`,
  `leakage.py` were not touched, per the hard constraint (another slice may
  be running against them concurrently).
- The 8 mis-dated symbols above are reported as evidence the bug was real
  and now fixed; no claim is made about whether any of the 8 previously fed
  a wrong date into a downstream label — that would require directive-1(f)
  to have actually run, which it has not.

## Risks

- None new. The fix narrows an existing risk (the unconfirmed-CA guard's
  backlog dates were sometimes wrong) rather than introducing one. The
  guard's own refuse-on-unconfirmed-session logic is unchanged; only the
  session dates it's fed are now correct.
