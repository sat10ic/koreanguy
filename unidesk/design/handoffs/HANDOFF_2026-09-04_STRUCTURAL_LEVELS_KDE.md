# HANDOFF — structural levels (pivot KDE) and the stop-geometry experiment

**Date:** 2026-09-04 · **Author:** Claude Opus 5 (audit/spec role; no code written by this doc)
**Prereq audit:** `AUDIT_2026-09-02_RENDERED_ELEMENT_SWEEP.md` §H and S1-4
**Prior wave:** `HANDOFF_2026-09-03_CORRECTIONS_THRUST_E_F_COMPLETED.md` (verified — see §0)

---

## 0 · Why this exists

The audit's largest finding is still open. Measured on session 2026-09-01:

| | |
|---|---|
| `stop_thrust_days` median | **0.67** |
| below 0.75 ("stop inside normal daily movement") | **37 of 57** |
| at or above 1.5 | **1 of 88** |

The stop is routinely tighter than the stock's own ordinary strong-day expansion, so
positions are closed by normal movement before the idea is tested. Every correction wave
so far has fixed how this is *reported*; none has changed how `invalidation` is *placed*.

The prior wave closed A-4 by refusing to rank sub-1R setups as PRIME
(`status.ts`: `if (c.rr != null && c.rr < 1.0) return "REJECT"`). That is correct and
honest — but it **hides** the bad geometry rather than fixing it. On 2026-09-03,
**21 of 61 candidates carry `rr` null or below 1.0**. A third of the desk is being
rejected for a reason that may be a stop-placement artefact, not a genuine absence of
opportunity.

**Hypothesis:** invalidation is currently derived from a fixed setup rule, not from market
structure. A stop placed just beyond a real shelf of prior pivots would sit further away in
thrust-days *and* be more defensible, improving R:R without widening risk arbitrarily.

**This handoff specifies the experiment that tests that hypothesis. It is not a licence to
change stop placement — see §5.**

## 0.1 · Provenance

The density-of-pivots idea is a clean-room reimplementation from the published description
of `Support & Resistance KDE` by **SatohK** (TradingView, MPL-2.0 header, author requests
contact before non-personal use of the logic — so **reimplement from the description
below, do not transliterate the Pine**). This is the same convention this package already
uses for `detectors/base_pattern.py` (BananaPatterns), `features/activity.py` (Reactor
Scale) and `features/thrust.py` (ADRMAX / ChopScore). Document it in-module the same way.

The algorithm as described: collect confirmed swing pivots over a lookback; for each,
place a triangular kernel centred on the pivot price whose half-width is **that pivot
bar's own high−low range**; sum the kernels across a price grid; take local maxima; keep
the top N separated by at least *k*×ATR.

Two properties make it a good fit here: the bandwidth is **data-derived, not a magic
constant**, and it uses **only confirmed pivots**, so it is point-in-time by construction.

---

## 1 · G-1 · `unidesk/momentum/features/levels.py` (new)

Follow the shape of `features/thrust.py` exactly: module docstring carrying provenance and
parameter rationale, frozen defaults, `ContractError` on bad input, `None` on warm-up
(never 0), windows **exclusive of the current bar**.

```python
PIVOT_LEFT_DEFAULT   = 10
PIVOT_RIGHT_DEFAULT  = 5     # a pivot is CONFIRMED only after this many bars
LOOKBACK_DEFAULT     = 400   # sessions of pivot history
MIN_SEPARATION_ATR   = 1.5
GRID_STEPS           = 100
MIN_PIVOTS           = 8     # below this, refuse — a KDE over 3 pivots is noise
```

Functions:

- `confirmed_pivots(highs, lows, *, left, right, as_of_index)` → list of
  `(index, price, bar_range, kind)`. **A pivot at bar *i* may only be returned once
  `as_of_index >= i + right`.** This is the entire point-in-time contract of the module;
  make it explicit in the signature, not implicit in the caller.
- `level_density(pivots, grid)` → density per grid price, triangular kernel with
  half-width = that pivot's `bar_range`. Skip pivots with non-positive range.
