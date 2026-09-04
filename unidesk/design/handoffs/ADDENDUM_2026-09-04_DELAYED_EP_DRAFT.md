# ADDENDUM — Delayed EP sub-section (SPEC DRAFT — owner decisions D1–D3 pending)

**Date:** 2026-09-04 · **Author:** GLM-5.3-Flash (spec role; no code written by this doc)
**Extends:** `HANDOFF_2026-09-04_EVENT_TRACK_IPO_EP.md` §4/§5 (EP track) · governed by
`HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §10 (containment)
**Lane note:** event track is Sol's lane; this document plans the sub-section for the
owner's approval. Implementation is re-laned by the owner after D1–D3 are answered.
**Attribution-ID:** attr-unidesk-delayed-ep-addendum-glm53flash-20260904-001

---

## 1 · What "delayed EP" means here (the evidence)

The desk's EP detector (`detectors/ep_signature.py`) already carries the hook: its
`EPDecision.circuit_ep` field is commented *"locked day — delayed-list candidate"*, and a
locked day's `close_location` component is marked uninformative. Nothing downstream
consumes that flag. So the concept is anticipated but unimplemented — and the current
scoring actively disadvantages delayed repricers:

- `gap_significance` is linear in single-day `gap_pct` (5% → 0, 12%+ → 100). A name that
  reprices via three successive 5% circuit locks shows ~5% on each day and never scores.
- `close_quality` is skipped on locked days by the `circuit_ep` guard, so the decisive
  sessions contribute *nothing* instead of contributing their locked-but-real signal.

A delayed EP is therefore: **a catalyst-driven repricing that completes over k sessions
instead of day 0** — typically circuit-locked runs on illiquid NSE names, or slow
digestion of a complex result. Today these are either invisible (scored below threshold)
or silently mishandled (locked days half-ignored).

## 2 · Candidate definitions (owner decision **D1**)

| | Definition | What it claims | Risk |
|---|---|---|---|
| **A** | **Circuit-stalled repricing** — catalyst announcement (E-2) + ≥2 consecutive locked/sessions where the close keeps making new post-announcement highs; day 0 = first locked session | These are real EPs the gap-day detector misses entirely | New detector behaviour; needs its own trust verdict |
| **B** | **Late confirmation** — day-0 gap holds (never loses gap low), then the *setup* matures k sessions later on the first close above the day-0 high | The existing EP geometry, shifted later | Arguably already covered by `episodic_pivot` + base stage; may not be a new object at all |
| **C** | **Slow-discovery** — the announcement was knowable but the market's reaction begins >1 session later without locks | Catches names the market under-reacted to | Hardest to distinguish from ordinary drift; highest leakage-audit burden |

**Recommendation: A first.** It is the case the detector already stubs, the one the
E-3 circuit-band work directly feeds, and the one where the current scoring is provably
blind. B can be evaluated as a variant of the existing detector's base-stage logic before
building anything. C is parked unless the owner insists.

## 3 · The anchor rule (owner decision **D2**)

Every event-relative feature needs day 0, and for a delayed EP the candidates are:

- **(i) announcement-knowable session** — first session at/after the announcement's
  `available_at` (the E-2 rule). Most honest; earliest; may precede any movement.
- **(ii) first movement session** — first session the stock actually reprices (first
  locked session or first gap). Measures from market behaviour, not filings.
- **(iii) completion session** — when repricing ends. Measures the *setup*, not the
  event; risky because completion is only knowable in hindsight (look-ahead by design).

**Recommendation: (i) for catalyst-relative features** (`days_since_catalyst`,
`sessions_since_announcement`) **and (ii) for price-structure features**
(`sessions_into_repricing`, `held_above_run_low`). Never (iii) as an anchor — completion
is an *outcome* field, computed only after it happens, and is the label side, not the
feature side. This preserves §8.4's transferable rule: features as-of T may only see bars
≤ T; completion is by construction a later fact.

## 4 · Feature set (extends `event_relative.py`; registry mandatory)

All frozen constants in-module; `ContractError` on bad input; `None` on warm-up; windows
exclusive of the current bar; every public callable registered in
`test_truncation_invariance.py`.

Shared: `sessions_since_event` on the trading calendar (already specced in the event track).

Delayed-EP specifics (definition A):

- `repricing_completion_pct` — total move from pre-announcement close ÷ sum of completed
  daily moves; distinguishes "repricing finished" from "still in progress".
- `consecutive_locked_sessions` / `locked_session_ratio` — from E-3 bands; the intensity
  of the delayed repricing.
- `sessions_to_gap_completion` — (ii) anchored; **outcome-side, never a feature at
  decision time** (see §3).
- `held_above_run_low` — the survival test, anchored to the lowest locked-session low.
- `post_run_base_depth` — consolidation after the run completes, relative to the run.
- `catalyst_type` / `days_since_catalyst` — from E-2; a delayed EP *requires* a catalyst
  match within the window, else it is not an EP (absence → `catalyst: null`, per the
  event track's absence rule).

## 5 · Detector and trust implications (owner decision **D3**)

- **Recommendation: a separate detector identity** (`episodic_pivot_delayed`) rather than
  a flag on `episodic_pivot`. Reasons: (a) detector trust is per-detector — the delayed
  variant must ship `REVIEW_REQUIRED` and must not ride `episodic_pivot`'s VERIFIED
  status, exactly as the event track protects `ipo_base`'s BLOCKED verdict; (b) its
  geometry differs (locked days), so its candidates are not interchangeable; (c) one
  validated detector per hypothesis keeps the S-1 verdicts attributable.
- Until validated through the harness (S-1, then a real run on the single-basis archive),
  the variant is **Lab tier** under KDE §10: nested `experimental` fields, tier badge,
  never in `deriveState`/`compareCandidates`, containment tests byte-identical.
- Trust flip to rankable is an **owner decision**, same rule as `ipo_base`.

## 6 · Data prerequisites and ordering

1. **E-2 announcements** (Sol's long pole) — the catalyst match is what makes it an EP.
   Without E-2 this sub-section cannot run at all.
2. **E-3 step 1** exact locked check (`high == low == close`, or ±2/5/10/20% within one
   tick) — the `consecutive_locked_sessions` feature is only as honest as the lock test.
3. **S-1 harness** — validation path for the variant's trust verdict; also the source of
   the delayed-EP acceptance test: on fixtures, a three-locked-session repricer must
   score non-trivially where the current detector scores ~0 on `gap_significance`.

## 7 · What I need from the owner (the rules I will not invent)

- **D1** — which definition (A/B/C) is the edge claim. Recommend A.
- **D2** — anchor rule per feature family. Recommend (i)+(ii) split, never (iii)-as-feature.
- **D3** — separate detector identity vs flag. Recommend separate, REVIEW_REQUIRED at birth.
- **D4** — the delay bound k (repricing must complete within k sessions to count as one
  event). This bounds every warm-up and the backtest eligibility. It is a trading-intent
  number; frozen in-module with its rationale stated, sensitivity-noted like
  `thrust.py`'s parameters — but the value itself must be the owner's.
- **D5** — lane: implement inside Sol's event track, or re-lane to GLM. Spec says Sol;
  no conflict as long as one agent owns it.

## 8 · Validation and kill criterion (draft, frozen before any result)

Validated through S-1 on the single-basis archive once B2-3 lands: delayed-EP events vs
the same events scored by the current detector, coverage alongside quality (how many
events the delayed rule sees that the current one misses — that coverage gap IS the
hypothesis). Draft kill criterion for the owner to amend **before** measurement: the
delayed variant must surface ≥25 events the current detector misses across the archive,
and their realised outcome distribution must not be worse than the detector's current
candidates' base rate; otherwise the sub-section is recorded as a negative finding and
the `circuit_ep` flag remains a descriptive note only.
