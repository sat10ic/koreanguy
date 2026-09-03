# Rendered element sweep — every screen, every panel (2026-09-02)

**Auditor:** Claude Opus 5 (audit role only — no code changed by this pass).
**Method:** app run live at `http://localhost:5183` (Vite dev, `unidesk-terminal`),
every screen opened and read, then **every displayed number cross-checked against
`data/market/reports/tonight_2026-09-01.json` and
`unidesk_terminal/src/data/outcomes_2026-09-01.json` by direct computation**.
This is not a code read — findings below are what the app actually put on screen.

**Repo state at audit:** commit `ba73462c`, branch `emergent`, working tree clean.
**Report under test:** session `2026-09-01`, 1,163 scanned, 88 candidates,
`actions_applied: 4`, `adjustment_status: confirmed_ca_applied`.

> **STATUS UPDATE 2026-09-03 23:19 — two findings below are ALREADY FIXED.**
> While this audit was being written, another session landed both:
>
> - **S1-7** (`test_truncation_invariance`) — `adr_max` and `chop_score` are now
>   registered `kind='series'` with real truncation checks; `chop_band` and
>   `stop_in_thrust_days` registered as skip with written reasons. Exactly as
>   B2-1 specified.
> - **B2-4** (fail-fast refresh) — `run_desk_refresh.py` now aborts on the first
>   failed step, asserts the session advanced (`--allow-no-new-session` to
>   override a holiday), and runs `run_published_invariants.py` +
>   `run_export_desk_checks.py` as steps. The `DONE` line no longer prints after
>   a failure, which closes the silent stale-data path in §A and §B.
>
> Everything else here was verified against the working tree at the time of
> writing and has **not** been re-checked since. **Re-verify any single finding
> before acting on it** — several agents work this repo in parallel and an audit
> ages within hours. That decay is itself finding S2-8 below.

Severity: **S1** = shows wrong or missing data to the trader · **S2** = misleading
presentation of correct data · **S3** = cosmetic / hygiene.

---

## Verdict up front

The **honesty layer is genuinely good**. Every breadth, funnel and participation
figure I recomputed matched to the decimal, nulls render as `—` rather than zero,
and denominators are disclosed. That work is real and should not be undone.

The failures are of a different kind: **two screens silently drop data, one panel
is frozen 103 days in the past, and three pairs of screens contradict each other
about the same session.** A trader reading this desk today would be misled on
four counts, none of which is visible as an error.

---

## S1-1 · Momentum Burst candidates are invisible on Tonight

`lib/candidates.ts:9-12` declares:

```ts
const SETUP_ORDER: SetupType[] = [
  "base_breakout", "episodic_pivot", "inside_bar", "ipo_base",
  "power_play", "pullback", "reversal_reclaim",
];
```

`momentum_burst` is **not in the list**. `groupBySetup` (`lib/candidates.ts:127-136`)
does `if (!groups.has(key)) continue;` — so those candidates are dropped on the
floor with no warning.

Measured on the live app:

| Section rendered on Tonight | Count |
|---|---|
| BASE BREAKOUT | 0 |
| EPISODIC PIVOT | 1 |
| INSIDE BAR | 68 |
| IPO BASE | 7 |
| POWER PLAY | 0 |
| PULLBACK | 7 |
| REVERSAL / RECLAIM | 3 |
| **Sum rendered** | **86** |
| **Header above it says** | **"88 candidates"** |

The 2 missing rows are the `momentum_burst` candidates. They are real — the
report carries them, the **Candidates** screen table shows all 88 including them,
the **Market** sector table sums to 88 including them, and Research's archive
shows `momentum_burst` with 15 historical hits. Only Tonight, the screen the
owner opens first, hides them.

Two dead sections (BASE BREAKOUT 0, POWER PLAY 0) are rendered in their place.

## S1-2 · "Prior calls" is frozen on 2026-05-21 — 103 days stale

Tonight's Prior-calls panel displays session **2026-05-21** (12 won / 10 stopped /
2 flat, avg +1.36R, n=24) on a desk whose header reads **2026-09-01**.

