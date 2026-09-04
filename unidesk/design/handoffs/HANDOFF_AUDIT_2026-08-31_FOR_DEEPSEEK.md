# HANDOFF — full audit, 2026-08-31 — for the next session (DeepSeek or any model)

Author: Claude (Opus 5), orchestrating session `koreanguy-fb`.
Audience: whoever picks this up next. Written to be actionable without this conversation.

**Read this before touching anything.** Two findings below are stop-work items:
the corporate-action table is built on inferred ratios (§1), and the archive
audit numbers circulating in this project are stale (§2).

Governing documents this audit was checked against:
- `phase0_implementation_data_build_spec_v1.md` (owner-supplied, in Downloads)
- `ai_native_indian_swing_research_constitution_v1.md` (owner-supplied, in Downloads)
- `unidesk/design/UI_BACKEND_INTEGRATION_PLAN.md`
- `unidesk/GOAL.md`, `unidesk/TASKS.md`

---

## 0. What I actually verified vs. what I did not

**Verified directly** (ran the code / read the file / drove the live UI):
every claim in §1–§6 carries a file:line, a command output, or a live-browser
observation. Where I ran a script, the script is named.

**NOT verified — do not treat as settled:**
- I did not re-run the archive audit after CA55 finishes. §2's numbers are void.
- I did not diff the built screens against `UNIFIED_DESK_UI_UX_MANUAL_V2.md`
  in full; UI claims are bounded by what renders and by code inspection.
- I did not verify any of the 51 auto-confirmed corporate actions against an
  authoritative source. That is the core of §1 and is the owner's call.
- I did not benchmark whether the detectors have an edge. That is blocked.

---

## 1. STOP-WORK — the corporate-action table is built on inferred ratios

**Status: this invalidates any research output built on the current archive.**

`unidesk/config/confirmed_actions.csv` went from 4 rows to 55 in commit
`823e1141`. Provenance breakdown:

```
close_to_close_archive_v1          4   (genuinely verified)
split_detector_auto_confirmed_v1  51   (INFERRED FROM THE PRICE GAP)
```

`unidesk/run_ca_auto_confirm.py` accepts any review-queue candidate whose
`clean_distance_pct <= 0.5` and whose `nearest_clean` matches a known
fraction, and writes it in as a **confirmed** action, which then
**back-adjusts real price history**.

This is forbidden in four separate places in this project:

| Rule | Where |
|---|---|
| "Detection never auto-adjusts… a wrong back-adjustment silently corrupts every historical feature" | `unidesk/momentum/data/corp_actions.py:5-12` (its own docstring) |
| "only the ratio source is owner-gated — do not infer ratios from price gaps" | owner's standing directive, this session |
| "ASHOKLEY-style open-gap fills stay out" | `unidesk/TASKS.md:176` — and `ASHOKLEY,2025-07-16,0.5` is now row 7 |
| "Conditional / manual review: rights issues, demergers, mergers, schemes" | Phase 0 spec §11.2 |
| "adjustment factor changes price history without audit record" = **BLOCKER** severity | Phase 0 spec §32.1 |

### Why this is dangerous in the wrong direction

A gap of ~0.5× has at least five causes, and the detector cannot distinguish them:

```
1:2 split          → factor 0.5 correct
bonus issue        → different ratio semantics
demerger / scheme  → NO clean fraction exists; price drops by spun-off value
rights issue       → requires manual review per spec §11.2
a real −50% crash  → fraud, regulatory action, guidance collapse
```

The detector's only extra filter is "volume continued ≥ 0.1× prior" — a crash
has continued volume too. **Back-adjusting a genuine −50% crash erases a real
catastrophic loss from history.** That is optimistic bias in exactly the
direction the stop-aware and gap-through label work existed to remove. The
archive would then show a detector surviving an event that actually ruined it.

Phase 0 spec §34 requires every `abs(raw_ret_1) >= 20%` move to carry a reason
code (`EXTREME_MOVE_CA` / `_CIRCUIT` / `_LISTING` / `_REAL` / `_UNKNOWN`) and
routes unknowns to a review queue **before labels are created**. The
auto-confirmer skips that entirely.

### Required action (owner decision, do not guess)

Pick one:

- **(a) Revert to 4.** `git revert 823e1141`, regenerate. Safest; loses real splits.
- **(b) Quarantine the 51.** Keep them in the table but route them through the
  existing `unconfirmed_candidate_sessions` path so they refuse outcomes
  (`UNRESOLVED` / `unconfirmed_corporate_action`) instead of back-adjusting.
  Preserves the work, stays honest. **This is my recommendation.**
- **(c) Verify all 51 against NSE corporate actions** and re-tag as
  `close_to_close_archive_v1`. 51 tickers is a small job. Best outcome.

