# Spec: Safe clean-room base episodes, screens, and chart annotations

## Objective

Make the public, clean-room BananaPatterns-style base measurements a
first-class UniDesk capability without claiming proprietary parity or allowing
known-unsafe detector outputs to be ranked as actionable candidates.

The first deliverable is a backward-compatible trust envelope in the nightly
JSON output and a BaseEpisode / ScreenMatcher pure domain layer. Later slices
will connect those outputs to real OHLCV charts, Market, and Screens views.

## Assumptions accepted by the owner instruction

- The existing clean-room detector remains the sole source for base geometry;
  it must not call BananaPatterns at runtime.
- N5 experiments and ablations remain blocked; no performance result is
  promoted while corporate-action and outcome-label gates are open.
- Existing report consumers may read the current detector fields, so trust
  metadata must be additive rather than changing existing booleans or enums.

## Contract decisions

- `detectorTrust` is an additive mapping from detector name to
  `{status, reason, version}`. Trust is separate from detector verdict and
  BaseEpisode lifecycle.
- A BaseEpisode is point-in-time: it records symbol, as-of, known-at, method
  version, adjustment basis hash, base window, pivot/floor, measurements and
  annotations. A candidate references an `episode_id`; it does not rederive
  the episode.
- Screen presets are pure named predicates over BaseEpisodes. They return
  included/excluded rule reasons and do not duplicate discovery logic.
- Failed-poke markers retain a confirmation timestamp and are never shown as
  if known on their occurrence date.

## First vertical slice

1. Define trust and screen/episode contracts with failing unit tests.
2. Emit trust metadata beside existing nightly JSON candidates; mark all
   audited unsafe/questionable detectors non-rankable.
3. Add BaseEpisode and ScreenMatcher pure adapters around the clean-room base
   detector, tested with hand-computed bars.
4. Extend JSON only after the contracts and tests are green.

## Commands

```powershell
py -m pytest unidesk/tests/test_cleanroom_base_pattern.py unidesk/tests/test_report_json.py -q
py unidesk/run_checks.py
```

## Boundaries

- Always: preserve raw detector outputs, version derived objects, disclose
  unavailable data, and test no-look-ahead behavior.
- Ask first: change the existing public terminal route shape, migrate a
  persistent store, add dependencies, or make N5/promotion claims.
- Never: overwrite prior archive labels, fetch private vendor data, use a
  vendor output as production fallback, or present a screen as advice.

## Success criteria

- Existing JSON remains parseable; consumers gain an additive trust map.
- Unsafe detector outputs cannot be ranked actionable by the new screen path.
- A BaseEpisode carries reproducible geometry and provenance, while a preset
  result explains every rejection.
- Unit tests and `run_checks.py` pass.
