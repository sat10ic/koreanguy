# Live Data Flow Design — Phase 2 Intraday (SVRO)

> Status: **DESIGN ONLY**. Do not implement until Phase 1 has run live for 30
> consecutive trading days and the tracker shows hit-rate 35–55% with mean
> R-multiple > 1.0.

## The data tiers we already use

| Tier | Source | Cadence | Used by |
|---|---|---|---|
| Daily OHLCV | Fyers REST `history` | EOD | fetch.py → ohlcv.db |
| Universe metadata | universe.csv | Manual | indicators.py, screen.py |
| Watchlist | watchlist.csv | Weekly manual | screen.py, verify.py |

## What Phase 2 SVRO needs
SVRO = **Start, Volume, Range, Opening** — Manas's intraday entry confirmation,
fired in the first ~15 minutes after the 09:15 IST open. The four legs:

- **S — Start:** today's open at or above prior close, or holds prior close on
  any pullback in the first 5 minutes.
- **V — Volume:** first 5-min bar prints ≥ `adv20 / 75` shares (1× normalized
  per-5-min average).
- **R — Range:** first 5-min bar's range ≥ 0.4 × `atr14`.
- **O — Opening:** breakout above the 5-min opening-range high (closing-bar
  basis), confirmed by a follow-through 5-min bar.

## Fyers API surface (already authorized for Phase 1)

| Endpoint | Use | Rate-limit-safe? |
|---|---|---|
| `quotes` REST | Snapshot LTP for many symbols | 10 RPS, fine for 30-name arm list |
| `depth` REST | Order-book snapshot | Optional — useful for liquidity sniff |
| `history` REST | Backfill 5-min bars | EOD only; not for live |
| **`data-socket` WebSocket** | Live tick + 5-min bar push | **Yes — primary live source** |
| `order-socket` | Order book updates | Not used (read-only system) |

WebSocket endpoint: `wss://api-t1.fyers.in/data/v3` (auth token in handshake).

## Data flow architecture

```
                       ┌────────── Phase 1 (EOD, today) ──────────┐
                       │                                          │
   verify.py ──writes──▶ output/svro_arm_today.json (top primary) │
                       │     {symbol, atr14, adv20, ref_close,    │
                       │      or_ceiling, or_floor, prior_score}  │
                       └──────────────────┬───────────────────────┘
                                          │ read at 09:10 IST
                                          ▼
   ┌────────── Phase 2 (intraday, tomorrow 09:15–10:00) ──────────┐
   │  intraday_monitor.py (single long-running process)           │
   │                                                              │
   │  09:10  load arms.json → subscribe Fyers WS for ≤ 30 syms    │
   │  09:15  state machine WAITING for each arm                   │
   │  09:20  evaluate Liquidity gate (vol ≥ adv20/30)             │
   │  09:20  S leg: LTP ≥ prior_close                             │
   │  09:20  V leg: 5-min vol ≥ adv20/75                          │
   │  09:20  R leg: 5-min range ≥ 0.4 × atr14                     │
   │  state → ARMED (all of S/V/R passed)                         │
   │                                                              │
   │  09:25–10:00  poll for O leg:                                │
   │    if 5-min close > or_ceiling → state TRIGGERED             │
   │    fire Telegram alert, write to intraday.db                 │
   │    if 10:00 elapsed without trigger → state EXPIRED          │
   └──────────────────┬───────────────────────────────────────────┘
                      │ writes
                      ▼
   data/intraday.db (table: intraday_5min, table: svro_events)
   output/intraday_alerts.log
   Telegram chat (separate "SVRO Live" channel)
```

## Database additions

```sql
-- 5-min bars, only for arm list, only on the trading day
CREATE TABLE intraday_5min (
  symbol TEXT, ts DATETIME,
  open REAL, high REAL, low REAL, close REAL, volume INTEGER,
  PRIMARY KEY (symbol, ts)
);

CREATE TABLE svro_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT, signal_date DATE, ts DATETIME,
  state TEXT,             -- WAITING, ARMED, TRIGGERED, EXPIRED
  s_pass INTEGER, v_pass INTEGER, r_pass INTEGER, o_pass INTEGER,
  trigger_price REAL, notes TEXT,
  FOREIGN KEY (symbol, signal_date) REFERENCES positions(symbol, signal_date)
);
```

## Connection between Phase 1 and Phase 2

This is the load-bearing design choice:

1. `verify.py` already writes `output/svro_arm_today.json` (built tonight).
2. `intraday_monitor.py` (Phase 2) consumes it at 09:10 IST tomorrow morning.
3. Phase 2 only subscribes to ≤ 30 symbols — well inside Fyers WS quota.
4. SVRO triggers update `positions.notes` with timestamps and tick-level entry
   price — but **do NOT change state** of the daily tracker. The Phase 1
   PENDING_CONFIRM → ACTIVE transition is unchanged. SVRO is decoration.
5. EOD, Phase 1 `track.py` runs as normal. The SVRO trigger metadata enriches
   the entry_price (intraday avg, not next-day close) when present.

## Failure modes and graceful degradation

| Failure | Behavior |
|---|---|
| WebSocket disconnect | Reconnect with exponential backoff; missed bars ignored — system uses next available bar |
| Token expired pre-market | Watchdog Telegram alert; intraday_monitor exits cleanly |
| `svro_arm_today.json` missing | intraday_monitor exits with "no arms"; Phase 1 EOD still runs |
| Single-symbol data drop | That arm's state stays WAITING until expiry; others continue |
| Fyers rate-limit on REST fallback | Drop REST fallback; rely on WS only |

## Phase 1.5 — shadow SVRO (build BEFORE Phase 2)

Build this first — costs nothing, banks evidence:

```
scripts/svro_replay.py     # nightly, EOD
  → reads svro_arm_today.json from this morning
  → fetches 5-min bars for each arm via Fyers REST history (resolution=5)
  → replays the SVRO state machine offline
  → writes output/svro_shadow_history.csv:
     symbol, date, would_trigger, trigger_ts, trigger_price,
     follow_through_pnl_at_15:30
```

After 30 days of shadow data:
- If hit-rate of would-trigger arms > 50% → Phase 2 worth building.
- If < 35% → SVRO rules need adjustment for NSE before live deployment.
- Threshold the prior_score (in `verify.py::_write_svro_arm`) at the level that
  isolates the top 50% of shadow winners.

## Live data costs to plan for

- WebSocket bandwidth: ~30 symbols × 5 ticks/sec × 6.5h = ~3.5M messages/day. Trivial.
- Storage: ~78 5-min bars × 30 syms = 2,340 rows/day in intraday_5min. Trivial.
- Latency requirement: only need 5-min granularity. SVRO doesn't require sub-second.

## What to NOT build

- Sub-second tick aggregation (5-min bars suffice).
- Multi-broker abstraction (Fyers only).
- Retry queues for missed alerts (Telegram is best-effort by design).
- Market-on-open auto-orders (paper trading only — Phase 1 invariant).
- Self-tuning SVRO thresholds (curve-fitting risk).

## Implementation order when Phase 2 unlocks

1. `intraday.db` schema + migration.
2. `scripts/svro_replay.py` (Phase 1.5, no live data).
3. Fyers WebSocket wrapper `scripts/_fyers_ws.py`.
4. `scripts/intraday_monitor.py` consuming arm list.
5. Cron at 09:10 IST starts monitor; supervisord-style auto-restart on crash.
6. Separate Telegram channel for SVRO triggers (keep daily channel uncluttered).