- `structural_levels(highs, lows, closes, atr, *, ...)` → ordered list of
  `Level(price, density, n_supporting_pivots, kind)`; local maxima, filtered to
  `MIN_SEPARATION_ATR × atr` apart, strongest first. `None` when fewer than `MIN_PIVOTS`
  confirmed pivots exist in the window.
- `nearest_below(levels, price)` / `nearest_above(levels, price)` → `Level | None`.

**Do not** invent a confidence score for a level. `density` and `n_supporting_pivots` are
the honest outputs; anything blended is an invented weighting (house rule).

**Acceptance test:** on a hand-built fixture with three pivots clustered at 100.0 and one
outlier at 130.0, `structural_levels` returns the 100.0 cluster first with
`n_supporting_pivots == 3`. Paste the output.

## 2 · G-2 · `unidesk/tests/test_levels.py` (new)

Mirror `test_thrust.py`. Minimum coverage:

1. **No-lookahead (the important one).** A pivot at bar *i* must be invisible to
   `confirmed_pivots(..., as_of_index=i + right - 1)` and visible at `i + right`.
   Build the assertion both ways.
2. **Warm-up refuses.** Fewer than `MIN_PIVOTS` → `None`, never an empty list, never 0.
3. **Determinism.** Two calls on identical input return identical output. No RNG anywhere
   in this module — three of the five scripts reviewed used unseeded `math.random()` and
   were therefore unreproducible.
4. **Separation honoured.** No two returned levels closer than `MIN_SEPARATION_ATR × atr`.
5. **Bad input raises** `ContractError` (unequal series lengths, `left/right < 1`).
6. **Register in `test_truncation_invariance.py`.** Every new public callable under
   `features/` must have a REGISTRY entry — `structural_levels` and `level_density` are
   windowed series functions and belong as `kind='series'` with a real truncation check.
   **This is not optional**; the thrust wave shipped without it and the guard caught it
   three days late.

**Acceptance test:** `pytest unidesk/tests/test_levels.py unidesk/tests/test_truncation_invariance.py -q` green. Paste it.

## 3 · G-3 · Emit, but do not act on it yet

Wire into `momentum/scan.py` and `momentum/report_json.py` alongside the thrust fields:

| Field | Meaning |
|---|---|
| `support_level` | nearest structural level strictly below `close` |
| `support_distance_pct` | `(close − support) / close × 100` |
| `support_thrust_days` | that distance ÷ `adr_max_pct` — comparable to `stop_thrust_days` |
| `support_pivots` | supporting pivot count |
| `resistance_level` | nearest level strictly above `trigger` (headroom to target) |
| `resistance_thrust_days` | same normalisation |

All `null` when unavailable — 31 of 88 names lacked `adr_max_pct` on 09-01, so the
thrust-normalised variants will be null at a similar rate. Never substitute ADR.

**Do not change `invalidation` in this step.** Emit only; §4 decides whether it earns the
right to influence placement.

**Acceptance test:** regenerate the newest report; paste `support_level`,
`support_thrust_days` and `support_pivots` for three symbols, hand-checked against the
bhavcopy pivots. Confirm the null rate is reported, not hidden.

## 4 · G-4 · The experiment (the actual point)

**Gate: run only on an archive that is on one corporate-action basis.** As of the last
audit, 393 of 1,570 partitions were on a stale or rejected basis (B2-3). Running this on a
mixed-basis archive produces confident nonsense. **Verify B2-3 is complete before starting
and paste the hash tally.**

For every archived event with derivable geometry, compute a **counterfactual structural
stop**: `nearest_below(levels, trigger)` minus a small buffer (state the buffer; a fraction
of ATR is defensible, an arbitrary rupee amount is not). Then re-run the **existing**
stop-aware labeller — do not write a second one — and compare:

| Metric | Current rule | Structural stop |
|---|---|---|
| median `stop_thrust_days` | 0.67 | ? |
| share below 0.75 | 65% | ? |
| median R:R | 1.13 | ? |
| stopped-out rate | ? | ? |
| reached +1R rate | ? | ? |
| **events with no level available** | n/a | ? (fail-closed count) |

