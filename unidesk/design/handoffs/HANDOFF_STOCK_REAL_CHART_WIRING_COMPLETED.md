# HANDOFF — Stock screen real-chart wiring — COMPLETED

Date: 2026-08-30. Resumes and completes the slice that HANDOFF.md's "To
continue" block recorded as PAUSED MID-SLICE (backend export done, frontend
wire NOT done). Scoped strictly to `unidesk/run_stock_history_export.py` +
`unidesk_terminal/`.

Attribution-ID: attr-unidesk-stock-real-chart-wiring-cline-20260830-001

## What was already done at pause time (verified, not assumed)

- `unidesk/run_stock_history_export.py` (new) — reads the real
  `data/bhavcopy` backlog via `InMemoryMarketStore`, emits up to 130 real
  daily bars per symbol (column-array JSON shape) for every symbol in the
  Tonight report, strictly at-or-before the report's `session_date`.
- `unidesk_terminal/src/data/stock_history_2026-08-28.json` (new, generated).
- `unidesk_terminal/src/data/stockHistory.ts` (new) — `getRealHistory(symbol)`
  returns real `Bar[]` or `undefined`, never fabricates.

## What this slice completed

1. `unidesk_terminal/src/components/widgets/StockChart.tsx` — now accepts an
   optional `history?: Bar[]` prop. Real bars win when supplied; otherwise it
   falls back to the labelled-synthetic `generateOhlc(symbol, price)`. The two
   are never blended in one series; `history` is in the effect deps so a
   symbol/report change re-renders.
2. `unidesk_terminal/src/screens/Stock.tsx` — calls `getRealHistory(symbol)`
   and passes the result down. When real history exists it renders a header
   line ("Real NSE bhavcopy · N daily sessions through <date>"). When it does
   not, it renders a **visible dashed note** stating the chart is synthetic
   and not market data — same honesty discipline as the existing
   "Illustrative candidate" banner (`dataSource === "illustrative"`). No
   silent blending.

## Verification (measured, not claimed)

```text
stock_history export integrity (direct read of the committed files):
  session_date 2026-08-28; 235 symbols; 29,979 bars
  future-leak symbols (bar session > report session_date): 0
  tonight symbols missing from history: 0
  last-close vs report-close mismatches: 0   (price lines sit on the final candle)

frontend:
  npx tsc -b                 -> clean
  npm run build (tsc+vite)   -> succeeds (2435 modules, dist emitted; only the
                               pre-existing >500kB chunk-size warning)
  npm run lint (oxlint)      -> 0 errors (1 pre-existing unrelated warning:
                               useMode fast-refresh in ModeContext.tsx)
```

## Honest limitations / still open

- The committed `stock_history_2026-08-28.json` is a build-time snapshot for
  the one existing real report (no live fetch, per the EOD integration plan).
  A newer report requires re-running `run_stock_history_export.py` and copying
  the new file in — same cadence as `tonight_<date>.json`.
- Illustrative fixture candidates (e.g. `dataSource === "illustrative"` rows
  whose symbols are not in the real 235) render the explicit synthetic
  fallback + note. That is intended, not a gap.
- No per-detector trust flag yet on the chart (the trading-logic audit's
  `base_breakout`/`reversal_reclaim` warnings remain a UI concern for a later
  slice; the generic "raw scan signals" disclaimer still applies).
- Size: the column-array JSON is 1.35 MB committed — acceptable for a static
  bundle; noted here so nobody "optimizes" it into a runtime fetch.

## Files

`unidesk/run_stock_history_export.py` (new, from the paused slice),
`unidesk_terminal/src/data/stock_history_2026-08-28.json` (new, generated),
`unidesk_terminal/src/data/stockHistory.ts` (new),
`unidesk_terminal/src/components/widgets/StockChart.tsx`,
`unidesk_terminal/src/screens/Stock.tsx`.

## Next slice (per UI_BACKEND_INTEGRATION_PLAN.md cadence)

History screen real-data wiring — its gate is now met: the N4 adjustment-basis
guard and the archive-attach future-map basis are both DONE (zero
`adjustment_basis_mismatch` in the real run; outcomes regenerated
stop-aware + net-of-cost under `outcome-labels-v4-net-cost`). That makes row 4
("History") wireable against the real event store.