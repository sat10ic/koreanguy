# HANDOFF — corrections + thrust metrics on cards (2026-09-02)

**For:** the next LLM coder (DeepSeek / GLM / Codex / Claude).
**From:** Claude Opus 5, audit role. Evidence:
`unidesk/design/AUDIT_2026-09-02_RENDERED_ELEMENT_SWEEP.md`. **Read that first.**
**Repo state:** commit `ba73462c`, branch `emergent`, working tree clean.
**Report under test:** `data/market/reports/tonight_2026-09-01.json`.

---

## READ THIS BEFORE YOU START

**Do not do three of these and leave the rest.** Every task below is numbered and
carries its own acceptance test. Work them in order. When you finish, paste the
result of every acceptance test into a completion handoff. If you cannot do one,
say so explicitly and say why — **do not silently skip it and do not mark it
done**.

## Work order (the dependencies are real — do not reshuffle)

| # | Part | Why here |
|---|---|---|
| 0 | **F-1** (CI) | **Do this before anything else.** Without it, every fix below can silently regress. |
| 1 | **PART A** (A-1…A-8) | Correctness bugs misleading the trader today. Cheap, mostly independent — A-7 has an interim step now and a final step after B2-8. |
| 2 | **B2-4** (fail-fast refresh + checks in chain) | **Gate for PART E.** A live UI on a chain that silently succeeds on old data is worse than the static app. |
| 3 | **PART B** (thrust meters) | Independent of everything else. Can run in parallel with 1-2 by a second agent — it touches only `CandidateCard.tsx`, `ScaleMeter.tsx`, `Candidates.tsx` columns, `DecisionCard.tsx`. |
| 4 | **B2-7** (register the nightly) | **The answer to "why doesn't it update on its own" — nothing schedules unidesk at all.** Depends on B2-4; do not automate a runner that reports success after failing. |
| 5 | **B2-8** (per-symbol refusal reasons) | Unblocks **A-7**. Do A-7's honest-gap wording in step 1; return for the real reason once this lands. |
| 6 | **B2-1, B2-2, B2-5, B2-6** | Backend correctness + the runbook. B2-1 makes the test suite green again. |
| 7 | **PART E** (dynamic workflow) | The big one. Blocked on B2-4. Ship E-1→E-3 before E-4 — data that updates without a rebuild is the win; motion without it is decoration. |
| 8 | **PART C** (hygiene) | Except C-4/C-5/C-6/C-7, which fold into E-4. |
| 9 | **F-2…F-7** (reliability bar) | F-2/F-3 early if you can — they stop UI regressions. F-6 whenever `git status` becomes unreadable. |
| 10 | **B2-3** (archive remediation) | **Run alone, detached, in its own wave.** Multi-hour. Never inside a UI wave. |

Parallelism: 1 and 3 are safe to run concurrently by two agents (disjoint files).
Everything else is sequential.

**House rules that override your defaults** (this repo enforces them):

1. **Never fabricate a value.** Missing data renders `—` with a named reason.
   Never 0, never a substituted average, never an interpolation.
2. **No dormant code.** A module ships only if it is wired into a pipeline AND
   surfaced in the UI.
3. **No model-authored risk numbers.** Nothing you write may author a stop, a
   size, or a position-risk figure.
4. **No invented weightings.** Do not blend two metrics into a composite score.
   If you want to show two things, show two things.
5. **Mirror backend thresholds, never re-derive them in TypeScript.** Where a
   band already exists in Python, the UI reads it or copies it with a comment
   citing the source file.
6. Environment: **the Bash tool is broken here** (`echo ok` fails at shell init).
   Use PowerShell. Python is
   `C:\Users\satta\Downloads\koreanguy\.venv-orderflow\Scripts\python.exe` —
   use the absolute path, bare `python` fails in sandboxes.
7. **Commit before you start.** The tree is clean at `ba73462c`; keep it that way
   by committing per task group.

---

# PART A — Correctness bugs (do these first; they mislead the trader today)

## A-1 · Restore Momentum Burst to the Tonight feed  · S1

**File:** `unidesk_terminal/src/lib/candidates.ts:9-12`

`SETUP_ORDER` omits `"momentum_burst"`, and `groupBySetup` (same file, lines
127-136) drops any candidate whose detector is not in that list. Two real
candidates vanish from the primary screen while the header above them says "88".

**Do:**
1. Add `"momentum_burst"` to `SETUP_ORDER`. Choose its position deliberately and
   say why in a comment (it is a burst/continuation setup — placing it beside
   `episodic_pivot` is defensible).
2. Make the drop impossible to repeat silently. In `groupBySetup`, replace the
   `continue` with logic that collects unknown detectors into an explicitly
   rendered "Other / unmapped detector" section, so a future detector added
   backend-side appears rather than disappears.
3. Suppress sections with zero candidates (BASE BREAKOUT and POWER PLAY currently
   render as empty headers) — unless Pro mode, where showing "0" is informative.

**Acceptance test:** On Tonight with session 2026-09-01, sum every rendered
section count. It must equal **88** and the feed must contain a **MOMENTUM
BURST** section with **2** rows. Paste the section-by-section counts.

## A-2 · Un-freeze the Prior-calls panel  · S1

**File:** `unidesk_terminal/src/screens/Tonight.tsx:454-479` (panel), `:186` (subtitle)

The panel picks *the newest session where EVERY call has finished its horizon*.
238 rows across six symbols (BODALCHEM, QUICKHEAL, BLISSGVS, PPAP, SHALPAINTS,
UFBL) carry `entry: null` and can **never** resolve, so no recent session can
ever qualify. The panel is stuck on **2026-05-21**, 103 days behind the desk, and
drifts further every day.

**Do:**
1. Exclude structurally-unresolvable rows from the completeness test. A call with
   `entry == null` never had geometry derived and must not gate the panel.
   Do **not** exclude them from the displayed counts — show them as "no data".
2. Make the gate match its own caption: select the newest session whose **10-bar
   horizon has elapsed** relative to the report session, then report what is
   still open within it, rather than demanding 100% resolution.
3. Fix the subtitle at `:186` to describe what the code actually does.
4. Render the chosen session's **age** beside it (e.g. "2026-08-14 · 12 sessions
   ago"), so a stale pick is visible rather than silent.

**Acceptance test:** The panel must display a session within **~15 sessions** of
2026-09-01, not 2026-05-21. Paste the session it picks and its computed age.

**Also worth reporting upstream (do not fix here):** six symbols producing 238
permanently-unresolvable calls is a backend data defect. Name it in your
completion handoff.

## A-3 · Stop History's "Latest" view from reporting a fake 0% hit rate  · S1

