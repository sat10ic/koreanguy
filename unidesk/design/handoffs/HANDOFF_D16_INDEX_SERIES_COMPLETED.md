# HANDOFF D16 NSE index series — COMPLETED (recent window)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-d16-index-series-grok46-20260829-001

## Outcome

- Adapter: `unidesk/momentum/data/indices.py` parses NSE `ind_close_all`
  (price index, not TRI) through `nse-archives`.
- Harvest: **59 sessions**, 2026-06-04 → 2026-08-28, **295 rows**, 5
  series (NIFTY_50, NIFTY_500, NIFTY_MIDCAP_150, NIFTY_SMALLCAP_250,
  INDIA_VIX). One date failed (2026-06-26). Parquet:
  `data/market/reference/indices.parquet`.
- R0: optional `midcap_above_sma50` gate. When set, source is
  `breadth_and_midcap150_sma50`; BULL/BEAR that disagree with Midcap 150
  vs SMA50 become CHOP. Midcap 150 was **above** SMA50 on 2026-08-28
  (close 23507.15). India VIX last 10.68.
- Finstack MCP was not connected. niftyindices.com `get_historical_index`
  failed Cloudflare JSON after installing cloudscraper.

## Files changed

- `unidesk/momentum/data/indices.py` (new)
- `unidesk/momentum/regime.py` (midcap gate)
- `unidesk/tests/test_indices_r0.py` (new)
- `unidesk/DECISIONS.md` (D16)
- `unidesk/TASKS.md`, `GOAL.md`, `HANDOFF.md`, `design/PHASE0_GAP.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q
.venv-orderflow/Scripts/python.exe unidesk/run_checks.py -> exit 0
Harvest: 59/60 sessions, 295 rows, 1 failed date
```

## Honest partials

- Window is 59 sessions, not 2016–. SMA200 is not computable yet.
- VIX is stored, not yet an R0 input (spec's z-score vs 1y needs ~252 days).
- PIT membership still not built (today's constituent list is not used).
- Finstack MCP still not wired.
