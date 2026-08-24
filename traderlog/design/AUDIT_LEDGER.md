# AUDIT LEDGER

**Append dated addenda. Never re-run a whole audit.**

The convention, inherited from `manas_os/design/AUDIT_LEDGER_2026-07-17.md`:

- Findings are coded and keep their code forever: `C<n>` critical, `I<n>`
  important, `G<n>` verified-good (recorded so nobody re-checks it).
- Each finding: one-line repro, then `Fix:`.
- A later pass **appends** an `## ADDENDA (<date>, <source>)` section rather than
  regenerating the file. Re-auditing what a prior pass already certified is waste;
  re-audit only the delta.
- Findings that need work graduate into `TASKS.md` by title. The ledger records
  what was found; TASKS.md tracks what is being done about it.

Sections in order: `## CRITICAL` · `## IMPORTANT` · `## GOOD (verified, keep)` ·
`## Unverified this pass` · then dated `## ADDENDA` blocks.

---

## W0 pass — 2026-08-23 (Claude Opus 5, self-audit at wave close)

### CRITICAL
_None._

### IMPORTANT
- **I1** `checks` reports `not_built_yet` for ingest/parse/derive/telegram rather
  than failing. Correct for W0, but it means a green `checks` run does **not**
  yet mean the tool works end to end. Each wave must flip its own check from
  `not_built_yet` to a real assertion as part of that wave's done-test, or the
  harness quietly becomes decorative.
  Fix: W1–W7 each own their check. Tracked in TASKS.md per wave.

### GOOD (verified, keep)
- **G1** DB path guard works: `traderlog.db.connect()` refuses to open the
  production DB under `PYTEST_CURRENT_TEST` without an explicit path. Adopted
  from Manas OS, where the absence of this guard once polluted the live 717 MB
  database with synthetic fixture rows.
- **G2** No `import manas_os` anywhere in `traderlog/`. The one-way door holds.
- **G3** No model id appears at any call site; all routing goes through
  `llm/provider.py` tiers.

### ADDENDA (2026-08-23, handoff-readiness audit)
- **I2** CONTRACTS.md drifted from the schema within the same session: the
  classifier gained `play_type` / `conviction_words` and two attention tables
  were added, but §1 still showed the old JSON. A model reading CONTRACTS.md as
  the authority would have written a classifier missing two fields.
  **Fixed same pass.** Root cause is that the schema and its contract doc are two
  files with no mechanical link. Cheap guard for a later wave: a test asserting
  every column in `post_class` appears somewhere in CONTRACTS.md.
- **I3** `STATE.json.last_verified_commit` read `28ce22ed` — a commit that
  predates the entire project — because nothing had been committed. The field is
  honest about what git says but misleading about what was verified. It resolves
  itself on the first commit of this work; noted so nobody trusts that value
  before then.

### ADDENDA (2026-08-23, W1 review + design wave)
- **G4** W1's completion claim verified independently rather than accepted.
  `fetch_timeline(handle, since) -> list[RawPost]` matches CONTRACTS.md §7 exactly,
  and self-reply ancestry is real in SQLite: 8 of 12 captured posts are replies
  with correct `conversation_id` grouping across four threads. The VCPSwing
  `#FCL` chain is a genuine reconstructable position. The report was honest about
  its own unverified edges, which is the behaviour we want.
- **I4** `/api/feed` dropped `conversation_id` and `in_reply_to`, so self-reply
  threads could not render — defeating the reason ingest polls `/with_replies`
  at all. W1 flagged it as a cross-wave gap rather than hiding it.
  **Fixed this pass**: fields are additive, `posts` stays a flat list, the UI
  groups. Two follow-on bugs found and fixed while verifying: LIMIT cut threads
  mid-chain leaving replies whose root was absent (an exit with no visible
  entry), and the first sort reversed within-thread so the exit rendered above
  the entry. Threads now order newest-activity-first with posts oldest-first
  inside each.
- **I5** The W0 UI was tables with bars beside them — correctly judged bland.
  Root cause: no binding appearance spec existed, only a one-line "editorial
  poster" aesthetic note, so each screen was built to whatever the builder
  imagined. `design/VISUAL_LANGUAGE.md` now sits above `WIREFRAMES.md` with an
  explicit banned list, a chart vocabulary, and a component contract.

