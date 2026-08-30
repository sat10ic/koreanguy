# Unified desk — handoff

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.
Attribution per `design/MODEL_ATTRIBUTION.md`.

## To continue

**2026-08-31 (latest) — v3→v4 net-cost archive regeneration VERIFIED
complete (`ecd1cdd1`).** Direct DuckDB read of every one of the 396
parquet partitions shows 100% `outcome-labels-v4-net-cost` stamp. The
prior HANDOFF's "stuck at 14h" was a misread of the partition mtime
cluster — the regen completed before the contended PIDs 31472/5036
exited. **History wiring is unblocked.**
`run_history_outcomes_export.py`'s refuse-on-label-mixed gate will
now let real exports through. Full record:
`unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_REGEN_V4_COMPLETED.md`.

**Next wave in safe order: History real-data wiring (UI plan row 4).**
- `unidesk/run_history_outcomes_export.py` (already written, refuses
  on label-mixed store) is now the gate; run it on a real session.
- Wire the output (`unidesk_terminal/src/data/history_<date>.json`)
  to `unidesk_terminal/src/screens/History.tsx`. The screen is
  currently driven by synthetic data per CANONICAL §1.
- Verify the terminal renders real history rows with no synthetic
  fallback (the screen's existing empty/synthetic code paths are the
  gate to retire).
- Bounded done-test: a real session_date's history rows render in
  the terminal with the same JSON shape the existing synthetic data
  uses, and the file is regenerated nightly.

**Still open / do NOT start:** no further label-version bump without
batching multiple logical changes (three bumps in 24h is a pattern
to stop); no writes to `data/market/research/events/` outside the
nightly pipeline (now safely runnable since no regen lives).

---

**2026-08-30 (earlier) — archive regeneration still running.** PID 5542
(`python unidesk/run_archive_attach_resume.py`), appending to
`data/market/reports/regen_v4.log`. Two brief near-misses this session from
other sessions'/agents' concurrent resumes of the same canonical process —
both verified harmless directly against the parquet files (atomic writes,
no duplicate `event_id`s, correct label version) before continuing. Check
`ps aux | grep python` before starting a third one.

---

**2026-08-30 (later) — N3 directive-4 CA-ratio review-queue artifact
produced (Claude Sonnet 5).** `unidesk/run_ca_review_queue.py` (new) runs
the existing, unchanged `scan_store_for_splits` detector across the full
`data/bhavcopy` backlog and filters through `confirmed_actions.csv` via
the existing `unconfirmed_candidate_sessions` guard — no new detection
logic, no ratio inference. Real run: **190 unconfirmed candidates**
written to `unidesk/config/ca_review_queue.csv` (committed — small,
owner-facing), reconciling exactly with N3's long-documented "194" figure
minus the 4 candidates since confirmed. The ratio SOURCE (an authoritative
NSE/BSE feed, or the owner directly) is still the only owner-gated part
and remains open.

**Also this session: the canonical archive-regeneration process (PID 3577)
died mid-run at 261/375 sessions — same session-limit failure mode as
three other subagents earlier this session, confirmed via `ps aux`
(process gone) and log inactivity, not assumed. Resumed directly**
(`python unidesk/run_archive_attach_resume.py >> data/market/reports/regen_v4.log`,
version-aware/resume-safe, picks up exactly where it stopped) — see the
entry below for the near-miss with a second, now-killed duplicate process
that ran briefly alongside the original before this resume.

**2026-08-30 — net-of-cost wiring actually finished + a live
NameError fixed; ARCHIVE REGENERATION IN PROGRESS under the real
`outcome-labels-v4-net-cost` — do not start a second one.**

State: label version is `outcome-labels-v4-net-cost`. `candidates.py::attach_outcomes`
now genuinely computes `net_bps`/`cost_total_rt_bps`/`costs_version` per
event (5%-of-trailing-20-ADV order sizing; fails closed to `None` when ADV
is missing, never fabricated) — a prior uncommitted slice had bumped the
version and claimed this was wired without actually calling
`net_return_bps`/`round_trip_cost`; corrected, see
`design/handoffs/HANDOFF_NET_COST_WIRING_COMPLETED.md` and the TASKS.md
correction note on the original entry. Also fixed a live `NameError` in
`walkforward.py::simulate_long`'s gap-through fill (undefined
`first_stop_bar`) that the existing test suite never exercised.

**Near-miss, resolved:** two independent regeneration processes were
briefly running concurrently against the same partition directory — mine
(PID 2415, scoped to only 123 sessions from 2026-02-24, killed) and a
wider one from elsewhere (PID 3577, `data/market/reports/regen_v4.log`,
scoped to the full 375-session archive from 2024-12-30). Killed the
narrower duplicate; directly verified the one overlapping partition
(`date=2026-02-24`, 2339 rows) is intact — no duplicate `event_id`s, every
row correctly stamped `outcome-labels-v4-net-cost` with `net_bps`,
`gap_through`, `exit_price` all present. The wider process is the one
still running; its output is the canonical regeneration.

DIRECTIVES for the next session:

1. **Do NOT start another regeneration.** Check `data/market/reports/regen_v4.log`
   (`tail -3`). Check completion: the log ends with an aggregate report, or
   no new partition mtimes for 15+ minutes after the log's final line. The
   driver is version-aware and resume-aware — if it died, rerun
   `unidesk/run_archive_attach_resume.py` once (check first that nothing
   else is already running it — `ps aux | grep python` — before starting
   a new one; the near-miss above is exactly the failure mode to avoid).
