# FUTURE — Phase 2+ ideas (do not build until Phase 1 has 30 live days)

## Confirmed for Phase 2 planning
- Intraday SVRO monitor (S/V/R/O legs) via Fyers WebSocket — see `LIVE_DATA_FLOW.md`.
- SVRO post-session analyzer (Phase 1.5): replay 5-min bars for primary candidates and report would-have-been outcomes.
- Cloudflare Pages or static-host deployment for mobile dashboard.
- Trailing stop at 20DMA with shakeout allowance (Manas).
- Scale-in logic when setup strengthens (Manas).
- Additional setups: PDH breakout, VCP — separate signal streams, not merged.
- India VIX as fifth pillar; FII/DII flow ingestion.
- Sector RS overlay — only arm SVRO names in top-2 sectors that day.

## Captured during Phase 1 build (rejected for now)
- Auto-edit watchlist.csv from helper output (rejected: keep human-in-the-loop).
- Multi-strategy plug-in registry (rejected: speculative generality).
- Async fetch / parallel indicator compute (rejected: premature optimization).
- ORM / FastAPI dashboard (rejected: framework creep).
- LLM-generated narrative summary (rejected: opacity).
- Walk-forward parameter tuner (rejected: curve-fitting risk; only thresholds in config.yaml).

## Explicitly NOT planned
- Multi-user SaaS.
- Broker execution.
- Options / F&O modules.

## Open during 30-day live phase
- Calibrate Purple Dot volume thresholds against real backfill distribution.
- Layer A: revisit 2-day/0.75 vs 3-day/0.85 once we have observed candidate flow.
- Sector concentration cap on primary list (e.g. max 3 from one sector).
