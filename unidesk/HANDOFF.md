# Unified desk — handoff

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.
Attribution per `design/MODEL_ATTRIBUTION.md`.

## To continue

**2026-08-30 (latest) — pre-loop safety pass (git baseline + Opus pre-flight
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
  MAE / stop-hit / catastrophic R-multiples for the 194 unconfirmed open-gap
  CA candidates into the labelled dataset, indistinguishable from real
  losses. This corruption is one stage earlier than the N5 gate the docs
  already state ("raw bars would silently mis-backtest") but was not itself
  gated. Fixed by making this a hard condition on N4's archive-wide attach,
  not just on N5.
- 194 detector candidates is the corroborated number (TASKS.md, PHASE0_GAP.md,
  D15 log entry, three-way agreement); "105" in the prior directive block was
  a stale single mention -- do not propagate it.
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
   `leakage_suite.py`. Build: (a) a module-enumerating parametrized truncation
   test -- for every callable in `momentum/features/*.py`,
   `momentum/primitives/*.py`, `momentum/scoring/*.py`, assert
   `f(series[:k]) == f(series)[...k]` (prefix-invariance), so a newly added
   module fails until covered; (b) a `labels.py` assertion that every label
   reads only indices strictly greater than the decision index; (c) extend
   `research/candidates.py:_snapshot()` to carry `adjusted: bool` + a
   confirmed-actions content hash, fold both plus the cost-assumptions version
   into `config_hash_for()`; (d) make `attach_outcomes` refuse (raise, or
   `UNRESOLVED` with `reason="adjustment_basis_mismatch"`) when the future
   series' basis does not match the snapshot's; (e) apply the same guard used
   for N5 to the archive-wide attach itself -- any of the 194 unconfirmed CA
   candidates must land as `UNRESOLVED`, `reason="unconfirmed_corporate_action"`,
   never as a real labelled loss; (f) only then run the archive-wide outcome
   attach over the full 1M-bar corpus; (g) ablation ladder P7.4; (h) candidate
   store persistence -- check `research/event_store.py` first, it may already
   cover this (verify before building).
2. **N3 remainder.** Index series is substantially closed (D16/D17 landed
   Nifty 50 / VIX from 2021-06-01, Midcap 150/500/Smallcap 250 from
   2024-07-08) -- re-verify against `data/market/reference/indices.parquet`
   before doing anything; the one open item is the VIX 1y z-score not yet in
   the R0 label rule. **Corporate-action RATIO source is owner-gated, full
   stop.** `manas.db` has no CA-ratio table; Chartsmaze's 10,972 announcements
   carry record dates and no ratios. Do NOT infer ratios from close-to-close
   gaps to clear the 194 backlog -- `corp_actions.py:70`'s own rule is
   "prefers misses over false adjustments," and inferring ratios is exactly
   the corruption D14 was written to prevent. Produce an owner review queue
   and stop.
3. **N5 -- NO-GO, do not start.** Stated gate (applied CA series) is unmet: 4
   of 198 names confirmed. GOAL.md names CP-3 (owner-invoked leakage audit) as
   "the highest-risk gate in the build" and N5 sits downstream of it; CP-3 has
   not run. Conditions to lift, all three required: (a) an authoritative CA
   ratio source lands (owner-gated, see item 2), (b) directive-1 conditions
   (c)/(d)/(e) above are in production, (c) a same-symbol overlapping-horizon
   control exists so consecutive-session events from one symbol are not
   counted as independent samples (currently nothing catches this -- same-day
   `same_event_collision` only matches on event id, not overlapping outcome
   windows). Re-run an Opus pre-flight when all three are claimed done, before
   writing any N5 code.
4. D12: PARKED (anonymized symbols). Requires authenticated access to resume.
5. **UI integration -- can start now, independent of 1-4.** See
   `design/UI_BACKEND_INTEGRATION_PLAN.md`. Order: emit
   `tonight_<date>.json` via `contracts.*.to_dict()` alongside the existing
   Markdown report (additive, does not touch research internals) -> wire
   Tonight/Candidates screens in `unidesk_terminal/` -> Stock screen waits on
   U-P0.3 -> History screen waits on directive-1 (c)/(d)/(e) -> Research
   screen waits on N5 being lifted (item 3).
6. Wave-close ritual per GOAL.md on every slice, **now including a git
   commit** (see the critical-fact paragraph above).

## Log


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
