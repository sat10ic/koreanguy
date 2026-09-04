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
