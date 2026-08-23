# SESSION HANDOFF — 2026-08-23 (Claude Opus 5 → next model)

Written at a deliberate pause. Read `traderlog/AGENTS.md` first if you have not;
this file assumes it.

**Do not trust this document over the working tree.** It was accurate at commit
`bd59d464` with W4 mid-flight. Run `git log --oneline -5` and
`python traderlog/run_checks.py` before believing anything below.

---

## 1. Read-first chain

`AGENTS.md` → `CANONICAL.md` → `STATE.json` → `HANDOFF.md` → `TASKS.md` →
`design/CONTRACTS.md`. Before any UI work also read `design/VISUAL_LANGUAGE.md`
(binding, and **§1a supersedes conflicting clauses below it**) then
`design/WIREFRAMES.md`.

Run `python traderlog/run_checks.py` before you start and after you finish.
**Note: this machine's python has `safe_path` on and ignores `PYTHONPATH`, so
`python -m traderlog.checks` fails.** Use the `run_*.py` shims.

---

## 2. Where things stand

Committed and verified:

```
bd59d464  lightweight-charts on the renderer ladder, behind two gates
baa515a4  correct a stale handoff that was about to cost a wave
73457232  stop shipping our build vocabulary, and make the tool navigable
4b5ef5cd  cross-thread linking, a PC-grade shell, and per-model attribution
```

| Wave | State |
|---|---|
| W0 frame, schema, checks, UI shell | complete |
| W1 ingest (Playwright + Chrome import) | complete; 12 real posts, 4 threads, 4 traders |
| W2 vision + reconciler + golden fixtures | complete; **never run against a live model** |
| W2b vision prompt repair | complete |
| W3 cross-thread linking + `run_link_pass` | complete as a library entrypoint; **nothing invokes it** |
| W3c 1920×1080 evidence-desk shell | complete |
| copy + UX audit fixes | complete |
| **W4 breadth + XP/MBI** | **complete — root accepted; see §3** |
| W5 Reactor Scale, W6 style, W7 Telegram, W9/W10 attention | not started |

Checks at last green run: `db`, `ingest`, `parse`, `golden`, `attribution`, `ui`
pass; `derive` honestly `stale_9d`; `telegram` `dry_run`.

---

## 3. W4 COMPLETE — root accepted production/API/Chrome evidence

The production run completed once; do not re-run ingestion unless a new source
run is explicitly required. It found 467 source dates, loaded **1,327,505** `daily_prices` rows
over **446** EQ sessions, and produced matching 446-row date sets in
`breadth_counts`, `breadth_daily`, and `regime_daily`. XP, XP z-state, MBI day
color, MBI score, and warning values are non-null on the derived rows.

The only XP reseeds were `2024-09-02` and `2025-06-20`. XP remains a
date-ordered recursion: a source gap must be reseeded, never interpolated.

XP is calibrated on the NIFTYMIDSML400 universe. `universe_breadth.py` and its
400-symbol constituent CSV are therefore hard dependencies. Canonical breadth
now requires at least 85% actual-date coverage (340/400 for the current file);
the completed run observed minimum 347, median 382.5, and maximum 400. Rows
below that threshold are logged as failures and are not persisted.

`run_w4.py` now stops at the first failed boundary: bhavcopy blocks stages 2–4,
breadth counts block universe/regime, and universe breadth blocks regime. A
bhavcopy file whose internal `DATE1` differs from its requested date is rejected
before price persistence. The `derive` check compares the newest five breadth
dates and regime rows exactly and requires all XP/MBI fields above; it should
report honest stale freshness (currently `stale_9d`-equivalent), not
`not_built_yet`.

`breadth_analytics.py` was deliberately removed: no named API/UI consumer
exists. Revisit it only with a specified payload or screen element.

Root separately completed production DB/API/Chrome acceptance with real data:
at a 1920×1080 viewport the document width was 1920, panel overflow count was
zero, no long decimals rendered, and the BandLine aria label was exactly
`Trend: 90 points, latest 7.3 (low).` This executor did not perform that browser
or API verification. See `HANDOFF_W4_breadth_COMPLETED.md`; root's own
append-only attribution records follow separately.

---

## 4. The single most important thing nobody has done

**The LLM pipeline has never run.** `llm_runs` = 0. Ten of twelve posts are
unclassified. All three positions are `reconcile_model = human-terra-verified`
— hand-written fixtures, not model output.

So `parse: pass` and `golden: pass` currently certify that **hand-written truth
matches hand-written expectations**. That is a real test of the plumbing and it
is *not* evidence the extraction works. A green board here is weaker than it
looks, and anyone reading the checks should know that.

Real extraction yield is the project's largest unknown and is now cheaply
measurable: run `llm/classify.py` over the 12 real posts on a free tier. Budget
rules are in §6.

---

## 5. Rules that will bite you