Root cause, `Tonight.tsx:462`, whose own comment states it:

> `// Newest session where EVERY call has finished its horizon.`

The outcomes archive carries calls through **2026-08-27**, but **238 rows are
permanently `unresolved`**, concentrated in six symbols that recur in almost
every session:

| Symbol | Unresolved rows |
|---|---|
| BODALCHEM | 61 |
| QUICKHEAL | 59 |
| BLISSGVS | 38 |
| PPAP | 31 |
| SHALPAINTS | 15 |
| UFBL | 12 |

These rows carry `entry: null` — no entry price was ever derived, so they can
**never** resolve. Because every recent session contains ~7 of them, the
"every call finished" test can never again pass, and the panel will drift further
into the past every single day.

The subtitle is also factually wrong. It reads *"newest session whose full 10-bar
horizon has elapsed"* (`Tonight.tsx:186`) — but the gate is not horizon-elapsed,
it is zero-unresolved. 2026-08-14's horizon **has** elapsed and it is still
excluded.

## S1-3 · History's "Latest" view cannot show a win, by construction

History → Latest displays:

```
129 calls in range · 0 won · 11 stopped · 0 flat · 104 still open · 14 no data
Hit rate 0%   Avg -1.00R   Best -1.0R   Worst -1.0R
```

`History.tsx:61` defines "latest" as the **last 7 days**. A win requires the full
10-bar horizon; a stop-out resolves the moment price touches the stop. So in any
7-day window, **only losses can have resolved**. The hit rate is guaranteed to be
0% and the average R guaranteed to be −1.00R regardless of how the strategy is
actually performing.

`Best -1.0R` and `Worst -1.0R` being identical is the visible tell.

This is right-censoring presented as performance. The footnote explains the
arithmetic (`0 + 11 + 0 + 104 + 14 = 129`) but never says the window is
structurally incapable of containing a winner. A trader glancing at this
concludes the system is losing on every trade.

## S1-4 · Same symbol, two screens, opposite verdicts

KINGFA, session 2026-09-01, both screens open at once:

| Screen | What it says |
|---|---|
| **Candidates** ranked table | Rank **02**, state **PRIME** |
| **Stock** page verdict | **"POOR RISK — Reward does not cover risk at these levels"** |

Both are reading the same candidate. Its `R:R` is **0.3R** and its stop sits
**0.37 thrust-days** away. The Stock page is right; the ranking is wrong.

This is not isolated. From the live ranked table, top-16 rows labelled **PRIME**:

| Rank | Symbol | R:R | STOP/TH |
|---|---|---|---|
| 01 | TBZ | **—** (none) | 1.26 |
| 02 | KINGFA | 0.3R | 0.37 |
| 04 | QPOWER | 0.3R | — |
| 09 | BEML | 0.6R | 0.43 |
| 16 | ACMESOLAR | 0.3R | — |

**Rank 01 has no R:R at all** and is still PRIME. `deriveState` is not consulting
reward geometry, so the top of the list is systematically populated by setups
whose reward is a fraction of their risk.

KINGFA's own "Past signals" panel, on the same page, lists it stopped out on
2026-08-18, 08-17, 06-05, 06-04, 06-03, 06-02 and 04-22. That history is
displayed but feeds nothing.

## S1-5 · Settings contradicts the report on corporate actions

`Settings.tsx:65` renders a hardcoded sentence:

> "Source: NSE bhavcopy (EQ series). **Corporate-action adjustment pass still
> open (N3).**"

The report it is displaying says `adjustment_status: confirmed_ca_applied`,
`actions_applied: 4`. The CA pass is closed on the verified 4-action table —
that was the acceptance test the previous plan set, and it passes. Settings
tells the owner the opposite. This is the same class of defect as the old
`SESSION` fixture (G-01), reappearing as prose instead of a number.

## S1-9 · The desk cannot say why a symbol is absent, and guesses wrong when asked

Prompted by the owner asking why MILKYMIST was in no setup. Reconstructing the
answer took raw-bhavcopy forensics; **the product could not answer it, and the
one tool built for the question gives a misleading reply.**

