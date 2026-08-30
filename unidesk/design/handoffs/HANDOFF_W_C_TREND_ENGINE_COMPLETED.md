# HANDOFF W-C Trend engine — COMPLETED (first slice)

Date: 2026-08-29. Slice: `unidesk/momentum/features/trend.py` — the first
momentum-engine module (build manual Task P1.2), storage-neutral per
`unidesk/momentum/DATA_POLICY.md`.

## Outcome

Frozen, fixture-tested deterministic definitions:

- `ema(series, span)` — SMA-seeded exponential moving average; `None` through
  warm-up; output at index *i* depends only on `values[:i+1]`.
- `ema_slope_pct`, `price_vs_ema_pct` — warm-up-honest (None, never zero).
- `trend_state` — STRONG_UPTREND / UPTREND / TRANSITION / WEAK / UNKNOWN per
  the frozen rule table (context only; creates no signal, manual R5).
- `ema_rising` — never invents direction during warm-up.

The no-look-ahead property is enforced by test (truncating the input series
never changes earlier outputs) — the leakage discipline CP-3 will demand,
built in from the first module.

## Attribution

Attribution-ID: attr-unidesk-wc-trend-glm53flash-20260829-001

## Files changed

- `unidesk/momentum/features/__init__.py` — package init (new).
- `unidesk/momentum/features/trend.py` — trend engine (new).
- `unidesk/tests/test_momentum_trend.py` — 8 tests (new).
- `unidesk/GOAL.md` — status refresh.

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest unidesk/tests orderflow/tests -q
  -> 125 passed
```

## Honest partials

- W-C continues: participation (RVOL/delivery), ADR/ATR, RS/sector/peer,
  AVWAP, circuit risk, stock-quality snapshot are not built.
- All feature values are definitions, not measurements — nothing has run
  against real market data; Model A (W-D) is where they meet data.
- CP-2 subagent review of W-A/W-B was dispatched and its findings are handled
  separately; open findings block further W-C modules.
