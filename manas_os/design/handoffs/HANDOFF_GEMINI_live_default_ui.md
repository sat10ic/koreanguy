# HANDOFF 8 — Desk live-default UI (finish live stage 2 frontend) (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Governing: `manas_os/design/LIVE_FIRST_DECISION.md` (LIVE default, EOD confirmatory).

## Context
Live stage-2 BACKEND landed (armed-zone schema; FSM; `manas_os/live/` session/quotes/heartbeat;
paper Telegram). The DESK live-default frontend is PARTIAL (per HANDOFF_GEMINI_live_stage2_COMPLETED.md).
Verify what exists first: is `GET /api/live/quotes` wired in app.py, is there a `/api/live/status`,
is any live-tick SSE present? Build only what's missing.

## Scope
1. If not already present: `GET /api/live/status` (market_open via market_calendar.is_market_hours,
   as_of, feed health) + a live-tick SSE (or cursor-poll fallback like UI-2) for armed/watchlist/
   position symbols from the quotes cache. Read-only serialization; one-writer (live authors nothing).
2. **Desk live-default**: during market hours, the shell + POSITIONS + SHORTLIST + DEBATE tape show
   live LTP (ticking, `mono-num`, a visible LIVE chip; change flashes once per LIVE_FIRST motion
   rule). Off-hours: render exactly as today with a "market closed — last close" stamp. On feed loss:
   keep last-confirmed values visible + an honest "live feed down / auth needed" chip, auto-fallback
   to EOD. NEVER a full-surface loading wipe. Live values NEVER replace EOD values in any gate/plan/
   journal computation — display + trigger only.
3. Freshness-banner inversion per LIVE_FIRST: market-hours staleness = feed health; overnight =
   pipeline-run. Fyers 6am-IST token expiry surfaced loudly as an actionable re-auth chip.
4. Tests: desk pure helpers (market-open gating, fallback-to-EOD logic, LTP formatting) vitest;
   status/stream endpoint tests.

## Guardrails
telegram_live stays false; no order routing; money-math locked; `.v5` tokens only; a11y AA;
reduced-motion (LTP flash respects it). Real data only.

## Output
`HANDOFF_GEMINI_live_default_ui_COMPLETED.md`: what existed vs built, the status/stream contract,
DOM evidence of live chip + market-closed stamp + feed-down fallback (REAL output), Monday 09:15 IST
first-WS-session checklist.