**The facts, from `sec_bhavdata_full_01092026.csv`:**

```
MILKYMIST  EQ  2026-09-01
prev 210.94  open 230.79  high 232.03  low 221.92  last 232.03  close 232.03
+10.00%  ·  turnover Rs 543.2 cr  ·  23.9M shares  ·  139,316 trades  ·  27% delivery
```

`high == last == close == 232.03`, exactly +10.00% off prev close — **locked at
the upper circuit**. First EQ print **2026-08-18**: only **11 sessions** of
history.

**Two independent exclusions, in this order** (`scan.py:351` runs before `:353`):

1. **Universe gates run first.** Circuit-locked → `universe_gate_circuit_locked`
   (`scan.py:196-197`), the bucket of 5 on this session. It passes the other
   gates comfortably: `MIN_PRICE = 30.0` (close ₹232), `MIN_AVG_TURNOVER_CR = 2.0`
   (₹543 cr), not an ETF.
2. **History minimum, only reached if gates pass.** `MIN_SESSIONS_DEFAULT = 61`
   (`scan.py:43`) vs 11 available → `insufficient_sessions`. This is the
   *durable* reason: it fires on every session until roughly 2026-11-14.

**Three defects this exposes:**

**(a) Per-symbol refusal reasons are never recorded.** The report carries only
aggregate buckets — `turnover_floor: 845`, `price_floor: 444`, `probable_etf: 59`,
`circuit_locked: 5`, plus 77 `insufficient_sessions`. `gate_skip_bucket` is
computed per symbol at `scan.py:281` and then **discarded**; only the counts are
emitted. The information exists in memory and is thrown away.

**(b) The veto tool answers wrongly.** `lib/veto.ts:31-32` returns one canned
string for every absent symbol: *"not in tonight's scanned universe (filtered by
universe gates: price floor, turnover floor, …)"*. For MILKYMIST it names the two
gates the stock passes by a wide margin, and never mentions circuit lock or
history depth — the two that actually excluded it. That is worse than "unknown":
a confident wrong answer to the exact question the panel exists to answer.

**(c) `ipo_base` cannot see IPOs.** A 61-session floor excludes anything under
roughly three months. Tonight's 7 `ipo_base` candidates are all older than that.
A genuinely fresh listing breaking out — the setup that detector is named for —
is invisible by construction. ADRMAX compounds it at 250 sessions, so even a
newly-eligible name shows "not enough history" for its thrust metrics.

Whether 61 is the right floor is a legitimate judgment call — ADR, RS and base
structure all need history, and a three-week-old listing has no meaningful base.
The defect is not the threshold; it is that the exclusion is **silent**. The desk
should be able to say *"MILKYMIST: 11 of 61 sessions, eligible ~2026-11-14; also
circuit-locked on this session"* instead of showing nothing and, when asked,
blaming the wrong gate.

## S2-1 · Detector count is stated three different ways

| Surface | Says |
|---|---|
| Tonight setup-feed subtitle (`Tonight.tsx:163`) | "**seven** detectors" (hardcoded literal) |
| Settings detector-trust card (`Settings.tsx:105`) | "6 of **8** detectors not rankable" |
| The report actually emits | **6** detectors with candidates |
| `SETUP_ORDER` renders | **7** sections (2 of them empty) |

No single number is right on all three screens.

## S2-2 · The prior-session comparison is ~99% empty but presented as a feature

Trigger Proximity is captioned *"distance now vs prior session"*. In practice
almost every row renders `— → +1.2%`: the prior value is absent. Of the 16 rows
visible across all four groups, exactly **one** (DECNGOLD, `+12.3% → +13.5%
fading`) has a prior distance. The panel promises drift and delivers a single
data point.

## S2-3 · Every candidate carries a low-coverage warning

Every row in the ranked table's QUALITY column shows `⚠` — 88 of 88. A warning
that fires on 100% of rows is not a warning; it is a background texture the eye
stops seeing. Either the coverage threshold is wrong or the underlying coverage
gap is systemic and should be stated once at panel level, not 88 times.

