# HANDOFF 2 — Flagged backend fields + small fixes batch (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
These are the accumulated "BACKEND FIELDS REQUESTED" flags from prior waves + two small bugs.

## Scope (each item small; all in one pass)
1. **`rupee_risk` server-side** (from the TRADE PLAN wave): the signal-guide payload
   (`api/app.py` `/api/desk/signal-guide`) gains a first-class `rupee_risk = final_qty * (entry - stop)`
   computed server-side; `desk/src/TradePlanTab.jsx` displays it verbatim and deletes its client
   multiplication. One-writer closure.
2. **`management_contract` block** (same wave): signal-guide gains a structured
   `management_contract {trade_type, trail_rule, normal_behaviour[], source_cite}` derived from the
   same deterministic steps[] machinery server-side; TradePlanTab replaces its fragile regex over
   steps[].title with this block (keep the regex as fallback for old payloads).
3. **Watchlist provenance + next_trigger** (SHORTLIST wave): `/api/desk/watchlist` rows gain
   `family`/`family_label` (join scan_candidates on scan_date+symbol; null-honest for user-added)
   and a structured `next_trigger` string (from the candidate plan's trigger where available,
   else null). `ShortlistTab.jsx` upgrades its tier-proxy provenance chip to the real
   family/mechanism label when present.
4. **Bug #37 — Focus Center 0-setups vs tagged-cards mismatch**: reproduce first (tab shows 0
   while tagged candidate cards exist); root-cause the filter mismatch (`setup_type` vs family
   naming per prior task note); fix so an EP candidate MUST appear in the lens; add the test.
5. **Data-gap repair** (from the discovery trace): (a) backfill `screener_hits` before 2026-07-04
   from ChartsMaze dumps ON DISK (check `legacy/SwingEdge/data/chartsmaze/<date>/` and
   manas_os/data/; if dumps genuinely absent for a date, record it as unavailable — don't fetch
   externally); (b) 2026-07-08 has zero EQ rows in daily_prices — confirm it was a trading day
   (market_calendar) and re-ingest that bhavcopy if the file exists on disk; report before/after
   counts and re-run the SKYGOLD early-window pool check (`scanner/candidates.detector_shortlist`)
   to show improved coverage.

## Do NOT
Change money math, gates, regime. No new thresholds. Keep every payload backward compatible
(additive fields only).

## Output
`HANDOFF_GEMINI_backend_fields_batch_COMPLETED.md` per standing rules, with curl proofs for
items 1-3, the reproduced-then-fixed evidence for item 4, and before/after row counts for item 5.
