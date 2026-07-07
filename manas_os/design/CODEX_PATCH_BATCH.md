# CODEX PATCH BATCH — Manas OS defects from 2026-07-07 wireframe audit

Rules: execute P1→P5 IN ORDER. Each is a mechanical fix with an exact location + expected
result. Do NOT redesign, do NOT touch anything not named. After EVERY task:
`C:\Users\satta\AppData\Local\Programs\Python\Python314\python.exe -m pytest manas_os/tests -q`
(baseline 174 green, never regress) AND `cd manas_os/frontend && npm run build` (must stay clean).
Python fallback if 3.14 missing: `...\Python312\python.exe`. Do NOT touch: scanner/gates.py,
risk/plan.py, regime/governor.py, backtest/replay.py. One writer per metric.

Verify each visually if you can reach the running dev server (frontend :5173, API :8000);
if your sandbox blocks the browser, mark "visual verification pending main thread" and continue —
but the build + pytest gates are mandatory and must pass.

---

## P1 — Regime: Sectors & TopIndices leak into Beginner (BEGINNER_EXPERT_SPEC §3.1)
File: `manas_os/frontend/src/components/RegimeSummary.jsx`, the `InternalsBlock` JSX (~L85-95).
Today it renders ParticipationPanel, BreadthGrid, SectorsThemesPanel, TopIndicesPanel,
SetupStickers, QuadrantGrid, TechnicalDetail — and in Beginner this whole block is shown inside
`<ShowDetails>` (a beginner-openable peek). Per BEGINNER_EXPERT_SPEC §3.1 the sector/index
LEADERBOARDS are Expert-only, never in Beginner (not even in the peek).
FIX: gate the two leaderboard panels on `expert` inside InternalsBlock so they never render in
Beginner:
```jsx
{expert && <SectorsThemesPanel />}
{expert && <TopIndicesPanel />}
```
`expert` is already in scope at this point (const expert = density === "expert"). Leave
ParticipationPanel/BreadthGrid/SetupStickers/QuadrantGrid/TechnicalDetail exactly as they are.
EXPECTED: in Beginner, opening "Show the numbers" no longer shows the Sectors & Themes table or
the TOP INDICES ladder; Expert still shows both inline.

## P2 — Regime: duplicate PostureCommandBar in Expert
Same file. `RegimePoster` (~L156) renders `<PostureCommandBar>` as its `action` prop
(always). Separately, the outer component (~L100) renders `{expert && <PostureCommandBar data={d} stale={stale} />}`
— so Expert shows it TWICE. FIX: delete the standalone `{expert && <PostureCommandBar .../>}`
line (~L100). Keep the one inside RegimePoster's action. EXPECTED: exactly one PostureCommandBar
in both modes.

## P3 — Regime: the stale READ / explanation sentence renders twice
Same file. The stale-data explanation string (`data.read || data.explanation_text ...`, e.g.
"Data is 1 trading day old — treat this as last-known...") currently appears twice on the Regime
poster in Beginner (once in the RegimePoster READ block, once again immediately below). Find both
render sites of that same string in RegimeSummary.jsx (grep `data.read`, `explanation_text`,
`readText`, and any `<Read>` in RegimePoster / the POSTURE section) and render it ONCE — keep the
one inside the POSTURE PosterBand (the `readText` at ~L152), remove the duplicate sibling that
repeats the same text. Do NOT remove the SWING/TREND/BIAS captions (those are different strings,
each from `quadrant.<x>.reason`). EXPECTED: the stale explanation shows once under POSTURE.
After this + P1, confirm the "DATA UPDATED UNTIL" DataStamp also appears only once in Beginner
(the mid-page one was coming from the now-hidden Sectors/TopIndices panels; if a duplicate
DataStamp still shows, remove the extra so it renders once at the bottom).

