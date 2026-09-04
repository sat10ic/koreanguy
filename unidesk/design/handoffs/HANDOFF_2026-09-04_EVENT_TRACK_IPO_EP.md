# HANDOFF — the event track: IPO and EP as a first-class surface

**Date:** 2026-09-04 · **Author:** Claude Opus 5 (spec role; no code written by this doc)
**For:** Sol · **Parallel to:** GLM's CA/infrastructure lane, and a Sonnet agent already
building E-1 (see §3.1)
**Roadmap:** North Star edges **5 (IPO base maturity)** and **6 (EP quality)**;
`STATUS_AND_ROADMAP_2026-09-04.md`
**Containment:** `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §10 governs every surface here

---

## 1 · Why IPO and EP need their own track

Every other setup is **structure-anchored**: price built a pattern over N sessions, and the
pattern is the subject. Base breakout, inside bar, pullback, reversal — all of them.

IPO and EP are **event-anchored**. The clock starts at a *thing that happened* — a listing,
a gap — and everything is measured relative to that day 0. That difference breaks four
assumptions the main desk is built on:

| Main desk assumes | IPO | EP |
|---|---|---|
| ≥61 sessions of history | 13-session listings are refused outright | fine |
| ADR20 is the volatility unit | needs 20 sessions the name doesn't have | the gap itself distorts ADR |
| RS percentile vs universe | needs 20-day returns | gap distorts the return |
| Structure over a 250-day window | there is no 250-day window | the only structure that matters is post-gap |

So they are not badly-served setups — **they are a different measurement frame.** MILKYMIST
is the proof: it was in the bhavcopy with ₹543 cr turnover and was silently refused for
having 13 of 61 sessions.

## 2 · Most of this is already built and dormant — connect, don't invent

**Read these before writing a line.** Every one is written, correct, and consumed by
nothing:

| Module | What it already gives you |
|---|---|
| `research/market_events.py` | `IPOListingFact`, `EarningsResultEvent` — PIT source contracts. Its docstring already states the rule: *"Consumers must use `available_at` rather than a listing date, fiscal period, or announced future board-meeting date."* |
| `research/event_anchors.py` | `EventAnchor` — kind, source_event_id, anchor_session, `available_at`, `source_hash`, `adjustment_basis`. Deliberately refuses planned/future events: *"a planned board meeting has no compatible type, so it cannot become an anchor by accident."* |
| `momentum/features/avwap.py` | anchored VWAP from an anchor index; returns `None` before the anchor rather than back-filling. Says anchor **detection** belongs to setup primitives — that is the missing piece. |
| `research/events.py:61` | `parse_ipo_listings()` — a parser with no data (E-1 fixes this) |

**The pattern to notice:** the hard, subtle parts — point-in-time contracts, availability
semantics, anchor provenance — are done. What is missing is the boring wiring. Do not
redesign the contracts; feed them.

## 3 · Data layer

### 3.1 · E-1 · IPO listing facts — IN FLIGHT, do not duplicate

A Sonnet agent is building `run_ingest_listing_calendar.py` + `data/reference/` snapshot +
listing-age feature + tests. **Do not touch it.** Its output must materialise as
`IPOListingFact` records (§2). If it lands producing something else, adapt at the boundary
rather than forking the contract.

### 3.2 · E-2 · Earnings and corporate announcements

Feeds EP quality (edge 6) and is the seed of AIRG (edge 1).

- **Source:** NSE corporate announcements. **BSE is an acceptable substitute** and is
  easier to fetch — nearly all names are dual-listed. State which you used.
- **The rule that decides whether this works:** an announcement is knowable at its
  **broadcast timestamp**, not its date. A post-close filing belongs to the *next*
  session. `EarningsResultEvent.available_at` already exists for exactly this — use it.
  Getting this wrong leaks the future into every EP result and the leakage suite will not
  catch it, because the timestamp is in your ingest, not in the labeller.
- **Store** partitioned by date under `data/reference/announcements/`, each record with
  `first_seen_at`. **This doubles as the Phase 0 availability ledger (gate item #26,
  currently FAIL)** — say so in your completion note; it closes a gate item for free.
- **Derived fields:** `catalyst_type` (results / order-win / guidance / other),
  `days_since_catalyst`, `is_results_gap`.
- **Absence is not evidence.** No announcement found → `catalyst: null`, never
  `catalyst: "none"`. A missing scrape is not a quiet tape.

**Acceptance:** pick three known results gaps from the archive. For each, show the
announcement, its `available_at`, and prove the session it becomes knowable in is the
session *after* a post-close filing. Paste all three.

### 3.3 · E-3 · Circuit bands

Two steps, ship the first immediately:

1. **Interim, no new source.** The current check is only `high == close`. Make it exact:
   locked when `high == low == close` (frozen), **or** when `close / prev_close` lands
   within one tick of ±2/5/10/20%. Uses data you already hold and fixes the false
   positives today.
2. **Proper.** NSE publishes a daily band file; store band % per symbol per session and
   stop inferring. Verify the URL yourself.

**Acceptance:** on 2026-09-01, MILKYMIST must be flagged locked (`high == last == close ==
232.03`, exactly +10.00% off 210.94), and a stock that merely closed on its high must
**not** be. Paste both.

## 4 · Feature layer — event-relative, not absolute

New module `momentum/features/event_relative.py`. Frozen defaults, `ContractError` on bad
input, `None` on warm-up, windows exclusive of the current bar — mirror `features/thrust.py`.

**Shared:** `sessions_since_event(anchor_session, as_of)` on the **trading calendar**,
never calendar days.

**IPO track** (day 0 = listing):
- `pct_from_listing_high`, `pct_from_listing_low`
- **`first_day_range_pct` as the volatility unit** — replaces ADR20, needs one session
  instead of twenty. This is the single change that makes young listings measurable.
- `base_vs_listing_range` — consolidation depth relative to day-0 range, not a 250-day window
- `pct_from_issue_price` — `None` until issue price is available; do not block on it

**EP track** (day 0 = gap):
- `gap_pct`, `gap_day_close_location`
- **`held_above_gap_low`** — the survival test that separates a durable EP from a squeeze
- `volume_decay_since_gap` — RVOL trajectory, not a point
- `days_locked_since_gap` (from E-3)
- `catalyst_type` / `days_since_catalyst` (from E-2)

**Register every new public callable in `test_truncation_invariance.py`.** Not optional —
the thrust wave shipped without it and the guard caught it three days late.

## 5 · UI — the Events screen

**A lens, not a second ranking.** These candidates already appear in the main feed. This
screen re-frames them; it must never produce its own ordering or its own signal.

### 5.1 · The core visual: event-normalised overlay

One chart per track. **X = sessions since day 0. Y = % from the day-0 anchor.** Every name
in the track is a line, all starting at (0, 0).

This is the North Star's *"Normalize Every IPO From Day 0"* rendered literally, and it is
the first place `research/analogue.py` becomes visible: **the faint background lines are
the retrieved historical analogues**, the bold line is tonight's name. The user sees what
happened to similar events without a single predictive claim being made.

Constitution §22 governs the caption: *what happened to similar events*, never a
probability, never "chance of success". Sample count always attached (§20).

### 5.2 · Two tracks, one grammar

| | IPO track | EP track |
|---|---|---|
| Day 0 | listing day | gap day |
| Volatility unit | first-day range | pre-gap ADR |
| Row headline | "Day 14 · +8% from listing high" | "Day 3 · held gap low · results" |
| Structural chip | base vs listing range | held / lost gap low |
| Countdown | anchor unlock in N sessions (§6) | — |
| Context | issue price distance | catalyst type + age |

### 5.3 · Honest states — non-negotiable

- **`ipo_base` trust is BLOCKED today** (`detectors/trust.py:33`,
  `listing_age_is_not_verified`). Even after E-1 lands, **flipping that status is an
  owner decision, not yours.** Until then every IPO row renders its BLOCKED chip and reason.
- Both tracks are **Lab tier** (§10) until the edge test validates them. Beginner and Pro
  must not show an unvalidated track as though it were a signal.
- `None` renders as an em dash with a named reason. A young listing with no `pct_from_issue_price`
  says "issue price not ingested", not "—" alone.

### 5.4 · Containment tests (from §10.6)

Ranked symbol order on Tonight and Candidates must be **byte-identical** with the Events
screen present and absent, and identical across all three modes. Paste the diff; it must
be empty.

## 6 · Lock-in — mostly free once E-1 lands

The lock-in **dates** are formulaic from the listing date under SEBI rules; only the anchor
*quantum* needs the RHP. So anchor and promoter unlock dates fall out of E-1 with no
scraping.

**Two conditions, both binding:**

1. **Verify the current SEBI lock-in periods yourself.** They changed around 2021-22. Do
   not take a period from this document or from memory — cite the rule you used.
2. Store as `derived_from_rule` with the rule version, **never as observed fact**, so a
   rule change cannot silently corrupt history.

Surface as a countdown chip on the IPO row. Descriptive context — it is not a risk input
and must not enter any score.

## 7 · Sequencing and constraints

```
E-1 listing facts (Sonnet, in flight)
   └─→ IPO features (§4) ──→ Events screen IPO track (§5)
                          └─→ lock-in countdown (§6)
