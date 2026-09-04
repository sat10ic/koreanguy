# HANDOFF — Market screen: full rotation / sector / industry / theme intelligence

**Date:** 2026-09-04 · **Author:** Claude Opus 5 (spec role; no code written by this doc)
**Source spec:** `market_sector_industry_theme_rotation_technical_spec.md` (owner-supplied)
**Reference repos (read for maths only — see §1):** BennyThadikaran/RRG-Lite ·
AdroitAnandAI/RRG-Sector-Rotation-India
**Containment:** `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §10 governs every surface here

---

## 0 · Scope decision, recorded

I recommended Phase 1 only, on the grounds that this is a **context layer** — it validates
none of the six North Star edges on its own, and building it while the first edge is still
unmeasured adds a second large unvalidated surface. **The owner chose the full spec.**
Recorded once; not repeated. The rest of this document builds all of it.

What is **not** negotiable regardless of scope: the correctness constraints in §3 and §4.
Those are bugs and lookahead traps, not preferences.

## 1 · Provenance and licence — clean-room, as usual

| Repo | Licence | Use |
|---|---|---|
| BennyThadikaran/RRG-Lite | **GPL-3.0** | **Do not vendor or copy.** Its own README admits it is "not yet at the level of the original RRG" and lacks smoothing. |
| AdroitAnandAI/RRG-Sector-Rotation-India | "educational and personal use" | **Do not vendor.** Carries the usable JdK formulation, restated below. |

Reimplement from the maths in §2 — the same convention this package already uses for
`detectors/base_pattern.py`, `features/activity.py` and `features/thrust.py`. Document
provenance in-module.

## 2 · The maths, frozen

Implement **both** normalisations. They answer different questions and share all inputs.

### 2.1 · Percentile form — the default (spec §20)

```
x = percentile_rank(group_rs,           all_groups_on_that_date)
y = percentile_rank(group_rs_accel,     all_groups_on_that_date)
```

Point-in-time by construction — the peer set is that date's groups. No full-sample
percentiles. This matches the Candidates scatter's existing percentile axes, so the desk
stays internally consistent.

### 2.2 · JdK form — Pro/Lab, for comparability with other platforms

```
RS            = group_index / benchmark_index
RS_Ratio      = 100 * EMA(RS, m) / RollingMean(EMA(RS, m), m)
ROC           = (RS_Ratio[t] - RS_Ratio[t-k]) / RS_Ratio[t-k]
RS_Momentum   = 100 + 100 * EMA(ROC, m)
```

with `alpha = 2/(m+1)`; **daily: m = 20, k = 20**. (Weekly m=14/k=10 and monthly m=6/k=3
are the source's other timeframes — freeze daily first.)

Optional z-score variant: `100 + 10 * (value - mean) / stdev`.

**Warm-up:** EMA(m) + rolling mean(m) + ROC(k) needs roughly `2m + k` ≈ **60 sessions** of
group history before the first honest point. Return `None` before that — never a partial
value (R12).

### 2.3 · RS acceleration — the simple form (spec §11)

```
rs_accel = slope(rs_ratio, prior 5 sessions) - slope(rs_ratio, prior 20 sessions)
```

Freeze the slope method (least-squares on the log ratio is defensible; state which).
**The frontend must never compute acceleration** — it renders what the backend emits.

## 3 · Three data findings — read before planning anything

### 3.1 · There are NO sectoral indices. This is the central problem.

`data/market/reference/indices.parquet` holds only:

```
NIFTY 50 · NIFTY 500 · NIFTY MIDCAP 150 · NIFTY SMALLCAP 250 · India VIX
```

No NIFTY IT, BANK, AUTO, PHARMA, FMCG, METAL, REALTY, ENERGY, INFRA.

Consequence: every group series must be **composited from member stocks**, which requires
point-in-time membership, which you barely have (§3.2).

**The unlock: ingest NSE's published sectoral indices.** NSE publishes them daily, free.
That gives correct, deep sector RS **with no membership dependency at all** — the index
constituents are the exchange's problem, not yours. Membership is then needed only for
*breadth* (% of members above EMA) and for the industry/theme layers.

**Do this first.** It converts the hardest part of this spec into a solved one.

### 3.2 · Membership exists in shape but not in depth

`universe_snapshots.parquet` — 43,980 rows, **23 sectors, 122 industries**,
`is_tradeable`, dated by `as_of_date`. Good taxonomy, real PIT structure.

But: **only 18 distinct dates, 2026-07-10 → 2026-08-20**, and it is **two weeks stale**.

Therefore:

| Horizon | Composited group series | Verdict |
|---|---|---|
| 5D, 20D | membership barely moves in a month | **safe** |
| 60D, 6M, persistence | applies *today's* membership to historical prices | **survivorship + lookahead** |

**Do not silently compute 60D/6M composites off current membership.** Either ingest the
sectoral indices (§3.1, removes the problem for sectors), extend the snapshot history, or
render those horizons as `INSUFFICIENT HISTORY`. Never the third option silently.

**Also: add the universe snapshot to the nightly.** A membership table that stops two weeks
ago will quietly rot the whole screen.

### 3.3 · Index names are duplicated across source tiers

```
NIFTY 50 (1240)  vs  Nifty 50 (59)
NIFTY 500 (474)  vs  Nifty 500 (59)
NIFTY MIDCAP 150 (474) vs Nifty Midcap 150 (59)
NIFTY SMALLCAP 250 (474) vs Nifty Smallcap 250 (59)
```

Same index, two spellings, two `source_tier`s. Any group RS built on this will split or
double-count the benchmark. **Normalise to a canonical `index_id` before anything else**,
and add an invariant that a session never carries two rows for one canonical index.

## 4 · R-0 · Blocking preconditions

Nothing else starts until these three land:

1. **Canonical index identity** (§3.3) + invariant.
2. **NSE sectoral index ingest** (§3.1) — dated, content-hashed snapshot under
   `data/market/reference/`, same pattern as `run_ingest_listing_calendar.py`. Store
   `first_seen_at`.
3. **Universe snapshot in the nightly** (§3.2) so membership stops aging.

**Acceptance:** one canonical row per index per session; sectoral index history depth
reported; `universe_snapshots` newest `as_of_date` equals the newest report session.

## 5 · Build order — the whole spec

### R-1 · Group state store

New `unidesk/research/group_state.py` + a persisted daily table mirroring
`GroupDailyState` (spec §38.2), including `availableAt` and `buildVersion`.

Every percentage stores **numerator, denominator, coverage** (spec §12). Suppress the
metric when `coverage < 0.80` (spec §46) and render `INSUFFICIENT COVERAGE` — never a bare
number, never 0 (spec §45).

Groups: SECTOR (23), INDUSTRY (122), THEME (later). Aggregate the per-symbol EMA/SMA
states `scan.py` **already computes universe-wide** — they exist and are simply never
grouped.

### R-2 · Group RS, acceleration, breadth deltas

§2 maths. Sector RS from the ingested sectoral index where one exists; equal-weight
composite otherwise, with the weighting **frozen and stated** (spec §10). Store the
cap-weighted variant alongside for comparison.

### R-3 · Leadership state lifecycle

`DORMANT → AWAKENING → EMERGING → LEADING → MATURE → FADING → WEAK` (spec §8).
Rule-derived, transparent thresholds, **stored as both `raw_state` and `final_state`** with
hysteresis so it does not flicker daily. Store `state_start_date` and `state_age_sessions`
— that is freshness (spec §17).

### R-4 · Concentration, density, setup mix, persistence

- `top3_contribution` → BROAD / MIXED / CONCENTRATED (spec §14), formula stored
- `candidate_density = candidate_count / valid_member_count` (spec §15)
- setup mix **from actual candidate records**, never re-inferred from price (spec §16)
- `persistence_pct` = share of prior N sessions in the top RS quartile (spec §18)
- **theme size guard** (spec §47): `member_count < 4` → `LOW_SAMPLE`, never ranked
  alongside broad sectors without the warning
- **candidate concentration guard** (spec §48): expose
  `candidate_distribution_by_industry`, not just the count

### R-5 · RRG-lite + momentum river

Percentile axes by default, JdK in Pro/Lab (§2). Trails 5 sessions default, 10 in Pro.
**Never more than 12-15 visible groups.** Bubble size = `breadth_ema21 × valid_member_count`
with the normalisation documented — **never candidate score** (spec §22). Restrained
palette keyed to state, not rainbow sectors (spec §23).

Momentum river = quantised percentile buckets across INTRADAY / 5D / 20D / 60D / 6M
(spec §28), with tooltips carrying the exact percentile. **INTRADAY renders `Unavailable`
until real intraday data exists — never synthesised from EOD** (spec §5.1).

Add the Breadth × RS alternative view (spec §24) — it is the beginner-legible one.

### R-6 · Theme system

Schema per spec §6.3 / §38.4: `theme_member` with `effective_from/to`, `source_type`,
`confidence`.

**Confidence gate (spec §7):** `VERIFIED` / `STRONG` / `MANUAL` may enter production
ranking. **`INFERRED` is Lab-only and excluded from production ranking by default.**
Never assign a theme from a company name or vague similarity (spec §1.3).

Theme discovery (spec §36-37) is research-only: AI may *propose*, price and breadth must
*confirm*, a human promotes. A newly inferred theme never becomes production-ranked
automatically.

### R-7 · UI

Page order per spec §3: market character → rotation horizon → rotation map → emerging /
fading → momentum river → hierarchical sector→industry→theme table → leaders → candidates.

- **Rotation horizon control** persisted; Beginner defaults to 20D, Pro remembers (§4)
- **Hierarchical table replaces `Candidates by sector`** (§29), with the Pro column set (§30)
- **Detail drawer** per §31, ending in `[ View Candidates ]`
- **§33 candidate linkage** — routes to Candidates filtered by `sector_id` / `industry_id` /
  `theme_id` / `rotation_horizon`, Market context ribbon retained
- **§34 stock context ribbon** — MARKET / SECTOR / INDUSTRY / THEME / STOCK RS on every
  stock opened from Market. **This is the highest product value in the whole spec** — it is
  what makes the desk top-down rather than a list of tickers.
- **§35 regime-aware emphasis** — CHOP emphasises acceleration, freshness, density; BULL
  emphasises persistence and breadth; RISK-OFF emphasises resilience and deterioration
- Beginner labels EMERGING / LEADING / FADING / WEAK; never "RS-Ratio", "quadrant
  rotation" (§42). Pro exposes percentiles, slopes, numerators/denominators, coverage,
  state-start date, theme confidence, source mapping (§43). Lab exposes raw formula
  outputs, alternate weightings, membership evidence, unvalidated hypotheses (§44).

## 6 · Containment (§10 of the levels handoff still governs)

This screen is a **lens**. It must not become a second ranking.

- Nothing here may reach `deriveState`, `compareCandidates`, or the geometry rule.
- Group state is emitted **nested**, so the compiler enforces separation.
- **Acceptance:** ranked symbol order on Tonight and Candidates is **byte-identical** with
  this screen present and absent, and across all three modes. Paste the empty diff.
- `INFERRED` themes and any unvalidated emergence weighting are **Lab tier**.

## 7 · Acceptance tests (spec §53 + this repo's bar)

1. **Rotation:** strongest / fastest-accelerating / newly emerging / fading answerable in
   under 10 seconds. Screenshot.
2. **Themes:** top 3 active themes, broad vs concentrated, age, leaders — without opening a
   chart.
3. **Multi-horizon:** intraday-only vs short-term emerging vs medium leader vs long-term
   mature, distinguishable from one screen.
4. **Linkage:** one click from a theme opens Candidates filtered to it, regime preserved.
5. **Coverage honesty:** force a group below 0.80 coverage; it must render
   `INSUFFICIENT COVERAGE`, not a number.
6. **Lookahead:** prove 60D/6M group series either use dated membership or are labelled —
   paste the membership dates used for one historical point.
7. **Visual QA (spec §51):** reject if it becomes a wall of coloured cards, the RRG shows
   40 labels, themes mix with sectors without hierarchy, RS shows without acceleration,
   breadth shows without denominator, one-stock themes rank without a warning, bubble size
   has no stated meaning, or candidate count is treated as leadership quality.

## 8 · What NOT to do

- **Do not vendor either RRG repo** (§1). GPL-3.0 and a personal-use licence.
- **Do not composite 60D/6M groups off current membership silently** (§3.2). This is the
  lookahead trap and it looks fine while being wrong.
- **Do not build on the un-normalised index table** (§3.3).
- **Do not synthesise intraday from EOD** (spec §5.1). `Unavailable` is the honest render.
- **Do not create one opaque "Theme AI Score"** (spec §25). `emergence_rank` is composed
  from named, standardised, configurable components.
- **Do not infer themes from company names** (spec §1.3).
- **Do not let candidate count stand in for leadership quality** (spec §51).
- **Do not let this screen change what the desk recommends** (§6).

## 9 · Sequencing against the roadmap

R-0 is independent and can start immediately — it is data hygiene that pays off regardless.
R-1 through R-4 are backend and do not touch any decision surface. R-5 through R-7 are UI.

**This does not jump the queue ahead of the experiment harness** (`STATUS_AND_ROADMAP_2026-09-04.md`
§8, steps 1-3). Rotation intelligence is context for edges that remain unvalidated; if
capacity is contested, the harness wins, because nothing here can be validated without it.
