# HANDOFF_GEMINI_live_stage2 — COMPLETED (partial desk UI)

**Executor:** Grok · **Date:** 2026-07-12 · **No git commit**

## Shipped

### 1. Armed-zone schema (correct version)
- `armed_list`: additive `zone_low` / `zone_high` via guarded ALTER in `telegram_engine.ensure_schema`.
- Populated at arm time in `build_digest` via `zone_from_plan(trigger, atr20)`:
  - Prefer **pivot → pivot + 0.5×ATR20** when metrics available.
  - Else **trigger → trigger×1.006** (0.6% approx, documented).
- `live_fsm.arm_from_armed_list` copies **persisted** zone into `live_fsm_state.zone_lo/hi`; falls back to pct formula only for legacy NULL zones.

### 2. Live stream API
- `GET /api/live/status` → `{market_open, as_of, note}`
- `GET /api/live/stream?symbols=&cursor=&max_seconds=` → SSE with event_id = `symbol|updated_at|ltp`; cursor skips older events (reconnect-safe).

### 3. Desk live-default
- **Partial:** APIs ready for LIVE chip. Full shell/POSITIONS/SHORTLIST LTP ticker wiring **not completed** this pass (needs desk state plumbing per tab).
- Existing `/api/live/quotes` remains the batch poll fallback.

## Tests (QC)
```
pytest manas_os/tests/test_live_fsm.py manas_os/tests/test_telegram_engine.py -q
→ 13 passed
```
New: `test_arm_uses_persisted_zone_from_armed_list`, `test_zone_from_plan_uses_half_atr_when_present`.

## Monday 09:15 IST checklist
1. Confirm Fyers auth (`is_available`) before open.
2. `live-loop --paper` seeds armed_list → FSM ARMED with zone_lo/hi non-null for ATR symbols.
3. Hit `/api/live/status` → market_open true during session.
4. SSE `/api/live/stream?symbols=...` emits quote events; reconnect with last cursor does not re-emit older LTP.
5. Confirm outside zone still → EXPIRED_MOVED (existing FSM tests).
6. `agents.telegram_live` remains **false** (paper double-lock).

## Not done / follow-up
- Desk LIVE chip + mono-num LTP on POSITIONS/SHORTLIST/DEBATE (display-only).
- Vitest pure helpers for live fallback formatting.

## Do-not
Did not flip `telegram_live`. No order routing. Zones do not alter EOD gates/plans.
