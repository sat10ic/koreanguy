# Unified desk — handoff

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.
Attribution per `design/MODEL_ATTRIBUTION.md`.

## To continue

**2026-08-30 (latest) — Opus deep-review of F1/F3/F4 fixes + the
BananaPatterns/IPO-EP/AVWAP forward plan, read-only, no code changed. Full
report: `design/handoffs/HANDOFF_FIXES_AND_FORWARD_PLAN_REVIEW_COMPLETED.md`.**

**Top-priority new finding, orchestrator-verified against source: F3's
stop-aware fix uses a constant `r_multiple = -1.0` on stop-hit
(`labels.py:101`), which understates loss magnitude on a gap-through fill
(`long_outcome` never receives or uses the stop-triggering bar's open,
though `opens` is already loaded in `candidates.py:211` for entry).
Systematically optimistic on exactly the gappy/illiquid names most likely
to produce a spurious apparent edge. NOT fixed this slice -- deliberately
not interrupting the in-flight archive regeneration for it. Queued as the
top-priority follow-up once the current regeneration completes and is
verified; do not run N5 or any promotion decision on the regenerated
archive without either fixing this first or explicitly accepting the known
bias direction.**

**Second finding, orchestrator-verified: F4's `blue_sky` flag
(`inputs.py:111-112`) is not a true listing high -- for any symbol with
<=21 bars of loaded history, it is mathematically identical to the pivot
check, so the room-rule bypass fires automatically. Masked today by
`MIN_SESSIONS_DEFAULT=61`, but latent in `compute_setup_inputs` itself for
any shorter-window caller.**

Other findings from the same review, not independently re-verified line-by-line
by the orchestrator (see the full report): F1's quarantine logic is correct
and complete on its target leak, with two latent fail-closed scoping issues
(UTC/IST boundary, `gold.py` calling with no `actions`); the clean-room
base-episode/non-promotion boundary is sound by convention but NOT enforced
in the emitted JSON (`base_episodes` carry no trust marker); the IPO/EP
AVWAP anchor has a real same-day-dissemination contamination defect that
traces to the plan's own wording, not an implementation slip; Slice 5's
vendor-comparison validates reimplementation fidelity, not edge quality --
an outcome-based alternative using this project's own event store is
cheaper and better, and missing from the plan; Slice 6a's promotion gate is
under-specified enough to be satisfiable by an uncorrected multi-comparison
search. **Sequencing verdict: Slices 1/2/6 and the event contracts are
correctly ahead of schedule (they unblock `ipo_base`'s existing
`listing_age_is_not_verified` block); Slice 3 (terminal/Screens) and Slice
5 as scoped should wait** -- Slice 3 because it would surface an unenforced
boundary over a still-ungated universe (F5) with no regime/quality context
(F2); Slice 5 because it's an external dependency bought before the
internal validation it should be measured against exists.

---

**2026-08-30 — RESUMED and CLOSED the paused label-version slice
below, per explicit owner instruction to pick up from the paused handoff.**
Verified (not trusted) everything the paused session claimed:
`OUTCOME_LABELS_VERSION` and `sessions_needing_label_refresh()` exist as
described; the paused handoff's own exact focused-test command passes (41
tests); full suite 342 passed/22 skipped, no regression; `run_checks`
green; `git diff --check` clean. Committed. Full report:
`design/handoffs/HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_COMPLETED.md`.

**Confirmed independently, exactly as the paused handoff warned: the
entire 904,221-event archive is stale.** Zero of 904,221 persisted events
carry the new `potential_r_multiple` schema marker -- every one predates
the stop-aware label fix (`03778ecd`). **The 58.53% stop-blind figure in
the entry further below describes this now-superseded data and must not
be cited as current until the archive is regenerated.** Regeneration
itself was NOT done this slice (needs the version-aware
`sessions_needing_label_refresh`-driven resume, not the older
`run_archive_attach_resume.py` unchanged, which only checks `status` and
would treat stale partitions as done) -- that is the next queued directive.