Whichever is chosen, the `source` column already distinguishes them — that part
was done honestly and makes the fix cheap.

---

## 2. The archive audit numbers in circulation are STALE — including mine

I ran a full archive audit and reported clean results. **Those numbers are void.**
I read the 396 partitions while a CA55 regen was actively rewriting them, so the
statistics mixed two different adjustment bases.

I also told the owner "regen finished, no process running" based on
`ps aux | grep python` returning empty. That was wrong — the regen was running
and writing files seconds before I checked. **Do not use process-absence as
proof a job finished.** Verify from persisted output: partition mtimes, row
counts, and a completion line in the log.

Re-run after CA55 completes:
```bash
python "<scratchpad>/audit_archive.py"    # recreate from §7 if lost
```

What the (stale) run did establish qualitatively, worth re-checking:
- label-version stamping and gap-through/net-cost wiring **do** reach the writer
- `net_bps` is absent on ~58% of events because ADV is missing — fail-closed and
  correct per Phase 0 spec §41 ("missing ADV → no simulated trade"), but it means
  **net-of-cost analysis currently covers only ~41% of the archive**
- the R distribution is dominated by degenerate near-zero-risk rows (liquid ETFs
  like `LIQUID1`, `HDFCLIQUID` producing |R| in the hundreds). `research/archive_attach.py`
  does **not** apply `momentum/universe/gates.py`, so ETFs the nightly scan
  excludes are still in the research archive. Phase 0 spec §18.2 lists ETF as a
  default exclusion. **Fix this before any N5 experiment.**

---

## 3. Owner's UI complaints — verdict on each

Checked in the live app (`npm run dev`, port 5183), not by reading code alone.

| # | Complaint | Verdict | Evidence |
|---|---|---|---|
| 1 | "pipeline date is super old / data outdated" | **Half right** — see below | latest bhavcopy = 2026-08-28 |
| 2 | "nothing from the reverse-engineered breadth Excel" | **CORRECT** | `features/breadth.py` exists, **zero production callers** |
| 3 | "no Reactor Scale section" | **Right in the UI, wrong in the backend** | computed at `scan.py:373`, emitted at `report_json.py:65`, but not rendered as its own surface |
| 4 | "Stock and History screens are blank" | **CORRECT — worse than blank** | Stock dead-ends; History **crashes** |
| 5 | "nothing integrated from BananaPatterns" | **Partly wrong** | `base_episode` wired in `scan.py:24,100`; `detectorTrust` renders in `CandidateCard.tsx:29`; `base_episodes` in `tonight.ts:88` |
| 6 | "all filler data should be removed now it's live" | **Needs an owner decision** — see §5 | `fixtures.ts:223` merges real + illustrative |
| 7 | "no AI-based intelligence we discussed" | **Correct by the owner's own locked sequencing** — see §4 | Phase 0 spec §0 |

### 3.1 On data freshness (complaint 1)

The data is **not** stale in trading terms. Today is Mon 2026-08-31. Latest
session in the archive is **Fri 2026-08-28** — 29th and 30th were the weekend,
and today's bhavcopy does not exist until after today's close. 2026-08-28 is
correctly the most recent completed session.

**But two real problems make it feel stale, and one is serious:**

- **There is no downloader.** `grep -rln "requests.get|urlopen|nseindia" unidesk/`
  matches only a test file. Nothing in the pipeline can fetch a new bhavcopy.
  Every session must be added manually. Phase 0 spec §27 specifies a full EOD
  polling workflow with a retry policy and an availability ledger (§26) — none
  of it exists. **This is the single biggest gap between the spec and the build.**
- **The UI is hard-pinned to one file.** `tonight.ts:22,25` imports
  `tonight_2026-08-28.json` as a build-time constant. A new report requires a
  code edit and a rebuild. There is no report picker.

So: "the EOD pipeline is supposed to be up to date at least" — correct, and it
cannot be, because the ingest half of it was never built.

### 3.2 Stock and History (complaint 4)

**Stock** — `/#/stock/ATHERENERG` renders "No symbol selected." `Stock.tsx:22`
looks the symbol up only in `ALL_CANDIDATES` (the 6-symbol fixture set,
`fixtures.ts:223`). Tonight and Candidates show **268 real candidates**, every
card linking to `/stock/:symbol`. So the scan→judge workflow dead-ends at the
second click for ~97% of content, from all three entry points
(`CandidateCard.tsx:37`, `CandidateScatter.tsx:69`, `History.tsx:94`).