- **Adopt, never import.** No `import manas_os` anywhere in `traderlog/`. Copy
  files into `adopted/` with a provenance header. The one-way door is checked.
- **Single writer per table** — `CANONICAL.md` §6. If you need to write a table
  that is not yours, stop and say so.
- **Every extracted field cites its post.** `evidence_json` maps field →
  `post_id`. A field you cannot cite is dropped, not stored. Anything the trader
  did not state goes in `unresolved[]`. **Never infer a number.** A wrong price
  is worse than a missing one — the whole value here is that it is a factual
  record.
- **Never name a model at a call site.** Ask `llm/provider.py` for a tier.
- **Production is real-data-only.** Never run `seed_mock.py` against
  `data/traderlog.db`.
- **Do not commit.** Write your `_COMPLETED.md`; the maintainer QCs and commits,
  one wave per commit.
- **Each wave flips its own check** from `not_built_yet` to a real assertion.
  A wave that does not leaves the harness decorative — audit finding I1.

---

## 6. LLM budget

`llm.daily_budget_usd` is `0.0` and tiers are `:free`; `provider.py` enforces it
and refuses paid calls rather than silently spending. **The owner's OpenRouter
credits are not to be spent on agent work.** Small free-tier smoke tests are
fine. Do not batch-process, and never generate golden fixtures with a model —
a fixture produced by the thing it tests, tests nothing.

---

## 7. The mistake this session made — do not repeat it

`HANDOFF.md` said *"Next: W3c — execute it"* while
`HANDOFF_W3c_pc_ui_recovery_COMPLETED.md` sat beside it saying W3c was done.
Both were committed together without the contradiction being noticed. A second
tool nearly re-executed a finished wave over `App.jsx`, `ui.jsx`, `Feed.jsx`,
`Ledger.jsx` and `app.css` — and **git would not have warned**, because
overwriting a clean tree is not a merge.

Two habits that would have caught it:

- When a `*_COMPLETED.md` exists, verify the wave's own done-tests against the
  working tree before believing *either* document.
- Before writing any file, `git log --oneline -3`. If your brief predates the
  head commit, re-read the files on disk rather than trusting your copy.

An unbuilt guard worth adding: a check that fails when a `*_COMPLETED.md` exists
while `HANDOFF.md` still says "Next: <that wave>".

---

## 8. Verified-good, do not "improve"

The copy audit found the human-shaped prose genuinely sharp and named it for
protection. Rewriting any of these is a regression:

- "work you owe the tool" (review queue)
- the deleted-post note about traders deleting losers biasing every metric
- the footnote that the agreement score measures agreement with one breadth
  model, **not** whether the trader was right
- "Results are what the trader *said* — never computed from market data"
- "not enough linked trades yet — N of a 10-trade minimum"

Also verified sound: unstated values render `—` / "not stated", never `0`;
adaptive precision (₹39.05 below 100, ₹955 above); evidence citations render
unconditionally, never behind a toggle.

---

## 9. Blocked on the owner — do not attempt these

1. **Log into X by hand** in the Playwright profile dir. No agent can or should.
   Until then ingest cannot run live and the corpus stays at 12 posts.
2. First capture for four approved handles: `@StocksNerd`, `@ChartistEdge`,
   `@iArpanK`, `@mystocks_in`. Live set is still the original four.
3. `tokens.css` sets `--fs-label: 10px` / `--fs-micro: 9px` against
   `VISUAL_LANGUAGE.md` §1a's stated 11–12px floor. Code and binding doc
   disagree; 38 elements on FEED render below it. **Do not silently pick one.**
4. Two rule-classified events carry `confidence` exactly `1.00` — calibration
   question, not a UI defect.
5. Confirm the W5 assumption that "the volume reverse engineer" is
   `manas_os/alpha/activity.py`.
6. The OpenRouter slug for **Ox Alpha** — deliberately not guessed.
7. Telegram bot token + chat id, at W7.

---

## 10. TO-DO — the actual work queue

Ordered. Each item names its done-test. Nothing here is started unless marked.

### T1 — W4 breadth + XP/MBI (COMPLETED)
- [x] One production backfill: 467 source dates; 1,327,505 price rows over 446
      EQ sessions; matching 446-row breadth/count/regime date sets; no null
      XP/z/MBI fields. Do not re-run it unless a new source run is required.
- [x] Enforce 85% actual-date NIFTYMIDSML400 coverage (340/400); observed
      coverage was min 347, median 382.5, max 400. A below-threshold date fails
      without a canonical breadth row.
- [x] Guard `DATE1`, stage fail-fast boundaries, and five-date derive parity;
      defer unused breadth-ratio/HL analytics until it has a named consumer.
- [x] Root accepted the API and BREADTH screen with real API/DB data at 1920×1080:
      document width 1920, zero panel overflows, no long decimals, and BandLine
      aria label `Trend: 90 points, latest 7.3 (low).`