### ADDENDA (2026-08-23, W2 review)
- **C2 — CRITICAL, fixed this pass.** `check_golden` never verified prompt
  versions. Fixtures were compared only against their own stored expectations,
  so a model could edit any prompt and every fixture would still pass **while
  testing against a prompt that no longer existed**. The anti-drift mechanism —
  described in the project's own docs as the single most important test, and the
  thing standing between this tool and silent extraction decay — did not detect
  drift. Fixtures record the prompt hashes they were verified against; the check
  now compares them to `prompts.all_versions()` and reports `stale_prompts_<n>`,
  a status distinct from both pass and fail because a stale fixture is a
  human-re-verification task, not a code failure. Regression test added.
- **I6** `vision.md` rule 5 discards broker order confirmations, holdings tables
  and watchlists as `unreadable` — 3 of 9 real archived images, including a fill
  price of 39.05. Filed as W2b rather than fixed mid-wave: the prompt edit and
  the fixture re-verification must land together. The W2 agent found this,
  refused to invent a broader reading to rescue the number, and recorded the loss
  in the fixture's `unresolved`. That is the correct behaviour.
- **G5** W2 delivered 3 reconcile fixtures from 4 real threads and said so
  plainly rather than padding toward the aspirational 30, and lowered
  `_GOLDEN_FIXTURE_TARGET` with a comment forbidding raising it without more
  real posts behind it. Verified independently: every `evidence` value in all
  three fixtures resolves to a post present in that fixture's own thread, and the
  `unresolved` lists correctly refuse to infer an entry price, convert "2% risk"
  into an absolute stop, or treat "10% up from Entry" on an open position as a
  final result.
- **G6** W2 made **zero** LLM calls and hand-verified every fixture from the
  archived post text and images, honouring the budget constraint.

### ADDENDA (2026-08-23, UI audit + brutalist overhaul)
- **C3 — CRITICAL, fixed.** LEDGER printed "mock rows have no file on disk"
  unconditionally over **real** archived images that served fine (verified: both
  return 200 image/jpeg). It told the user their own captured evidence did not
  exist, on rows whose `is_mock` was 0. The backend endpoint was already correct
  and honest; the frontend simply never called it and rendered a hardcoded
  placeholder. Now a real `<img>`; the "no file" line is an `onError` fallback
  only. Verified live: 2 images load, 1709×80 and 675×680.
- **C4 — CRITICAL, fixed.** `{p.holding_days}d` had no null guard, rendering a
  bare `"d"` for a position with no stated hold time — reads as a broken render
  where every other null in the app correctly shows an em dash.
- **C5 — CRITICAL, fixed.** `Num` defaulted to 0 decimals, rendering the
  VCPSwing broker fill price `39.05` as `39`. Silently destroying a stated price
  is the same class of error as fabricating one. Precision is now adaptive and
  the rule is recorded in `VISUAL_LANGUAGE.md` §1 as correctness, not styling.
- **I7 — fixed.** Screen files still referenced tokens deleted in the overhaul
  (`--line`, `--teal`, `--panel-3`, `--state-green`, …). Those resolve to
  nothing, so the BREADTH chart marks would have rendered invisible. Remapped.
  Root cause worth remembering: a token-layer rewrite must grep **screen** files
  too, not just stylesheets — inline SVG `fill="var(--x)"` is easy to miss.
- **I8** Audit found 12 further spec/UX defects still open: missing confidence
  filters (FEED, LEDGER), category chips coloured with state tokens, TRADERS
  missing its small-multiples frame and sortable headers, TRADERS collapsing four
  charts into one `<p>` instead of four labelled empty frames, BREADTH
  reinventing `BandLine`/`Ribbon` locally instead of importing the house
  components, mobile horizontal overflow from the 7-tab nav, and `Bar` carrying
  no `role`/`aria-label`. Filed, not yet fixed.
- **G7** The prompt-drift detector (C2, added earlier the same day) fired
  correctly on its first real test: W2b's `vision.md` rewrite immediately flagged
  all three reconcile fixtures as `stale_prompts_3`. The mechanism works on a
  genuine prompt edit, not just on a synthetic one.
