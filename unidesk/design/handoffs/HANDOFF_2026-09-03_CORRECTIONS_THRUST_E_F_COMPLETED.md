# HANDOFF COMPLETED — corrections + thrust UI + dynamic workflow + reliability bar (2026-09-03)

Attribution-ID: attr-unidesk-corrections-thrust-e-20260903-glm53flash-001
Attribution-ID: attr-unidesk-corrections-thrust-e-20260903-glm53flash-002

**Attribution-ID:** attr-unidesk-corrections-thrust-e-20260903-glm53flash-001
**Executor:** GLM-5.3-Flash via ZCode (host_verified). **Branch:** `emergent`.
**Implements:** `unidesk/design/handoffs/HANDOFF_2026-09-02_CORRECTIONS_AND_THRUST_UI.md`
(in its final form: PART A incl. A-7/A-8, PART B, PART B2, PART C, PART E, PART F),
against `AUDIT_2026-09-02_RENDERED_ELEMENT_SWEEP.md`.
**Evidence screenshots:** `unidesk/design/evidence-2026-09-03/`.

Commits (in order): `156498a8` PART A+B · `7cd53496` PART C · `6d62af86` B2-4/1/2/5/6 ·
`7b3f87f2` E-1/E-2/E-6 + B2-7 + B2-8 + A-7 interim · `a9f2bb8b` F-1 + A-7 final + A-8 ·
`14c26d31` E-3/E-4/F-2/F-3/F-4 + C-9 + F-5 · `1f171c1d` E-5 + runner alignment + 09-03 data.

---

## PART A — acceptance results

**A-1 · Momentum Burst restored.** On Tonight, session 2026-09-01 (Beginner), rendered
section counts (playwright, evidence/tonight-feed-0901-momentum-burst.png):
`EPISODIC PIVOT 1 · MOMENTUM BURST 2 · INSIDE BAR 68 · IPO BASE 7 · PULLBACK 7 ·
REVERSAL/RECLAIM 3` — **sum = 88 = header count**, MOMENTUM BURST carries exactly 2 rows
(GANDHAR, UDS). Zero sections (BASE BREAKOUT, POWER PLAY) suppressed in Beginner, shown as
"0" in Pro. Unknown detectors render in an explicit "Other / unmapped detector" section.
Class guard: `inv:setup_sections_cover_detectors` (published invariant) + F-3 smoke test.

