# AI integration exploration — L1.5 analogue retrieval (A-02) — prototype notes

**Date:** 2026-09-02 · **Directive:** owner asked to "start exploring the AI
integration". This document and the accompanying prototype honour both that
directive and the gate: **the Phase 0 gate is open** (A-01 audit: 9 FAIL
items), so nothing here is surfaced in any user-facing screen and no edge
claim is made. This is constraint-compliant exploration — evidence
gathering, not product.

**Artifacts:** `unidesk/research/analogue.py` (prototype),
`unidesk/tests/test_analogue.py` (11 constraint tests, all passing),
plus a live smoke run against the real event store (results below).

## Constraint compliance matrix (A-02 hard constraints)

| Constraint (UI_BUILD_SPEC_V1 A-02 / Constitution) | Status in prototype |
|---|---|
| Engineered vectors only — no neural network | ✅ Deterministic flatten of `n5_inputs` + snapshot fields |
| Cosine distance ONLY (§10) | ✅ `cosine_distance()`; no other metric implemented |
| k = 25 or 50 ONLY (§10) | ✅ `ALLOWED_K == (25, 50)`; `retrieve()` raises otherwise (tested) |
| Same-symbol embargo wired (`leakage.embargo_overlapping_events` — previously built, unused) | ✅ Applied before ranking; embargo count reported on every result |
| Max 20% of neighbours from one cell (§6.3) | ⚠️ Week-half implemented and enforced; **industry-half PENDING** the universe sector join — named, not faked |
| Point-in-time normalisation, no full-sample z-scores (§6.4) | ✅ Rank-normalisation reference = corpus events STRICTLY OLDER than the query |
| Vector dims (§7) | ✅ Mapped with documented drift: gap_pct, close_loc, rvol (constitution says rvol_20 — store carries rvol), prior_atr_percentile, S_ep (mapped to tightness score), base_depth, RS, adr (liquidity proxy), market_regime (joined from the archived breadth series). Missing dims excluded pairwise and renormalised — never zero-filled. |
| Sample count always attached (§20) | ✅ `RetrievalResult.sample_size` + per-bucket distribution |
| Similarity never shown as probability (§22) | ✅ Similarity is an internal retrieval quantity; the result type carries outcomes, not confidence |

## Live smoke run (real data, 2026-09-02)

- Query: one labelled event from partition `date=2014-08-06` (r_multiple present, n5_inputs present).
- Corpus: the full event store (regen partitions 2010→2014 carry BOTH
  vectors and labels).
- Result: retrieval executed end-to-end with embargo and PIT scaling; the
  distribution/median-R numbers are deliberately left unquoted in this
  document — quoting them would risk reading as an edge claim before the
  gate review. They are reproducible via the module.

## Key exploration finding (store gap)

The store had **two disjoint event generations**: pre-regen partitions carry
outcome labels but no `n5_inputs` vectors; the fresh nightly partitions carry
vectors but no labels yet (10-bar horizon). The in-flight full-archive regen
(`run_archive_attach` / resume) is closing exactly this gap — its partitions
(2010→2014 verified) carry BOTH. Until it completes, retrieval has a corpus
only over the regenerated range. This is the concrete data prerequisite A-02
waits on, now measurable: sessions with vectors+labels = the regen's progress
counter.

## What stands between exploration and A-02 eligibility

1. Phase 0 §53 gate review (A-01 audit: 9 FAIL rows — manifests, identity
   model, PIT membership, deterministic rebuilds).
2. Archive regen completion (B-04) so the vector+label corpus spans 2010→2026.
3. Industry-half of the §6.3 concentration cap (sector join at event level).
4. A frozen evaluation protocol (§19 promotion rule inputs) BEFORE any
   holdout is touched.

Until all four hold, A-02 stays BLOCKED-as-product; this prototype is the
reusable, constraint-checked starting point.
