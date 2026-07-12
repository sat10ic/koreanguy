# HANDOFF — Weekly breakout timeframe scan (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: see
`manas_os/design/handoffs/HANDOFF_INDEX.md` (do not commit; write a `_COMPLETED.md`; real data
only; money-math/gates untouched by anything outside this scan's own new code; absolute python
paths; never print the rupee glyph — use "Rs"). LOW PRIORITY — do this only after the de-wonk
Waves B/C/D handoff is done and QC'd.

## Context
Reviewed `github.com/Elicherla01/breakoutscanner` (NIFTY500 breakout scanner, 1h/1D/1W/1M
timeframes, rolling-N-bar-high + volume-confirm + candle-close-position, strict mode adds ATR
range-expansion). Our existing daily breakout logic in `scanner/gates.py` (VOL_CONFIRM=1.2x 20d
avg, ATR14 range-expansion check) is comparable and already integrated into the deterministic gate
cascade — do NOT port their code/stack (no yfinance/Streamlit; we have bhavcopy/ChartsMaze). The
one real gap: we only scan the DAILY timeframe. A weekly-breakout variant is a legitimate, distinct
setup (bigger base, more durable signal) we don't have.

## Scope
1. Read `scanner/gates.py` (breakout gate + VOL_CONFIRM + ATR range-expansion logic) and
   `scanner/candidates.py` (`_compute_breakout_age`, pivot/prior-highs computation) to understand
   the exact daily pattern you're extending to weekly.
2. Add a WEEKLY resample of `daily_prices` (Mon-Fri OHLCV aggregated to weekly bars, standard
   resample: open=first, high=max, low=min, close=last, volume=sum) — either a SQL view/query
   helper or a small pure function; do not create a new stored table unless resampling on read is
   too slow (if so, an additive `weekly_prices` cache table is fine, point-in-time, rebuildable).
3. Apply the SAME breakout + volume-confirm logic used daily (rolling-N-week-high pivot,
   volume ≥ 1.2x 20-week avg, close in upper portion of the weekly range) to detect a
   **weekly base breakout** setup. Give it its own `setup_family` label (e.g. `weekly_base_breakout`)
   — distinct from the existing daily breakout family, never merged/confused with it (one-opinion:
   a symbol can have a daily AND a weekly breakout state simultaneously, shown separately).
4. Wire it as a new scanner preset (follow the existing preset registration pattern in
   `scanner/scanner_presets.py` — owner="TradeTM" or similar, LIVE status, real hit count) so it
   surfaces on SCANNERS like the other 19 presets, and feeds the normal candidate/gate/debate
   pipeline if it clears the SAME deterministic gates as any other setup family (regime/tradability/
   risk — do not weaken or bypass any existing gate for this new family).
5. Tests: pivot/vol-confirm math on a seeded weekly-resampled fixture (hand-computed expected
   breakout/no-breakout); resample correctness (a known daily OHLCV set resamples to the expected
   weekly bar).

## Guardrails
This is ADDITIVE discovery only — do not touch money-math, sizing, or existing gate thresholds.
No new dependencies (Streamlit/yfinance not needed — everything comes from daily_prices we already
ingest). Real hit counts only, no synthetic. `.v5` frontend touch only if you add a chip/label
distinguishing weekly vs daily breakout in an existing preset card — keep it minimal, tokens only.

## Output
`HANDOFF_GEMINI_weekly_breakout_scan_COMPLETED.md`: the resample approach, the weekly-breakout
function contract, the new preset + real hit count on 2026-07-10 data, test results, wiring notes.