**A-2 · Prior-calls unfrozen.** Gate = newest session whose 10-bar horizon has elapsed on
the real trading calendar (union of the newest stock-history snapshot's sessions). Evidence
(evidence/prior-calls-panel.png), report session 2026-09-03:
`2026-08-17 · 10 sessions ago — 0 won / 11 stopped / 14 still open / 1 no data · avg -1.00R n=11`.
On session 2026-09-01 it picked **2026-08-18 · 10 sessions ago**. Both within ~15 sessions of
the desk; never 2026-05-21 again. `entry: null` rows show as "no data" and no longer gate the
pick. **Upstream defect reported (not fixed here, per handoff):** 238 permanently-unresolvable
outcome rows across BODALCHEM(61), QUICKHEAL(59), BLISSGVS(38), PPAP(31), SHALPAINTS(15),
UFBL(12) — `entry: null` means geometry was never derived for them.

**A-3 · History no longer reports censoring as performance.** Default range is now
**Settled** (every call's 10-bar horizon elapsed). evidence/history-default.png: opens on
`2921 won · 5037 stopped · 308 flat · 29 still open · 70 no data · Hit rate 39% · Avg +0.47R ·
Best +15.8R · Worst -22.6R` with the arithmetic footnote AND the right-censoring footnote.
Windows with zero horizon-elapsed calls print "No call in this window has completed its
10-bar horizon — win rate is not yet measurable. N still open." instead of a hit rate.
Best/Worst suppressed on single-valued sets.

**A-4 · PRIME gated on reward geometry.** Option (a) implemented: in `deriveState`, a
candidate that would be PRIME is demoted when `rr < 1.0` (→ REJECT, mirroring verdict.ts
rule 3 POOR_RISK — the same rejection the Stock page renders) or `rr == null` (→ WATCH:
promotion withheld without asserting a rejection the evidence does not support; TBZ's Stock
verdict is ACTIONABLE, so REJECT there would have created a new contradiction). PRIME rows
on 2026-09-01 after the gate (symbol, rr, stop_thrust_days) — 8 rows, none with rr null/<1.0:
KSHINTL 1.1R — · FLUOROCHEM 1.4R 0.42 · GRASIM 1.2R 0.92 · UNIONBANK 1.3R 0.69 ·
SAGILITY 1.7R — · WHEELS 1.6R 0.38 · GLENMARK 3.4R 0.56 · VSSL 1.5R 0.43
(evidence/candidates-table.png; the two "—" stop values are adr-max-null names). Smoke test
A-4 asserts this permanently. 22 rows were demoted (21 → REJECT, TBZ → WATCH).

**A-5 · Settings tells the report's truth.** The hardcoded CA sentence is gone; Settings
renders `adjustment_status` / `actions_applied` / `adjusted_symbols` from the selected
report → reads "confirmed_ca_applied — 4 actions applied across 2 symbols". Grep of
`src/screens/` for hardcoded status prose: every remaining hit is either a live-computed
null-reason, a true app-capability statement (e.g. "replay not wired"), or an honesty
disclosure the audit verified correct — none claims report state. Guard:
`inv:no_hardcoded_status_prose` (fails on the historical phrases + session literals in
screens/ and data/; demonstrated firing).

**A-6 · One detector count.** Tonight subtitle now derives
"**6 of 8** detectors fired tonight" (distinct detectors among candidates / trust-audited
detectors in the report); Settings derives "**6 of 8** detectors not rankable" from
settings_2026-09-01.json; the report emits 6 detectors with candidates. Mutually consistent;
no literals.

**A-7 · Veto tells the truth.** Interim wording shipped first, then the real reason once
B2-8 landed. Acceptance (evidence/desk-veto-milkymist-0903.png, session 2026-09-03):
`MILKYMIST — NOT IN TONIGHT'S UNIVERSE: excluded: only 13 of 61 sessions of history
(eligible ~2026-11-11)` — no price/turnover mention. Eligibility is a labelled "~"
estimate (deficit × 365/250). Pre-B2-8 reports fall back to the named-gap wording
(evidence/desk-veto-milkymist.png, session 09-01).

**A-8 · The desk states its age.** TopBar now always renders
`Session <date> · current` or `· N session(s) behind`, weekday-approximation disclosed in
the tooltip, escalated past one session with "— run the nightly refresh"; evening-of-session
reads current (the original false-positive stays fixed). Live: bundle 2026-09-01 on
2026-09-03 showed "2 sessions behind"; after the nightly brought 2026-09-03 it shows
"1 session behind". Smoke test A-8 asserts the age renders.

## PART B — acceptance results

Meters live on candidate cards, Candidates columns, and the Stock panel.
evidence/card-ARIES.png — `chop_band CLEAN, chop_score 51.06, stop_thrust_days 0.78` →
renders **Clean (4 green)** + **Tight (2 amber)** — matches thresholds.
evidence/card-VARROC.png — `VERY_CHOPPY, 66.81, 0.68` → **Very choppy (1 red)** +
**Inside noise (1 red)** ✓.
evidence/card-INDOTECH.png — `chop_band CLEAN, adr_max_pct null, stop_thrust_days null` →
**Clean** + `— needs 250 sessions of history` (not 0, not blank) ✓.
B-3 respected: the red-dominant column is the true finding; the cohort banner states it once
(computed live): "37 of 57 candidates have stops inside 0.75 thrust-days…" (09-01),
(evidence/tonight-feed-0901-momentum-burst.png). Optional B-2 third Thrust meter NOT built
(cohort percentile needs cohort context in a per-row card; skipped as optional).
B-5: CHOP/STOP-TH columns keep numbers + gained band words; DecisionCard Pro panel gained
the meters above its raw thrust rows.

## PART B2 — results

**B2-4 ✓** `run_desk_refresh.py` (now a thin client over `unidesk/server/jobs.py` — the
shared chain, E-1) aborts on the first failed step, runs `run_checks.py` +
`run_published_invariants.py` + `run_export_desk_checks.py` before the build, and fails
unless the newest session advanced (`--allow-no-new-session` for holidays).
Acceptance: downloader renamed → `exit 1`, step named, **no npm build, no DONE line**.
Live proof: the first full API run flagged `inv:scores_have_variance` and **aborted before
build** — the contract working. Docstring now true.

**B2-1 ✓** `adr_max` / `chop_score` registered `kind='series'` with a REAL windowed-scalar
check (warm-up=None-never-0; window alignment `f(x[:k]) == f(x[k-lookback-1:k])`;
current-bar exclusivity — replacing the last bar with an extreme outlier must not move the
output, confirming thrust.py:118/167). `chop_band` / `stop_in_thrust_days` /
`setup_quality_snapshot` skipped with written reasons. Suite: **23 passed, 33 skipped**
(`pytest unidesk/tests/test_truncation_invariance.py -q`).

**B2-2 ⚠ PREMISE FALSIFIED — detector NOT changed; test re-fixtured; owner action needed.**
Full-corpus sweep (4,035 files, EQ series): the detector flags **1,598 sessions across 934
symbols** against a confirmed table of **4 rows**; 2,843 symbols are clean. TCS's flagged
session is **2018-05-31: open −50.7% on ~3× volume, never recovered — the real ex-date of
TCS's 1:1 bonus**. The flag is a TRUE positive; the owner-gated confirmed-actions table is
simply missing the action (an agent must not infer ratios from price gaps). Tightening to
unflag TCS would unflag equally-shaped real actions (AMIORG) — rejected per the handoff's
own "if the count is large, stop and report" gate. The failing test's fixture assumption
("TCS: plain symbol, no CA history at all") was factually false: re-fixtured to
verified-clean **TITAN** (zero flags, 4,034 bars) with a TCS-true-positive regression guard.
**Owner action:** confirm TCS 2018-05-31 1:1 bonus (factor 0.5) from an official ratio
source into `unidesk/config/confirmed_actions.csv`, and review the ~934-symbol queue
(`unidesk/run_ca_review_queue.py`). Test run deferred — needs the full-corpus ingest
(~6 GB; only ~1.5–2.2 GB free all session; logic verified by the light sweep instead).

**B2-3 ⏳ NOT RUN — explicitly last, alone, RAM-gated.** The handoff forbids running it in
a UI wave; the box never had >2.2 GB free (job needs ~6 GB). Command ready:
`.venv-orderflow\Scripts\python.exe unidesk\run_archive_attach_resume.py` — run detached,
verify from persisted partition counts, never process absence. Baseline for its acceptance:
1,177 / 200 / 193 partitions by ca_table_hash, 397 sessions needing refresh.

**B2-4 ✓ (see above) · B2-5 ✓** `showing_synthetic_data` removed from the writer (was
hardcoded True; the desk carries no synthetic data — G-01) and purged from STATE.json;
two consecutive `run_checks.py` runs exit 0 with the key absent (stable).
**B2-6 ✓** `unidesk/RUNBOOK.md` — the real run order, the scheduled task, flags, archive
remediation rules, server startup.

**B2-7 ✓** Nightly registered: `unidesk/nightly_desk.cmd` → `run_scheduled_refresh.py`
(dated logs in `unidesk/logs/`, newest 30 kept; machine-readable `unidesk/last_run.json`) →
Windows task **UniDesk-NightlyRefresh** (weekdays 19:30, interactive logon; next run
2026-09-04 19:30; schtasks command in the RUNBOOK). Acceptance: task fired via scheduler
with an induced download failure → exit 1, log names the failed step, and `/api/health`
exposes it as `last_scheduled_run` → the UI renders a "Last scheduled nightly FAILED"
banner (visible in every evidence screenshot). **Owner decision flagged (in RUNBOOK):**
holiday calendar in the freshness gate vs warning — currently a holiday produces a named,
visible failure (not silent).
**B2-8 ✓** `scan.py` emits per-symbol refusals (primary reason + detail + "also" list with
ALL applicable reasons; insufficient-sessions depth recorded); `report_json.py` publishes
`honesty_footer.symbol_refusals`. Acceptance on the regenerated report
(tonight_2026-09-03.json): `MILKYMIST: {"reason": "insufficient_sessions", "sessions": 13,
"required": 61}`; 1,437 refusals; per-symbol primaries tally exactly to the aggregate
buckets (turnover 848 · price 451 · etf 58 · circuit 5 · insufficient 75).
`unidesk/tests/test_symbol_refusals.py` green (2 passed). **Owner question flagged, not
decided:** the 61-session floor means ipo_base can never see a genuine recent IPO — lower
the floor for that detector with explicit caveats, or state the ~3-month coverage limit in
the UI; `MIN_SESSIONS_DEFAULT` untouched (R14).

## PART C — results

C-1 stale constant+comment deleted (no session literal left in src/data — guarded by
`inv:no_hardcoded_status_prose`). C-2 both modules sort newest-first (guarded by
`inv:dated_bundles_sorted_newest_first`; demonstrated firing on a deliberately broken
sort). C-3 LeftRail deleted. C-4 `scroll-fade-x` defined. C-5 pulse variant deleted.
C-6 tokens deleted. C-7 search navigates to /stock/<SYMBOL>, dead bell removed.
C-8 Beginner gloss brackets balanced (RegimeHero). C-9 denominators labelled
(7,850 sampled probe vs 9,081 exported rows vs 8,843 measurable-R; equity caption +
coverage card + Research MIXED explained via stale_versions; History notes the export is
single-version). C-10 per-row ⚠ removed; panel-level computed coverage statement.

## PART E — results

**E-1/E-2** `unidesk/server/jobs.py` (one REFRESH_STEPS table incl. run_checks; iter_job
events; fail-fast) + `unidesk/server/app.py` (FastAPI, 127.0.0.1:8181, full GET contract +
POST /api/refresh 409-on-concurrent + SSE with heartbeat and finished-job replay;
newest-by-date selection — the E-6 test caught my first implementation preserving filename
order, fixed). Deps installed (fastapi 0.141.1, uvicorn 0.52.4, httpx 0.28.1) and recorded
in root `requirements.txt`. **E-6 ✓ 13 passed** (`pytest unidesk/tests/test_server.py -q`).
**E-3** deskData.ts hydrates every domain in place — zero screen changes; useReport stays
sync deliberately (byte-identical screen API wins over the async-hook wording; loading is
handled at bootstrap with a named skeleton). OFFLINE fallback is loud (banner names the
bundled session; visible in evidence/tonight-feed-0901-momentum-burst.png).
**E-4** framer-motion (only new runtime dep): real Run button (optimistic start → SSE
per-stage progress + elapsed + determinate bar → success toast naming the session or
failure card naming stage+exit code; data rehydrates, screens update, no reload), toasts,
skeletons, route fades, staggered feed, layout-animated ranked rows, count-up hero —
all under MotionConfig reducedMotion="user" + the CSS block.
**E-7:** (1) health ✓ (pasted above, includes last_scheduled_run). (2) **Headline ✓**:
with the server up, a full refresh ran (download→nightly→gate→exports→checks→invariants→
desk-checks), `job_finished session 2026-09-03`; the header session date changed to
03 SEP 2026 with **no page reload and no npm run build**. (3) Failure ✓: induced download
failure streamed `stage_failed download exit 2 → job_failed` over SSE. (4) OFFLINE ✓
(banner evidence). (5) reduced-motion ✓ by construction (MotionConfig user + CSS).
(6) `pytest unidesk/tests/test_server.py -q` → **13 passed**.
**E-5** decision record appended to UI_BACKEND_INTEGRATION_PLAN.md (clause superseded,
not deleted) + ledger record (below).

## PART F — results

**F-1** `.github/workflows/unidesk.yml` (backend suite + run_checks on push/PR paths-filtered;
frontend build = tsc; smoke job with Playwright chromium) + `unidesk/verify.cmd` fast lane +
`.githooks/pre-push` (install: `git config core.hooksPath .githooks`). **CI acceptance
incomplete: gh CLI is not installed on this box, so no PR could be opened to watch a run go
red — the workflow is in place and the same three commands were executed locally
(run_checks green, pytest green, build green).** First push will trigger it.
**F-2** PanelBoundary (mirrors traderlog's PanelErrorBoundary pattern, TS, diagnostic
fallback with retry) wrapping every route; boot skeleton names what is loading. It proved
itself during the wave by converting a render crash into a named panel failure.
**F-3 ✓** `unidesk_terminal/tests/smoke.spec.ts` — 8 route specs (landmark + console-clean,
/api-probe 502 in offline mode filtered as designed) + A-1/A-4/A-8 invariant specs.
Acceptance: A-1 deliberately broken → guard failed (after sharpening: the Other-section
fallback keeps the sum honest, so the assertion is "no unmapped-detector section");
restored → **11 passed**. Wired into CI. The suite caught a real latent bug during the
wave: Vite eager-glob JSON yields module NAMESPACES — `import: "default"` now required in
all five data modules.
**F-4** Register Export/Import JSON + defensive localStorage reads. Acceptance: add entry →
export (`unidesk-register-2026-09-03.json`) → localStorage.clear() + reload → entry gone →
import → entry restored. Server-side persistence (step 3) not built — noted for the next
wave. **F-5** route-level React.lazy + chart chunks split (initial chunk 1,211→1,009 KB
gzip; the remainder is the bundled OFFLINE fallback data — removing it means server-only
mode, flagged not done). **F-6** NOT DONE (end-of-wave item by design): node_modules
untracking, .gitignore extension, gc — touching other projects' tracked files; left for a
dedicated hygiene pass to avoid disturbing unrelated in-flight work. **F-7** class guards
added: `inv:setup_sections_cover_detectors`, `inv:dated_bundles_sorted_newest_first`,
`inv:no_hardcoded_status_prose` (all green; the dated-bundles guard demonstrated firing) +
F-3 render-side invariants (A-1 sharpened, A-4, A-8). run_checks: all green.

## Not done / deferred (explicit)

1. **B2-3 archive remediation** — not run (RAM + wave rules). Command ready; see above.
2. **B2-2 test execution** — deferred with the same ingest; detector verdict, sweep, and
   re-fixtured test are in; owner action on the confirmed-actions table is the real fix.
3. **B2-8 owner question** (ipo_base × 61-session floor) — flagged, not decided.
4. **B2-7 owner decision** (holiday calendar vs warning) — flagged in RUNBOOK.
5. **A-4 residual tension** — TBZ (rr null) is WATCH on Candidates while its Stock verdict
   can read ACTIONABLE; chosen as the least-wrong pairing (rr==null cannot support a
   rejection); the geometry gap itself is the handoff's §H task.
6. **F-1 CI watch** — needs one push (or gh install) to see a run; workflow ready.
7. **F-6 hygiene** — deliberately left; ~300 root files remain.
8. **E-8 note** honoured: bundle size flagged (1,009 KB gzip initial), not fixed further.

## Environment notes

Bash tool worked in this session (house rule 6's broken-Bash applied to a different
sandbox); Python used via the absolute venv path throughout. The desk server was left
STOPPED at session end (start: `python -m uvicorn unidesk.server.app:app --port 8181`).