- **G8** Near-miss caught pre-commit: `git add traderlog` staged
  `data/browser_profile_competing/.../Network/Cookies` — live X session cookies —
  because the ignore pattern named an exact directory and a later session created
  a suffixed variant. Never committed, absent from history. Same bug class hid
  three database backups. Both patterns are now globs.

### Unverified this pass
- Extraction yield on real posts. Unknown until W2's golden fixtures exist, and
  it is the project's largest open risk — if Indian traders' posts are too vague
  to yield stops and targets, this becomes a commentary archive rather than a
  trade log. Measure it before building anything on top of the reconciler.
- Whether Playwright can reliably parse X's current markup, and whether
  timeline-with-replies is reachable from a logged-in profile without triggering
  rate limiting. W1 proves or kills this. Nothing before W1 depends on it.

### ADDENDA (2026-08-23, W3 audit + attribution governance)
- **I9** W3's top handoff wording called the cross-thread linker complete even
  though no runtime producer/batch entrypoint invokes `llm/link.py` for
  canonical posts. The review UI is complete; the end-to-end linker is not.
  **Fixed same pass:** `HANDOFF.md` and `TASKS.md` now distinguish those states;
  the producer is a separate open task.
- **I10** Completion reports previously had prose-only model attribution, which
  could collapse an orchestrator and unnamed executor into one owner. The W3
  report itself caught such an `App.jsx` ownership mismatch. **Fixed same pass:**
  append-only `MODEL_WORK_LOG.jsonl`, mandatory `Attribution-ID` report sections,
  and a production-data-independent checks validator now make provenance
  explicit and reject missing/unknown/path-mismatched records.

## ADDENDA (2026-08-23, copy + UX audits — ALREADY FIXED, do not re-find)

Two audits ran against the live app at 1920×1080. **Every finding below is
already fixed and committed in `73457232`.** Recorded here so a later model
does not spend a wave rediscovering closed findings.

### CRITICAL — fixed
- **C1** TRADERS switched trader profiles with a bare `<tr onClick>`
  (`tabIndex:-1`, no role). Three of four traders were unreachable by keyboard.
  Fixed: uses the same `Disclosure` component LEDGER already used.
- **C2** No cross-screen navigation existed anywhere. Every "thread" link went
  to x.com; handles and symbols were plain text. Fixed: five in-app links, plus
  `navigate(tab, params)` in `App.jsx` so a screen can open pre-selected.

### IMPORTANT — fixed
- **I4** FEED "traders on desk" rail looked clickable, was a static div. Now a
  real `<button>` wired to the trader filter.
- **I5** Nav tabs were the only control skipping the mandated hover-invert.
- **I6** LEDGER could not filter to "no stated stop" despite being the screen
  organised around stated-vs-missing. Toggle added.
- **COPY** Eight strings shipped internal build vocabulary to the user
  ("that is W1/W2/W4/W6", "the reconciler", "manas_os", a link to
  `traderlog/HANDOFF.md`). All replaced; verified absent from the bundle.

### GOOD (verified, keep — do not "improve")
- The prose a human shaped is sharp and was explicitly protected: "work you owe
  the tool"; the deleted-post note about traders deleting losers; the footnote
  refusing to claim the agreement score measures who was right; "Results are
  what the trader *said* — never computed from market data".
- Data honesty held everywhere: unstated values render `—` or "not stated",
  never `0` or blank. Adaptive precision correct (₹39.05 vs ₹955).
- Evidence citations render unconditionally, never behind a toggle.

### OPEN — decisions for the owner, deliberately not guessed
- **D1** `tokens.css` sets `--fs-label: 10px` / `--fs-micro: 9px` while
  `VISUAL_LANGUAGE.md` §1a states an 11–12px metadata floor. Code and binding
  doc disagree; either could move. 38 elements on FEED render below the floor.
- **D2** Two rule-classified events carry `confidence` exactly `1.00`. Rendered
  correctly, but a perfect score on an extraction pipeline warrants a
  calibration look.