2. Then verify directly from disk (not from a log claim): every partition's
   events carry `label_version == outcome-labels-v4-net-cost`, stopped
   events carry non-null `exit_price`/`gap_through`, some real fraction has
   `gap_through=true` (zero would mean the opens wiring never reached the
   writer), and a real fraction of resolved events carry non-null `net_bps`
   (zero would mean the ADV wiring never reached the writer either).
3. Only after 1+2: N5 Experiment A/B may read outcomes.
4. N3 remainder unchanged: CA ratio source (105 unconfirmed candidates),
   index series via D16 `ind_close_all`.
5. `tightness.py::contraction_sequence` (untracked file, not yet committed
   by whoever is building it) fails its own property test
   (`test_truncation_invariance.py`) as of this entry — not touched here,
   flagged for whoever owns that slice.

## Log

## Log

### 2026-08-30 — Stock screen real-chart wiring completed (Cline, terminal)

Resumed the owner-paused slice recorded above. The backend export and
data modules already existed uncommitted
(`run_stock_history_export.py`, `stock_history_2026-08-28.json`,
`stockHistory.ts`); this session completed the frontend half and the ritual.
`StockChart.tsx` gained an optional `history?: Bar[]` prop (real bars
preferred, `generateOhlc` only as the labelled synthetic fallback, never a
silent blend; `history` added to the effect deps). `Stock.tsx` calls
`getRealHistory(symbol)` and renders a live honesty header when real bars
are shown ("Real NSE bhavcopy · N sessions through <date>") or a dashed
synthetic-fallback note when they are not.

Independently verified the export directly from the committed JSON: 235
tonight symbols, 29,979 bars, zero sessions after the report's
`session_date` (2026-08-28), zero tonight symbols missing, zero
last-close-vs-report-close mismatches. `npx tsc -b` clean, `npm run build`
succeeds (only the pre-existing chunk-size warning), `oxlint` 0 errors.
Completion report:
`design/handoffs/HANDOFF_STOCK_REAL_CHART_WIRING_COMPLETED.md`
(Attribution-ID: attr-unidesk-stock-real-chart-wiring-cline-20260830-001).
Next slice per the integration-plan cadence: History screen real-data wiring
(gate now met — see To continue).

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

### 2026-08-30 — Settings config + trust + leak-guard wiring (Cline, terminal)

Continued the loop after the Stock slice. The junction audit (see TASKS.md
"⚠ AUDIT" block) found the archive is label-mixed and under concurrent
regeneration — History held. This pass:

- **Settings real config surfacing** (UI plan row 6, mechanical, store-free):
  `unidesk/run_settings_export.py` reads `costs.yaml` + backend constants and
  emits `settings_2026-08-28.json`; `unidesk_terminal/src/data/settings.ts`
  types it; `Settings.tsx` now shows real cost model, labels version, universe
  gates, and the detector trust table (8 detectors, 6 not rankable).
- **Per-detector trust chip**: `detectorTrust` added to `Candidate`, populated
  from the report's `detector_trust` map; non-rankable detectors show a
  "Blocked"/"Review" chip on cards and group headers.
- **Leak-guard wiring**: `same_event_collision` is now a scanner-side guard in
  `scan_universe` (duplicate detector verdicts on one symbol → ContractError).
  `assert_feature_not_after_decision` deliberately NOT wired at scan level
  (scanner-before-publication is normal; PIT guarantee lives at the store).
  `embargo_overlapping_events` remains a research/freeze-layer concern, not
  scanner-side. 70/70 scan+leakage+detector tests pass.
- Plan doc corrected: `report_json.py` does NOT use `contracts.*.to_dict()`;
  it builds directly from `ScanResult`/`SymbolScan` (honesty rule — no fake
  contract instances).

Attribution (honest): executing in a terminal harness that does not expose my
underlying model, so I sign as **`cline`** (this agent), identity_basis
`self_reported`. Verification is against real disk reads and exit codes, not
self-report.

Next: wait for the regen to settle, verify all-v4 from disk, then wire
History to real outcome calls. Multi-date report picker blocked on second
report; ablation ladder blocked on N5 CA-ratio gate.

The running archive regeneration (the log entry directly below) is currently
**two concurrent processes** (PIDs 31472 and 5036, both
`unidesk/run_archive_attach_resume.py`) interleaving writes to the same
`data/market/research/events/date=*` partition dir (non-monotonic mtimes).
A junction audit also showed the store is currently **label-mixed**: 162,962
of 863,771 events (~19%) are still on `outcome-labels-v2-stop-aware` — the 63
newest sessions including 2026-08-28 — contradicting the "zero stale" claim.
`archive_attach_summary.json` never reads `label_version`, so it cannot detect
this.

Actions this pass (all **read-only / store-free**, no process touched):
- Recorded the audit finding in TASKS.md and corrected the "396/396" claim at
  its source.
- Rewrote HANDOFF.md "To continue" to hold History wiring until the store
  verifies all-v4 from disk, and to forbid any new writer/nightly while the
  regen lives.
- Added `unidesk/run_history_outcomes_export.py` (safe scaffolding): reads the
  event store and emits real outcome calls for History, but **refuses to run**
  while any partition is off the current label version. Verified by py_compile
  + a fast probe that the gate correctly refuses today.
- Added `unidesk/run_settings_export.py` (store-free config/detector-trust
  exporter).

Attribution (honest): executing in a terminal harness that does not expose my
underlying model, so I sign as **`cline`** (this agent), identity_basis
`self_reported`. Verification is against real disk reads and exit codes, not
self-report.

Next: wire `Settings.tsx` to the settings JSON, wire the per-detector trust
chip, then wait for the store to settle before History.

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
