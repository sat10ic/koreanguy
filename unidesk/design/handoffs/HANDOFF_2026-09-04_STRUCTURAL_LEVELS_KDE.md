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
- **Do not let a label share a bar with its own features.** See §8.3 — this is the defect
  that made the reviewed ANN script a lagging summary rather than a forecast, and it is
  subtle enough to survive code review. Every label in §4 comes from the existing
  stop-aware labeller, which already enforces it; do not hand-roll an alternative.

## 8 · Three smaller harvests, not worth their own wave

- **Multi-lag feature stack for `research/analogue.py`.** The KNN script encodes the same
  indicator at *t*, *t−10*, *t−20*, so the neighbour match is on a *trajectory* rather than
  a point. Your analogue vector is a point snapshot. Adding lagged copies of two or three
  existing dims is a small, testable change; measure it with the existing retrieval
  evaluation before keeping it.
- **Normalisation hygiene, already correct here.** Two of the reviewed scripts normalise
  with `ta.sma(src[1], len)` — excluding the current bar from its own baseline — while the
  ANN script includes it. Your `thrust.py` already uses exclusive windows. No action;
  recorded so the next reader does not "fix" it in the wrong direction.

### 8.3 · Calibrated uncertainty on analogue retrieval (from the ANN script)

The `Deep Machine Learning [SatohK]` ANN is **rejected** (§7) — but one idea in it is worth
keeping, in a form that does not require the network.

It attaches an uncertainty band to its output via MC Dropout: run the forward pass N times
with dropout on, take the spread. The *idea* — never publish a call without saying how
confident it is — is right. The *implementation* is weak: MC Dropout measures the model's
disagreement with itself, not its correctness, so a confidently wrong model shows a tight
interval. That script also has no accuracy metric anywhere, so nothing checks the band
against reality.

**The honest version, and where it belongs:** `research/analogue.py` (L1.5) already returns
the outcomes of the k nearest historical analogues. That is a *sample*, so it supports a
real interval with **measured coverage** — e.g. "of 25 nearest analogues, 11 reached +1R;
80% interval [x, y], coverage verified at z% on held-out folds" — via conformal prediction
or a plain bootstrap over the neighbour outcomes.

This satisfies two constitution constraints that MC Dropout would not:

- **§20 sample count always attached** — the n is intrinsic to the method.
- **§22 similarity is never shown as a probability** — a coverage-stated interval over
  realised neighbour outcomes is an empirical frequency with its uncertainty declared, not
  a model-authored probability. Keep that distinction in the wording on any surface: report
  what happened to similar setups, never "chance of success".

**Gate:** L1.5 retrieval is built (`research/analogue.py`, 11 constraint tests) but has
**never been evaluated for edge**. Calibrating an interval around an unvalidated retrieval
is polishing an unmeasured thing. Do this only after L1.5 has a measured result, and never
before §4 of this document returns.

**Acceptance test, when it is time:** on held-out folds, the stated interval must contain
the realised outcome at approximately its nominal rate. If nominal 80% delivers 55%
coverage, the interval is decoration and must not ship.

### 8.4 · The transferable rule from the ANN, worth more than the harvest

The reviewed script hardcodes `predict_period = 0`, so for two of its three targets the
label is the direction of **the same bar the features come from** — the indicators are
functions of that bar's close, and the label is that bar's close versus its open. It
learns to restate the present. Its "prediction" line is a lagging summary, and nothing in
the script surfaces that.

**The rule:** a label must be strictly in the future relative to every input that produces
it, and the gap must be explicit and asserted, not a parameter someone can quietly set to
zero. Your archive already enforces this with exclusive windows and stop-aware outcomes —
which is exactly what that script lacks. Recorded because the failure is silent: the model
trains, converges, and reports confidence, while forecasting nothing.

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

---

## 10 · Containment: keep experimental work out of the working desk

**Owner directive, 2026-09-04:** these ideas must not be able to disturb the desk that
currently works. This section is binding on §3, §5, §6 and §8, and should be lifted into
`UI_BUILD_SPEC_V1.md` once adopted — it is general policy, not levels-specific.

### 10.1 · The risk is authorship, not visibility

The danger is not that a new number appears on screen. It is that a new number silently
**influences a decision**. Today the decision surface is small and explicit:

- `lib/status.ts::deriveState` — accepts a narrow structural type:
  `close, trigger, stockStrength, stock_quality, rvol, rsRank, rr`. Nothing else.
- `lib/candidates.ts::compareCandidates` — `deriveState`, `triggerDistPct`, `rsRank`, symbol.
- the backend geometry rule that sets `trigger` / `invalidation`.

