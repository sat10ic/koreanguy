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

---
## SHARPENED (2026-07-14) — Fyers is the PRIMARY feed; EOD sections stamp "as of <date>"
User (repeated directive): make Fyers the primary data source so the tool is real-time and never
"stuck in old data"; only the sections that still depend on EOD (bhavcopy/ChartsMaze) should flash
an outdated message.

### Binding interpretation + honest premise correction
Fyers = the DEFAULT read for the LIVE layer: current quotes/LTP, intraday + daily candles, chart
drawer, positions/watchlist marks, tape, and a live index-based regime proxy (NIFTY/VIX). During
market hours these tick live; the tool shows a live price, so it never LOOKS frozen.

BUT these are structurally EOD and CANNOT be made real-time (Fyers does not carry them) — each must
render with an explicit "EOD as of <date>" stamp, not be faked live:
- delivery % / delivery qty / number-of-trades (post-close bhavcopy only) → all delivery-based
  accumulation (SMF, quiet-accumulation, absorption);
- computed breadth / XP / MBI / 4.5R (from the day's full bhavcopy);
- ChartsMaze screeners, RS ratings, sector analytics;
- disclosures (bulk/block/insider), ASM/circuit revisions;
- the deterministic GATES + candidate scan + money-math (EOD-anchored by design; live never
  authors risk — unchanged from the original decision above).

### Result (why this kills the "stuck" problem)
The price/state layer is always current (Fyers), so the desk is never blank/frozen. The edge layer
is honestly dated: a per-section freshness stamp shows "live" (Fyers, market hours), "last close"
(off-hours), or "EOD as of <date>" (bhavcopy/ChartsMaze-derived). Staleness becomes visible and
localized instead of freezing the whole tool at one date.

### Hard dependency order
1. Fyers auth + IN-APP RE-AUTH (blocking — token dies ~6am IST; no UI today). Nothing "Fyers-primary"
   starts until this works. (Handoff: HANDOFF_GEMINI_update_fyers_freshness.md.)
2. Fyers live-price layer as the default read for quotes/charts/positions/watchlist/tape + live
   index regime proxy; EOD values are the fallback when the feed is down/off-hours.
3. Per-section freshness stamp everywhere: live / last-close / EOD-as-of-<date>. No section renders
   old data as current (the honest-freshness rule).
4. Rate-limit/token-expiry/WS-reconnect handling (live engine stage-1 exists, paper/replay; needs
   Monday market-hours validation).

One-writer + money-math + paper-Telegram all UNCHANGED. Live displays and triggers; EOD authors
risk and evidence.