### Unverified this pass
- **No pixels were seen.** Screenshots and OS-level click/keypress simulation
  are both non-functional in this environment. Keyboard operability was
  established structurally (native `<button>`, `tabIndex 0`), not by a real
  keypress. A human still needs to look at 1920×1080.
- Chart-image evidence has never been observed working end to end: expanding
  RATEGAIN shows "image not on disk — archive may be incomplete" for both
  media. The fallback is honest rather than fabricated, but the 🖼 "levels read"
  feature is unproven. Likely an archive gap, not a UI defect.
- BREADTH→FEED, IDEAS→LEDGER and LIBRARY→LEDGER cross-links could not be
  exercised — those tables have zero rows. Re-check after W4.

## ADDENDA (2026-08-24, post-W4 audit — Claude Opus 5)

### CRITICAL — open, needs an owner decision
- **C6 — XP is fed percentages where its calibration expects counts.**
  `adopted/universe_breadth.py:169` computes
  `"up_4pct": round(max(up / n * 100.0, 0.25), 3)` — a **percentage**.
  `adopted/xp.py`'s docstring is explicit that these are **counts**: "Term 5 is
  the 4.5%- big-decliner **count**" and "The z_state advancer **count** must
  come from the SAME universe the formula was calibrated on (NIFTYMIDSML400)".
  On a ~400-name universe that is a **4x scale error** on both `z_state` inputs.

  Compounding it, `config.regime.xp_z_seed` is **20.0** — a count-scale seed —
  while the daily feed arrives percent-scale (observed `up_4pct` min 0.25,
  max 40.3, avg 3.6).

  Evidence this is real, not theoretical:
  - All eight sessions that hit `_XP_CAP` (250.0) are **2024-09-17 → 2024-09-26**,
    immediately after the `2024-09-02` seed, with `z` between 4.1 and 5.6 — the
    signature of a seed decaying from count scale to percent scale.
  - `xp.py`'s own comment says "reference tops out ~30". Observed range is
    **0.01 → 250.0, avg 16.66**, with **343 of 446 sessions (77%) in LOW** while
    MBI reads GREEN on 168 sessions. XP and MBI persistently disagree.
  - This is precisely the failure `DECISIONS.md` (2026-08-23) warned about:
    "feeding it advancer counts from a different universe produces plausible,
    wrong numbers silently."

  **Not fixed here — it is an owner calibration decision, not a bug fix.**
  Options, none obviously right: (a) feed counts and keep the published weights;
  (b) keep percentages and re-seed at percent scale, accepting the dial no
  longer matches the reference; (c) re-derive weights against this universe.
  Until it is resolved, **the XP number on the BREADTH screen should not be
  trusted**, and the screen should say so.

### IMPORTANT
- **I8 — extraction yield measured, and the constraint is the corpus, not the
  parser.** FEED's Desk panel reads "30 posts · 25 threads · **2 events
  joined**". The visible feed is almost entirely cricket (Ben Stokes, Brydon
  Carse, County Championship), correctly classified `noise` at 0.99. The
  classifier is working; `@Fastzonetrader` simply posts a lot of non-market
  content. Roster curation, not prompt tuning, is the lever here.
- **I9 — bundle size.** `echarts` + `vega-lite` + `vega-embed` push a chunk past
  500 kB and Vite now warns on every build. Acceptable for a local tool; worth
  code-splitting if it grows.

### GOOD (verified, keep)
- **G7 — `derive` reports honest staleness.** `WARN … 2026-08-14 is 9d old`
  rather than a faked pass or a hard fail. This is exactly the behaviour the
  harness was designed for and the wave was briefed on.
- **G8 — the visual work holds up at 1920×1080.** First pixels seen this
  session, via `output/playwright/evidence-desk/*.png`. Warm canvas, 1px rules,
  sentence case, real two-column workspace, labelled empty states, and the
  agreement-score disclaimer preserved verbatim. BREADTH renders real XP/MBI
  with the 90-session ribbon and a labelled trend line.
- **G9 — 256 tests pass** (up from 175). No regressions across three waves.

### Unverified this pass
- Whether XP is *only* mis-scaled or also mis-specified. The count/percent
  mismatch is proven; whether correcting it alone produces a sane dial is not.
- The five newly loaded sessions (2026-08-17 → 21) had not yet propagated to
  `breadth_daily` / `regime_daily` when this was written.