Report **coverage alongside quality** — a structural rule that only fires on 30% of events
is a different product from one that fires on 90%, and the comparison is meaningless
without it.

Use the existing machinery: `research/experiments.py::compare_edge()` and
`research/significance.py` for deflated Sharpe. **Do not hand-roll a significance test.**
Apply the same-symbol embargo (`leakage.embargo_overlapping_events`) and walk-forward
folds — this is a cross-sectional comparison over the same events, so the embargo matters
for the significance estimate even though both arms see identical entries.

**Kill criterion, written before you look at the result:** if the structural stop does not
raise median `stop_thrust_days` above 1.0 **while holding median R:R at or above the
current 1.13**, it is rejected and the finding is recorded as negative. A wider stop that
merely lowers R:R is not an improvement — it is the same trade with more risk.

**Acceptance test:** paste the full table above plus the DSR result and the coverage
figure. A negative result is a valid, publishable outcome — record it on the Research
screen's negative-findings board either way.

## 5 · G-5 · Only if §4 passes

- Draw levels on the Stock chart (`StockChart.tsx` already renders trigger/invalidation
  lines — reuse that path), shaded by density, labelled with supporting pivot count.
- On the candidate card, a chip reading whether the current invalidation sits **inside** or
  **beyond** the nearest structural support. Descriptive only.
- Charter constraint: *"No model output may author a stop, a size, or a risk number."* A
  deterministic, documented rule proposing a level is the same class as the existing
  geometry rule and is acceptable; a *score* that ranks stops is not. Keep the level and
  the decision separate — the desk shows structure, the owner places the stop.
- Class guard (F-7): add a published invariant that a rendered `support_level` is always
  strictly below the close it is attached to, and `resistance_level` strictly above.

---

## 6 · Follow-on, gated: regime-conditioned geometry distributions

From `MFE (Market Fractal Entropy)`, same author, same clean-room rule. The idea worth
taking: classify structure into four quadrants (HH-HL / HH-LL / LH-HL / LH-LL), keep
per-quadrant distributions of swing features, and score how *surprising* the current swing
is using a robust z (median + MAD × 1.4826, tanh-clipped).

Why it fits: it is distribution-based and deterministic, so it satisfies the constitution's
**"engineered vectors only — no neural network"**, and you already classify BULL/BEAR/CHOP
and hold 1,570 archived sessions with stop-aware outcomes. It would answer a question the
desk cannot currently answer: *is this base unusual for bases that worked in this regime?*

**Two defects in the source; do not reproduce them:**

1. **Empty-quadrant argmin.** Its `calc_directional_info` returns `0.0` when a quadrant has
   fewer than 10 samples, and the selector then picks the quadrant with **minimum** total
   absolute information. An unpopulated quadrant scores 0 and therefore always wins. Any
   port must require a populated distribution before a quadrant is eligible, and return
   `None` when none qualifies.
2. **Sample starvation.** Four quadrants × five features needs far more pivots than a
   single chart provides. Your archive can support it; a per-symbol version cannot. Build
   it cross-sectionally or not at all.

**Do not start this until §4 has produced a result.** One experiment at a time, with a
stated kill criterion, is the discipline that keeps the ladder honest.

---

## 7 · What NOT to do

- **Do not transliterate the Pine.** Reimplement from the description in §0.1; the author
  asks for contact before non-personal use of the logic.
- **Do not run §4 on a mixed-CA archive.** Verify B2-3 first.
- **Do not change `invalidation` before §4 returns.** Emit, measure, then decide.
- **Do not add a neural network.** The constitution's first constraint row is "Engineered
  vectors only — no neural network", the Phase 0 gate is open on 9 FAIL items, and L1.5
  (`research/analogue.py`) is built but still untested.
- **Do not skip the truncation registry entry** (§2.6).
- **Do not tune the kill criterion after seeing the result.**

## 8 · Two smaller harvests, not worth their own wave