## P4 — Journal: REFUSED cohort tile shows raw lifetime count (160,766)
File: `manas_os/api/app.py`, function that builds `/api/journal/visuals` (~L1868).
Currently: `refused = conn.execute("SELECT COUNT(*) AS n FROM refusals").fetchone()` — this is
every refusal ever, so the cohort strip shows a meaningless 6-figure number next to taken=1.
FIX: scope the refused count to the most recent 20 distinct scan_dates in refusals, so it is a
comparable recent-window number:
```python
refused = conn.execute(
    "SELECT COUNT(*) AS n FROM refusals WHERE scan_date IN "
    "(SELECT DISTINCT scan_date FROM refusals ORDER BY scan_date DESC LIMIT 20)"
).fetchone()
```
Leave the other cohorts (taken/skipped/tracked_near_miss) as-is. Frontend
`JournalPage.jsx` cohort tile already reads `cohorts.refused` — no frontend change needed, but
update its `sub` label (grep the "scanner hard no" MetricTape item) to "scanner hard no · last 20 sessions".
TEST: extend `manas_os/tests/test_journal_visuals.py` if it exists (else the nearest
journal-visuals test): seed refusals across >20 distinct scan_dates and assert
`cohort_counts["refused"]` is bounded to the last-20-session total, not the full table count.
If no such test file exists, add `manas_os/tests/test_journal_visuals_cohorts.py` with a
TestClient test doing exactly that.

## P5a — Watchlist: active position OPEN R / DAYS show "-"
File: `manas_os/api/app.py`, `/api/watchlist/organic` active-position loop (~L1731-1736).
Each `active` item has `coach` (from `_coach_for_open_trade`) but no top-level open-R or
days-held, so the frontend renders "-". FIX: after `item["coach"] = ...`, add:
```python
item["open_r"] = (item.get("coach") or {}).get("r")
try:
    item["days_held"] = market_calendar.trading_days_between(
        _date.fromisoformat(row["trade_date"]), _date.fromisoformat(on_or_before)
    )
except (ValueError, TypeError):
    item["days_held"] = None
```
(`market_calendar` and `_date` are already imported in app.py — confirm and reuse; do not
re-import.) 

## P5b — Watchlist frontend: ALREADY READS THESE FIELDS — do not change
`manas_os/frontend/src/components/WatchlistPage.jsx` L117-118 already read `item.open_r` and
`item.days_held` and render "-" when null. Once P5a sets them in the payload they render
automatically. NO frontend edit. Just confirm the values appear after P5a.
TEST: add a TestClient test (new file `manas_os/tests/test_organic_watchlist.py` — no organic
test exists yet): seed conftest `insert_price_ramp` + `seed_confluent_symbol`, insert one open
`journal_trades` row (exit NULL), GET `/api/watchlist/organic`, assert
`active_positions[0]` contains keys `"open_r"` and `"days_held"` (values may be null but keys
must be present).

## P6 — Regime SWING mini-table: %>10DMA column empty
File: `manas_os/api/app.py`, `regime_breadth_history` (~L1188). Both SELECTs list
`pct_above_20dma, pct_above_40dma, pct_above_50dma` but NOT `pct_above_10dma` — so the SWING
table's %>10DMA column is always "-". `breadth_daily` HAS a `pct_above_10dma` column (confirmed).
FIX: add `pct_above_10dma` to BOTH the inner and outer SELECT column lists in that query. The
frontend SWING table already reads `pct_above_10dma` (renders "-" when absent), so no frontend
change needed. TEST: extend the breadth-history test (grep tests for "breadth_history" /
"breadth-history") to assert each returned row has a non-null `pct_above_10dma` when the seed
data provides it.

---
## Reporting
After P1-P6: run pytest + npm build one final time. Update this file's status line below, then
report per-task: one-liner, pytest tail, npm tail, files changed, deviations (should be none).
Do NOT attempt P4-of-audit (empty rolling_t10_medians) or MFE/MAE scatter — those need an
outcomes/excursion data backfill and are explicitly OUT OF SCOPE for this patch batch.

STATUS: [x] P1-P6 patched; pytest/npm verification blocked by local execution sandbox