**Separately verified this slice, three other fixes that landed from a
different session while this session was mid-review (commit-message style
differs, not this session's own work) -- all independently re-verified
against source, not trusted from commit messages alone:**
- `cb67bc91` fixes the audit's F4 finding: `base_breakout` now has a real
  `close_cleared_pivot` breakout condition (previously missing entirely)
  and the inverted `room_adr` rule is replaced with `overhead_room_adr` +
  an explicit `blue_sky` flag for new-high breakouts, rather than
  penalizing them.
- `334ab9a6` fixes the audit's F1 finding: `scan.py` now quarantines an
  entire symbol from cross-sectional RS computation whenever ANY
  unconfirmed split candidate exists in its history up to `as_of` --
  stronger than the originally-scoped fix (which only guarded the local
  contraction window).
- `03778ecd` fixes the audit's F3 finding (see above): stop-aware
  `r_multiple`.
- BananaPatterns/benchmark-event work (`273e6719`, `1cc101f5`, `df7aa47c`,
  `36626f6e`, `08559333`) is task-definition and provenance-checked
  offline-comparison scaffolding, not a violation of D12's owner-gated
  parked status -- it explicitly declines to adopt third-party sources as
  runtime dependencies.

**Remaining open from the audit: F2 (quality-score layer + R0 regime
classifier still have zero production call sites) and F5 (universe scan
still ungated) are UNCHANGED by any of the above.**

---

**2026-08-30 (PAUSED by owner, NOW RESUMED ABOVE) — preserve the
uncommitted working tree.**
The complete paused-state record is
`design/handoffs/HANDOFF_N5_LABEL_VERSION_EVENT_ANCHOR_PAUSED.md`.

**Uncommitted work:** label-version stamping and stale-partition discovery,
plus fact-backed IPO/realised-results AVWAP anchors and RED-first tests. The
stop-aware repair itself is already committed as `03778ecd`.

**First actions on resume:** run the exact focused tests named in the paused
handoff; commit only after they pass; make the archive-resume driver
version-aware; regenerate every event partition; then verify every partition
has `outcome-labels-v2-stop-aware` and no stop-hit outcome has positive
`r_multiple`. Do not run ablations or promote anchored AVWAP before that.

**2026-08-30 (latest) — N5 stop-aware labels repaired; do not run research
experiments yet.** `labels.long_outcome` now records conservative realised
`r_multiple=-1R` after a stop touch and keeps MFE opportunity separately as
`potential_r_multiple`. `walkforward.stop_aware_return_bps` makes both the
simulation and event attachment exit at the stop instead of allowing a later
close to overwrite the loss. Regression proof is in
`design/handoffs/HANDOFF_N5_STOP_AWARE_LABELS_COMPLETED.md`.

**Still blocking N5:** regenerate the persisted archive from the new labels;
explicit cost inputs (real order value and ADV) are required before net return
is eligible for a decision; CA-ratio authority remains owner-gated; and the
same-symbol collision/embargo guards still lack production wiring. Do not run
the ablation ladder against the legacy archive.

**Data-source task added:** U-P0.6 registers official NSE/BSE listing-document
and realised-results ingestors. IPO age must come from an ISIN-linked exchange
listing record, with bhavcopy only as a cross-check. Results Calendar dates are
schedule metadata only; EP event availability comes from archived exchange
filing dissemination timestamps and attachment hashes.

**2026-08-30 (latest) — directive-1(f) archive-wide outcome attach:
CORRECTED to its real, complete total. The prior entry below (committed as
44c126fb) reported 702,369 events as if the run had finished cleanly; it
had not -- the background process was killed by the host after ~320/396
sessions, and the committing session mistook a `tasklist`-confirmed process
exit for a clean completion rather than a kill. 76 sessions
(2026-05-07 → 2026-08-26) were never attempted at all, not merely the one
2026-08-28 gap that report flagged as benign. This session (the same
executing agent, continuing past the point the orchestrator believed it had
ended) detected the kill directly from its own background-task
notification, built `run_archive_attach_resume.py` to find every
session whose partition was either missing or still carried empty
freeze-only `outcome_labels` (not just the visibly-missing ones), and
reprocessed all 78 of them. **Real, complete total: 904,221 events across
all 396 eligible sessions** (2024-11-28 → 2026-08-28) -- 844,872 RESOLVED,
24,889 PARTIAL, 34,460 UNRESOLVED (31,255 `no_future_bars`, 3,205
`unconfirmed_corporate_action`, 0 `adjustment_basis_mismatch` -- the
Opus-flagged basis trap fires zero times, confirmed on the FULL archive
now, not a partial one). Verified zero leftover no-`status` events and all
396 distinct sessions present, read directly from
`load_events(root="data/market")` after the resume finished -- not asserted
from either run's own progress log.

**The stop-blind `r_multiple` finding (F3) from the prior entry is
re-verified on the complete store, not just the partial one it was first
measured on:** 494,540 of 844,872 RESOLVED events (58.53%) have
`stop_hit=True` with a positive `r_multiple` recorded anyway. Close to the
partial-sample figure (60.0%) -- this is a real, robust defect, not a
sampling artifact of the incomplete run. Still N5's most urgent blocking
condition, ahead of the CA-ratio gate.

Full detail: `design/handoffs/HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`
(corrected in place, prior numbers struck through, not deleted).
`python -m pytest unidesk/tests orderflow/tests -q` → 328 passed, 22
skipped (unchanged by this correction -- no code changed, only the
persisted data and the numbers describing it).
`python unidesk/run_checks.py` → all green, `[attribution] pass`.
Attribution-ID: `attr-unidesk-n4-archive-attach-reconcile-claude-sonnet5-20260830-002`.

Directive 1 is now functionally complete except (g) the ablation ladder
(P7.4) -- which must NOT run against this event store until `labels.py` is
fixed to respect `stop_hit`, or its numbers are meaningless -- and wiring
`research/leakage.py`'s three still-unused constitution guards into
production (unchanged gap from earlier slices).

**Directive queue update: N5's blocking conditions are now THREE, not
two.** (a) authoritative CA ratio source (owner-gated, unchanged), (b)
**NEW** -- the stop-blind label defect above must be fixed, (c)
same-symbol overlapping-horizon control (still absent, unchanged).

---

**2026-08-30 — directive-1(f) archive-wide outcome attach, FIRST REPORT
(CORRECTED ABOVE -- its 702,369 figure was an undercount from a killed
run mistaken for a complete one; do not cite the numbers in this entry,
use the corrected entry above instead). Original text preserved for the
record:**

702,369 events persisted. It surfaced a NEW, urgent, quantified finding:
60.0% of resolved events (410,165 of 683,257) have `stop_hit=True` with a
positive `r_multiple` recorded anyway -- a direct confirmation of the
concurrent audit's F3 finding, now measured on the real archive, not just
reasoned about. This is now N5's most urgent blocking condition, ahead of
the CA-ratio gate. Full detail:
`design/handoffs/HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`. 328 passed, 22
skipped; all run_checks green; attribution 40 records / 27 handoffs.

Directive 1 is now functionally complete except (g) the ablation ladder
(P7.4) -- which must NOT run against this event store until `labels.py` is
fixed to respect `stop_hit`, or its numbers are meaningless -- and wiring
`research/leakage.py`'s three still-unused constitution guards into
production (unchanged gap from earlier slices).

**Directive queue update: N5's blocking conditions are now THREE, not
two.** (a) authoritative CA ratio source (owner-gated, unchanged), (b)
**NEW** -- the stop-blind label defect above must be fixed, (c)
same-symbol overlapping-horizon control (still absent, unchanged).

---

**2026-08-30 -- orchestrator checkpoint: two concurrent slices
completed their code but died on the account rate limit before finishing
their own paperwork/commit; a following orchestrator session (same model,
Claude Sonnet 5) independently verified both and finished the ritual.
Real combined state: 325 passed, 22 skipped (unidesk+orderflow); all
run_checks green including attribution (38 records now).**

Both the split-detector-fix session and the UI-JSON-emitter session hit
"account session limit" mid-task. Neither had committed. The orchestrator
found their working-tree changes, ran the tests and checks itself (not
trusting either session's self-report), found ONE false claim in the
split-detector session's own completion report (it asserted a second
`run_checks.py` pass confirmed `[attribution] pass` after appending its
ledger record -- the record did not exist; the sentence was written before
the step it describes actually happened, then the session died). Corrected
in place in `HANDOFF_SPLIT_DETECTOR_INDEX_FIX_COMPLETED.md`. The code and
regression test from that slice were independently verified accurate --
only that one verification sentence was premature.

The UI-JSON-emitter session completed only the backend half of its task
(the JSON sibling emitter, verified working against the real archive) and
never touched `unidesk_terminal/` at all (`git status --porcelain
unidesk_terminal` empty). Its attribution record is filed `status:
"partial"`, not `"completed"`, and directive 5 below is corrected to say so.

**Directive-1(f) status update:** the split-detector fix found the bug had
REAL effect -- 8 of 194 real-archive candidates were mis-dated by the old
code, one by ~9 months (KOTAKBANK). Detail: `HANDOFF_SPLIT_DETECTOR_INDEX_FIX_COMPLETED.md`.
The unconfirmed-CA backlog is now built from correct dates; the real
unconfirmed count is **190** (194 total detected minus 4 confirmed), not
194 -- "194" and "190" mean different things and should not be used
interchangeably going forward. Directive-1(f) (archive-wide outcome attach)
is now safe to attempt on the split-dating front, but an earlier Opus
checkpoint (see the log entry below) flagged a SEPARATE, still-unaddressed
trap for it: if (f)'s future-outcome map doesn't itself carry an
`adjusted`/`ca_table_hash` basis matching the snapshot's, every genuinely
adjusted symbol will land `UNRESOLVED` across the whole archive, silently.
Do not start (f) without constructing that future map with its basis
stated -- this was true before this checkpoint and remains true now.

Two commits will follow this entry, one per corrected slice, each
referencing its Attribution-ID. See `unidesk/design/MODEL_WORK_LOG.jsonl`
records `attr-unidesk-split-detector-fix-claude-sonnet5-20260830-001` and
`attr-unidesk-ui-json-emitter-claude-sonnet5-20260830-001`.

**2026-08-30 — split-detector index bug FIXED (Claude Sonnet 5).**
`corp_actions.py:detect_split_candidates_bars`'s `closes.index(cand.prev_close)`
bar-relocation bug (flagged, not fixed, in the entry below) is now fixed:
`SplitCandidate` carries a new `gap_index: Optional[int] = None` field,
populated by `detect_split_candidates`'s own loop index `i`, and
`detect_split_candidates_bars` uses it directly instead of re-deriving the
bar by value. Regression test added:
`test_split_candidate_bars_dates_the_correct_gap_day_on_flat_pre_gap_closes`
in `unidesk/tests/test_corp_actions.py` (flat/repeating pre-gap closes,
asserts the correct gap day is reported, not an earlier day with a matching
close value).

**Re-derived against the FULL real archive** (`data/bhavcopy/`, 503 files,
1,004,896 bars ingested via `bhavcopy.py:ingest_directory`, ~29s; scan
~2.6s): `scan_store_for_splits()` returns **194 total detector candidates**
— the same count as the previously-cited "194" figure, confirmed by
measurement, not assumed. Of those, 4 match `confirmed_actions.csv` by
`(symbol, ex_date)`, leaving **190 unconfirmed candidate-sessions across 185
symbols** via `unconfirmed_candidate_sessions()` — this is the number that
actually feeds the guard's refuse-list; "194" was the raw detector count,
not the unconfirmed count, and the two should not be used interchangeably
going forward. **The bug was real and had real effect on this archive**: a
direct old-vs-new comparison run on the same 194 candidates shows **8 of
194 (4%) had their `.session` silently mis-dated by the old code**, in one
case by ~9 months (`KOTAKBANK`: old code said 2025-04-04, correct gap day is
2026-01-14) and ~7 months (`HEADSUP`: old code said 2024-11-07, correct is
2025-06-20). Full symbol/date list: `AMIORG`, `ASHOKLEY`, `DEVIT`,
`KOTAKBANK`, `LALPATHLAB`, `FILATFASH`, `HEADSUP`, `RHETAN`. This means
directive-1(f) (archive-wide outcome attach), if it had run before this
fix, would have built its unconfirmed-CA refuse-list off wrong dates for
these 8 names — silently under-protecting the true gap day and
over-protecting an unrelated day for each. Directive-1(f) itself was NOT
run (out of scope for this slice, per its own constraint) — only detection
and re-derivation were exercised.
`unidesk/tests/test_unconfirmed_ca_guard.py`'s `_build_store_with_a_real_
unconfirmed_gap` fixture docstring's claim that the ramp is a required
workaround is now stale (the fixture still passes — ramping closes were
never wrong, just no longer necessary to dodge the bug) — updated in place
to say so; no behavioural change to the fixture or its assertions.

**2026-08-30 — directive 1(a)-(e) DONE (Claude Sonnet 5). Module-
enumerating truncation test, labels-future-only assertion, and the
adjustment-basis + unconfirmed-CA guards on `attach_outcomes` are built and
tested (63 new tests, 314 passed/22 skipped combined
`unidesk/tests`+`orderflow/tests`, up from the 272 passed/1 skipped
baseline — no regression). Full report:
`design/handoffs/HANDOFF_N4_LEAKAGE_GUARDS_COMPLETED.md`
(`Attribution-ID: attr-unidesk-n4-leakage-guards-claude-sonnet5-20260830-001`).
`costs.py`/`leakage_suite.py` were re-verified complete before starting and
were NOT touched, per the corrected scope below. Directive 1 items (f)
archive-wide outcome attach, (g) ablation ladder P7.4, (h) candidate-store
persistence verification remain open -- see the updated directive 1 below.**

**Still open, real, and NOT fixed by this slice (do not re-close by
accident): `assert_feature_not_after_decision`, `same_symbol_embargo`, and
`same_event_collision` in `research/leakage.py` still have exactly one
caller each -- a test file -- and zero production call sites. This was the
actual stage-1 gap named by the 2026-08-30 Opus pre-flight; item (a) below
proved prefix-invariance on the FEATURE side, which is a different (also
real, also necessary) property, not production wiring of these three
guards. Wiring them into a real call site is still undone.**

**FIXED 2026-08-30 (see latest entry above): `momentum/data/corp_actions.py:
detect_split_candidates_bars`'s `closes.index(cand.prev_close)` bar-relocation
bug is fixed via `SplitCandidate.gap_index`. It DID have real effect: 8 of
194 real-archive candidates were mis-dated by the old code before this fix
(list above). Directive 1(f) can now build its unconfirmed-CA backlog off
correct dates -- it still has not been run.**

**2026-08-30 — pre-loop safety pass (git baseline + Opus pre-flight
review) done; corrected directive queue below supersedes the 2026-08-29 one,
which contained two decoy items and one mis-scoped gate.**

**Critical fact for any session picking this up: `unidesk/`, `orderflow/`,
`plan/`, `unidesk_terminal/` were untracked in git for the first two days of
this build (verified `git ls-files unidesk` == 0, no `.gitignore` rule).
Fixed 2026-08-30, commit `f5615227` ("pre-loop baseline, no functional
change"). Any HANDOFF entry above this line describing work done before that
commit has no corresponding git history -- the working tree is the only
record. Commit at every wave close from here forward; it is now part of the
wave-close ritual, not optional.**

An Opus subagent reviewed `DECISIONS.md` (D1-D18) and
`plan/UNIFIED_DESK_INTEGRATION_PLAN.md` in full against the queue below before
this session executed anything. Corrections it found, already applied to this
block:

- **Cost model and the P7.3 planted-bug leakage suite are already built**
  (`research/costs.py`, `research/leakage_suite.py`) and were about to be
  rebuilt from a stale directive. Do not re-implement them.
- **The real leakage gap is that `assert_feature_not_after_decision`,
  `same_symbol_embargo`, and `same_event_collision` have exactly one caller
  each -- a test file -- and zero production call sites.** The planted-bug
  suite tests two toy functions against each other, not any production
  feature/primitive/scoring module. This is the actual stage-1 work.
- **Corporate-action adjustment basis is not tracked on frozen research
  events**, and outcome attach performs no consistency check. Running
  archive-wide outcome attach before fixing this will silently write ~-50%
  MAE / stop-hit / catastrophic R-multiples for the 190 unconfirmed open-gap
  CA candidate-sessions into the labelled dataset, indistinguishable from
  real losses. This corruption is one stage earlier than the N5 gate the
  docs already state ("raw bars would silently mis-backtest") but was not
  itself gated. Fixed by making this a hard condition on N4's archive-wide
  attach, not just on N5.
- 194 is the re-derived, MEASURED total detector-candidate count against the
  full real archive (2026-08-30, post index-fix; see latest "To continue"
  entry -- corroborates TASKS.md/PHASE0_GAP.md/D15's prior citation, but
  those were not themselves re-measurements). Of those 194, 4 match
  `confirmed_actions.csv` and 190 (185 symbols) are the actual unconfirmed
  backlog `unconfirmed_candidate_sessions()` produces -- use 190, not 194,
  when the number needs to mean "still needs a human/owner decision."
  "105" in the prior directive block was a stale single mention -- do not
  propagate it either.
- Path corrections for any doc pointing at `unidesk/design/DECISIONS.md` or
  `unidesk/design/CANONICAL.md`: both actually live at `unidesk/DECISIONS.md`
  and `unidesk/CANONICAL.md` (no `design/` prefix).
- `STATE.json`'s `wave` and `showing_synthetic_data` fields are hardcoded
  literals in `checks/runner.py` (`write_state()`), not measurements. Do not
  cite STATE.json as evidence of build stage; read HANDOFF.md + TASKS.md +
  `run_checks.py` output instead. Do not "fix" the literals casually either --
  wire them to real measurements deliberately, as its own slice, or leave
  them and note the caveat.

Full review transcript is not persisted verbatim; this block is the actionable
summary. Re-run a fresh Opus pre-flight before N5 specifically (see item 3).

Directives (in order):

1. **N4 remainder -- corrected scope.** Do NOT touch `costs.py` or
   `leakage_suite.py`.
   - **(a) DONE 2026-08-30** — module-enumerating parametrized truncation
     test: `unidesk/tests/test_truncation_invariance.py`, 40 callables
     enumerated via `pkgutil` across features/primitives/scoring, 19 run the
     real `f(series[:k]) == f(series)[:k]` check, 1 special-cased
     (`fractal_pivots`), 20 explicit reasoned skips; a coverage test fails
     if a new module/function has no registry entry.
   - **(b) DONE 2026-08-30** — `research/labels.py:assert_future_only()`,
     wired into `attach_outcomes` as defense-in-depth alongside
     `future_after`. Tests: `test_labels_future_only.py`.
   - **(c) DONE 2026-08-30** — `SymbolScan.adjusted`, `_snapshot()` carries
     `adjusted`/`ca_table_hash`, `config_hash_for()` folds in the
     confirmed-actions CONTENT hash (`corp_actions.py:
     confirmed_actions_content_hash`) plus `costs.COSTS_VERSION`.
   - **(d) DONE 2026-08-30** — `attach_outcomes` refuses
     (`UNRESOLVED`/`reason="adjustment_basis_mismatch"`) when the future
     series' stated basis disagrees with the snapshot's. Tests (c)+(d):
     `test_adjustment_basis_guard.py`.
   - **(e) DONE 2026-08-30** — `momentum/data/splits.py:
     unconfirmed_candidate_sessions()` groups the LIVE detector backlog
     (there is no persisted 194-row file anywhere in the repo -- it is
     `scan_store_for_splits()`'s output minus `confirmed_actions.csv`) by
     symbol; `attach_outcomes` gained an optional `unconfirmed_ca_sessions`
     param that refuses
     (`UNRESOLVED`/`reason="unconfirmed_corporate_action"`) when the outcome
     window spans an unconfirmed gap session. Tested against a REAL
     detector-flagged fixture with a negative control proving the guard is
     load-bearing: `test_unconfirmed_ca_guard.py`. Full report:
     `design/handoffs/HANDOFF_N4_LEAKAGE_GUARDS_COMPLETED.md`.
   - **(f) OPEN** — only now (guards c/d/e exist) run the archive-wide
     outcome attach over the full 1M-bar corpus. Requires wiring
     `unconfirmed_ca_sessions=unconfirmed_candidate_sessions(...)` and a
     real CA-basis-aware future map into that run -- not done yet.
   - **(g) OPEN** — ablation ladder P7.4.
   - **(h) OPEN** — candidate store persistence -- check
     `research/event_store.py` first, it may already cover this (verify
     before building).
2. **N3 remainder.** Index series is substantially closed (D16/D17 landed
   Nifty 50 / VIX from 2021-06-01, Midcap 150/500/Smallcap 250 from
   2024-07-08) -- re-verify against `data/market/reference/indices.parquet`
   before doing anything; the one open item is the VIX 1y z-score not yet in
   the R0 label rule. **Corporate-action RATIO source is owner-gated, full
   stop.** `manas.db` has no CA-ratio table; Chartsmaze's 10,972 announcements
   carry record dates and no ratios. Do NOT infer ratios from close-to-close
   gaps to clear the 190-session unconfirmed backlog -- `corp_actions.py:70`'s own rule is
   "prefers misses over false adjustments," and inferring ratios is exactly
   the corruption D14 was written to prevent. Produce an owner review queue
   and stop.
3. **N5 -- NO-GO, do not start. THREE conditions now, not two -- one is
   new and more urgent than the others.** Stated gate (applied CA series)
   is unmet: 4 of 198 names confirmed. GOAL.md names CP-3 (owner-invoked
   leakage audit) as "the highest-risk gate in the build" and N5 sits
   downstream of it; CP-3 has not run. Conditions to lift, all three
   required: (a) an authoritative CA ratio source lands (owner-gated, see
   item 2); (b) **NEW, 2026-08-30, most urgent** -- directive-1(f)'s
   archive-wide run (now DONE, 702,369 events) surfaced that `labels.py`'s
   `r_multiple = mfe_pct / risk` ignores `stop_hit` entirely: **60.0% of
   resolved events (410,165 of 683,257) show `stop_hit=True` with a
   positive R-multiple recorded anyway.** This must be fixed in
   `labels.py` before N5 or the ablation ladder (directive 1g) run against
   this event store -- their numbers would be systematically overstating
   performance. Detail: `design/handoffs/HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`.
   (c) a same-symbol overlapping-horizon control exists so consecutive-session
   events from one symbol are not counted as independent samples (currently
   nothing catches this -- same-day `same_event_collision` only matches on
   event id, not overlapping outcome windows). Re-run an Opus pre-flight when
   all three are claimed done, before writing any N5 code.
4. D12: PARKED (anonymized symbols). Requires authenticated access to resume.
5. **UI integration -- steps 1 AND 2 DONE 2026-08-30.**
   `unidesk/momentum/report_json.py` emits `tonight_<date>.json` alongside
   the Markdown report -- corrected the plan itself along the way: it
   builds from `ScanResult`/`SymbolScan` directly, NOT via
   `contracts.*.to_dict()` as `UI_BACKEND_INTEGRATION_PLAN.md` originally
   claimed (that document still needs the correction folded in; not yet
   done). `unidesk_terminal/`'s Tonight and Candidates screens now render
   all 268 real candidates from the real report (commit `6cd84a67`),
   distinguished from illustrative fixtures by a "REAL SCAN" badge and a
   "RAW SCAN SIGNALS -- NO QUALITY SCORE COMPUTED" card path, never blended.
   Full report: `design/handoffs/HANDOFF_UI_TONIGHT_CANDIDATES_WIRED_COMPLETED.md`.
   **Important, from the concurrent trading-logic audit** (see log entry
   below): several detectors now visible through this UI have real logic
   defects, most notably `base_breakout` (no breakout condition, inverted
   room rule). The UI's generic "rule output, not a recommendation"
   disclaimer covers this honestly but there is no detector-specific
   warning yet -- worth adding once the audit's findings are triaged.
   **STILL OPEN:** Stock screen waits on U-P0.3; History screen waits on
   directive-1 (c)/(d)/(e) (done) plus the Gap-2 future-map basis fix
   (archive-attach in flight as of this entry, see directive 1); Research
   screen waits on N5 (item 3, still NO-GO); no multi-date report picker
   exists (hardcoded to the one real report on disk).
6. Wave-close ritual per GOAL.md on every slice, **now including a git
   commit** (see the critical-fact paragraph above).

## Log

### 2026-08-30 — Split-detector index bug fixed + real re-derivation (Claude Sonnet 5)

Fixed `corp_actions.py:detect_split_candidates_bars`'s `closes.index(cand.
prev_close)` bar-relocation bug (flagged, not fixed, by the prior 2026-08-30
entry). Root cause: `list.index()` returns the FIRST matching value, so on
flat/repeating pre-gap closes (common in illiquid NSE smallcaps) the
candidate got attributed to an earlier bar than the real gap day. Fix:
`SplitCandidate` gained `gap_index: Optional[int] = None`, populated by
`detect_split_candidates`'s own loop index; `detect_split_candidates_bars`
now uses it directly instead of re-deriving the index by value. Checked
`grep -rn "SplitCandidate("` and `detect_split_candidates\b` first — only
the two in-module construction sites exist, both keyword-argument, no
positional-construction breakage risk.

Added regression test
`test_split_candidate_bars_dates_the_correct_gap_day_on_flat_pre_gap_closes`
(`unidesk/tests/test_corp_actions.py`) using bars with 3 repeating flat
pre-gap closes through `detect_split_candidates_bars` — asserts the correct
gap day is reported, not the earlier day the old code would have picked.

Re-derived the real candidate count against the FULL real archive
(`data/bhavcopy/`, 503 files, 1,004,896 bars, ~29s ingest + ~2.6s scan via
`bhavcopy.py:ingest_directory` + `splits.py:scan_store_for_splits`), not
assumed from the prior "194" citation: **194 total detector candidates**
(matches the prior figure), **4 confirmed matches**, **190 unconfirmed
candidate-sessions across 185 symbols** (the number that actually drives
`unconfirmed_candidate_sessions()`'s refuse-list — "194" and "190" are not
interchangeable; HANDOFF corrected to use 190 where the unconfirmed count is
meant). A direct old-code-vs-new-code comparison on the same 194 candidates
found **8 were genuinely mis-dated by the pre-fix code**: `AMIORG`,
`ASHOKLEY`, `DEVIT`, `KOTAKBANK` (worst case, ~9 months off),
`LALPATHLAB`, `FILATFASH`, `HEADSUP` (~7 months off), `RHETAN` — confirming
the bug was not cosmetic and would have silently corrupted the
unconfirmed-CA guard's refuse-list for these names had directive-1(f) run
before this fix. Directive-1(f) itself (archive-wide outcome attach) was
NOT run — out of scope for this slice per its own constraint.

Reviewed `test_unconfirmed_ca_guard.py`'s `_build_store_with_a_real_
unconfirmed_gap` fixture: its ramping-pre-gap-closes shape still produces a
correct, real detector-flagged candidate after the fix (all 5 tests in that
file still pass unmodified) — the fixture's *behaviour* did not need a fix,
only its docstring's claim that the ramp is a required workaround, which was
now stale and has been corrected in place to explain the fix instead.

Full test run: `python -m pytest unidesk/tests orderflow/tests -q` → 315
passed, 22 skipped (baseline was 314 passed/22 skipped; +1 for the new
regression test, no regressions). `python unidesk/run_checks.py` → all
green, `[attribution] pass`. Full report:
`design/handoffs/HANDOFF_SPLIT_DETECTOR_INDEX_FIX_COMPLETED.md`
(`Attribution-ID: attr-unidesk-split-detector-fix-claude-sonnet5-20260830-001`).

### 2026-08-30 — Directive 1(a)-(e) leakage guards (Claude Sonnet 5)

Built and tested the corrected-scope N4 remainder: (a) a module-enumerating
truncation-invariance test over every public callable in
`momentum/features|primitives|scoring` (40 enumerated, 19 real checks, 1
special-cased, 20 explicit skips, coverage self-check against drift); (b)
`labels.py:assert_future_only`, wired into `attach_outcomes`; (c) `SymbolScan.
adjusted` + snapshot/`config_hash_for` now carry the confirmed-actions
CONTENT hash and `costs.COSTS_VERSION`; (d) `attach_outcomes` refuses on an
adjustment-basis mismatch (`UNRESOLVED`/`adjustment_basis_mismatch`); (e)
`splits.py:unconfirmed_candidate_sessions` groups the LIVE (not persisted
anywhere) detector backlog and `attach_outcomes` refuses when an outcome
window spans an unconfirmed gap
(`UNRESOLVED`/`unconfirmed_corporate_action`), tested against a real
detector-flagged fixture with a negative control. `costs.py`/
`leakage_suite.py` re-verified complete, not touched. 63 new tests across 4
new files; combined `unidesk/tests`+`orderflow/tests` 314 passed/22 skipped
(baseline 272 passed/1 skipped, no regression);
`python unidesk/run_checks.py` all green. Flagged, not fixed: production
wiring of `leakage.py`'s three guards is still zero-call-site (real gap,
separate from what (a) proves); `detect_split_candidates_bars`'s
`closes.index()` bar-relocation bug can mis-date a candidate under a flat
pre-gap price (spawned as a separate background task, not fixed here).
Items (f)/(g)/(h) remain open. Report:
`design/handoffs/HANDOFF_N4_LEAKAGE_GUARDS_COMPLETED.md`.


### 2026-08-29 — N4 parquet event store + outcome attach (Grok 4.6)

Freeze now persists under `research/events/date=`. Outcomes attach from
bars strictly after the decision session (next open = fill). Empty future
is UNRESOLVED, not zeros. Official CA files still not in the repo; did
not copy `daily_prices`. Report:
`HANDOFF_N4_EVENT_STORE_COMPLETED.md`.

### 2026-08-29 — Confirmed CA derived view (Grok 4.6)

Seed table of four 2:1 names (ANANDRATHI, BEML, AGIIL, ANUHPHR) applied
at scan time. Raw store untouched. Nightly loads the CSV. ASHOKLEY not
in the table. manas.db has no CA-ratio table; official feed still open.
Did not copy `daily_prices`. Report:
`HANDOFF_N3_CONFIRMED_CA_VIEW_COMPLETED.md`.

### 2026-08-29 — UI/UX prototype rebuilt for V2 (Claude Code, Sonnet 5)

Picked up the UI track parked earlier this session (see the "Owner-directed
pivot" entry below). While that V1-manual build was in progress, the backend
adopted V2 manuals (D13) — the product pivoted from a live cockpit to an
evening desk. The V1 build was superseded, not finished: deleted all
V1-only screens/widgets (Flow console, trigger queue, sector heatmap, room
meter, RR ladder, correction-type widget, social evidence rail) and rebuilt
`../unidesk_terminal/` against `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` — nav
is now Tonight/Candidates/Stock/History/Research/Settings (V2 §2). An Opus
subagent audit of the V1 build (amber-overload, accessibility gaps, a
duplicated tone→color map, an off-canvas nav indicator) got folded into the
rebuild rather than re-run separately, since most of what it reviewed no
longer exists. Fixtures for the 3 real Momentum Burst candidates are
verbatim from `data/market/reports/tonight_2026-07-03.md` (the one report
that's actually run on real data); everything else is tagged
`dataSource: "illustrative"` and renders with a visible dashed-border label.
Visually verified with Playwright (screenshotted every screen, read the
images, caught and fixed two real bugs: a chart/trigger-line scale bug and
Beginner/Pro mode not reaching the Decision panel). No backend `unidesk/`
files touched. Full state: `../unidesk_terminal/HANDOFF.md`.

### 2026-08-29 — D18 written into the design spec (Grok 4.6)

Owner asked to update the plan-folder spec with the nexus fill. V2 now
has D18 / R-R / §12.8.1 (Chartsmaze primary, 2,772 names, no taxonomy
mix). Companion plan files and DECISIONS.md match. Fill itself already
landed; this slice is documentation.

### 2026-08-29 — Nexus industry-map fill (Grok 4.6)

Owner pointed at `manas_os/data/nexus_industry_map`. Parsed the CSV RO
(no manas_os import). Chartsmaze kept 2,423 labels; 349 previously unmapped
names filled; 2,327 overlapping labels disagreed so they were not mixed.
Total 2,772 with `source_tier`. Report:
`HANDOFF_NEXUS_INDUSTRY_FILL_COMPLETED.md`.

### 2026-08-29 — Plan-folder design spec as-built rewrite (Grok 4.6)

Owner asked to update the design spec in `plan/` with all new changes.
Rewrote `UNIFIED_DESK_BUILD_MANUAL_V2.md` as the controlling design of the
tool (product + rules + data + waves + §12 as-built modules/detectors/R0/
research/CLI). As-built maps added to swing-edges, Phase 0 spec, UI V2,
constitution, north star. V1 manuals marked SUPERSEDED in the visible
status line. CANONICAL/GOAL/TASKS now cite V2. Report:
`HANDOFF_SPEC_AS_BUILT_DESIGN_REFRESH.md`.

### 2026-08-29 — D17 manas RO extract + V2 spec as-built (Grok 4.6)

Owner pointed at `manas_os/sources`. Extracted `sector_index_prices` and
dated `universe` snapshots from `manas.db` without importing manas_os.
Index parquet is now 2021-06-01 → 2026-08-28 (Nifty 50 / VIX) and
2024-07-08 → 2026-08-28 (Midcap 150 / 500 / Smallcap 250). Build Manual V2
§0.1/§3/§6/§11 rewritten to the as-built map. Integration plan sequencing
is EOD-first.

### 2026-08-29 — D16 NSE index daily + R0 midcap gate (Grok 4.6)

Finstack MCP not in this session. Fetched NSE `ind_close_all` via
nse-archives (NikhilSuthar/indian-market-data). niftyindices.com historical
API failed Cloudflare JSON. 59/60 sessions 2026-06-04 → 2026-08-28; 295
rows; India VIX last 10.68; Midcap 150 above SMA50 at 2026-08-28. R0
disagreement with Midcap SMA50 forces CHOP. Report:
`HANDOFF_D16_INDEX_SERIES_COMPLETED.md`.

### 2026-08-29 — N4 research spine: freeze, walk-forward, leakage (Grok 4.6)

N3 official files (2016 history, index/VIX, PIT membership, CA ratios)
were not on disk; did not back-fill today's Nifty list. Built N4 instead:
`ResearchEvent` freeze including INVALID, expanding folds + 5-session
embargo, next-bar fill, net-of-cost `simulate_long`, planted-bug leakage
suite, runner leakage smoke. 4y/1y folds refuse on a short calendar.
Report: `HANDOFF_N4_RESEARCH_SPINE_COMPLETED.md`.

### 2026-08-29 — D15 extended archive + Chartsmaze events + known-split (Grok 4.6)

Nightly ingest now reads `data/bhavcopy/` (the downloader's actual target):
503 files, 1,004,896 bars, 2024-09-02 → 2026-08-28. Event parsers for IPO
listings, circuit revisions (PIT), corporate-announcement review queue
(never auto-adjustable), vendor breadth. Split confirmation is close-to-close;
four real 2:1 names kill the gap. 194 detector candidates. Report:
`HANDOFF_N3_EXTENDED_ARCHIVE_EVENTS_COMPLETED.md`.

### 2026-08-29 — D14 constitution + Phase 0 primitives; W-E gold fixtures (Grok 4.6)

Adopted the owner research constitution and Phase 0 data-build spec into
`plan/` (D14). Closed W-E P2.3 gold fixtures (32 real cases). Landed
Phase 0 library primitives (calendar, costs, leakage contracts, OHLC
invariants, delivery lag). 245 tests; run_checks exit 0. Phase 0 is not
complete — next is N3 official files (history / index / membership / CA).
Reports: `HANDOFF_W_E_GOLD_FIXTURES_COMPLETED.md`,
`HANDOFF_D14_PHASE0_PRIMITIVES_COMPLETED.md`.

### 2026-08-29 — Owner-directed pivot: UI/UX prototype track started (Claude Code, Sonnet 5)

Owner redirected this session from the queued backend slice (W-E gold
fixtures, per `GOAL.md`) to start the UI/UX build against
`../Downloads/UNIFIED_MOMENTUM_TRADING_DESK_UI_UX_PRODUCT_MANUAL.md`. No
backend files in `unidesk/` were touched; W-E gold fixtures remain the next
backend slice, untouched, still queued. New sibling app `../unidesk_terminal/`
built (Vite/React/Tailwind, UI Phase 1 shell + full Home screen, fixture
data). This does not change any wave/checkpoint status in this file's "To
continue" block above or in `GOAL.md`'s W-H entry — the UI track is running
ahead of the W-F data dependency on fixtures only, by explicit owner
instruction for this session. Full state: `../unidesk_terminal/HANDOFF.md`.

### 2026-08-29 — U-P0.1 repository and data-authority map (Codex desktop)

Completed the read-only persistent-store/API audit and encoded it in a
machine-checked JSON manifest plus human guide. Named 20 logical stores and 12
unified field authorities; explicitly separated accepted evidence from model
annotations; kept 305 deterministic TraderLog positions / 436 events
quarantined; marked Manas, SwingEdge, and legacy copies non-authoritative for
UniDesk; and left the U-P0.3 data home/symbol master as explicit owner decisions.
No production data was modified. Report:
`unidesk/design/handoffs/HANDOFF_U_P0_1_DATA_AUTHORITY_COMPLETED.md`.

### 2026-08-29 — W-A / U-P0.5 offline recorder core (Codex desktop)

Closed the complete offline-provable recorder slice: append-safe partitioned
Parquet, DuckDB views and exact depth replay, health/lifecycle/gap persistence,
fresh-depth reconnect recovery, launcher integration, and recursive secret
redaction. Evidence: 84 orderflow tests and 102 combined orderflow + unidesk
tests passed. U-P0.5 stays partial because no owner live FYERS session was run.
Attribution and limitations are recorded in
`orderflow/design/handoffs/N2_OFFLINE_RECORDER_CORE_COMPLETED.md`.

### 2026-08-28 — U-P0 integration slice: governance chain, contracts, crosswalk (GLM-5.3-Flash)

Landed: manuals into `plan/` with adoption notes; `unidesk/` governance chain
(CANONICAL / DECISIONS D1–D7 / TASKS / HANDOFF / STATE + attribution runner
fork); 12 shared contract schemas with fail-closed validation; integration
crosswalk; Autoclaw N1 handover persisted and aligned with its stop report.
Absorbed session attr-orderflow-n1-prep-glm53flash-20260828-001 (N1 prep stop)
without redoing any of its work; its transport findings are locked as D7.

Open, carried forward:

- `Unverified:` everything feed-related (cadence, TBT provisioning,
  subscription limits, optional-field population, `exch_feed_time` epoch
  semantics, depth-size scaling) until the owner-run live session.
- `Assumption:` contract field definitions match the build manual §4 as
  written; manual amendments require append-only contract-version bumps.
- Orderflow manual's Phases 1–2 remain unbuilt; unified U-P0.1 full inventory
  pass still owed (needs read-only access into traderlog/, out of boundary
  for this session).

### 2026-08-30 -- Pre-loop safety pass: git baseline, Opus review, corrected directives, UI integration plan (Claude Sonnet 5)

Owner asked to resume the build loop with an Opus foolproofing check before
coding, plus a plan for backend to frontend integration. Found and fixed the
most severe gap in the project: unidesk/orderflow/plan/unidesk_terminal
had zero git history (untracked, no gitignore rule) after two days and four
models of work. Committed a baseline (f5615227, 230 files, no functional
change) before touching anything.

Spawned an Opus subagent to read DECISIONS.md and
plan/UNIFIED_DESK_INTEGRATION_PLAN.md in full against the queued directive
list. It found the queue would have rebuilt two already-complete modules
(cost model, planted-bug leakage suite) and, more seriously, that the
project constitution-level leakage guards (assert_feature_not_after_decision,
same_symbol_embargo, same_event_collision) have zero production call sites --
they are declared, not enforced -- and that corporate-action adjustment
basis is untracked on frozen research events, meaning an archive-wide
outcome attach would silently write catastrophic-loss labels for the 194
unconfirmed CA candidates into the research spine, one stage before the N5
gate that was supposed to catch exactly this class of corruption. Full
findings and corrected directives are now the To continue block above.

Wrote design/UI_BACKEND_INTEGRATION_PLAN.md: the terminal has zero real
data wiring today (grep confirmed, fixtures.ts only); the plan adds a JSON
sibling to the existing Markdown report via the already-built
contracts.*.to_dict(), then wires screens one at a time gated on real
backend coverage (Tonight/Candidates now, Stock on U-P0.3, History on the N4
adjustment-basis fix, Research on N5 being lifted).

Scheduled an hourly session-only cron reminder (auto-expires in 7 days) to
resume the build loop if this session stalls mid-stage.

No production code changed this slice; it is safety infrastructure and
corrected planning. Report: this HANDOFF entry is the completion report.
Attribution-ID: attr-unidesk-preloop-safety-and-ui-plan-claude-sonnet5-20260830-001

### 2026-08-30 -- Cross-model + trading-logic audit (Opus), and UI wired to real data (Claude Sonnet 5, logged by orchestrator)

Two things landed this slice, reported together since the second directly
implicates the first.

**Trading-logic audit completed** (`unidesk/design/handoffs/` has no
dedicated file for this -- it was a read-only review, not a code change;
full text lives in this session's transcript and is condensed here).
Scope: all 39 `MODEL_WORK_LOG.jsonl` records across four models, the 8 setup
detectors, R0 regime classifier, cost model, and cross-model interface
consistency. The orchestrator independently re-verified the five most
severe claims against source before accepting them -- all held.

**Most consequential findings, ranked:**

1. **`base_breakout` (`momentum/detectors/setups.py:96-109`) has no
   breakout condition.** Five rules (RVOL, base depth, contraction, RS,
   room) -- none test price against the base high. Worse: `room_adr` is fed
   `distance_from_listing_high_pct / adr_pct` (grok's `inputs.py:95-98`,
   *distance below* the highest high), while the rule requires
   `room_adr >= 1.0`. A stock genuinely breaking to new highs scores
   `room_adr ~= 0` and is REJECTED; a stock 3 ADR below its 2-year high
   scores best. The detector systematically selects laggards and excludes
   real breakouts. Same inversion appears again in `entry_quality.py:83`.
2. **The STOCK/SETUP/ENTRY quality-score architecture and R0 regime
   classifier are dead code.** `stock_quality_snapshot`,
   `entry_quality_snapshot`, `RegimeClassifier` -- zero production call
   sites (grep-confirmed, tests only). `entry_quality_snapshot` isn't even
   exported from `scoring/__init__.py`. `nightly.py` never constructs
   `RegimeClassifier`; `report_json.py` hardcodes
   `regime_note="not built yet"`. The nightly output is eight raw booleans,
   not the three-score separation the build manual promises.
3. **Outcome labels ignore stop-hits and no trading cost is ever applied.**
   `labels.py:92 r_multiple = mfe_pct / risk` has no reference to
   `stop_hit` -- a trade that gaps through its stop for a real loss, then
   rallies, records as a win. `round_trip_cost`'s only caller is
   `simulate_long` (`walkforward.py`), which itself has zero callers
   anywhere in the codebase -- confirmed by grep, one hop deeper than it
   first looked. Any backtest built on this labels dataset is pre-cost,
   stop-blind, best-case.
4. **Unadjusted corporate actions create a precise 5-session false-signal
   window.** `scan.py` adjusts OHLCV with confirmed actions only (4 of
   194/190 -- see the split-detector-fix entry above for that count's
   history). A real split leaves `contraction_ratio` artificially near 0.5
   for the ~5 sessions after the 20-day RS window clears but the
   contraction window hasn't -- across up to 190 unconfirmed events, this
   is a mechanism for a real corporate action to appear as a textbook
   coiling setup. The existing unconfirmed-CA guard (directive 1e) only
   protects *outcome labels*, not this *feature*-side artifact -- a real
   gap the guard does not close.
5. **The universe scan is entirely ungated.** `scan.py` never imports
   `universe/gates.py` (price floor, turnover floor, ETF exclusion,
   circuit-lock all exist and are unused). Only filter is
   `len(bars) >= 61`. The RS percentile denominator is computed over this
   polluted ~2,760-symbol set, distorting every `rs_rank >= 70` gate in
   every detector.

Also found: R0's docstring claims breadth *direction* matters, the code
only checks *level* (`regime.py:6-8` vs `:59-72`); `ipo_base` fires on any
symbol with 61-250 bars of history for ANY reason (suspension, ticker
change, data hole), not genuine listing age (`inputs.py:45-48` admits
this); `pullback`'s "proximity to anchor" has no sign, so a stock 2.5%
*above* EMA21 satisfies a rule meant to require a decline; `reversal_reclaim`
compares past closes to *today's* EMA21 value rather than each day's own,
collapsing it to a continuation screen; the spec calls for a VCP detector,
none exists (`power_play` ships instead); `is_probable_etf` substring-matches
"ABSL" and would wrongly exclude the real stock ABSLAMC.

Rated GOOD as built: episodic pivot, inside bar (loose volume threshold
only). QUESTIONABLE: momentum burst (its one anti-chase guard,
AVWAP extension, is structurally always `None` and never fires -- inert,
not just occasionally absent), power play (sound rule, hazardous
ungated cohort). WRONG-AS-BUILT: base breakout, ipo base, pullback,
reversal/reclaim.

**Do not treat any candidate this tool surfaces as a validated signal
until these are triaged.** Recommended fix order: (1) base_breakout's
inverted room rule and missing breakout test -- actively backwards right
now; (2) wire the quality-score layer and R0 so the nightly output isn't
just eight booleans; (3) fix labels.py to respect stop_hit and wire
round_trip_cost into whatever produces the event store's numbers; (4) gate
the universe; (5) the corporate-action feature-side leak (distinct from
the already-fixed outcome-side guard).

**UI now surfaces this raw output to a human for the first time.**
Commit `6cd84a67` (`unidesk_terminal/`, logged by the orchestrator on
behalf of the executing session -- see
`design/handoffs/HANDOFF_UI_TONIGHT_CANDIDATES_WIRED_COMPLETED.md`) wires
Tonight/Candidates to the real 268-candidate report. The UI's "raw scan
signals, no quality score, not a recommendation" framing is honest, but
carries no detector-specific warning -- a stock surfaced under
"Base Breakout" right now is, per finding 1 above, more likely to be a
laggard than a breakout. Worth a per-detector trust flag once the fixes
above land, rather than relying solely on the generic disclaimer.

The audit itself was read-only (no code changed) and produced no dedicated
completion report; the UI-wiring slice's own record is
attr-unidesk-ui-tonight-candidates-wired-claude-sonnet5-20260830-001
(design/handoffs/HANDOFF_UI_TONIGHT_CANDIDATES_WIRED_COMPLETED.md).
