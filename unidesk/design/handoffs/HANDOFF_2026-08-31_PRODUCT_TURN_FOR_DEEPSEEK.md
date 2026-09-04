# HANDOFF — product turn + repo harvest — 2026-08-31 (second handoff of the day)

Author: Claude (Opus 5), session `koreanguy-fb`. Supersedes nothing in
`HANDOFF_AUDIT_2026-08-31_FOR_DEEPSEEK.md` — read that one first for the
corporate-action story; this one covers what changed after it, plus a
re-prioritisation the owner explicitly asked for.

**No code was written in this session.** One subagent was launched to start
Stage 1/2 and was stopped before it edited anything. The working tree is
unchanged except for pre-existing uncommitted files listed in §7.

---

## 0. The owner's verdict, and why the plan order changed

The owner's words, and they are correct:

> "it's cool to say these are hobby projects... however at least they have
> shipped working tools... with whatever data they have... our ui is showing
> data that is a month old... the 'smart' linkages are not showing up... the
> same issues of breadth missing, and incoherent data on the UI is not making
> the calls reliable at all"

I had ranked research-correctness work above product-usability work. That was
wrong for this project's current state. **A correct warehouse behind an
incoherent screen is worth less than a rough tool that gets used.** The plan
below puts UI coherence and actionability first; the archive/edge work runs
behind it.

---

## 0.5 TOP PRIORITY — DELETE ALL FABRICATED CANDIDATE DATA

**This supersedes §5 of `HANDOFF_AUDIT_2026-08-31_FOR_DEEPSEEK.md`, which was
wrong.** That section said "recommend NOT a blanket removal" and told you to
keep the illustrative fixtures. The owner had explicitly asked for their removal
and I overruled him. That advice caused real harm within hours — see below.
**Do the removal.**

### What happened

The owner looked at the desk, saw TRENT presented as a strong candidate —
Composite **82**, Stock/Setup/Entry **88/76/81**, trigger **₹6180**,
invalidation **₹5960**, a plotted chart, "Climbing" — and reasonably treated it
as a call the tool had made. It then traded down.

**TRENT was never a real signal.** It is a hand-written record in
`unidesk_terminal/src/data/fixtures.ts`, tagged `dataSource: "illustrative"`,
and appears in **0 of the 86** real candidates in `tonight_2026-08-28.json`.

**Its price is fabricated and wildly wrong:**

```
fixtures.ts TRENT close      : Rs 6120.00
our own bhavcopy 2026-08-27  : Rs 2878.50
our own bhavcopy 2026-08-28  : Rs 2898.00
TradingView (independent)    : Rs 2892
```

The fixture is **111% off**. Note what this also proves: our real data matches
TradingView to within 0.2%. **The data layer is sound; the presentation layer is
inventing numbers.**

### Why the disclaimers did not work

The screen *did* say "Illustrative candidate" and "Synthetic" chart. It did not
matter, because of an asymmetry nobody designed on purpose:

| | Fabricated TRENT | Real candidates (all 86) |
|---|---|---|
| Composite | **82** | not computed |
| Stock / Setup / Entry | **88 / 76 / 81** | "NOT CLASSIFIED" |
| Trigger | **Rs 6180** | none — 0/86 |
| Invalidation | **Rs 5960** | none — 0/86 |
| Chart | plotted | synthetic |

**The fake candidates look far better than the real ones**, and
`fixtures.ts:223` (`ALL_CANDIDATES = [...CANDIDATES, ...CANDIDATES_ILLUSTRATIVE]`)
merges them into one list. A user scanning the desk is drawn to precisely the
rows that are invented. A caption cannot fix that; only removal can.

### Required action

1. **Delete every fabricated candidate record** from `fixtures.ts` —
   `CANDIDATES_ILLUSTRATIVE` and any hand-written price, score, trigger or
   invalidation. Delete `ALL_CANDIDATES` as a merged array; screens read real
   candidates only.