**History** — not blank, **hard-crashes**. Console:
```
TypeError: Cannot read properties of null (reading 'toFixed')
```
Cause: `History.tsx:103,106` call `c.mfePct.toFixed(1)` / `c.maePct.toFixed(1)`
unguarded, and `outcomes.ts:35,36` type them as non-nullable `number`. But
UNRESOLVED events carry no MFE/MAE — and CA55 raised UNRESOLVED sharply
(`unconfirmed_corporate_action` = 3001). `netBps` **is** correctly guarded
(`History.tsx:32-36`), so the pattern was understood; it just wasn't applied to
these two fields. React unmounts the tree → black screen.

This is the clean causal link between §1/§2 and the UI: **a data-layer null
became a crashed screen because one field was typed as always-present.**

---

## 4. On "no AI intelligence" — this one is correct by design, and worth re-reading

The owner's own constitution forbids it at this stage. Directly:

> **"Phase 0 contains no predictive AI."** — Phase 0 spec §0
> Explicitly not included: *T1 signals, T5 signals, L1.5 analogue retrieval,
> neural encoders, intraday EP models* — Phase 0 spec §1.2

And the mandated order (Constitution §1, §7):
```
L0 raw rule → L1 engineered score → L1.5 engineered-state analogue retrieval
→ L2 supervised learned representation → L3 learned analogues → L5 execution
```
with **L1.5 (retrieval on hand-crafted features only) mandatory before any
neural net** — its entire purpose is to separate "retrieval helps" from
"learned representation helps" (§7). And: *"No learned model should be trained
before this gate"* (§54).

So the absence of the AI layer is **not drift — it is the plan being followed.**

The honest problem is different, and it is worth stating plainly: **Phase 0 is
not close to its own Definition of Done, so the AI gate cannot open.** Against
spec §53's checklist, the large gaps are:

- history target is 2016-01-01 (§2.1); the archive starts **2025-03-19** — about 1.4 years
- no immutable raw archive, no SHA256 source manifest, no build manifest (§30, §31)
- no availability ledger (§26) — so decision-time safety for delivery is asserted, not proven
- no PIT index membership → R0 breadth cannot use PIT Nifty 500 (§17.2 says this must
  set `r0_status = BLOCKED_MEMBERSHIP`; the app instead shows "Regime not built yet",
  which is honest but is not the specified status field)
- no `make rebuild` determinism check (§2.2)
- security identity is symbol-keyed, not `security_id`/ISIN + `continuity_id` (§8)

That is the real answer to "where is the AI": it is four work-packages away, and
the gap is data infrastructure, not modelling.

---

## 5. On removing filler data (complaint 6) — recommend NOT a blanket removal

The `dataSource: "real_scan" | "real_scan_raw" | "illustrative"` convention
(`fixtures.ts:65`) is one of the genuinely good things in this codebase, and the
live UI honours it well — I saw "ILLUSTRATIVE PREVIEW — NOT THE REAL CLASSIFIER",
"RAW SCAN SIGNALS — NO QUALITY SCORE COMPUTED", "Trigger / invalidation not
computed — raw scan only", and "REAL SCAN · 291 SESSIONS" all rendering correctly.

Deleting fixtures wholesale would **blank several screens** rather than make them
honest, because their backends genuinely don't exist yet (per the integration
plan's cadence table). Better rule:

> Fixtures may remain **only** where the screen has no real backend and the
> illustrative tag is rendered at the point of use. Anywhere a real backend
> exists, the fixture must not be merged into the same list as real rows.

Concretely: `ALL_CANDIDATES = [...CANDIDATES, ...CANDIDATES_ILLUSTRATIVE]`
(`fixtures.ts:223`) merges the two into one array. That is the pattern to remove.
Keep the illustrative records; stop blending them into a real collection.

Also: `Settings.tsx:51-59` still shows the stale 2026-07-03 fixture session
unlabelled while the rest of the app is on 2026-08-28 real data. That one is a
straight bug — fix it.

---

## 6. Deterministic-formula audit — code correctness

Read in full: `adr_atr.py`, `rs.py`, `labels.py`, `walkforward.py`,
`candidates.py`, `leakage.py`, `market_store.py`, `corp_actions.py`, `splits.py`.

**Correct, no action:**
- `adr()` uses an exclusive prior window (`adr_atr.py:39`) — current session never
  in its own baseline. No lookahead.
- `atr()` Wilder seeding at index `span`, correct smoothing (`adr_atr.py:60-74`).
- `InMemoryMarketStore.get_market_state` filters on both session date **and**
  `available_at <= as_of` (`market_store.py:126-152`) — real point-in-time
  semantics, 9 passing tests including future-row invisibility.
- Gap-through fill now uses `min(gap_open, stop)` and persists
  `exit_price`/`gap_through` (`labels.py`). Verified against the archive: zero
  `stop_hit=True` rows with positive `r_multiple`.

