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
| **W4 breadth + XP/MBI** | **IN FLIGHT — see §3** |
| W5 Reactor Scale, W6 style, W7 Telegram, W9/W10 attention | not started |

Checks at last green run: `db`, `ingest`, `parse`, `golden`, `attribution`, `ui`
pass; `derive` `not_built_yet`; `telegram` `dry_run`.

---

## 3. W4 IS MID-FLIGHT — read before touching anything

A Sonnet subagent was executing `W4` when this was written. **Its state on disk
is partial.** Verify before continuing or discarding.

Written, uncommitted:
`adopted/bhavcopy.py`, `breadth_analytics.py`, `breadth_counts.py`, `mbi.py`,
`regime_daily.py`, `universe_breadth.py`, `xp.py`, plus `run_w4.py`,
`traderlog/data/`, and edits to `checks/runner.py`, `config.example.yaml`,
`adopted/__init__.py`, `STATE.json`.

**Not done:** `daily_prices`, `breadth_daily`, `breadth_counts` and
`regime_daily` were all still **0 rows**. The modules exist; the ingestion had
not run.

Decide first: resume it, or verify and finish it yourself. Do not start a
parallel W4 — you will collide with files already written.

### The three traps W4 was briefed on

1. **A 46-day gap in the bhavcopy data: 2025-05-05 → 2025-06-20.** XP is a
   *recursion* on the prior session's `xp_value`/`xp_z_state`. A gap is a chain
   break, **not something to interpolate across**. Carrying the pre-gap value
   forward 46 days fabricates market state. `config.example.yaml` now carries
   `regime.xp_seed` / `xp_z_seed` for first-run and post-break reseeding.
   **`Unverified:` whether that gap is a real market closure or simply CSVs
   never downloaded.** Nobody has checked. If it is the latter, backfilling
   beats designing around a break that should not exist.
2. **XP's weights were calibrated on NIFTYMIDSML400.** Feeding it advancer
   counts from a different universe yields plausible, wrong numbers silently.
   `universe_breadth.py` + `data/niftymidsml400_constituents.csv` are hard
   dependencies of XP, not optional breadth extras.
3. **The price data ends 2026-03-23; today is 2026-08-23 — five months stale.**
   The `derive` check asserts breadth for the last 5 trading days and will not
   pass. **Do not weaken the check and do not fabricate recent rows.** Report an
   honest `stale_<n>d`, the shape `check_ingest` already uses.

### Data on disk, verified
493 NSE bhavcopy CSVs at **repo-root `data/bhavcopy/`** (not
`traderlog/data/bhavcopy`), 230 unique sessions, `2025-03-19 → 2026-03-23`.
Header has **leading spaces** — parse defensively. `DELIV_QTY` / `DELIV_PER`
are present, so W5's Reactor Scale is feasible later.

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

## 10. Suggested order

1. **Resolve W4** — finish or verify the in-flight work; populate `daily_prices`
   → `breadth_daily` → `regime_daily`; flip `derive` honestly.
2. **Measure extraction yield** (§4). Cheap, and it de-risks everything after.
3. **Symbol validation against the NSE universe.** The corpus holds `RATEGAIN`
   and `FCL`; `FCL` came from a bare `#FCL` hashtag with nothing checking it
   resolves to a real ticker. This gates the chart work.
4. **lightweight-charts price pane** — approved and on the ladder
   (`DECISIONS.md` 2026-08-23), gated on 1 and 3.
5. W5 Reactor Scale, then W6 style profiles.

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