## S2-4 · Research shows three different totals for the same archive

Within one viewport:

- Archive coverage card: **7,850** sampled outcomes · 7,760 resolved
- Equity-curve caption: **8,843** resolved calls
- Same caption, parenthetical: **9,081** rows

Three denominators, no explanation of how they differ. Also `Label version:
**MIXED**` here, while History states a single version (`outcome-labels-v4-net-cost`)
as though the archive were uniform.

## S2-5 · setup_quality is still a constant

Stock page for KINGFA: `SETUP 100`. The Candidates landscape had to abandon
`Setup × Entry` as its default axis precisely because this value is ~100 for
every candidate. It is a rule-completion flag being displayed as a 0–100 score,
and it still reads "Excellent" in the Beginner verdict panel.

## S3-1 · Unbalanced parenthesis in the Beginner regime gloss

Tonight's hero renders `CHOP (breadth 50.0% above EMA50` — the gloss truncates
the verbatim `regime_note` at `breadth_only` and leaves the opening bracket
unclosed.

## S3-2 · Dead code and unreachable affordances

- `components/shell/LeftRail.tsx` (58 lines) — a second nav rail, imported by
  nothing, with a **different** nav list than the live `Sidebar.tsx`.
- `Chip.tsx:29-34` — an `animate-ping` pulse variant never passed `pulse={true}`
  anywhere. Looks like a live indicator; unreachable.
- `ScrollRail.tsx:27` — applies class `scroll-fade-x`, which **is not defined in
  any CSS file**. The scroll affordance is a no-op.
- `index.css:156-157` — `--dur-hover` / `--dur-panel` tokens with zero usages.
- `TopBar.tsx` — search input and alerts bell, neither with a handler.
- `data/tonight.ts:16` — `TONIGHT_JSON_FILENAME = "tonight_2026-08-31.json"`,
  with a comment calling it "the newest". `2026-09-01` is newer and is bundled.

## S3-3 · Latent wrong-file selection

`settings.ts:45` and `researchCoverage.ts:29` take `Object.values(modules)[0]`
with **no sort**, while `reportRegistry.ts:21`, `outcomes.ts` and
`stockHistory.ts` all sort by session date descending. Harmless today (one dated
file each); picks an arbitrary file the moment a second lands.

---

## What I checked and found correct

Stated explicitly so the next reader does not re-audit it:

| Panel | Displayed | Ground truth | ✓ |
|---|---|---|---|
| Above EMA21 | 42.2% | 491 / 1,163 = 42.22% | ✓ |
| Above EMA50 | 50.0% | `pct_above_ema50: 50.0` | ✓ |
| Near 52W high | 8.5% | 99 / 1,163 = 8.51% | ✓ |
| Near 52W low | 5.7% | 66 / 1,163 = 5.68% | ✓ |
| New highs vs lows | 0.172 | `net_nh_nl: 0.17196…` | ✓ |
| Stocks closing up | 47.6% | `up_down_close_pct: 47.588…` | ✓ |
| Volume vs normal | 0.44 | `volume_ratio: 0.4375` | ✓ |
| Volatility vs normal | 0.85 | `volatility_ratio: 0.84796…` | ✓ |
| Breakouts vs breakdowns | `—` | `bo_bd_ratio: null` | ✓ (correctly not 0) |
| Opportunity funnel | 2,593 → 1,163 → 88 → 64 → 60 | 1,163 + 1,353 gated + 77 skipped = 2,593; nests monotonically | ✓ |
| Data-quality strip | 1,163 scanned · 77 skipped · 1,353 gated · 131 stale | exact match | ✓ |
| Market sector table | sums to 88 | 88 candidates | ✓ |
| Settings session block | 2026-09-01 · 1,163 · 50.0% | exact match | ✓ |
| Trigger proximity | 27 + 48 + 0 + 13 = 88 tracked | 88 candidates | ✓ |
| Candidates landscape | percentile axes, all four quadrants populated | — | ✓ |

Build is clean (`tsc -b && vite build`, zero TS errors). No console errors on any
screen. No fabricated rows found anywhere.