**File:** `unidesk_terminal/src/screens/History.tsx:56-61`, and the summary block

`inRange(..., "latest")` is a **7-day** window. Wins need 10 bars to resolve;
stop-outs resolve immediately. So the Latest window can contain only losses:
`Hit rate 0% · Avg -1.00R · Best -1.0R · Worst -1.0R` is an artifact of
right-censoring, not performance. `Best === Worst === -1.0R` is the tell.

**Do:**
1. Where a range cannot yet contain a resolved winner, **do not print a hit rate
   or an average R at all.** Replace with an explicit statement:
   *"No call in this window has completed its 10-bar horizon — win rate is not
   yet measurable. 104 still open."*
2. Make the default range one whose horizon has actually elapsed, so the screen
   opens on something meaningful.
3. Keep the existing arithmetic footnote; add the censoring explanation, which is
   the part currently missing.
4. Suppress `Best`/`Worst` when they derive from a single-valued set.

**Acceptance test:** History on load must not show `Hit rate 0%` alongside
`104 still open`. Screenshot the default view and paste the summary block.

## A-4 · Reconcile PRIME with reward geometry  · S1

**Files:** `unidesk_terminal/src/lib/status.ts` (`deriveState`, `STATE_THRESHOLDS`)

The Candidates table ranks **KINGFA #02 PRIME** while the Stock page for the same
symbol, same session, reads **"POOR RISK — reward does not cover risk at these
levels"** (R:R 0.3R). **Rank 01 (TBZ) has no R:R at all** and is still PRIME.
Two screens, one dataset, opposite conclusions.

**Do — and read this constraint carefully:** you may **not** invent a new
composite score or a weighting (house rule 4). Do exactly one of:

- **(a) Gate the state.** A candidate whose `rr` is `null` or `< 1.0` cannot be
  PRIME. Introduce or reuse an existing lower state for it. The threshold 1.0 is
  not invented — it is the break-even point where reward equals risk, and
  `CandidateCard.tsx:35` already treats `rr < 1.0` as a danger condition
  (`lowRR`). Cite that precedent in your comment.
- **(b) If you believe (a) is wrong**, do not implement anything: write the case
  in your completion handoff and leave the code alone.

Whichever you choose, **make the two screens agree**. The same symbol must not
carry a promoted rank on one screen and a rejection verdict on another.

**Acceptance test:** For every candidate rendered PRIME, print `symbol, rr,
stop_thrust_days`. No row may have `rr == null` or `rr < 1.0`. Paste the table.

## A-5 · Settings contradicts the report on corporate actions  · S1

**File:** `unidesk_terminal/src/screens/Settings.tsx:65`

Hardcoded prose reads *"Corporate-action adjustment pass still open (N3)"* while
the report it displays says `adjustment_status: confirmed_ca_applied`,
`actions_applied: 4`. The CA pass is **closed** on the verified 4-action table.

**Do:** delete the literal. Render `honesty_footer.adjustment_status`,
`actions_applied` and `adjusted_symbols` from the selected report, exactly as the
Tonight data-quality strip already does. Then **grep `src/screens/` for every
other hardcoded factual claim in prose** and give each the same treatment or
delete it.

**Acceptance test:** Settings must read "4 actions applied" (or the live
equivalent) for session 2026-09-01. Paste the grep output showing no remaining
hardcoded status prose.

## A-6 · One detector count, not three  · S2

Three surfaces disagree: `Tonight.tsx:163` hardcodes **"seven detectors"**;
`Settings.tsx:105` renders **"6 of 8"**; the report emits **6**; `SETUP_ORDER`
renders **7** sections.

**Do:** derive every count from the report/settings data. No literals.

**Acceptance test:** All three surfaces show mutually consistent numbers for
session 2026-09-01. Paste all three.

---

## A-7 · Make the veto tool tell the truth about absent symbols  · S1

**File:** `unidesk_terminal/src/lib/veto.ts:31-32`, plus the Desk pre-trade panel

Today every absent symbol gets one canned string naming price and turnover
gates. For MILKYMIST that is **actively wrong** — it clears both easily and was
excluded for circuit lock and history depth (audit S1-9).

**Do:**
1. Consume the per-symbol refusal reason that **B2-8** adds to the report. Render
   the actual reason, e.g. *"MILKYMIST — excluded: only 11 of 61 sessions of
   history (eligible ~2026-11-14); also circuit-locked on 2026-09-01."*
2. Until B2-8 lands, **do not guess**. Replace the canned gate list with an
   honest "not in tonight's universe — per-symbol reason not recorded by the
   nightly (see B2-8)". A named gap beats a confident wrong answer.
3. For an insufficient-history symbol, show the eligibility date — it is
   computable from the session count and `MIN_SESSIONS_DEFAULT`.

**Acceptance test:** Type `MILKYMIST` into the Desk pre-trade check. It must not
cite the price or turnover floor. Paste the rendered output.

## B2-8 · Record why each symbol was refused  · S1

**Files:** `unidesk/momentum/scan.py` (~181-198, 269-283, 347-355),
`unidesk/momentum/report_json.py`

`gate_skip_bucket[sym]` is computed per symbol at `scan.py:281` and then
**discarded** — only aggregate counts reach the report. The same is true of the
`insufficient_sessions` counter at `:354`, which never records which symbols or
how short they were.

**Do:**
1. Emit a per-symbol refusal map in the report:
   `{symbol: {reason, detail}}` — e.g.
   `{"MILKYMIST": {"reason": "insufficient_sessions", "sessions": 11, "required": 61}}`,
   `{"XYZ": {"reason": "universe_gate_circuit_locked"}}`.
2. Record **all** applicable reasons, not just the first to fire. Gates run
   before the history check (`:351` before `:353`), so a symbol failing both is
   currently attributed only to the gate — which is how MILKYMIST's durable
   reason (11 of 61 sessions) becomes invisible on a day it happens to be
   circuit-locked.
3. Size guard: ~1,400 refused symbols per session. Keep it compact — a flat map
   of short codes, not prose per symbol — and confirm the report JSON does not
   balloon (it is bundled into the UI).
