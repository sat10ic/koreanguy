# HANDOFF — SMF-style Activity Screener + drill-in (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md
(no commit; write `_COMPLETED.md`; real data only; absolute python paths; no rupee glyph to
console — "Rs"). Run `python scripts/desk_gate.py` on the desk wave.

## Context — read FIRST, this defines what is and is not being built
`manas_os/design/SMF_DATA_COMPLETE_REVERSE_ENGINEERING_2026-07-14.md` — the full dossier.
Summary: the proprietary "Reactor/SMF" formula was NOT exactly recovered (proven missing
variable); our own `sat10ic_eod_activity_v2` (`alpha/activity.py`) is a close, honest,
direction-neutral ANALOGUE (July screenshots ±0.25, 15/15 threshold agreement). The engine +
API already exist: `GET /api/alpha/activity` (leaders cross-section) and
`GET /api/alpha/activity/{symbol}?trail=N` (per-symbol trail). You are building the PRODUCT
SURFACE (screener + drill-in, reference screenshots the maintainer has) plus the dossier's §12
fidelity gaps. NEVER present it as the proprietary SMF/Reactor score or "institutional buying"
— permanent wording per §13: **"Abnormal activity; direction unresolved."** + SHADOW StatusBadge.

## Scope
### A. Backend fidelity fixes (dossier §12 — do before UI)
1. **Persistence threshold**: source teaching = >=3 consecutive abnormal sessions; code flips
   `persistent_abnormal` at 2. Follow §12.1: require 3 for `persistent_abnormal`, and expose the
   raw `streak` count so the UI can show "2d"/"3d"/"5d" chips distinctly.
2. **Fund-unit contamination**: the persisted cross-section still surfaces fund-like instruments
   (SBIBPB, TOP10ADD, HDFCNIFBAN). Verify/extend the ETF/fund guard (use `classify_universe` /
   symbol_identity where possible), then RECOMPUTE and re-persist the affected date(s) so the
   leaderboard is a true Stocks view. Add an explicit `instrument_class` filter param to the
   leaders endpoint (stock | all).
3. **Corporate-action quarantine**: per §12.3 add a visible per-row quarantine: if a symbol's
   avg-trade-qty baseline is distorted by a split-like discontinuity (e.g. >3x single-day jump in
   shares traded baseline or price gap consistent with a split ratio), flag
   `quarantined: "possible corporate action"` instead of showing an extreme score as real. Honest
   flag, conservative heuristic, documented.
4. Extend `leaders()` to support the screener's needs server-side (one writer, no client math):
   min_score, min_avg4, sector, segment (EQ/F&O if derivable from scan data; else omit —
   flag it), mcap band (from fundamentals/universe if available; else omit — flag it),
   symbol search, full-universe count + filtered count, and per-row: score, prev_day_delta,
   avg4, avg10, streak, 10-session trail array, percentile, quality/quarantine flags.

### B. ACTIVITY screener panel (reference: source dashboard screenshot — replicate CONTENT +
   functionality, NOT their dark neon theme; ours is the locked v5 LIGHT language)
New desk surface (own tab or ALPHA-tab section — pick what fits the IA, justify): 
- Header strip: universe count, filtered count, selected date, count score>=6, max streak,
  surge-day count, SHADOW badge + the §13 wording.
- Filters: date picker (default latest session; honest no-run handling), quick filters
  (All / Hot=score>=6 / Multi-Day=streak>=3 / Surge=prev_day_delta large), min-score +
  min-4d-avg sliders, sector dropdown, instrument-class, search box.
- Table (v5, mono numerals): symbol, sector, segment chip, mkt-cap (if available), SCORE
  (colored by band: <3.5 mute, 3.5-8 amber, >=8 green/bold), prev-day delta, 4d avg, 10d avg,
  streak ("2d"), 10-day trend = inline bar mini-chart from the trail array (plain SVG, band
  colors, no chart libs), signal chips (surge / above-avg / quarantined).
- Row click → drill-in (C). Sort by any column server-side or client-side on delivered rows.
- Honest states: loading, no-run date, insufficient-history rows show "warming (n/20 sessions)".
### C. Drill-in (reference: second screenshot)
Reuse the existing ChartDrawer (daily candles) for the symbol + BELOW it two aligned plain-SVG
bar strips from the trail/API: (1) activity score per session, band-colored, 3.5 reference line;
(2) delivery % per session (>=50 strong / 25-50 moderate / <25 weak colors). Timeframe toggles
can reuse ChartDrawer's existing ranges. Every number from the API verbatim.

## Guardrails
Score stays SHADOW: must not feed gates/sizing/ranking/verdicts (it already doesn't — keep it
so). Direction-neutral wording everywhere. v5 tokens only, `.v5`-scoped CSS, plain SVG, a11y AA,
reduced-motion. Real data; no synthetic trails. pytest green (known sector-downside fail
allowed) + vitest + build + desk_gate.

## Output
`HANDOFF_GEMINI_smf_activity_screener_COMPLETED.md`: files, the leaders-endpoint contract,
before/after of the fund-contamination recompute (top-10 with the ETFs gone), the 3-session
persistence change, quarantine heuristic + example, REAL DOM evidence of the screener + drill-in
on the latest session, test results.