- [x] Executor completion record and handoff are present. Root's separate
      attribution records are append-only follow-up, not a reason to reopen W4.
- **Done-test met:** `run_checks.py` reports honest `stale_9d` derive freshness;
  root's BREADTH-screen acceptance observed verified XP/MBI values without mock data.

### T2 — Measure extraction yield (cheap, de-risks everything downstream)
- [ ] Run `llm/classify.py` over the 12 real posts on a **free tier**.
- [ ] Record how many yield a usable `kind`, `symbols`, `play_type`.
- **Why first among the LLM work:** `llm_runs` is 0 and yield is the project's
  largest unknown (§4). Everything after this — style profiles, the attention
  engine, practice-vs-preach — assumes extraction works, and nothing has tested
  that assumption against a model.
- **Done-test:** a number, written into `AUDIT_LEDGER.md`, and `llm_runs` > 0.

### T3 — NSE symbol validation
- [ ] Validate extracted symbols against a real NSE ticker list.
- [ ] `FCL` came from a bare `#FCL` hashtag with nothing checking it resolves.
- [ ] Unresolvable symbols must surface as unresolved, never silently kept.
- **Gates T4.** A chart of the wrong instrument looks authoritative and is false.
- **Done-test:** every symbol in `positions` / `watch_ideas` either resolves or
  is flagged.

### T4 — lightweight-charts price pane
- [ ] Add the dependency; it is on the ladder for this one row only
      (`VISUAL_LANGUAGE.md` §2, `DECISIONS.md` 2026-08-23).
- [ ] Price pane for a symbol on LEDGER / IDEAS, reading `daily_prices`.
- [ ] Labelled empty frame when bars or a validated symbol are missing.
- **Blocked on T1 and T3.**

### T5 — Wire the W3 link producer
- [ ] `run_link_pass` exists in `llm/link.py` and **nothing invokes it**. It is
      a library entrypoint with no caller, so cross-thread linking is not a
      production capability yet.
- [ ] Wiring belongs to W2 parse orchestration, which is not built. See
      `HANDOFF_W3_link_AUDIT_FEEDBACK.md`.

### T6 — W5 Reactor Scale
- [ ] Adopt `manas_os/alpha/activity.py` + `alpha/schema.py` +
      `engine/universe_filter.py`. `DELIV_QTY` / `DELIV_PER` are present in the
      bhavcopy CSVs, so the inputs exist.
- [ ] **Blocked on owner confirmation** that `activity.py` is what "the volume
      reverse engineer" refers to (§9).

### T7 — W6 trader style profiles
- [ ] Hold-time distribution, stated-exit win rate, avg R, sector tilt, stop
      discipline (stated vs honoured), preach score.
- [ ] Unblocks the four empty charts on TRADERS, which currently render empty
      frames by design.
- [ ] Needs materially more than 3 positions to be meaningful — gated on live
      ingest (§9 item 1), not on code.

### T8 — Guard against the stale-handoff class of error
- [ ] Add a check that fails when a `*_COMPLETED.md` exists while `HANDOFF.md`
      still says "Next: <that wave>". See §7 for why this is not hypothetical.

### T9 — Close the verification gap
- [ ] **Someone must look at the tool at 1920×1080.** Two commits of UI work are
      verified structurally only; no pixels have been seen (§11).
- [ ] Confirm chart-image evidence works end to end — expanding RATEGAIN shows
      "image not on disk" for both media and the feature is unproven.
- [ ] Re-check BREADTH→FEED, IDEAS→LEDGER, LIBRARY→LEDGER cross-links once
      those tables have rows.

### Deferred, specified, not started
- **W7 Telegram** — outbound digests via the transactional outbox; blocked on
  the owner's bot token.
- **W9/W10 attention engine + validation** — full spec in
  `design/ATTENTION_ENGINE.md`. Do not start early; every input is missing.
  The score must not ship as a ranking until it beats the universe median at
  +10 sessions over ≥60 clusters.

---

## 11. What has never been seen

**No pixels.** Screenshots and OS-level click/keypress are both non-functional
in this environment. Two commits of UI work — the brutalist reskin, five
cross-screen links, the TRADERS keyboard fix — are verified **structurally
only**: native `<button>`, `tabIndex 0`, computed styles, `getBoundingClientRect`.
Keyboard operability was inferred from the HTML spec, not observed.

**Chart-image evidence has never been observed working.** Expanding RATEGAIN
shows "image not on disk — archive may be incomplete" for both media. The
fallback is honest rather than fabricated, but the 🖼 "levels read" feature is
unproven end to end. Likely an archive gap, not a UI defect.

**Three cross-links are untestable** — BREADTH→FEED, IDEAS→LEDGER,
LIBRARY→LEDGER. Those tables have zero rows. Re-check after W4.

If you can take a screenshot in your environment, do it early and report what
you actually see. That gap is the biggest hole in this session's verification.
