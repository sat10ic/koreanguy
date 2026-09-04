# INJECTION — outcome semantics wave (paste into the running loop)

**Do not restart the loop. Do not re-plan the graph. Finish the node you are on, record it
normally, then apply this at your next step 1.**

---

## What already happened without you (do not redo it)

- `unidesk/design/BUILD_GRAPH_2026-09-04.md` gained **§9 · ADDENDUM 2** — nodes N-50..N-60.
- `unidesk/design/BUILD_STATE.json` already contains N-50..N-60 as `TODO`. **Registered.
  Do not re-register, do not renumber anything, do not touch N-0..N-49 ids.**
- `N-11`'s `note` field is already amended with its new blocker.
- The source review is now in the repo at
  `unidesk/design/reviews/tonight_page_review_outcome_model.md`. §-numbers in §9 refer to
  **that file**. Read it before N-53, N-56, N-57, N-59, N-60 — those nodes are specified by
  section reference, not restated in full.
- Commit `166c6271`.

## Rule 1 — the hard dependency, and it overrides your queue order

**N-11 is now blocked on N-50, N-51 and N-52.** N-11 is still `TODO`, so nothing is
retroactive — but if you reach it before N-52 is `DONE`, every experiment verdict is
computed on a superseded outcome basis and must be thrown away. This is the same failure
mode as the B2-3 CA-basis rewrite. It cost hours once.

**Priority override to §1 step 2:** the "lowest-numbered eligible TODO" rule would run
N-50..N-52 last. Do not follow it here. **N-50 and N-51 have no dependencies and become the
highest-priority eligible nodes the moment your current node is recorded.** Order:

```
N-50, N-51  ->  N-52 (needs N-0 DONE)  ->  then resume normal queue order
```

N-53..N-60 are UI/semantics work with no experiment coupling. Leave them in normal queue
order; they block nothing.

## Rule 2 — one thing in the review is already solved. Do not "fix" it.

`research/labels.py:89-98` **already forbids the optimistic within-bar assumption** and says
so in its own docstring:

> "OHLC cannot determine intrabar ordering, so a bar which both reaches a target and touches
> the stop must never be recorded as a captured positive R." / "Optimistic-by-default is
> forbidden."

The review's `PATH_AMBIGUOUS` concern is therefore **already handled within a bar**, by the
conservative policy the review itself lists as acceptable (§14). **Do not rewrite this
logic. Do not relax it.**

**The actual gap is across bars:**

- `r_multiple` is **stop-dominant** — `stop_hit = any(lo <= stop for lo in l)` spans the
  whole horizon, so +1.8R on bar 2 followed by a stop on bar 9 is labelled **−1R**.
- `potential_r_multiple` is **stop-blind** — MFE over the whole horizon, including moves
  after the stop would have fired.

Neither answers *"did +1R arrive before −1R"*. So the desk cannot currently distinguish
**"the setup failed"** from **"the setup worked and gave it back."** That is what N-50 adds.

**`r_multiple` is not wrong and must not change.** It correctly answers "fixed-stop position
held to the horizon." N-50 is an added dimension beside it, never a replacement. If your
diff modifies the value of `r_multiple` or `potential_r_multiple` for any existing event,
you have built the wrong thing — revert and re-read this section.

## Rule 3 — new escalations, append to §4

| # | Decision | Why it is not yours |
|---|---|---|
| E8 | Changing the review horizons in N-51 **after** observing performance on them | that is fitting the measurement to the result; horizons are frozen config, owner-gated to change |
| E9 | Changing the R thresholds that define `WORKED` (+1R) or `WIN` (+2R) | they define what the desk means by "worked"; owner-gated like the CHOP wording (E4) |

**E4 extends to N-56 and N-58.** Plain-language translations must be **descriptive, not
advisory** — describe what a number measures, never what the reader should do about it. "MFE
= the best move after entry" is fine. Anything resembling "so take profit here" is E4 and
you may not author it.

## Rule 4 — standing rules that this wave will tempt you to break

- **§2.1 never fabricate.** N-53 exists precisely because four different causes currently
  render as one em dash. Adding the four states must not add a fifth behaviour where a
  missing value acquires a number.
- **§2.4 no invented composites.** N-54's confidence labels are **coverage counts and n**,
  not a blended reliability score.
- **§2.3 truncation registry.** N-50 adds public callables under `research/` — if any land
  under `features/`, `primitives/` or `scoring/`, they need a `test_truncation_invariance.py`
  REGISTRY entry. The thrust wave shipped without one and the guard caught it three days
  late.
- **§2.5 no dormant code.** N-50's states must reach the UI (N-55) or they are not shipped.
- **RAM.** N-52 is an archive rewrite of the same weight class as B2-3. **Never run it
  beside a live archive job.** Check for a running N-0 job from persisted artefacts on disk
  before starting — not from process absence.

## Rule 5 — done-conditions worth restating, because they are easy to fake

- **N-50:** hand-built fixture. `+1.8R on bar 2, stop on bar 9` returns `WORKED`.
  `stop on bar 1` returns `STOPPED`. **Both still report `r_multiple = −1R`.** Paste both
  outputs. A node is not DONE because the states exist — it is DONE when that fixture
  discriminates.
- **N-51:** horizons readable from versioned config, not literals in the labeller.
- **N-52:** every partition carries the new `outcome_basis_version`; state-tally reported
  before and after. Same evidence bar as B2-3.
- **N-55:** all 8 states with counts. **No average printed without stating what entered its
  denominator.**
- **N-57:** ranked order byte-identical across Beginner/Pro/Lab (§10.6). Density changes
  what is shown, never what is ranked.
- **N-60:** applied filters listed explicitly, with a `Clear lens` control. A lens that
  changes results without showing what it changed is an opaque action and fails the node.

## Then

Resume §1 step 1. Report per §6. If N-50's fixture reveals that the existing labeller is
wrong in a way this document did not predict, that is a **finding — record it and continue**;
it is not a halt condition.