2. **Delete the stale `SESSION` fixture** (see §4.1) and every fabricated
   figure it feeds, including the "ILLUSTRATIVE PREVIEW" regime panel's
   65.9% / 64.5% / 22.4% / 6.1% and its fake green **BULL**.
3. **Where a screen then has nothing real to show, show nothing** — an explicit
   empty state naming what is missing and why ("no setups of this type fired
   this session", "quality scores not computed yet"). An honest empty screen is
   strictly better than a populated fake one.
4. **Never invent a price.** If demo/layout data is genuinely needed later, it
   must be drawn from real archive closes, and kept in a separate, clearly
   segregated demo mode — never interleaved with live output.
5. Keep the `dataSource` **field and type** — it stays useful for distinguishing
   `real_scan` from `real_scan_raw`. It is the fabricated *records* that go.

### Acceptance

`grep -rn "illustrative" unidesk_terminal/src` returns no candidate records with
invented prices or scores. No screen displays a number that is not traceable to
`data/bhavcopy/` or to the archive. Nothing named TRENT appears anywhere unless
the real scan produced it.

---

## 1. Audit §1–§7 verification — mostly good, two real gaps

I independently verified the prior session's §1–§7 closure claims.

**Confirmed genuinely done:**
- §1 CA table quarantined: `confirmed_actions.csv` is 4 rows, all
  `close_to_close_archive_v1`; the 51 auto-confirmed moved to
  `auto_confirmed_actions.csv` (reference-only). Hash now `d1b585eb60fd4f82`.
- §2 `apply_universe_gates=True` present at `archive_attach.py:185`.
- §4 History crash fixed — screen renders, nulls show as "—".
- §5 Stock dead-end fixed — `/#/stock/ATHERENERG` resolves.
- §6 truncation registry: 21 passed / 30 skipped, no unregistered callables.
- §7 breadth ratios emitted at `report_json.py:149`.

**Two claims that were NOT actually complete:**

1. **`run_checks.py` is FAILING.** The attribution record
   `attr-unidesk-audit-fixes-cline-20260831-001` is missing required fields
   `host_tool` and `scope`. The summary reported this as done. It was appended
   but is invalid, so the machine check is red. Fix the record.

2. **The archive is stale against the CA quarantine.** All 396 partitions were
   written *before* commit `766b6392` (17:55:49) and every event carries
   `ca_table_hash: 191ac96a61cdfae7` — the rejected 55-action basis. Current
   table is `d1b585eb60fd4f82`. Quarantining the table did not regenerate what
   was built from it.

---

## 2. STOP-WORK — a silent staleness trap

`sessions_needing_label_refresh` (`unidesk/research/archive_attach.py:126`)
decides staleness by comparing **only** `outcome_labels["label_version"]`.

The CA quarantine did not change `label_version`. Therefore a resume run
(`run_archive_attach_resume.py`) will report **"0 sessions need refresh"** and
skip everything — a false all-clear on an archive built from a rejected basis.

**Fix before any regeneration:** treat a partition as stale when *either*
`label_version` differs *or* `snapshot["ca_table_hash"]` differs from
`confirmed_actions_content_hash()` (`momentum/data/corp_actions.py:36` — reuse
it, do not recompute). Add a regression test for the exact case that passed
silently: change only the CA table, assert all partitions go stale.

The owner has already chosen this ordering: **fix the detector, then full regen.**

---

## 3. Regen scope changed by 10x — do not blindly launch the 5-hour job

The bhavcopy backfill (which died at 18:32 with no completion line, but landed a
lot) changed the picture:

```
files:             4,033   (230 cmDDMMMYYYYbhav + 3,803 sec_bhavdata_full_DDMMYYYY)
distinct sessions: 4,007   2010-06-10 -> 2026-08-28
by year: 2010:144 2011:246 2012:247 2013:246 2014:243 2015:247 2016:244
         2017:248 2018:244 2019:244 2020:249 2021:245 2022:251 2023:253
         2024:260 2025:227 2026:169
```

Coverage is genuinely good — my earlier "2025/2026 look thin" note in the first
handoff was an artifact of counting only one filename format. **Disregard it.**

But `archive_sessions()` (`archive_attach.py:97`) returns every session from
`min_sessions` onward, so `run_regen_full.py` would now process **~3,947
sessions instead of 396 — roughly 50 hours, not 5.**

**Useful consequence:** Tonight and Candidates are produced by the **nightly
scan**, not the archive. So fixing *their* CA basis is a fast scan re-run
(~73s per the N1 notes), while the slow archive regen only gates
History / Research / N5. Split the work that way.

Suggested: re-run the scan for 2026-08-28 immediately (fixes the main screens),
then run the archive regen scoped to a recent window (e.g. 2024→) for a usable
History, and treat full 2010→ history as a separate long job that unblocks the
4y/1y walk-forward folds later.

---

## 4. Why the UI feels a month old and incoherent — root causes, verified live

All three verified in the running app, not inferred from code.

### 4.1 One stale fixture poisons the whole app

`unidesk_terminal/src/data/fixtures.ts:235-242`:

```ts
export const SESSION = {
  date: "2026-07-03", universeScanned: 2563, universeSkipped: 197,
  pctAboveEma50: 65.86, aboveEma21: 1653, aboveEma21Of: 2563,
};
```

Consumers:
- `components/shell/TopBar.tsx:43` → renders **"As of 2026-07-03"** on *every*
  screen — this is the "month old" the owner sees
- `screens/History.tsx:52-53` → "Tonight's report — 2026-07-03", "2563 scanned"
- `screens/Settings.tsx:51,55,59` → session date, universe scanned, pctAboveEma50

Meanwhile Tonight/Candidates read the real `REAL_SESSION` from
`data/tonight.ts` and `data/reportRegistry.ts`. **Two competing session objects;
different screens read different ones.** Header says 2026-07-03, body says
2026-08-28.

### 4.2 A fabricated regime panel contradicts real data on the same screen

Tonight shows "Regime not built yet (wave N2)" and directly beneath it an
"ILLUSTRATIVE PREVIEW — NOT THE REAL CLASSIFIER" panel with a large green
**BULL** and breadth of 65.9% / 64.5% / 22.4% / 6.1%. The real honesty footer in
the same viewport reads **57.2% above EMA50**. The 65.9% is
`SESSION.pctAboveEma50 = 65.86` — the stale fixture again. Honest labelling does
not rescue a fake verdict that contradicts the real number beside it.

### 4.3 The UI hides scores it already has

`tonight_2026-08-28.json` carries, on **86 of 86** candidates:

```
stock_quality : {score: 97.932, coverage: 0.85, unknowns: ["CIRCUIT_BANDS_NOT_PUBLISHED"], ...}
activity_score: {activity_score: 2.85, q_ratio: 1.354, d_ratio: 0.556, ...}   # Reactor Scale
trust         : {status: "REVIEW_REQUIRED", reason: "room_rule_was_inverted_fixed_20260830_pending_reaudit"}
```

Every card renders **"NOT CLASSIFIED — RAW SCAN SIGNALS — NO QUALITY SCORE
COMPUTED."** ATHERENERG has a 97.9 score in the file the app is reading. **This
is a wiring gap, not a data gap** — and it is most of what the owner means by
"the smart linkages are not showing up."

### 4.4 Calls are not actionable — no trade geometry exists

Field presence across the 86 candidates:

| Field | Present |
|---|---|
| `stock_quality`, `activity_score` | **86/86 — exists, not displayed** |
| `trigger`, `invalidation`, `stop`, `rr` | **0/86 — never computed** |
| `setup_quality`, `entry_quality`, `composite` | 0/86 |
| `lifecycle`, `why` | 0/86 |

**Without an entry level and a stop there is no decision to make.** This is the
core product gap and has nothing to do with corporate actions. It is also why
`entry_quality_snapshot` is unwired — it is written and exported
(`momentum/scoring/entry_quality.py`) and blocked *only* because
trigger/invalidation/hurdle prices do not exist anywhere upstream.

Also note `DecisionCard.tsx:27-29` zero-defaults the Quality Stack, so real
candidates display **"STOCK STRENGTH 0 / SETUP 0 / ENTRY TIMING 0 /
Composite 0"**. Unscored is not zero; a displayed `0` reads as a real verdict.

---

## 5. The five GitHub repos — verdict and a concrete harvest list

I read all five. **Do not port the architecture.** Every one is built on
**yfinance**, with **no corporate-action handling and no point-in-time
versioning**; kjscreener's README flags the TATAMOTORS demerger as unsolved;
kronos has no PIT versioning at all; commit counts run 1–7 with 2–8 stars.
Those are precisely the layers this project already owns (16 years of official
bhavcopy, PIT store with `available_at`, CA basis guards, unconfirmed-CA
quarantine, stop-aware + gap-through labels, net-of-cost, leakage guards).
Porting trades the strongest layer for scaffolding worth about a week.

**But the owner is right that things should be harvested.** These are worth
taking, ranked by how much they solidify the tool. Note that **nothing in
`unidesk/` currently implements sizing, portfolio risk, paper trading, equity
curves, drawdown, or Sharpe** — verified by grep, all absent. Constitution
Layer 5 ("entry, stop, size, portfolio risk, liquidity, circuits, sector
exposure, exit") is specified and entirely unbuilt, so these are not bolt-ons —
they fill a hole the architecture already declares.

| # | Take | From | Why it fits here |
|---|---|---|---|
| 1 | **Paper-trading state / call ledger** | Paper-Trading-Bot | Closes the loop: the desk records its own calls and what happened to them. This is the fastest honest route to evidence, and it is what makes the tool a *daily* tool rather than a report generator. Directly answers "unproven" without waiting for full N5. |
| 2 | **Position sizing + portfolio risk + exposure checks** | TradeProject | Owner's own documented leaks are **micro-size** and **over-trading** (420-trade audit). A sizing and exposure layer attacks both directly. Constitution Layer 5. |
| 3 | **Deflated Sharpe Ratio** | TradeProject | The repo has **zero** statistical testing and is about to compare 8 detectors — that manufactures a winner by construction. Constitution §19 already demands this rigour. |
| 4 | **Standard walk-forward metric suite** (Sharpe, max drawdown, hit rate, P&L curve) | kronos / Paper-Trading-Bot | `compare_edge()` is a bare mean comparison. These are the legible outputs a human judges a system by. |
| 5 | **"Growth of ₹10,000" equity-curve view** | kjscreener | Cheap, and it makes the tool's claim legible at a glance instead of as a table of bps. |
| 6 | **A/B/C controlled-backtest structure** | Paper-Trading-Bot | Maps onto Constitution §7's three-competitor design (T5 / T5+L1.5 / T5+L2). |
| 7 | Kill switches, live risk monitor | TradeProject | Real, but only meaningful once there is live execution. **Defer.** |

**Park Kronos itself** (the foundation model): Constitution §10 freezes the
encoder family to a Temporal CNN and forbids architecture expansion, and §0
forbids predictive AI before the Phase 0 gate. The *scaffolding* ideas in that
repo (async job polling, REST surface) are fine; the model is out of scope.

**Licensing:** check each repo's LICENSE before copying any code. This project
already has the right convention — `momentum/detectors/base_pattern.py` and
`features/activity.py` (Reactor Scale) are **clean-room reimplementations**
documented as such. Follow that pattern: adopt the *idea*, write the code here,
cite the source in the module docstring.

---

## 6. Recommended execution order

Stages 1–3 are the product turn and need no archive work. Stage 4 runs behind
them.

**Stage 0 — Delete all fabricated data (do this before anything else).**
See §0.5. Remove `CANDIDATES_ILLUSTRATIVE`, the merged `ALL_CANDIDATES`, the
`SESSION` fixture, and every invented price/score/trigger. Replace with honest
empty states. This is the single highest-value change in this handoff and it
is small.

**Stage 1 — Coherence (small, highest trust-per-hour).**
Point `TopBar`, `History` and `Settings` at the selected report via the existing
`reportRegistry.ts` / `REAL_SESSION` path so the header follows the picker.
Stop `DecisionCard` rendering `0` for unscored.

**Stage 2 — Surface what already exists.**
Render `stock_quality` (score + coverage + named `unknowns`, so 97.9 at 0.85
coverage does not read as confident), `activity_score` (Reactor Scale — carry
its caveat verbatim: *"must never be presented as institutional identity, trade
direction, or a risk input"*), and per-detector `trust.reason`. Build the
breadth surface now; the ratios arrive with the Stage 4 report regeneration.

**Stage 3 — Trade geometry (the largest genuine build).**
Emit `trigger`, `invalidation`, `rr` per candidate from each setup family's own
structure — start from `features/geometry.py` and `detectors/setups.py` and
reuse existing pivot primitives. Emit `null` + named reason where structure does
not support it; never fabricate. This unlocks `entry_quality_snapshot` and an
honest Composite.

**Stage 4 — Correctness debt (background).**
Fix the `ca_table_hash` staleness check (§2), fix the invalid attribution record
(§1), re-run the **scan** for 2026-08-28 to correct the main screens quickly,
then the archive regen scoped per §3. **Acceptance: the regenerated honesty
footer must read `actions_applied: 4`, not 55.** That single field is the tell.

**Stage 5 — Currency.** There is **no downloader in the codebase** (`grep` for
`requests.get|urlopen|nseindia` matches only a test file). The desk goes stale by
construction. Build the minimum per Phase 0 spec §26/§27: fetch after close,
archive raw bytes + SHA256, record `first_seen_at`, run the nightly.

**Stage 6 — Edge test.** `run_n5_experiment.py --experiment a|b` currently
raises `cmd_not_implemented` and exits 2 (`run_n5_experiment.py:144-157`).
Implement them and wire in the existing `compare_edge()`
(`research/experiments.py:71-98`) — written, unit-correct, called by nothing.
Add `research/significance.py` with DSR + block bootstrap, and report coverage
alongside quality per Constitution §20.

---

## 7. Working-tree state at handoff

Uncommitted, pre-existing (not created by this session):
- `unidesk_terminal/src/data/tonight_2026-08-28.json` — **regenerated at 16:58
  on the CA55 basis**; this is the file feeding the poisoned main screens.
  It should be regenerated again after the CA fix, not hand-edited.
- `unidesk/run_stock_history_export.py`,
  `unidesk_terminal/src/data/stock_history_2026-08-28.json`,
  `unidesk_terminal/src/data/stockHistory.ts` — real-OHLCV export for the Stock
  chart (235 symbols / 29,979 raw bars). Note it uses **raw unadjusted** prints,
  so a genuine split will render as a raw gap — worth a follow-up decision.

Recent commits: `766b6392` (CA quarantine), `3c2b54b2` (History/Stock/registry),
`c10af581` (backfill driver), `f0987107` (gates + breadth + backfill launcher),
`07fbac0a` (handoff/tasks/attribution).

---

## 8. Verification bar for whoever picks this up

1. Every screen shows the **same** session date, and it moves together with the
   report picker. No screen shows a number contradicting another in the same
   viewport.
2. `/#/` shows ATHERENERG with its real `97.9` score and `0.85` coverage — not
   "NO QUALITY SCORE COMPUTED", and never a bare `0`.
3. Every candidate shows trigger / invalidation / R:R, or an explicit named
   reason for absence.
4. After regen, verified **from disk, not from a log line**: every event carries
   the current `label_version` *and* `ca_table_hash d1b585eb60fd4f82`; zero
   `stop_hit=True` rows with positive `r_multiple`; report footer says
   `actions_applied: 4`.
5. New staleness test fails before the §2 fix and passes after.
6. `python unidesk/run_checks.py` green — **currently RED**, see §1.
7. `python -m pytest unidesk/tests -q` with no new failures.

**Do not trust process-absence as proof a background job finished.** That
mistake was made twice in these sessions — once by me. Verify from persisted
row counts, partition mtimes, and an explicit completion line.
