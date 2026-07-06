# LEARNINGS.md — threshold changes, replay results, calibration log (Manas 2.0)

Every gate/threshold change and every replay/validation result gets one entry.
No silent reweighting.

## 2026-07-06 — Phase 0 complete (T0.1 clamps + T0.2 replay harness)
- Growth clamp [-200, +500] + untrusted flag live; "+-" sign bug fixed; stop bound
  1-8% enforced at candidate build (out-of-band stops dropped with named reason);
  rr + suggested_qty required on every persisted candidate. (Codex build, Opus QC.)
- Replay harness live (`manas_os/backtest/replay.py`): per (setup_family × regime)
  cells, A/B configs, thin-cell suppression (n<20), look-ahead guard tested.
- Fixed in QC: `backtest/__init__.py` re-export shadowed the `replay` submodule;
  replay tests rewritten to a pluggable fake generator (right unit boundary);
  three test fixtures used a +1/day ramp whose 20-day-low stop was ~16% — the new
  bound correctly refused them; ramps flattened to 0.1/day (the code was right).
- delivery_z gained a 1pp dispersion floor: constant-delivery history had std=0,
  masking a 60→20 collapse (z forced to 0). Found by test.

## 2026-07-06 — CRITICAL replay finding (shapes T1.4)
`replay('legacy', 2026-05-01..2026-07-03)` = **zero completed observations**: the
legacy candidate pool requires ChartsMaze `screener_hits`, which exist only for
the dated dump folders (2026-03-23 → 2026-07-05, 7 dates). Historical sessions
have no screener data → no candidates → no backtest.
**Consequence (binding for T1.4):** the `cascade` generator must derive setup
detection from OHLCV point-in-time (daily_prices covers all ~282 sessions), with
screener-confluence as an optional boost when a dump date is available — otherwise
the validation loop (T1.6) and the expectancy moat (T2.3) have no history to learn
from. Going forward, daily ChartsMaze dumps accumulate real confluence history.

## 2026-07-06 — Phase 1 core built (T1.1–T1.3, hand-written + tested)
- `scanner/gates.py`: deterministic cascade (regime → tradability(ASM/MAX/pump) →
  trend-template(50>200, EMA Lead, nearness≥0.85, RS≥80) → fresh-leg state machine →
  participation(delivery_z≥0, breakout vol 1.2×) → risk). Fail-fast with named
  reasons; 19 tests.
- `risk/plan.py`: single writer of stop/size/R:R; 3-stop hierarchy; LOCKED caps
  (6/5/4%, EP-IPO 7.5%, abs 8%, floor 1%); R:R≥1.5; AGGRESSIVE default profile
  (0.75/0.50/0.30 base risk, heat caps 3.0/2.0/1.0, ≤5 positions); sector
  concentration (≤2, 3rd half-size); circuit-band feasibility hook.
- `regime/governor.py`: feed caps 8/4/2/0, allowed families, risk bands,
  push_allowed; unknown mode degrades to NO_TRADE (never permissive).
- Suite: 135 passed.