---

## Thrust-metric coverage (context for the UI work)

Measured across all 88 candidates:

| Field | Coverage | Distribution |
|---|---|---|
| `chop_band` | 88/88 | CLEAN 18 · MODERATE 22 · MESSY 32 · VERY_CHOPPY 16 |
| `adr_max_pct` | 57/88 | 31 names under 250 sessions → `null` by design (`thrust.py:114-115`) |
| `stop_thrust_days` | 57/88 | min 0.32 · p25 0.49 · **median 0.67** · p75 0.87 · max 1.64 |

**37 of 57 (65%) have a stop inside 0.75 thrust-days.** Exactly one candidate of
88 clears 1.5. The stop is routinely tighter than the stock's own ordinary strong
day — the position is closed by normal movement before the idea is tested. This
is the mechanism behind S1-4, and behind the owner's standing question about
high scores producing poor R:R.

**Do not re-band these thresholds to make the UI look balanced.** The flat red is
the true reading. The correction belongs in the geometry rule that sets
`invalidation`, not in the display.

---

---

# Backend sweep — pipeline, archive, tests

Added after the rendered pass. **Every claim below was re-verified by me
directly** (a delegated agent surfaced them; I reproduced each one before
recording it, and one of my own first attempts was wrong — noted where relevant).

## S1-6 · A quarter of the research archive is on a rejected corporate-action basis

Tallying `ca_table_hash` out of `snapshot_json` across **all 1,570** parquet
partitions in `data/market/research/events/`:

| `ca_table_hash` | Partitions | What it is |
|---|---|---|
| `d1b585eb60fd4f82` | **1,177** | current verified 4-action table |
| `b3b43b561621b11f` | **200** | older pre-audit basis |
| `191ac96a61cdfae7` | **193** | **the explicitly rejected 55-action table** |

**393 of 1,570 (25%) are on a stale or rejected basis.**

`sessions_needing_label_refresh(Path("data/market"))` returns **397** stale
sessions — 393 for the wrong CA hash, ~4 recent ones merely awaiting labels.

This **qualifies the good news in §G**. Front-of-book is genuinely clean:
`tonight_2026-09-01.json` reads `actions_applied: 4`, and the newest partition
carries the current hash. But **History and Research compute over the whole
archive**, so every statistic on those two screens — the cumulative-R curve, the
setup scorecard, the 9,081-call totals — is computed across a mixture of three
different corporate-action bases. That is a second, independent reason to
distrust those numbers, on top of the censoring artifact in S1-3.

The detector itself is now honest — the B-05 fix at `archive_attach.py:136-138`
does compare the hash, and it correctly reports the drift. Nobody has run the
remediation.

*Correction to my own working note:* my first call of that function returned
`0` and I briefly took the agent's `397` to be wrong. My call was wrong — the
function takes `data_root` and appends `research/events` itself (line 129), so I
had passed a doubled path. The 397 is correct.

## S1-7 · Point-in-time correctness of the thrust fields is unverified — including mine

`unidesk/tests/test_truncation_invariance.py::test_every_enumerated_callable_is_registered`
**fails**. Verbatim:

```
New public callable(s) found with no REGISTRY entry:
    unidesk.momentum.features.thrust.adr_max
    unidesk.momentum.features.thrust.chop_band
    unidesk.momentum.features.thrust.chop_score
    unidesk.momentum.features.thrust.stop_in_thrust_days
    unidesk.momentum.scoring.setup_quality.setup_quality_snapshot
```

That test auto-enumerates every public callable under `features/`,
`primitives/` and `scoring/` and fails loudly when one is unclassified, so it
"can never silently pass uncovered". Five functions are unclassified.

**Four of the five are mine** — the thrust wave shipped `adr_max`, `chop_score`,
`chop_band` and `stop_in_thrust_days` into every candidate row of every report
without registering them for truncation-invariance. They have their own unit
tests (`test_thrust.py`, 15 passing, including no-lookahead cases), but they are
**not covered by the repo's own point-in-time guard**, which is the check that
matters for a research archive. I introduced that gap and did not notice it.

