# RENDERED UX AUDIT LEDGER — 2026-07-17 (task #46)

Method: drove every tab in the browser on real 07-16 data, beginner lens, tree-based (preview
pane wouldn't screenshot — pixel layout UNVERIFIED this pass; structure/copy/data fully checked).
Severity per website-audit-skill. Fix owner: Codex waves (#47).

## CRITICAL (beginner gets wrong/contradictory answer)
- C1 ONE-VOICE FAILURE, TODAY: three answers to "do I act today?" — guided flow "4 of 4 setups
  need TAKEN/SKIPPED" vs verdict "SIT OUT — nothing cleared the bar" vs DEBATE "0 verdicts".
  Fix: single source: flow step 4 must read the same verdict object; when debate failed, say so
  in the flow step ("council didn't run — setups are ungraded; review manually or retry").
- C2 DOUBLE BANNER, TODAY: "market closed — update expected ~19:00 IST" AND "⚠ last night's run
  did not complete" simultaneously. Fix: one freshness banner with one state machine
  (fresh / awaiting-tonight / failed-run + reason).
- C3 RAW JSON IN UI, DEBATE: pipeline note renders `{"detail":"scan_date=..."}`. Fix: humanize
  ("Council models errored last night (rate-limited). 15 candidates went ungraded. [Retry]"),
  keep JSON behind expert drill-in.
- C4 WATCH DEAD-END: "No shortlist yet" while TODAY's step 4 points here. Fix: when shortlist
  empty but scan has grade-B cards, show them as "tonight's gate-passed candidates" with
  TAKEN/SKIPPED — the flow must never point at an empty room.

## IMPORTANT (trust/legibility)
- I1 float leaks: "RVOL20 (0.8052299365389679)", "open risk 0.0000 % used" → 1-2 decimals, units.
- I2 dev-speak leaks: "NH/NL -4 (up_4pct-down_4pct (NH/NL not ingested; proxy))"; truncated
  "(allowed: [" list dumps in shortlist history → plain sentences.
- I3 debated-strip chips: all 15 symbols show identical "65dL" tag → either real per-symbol
  data or drop the chip.
- I4 D2/Episodic scanner 0 hits on a real D2 day (HIRECT +19.9% 07-16) → detector thresholds
  audit (join with practitioner labels).
- I5 ALPHA greek labels: "20d residual" → "outperformance vs market, 20d"; "Leadership 100%"
  needs info-dot; "SHADOW EVIDENCE/OBSERVING" → plain header; missing sector on some rows.
- I6 top-deals panel STALE at 07-10 (source empty since 07-11) with no stamp → NSE-direct
  bulk/block source + per-panel freshness stamp (already-designed fix).
- I7 gate funnel confirms trend-template -563 / risk -222 as dominant killers → discovery wave
  (trend-template recovery/EP relaxation + anticipation WATCH lens + EP target math).
- I8 discovery_bucket=0 for all 13 practitioner labels → sensitivity bucket broken/mis-scoped.

## GOOD (verified, keep)
Freshness stamps per section; honest empty states (POSITIONS/JOURNAL/lessons); funnel explainer
(2386→1937→1101→234→15) on three tabs; practitioner scanners with citations + hit counts +
schematics; Fyers chip + re-auth flow; guided rail skeleton; ALPHA push-to-debate/add-to-
shortlist actions; governor "today's law" panel.

## Unverified this pass
Pixel layout/overlap (screenshot capture broken in preview env); chart drawer internals;
activity inspector; mobile.

## ADDENDA (2026-07-18, user-reported)
- I9 UPDATE swallowed by wedged thread: job 22 stuck 'running' since 07-17 18:34 made every later click return silent 'already running' (no UI surfacing, no watchdog). Fix: surface 'run active since HH:MM' + cancel button + stale-run watchdog (>45min = mark interrupted, allow restart). VERIFIED via jobs table forensics.
- I10 debate card stale evidence: vision/observer cites 22-month-old weekly events (ADANIENT 'Sep 2024 sell-off') as headline Contradiction. Fix: prompt recency constraint (contradictions from last 3-6mo; older = 'historic, low weight') + card lint tagging claims >6mo as historic.
- I11 ML P(up 10d) empty on debate cards while ml_scores has 1,202 scored symbols for the date -- verify join after server restart (scan_date vs run_date / symbol coverage).
