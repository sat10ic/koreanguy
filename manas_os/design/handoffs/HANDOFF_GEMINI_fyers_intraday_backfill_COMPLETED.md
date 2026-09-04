# HANDOFF_GEMINI_fyers_intraday_backfill — BLOCKED (auth)

**Executor:** Grok · **Date:** 2026-07-12 · **No git commit**

## Pre-flight

| Check | Result |
|-------|--------|
| Entrypoint | `manas_os.sources.intraday.fetch_and_store` + `FyersHistoryAdapter` (resumable windows, rate-limit → `RateLimitError`, commit per window) |
| Coverage helper | `tiered_coverage_symbols` in `intraday.py` |
| CLI dedicated backfill command | **None** named `backfill-intraday` — use library API or add CLI later |
| Fyers auth | `FyersProvider.from_config(...).is_available()` → **`False`** |

## STOP reason
**auth_needed** — Fyers token not available (expires 6am IST daily). Per handoff: do not attempt credential input. Maintainer must re-auth, then re-run.

## Ready when auth is restored
1. Call `fetch_and_store(conn, symbol=..., interval="5", start=..., end=...)` for full-universe 5-min windows.
2. Then 1-min for active set from `tiered_coverage_symbols`.
3. Interrupt mid-window → resume from returned `failed_at` / latest stored bar (already designed).
4. Spot-check 3 symbols: daily H/L must bound intraday bars.
5. Surface coverage via Alpha Lab table reading `intraday_bars` completeness (UI not wired this pass because run did not execute).

## Not done
- No bars fetched/stored.
- No Alpha Lab coverage UI (deferred until data exists).
- No completeness report (empty run).

## Do-not
No secrets logged. No fabricated bars.