E-2 announcements ──→ EP features (§4) ──→ Events screen EP track (§5)
E-3 bands (step 1 today) ──→ both
```

**Order for Sol:** E-3 step 1 (an hour, immediate value) → E-2 (the long pole) → §4 features
→ §5 UI. Do §5 last; a track with no event data is empty frames.

**Do not:**
- duplicate E-1 — a Sonnet agent owns it
- open GLM's files (see `WORK_ORDER_2026-09-04_SOL_PARALLEL.md` §1) or run git index surgery
- read/write `data/market/research/events/**` while B2-3 runs
- flip `ipo_base` to rankable — owner decision
- let the Events screen influence ranking, `deriveState`, or `invalidation`
- redesign `market_events.py` / `event_anchors.py` — they are correct; feed them

**This slots into the roadmap at step 6** of `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md`
§11.2 (edge 5, IPO) and step 5 (edge 6, EP). It does **not** jump the queue ahead of S-1,
the experiment harness — without that, neither track can ever be validated, and an
unvalidated track is a Lab curiosity rather than a product.

---

## 8 · Source integration — the practitioner spec and its addendum

**Added 2026-09-04.** Two owner-supplied documents now govern the *content* of this track:

- `ipo_ep_consolidated_technical_spec.md` — source-derived IPO/EP methodology, with
  disagreements between sources preserved rather than reconciled
- `ipo_ep_tool_integration_addendum.md` — maps that material onto this architecture

**Adopt the addendum's governing model verbatim (§0).** It is the same discipline this
repo already enforces, stated for source knowledge:

```
source says X  ->  encode X as observable evidence  ->  test whether X matters
               ->  decide: filter / ranker / context / UI-only
```

Never `source says X -> score -> trade`. And keep its three layers separate:
**what we observe** / **what the source claims it means** / **what our validation proves**.
Only the third drives ranking or gating.

### 8.1 · Two conflicts, recorded as decisions rather than dropped

**(a) Source stop widths are not merely unvalidated — they are locally falsified.**

The spec carries §13.2 (~1.5-2% EP stop) and §53.1 (~4% IPO stop). The addendum correctly
parks both in §25 as unproven. **This repo has already measured further than that.**

Median `stop_thrust_days` on the desk is **0.67**, and 37 of 57 sit below 0.75 — stops are
*already* tighter than one ordinary strong day. A 1.5% stop on a name with ~10% ADRMAX is
**0.15 thrust-days**: a seventh of an already-too-tight median.

Those widths work in the source **because of intraday management** — enter at 9:15, move to
breakeven within minutes (spec §15). An EOD desk keeps the tight stop and loses the
mechanism that made it survivable.

**Decision: do not port any source stop percentage.** The spec's own §53.3 principle — stop
width must be judged against potential movement — is right, and `stop_thrust_days` is
already this repo's expression of it. Structural stops (§1-§5 of the levels handoff) are
the live alternative.

**(b) RVOL — the spec and the constitution disagree, and neither wins by argument.**

Spec §21 argues RVOL/delivery must not gate EP Day-0. The constitution's engineered EP
vector includes `rvol_20`. Addendum §14 is right: settle it with the experiment, comparing
*baseline vs +RVOL* and *ranking feature vs hard gate*, reporting coverage alongside
expectancy. **Note the spec scopes its objection to EP Day-0 only** — it does not
generalise to the universe gates, and must not be read as doing so.

### 8.2 · Where each source concept lands

Tiers: **NOW** = daily bars, deterministic, buildable today · **E-2/E-3** = needs the
announcement or band ingest · **INTRADAY** = order-flow engine, last by owner directive.

| Source concept | Repo destination | Tier |
|---|---|---|
| Listing age, free-trade age | `listing_calendar.py` (built) | **NOW** |
| Listing AVWAP | `features/avwap.py` + `event_anchors.py` — **both dormant, connect them** | **NOW** |
| IPO-day range, 50% level, defended | `features/event_relative.py` (§4) | **NOW** |
| Base depth / duration / contractions | `base_episode.py`, `base_pattern.py` (exist) | **NOW** |
| VCP geometry class (flat-high/higher-low, converging, flat-low/lower-high) | new, from pivot highs/lows | **NOW** |
| Bar-by-bar: overlap, range sequence, low progression, close location, lower-tail, ground-lost, momentum-bar reclaim | new — **spec §48-§51, the strongest unbuilt material here** | **NOW** |
| Crow Bar / Hook / Fast Flag | separable by MA relationship (price returns to MA / MA catches up / neither) | **NOW** |
| TVCP | contraction sequence — computable | **NOW** |
| IHS, J-Curve | **human/AI label only** — do not invent geometry tolerance (addendum §4.3) | later (L2) |
| Volume baseline gate | spec §55 — only normalise once baseline sessions exist | **NOW** |
| Neglect evidence vector | spec §4.2, addendum §12 — vector, never a boolean or a score | **NOW** |
| Gap %, close location, extension | `features/event_relative.py` (§4) | **NOW** |
| Follow-through D1/D3/D5 | archive + existing labeller | **NOW** |
| Outcome distribution (full loss / partial / breakeven / small / large win) | spec §15 — richer than win rate; R-multiples already exist | **NOW** |
| EP reset / delayed / pullback lifecycle | spec §60, addendum §7 | **NOW** |
| Repeated quarterly EP | archive event history | **NOW** |
| Catalyst type + taxonomy | E-2 | **E-2** |
| EPS/Sales QoQ+YoY, consolidated flag, exceptional items | E-2 (`results_calendar.parquet` has a 175-row start) | **E-2** |
| Circuit limit / state | E-3 | **E-3** |
| Delivery — **decision-time split** | see §8.3 | **E-2** |
| Day-0 ORB, 1m/3m/5m, first-negative-bar, pre-open | order-flow engine | **INTRADAY** |
| 75m / 15m multi-timeframe | order-flow engine | **INTRADAY** |

### 8.3 · Delivery: the sharpest rule in the addendum (§15)

- **Day-0 EP: same-day delivery MUST NOT be used.** It is not public at decision time.
- **Day-1 and later: EP-day delivery MAY be used** — for follow-through, reset state,
  pullback and analogue retrieval.

This is the cleanest illustration of why `available_at` exists in `market_events.py`. Any
feature that violates it leaks the future in a way the leakage suite will not catch,
because the violation is in the ingest, not the labeller.

### 8.4 · The reframe that makes an EOD desk sufficient

Spec §16 states it outright: **"successful Day-0 entry ≠ successful EP."** The EP is
validated by follow-through, not by the ORB trigger.

So the intraday gap does **not** block the research. This desk can build and validate the
EP hypothesis on daily bars; it simply cannot trade the open. Addendum §16 sequences this
correctly — **Phase 3A daily-only, then Phase 3B intraday, compared on the same subset.**

### 8.5 · What the addendum assumes that does not exist here

Its examples reference **"Home 2"** and **"Home 4"**. This app has Tonight, Market,
Candidates, Desk, History, Research, Settings. Map before building:

| Addendum | This app |
|---|---|
| Home 2 (decision-relevant subset) | **Tonight** |
| Home 4 (EP watchlist by lifecycle state) | **Desk**, or the Events screen (§5) |
| Candidates research lab | **Candidates** |
| IPO Lab / EP Lab (§20) | **Research** — belongs there, not on Tonight |
| Stock Detail → Setup Evidence | **Stock** (`SetupEvidencePanel.tsx` exists) |

Addendum §22's lifecycle layer (regime → setup family → event/structure → lifecycle state →
candidate → entry readiness → outcome) is a **real architectural addition**, not a rename.
Scope it separately; do not smuggle it into this track.

### 8.6 · Everything marked "Validate" queues behind one thing

Addendum §26 marks these for validation: the 30% earnings heuristic, RVOL as gate, the 3%
gap cutoff, the 12% extension cutoff, stop families, IPO-day 50% defence, down-expansion
reversal.

**All of them need the same experiment harness** — `run_n5_experiment.py --experiment a|b`
against `compare_edge` + deflated Sharpe, which now exists on fixtures and runs for real
once B2-3 lands. Addendum §28's required outputs (coverage, expectancy, MFE, MAE, drawdown,
year/sector concentration, regime distribution) should become that harness's standard
report, not a per-experiment reinvention.

**Do not build a scoring layer for any of this first.** Spec §66: *"Do not start by
building a black-box EP score."* Evidence, then validation, then promotion.

### 8.7 · Adopt regardless of build order

- **Spec §65 anti-hallucination rules** — near-verbatim this repo's house rules. Add the
  list to the handoff checklist for any agent touching IPO/EP.
- **Spec §61 hard-vs-soft split** — maps directly onto §10's containment tiers in the
  levels handoff. Soft/contextual fields are Lab tier by construction.
- **Spec §62 source-conflict matrix** — preserving disagreement as configuration rather
  than reconciling it silently is a pattern worth copying repo-wide.
- **Spec §25 "FAILED EPs MUST BE INCLUDED"** — the same anti-survivorship error this desk
  already made once, when History reported a censored 0% hit rate as performance.
- **Addendum §19's division of labour** — deterministic layer owns what is measurable
  (gap, range, inside bar, higher lows, EMA distance, age, depth, RS, ATR contraction);
  the AI challenger earns its place only on what is genuinely morphological (visual
  contraction quality, IHS/J-Curve shape, reset quality, path similarity). That is what
  makes L2 a challenger rather than an expensive reimplementation of hand-coded metrics.