- **Multi-lag feature stack for `research/analogue.py`.** The KNN script encodes the same
  indicator at *t*, *t−10*, *t−20*, so the neighbour match is on a *trajectory* rather than
  a point. Your analogue vector is a point snapshot. Adding lagged copies of two or three
  existing dims is a small, testable change; measure it with the existing retrieval
  evaluation before keeping it.
- **Normalisation hygiene, already correct here.** Two of the reviewed scripts normalise
  with `ta.sma(src[1], len)` — excluding the current bar from its own baseline — while the
  ANN script includes it. Your `thrust.py` already uses exclusive windows. No action;
  recorded so the next reader does not "fix" it in the wrong direction.

---

## 9 · Carried forward from the previous wave (verified 2026-09-04)

The reliability bar (PART F of
`HANDOFF_2026-09-02_CORRECTIONS_AND_THRUST_UI.md`, spec in
`SAAS_READINESS_2026-09-03.md`) is **6 of 7 done**. Verified from the tree, not from
commit messages:

| | Status | Evidence |
|---|---|---|
| F-1 CI | ✅ | `.github/workflows/unidesk.yml` runs pytest, `run_checks.py`, `npm run build`, playwright |
| F-2 error boundaries | ✅ | `src/components/ui/PanelBoundary.tsx` |
| F-3 smoke tests | ✅ | `playwright.config.ts` → `unidesk_terminal/tests/smoke.spec.ts` |
| F-4 durable register | ✅ front | `Desk.tsx` `exportRegister()` / import, defensive `localStorage` reads (F-4.1/F-4.2). Server-side persistence (F-4.3) not confirmed |
| F-5 bundle split | ✅ | route-split landed in `14c26d31`; before/after chunk sizes not independently checked |
| F-6 repo hygiene | ❌ **not started** | see below |
| F-7 class-level guards | ✅ | three new invariants: `check_setup_sections_cover_detectors`, `check_dated_bundles_sorted_newest_first`, `check_no_hardcoded_status_prose` |

**F-7 deserves a note:** those three guards are exactly the class-level fixes the audit
asked for — a finding is now closed by something that *fails when it regresses*, not by a
paragraph. That is the mechanism that stops audit #12. **Every new finding from §4 of this
document must land the same way.**

### F-6 is the only reliability item left, and it is getting worse

Measured 2026-09-04:

```
git status --porcelain   -> 303 lines (260 untracked)
git ls-files | node_modules -> 5,296 tracked files
```

`node_modules` is still committed under `manas_os/terminal/`, and roughly 260 untracked
files sit at the repo root (`api_restart*.log`, `_agrec_*` dumps, screenshots,
`scratch_diag*.py`, `manas.db`, a file named `=`).

This is not cosmetic. **An unreadable `git status` is why three sessions of work once sat
with no restore point**, and it slows every CI checkout (F-1 now runs on push). The full
spec is F-6 in the previous handoff. Summary:

1. `git rm -r --cached` the committed `node_modules`; add to `.gitignore`.
2. Extend `.gitignore`: `*.log`, root `*.png`, `_agrec_*`, `scratch_*`, `_diag_*`, `*.db`,
   `tmp_*`, `=`.
3. `git gc --prune=now`.
4. **Ignore, do not delete.** `manas.db`, `traderlog/data/*.db` and `output/` may be real
   data. List anything you were unsure about rather than removing it.

**Acceptance test:** `git status --porcelain` drops below ~20 lines on a clean tree, and
tracked `node_modules` files reach 0. Paste before/after counts.

### Ordering against this document

F-6 is independent of §1-§5 and touches no unidesk code — it can run in parallel, by a
different agent, in its own commit. It is **not** a prerequisite for the levels work.

### Also still open, from the audit rather than PART F

- **B2-3** — archive corporate-action remediation. 393 of 1,570 partitions on a stale or
  rejected basis at last check. **This one IS a hard gate on §4** (see the gate note
  there). Re-verify the hash tally before starting the experiment; it may have been run
  since.
- **The stop-geometry defect itself** — audit §H. That is what this document exists to
  address.
