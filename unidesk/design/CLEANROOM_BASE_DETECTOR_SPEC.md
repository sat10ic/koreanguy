# Spec: Clean-room daily base-pattern detector

## Objective

Build a storage-neutral, deterministic detector that derives a defensible
base-and-breakout description from daily OHLCV data: `baseStart`, `pivot`,
`depth`, `coil`, `dry`, relative-strength rank, chart annotations, and
lifecycle verdict. It is a clean-room approximation of public
BananaPatterns behavior, not a claim of identical proprietary logic.

The primary acceptance target is to reproduce the publicly disclosed metric
definitions and the YASHHV public calibration case without look-ahead. Any
rule that is not disclosed must be configurable and labelled as a heuristic.

## Evidence and assumptions

- Public client definitions establish: base duration is trading sessions/5;
  depth is the pivot-to-low percentage; `coil` is second-half ATR% divided by
  first-half ATR%; `dry` is second-half volume divided by first-half volume;
  `dryDepth` is quietest-day volume divided by the base median volume.
- The public guide establishes a 1--99 cross-sectional trailing-performance
  rank, not the undisclosed lookback/weighting formula.
- Daily bars are complete EOD data ordered by session. The detector must not
  use a pivot before its confirmation lag, and annotations that need later
  confirmation must declare that fact.

## Public interface

`unidesk.momentum.detectors.base_pattern` will expose:

- `DailyBar`: validated input bar.
- `BaseRules`: explicit parameters, including pivot confirmation lag,
  minimum base length, rebase maturation, maximum depth, and breakout
  freshness. RS lookbacks and weights are parameters of the rank function.
- `BaseVerdict`: `WATCH`, `BREAKOUT`, `RUNNING`, `EXITED`, or
  `INSUFFICIENT_DATA`.
- `BasePattern`: the immutable detector output and chart annotations.
- `detect_base_pattern(bars, rs_rank=None, rules=...)`.
- `relative_strength_ranks(closes_by_symbol, lookbacks=..., weights=...)`.

## Algorithm boundary

1. Confirm swing highs with a symmetric fractal window; a high becomes usable
   only after the right-side confirmation bars exist.
2. Treat the session after every usable structural high as a candidate base
   start. A forming candidate must mature for the configurable rebase duration
   before it can replace an incumbent; otherwise the candidate is retained as
   an annotation only. This is a clean-room heuristic, not a parity claim.
3. Define the pivot as the candidate base's highest close. Define depth as
   `(pivot - minimum_low) / pivot * 100`; duration is sessions/5.
4. Split the complete base into chronological halves. `coil` uses mean true
   range as a percentage of close; `dry` uses mean share volume; `dryDepth`
   uses minimum/median share volume.
5. Mark squats when high exceeds the pivot while close remains at or below it.
   Mark a breakout at the first close above the pivot. Mark a fresh breakout,
   running leg, or exit from explicit post-breakout price/50-day-MA rules.
6. Rank each symbol's configurable weighted trailing returns into 1--99
   percentiles. This is independent of base discovery.

## Commands

```powershell
py -m pytest unidesk/tests/test_cleanroom_base_pattern.py -q
py -m pytest unidesk/tests/test_setup_primitives.py unidesk/tests/test_detectors_geometry.py unidesk/tests/test_cleanroom_base_pattern.py -q
py unidesk/run_checks.py
```

## Structure and style

- Pure detector code belongs in `unidesk/momentum/detectors/` and performs no
  network, filesystem, or persistence I/O.
- Tests belong in `unidesk/tests/` and use hand-computed synthetic bars. The
  public YASHHV record is a calibration fixture in a test comment only; tests
  do not fetch or depend on BananaPatterns at runtime.
- Dataclasses are immutable. Inputs are validated and failures are explicit;
  no unavailable input is silently converted into a positive signal.

## Testing strategy

- Unit tests cover each measured formula, pivot confirmation lag, base-start
  selection, squat/breakout annotations, lifecycle states, no-look-ahead,
  insufficient data, and 1--99 RS ordering.
- A manual calibration replay reconstructs the observable YASHHV duration,
  depth, `coil`, `dry`, and `dryDepth` to a stated tolerance from the public
  OHLC sample; no public data is bundled in the repository or fetched by tests.
- Existing primitive and geometry tests protect the shared pivot/contraction
  contracts.

## Boundaries

- Always: retain no-look-ahead semantics, surface heuristics as parameters,
  preserve existing contracts, and run the listed tests.
- Ask first: persist new fields, wire this into production scanning, add a
  network dependency, or claim parity with BananaPatterns.
- Never: copy hidden source, evade controls, retrieve private data, or present
  a detected pattern as investment advice.

## Success criteria

- The new detector produces every requested output field for sufficient daily
  data and refuses short/invalid inputs.
- Formula tests pass, and a manual calibration replay is recorded separately.
- The implementation documents which components are exact public definitions
  and which are configurable clean-room heuristics.

## Open questions

- The proprietary structural base-selection/tie-break rule is not public.
- The exact RS lookback/weights and universe hygiene are not public.
- Failed-poke confirmation and rebase/overlap policy need a wider labelled
  public sample before claiming close parity.