The fifth, `setup_quality_snapshot`, is the constant-100 function from S2-5.

## S1-8 · The CA detector flags a clean stock, silently dropping it from research

`unidesk/tests/test_archive_attach.py::test_plain_symbol_no_ca_history_resolves_with_no_op_basis`
**fails**: `assert 'TCS' not in real_ca_backlog` — TCS *is* in the
unconfirmed-corporate-action backlog, despite having no confirmed action.

The bar-shape heuristic behind `run_ca_review_queue.py` is false-positiving on a
large, liquid, action-free name. Symbols caught this way get labelled
`UNRESOLVED` / `unconfirmed_corporate_action` and are dropped from outcome
labelling — **silently degrading research coverage with no error surfaced**.
This is plausibly one source of the permanently-unresolved rows in S1-2.

Full suite: **370 passed · 2 failed · 31 skipped** (16m38s). Both failures are
the two above; neither is cosmetic.

## S2-6 · A docstring claims wiring that does not exist

`unidesk/run_published_invariants.py:1-4` states:

> "…**Called by `run_desk_refresh.py`** so the desk verifies itself on every
> refresh — no agent in the loop."

Grepping `run_desk_refresh.py` for `published_invariants|run_checks|export_desk_checks|archive_attach`
returns **no matches**. The claim is false. This is the mechanism behind §B: the
UI's "Desk self-checks — n/n passing" panel is fed by an exporter nothing calls,
and the docstring is what stops the next reader from noticing.

Practical consequence: the full chain from raw data to a self-verified UI is
**at least three separate manual invocations** (`run_desk_refresh.py`, then
`run_published_invariants.py` + desk-checks export, then periodically
`run_archive_attach_resume.py`), and that order is documented nowhere. There is
no scheduler — the desk goes stale unless the owner remembers.

## S2-7 · `showing_synthetic_data` is hardcoded true

`unidesk/checks/runner.py:517` stamps `"showing_synthetic_data": true` into
`STATE.json` on every run regardless of what actually ran. The preservation
manifest records a prior session hand-correcting this to `false`; the runner
overwrites it again on the next invocation. A flag that is always true carries
no information — and it currently asserts the opposite of the truth, since the
UI carries no synthetic data.

## S3-4 · The live downloader depends on a third-party mirror

The earlier audit conclusion that **no downloader exists is refuted** — there are
two:

- `bhavcopy_extractor/download_bhavcopy.py` — **the one actually wired in**
  (`run_desk_refresh.py:71-72`). Pulls from third-party GitHub mirrors
  (`tilak999/NSE-Data-bank`, `girishg4t/bhavCopy-downloader`).
- `unidesk/fetch_nse_bhavcopy.py` — hits **official** `archives.nseindia.com`,
  and is **orphaned**: referenced only in `MODEL_WORK_LOG.jsonl`, invoked by no
  driver.

So the nightly's data supply depends on unofficial mirrors staying current while
the official-source fetcher sits unused. Not urgent, but it is a single point of
failure outside the owner's control.

## Confirmed fixed (do not re-open)

- **Liveness gate wall-clock bug** — `momentum/scan.py:288-314` now compares
  against `market_session` (max last-bar session actually present), not
  `as_of.date()`. Fixed, with the old bug documented in-comment.
- **`sessions_needing_label_refresh` false all-clear** — `archive_attach.py:136-138`
  now compares `label_version` **and** `ca_table_hash`. Fixed; see S1-6 for the
  unremediated data it now correctly detects.

## Freshness, stated plainly

| Layer | Newest |
|---|---|
| Raw bhavcopy (`data/bhavcopy/`) | 2026-09-01 |
| Archive event partitions | 2026-09-01 |
| `data/market/reports/tonight_*.json` | 2026-09-01 |
| UI-bundled reports | 2026-08-31 and 2026-09-01 |

All layers agree at one session behind today — the expected EOD lag, not a bug.
**The freshness problem in this desk is not the front of the pipeline.** It is
the frozen prior-calls panel (S1-2), the 25% archive (S1-6), and the
self-check panel that can vouch for data it never saw (§B).

