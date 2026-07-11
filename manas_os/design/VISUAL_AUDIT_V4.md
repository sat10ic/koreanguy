# VISUAL_AUDIT_V4 (Opus, 2026-07-11) — element->visual/animation/card conversions
Full audit in session log; this file records the RANKED WORK LIST + animation language.

## Slice V4-T6b "visual quick wins" (all S effort, one wave)
1. Scanner purple-dot glyph strip (int -> filled dots; spec'd in V4 ASCII, code regressed)
2. Scanner row heat: colorScale bg on move%/ADR (reuse viz.js)
3. DEBATE vision checkmark/cross chips
4. JOURNAL per-trade R bars + win/loss bar
5. MARKET funnel bars scanned->shortlisted->actionable (reuse FunnelPanel idiom)
6. MARKET stepper advance + one-shot current-step pulse
7. POSITIONS Rs P&L surfaced prominently (+%)
Runner-ups: choppy-brake state pill, DEBATE council balance bar.

## Fold into tab slices
- T9 SHORTLIST: status-flow timeline (colored dots on date axis per stock) + conviction delta arrows — build visual from the start.
- T13 TRADE PLAN: R-ladder rail (entry/stop/target as distances) + risk-check fill-bars vs caps.
- T14 POSITIONS: R-thermometer rail (stop|entry|current|target) alongside existing r_path sparkline.
- T15 JOURNAL: cumulative-R equity curve above trade table.
- MARKET (post-T6b): four-phase cycle ring, MBI breadth thermometer.
- T12 charts: weekly mini-candle + PD-density thumbnails on scanner/shortlist rows (L effort, highest raw value).
- XP sparkline+arrow: needs /api/regime/history endpoint first.

## Rejected
- ECharts dep: not the difference-maker anywhere in scope; funnel-as-sankey = decoration for 4 integers.
- Breathing/pulsing P&L: decision numbers never animate.

## Animation language (binding)
Motion marks CHANGE only: pipeline fills, counts tick up, stepper advances + single pulse,
watchlist status-change flashes once, charts draw in on open, verdict cross-fades on real
stance change. NEVER moves: law tiles, gate dots, risk numbers, stop/target, P&L, verdict.
150-250ms ease-out, one-shot, no loops/idle motion, prefers-reduced-motion honored.
Rule: if it didn't just change, it doesn't move; if it changed, it moves once, then holds.