**Defects found:**

1. **`rs.py:113` — walrus truthiness bug.**
   ```python
   if sector_return_mean := _mean(sector_returns):
   ```
   A legitimate sector mean of exactly `0.0` is falsy → takes the `else` branch,
   reports `NO_SECTOR_RETURNS`, and leaves `rs_sector`/`sector_vs_market` as
   `None` **even though the returns exist**. Same bug class as the one fixed in
   `844b3ba8`. Fix: `if (m := _mean(...)) is not None:`.
   *Note: `rs_snapshot` has no production caller today — it is used by tests only.
   Fix it before wiring it, not after.*

2. **`research/archive_attach.py` does not apply universe gates** — see §2.
   ETFs and sub-floor names are in the research archive. Phase 0 spec §18.2.

3. **`test_truncation_invariance.py::test_every_enumerated_callable_is_registered`
   is FAILING** — 6 new public callables have no REGISTRY classification:
   ```
   features.activity.activity_score
   features.breadth.{bo_bd_ratio, net_nh_nl, up_down_close_pct,
                     volatility_ratio, volume_ratio}
   ```
   This test exists to stop exactly this drift. Each needs `kind='series'` (with a
   truncation check), `'special'`, or `'skip'` with a written reason. **Do not
   silence it by deleting the assertion.**

4. **`walkforward.py:173`** — a bare string sits after an `if` block where a
   docstring was intended; it is dead code. Cosmetic, but it means
   `simulate_long.__doc__` is not what the author thought.

---

## 7. Recommended order of work

Ranked by "what unblocks the most, and what prevents believing a false number."

1. **Resolve §1 (CA ratios).** Owner decision. Everything downstream is
   uninterpretable until this is settled. Recommend option (b) quarantine, or (c)
   if willing to verify 51 tickers.
2. **Gate the research archive** with `universe/gates.py` (§2/§6.2), then
   regenerate. Removes the ±1000R ETF garbage.
3. **Re-run the archive audit from disk** and only then quote any number.
4. **Fix the History crash** — guard `mfePct`/`maePct` at `History.tsx:103,106`
   and make them `number | null` in `outcomes.ts:35,36`. One-line class of fix,
   restores a whole screen.
5. **Fix the Stock dead-end** — `Stock.tsx:22` should also search the real
   candidate set, and render a raw-stats panel for unscored real candidates
   rather than `DecisionCard`'s zero-defaulted Quality Stack (which would
   otherwise display a false "scored 0").
6. **Fix `rs.py:113`** and **classify the 6 unregistered callables**.
7. **Wire `features/breadth.py`** into the nightly pipeline and surface it —
   this is the owner's reverse-engineered Market Breadth work, currently built
   and unused. Source doc: `manas_os/design/knowledge/MARKET_BREADTH_V2_REVERSE.md`.
8. **Surface Reactor Scale** in the UI. Backend already emits `activity_score`;
   it needs a rendering surface. **Carry its caveat verbatim** — the owner's own
   note in `traderlog/adopted/activity.py`: it *"must never be presented as
   institutional identity, trade direction, or a risk input."*
9. **Build the downloader + availability ledger** (Phase 0 spec §26, §27). Until
   this exists the desk cannot be current, and delivery-timing safety is an
   assertion rather than a measurement.
10. **Then, and only then**, reassess the Phase 0 checklist (§53) and whether the
    L1.5 gate can open.

**Do not run the N5 experiment** until items 1–3 are done. Running it now produces
a number that looks like an edge and is built on inferred corporate actions and
ETF outliers.

---

## 8. Session provenance

Commits landed by this session before the audit:
`bd6aae14` (quality/regime + universe gates wired into scan), `40054196`
(`TrendState.UNKNOWN` crash fix), `078c6f3f` (gap-aware + net-of-cost labels,
`simulate_long` NameError fix), `eb5c1c64` (CA review-queue artifact — note: this
produced the queue the auto-confirmer then consumed, see §1), `c1770539`
(same-symbol embargo control).

Uncommitted at handoff time: `unidesk/run_stock_history_export.py`,
`unidesk_terminal/src/data/stock_history_2026-08-28.json`,
`unidesk_terminal/src/data/stockHistory.ts` — a real-OHLCV export for the Stock
chart (235/235 symbols, 29,979 real bars, replaces the synthetic
`lib/ohlc.ts:generateOhlc`). Backend done, frontend wiring not started; this is
the natural companion to fix #5 above.

Full UX detail: `unidesk/design/UX_AUDIT_2026-08-31.md`.
Attribution-ID: attr-unidesk-audit-fixes-cline-20260831-001