**Those three are the protected surface.** Anything that reaches them changes which trades
the owner takes.

So the classification line is **does it author a decision**, not **is it new**:

| | Where it belongs |
|---|---|
| Descriptive context (ADRMAX, ChopScore, stop-in-thrust-days) | Main desk, with provenance. Already shipped, already correct — **do not rip these out**; they describe, they do not decide. |
| A level *drawn on a chart* (§5) | Main desk, descriptive, provenance-labelled. |
| A level *changing `invalidation`* (§4) | Protected surface — requires §4 to pass its kill criterion first. |
| Analogue retrieval, uncertainty intervals, regime-surprise scores (§6, §8.3) | **Lab only**, always. |

### 10.2 · A ladder, not a third parallel mode

Extend the existing toggle rather than adding a second axis:

```ts
export type Mode = "beginner" | "pro" | "lab";   // monotonic: beginner ⊂ pro ⊂ lab
export function atLeast(mode: Mode, floor: Mode): boolean
```

`lab` is Pro vocabulary **plus** unvalidated surfaces. Monotonic because a tier that is a
strict superset is one thing to reason about; two orthogonal booleans is four states, three
of which nobody has thought about. Default `beginner`, persisted like the theme.
`ModeContext.tsx` already carries `mode`/`setMode` — this is a type widening plus a
three-way control, not new plumbing.

**Lab is never the default and never persists across a data reset.** If the owner is in
Lab, the top bar says so unmissably — an unvalidated surface must never be mistaken for
the desk.

### 10.3 · Structural separation — let the type system do the work

Emit experimental fields **nested**, never flat on the candidate:

```jsonc
{ "symbol": "...", "close": 1, "trigger": 2, "rr": 1.4,
  "experimental": { "support_level": 1180.5, "support_pivots": 4, "analogue": { } } }
```

Mapped to `Candidate.experimental?: {...}` in the UI.

This is the cheapest guard available: `deriveState` takes a **flat** structural type, so a
nested field **cannot** be passed to it without someone deliberately destructuring it out.
The compiler enforces containment; nobody has to remember a convention.

`support_level` in §3 is emitted under `experimental` until §4 returns. If §4 passes, it is
**promoted** — moved flat, with the experiment result cited in the commit. Promotion is a
deliberate, reviewable act.

### 10.4 · The machine-checked guard (F-7 pattern)

Conventions rot; invariants do not. Add to `checks/published_invariants.py`:

**`check_experimental_fields_not_in_decision_path`** — parse `lib/status.ts` and
`lib/candidates.ts`; fail if any key under `experimental` in the newest report appears in
`deriveState`, `compareCandidates`, or the ranking key. Prove it fires: temporarily
reference an experimental field in `deriveState`, confirm the check fails, revert, paste
both runs.

**`check_experimental_surfaces_labelled`** — every experimental field rendered anywhere
must sit inside a component carrying a tier badge. Enforce via a smoke assertion (F-3) if
static parsing is brittle.

### 10.5 · Honest labelling

Reuse the existing detector-trust vocabulary rather than inventing a second one — the desk
already renders `REVIEW_REQUIRED` / `BLOCKED` chips with reasons.

Every Lab surface carries a badge stating tier and **why**: *"EXPLORATORY — computed and
unit-tested; no measured edge. See HANDOFF_2026-09-04 §4."* Never a bare "beta".

Constitution §22 still applies inside Lab: similarity is not a probability, and a retrieval
result reports **what happened to similar setups**, never "chance of success".

### 10.6 · Acceptance tests

1. In Beginner and Pro, **no experimental field renders anywhere.** Screenshot both.
2. In Lab, every experimental surface carries a tier badge naming its status and reason.
3. `deriveState` and `compareCandidates` produce **byte-identical output** in all three
   modes for the same report. Paste a diff of the ranked symbol order across modes — it
   must be empty. *This is the test that actually matters.*
4. The two invariants above are green, and each has been proven to fire on a planted defect.
5. Turning Lab on and off does not change the candidate list, the ranking, or any
   trigger/invalidation value.

### 10.7 · What this does not license

- Lab is **not** a place to park unfinished work. Charter: *"No dormant code — a module
  ships only if it is wired into a pipeline AND surfaced in the UI."* Lab satisfies
  "surfaced"; it does not excuse a half-built feature.
- Lab is **not** a way to show a number that has no honest interpretation. If it cannot
  carry a truthful badge, it does not ship in any tier.
- Lab does **not** relax point-in-time discipline, the truncation registry (§2.6), or the
  no-fabricated-values rule. Same engineering bar; lower *claim*.
