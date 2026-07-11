# LIVE-FIRST — user-locked mode decision (2026-07-11)

User (verbatim): "Live should be default mode, with backend bhavcopy, chartsmaze etc data being
the supportive/confirmatory backup."

## What this means (binding interpretation)
- **Default experience = LIVE.** During market hours the desk leads with live Fyers-derived state:
  live LTP on positions/watchlist/debate tape, live regime read, armed-list/FSM states streaming
  in (via the UI-2 SSE plumbing). Off-hours it renders the latest EOD state (as today) with an
  honest "market closed — showing last close" stamp.
- **EOD = supportive/confirmatory, not gone.** bhavcopy/ChartsMaze remain the canonical EVIDENCE
  layer: gates, screeners, delivery %, candidates, debate, sizing all stay EOD-anchored and
  point-in-time. The nightly run confirms/reconciles what live showed intraday.
- **One-writer unchanged:** live data NEVER authors risk (stop/qty/target come from the persisted
  deterministic plan). Live may only display, trigger pre-committed armed levels, and revalidate.
- **Freshness inversion:** staleness banners now mean "live feed down" during market hours (auth
  6am IST expiry surfaced loudly), and "EOD pipeline not run" overnight.

## Build sequence
1. Stage 1 (in flight): WS engine + armed-list + FSM + replay harness, paper alerts.
2. Stage 2 (after UI-7 frees desk): live default in the desk — live LTP cache endpoint + SSE tick
   stream, tabs consume it market-hours; EOD fallback + closed-market stamp.
3. Stage 3: nightly reconcile report (live-seen vs EOD-confirmed deltas) — the "confirmatory" leg.