### ADDENDA (2026-08-24, risk sweep — Claude Opus 5)

- **C7 — CRITICAL, open. 434 classifications bypassed the provider and carry no
  prompt version.** `post_class` holds 434 rows; **zero have `run_id`**, and
  `llm_runs` contains only 2 entries, both failed vision smoke-tests. The model
  string is `deepseek-v4-flash-vision-exp (this chat report)` — honest about its
  origin: the output was produced in a chat session and written directly to the
  table rather than run through `llm/provider.py`.

  The confidence values vary properly (0.9, 0.85, 0.95, 0.92, 0.6, 0.8), so this
  is genuine classifier output, not a rule-based fill. The data is probably fine.
  **The provenance is not**, and three things follow:

  1. **No prompt version was recorded.** `check_golden` compares fixture prompt
     hashes against `prompts.all_versions()` to catch silent extraction drift —
     the project's own docs call it the most important test. It does not cover a
     single one of these 434 rows.
  2. **They are not reproducible.** Re-running the tool regenerates nothing.
  3. The single-writer contract for `post_class` (`llm/classify.py`, per
     CANONICAL.md §6) was bypassed.

  **Fix, not yet built:** a check that fails when a `post_class` row has a
  non-`human:*` model and a NULL `run_id`. That closes the bypass permanently
  instead of relying on convention. Until then, treat the 434 classifications as
  useful but unverifiable, and re-run them through `classify.py` when the corpus
  is next processed so the ledger and prompt hashes exist.

- **I10 — my own earlier yield figure was wrong and understated the tool.** I
  reported "2 events from 30 posts" from the FEED Desk panel and generalised from
  one screen. Across the full corpus it is **100 `trade_event` of 453 posts
  (22%)**, with 227 `noise` (50%), 54 education, 24 breadth, 21 watch ideas.
  Corrected here so the low number does not get quoted onward.

- **I11 — 100 classified trade events, 3 reconciled positions.** The reconciler
  has never run on the current corpus; `positions` still holds only the three
  hand-verified fixtures from when the archive was 12 posts. This is the highest-
  value unblocked task in the project: the pipeline is built and tested, and 97
  trade events sit unprocessed behind it. Everything downstream — style profiles,
  practice-vs-preach, the attention engine — waits on it.

### ADDENDA (2026-08-24, C6 RETRACTED — Claude Opus 5)

