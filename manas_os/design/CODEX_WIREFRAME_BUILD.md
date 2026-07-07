# CODEX WIREFRAME BUILD — build each screen TO manas_os/design/WIREFRAMES.md, element-for-element

READ THIS FIRST. This is NOT a polish pass. Ten prior rounds "made it denser/nicer" with
generic poster primitives (PosterBand / VisualCard / MetricTape) and the result bears NO
structural resemblance to WIREFRAMES.md. That approach is BANNED here. This doc rebuilds each
screen's LAYOUT to match the wireframe ASCII block-for-block.

## The one rule (fidelity) — TWO DIRECTIONS
For each screen, the WIREFRAMES.md ASCII is the CONTRACT. The screen is done ONLY when a
desktop screenshot, laid next to that ASCII, has the same major blocks in the same order and
role — AND NOTHING ELSE. Both directions are the test:
(a) every ASCII block present, in order, in its role;
(b) every rendered block traceable to a line of the ASCII — anything on screen the wireframe
    does not show (old posture strips, data-stamp rows, metric tapes, leftover panels, legacy
    read blocks) is a DEFECT, same severity as a missing block.
"npm run build clean + pytest green" proves it COMPILES — NOT the done-test.

## REWRITE, don't patch (added 2026-07-07 after round 11 of patchwork)
For each screen: REWRITE the page component from scratch, top-down from the ASCII. Start from
an empty return and add blocks in ASCII order. The ONLY things that survive from the old file:
data-fetch calls (api.js functions), design tokens, and small atoms the ASCII itself needs
(InfoDot, SymbolChip). Old layout components (PosterBand/VisualCard/MetricTape/PostureCommandBar
/DataStamp rows/any panel the ASCII doesn't show) do NOT get mounted — delete their usage from
the page. If they become unreferenced repo-wide, delete the file (no dormant code).

## Execution model — ONE SCREEN PER BATCH, verified before the next
Do NOT do all screens in one pass (that is how every prior round "finished" without resembling
anything). Order: SETUPS → REGIME → WATCHLIST → JOURNAL → FOCUS → CHART DRAWER. For each
screen:
1. Open WIREFRAMES.md, copy its ASCII block for that screen.
2. List the ordered blocks the ASCII mandates (see per-screen breakdown below).
3. Build the screen's JSX so those blocks exist, in that order, with those roles. Reuse
   existing data fetches + tokens; you may keep primitives as building material, but the
   LAYOUT must be the wireframe's, not a generic stack of cards.
4. Run API (:8000) + dev server (:5173). Screenshot the screen (desktop ≥1440 wide).
5. Write a FIDELITY REPORT: for every block in the ASCII, state present / missing / misplaced
   with a one-line note. If any major block is missing or out of order, fix and re-shoot before
   moving on.
6. Only then tick the screen and move to the next.

Rules: no new colors/fonts (design_guidelines tokens only). No backend logic/threshold changes
(presentation only; a missing data field for a wireframe block → add to the existing endpoint's
SELECT/payload, do not invent values). Baseline pytest 176 green, never regress. Python:
C:\Users\satta\AppData\Local\Programs\Python\Python314\python.exe (fallback ...\Python312).
Do NOT touch scanner/gates.py, risk/plan.py, regime/governor.py, backtest/replay.py.

Files: the five page components in manas_os/frontend/src/components/ (SetupsPage, RegimeSummary,
WatchlistPage, JournalPage, ChartDrawer) + poster/Primitives.jsx + api.js. Focus is a new
component + a nav tab (App.jsx). Backend only where a wireframe block needs a field the endpoint
doesn't return yet.

---

## SCREEN 1 — SETUPS  (WIREFRAMES.md §2 "the feed that says NO")
ASCII target (from WIREFRAMES.md §2). Required blocks, in order:
1. **REFUSAL FUNNEL hero** — Universe → Screeners → Gates → PASSED, horizontal, with the
   SELECTIVE cap labeled, and the per-gate drop reasons on hover (tradability -N, trend-template
   -N, fresh-leg -N, risk -N). Source: /api/setups/refusals + /api/setups.
2. **One CARD per survivor** (max = governor cap). Each card, in this internal order:
   - header row: SYMBOL · setup·family · "RANK n of M today" · [TAKEN] [SKIPPED ▾reason]
   - **six GATE DOTS in a row** (regime/tradable/trend/fresh/particip/risk), green/red, reason
     on hover — this specific dot row is a wireframe signature element; it currently renders but
     confirm it is a single compact row, not buried.
   - **PLAN block and EXPECTANCY block SIDE BY SIDE** (two columns): PLAN = entry · stop (%,
     source) · R:R · qty (risk ₹); EXPECTANCY = "EP×SELECTIVE: 62% hit · +0.8R med (n=47, sys)
     · yours: n=3 thin".
   - evidence line (plain, curated — NOT raw screener codenames; that fix already shipped).
   - probation chip if ipo/flag family ("unproven — building sample, half size").
3. **[E] NEAR-MISSES** — top-10 refused with the failed gate named ("SUNPHARMA — failed
   fresh-leg: 9.2% > 8%"). Already exists as a lane; keep.
DONE-TEST screenshot check: funnel is the hero at top; each card visibly has the 6-dot gate row
AND the plan|expectancy two-column block. If plan and expectancy are stacked vertically or the
gate dots are missing, it FAILS.

## SCREEN 2 — REGIME  (WIREFRAMES.md §1 "today's law")
Required blocks, in order:
1. **GOVERNOR PANEL hero** — one line verdict ("SELECTIVE — trade small and picky") then a
   row of tiles: MAX CARDS | RISK/TRADE | ALLOWED SETUPS | OPEN-RISK CAP (used/cap) | PUSHES.
   Then a WHY (plain) line. Source: /api/setups .governor + /api/portfolio/heat for open-risk.
2. **TOP SETUPS STRIP** — "① KPIL EP 1/4  ② ATUL pullback 2/4 → 2 of 4 reviewed [go to Setups]".
3. **[E] SHOW THE NUMBERS accordion** (expert only, never in beginner): breadth heatmap, sector
   rotation, XP+participation lines, indices strip. (P1 already gates Sectors/TopIndices to
   expert — keep.)
NOTE the separate four-pillar-chart request is tracked as E11 in NORTH_STAR.md and is a SEPARATE
task from this layout pass — do not attempt it here unless told; here just make the governor
hero + setups strip match the ASCII and keep the expert accordion.
DONE-TEST: governor tiles row is the hero; beginner shows governor + posture + setups strip only.

## SCREEN 3 — WATCHLIST  (WIREFRAMES.md §4 "positions + heat")
Required blocks, in order:
1. **HEAT ROW** — three side-by-side: OPEN-RISK gauge (1.2% vs cap 2.0), SECTOR donut
   (PHARMA 2 ⚠max), PROGRESSIVE EXPOSURE (last-10 avg R → full/half size). Source:
   /api/portfolio/heat.
2. **POSITION COACH CARDS** (open positions first): "⚠ TITAN +1.1R → move stop to 902 + sell ⅓"
   / "● KPIL +0.4R → HOLD initiation" / "🔴 HFCL EXIT TODAY — 2 rules fired. Unacted 2 days!".
   Source: /api/watchlist/organic active_positions (open_r + days_held now present).
3. **WATCH TABLE** — sortable, color-banded: SYM | RS | ADR% | dlv_z | dist-pivot | exit-state |
   trail | days | open R.
DONE-TEST: heat row (gauge+donut+exposure) is the hero; coach cards list open positions with the
verdict+action sentence; table below.

## SCREEN 4 — JOURNAL  (WIREFRAMES.md §5 "the moat rendered")
Required blocks, in order:
1. **EQUITY CURVE in R** hero (cumulative R, drawdown shaded).
2. Row: **EXPECTANCY MATRIX** heatmap (setup_family × regime, cell=posterior R, label=n, grey
   n<20) · **MFE/MAE scatter** · **R histogram** (0.5R bins). MFE/MAE needs per-trade excursion
   data — if absent, add a minimal computation OR render an explicit "needs excursion data"
   empty state (do NOT silently omit the block).
3. **FOUR-COHORT STRIP**: taken +0.6R | pushed-skipped +0.9R(!) | armed-skipped | refused -0.2R,
   with the READ line "you skip winners — pushed-skipped outperform taken". This is the edge
   read; the refused count is already scoped to last-20 sessions.
4. mistake-tag Pareto.
DONE-TEST: equity curve is hero; the four-cohort strip with its READ is visibly present.

## SCREEN 5 — FOCUS  (WIREFRAMES.md §3) — NEW TAB
Add a FOCUS tab between SETUPS and WATCHLIST in App.jsx. It is the SAME funnel + cards as
Setups, filtered to the catalyst family (EP + IPO-base), plus columns base-age / days-since-
listing / circuit-state. NO separate engine — reuse the Setups feed's focus_candidates (already
in the /api/setups payload). DONE-TEST: Focus tab exists and shows only catalyst-family cards
with the extra age/circuit fields.

## SCREEN 6 — CHART DRAWER  (WIREFRAMES.md §6)
Already close: SETUP/TREND/EXIT tabs, lightweight-charts candles+vol, EMA10/21/50, AVWAP with
anchor reason, buy-zone band + stop line + entry/exit arrows + pocket-pivot dots, compact legend,
[E] RS-line + TTM panes. DONE-TEST: the three tabs switch overlays; legend is one line.

---
## After all six
Final: one screenshot per tab (desktop). For EACH, write the FIDELITY REPORT (every ASCII block
present/missing/misplaced). Tick a screen ONLY when its report shows all major blocks matched.
Report per screen: the fidelity report + pytest tail + npm tail + files changed. If a block
genuinely cannot be built because data does not exist, say so with what you found — do not fake it
and do not silently drop it (render an honest empty state).

STATUS: [x] SETUPS  [x] REGIME (two-direction-verified 2026-07-07: hero verdict+5 tiles+WHY → setups strip → collapsed [E] accordion, ZERO extra blocks; risk-band field fix base_pct/hard_max_pct)  [x] WATCHLIST (two-direction-verified 2026-07-07: heat row → coach cards → clean 9-col table, chip clusters deleted)  [ ] JOURNAL  [ ] FOCUS  [ ] CHART DRAWER