4. This also closes the ⛔ item standing in `UX_PANEL_AUDIT_2026-09-02.md`
   ("per-symbol gate reasons are not logged backend-side; aggregate counts
   only") and unblocks A-7.

**Acceptance test:** In the regenerated report, look up MILKYMIST and paste its
refusal entry. It must name **both** the circuit lock and `11 of 61 sessions`.
Then confirm the aggregate bucket counts still equal the per-symbol tallies —
`price_floor 444`, `turnover_floor 845`, `probable_etf 59`, `circuit_locked 5`,
`insufficient_sessions 77` for session 2026-09-01.

**Owner question, flag it — do not decide alone:** a 61-session floor means the
`ipo_base` detector can never see a genuine recent IPO (audit S1-9c). Either
lower the floor for that detector with the reduced-history caveats made explicit,
or state plainly in the UI that the desk does not cover listings under ~3 months.
Do not change `MIN_SESSIONS_DEFAULT` on your own initiative — it is a frozen
default (R14) with a documented rationale in the comment at `scan.py:43`.

# PART B — ADRMAX + ChopScore in simplified good-to-bad terms

This is the owner's direct request: *"can they be added to each stock card, and
in simplified terms (maybe a scale of good to bad)"*.

**Current state — verify before building.** The data flows end-to-end already:
`momentum/features/thrust.py` → `momentum/scan.py` → `momentum/report_json.py` →
`src/data/tonight.ts:49-52` → `src/lib/candidates.ts:76-81` →
`src/data/fixtures.ts:101-107`. **Do not re-plumb it.** It currently renders as
raw numbers in exactly three places:

- Candidates scatter default axis — `Candidates.tsx:44-48`
- Candidates table CHOP / STOP-TH columns — `Candidates.tsx:438-456`
- Stock Pro raw panel — `DecisionCard.tsx:150-154`

**It is absent from the card entirely** — `CandidateCard.tsx` references none of
the four fields.

## B-1 · Build `ScaleMeter`

**New file:** `unidesk_terminal/src/components/ui/ScaleMeter.tsx`

A four-segment meter: N filled segments, tone colour, a plain-English word, and a
`title` tooltip carrying **the raw number and the threshold rule that produced the
word**. Colour against the existing tone vocabulary in `lib/status.ts`
(`STATE_META`) so it matches the rest of the app.

Renders `—` plus a reason when the value is `null`. Must be usable at row density
(the card is a flex row with fixed-width cells) and at panel density (Stock page).

## B-2 · Two meters on the candidate card

**File:** `unidesk_terminal/src/components/widgets/CandidateCard.tsx`

Follow the file's existing grammar exactly: fixed-width cells (`w-14`, `w-16`…),
`!= null ? value : "—"`, Pro-only fields inside the `isPro && (...)` block.

| Meter | Source field | Segments, good → bad |
|---|---|---|
| **Cleanliness** | `chopBand` | `CLEAN` → **Clean** (4) · `MODERATE` → **Fair** (3) · `MESSY` → **Choppy** (2) · `VERY_CHOPPY` → **Very choppy** (1) |
| **Stop room** | `stopThrustDays` | ≥1.5 **Roomy** (4) · 1.0–1.5 **OK** (3) · 0.75–1.0 **Tight** (2) · <0.75 **Inside noise** (1) |

`chopBand` is already computed by `thrust.py:177-187` — **mirror it, do not
recompute it in TypeScript.** Comment the mirror with the source path.

Beginner mode shows the word only. Pro mode shows the word plus the raw number.

**Optional, Pro only:** a third **Thrust** meter from `adrMaxPct`, expressed as a
percentile *within tonight's cohort* and labelled cohort-relative — ADRMAX has no
absolute good/bad, so an absolute band would be invented.

## B-3 · Expect the display to look bad, and leave it that way

Measured on session 2026-09-01:

| | |
|---|---|
| `stop_thrust_days` median | **0.67** |
| below 0.75 ("Inside noise") | **37 of 57** |
| ≥ 1.5 ("Roomy") | **1 of 88** |
| `adr_max_pct` null (under 250 sessions) | **31 of 88** |

So roughly two-thirds of rows will read **Inside noise** in red, and **Roomy**
will appear once.

**That is the correct output. Do not re-band to percentiles to spread the colours
out.** The flat red is a true finding: stops are routinely tighter than the
stock's own ordinary strong-day expansion, which is why scores look high while
R:R stays poor. Hiding it by rescaling would repeat, in reverse, the
`setup_quality = 100` degeneracy the UX audit already flagged. The fix belongs in
the geometry rule that sets `invalidation` — **which is not your task here.**

Because 35% of cards will show the null state, make that state look **deliberate
and explained** ("needs 250 sessions"), not like a rendering failure.

## B-4 · Cohort banner

On Tonight and Candidates, render one line computed from the live report:

> *"37 of 57 candidates have stops inside 0.75 thrust-days — stops are tighter
> than these stocks' normal daily expansion."*

Counts computed from the data, never hardcoded.

## B-5 · Band words beside the raw numbers

- `Candidates.tsx:438-456` — the CHOP and STOP/TH columns keep their numbers and
  gain the same band word.
- `DecisionCard.tsx:150-154` — the Stock Pro panel gains the meters above its
  existing raw rows.

**Acceptance test for PART B:** Pick three symbols from
`tonight_2026-09-01.json` — one `CLEAN`, one `VERY_CHOPPY`, one with
`adr_max_pct: null`. For each, paste the raw JSON values and a screenshot of the
rendered card. The words must match the thresholds above, and the null case must
read "needs 250 sessions", not `0`, not blank.

---

## A-8 · The desk cannot tell you it is behind reality  · S1

**File:** `unidesk_terminal/src/components/shell/TopBar.tsx:39-42`

```ts
// "stale" = OLDER than the newest bundled session -- not "not today":
const stale = sessionDate < newest;
```

Staleness is measured **relative to the newest bundled report**. The newest
bundle can never be older than itself, so **the "stale" flag can never fire on
the data you are actually looking at.** The desk could be three weeks behind the
market and show no warning at all.

That earlier change was a deliberate fix for a different bug (a false "stale"
warning at night on the newest completed session, `UX_PANEL_AUDIT_2026-09-02.md`).
It over-corrected: it removed the false positive by making true positives
impossible.

**Live proof, 2026-09-03:** newest bundled and newest on-disk session is
**2026-09-01**. Wednesday 09-02 was a trading day that was never downloaded
(nothing schedules the nightly — B2-7). The desk is **two sessions behind and
displays no indication of it.**

**Do:**
1. Compute staleness against **the calendar**, not against the bundle: how many
   trading days is `report.session_date` behind today?
2. Render it always, not only past a threshold — e.g. `Session 2026-09-01 ·
   current` versus `Session 2026-09-01 · 2 sessions behind`. A permanent,
   truthful age is better than a warning that fires on a rule nobody remembers.
3. Escalate visually past one trading day, and say what to do:
   *"2 sessions behind — run the nightly refresh."*
4. **Keep the original bug fixed.** At 21:00 on a completed trading day, the desk
   must read *current*, not *stale*. The test is "how far behind the market",
   not "is the timestamp today".
5. **Do not require a server.** This must work in the current static build.
   Trading days can be approximated client-side by excluding weekends, clearly
   labelled as an approximation; NSE holidays will make it occasionally read one
   day pessimistic, which is the safe direction. If `TradingCalendar` is exposed
   to the UI later, use it and drop the approximation.
6. When PART E lands, upgrade this to compare against
   `/api/health`'s `newest_session_on_disk`, which additionally catches "the
   nightly ran but the bundle was never refreshed".

**Acceptance test:** With the bundle at session 2026-09-01 and the system clock
at 2026-09-03, the top bar must state the desk is 2 sessions behind. Then set
the clock to the evening of 2026-09-01 and confirm it reads current, not stale.
Paste both.

# PART B2 — Backend correctness (added after the backend sweep; all verified)

These are not UI work. If you are a frontend-only agent, **say so and leave PART
B2 untouched** — do not half-do it.

## B2-1 · Register the thrust functions for truncation invariance  · S1

**File:** `unidesk/tests/test_truncation_invariance.py` (REGISTRY)

`test_every_enumerated_callable_is_registered` **fails today**. Five public
callables ship in every report with no point-in-time coverage:

```
unidesk.momentum.features.thrust.adr_max
unidesk.momentum.features.thrust.chop_band
unidesk.momentum.features.thrust.chop_score
unidesk.momentum.features.thrust.stop_in_thrust_days
unidesk.momentum.scoring.setup_quality.setup_quality_snapshot
```

**Do:** classify each as `kind='series'` (with a real truncation check),
`'special'`, or `'skip'` (with an explicit written reason). `adr_max` and
`chop_score` are windowed series functions over OHLC and **must** be
`kind='series'` with a genuine truncation check — they are exactly what the guard
exists for. `chop_band` and `stop_in_thrust_days` are pure transforms of
already-computed values and are defensibly `'skip'` **if** you write the reason.

**Do not** make this test pass by weakening it or by marking the series
functions `'skip'` to save effort. Both windows in `thrust.py` are already
exclusive of the current bar (lines 118, 167) — the check should confirm that,
not paper over it.

**Acceptance test:** `pytest unidesk/tests/test_truncation_invariance.py -q`
passes, and the diff shows a real truncation assertion for `adr_max` and
`chop_score` — not a bare skip. Paste both.

## B2-2 · Fix the CA false positive dropping clean symbols  · S1

**Test:** `unidesk/tests/test_archive_attach.py::test_plain_symbol_no_ca_history_resolves_with_no_op_basis`
— **fails**: `assert 'TCS' not in real_ca_backlog`.

The bar-shape heuristic behind `run_ca_review_queue.py` flags TCS — large,
liquid, no confirmed corporate action — as a suspected unconfirmed split/bonus.
Flagged symbols are labelled `UNRESOLVED` / `unconfirmed_corporate_action` and
**dropped from outcome labelling with no error surfaced**. This is plausibly one
source of the permanently-unresolved rows in A-2.

**Do:** tighten the detector so a symbol with no CA history and no confirmed
action is not flagged on bar shape alone. **Owner constraint, non-negotiable:
only the ratio source is owner-gated — do not infer ratios from price gaps.**
Fixing this means narrowing the *candidate* heuristic, never auto-confirming an
action.

**Acceptance test:** that test passes, and you report how many symbols leave the
backlog as a result. If the count is large, stop and report rather than
proceeding — a big swing means the heuristic change is too broad.

## B2-3 · Remediate the 393 wrong-basis archive partitions  · S1

**Verified tally** across all 1,570 partitions in `data/market/research/events/`:

| `ca_table_hash` | Partitions |
|---|---|
| `d1b585eb60fd4f82` (current, verified 4-action) | 1,177 |
| `b3b43b561621b11f` (older pre-audit) | 200 |
| `191ac96a61cdfae7` (**rejected** 55-action) | 193 |

`sessions_needing_label_refresh(Path("data/market"))` returns **397**.

History and Research compute over the whole archive, so their statistics
currently mix three corporate-action bases.

**Do:** run `unidesk/run_archive_attach_resume.py` to completion on the current
basis. This is a long job.

**Two hard rules, both learned the expensive way:**
- Run it **detached**, and **verify progress from persisted partition counts on
  disk — never from process absence.** A killed process and a clean exit look
  identical from outside. This mistake has been made twice on this repo.
- **Do not** start this in the same wave as the UI work. It is hours long and
  will be interrupted.

**Acceptance test:** re-run the parquet tally; `d1b585eb60fd4f82` must be 1,570
of 1,570, and `sessions_needing_label_refresh` must return only recent
label-pending sessions (~4), zero hash mismatches. Paste both numbers.

## B2-4 · Wire the self-checks into the refresh, and delete the false docstring  · S1

`unidesk/run_published_invariants.py:1-4` claims:

> "…**Called by `run_desk_refresh.py`** so the desk verifies itself on every
> refresh — no agent in the loop."

Grep `run_desk_refresh.py` for `published_invariants|run_checks|export_desk_checks`
→ **no matches**. The claim is false, which is why the UI's "Desk self-checks —
n/n passing" panel can vouch for data it never saw.

**Do:**
1. Add `run_published_invariants.py` and `run_export_desk_checks.py` as steps in
   `run_desk_refresh.py`, so the green light is produced by the same run that
   produced the data.
2. Make `run_desk_refresh.py` **abort on the first failed step** — it currently
   accumulates `failures` (lines 70-113) and still bundles, rebuilds and prints
   `DONE — session <old date>` after a failed download. That is the silent
   stale-data path.
3. Assert the newest session actually advanced after the nightly; if not, fail
   unless an explicit `--allow-no-new-session` flag is passed (holidays are
   legitimate).
4. Either make the docstring true or delete the sentence. **Do not leave a
   docstring asserting wiring that does not exist.**

**Acceptance test:** rename the downloader so step 1 fails; confirm the script
exits non-zero, does **not** run `npm run build`, and does **not** print `DONE`.
Paste the output.

## B2-5 · Stop hardcoding `showing_synthetic_data: true`  · S2

`unidesk/checks/runner.py:517` stamps `"showing_synthetic_data": true` into
`STATE.json` on every run regardless of what ran. A previous session
hand-corrected it to `false`; the next run overwrote it. The UI carries no
synthetic data, so the flag currently asserts the opposite of the truth.

**Do:** derive it, or remove it. *Test:* run the checks twice; the value reflects
reality and is stable.

## B2-7 · Nothing schedules unidesk — register the nightly  · S1

**This is why the desk does not update on its own.** Verified on the machine
2026-09-03, not inferred from the repo:

- `Get-ScheduledTask` shows **no task for unidesk**. The only entries are
  `ManasOS-NightlyUpdate` → `manas_os\nightly_update.cmd` and
  `ManasDailyPipeline` (**Disabled**) — both belong to a *different* tool in this
  repo. `run_daily_update.bat` likewise runs `run_manas_cli.py run-eod`, not
  unidesk.
- `run_desk_refresh.py` therefore executes **only when the owner types it**.
- Newest bhavcopy on disk: **2026-09-01**. Today: **Thursday 2026-09-03**.
  Wednesday 09-02 was a trading session and was never fetched — the desk is two
  sessions behind and the gap widens daily.
- **The one scheduled job on this machine is failing silently.**
  `ManasOS-NightlyUpdate` last ran 2026-09-03 19:48:44 with
  `LastTaskResult 1`. Scheduling works here; it fires and errors with nothing
  surfaced.

**Do:**
1. Add `unidesk/nightly_desk.cmd` invoking `run_desk_refresh.py` with the
   absolute venv interpreter (`.venv-orderflow\Scripts\python.exe` — bare
   `python` fails under Task Scheduler's environment, which is a plausible cause
   of the manas job's exit 1).
2. Register a Windows scheduled task (post-close, ~19:15-20:00 IST, weekdays)
   running it. Provide the `schtasks` / `Register-ScheduledTask` command in the
   runbook so the owner can inspect and change it.
3. **Log every run to a dated file and make the last result visible in the UI.**
   A scheduled job that fails silently is worse than no scheduled job — see the
   manas task above. `/api/health` (PART E) should expose last-run time, exit
   code and the session it produced; the UI renders a banner when the last
   scheduled run failed or the newest session is more than one trading day old.
4. This depends on **B2-4** (fail-fast). Do not schedule a runner that reports
   success after a failed step — automation would then manufacture stale data on
   a timer.

**Acceptance test:** disconnect the network, let the task fire (or trigger it
manually), and confirm: the task exits **non-zero**, the log names the failed
step, and the UI shows the failure rather than a stale-but-confident desk. Paste
the log and a screenshot.

**Owner decision, flag it — do not choose alone:** a trading-holiday calendar
means "no new session" is sometimes correct. Either wire the existing
`TradingCalendar` into the freshness check, or treat "no new session on a
weekday" as a warning rather than an error. State which you did.

## B2-6 · Document the real run order (no code)

There is **no scheduler**, and the full chain from raw data to a self-verified UI
is at least three manual invocations whose order is documented nowhere:
`run_desk_refresh.py` → `run_published_invariants.py` (+ desk-checks export) →
periodically `run_archive_attach_resume.py`.

**Do:** write that runbook into `unidesk/HANDOFF.md` or a `RUNBOOK.md`. If B2-4
lands, steps 1-2 collapse into one and the runbook says so.

*Also worth the owner knowing (no action required):* the wired-in downloader
`bhavcopy_extractor/download_bhavcopy.py` pulls from **third-party GitHub
mirrors**, while `unidesk/fetch_nse_bhavcopy.py`, which hits official
`archives.nseindia.com`, is **orphaned** — referenced only in the work log,
invoked by nothing.

---

# PART C — Hygiene (do after A and B; each is small)

- **C-1** `data/tonight.ts:16` — `TONIGHT_JSON_FILENAME = "tonight_2026-08-31.json"`
  with a comment calling it "the newest". `2026-09-01` is newer. Delete the
  constant if unused; fix it and the comment if used. *Test:* grep shows no stale
  session literal in `src/data/`.
- **C-2** `settings.ts:45` and `researchCoverage.ts:29` use
  `Object.values(modules)[0]` **unsorted**, while `reportRegistry.ts:21`,
  `outcomes.ts` and `stockHistory.ts` sort newest-first. *Test:* add a second
  dated file for each and confirm the newest is chosen.
- **C-3** Delete `components/shell/LeftRail.tsx` — dead nav rail, imported by
  nothing, with a nav list that contradicts the live `Sidebar.tsx`.
- **C-4** `ScrollRail.tsx:27` applies class `scroll-fade-x`, **undefined in any
  CSS file**. Define it or remove it.
- **C-5** `Chip.tsx:29-34` — `animate-ping` pulse variant never passed
  `pulse={true}`. Wire it to something real or delete it.
- **C-6** `index.css:156-157` — `--dur-hover` / `--dur-panel` have zero usages;
  every transition hardcodes a Tailwind duration. Adopt the tokens or delete them.
- **C-7** `TopBar.tsx` — search input and alerts bell have no handlers. Implement
  or hide. A control that looks interactive and does nothing is worse than absent.
- **C-8** Tonight hero renders `CHOP (breadth 50.0% above EMA50` — the Beginner
  gloss truncates `regime_note` and leaves the bracket unclosed.
- **C-9** Research shows **7,850** sampled / **8,843** resolved / **9,081** rows
  in one viewport with no explanation, and `Label version: MIXED` while History
  states a single version. Reconcile or label each denominator.
- **C-10** The QUALITY column shows `⚠` on **88 of 88** rows. A warning on every
  row is invisible. Either fix the threshold or state the coverage gap once at
  panel level.

---

# PART D — Do NOT do these

- **Do not** re-band the thrust thresholds to make the UI look balanced (B-3).
- **Do not** build a composite "price action grade" from chop + stop room. That
  invents a weighting.
- **Do not** touch `unidesk/momentum/features/thrust.py`. Its parameters (250
  lookback, 15% top) are the original author's published values and its bands are
  calibrated; the provenance is documented in-module. Read it, mirror it.
- **Do not** fix the stop-geometry rule as a side quest. It is the highest-value
  finding in the audit (§H) and deserves its own task with the owner's sign-off —
  not a drive-by change buried in a UI wave.
- **Do not** delete or weaken any honesty-footer disclosure. That layer was
  verified correct across every screen in this audit and is the best thing in the
  codebase.
- **Do not** make `test_truncation_invariance` pass by marking `adr_max` /
  `chop_score` as `kind='skip'` (B2-1). They are windowed series functions; the
  guard exists precisely for them.
- **Do not** auto-confirm corporate actions while fixing B2-2. Only the ratio
  source is owner-gated; ratios must never be inferred from price gaps.
- **Do not** run the archive remediation (B2-3) inside a UI wave, and never treat
  process absence as proof it finished.
- **Do not** re-open the liveness gate (`momentum/scan.py:288-314`) or
  `sessions_needing_label_refresh` (`archive_attach.py:136-138`). Both were
  verified **genuinely fixed**. The stale data B2-3 addresses is what the fixed
  detector now correctly reports.

---

# PART F — Reliability bar (the fixes behind SAAS_READINESS_2026-09-03.md)

The correctness parts above fix *findings*. **This part fixes the reasons
findings keep coming back.** Source: `unidesk/design/SAAS_READINESS_2026-09-03.md`
§4-§6. Scope is a personal tool that should not need babysitting — **not** a
product launch. Auth, multi-tenancy, rate limiting and uptime targets are
explicitly out of scope.

**F-1 is the highest-leverage task in this entire document.** Doing PART A
through E without it produces finding #21.

## F-1 · CI — nothing currently runs on change  · S1

**Measured:** no `.github` directory. No git hooks installed
(`.git/hooks` holds only samples). Remote exists: `sat10ic/koreanguy`.

Consequence, verified: `test_truncation_invariance` was purpose-built to fail
when a public callable ships without point-in-time coverage. It caught the
thrust wave **three days late**, and only because someone ran pytest by hand.
The guard worked perfectly and was wired to nothing.

**Do:**
1. `.github/workflows/unidesk.yml` — on push and PR, paths-filtered to
   `unidesk/**` and `unidesk_terminal/**`:
   - `python -m pytest unidesk/tests -q`
   - `python unidesk/run_checks.py`
   - `cd unidesk_terminal && npm ci && npm run build` (this runs `tsc -b`, so it
     type-checks too)
2. Add a **local fast lane**, because pushes to this repo are infrequent: a
   `verify.cmd` at the unidesk root running the same three commands, plus a
   `pre-push` hook that invokes it. The hook must be installable by a documented
   one-liner (hooks are not version-controlled).
3. Do not let CI go red-and-ignored. If a suite is legitimately long, split it:
   a fast job on every push, the full archive-touching tests nightly.

**Watch out:** the repo has **`node_modules` committed** under
`manas_os/terminal/` and a 299 MiB pack — a naive checkout in CI will be slow.
Restrict the workflow's `paths` and use `actions/checkout` with
`fetch-depth: 1`. F-6 addresses the root cause.

**Acceptance test:** open a PR that deletes a `REGISTRY` entry from
`test_truncation_invariance.py`. CI must fail. Paste the failing run's URL or
log. Then confirm a clean branch passes.

## F-2 · Error boundaries — one null blanks a screen  · S1

**Measured:** `ErrorBoundary` / `componentDidCatch` / `errorElement` appear in
**0 of 53** files under `unidesk_terminal/src`. `try {` appears in **1 of 53**.

This already happened: History crashed on `.toFixed()` against a null
`mfePct`/`maePct`. A single malformed field takes the screen to blank rather
than degrading.

**Do:**
1. One `ErrorBoundary` component. Wrap each route in `App.tsx`, and separately
   wrap each major panel so one bad widget does not take the page.
2. The fallback must be **diagnostic, not decorative**: name the panel, show the
   error message, and offer a reload — this is a tool you debug yourself.
3. `traderlog/ui/src/components/PanelErrorBoundary.jsx` already exists in this
   repo. **Read it first and match the pattern** rather than inventing a second
   one.

**Acceptance test:** temporarily make one widget throw. Confirm the rest of the
page still renders and the fallback names the failing panel. Paste a screenshot,
then revert the deliberate throw.

## F-3 · Frontend smoke tests — zero exist  · S1

**Measured:** `playwright` is in `devDependencies`; there are **0 test files and
0 Playwright specs**. Every UI regression is currently found by the owner,
visually, later.

**Do:**
1. One spec per route (`/`, `/market`, `/candidates`, `/stock/:symbol`, `/desk`,
   `/history`, `/research`, `/settings`) asserting: the page renders a known
   landmark, and **the console has no errors**. That last assertion alone would
   have caught the History crash.
2. Add assertions for the invariants this audit found broken, so they cannot
   regress silently:
   - Tonight's rendered section counts **sum to the header count** (A-1).
   - No candidate rendered `PRIME` has `rr == null` or `rr < 1.0` (A-4).
   - The top bar reports a session age (A-8).
3. Wire into F-1's workflow.

**Acceptance test:** revert A-1's fix locally; the suite must fail. Restore it;
the suite must pass. Paste both runs.

## F-4 · The positions register can be erased by a cache clear  · S1

**Measured:** `localStorage` is used in 5 files. The Desk positions register and
stated account size live **only** there. No export, no import, no backup.

For a tool holding your own trade record, browser cache is not storage.

**Do:**
1. Immediate, no server needed: **Export / Import JSON** buttons on the Desk
   register. This alone removes the data-loss risk.
2. Wrap every `localStorage` read in try/catch — it throws in some contexts and
   currently there is almost no error handling (F-2).
3. When PART E lands, persist server-side to a file under `data/` and treat
   `localStorage` as a cache, not the record.

**Acceptance test:** add a register entry, export, clear site data, re-import,
confirm the entry returns. Paste the steps.

## F-5 · Bundle is one 7.3 MB chunk  · S3

**Measured:** `dist/assets/index-*.js` 7,336 kB (1,208 kB gzip), no code
splitting. `recharts` and `lightweight-charts` are the likely bulk, and PART E
adds `framer-motion`.

**Do:** route-level `React.lazy` splitting, and dynamic-import the two chart
libraries so they load only on screens that draw. *Test:* report before/after
chunk sizes; the initial chunk should fall well under 1 MB gzip.

## F-6 · Repo hygiene  · S2

**Measured:** `node_modules` is **committed** (`manas_os/terminal/node_modules/…`);
pack is **299 MiB**; loose garbage objects sit in `.git`; roughly **300
untracked files** at the repo root — `api_restart*.log`, `_agrec_*` dumps,
screenshots, `scratch_diag*.py`, `manas.db`, a stray file literally named `=`.

This is why a routine `git status` is unreadable, which is why work goes
uncommitted, which is how three sessions of work ended up with no restore point.

**Do:**
1. `git rm -r --cached` the committed `node_modules`; add to `.gitignore`.
2. Extend `.gitignore`: `*.log`, `*.png` at root, `_agrec_*`, `scratch_*`,
   `_diag_*`, `*.db`, `tmp_*`, `test_out.txt`, `=`.
3. `git gc --prune=now` to clear the loose garbage.
4. **Do not `git rm` anything untracked that might be data** — `manas.db`,
   `traderlog/data/*.db` and the `output/` tree may matter. Ignore, do not
   delete, and list anything you were unsure about.

**Acceptance test:** `git status --porcelain | wc -l` drops below ~20 for a clean
tree. Paste before/after counts.

## F-7 · Make findings permanent — a ledger of tests, not paragraphs  · S1

The meta-finding (audit §S2-8): 11 audit documents, 48 handoffs marked
COMPLETED, and new S1s every pass, because **audits emit prose and only code
prevents regression.** Fixes land as instances, never as classes — the `SESSION`
fixture was deleted months ago and the identical defect reappeared as prose at
`Settings.tsx:65`.

**Do:** for every S1 fixed in PART A and B2, add the *class-level* guard, not
only the instance fix:

| Finding | Instance fix | Class-level guard to add |
|---|---|---|
| A-1 Momentum Burst dropped | add to `SETUP_ORDER` | invariant: every detector in the report renders in some section |
| A-5 hardcoded CA prose | read from the report | invariant/lint: no hardcoded market-status prose in `src/screens/` |
| A-6 detector count literals | derive from data | the same lint |
| C-2 unsorted `Object.values()[0]` | sort both | lint: every dated-bundle module sorts newest-first |
| A-8 staleness vs bundle | compare to calendar | smoke assertion (F-3) |

`checks/published_invariants.py` is the right home for the data-side guards; F-3
for the render-side ones. **A finding is not closed until something fails when it
regresses.**

**Acceptance test:** for each row, break the fix deliberately and show the guard
firing. Paste the failures.

# PART E — Make the workflow dynamic (full build spec)

**Status: owner-approved plan, not started.** This is the answer to *"why does
the tool not feel like a real website"*. It is the largest task in this handoff.
Build it **after PART A and B2-4**, never before — see the sequencing warning at
the end of this part.

## E-0 · Why the app cannot currently do this

Do not attempt a cosmetic fix. Verified facts:

- `grep -rn "fetch(\|XMLHttpRequest\|axios" unidesk_terminal/src` → **zero
  matches.** There is no network call anywhere in the frontend.
- Every data domain is a build-time Vite glob:
  `reportRegistry.ts:4`, `outcomes.ts:7`, `settings.ts:5`,
  `researchCoverage.ts:5`, `stockHistory.ts:19` — all
  `import.meta.glob(..., { eager: true })`.
- `grep -rn "FastAPI|Flask|uvicorn|http.server" unidesk/` → **no matches.**
  There is no server. (`traderlog/api/app.py` is a different project the
  terminal never calls.)

So report data is **compiled into the JS bundle**. That is why
`run_desk_refresh.py` must end with `npm run build`, why nothing updates without
a rebuild, and why the old "Run pipeline" control was a `<span>` with
`cursor-default` and no `onClick` — there was nothing for it to call.

`UI_BACKEND_INTEGRATION_PLAN.md` froze this deliberately: *"No live server, no
websocket, until N7 is owner-requested."* **The owner requested it on
2026-09-02.** You are reversing a locked decision — record it (E-5), do not slip
it in.

## E-1 · `unidesk/server/jobs.py` — one definition of the nightly chain

Extract the chain out of `run_desk_refresh.py` so the CLI and the server cannot
drift apart.

- `REFRESH_STEPS`: ordered table of `(name, label, argv, skippable_under_flag)`.
  Mirror the script's existing flags exactly — read them, do not guess.
- `run_job(...)`: executes steps in order, yields structured events, **aborts on
  the first failure** (this is B2-4; if B2-4 already landed, reuse it rather than
  writing it twice).
- Include `run_checks.py`, `run_published_invariants.py` and
  `run_export_desk_checks.py` as steps.
- Assert the newest session advanced; fail unless `allow_no_new_session`.
- Keep `npm run build` as the **final, optional** step — with the server running
  it is no longer required to see new data.

Then refactor `run_desk_refresh.py` to consume `REFRESH_STEPS`, preserving its
CLI flags and printed output.

## E-2 · `unidesk/server/app.py` — the API

FastAPI, bound to **127.0.0.1 only**, port **8181**. No auth — it is a local
operator console, not a deployed service. **It must never touch broker
credentials**; that is owner-gated and out of scope.

**Dependency note (verified):** `fastapi` and `uvicorn` are **not installed** in
`.venv-orderflow`. Install with the absolute interpreter path, then record them
wherever this repo declares Python deps (find `requirements.txt` /
`pyproject.toml`; if none exists, say so rather than inventing one).

Implement exactly this contract — the frontend in E-3 is written against it:

```
GET  /api/health
     -> {"ok": true,
         "newest_session_on_disk": "2026-09-01",   # data/market/reports/
         "newest_derived_session": "2026-09-01",   # unidesk_terminal/src/data/
         "reports_dir": "<abs path>",
         "job_running": false}

GET  /api/reports          -> {"sessions": ["2026-09-01", "2026-08-31", ...]}  # newest first
GET  /api/report/{session} -> raw tonight_<session>.json, verbatim
GET  /api/outcomes         -> {"session": "<date>", "data": <newest outcomes_*.json>}
GET  /api/settings         -> {"session": "<date>", "data": <newest settings_*.json>}
GET  /api/coverage         -> {"session": "<date>", "data": <newest research_coverage_*.json>}
GET  /api/desk-checks      -> desk_checks.json verbatim
GET  /api/stock-history/{session} -> stock_history_<session>.json verbatim
GET  /api/regime-history   -> regime_history.json verbatim
GET  /api/metric-history   -> metric_history.json verbatim
GET  /api/sector-mapping   -> sector_mapping.json verbatim

POST /api/refresh  -> 202 {"job_id": "<uuid>"} | 409 {"error":"job_already_running","job_id":"..."}
     body (all optional): {"no_download","exports_only","skip_build","allow_no_new_session"}
GET  /api/jobs/{job_id}        -> {"job_id","status","started_at","finished_at",
                                   "steps":[{name,label,status,exit_code,duration_s}]}
GET  /api/jobs/{job_id}/events -> SSE stream
```

**Two file roots** (verify each yourself from the exporter sources):
- Reports, authoritative: `<REPO>/data/market/reports/` — **repo root**, not
  under `unidesk/`.
- Derived exports: `<REPO>/unidesk_terminal/src/data/` — where every
  `run_export_*.py` writes.

`/api/health` deliberately reports **both** newest sessions. A mismatch is the
freshness signal the UI renders in E-4.

"Newest" for dated files means **sorted by session date descending** — never
`Object.values(...)[0]`, never glob order (that bug is live today: C-2).

**SSE events**, each with a JSON `data:` payload: `job_started`,
`stage_started`, `stage_finished`, `stage_failed`, `job_finished`, `job_failed`.
Carry `name`, `label`, `index`, `total` on stage events; `exit_code` and
`duration_s` on terminal ones. Send a periodic heartbeat comment. **A client
connecting to an already-finished job must receive the full history then a
terminal event — never hang.**

Run the job in a background thread, one at a time, 409 on concurrent start.
Stream each step's stdout/stderr into the job record so a failure is diagnosable
from the UI, with a retained-output cap so a long run cannot exhaust memory.

## E-3 · Frontend: glob → fetch, without touching the screens

Replace each `import.meta.glob(..., {eager:true})` module with a fetch, **keeping
the exported API byte-identical** so no screen changes:
`reportRegistry.ts` (`getReport` / `getAvailableSessions` / `hasMultipleReports`),
`outcomes.ts`, `settings.ts`, `researchCoverage.ts`, `stockHistory.ts`.
`useReport.ts` becomes async with a loading state.

**Keep the bundled JSONs as a labelled offline fallback.** House rule 1 forbids
silently substituting data: if the server is unreachable, render a loud OFFLINE
banner naming the bundled session date. **Never fall back silently.**

`vite.config.ts` gains a `/api` proxy to `:8181`. Leave `server.port` at 5183 —
note it is hardcoded there, so a harness that assigns a different port is
ignored.

## E-4 · The motion and feedback layer

Add `framer-motion` — the only new runtime dep. Today the app has **no animation
library, no `@keyframes` anywhere, and zero feedback primitives** (grep for
`spinner|loading|skeleton|toast|isPending|optimistic` → no matches).

Everything below must respect the existing `prefers-reduced-motion` block at
`index.css:277-283`.

1. **Real Run-pipeline button** in `TopBar`, replacing the dead `<span>`:
   idle → click → immediate optimistic "Starting…" → live SSE progress with
   per-stage ticks, elapsed time and a determinate bar → success toast naming
   the new session, **or** a failure card naming the failed stage and its exit
   code. On success, refetch the report list and update the screen **without a
   reload**.
2. **Toast system** (`components/ui/Toast.tsx`) — the missing acknowledgment
   layer. Start with the Desk register add/remove, which today changes state
   with zero visual feedback.
3. **Skeletons** (`components/ui/Skeleton.tsx`) for the now-async report load.
4. **Route transitions** — short fade/slide via `AnimatePresence` in `AppShell`
   (screens currently hard-cut).
5. **List motion** — animated reorder on the Candidates ranked table when sort or
   filter changes; staggered entry on the Tonight setup feed.
6. **Number transitions** — count-up on the hero regime/breadth figures, so a
   refresh visibly *changes something*.
7. **Fix the dead affordances** while you are here — these are PART C items and
   belong in this wave: `scroll-fade-x` (C-4), the `Chip` pulse (C-5), the unused
   `--dur-hover`/`--dur-panel` tokens (C-6), the handler-less search box and
   alerts bell (C-7).

## E-5 · Governance (required, not optional)

- Append a dated decision record to `unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md`
  explicitly reversing *"No live server, no websocket, until N7 is
  owner-requested"*: owner requested 2026-09-02; static bundle retained as a
  labelled offline fallback. **Supersede the clause visibly — do not delete it.**
- Append an attribution record to `unidesk/design/MODEL_WORK_LOG.jsonl`.
  **Read several existing records first and match the schema exactly** — a
  malformed record has broken `run_checks.py` before.

## E-6 · Tests

`unidesk/tests/test_server.py`, FastAPI `TestClient`:

- every GET returns the expected shape against the real files on disk;
- `/api/report/{session}` 404s on an unknown session and **rejects path
  traversal** (`../../etc/passwd`-style input);
- a second `POST /api/refresh` while one runs returns 409;
- newest-session selection picks by **date**, not glob order — construct a case
  where the two differ;
- `run_job` **aborts on the first failing step and does not execute later
  steps** (use a fake step table).

Do not run the real refresh chain in tests.

## E-7 · Acceptance tests

1. `Invoke-RestMethod 127.0.0.1:8181/api/health` returns the newest session on
   disk. Paste it.
2. **The headline test:** click Run with the server up. Progress streams stage by
   stage. On completion the header session date changes **without a page reload
   and without `npm run build`**. Record it.
3. Kill the nightly mid-run. The UI must report a **failed stage with its exit
   code** — not a success toast.
4. Stop the server. The UI shows the OFFLINE banner naming the bundled session.
   It must never render stale data as current.
5. Enable OS reduced-motion. Animations suppress; the app stays fully usable.
6. `pytest unidesk/tests/test_server.py -q` green. Paste it.

## E-8 · Sequencing warning — read before starting

**A server makes stale data easier to hide, not harder.** A live-looking UI earns
more trust than the static one deserved, so if the freshness contract slips, the
owner is worse off than before. Therefore:

- **B2-4 (fail-fast refresh + checks in the chain) must land before E-2.** Do not
  build the Run button on top of a chain that silently succeeds on old data.
- If time runs short, **ship E-1 through E-3 and stop.** Data that updates
  without a rebuild is the real win; motion without it is decoration.
- The 7.3MB single-chunk bundle (no code-splitting) will grow with
  `framer-motion`. Out of scope here — flag it, do not fix it in this wave.

---

# PART E-REF — Background on the removed control

The owner asked why the tool "does not feel like a real website" and why the
run-pipeline control vanished. Findings, for the record:

- **The control was never functional.** Introduced in `cc3d345c`, it was a
  `<span>` with `cursor-default` and **no `onClick`** whose tooltip printed a
  shell command for the operator to type. It was removed in the Tonight rewrite.
- **The app cannot have a working one as currently built.** There are **zero**
  network calls in `unidesk_terminal/src` — every data domain is a build-time
  `import.meta.glob(..., {eager:true})`, and `unidesk/` exposes **no HTTP
  server**. Data is compiled into the JS bundle, which is why
  `run_desk_refresh.py` must end with `npm run build`.
- `UI_BACKEND_INTEGRATION_PLAN.md` froze this deliberately: *"No live server, no
  websocket, until N7 is owner-requested."*

**The build spec for the replacement is PART E above** — localhost FastAPI desk
server, reports served from disk, `POST /api/refresh` with SSE progress, a real
Run button, no rebuild needed, plus the motion/feedback layer. Owner-approved on
2026-09-02; not started. The decision reversal it requires is E-5.

The two pipeline defects found alongside it are **B2-4**, which must land before
PART E begins:

- `unidesk/run_desk_refresh.py:70-113` accumulates `failures` but **never aborts
  on a failed step** — a failed download still bundles, rebuilds and prints
  `DONE — session <old date>`. Silent stale data.
- `unidesk/run_export_desk_checks.py` is **called by nothing**, so the UI's
  "Desk self-checks — 7/7 passing" panel can vouch for data it never saw.
  Neither it nor `run_checks.py` is in the refresh chain.