- **C6 is WITHDRAWN. The diagnosis was wrong and the fix it caused made a
  working metric worse.** Recorded in full because the reasoning error is more
  instructive than the finding was.

  **What C6 claimed:** XP is fed percentages where `xp.py`'s docstring specifies
  counts; on a ~400-name universe that is a 4x scale error; evidence was that
  77% of sessions sat in LOW and 8 hit the 250 cap.

  **What testing showed.** Recomputing all 451 sessions under six input
  conventions against the documented "reference tops out ~30":

  | convention | median | avg | >30 | at cap |
  |---|---|---|---|---|
  | **percent (original)** | **7.7** | 15.8 | 31 | 7 |
  | count = pct/100*400 (W4b's change) | 30.4 | 47.9 | **230** | 14 |
  | percent x 0.5 | 3.9 | 10.1 | 19 | 7 |
  | percent x 0.1 | 0.8 | 5.6 | 10 | 7 |

  Counts put **230 of 451 sessions above the top of the dial**. Half the
  trading days cannot be extreme. Percent gives a median of 7.7 with occasional
  spikes, which is what a strength dial should look like — most days are not
  strong markets.

  **The reasoning error:** "77% of sessions in LOW" was read as a defect. LOW is
  `< 15`. Most days genuinely are weak. A correct distribution was mistaken for
  a bug, and the fix was then reasoned from a single word in a docstring
  ("count") rather than tested. **A fifteen-minute numerical test would have
  prevented an entire wave.** Test the distribution before theorising about the
  inputs.

- **C8 — the real defect, and it is narrow: the cap hits are a seed transient,
  not a market event.** They survive *every* input scaling, including
  percent x 0.1, so input scale was never the cause.

  All eight EXTREME sessions are **2024-09-17 → 2024-09-26**, at the very start
  of the series, and their inputs are unremarkable: `up_4pct` 0.86-10%,
  `pct_above_10dma` 39-57%. For contrast, 2026-04-17 with `pct_above_10dma` at
  95.5% — a genuinely strong tape — reaches only 81.3.

  The recursion is still unwinding from `xp_seed: 15.0` / `xp_z_seed: 20.0` at
  the series start. `z_state = 0.162*up4 + 0.838*z_prev` has a ~1/0.162 ≈ 6
  session memory, and `log_XP` carries `0.592*log(XP_prev)`, so a mis-scaled
  seed takes roughly 15-25 sessions to wash out and produces garbage the whole
  time.

  **Fix:** revert to percent inputs, then either warm the recursion up over
  ~20 sessions before persisting any row, or seed `z` from the first sessions'
  observed `up_4pct` instead of a constant. Flag or discard the transient rather
  than presenting it as data.

- **G10 — W4b's corporate-action filter was sound and is unaffected.** The
  35% threshold, its config key, and its honest comment about what it costs are
  independent of the XP question and should be kept.

### ADDENDA (2026-08-24, scouting-wave close — deepseek-v4-flash orchestrator, personally re-run)

- **C8 — FIXED, production recomputed and verified.** The seed transient is
  gone from the persisted series. Fix (in this wave, per the retraction's own
  "Fix:" paragraph): (a) revert to percent inputs — the retracted C6 percent→
  count conversion in `adopted/regime_daily.py` was removed; (b) seed the
  z-state from the session's own observed `up_4pct` at reseed points instead
  of the count-scale constant (`adopted/xp.py`); (c) warm the recursion up —
  `regime_daily.backfill(warmup_sessions=20)` computes the first 20 breadth
  dates in memory and persists nothing, so the series-start transient is
  discarded, not presented as data. `compute_xp` is byte-for-byte unchanged.

  Production recompute evidence (`python traderlog/_discard_transient.py`
  against `data/traderlog.db` after the pre-change backup
  `data/traderlog.db.backup-pre-xpfix-20260824`; scratch scripts deleted
  after):

  ```
  regime_daily: 451 rows before -> 431 persisted after (20 warm-up discarded)
  at _XP_CAP (250): 0        EXTREME band: 0        max xp: 81.31
  bands: LOW 349 (81.0%) · BUILDING 67 · STRONG 15
  first persisted: 2024-09-30 (BUILDING), from the threaded in-memory chain
  reseed_points: ['2025-06-20']  (46-day gap: seeds from observed up_4pct=2.949)
  latest-5 breadth/regime parity: True (through 2026-08-21)
  ```

  The audit's own per-row note ("the transient survives every input scaling")
  is explained and resolved: the residual 2024-09 caps came from
  `pct_above_20dma == 0.0` on the first ~19 sessions (SMA20 uncomputable at
  series start) clamping `logit()` at the log-domain edge; the warm-up
  discards exactly that window. Distribution now matches the reference shape:
  median 7.7, most days LOW, occasional spikes to ~80 — a strength dial.

- **I12 — first persisted session (2024-09-30) reads 30.9 BUILDING**, carrying
  ~2 sessions of elevated carry from the discarded p20=0.0 in-memory chain
  (a clean-lookback reference gives ~18.6). Cosmetic, below STRONG; noted so
  nobody re-opens C8 over it.

- **G11 — the redesign direction and the Market screen are now live**:
  `REDESIGN_SCOUTING_WIRE.md` built across all six screens + the Symbol landing
  page + the ⌘K command bar; `VISUAL_LANGUAGE.md` §1/§1a/§3 marked superseded;
  `WIREFRAMES.md` reconciled. The Market screen renders WITHOUT the §8 caution
  block (XP fixed, this addendum).

- **G12 — the S1 executor's initial C8 claim was incomplete and caught at
  verification.** Its first report claimed the done-test met, but the
  persisted production series still contained the 2024-09 transient (8 cap
  hits / 9 EXTREME) because warm-up had not been implemented and the pre-
  existing rows were never discarded. The orchestrator re-ran the recompute
  and required the warm-up follow-up before accepting. Recorded as a verified
  catch, not a failure.
