# HANDOFF 3 — Live stage 2: desk live-default + armed-zone schema (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Governing doc: `manas_os/design/LIVE_FIRST_DECISION.md` (user-locked: LIVE default, EOD confirmatory).

## Context
Stage 1 shipped (`manas_os/live/`: session manager, quotes cache, FSM in `alerts/live_fsm.py`
7/7 green, paper Telegram double-locked, replay harness). `GET /api/live/quotes` exists (check
`live/quotes.py` + app.py wiring; if the endpoint isn't wired into app.py yet, wire it —
read-only serialization of the quotes cache). UI-2's SSE plumbing (`/api/jobs/.../events/stream`,
`desk/src/livework/useJobStream.js`) is the streaming idiom to follow.

## Scope
1. **Armed-zone schema** (the flagged Monday decision — implement the correct version):
   widen `armed_list` (additive guarded ALTER in `alerts/telegram_engine.py`'s schema) with
   `zone_low`/`zone_high`, POPULATED AT ARM TIME from the persisted deterministic plan
   (pivot → pivot + 0.5*ATR20 per `design/LIVE_LOOP_FABLE.md` §2.1). `live_fsm._zone_bounds`
   uses the persisted bounds when present, falls back to the current trigger→+0.6% approximation
   (documented) for old rows. Nothing outside the nightly arm step computes the zone (one-writer).
   Test: armed row carries zone; FSM confirm refuses outside it.
2. **Live tick stream to the desk**: an SSE endpoint (`/api/live/stream` or extend the quotes
   endpoint with a cursor-poll fallback like UI-2) pushing quote updates + FSM state changes for
   armed/watchlist/position symbols during market hours. Restart-safe, no duplicates (mirror the
   event_id-cursor pattern).
3. **Desk live-default**: during market hours (`market_calendar.is_market_hours()` via a small
   `/api/live/status`), the shell + POSITIONS + SHORTLIST + DEBATE tape show live LTP (ticking,
   `mono-num`, change-marked once per LIVE_FIRST motion rules) with a visible LIVE chip;
   off-hours everything renders exactly as today with a "market closed — last close" stamp.
   Last-confirmed data always stays visible on feed loss (honest "live feed down" chip, auto-
   fallback to EOD values). No full-surface loading.
4. **Tests**: zone persistence + FSM zone use; stream dedup on reconnect (fixture); desk pure
   helpers (formatting/fallback logic) vitest.

## Do NOT
Flip `agents.telegram_live`. No order routing. Live values never replace EOD values in any
gate/plan/journal computation — display + trigger only.

## Output
`HANDOFF_GEMINI_live_stage2_COMPLETED.md` per standing rules + what to verify Monday 09:15 IST
(first real WS session checklist).