## S2-8 · Why ~11 audits keep finding new issues (the meta-finding)

The owner's question, answered with evidence rather than theory. This is the
highest-leverage item in this document.

**Measured:** 11 audit/review documents under `unidesk/design/`, and **48
handoffs marked `COMPLETED`**. New S1s are still being found in every pass.

Six mechanisms, all verifiable:

1. **Audits emit prose; only code prevents regression.** The findings that stuck
   are the ones that became `checks/published_invariants.py`. Everything that
   stayed markdown gets re-found. *This document is prose.*

2. **There is no CI — no `.github` directory exists.** Nothing runs `pytest` or
   `run_checks.py` on change. `test_truncation_invariance` was purpose-built to
   fail when a public callable ships without point-in-time coverage. It caught
   the thrust wave's omission **three days late**, and only because an agent ran
   the suite by hand. The guard worked perfectly and was wired to nothing.

3. **Parallel agents, no lock.** Several models work this repo concurrently.
   `PRESERVATION_MANIFEST_CLAUDE_THRUST_2026-09-02.md` exists precisely because
   one session nearly overwrote another's. **Live proof: two S1 findings in this
   very document were fixed at 23:19 on 2026-09-03, while the document was being
   written.** Every audit describes a target that has already moved.

4. **Fixes are instance-level, never class-level.** G-01 deleted the `SESSION`
   fixture (a hardcoded value contradicting the report); S1-5 above is the same
   class reappearing as prose at `Settings.tsx:65`. `Object.values(...)[0]`
   without a sort is correct in three modules and wrong in two (S3-3). Nobody
   wrote the check that makes the class impossible, so the class keeps emitting
   instances.

5. **48 `COMPLETED` handoffs, no decay-tracked ledger.** Completion is asserted
   once per wave and never re-verified. Audit N+1 re-discovers what audit N
   certified, because nothing records that a certification expires when the code
   underneath it changes.

6. **Each audit uses a different lens and no lens is retained.** Panel-by-panel
   UX (GLM, 09-02), rendered-value-vs-ground-truth (this one), metrics/currency
   (09-01). Each lens finds what the others structurally cannot — which is why
   the findings are *new* rather than repeats. That part is healthy. The failure
   is that no lens is ever re-run after a later wave changes the code.

**Root cause in one line:** the product is being built faster than its guardrails
are being wired, and audit output is prose while only code prevents regression.

**What ends it — two of the three already exist and are simply unconnected:**

| Fix | Status |
|---|---|
| CI running `pytest` + `run_checks.py` on every change | **does not exist** — no `.github` |
| Published invariants inside the nightly chain | **exists**; wired into `run_desk_refresh.py` on 2026-09-03 |
| Findings ledger where each entry is a test, not a paragraph | does not exist |

Until the first and third land, expect audit #12 to find new S1s — and expect
this document to be stale within days.

## Not covered by this sweep

- Desk screen's broker-import panels were read but not reconciled against the
  source CSV.
- Market's breadth-history chart shows 43 sessions with a last tick of `08-28`;
  whether the series actually includes 08-31 and 09-01 was **not** verified.
- The 1D/5D participation deltas were read but not recomputed from the archive.
- Pro mode was not swept panel-by-panel; the Stock thrust panel is Pro-only and
  was therefore not seen rendered in this pass.
- `run_checks.py` was **not executed** — `checks/runner.py:493-519` writes
  `STATE.json` unconditionally, so running it would have mutated the repo during
  a read-only audit. Its 14 checks were enumerated from source instead:
  `attribution`, `orderflow_ledger`, `contracts`, `data_authority`, `leakage`,
  `inv:outcome_labels`, `inv:funnel_nested`, `inv:prices_match_source`,
  `inv:no_hardcoded_market_values`, `inv:ranked_symbols_traded`,
  `inv:scores_have_variance`, `inv:no_fabricated_rows`, `stale_state` (stub),
  `provenance` (stub).
- Whether the 393 wrong-basis partitions actually change any published outcome
  statistic was not quantified — only that they are on a different basis.
