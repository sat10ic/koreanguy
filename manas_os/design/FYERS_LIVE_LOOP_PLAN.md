# FYERS_LIVE_LOOP_PLAN — Live-Feel Wave (Task #21) — PROPOSAL, no code

Date: 2026-07-11. Status: PROPOSAL only — nothing in this doc is built. Gated on
explicit user go-ahead (see DECISIONS NEEDED at the end).

Builds directly on `manas_os/design/LIVE_LOOP_FABLE.md` (Fable's architecture
review of the live intraday loop, 2026-07-06) and `manas_os/design/
WAVE_M_CONFORMANCE.md` (Opus's TradeTM-conformance audit, 2026-07-10). This doc
does not re-litigate either — it restates their binding decisions, cites them,
and adds the one layer neither fully specified: **what actually gets built on
the wire to make the desk feel alive**, and in what order.

---

## 1. Goal, restated in one line

Make the desk **feel like it's watching the market**, not like a form you
reload — ticking prices, moving positions P&L, armed names lighting up as they
cross triggers, and the pipeline progress bar advancing live — without
pretending the tool executes trades (it never does; manual execution stays,
per every prior doc).

### What needs a live feed vs what is already fake-live today

| Feels live because... | Needs Fyers WS/streaming data | Can be built TODAY on EOD/existing polling |
|---|---|---|
| Ticking LTP on POSITIONS, TRADE PLAN, SCANNERS chart | **Yes** — intraday price only exists via Fyers | — |
| Positions P&L updating in real time | **Yes** (LTP feed) | Currently: static EOD close, page-reload-to-refresh |
| Armed names "lighting up" when price crosses trigger zone (LIVE_LOOP_FABLE §2.2 FSM) | **Yes** — the FSM transitions on live ticks | The FSM *states* (ARMED, evening pre-arm) already exist conceptually as tonight's armed list — just not animated |
| MARKET pipeline progress bar (`stage 18/26 ETA`) advancing without a manual reload | **No** — this is the nightly `run-eod` subprocess, already server-side | **Yes today** — `/api/pipeline/status` (WAVE_M M-adjacent, WIREFRAMES_V4 V4-T2) just needs the browser to *poll* it instead of the user hitting `⟳ UPDATE`. This is the cheapest live-feel win in the whole plan and needs zero Fyers work. |
| Debate/Shortlist/Journal tabs | **No** — these update once per evening pipeline run, not intraday | Auto-refresh on a coarse interval (or SSE from the same pipeline-status channel) is enough |

So "live feel" splits cleanly into two independently shippable things:
**(A) intraday WS-driven ticking (needs Fyers, the hard/new part)** and
**(B) push/poll UI refresh for data that already updates server-side but
currently requires a manual click (cheap, no Fyers dependency, ship first)**.

---

## 2. Stack decision — confirmed from the codebase, no new framework

- **Backend is FastAPI already.** `manas_os/api/app.py:51` —
  `app = FastAPI(title="Manas AI Trading OS", version="0.0.1")`, run via
  `uvicorn` (`manas_os/api/__main__.py`). FastAPI supports `@app.websocket(...)`
  natively (Starlette-based) — no new dependency needed for the browser-facing
  WS endpoint.
- **Frontend is React 18 + Vite**, confirmed in `manas_os/desk/package.json`:
  `react@^18.3.1`, `vite@^5.4.1`, no state-management library beyond React's
  own (context/hooks pattern already used for beg/exp toggle per
  WIREFRAMES_V4). A WS client is a `useEffect` + `WebSocket` + `useState`
  hook — no new frontend dependency.
- **Charting is `lightweight-charts@^4.2.3`** (`manas_os/desk/package.json`,
  used in `manas_os/desk/src/ChartDrawer.jsx`). Lightweight Charts natively
  supports `series.update(bar)` for incremental single-bar/point pushes
  without re-rendering the whole series — this is the exact primitive needed
  to tick a chart from a WS message. Unverified: whether ChartDrawer.jsx
  today wires a subscribable update path or only ever calls `setData()` once
  per full payload — confirm in `manas_os/desk/src/ChartDrawer.jsx` before
  building slice C3 below.
- **What's genuinely new:** one small, separate backend process
  ("streamer") that (a) opens the Fyers WebSocket, (b) subscribes to the
  armed-list symbols, (c) applies the FSM from LIVE_LOOP_FABLE §2.2 to each
  tick, and (d) fans out FSM-state-changes + LTP over a FastAPI `WebSocket`
  route to the browser. No new framework anywhere in this stack — it's
  Fyers-WS-in, FastAPI-WS-out, React-state-in-between.

---

## 3. What legacy/ssrvol genuinely provides — read, not assumed

`EXECUTOR_PLAYBOOK.md:129` currently says *"6.1 Fyers WS client adopted from
legacy/ssrvol (adopt-not-import): reconnect + dedupe tested with a fake WS
server fixture."* **This is not accurate and needs correcting before Wave 6
executes** — I read every file listed and confirmed the following:

| Capability | Genuinely exists in ssrvol? | Evidence |
|---|---|---|
| Fyers OAuth / auth-code exchange / token cache | **Yes** | `legacy/ssrvol/fyers_auth.py` — full `SessionModel` login flow (`generate_auth_url`, `exchange_auth_code`), token cached to `.fyers_token.json` with `expires_at`, `get_access_token()` never prompts/raises, `token_status()` → ready / missing_app_id / missing_token. Real, reusable. |
| Fyers **WebSocket** subscribe | **No.** | Grepped the whole package for `websocket`/`WebSocket`/`FyersDataSocket`/`ws.` — zero hits in `fyers_provider.py` or anywhere in `ssrvol/*.py`. `FyersProvider.get_snapshot()` (`legacy/ssrvol/providers/fyers_provider.py:77`) calls `client.quotes({...})` — a **REST batch quote call** (`fyersModel.FyersModel`), batched at `BATCH_SIZE = 50`. There is no streaming client anywhere in this repo. |
| "Live" updates today | REST **polling**, not push | `legacy/ssrvol/app.py:542` — `alert_poll_loop()`, an `asyncio` loop that calls `run_one_alert_poll()` every `poll_interval_s=45` (default 45s), which calls `build_dashboard_rows()` → `provider.get_snapshot()` → the REST quotes call above. This is the entire "live" mechanism ssrvol has: poll REST every 45s inside a FastAPI lifespan background task. |
| Reconnect handling | **N/A — nothing to reconnect.** REST calls just fail-and-retry-next-poll (`try/except` around each batch, logs a warning, moves on). There is no persistent connection, so there's no reconnect/backoff logic to adopt. |
| Dedup / idempotent alert state | **Partially yes**, but for a *45s-poll* cadence, not tick-level. `alert_poll_loop` → `evaluate_and_fire_alerts()` (`app.py:452`) tracks `alert_state` per `(symbol, date)` with `false_streak`, `fires_today`, `max_alerts_per_symbol_day`, and a `once_per_day` / `re-arm` policy read from `db.get_alert_state`/`db.upsert_alert_state`. This is a genuinely reusable **pattern** (per-symbol-per-day state machine idea) but it is not tick-dedup and not a WS reconnect story — LIVE_LOOP_FABLE §2.2's FSM (key = `(symbol, trade_date, setup_id)`, monotonic `bar_ts` guard) is the correct design and is **not** what ssrvol implements; ssrvol's version is coarser (poll-count streaks, no bar-timestamp monotonicity guard).
| Telegram send | **Yes, solid** | `legacy/ssrvol/telegram.py` — HTML `parse_mode`, credential precedence (env > config.yaml `telegram:` block > settings table — matches this repo's `config.yaml`-gitignored pattern), batches multiple triggers into one message, retries once after 5s, never raises. Directly adoptable (copy-pattern, not import, per anti-mashup rule). |
| Market-hours / trading-day calendar | **Yes** | `legacy/ssrvol/calendar.py` — `pandas_market_calendars` XNSE primary path, weekday-only fallback if the dependency is missing (explicitly flagged as NOT accounting for holidays in that fallback branch — `TODO` at line 53). Directly adoptable; note the fallback gap for the session-clock work in LIVE_LOOP_FABLE §2.7. |

**Bottom line: ssrvol is a REST-polling dashboard with a real Fyers OAuth
flow and a real Telegram sender bolted on — it is not a WebSocket seed.**
Everything about live *streaming* (WS connect, subscribe, on-tick handler,
reconnect/backoff, gap-backfill on reconnect) is new work; only auth,
Telegram delivery, and the market-calendar helper are genuinely adopt-ready.
This changes the Wave 6 estimate in `EXECUTOR_PLAYBOOK.md` — 6.1 should read
"Fyers auth + Telegram sender + calendar adopted from ssrvol; **WS client
built new** against `fyers_apiv3`'s `FyersDataSocket` (unverified — confirm
whether the installed `fyers-apiv3` package version exposes it; not
exercised anywhere in this codebase today)."

---

## 4. Architecture

### 4.1 Components (new work in bold)

```
Fyers WS (external)
   │  ticks for armed-list symbols only
   ▼
[**streamer** — new asyncio process/task]
   │  - FyersDataSocket subscribe (adopt Fyers auth from ssrvol; WS client is new)
   │  - applies FSM (LIVE_LOOP_FABLE §2.2) per tick, SQLite WAL, single writer
   │  - market-hours gate (adopt ssrvol/calendar.py pattern)
   │  - reconnect + backfill-from-history on gap (LIVE_LOOP_FABLE §2.5)
   ▼
[FastAPI **`/ws/live`** route — new] ── fans out FSM-state-change + LTP events
   │  one process, existing `app.py`, same uvicorn instance
   ▼
[React **`useLiveFeed()`** hook — new] ── WebSocket client, reconnect w/ backoff
   │  updates React state keyed by symbol
   ▼
POSITIONS (live P&L) · SCANNERS/SHORTLIST (armed-name status badge) ·
TRADE PLAN (live LTP vs entry zone) · Chart (lightweight-charts incremental update)
```

### 4.2 One-writer ownership (per `EXECUTOR_PLAYBOOK.md:20`, "one writer per
metric — a number the payload already states is never re-derived in JSX")

- The **streamer** is the single writer of live FSM state and live LTP —
  persisted in SQLite (same DB, WAL mode, per LIVE_LOOP_FABLE §2.2), keyed
  `(symbol, trade_date, setup_id)`.
- The FastAPI `/ws/live` route is a **pure fan-out** — it reads streamer
  state and pushes it, it never computes anything itself.
- React never recomputes P&L, RVOL, or FSM status client-side from raw
  ticks — it only renders whatever field the payload already states, exactly
  the same "no re-derive in JSX" rule already governing the EOD payloads.
- Positions P&L displayed live = `(live_ltp - entry) * qty`, computed once
  server-side in the streamer (or in a thin FastAPI handler reading the
  latest cached LTP), never twice.

### 4.3 Market-hours gating

Reuse `legacy/ssrvol/calendar.py`'s pattern (`is_trading_day`, `is_market_hours`,
XNSE calendar with weekday-only fallback) — adopt-not-import, ported into
`manas_os/market_calendar.py` (already imported in `api/app.py:26`; confirm
whether it already has equivalent logic before duplicating — unverified,
check `manas_os/market_calendar.py` before building). The streamer refuses
to open a WS connection or emit anything outside 09:00–15:30 IST on a trading
day; the browser hook shows a static "market closed" badge instead of
attempting to connect.

### 4.4 Reconnect / dedup

Directly reuses **LIVE_LOOP_FABLE §2.2 and §2.5**, cited not reinvented:
- FSM keyed `(symbol, trade_date, setup_id)`, transition legal only if
  `bar_ts > last_transition_bar_ts` — this is what makes a WS reconnect
  replay a no-op (§2.2).
- On reconnect: exponential backoff, then backfill the gap from Fyers 1-min
  history API and replay through the same FSM before resuming live (§2.5) —
  idempotent by construction, so replay is safe.
- The FastAPI `/ws/live` → browser leg needs its **own** lightweight
  dedup: the browser may reconnect (tab refocus, laptop sleep) and should
  not double-apply a state it already has — send a monotonic
  `seq` or `bar_ts` per message and have the React hook ignore anything not
  newer than what it already holds for that symbol. This second dedup layer
  is new (LIVE_LOOP_FABLE's dedup story stops at the streamer↔Fyers leg; it
  doesn't cover the browser↔backend leg, which is specific to this project's
  local-web-app shape and not something ssrvol needed since it had no
  browser push).

### 4.5 Armed-list FSM

Reused verbatim from **LIVE_LOOP_FABLE §2.1–§2.3**, not reinvented here:
`IDLE → ARMED(evening) → TRIGGERED → ALERTED → CONFIRM_PENDING → CONFIRMED →
IN_TRADE`, with `EXPIRED`/`EXPIRED_MOVED` branches, 25-min TTL on ALERTED,
zone-based revalidation at confirm time (§2.3's "confirm = revalidation, the
core fix"). This doc's only addition: the FSM's `TRIGGERED`/`ALERTED`
*state itself* is now also a UI field, pushed to SCANNERS/SHORTLIST rows and
TRADE PLAN so the badge lights up — the FSM already existed as a decision
model in LIVE_LOOP_FABLE; this doc's job is only "how does that state reach
the browser," not re-deriving the state machine.

---

## 5. Scope split

### MVP — ships the "feels alive" sensation with the least new risk

1. **Zero-Fyers-dependency win first (§1 table, column B):** poll
   `/api/pipeline/status` from the MARKET tab every few seconds while a run
   is in flight (already spec'd fields in WIREFRAMES_V4 V4-T2 / it may
   already exist — confirm in `api/app.py` before treating as new). This
   alone kills the "click reload to see progress" complaint for the nightly
   run and needs no Fyers work at all. Ship this before anything WS-based.
2. **Positions live P&L** (POSITIONS tab) — the highest-value, lowest-risk
   Fyers-WS use: subscribe only to symbols in *open positions* (small,
   bounded set), stream LTP, compute P&L server-side, push over `/ws/live`.
   No trigger logic, no alerting, no Telegram — just a ticking number and a
   ticking sparkline point. This is intraday's "hello world" and de-risks
   the WS plumbing before anything alert-shaped touches it.
3. **Armed-name status badge** on SCANNERS/SHORTLIST/TRADE PLAN — reads the
   FSM state already being computed for positions-scale work in (2), applied
   to the evening armed list (LIVE_LOOP_FABLE §2.1, ≤10–15 names). Shows
   IDLE/ARMED/TRIGGERED/ALERTED as a colored chip, no Telegram push yet.
4. **Chart incremental tick** on the currently-open chart panel only (not
   every row) — `lightweight-charts` `series.update()` for the one symbol in
   view.

### Later — the bigger, riskier capability (do not build in this wave)

- Full intraday execution triggers: EP 5-min ORB entry math, strong-start
  2–3-min confirm window, D2 branch classification, gap-down 10-min
  protocol — this is `WAVE_M_CONFORMANCE.md` M10 ("intraday layer... behind
  #21"), explicitly deferred there too. MVP above surfaces *state*, not
  *entry signals*.
- Telegram digest / confirm-revalidation loop (LIVE_LOOP_FABLE §2.3, §2.4) —
  requires `agents.telegram_live` flipped true, which the user has not
  authorized (see §7).
- Weekend/backtest replay harness as a *product feature* (it's needed as a
  *dev/test tool* before any of this ships — see Build Order below, which is
  different from shipping it to the user).

---

## 6. Build order — Codex-sized slices

Each slice is independently testable; later slices depend on earlier ones.
Per this repo's standing rule (LIVE_LOOP_FABLE's own build-order note,
`EXECUTOR_PLAYBOOK.md` 4.1), **the replay harness comes first** — nothing
below it should be built against live Fyers data as the only test path,
since weekends/market-closed hours mean live data is unavailable most of the
time this gets developed.

- **L1 — Replay harness.** Record or synthesize a session of Fyers-tick-shaped
  events to a fixture file; a `--replay <date> --speed Nx` driver replays them
  through whatever FSM/streamer code exists. Assertion from day one: replaying
  the same session twice produces zero duplicate transitions. This is also
  the only way to develop/test slices L2+ on a weekend. *Acceptance:* replay
  driver runs against a fixture with zero network calls; dedupe assertion
  passes.
- **L2 — Streamer skeleton + FSM (no Fyers yet).** Build the
  `(symbol, trade_date, setup_id)`-keyed FSM in SQLite per LIVE_LOOP_FABLE
  §2.2, driven only by the L1 replay fixture. *Acceptance:* FSM harness green
  incl. dedupe (mirrors `EXECUTOR_PLAYBOOK.md` W4 done-test pattern already
  used for the Telegram FSM).
- **L3 — Fyers WS client (new, not adopted).** Wrap `fyers_apiv3`'s
  streaming client (confirm module name/import path — unverified, not present
  in ssrvol; check installed `fyers-apiv3` version's docs/`__init__.py`
  before assuming `FyersDataSocket` is the right symbol), subscribing only to
  a small symbol set. Auth token sourced via the adopted `fyers_auth.py`
  pattern. *Acceptance:* connects during market hours to a small watch set,
  logs ticks, disconnects cleanly outside market hours; chaos test — kill the
  socket mid-session, assert reconnect + gap-backfill-or-DATA-DOWN messaging
  (LIVE_LOOP_FABLE §2.5, §3.2).
- **L4 — `/ws/live` FastAPI route + browser dedup.** Fan out streamer state
  over a native FastAPI WebSocket; React `useLiveFeed()` hook with
  reconnect+backoff and the `seq`/`bar_ts` dedup described in §4.4.
  *Acceptance:* two browser tabs open simultaneously both see identical,
  monotonic state; killing and restarting the FastAPI process doesn't crash
  the browser tab (auto-reconnects).
- **L5 — MVP surface: Positions live P&L.** Wire `/ws/live` LTP for
  open-position symbols into POSITIONS tab; P&L computed server-side per
  §4.2. *Acceptance:* with the replay harness driving fake ticks, POSITIONS
  P&L updates without a page reload; screenshot before/after a simulated
  tick.
- **L6 — MVP surface: armed-name status badges.** Apply the evening
  pre-arm list (LIVE_LOOP_FABLE §2.1) to the FSM; badge on
  SCANNERS/SHORTLIST/TRADE PLAN rows. *Acceptance:* a replay-driven trigger
  flips IDLE→ARMED→TRIGGERED visibly; no Telegram side effect fires (the
  badge is UI-only in this slice).
- **L7 — Pipeline-status live poll (can actually ship independently/first
  if desired — no dependency on L1–L6).** MARKET tab polls
  `/api/pipeline/status` during an in-flight run. *Acceptance:* progress bar
  advances without a manual `⟳ UPDATE` click.
- **L8 — Chart incremental tick.** `series.update()` on the open chart panel
  only. *Acceptance:* one symbol's chart ticks live while others on the page
  don't re-render.
- **Gated, not in this wave — L9+.** Telegram digest wiring, confirm/
  revalidation flow, full intraday execution triggers (WAVE_M M10). These
  require the graduation criteria in §7 to be met first.

---

## 7. Gates — this wave does not proceed past L4 without explicit sign-off

1. **User go-ahead on this doc** — this is a proposal; nothing here is
   authorized to build yet.
2. **Fyers auth working end-to-end**, including the **6am-IST daily token
   expiry**. `fyers_auth.py`'s `cache_access_token(ttl_hours=18.0)` means a
   token obtained ~noon expires ~6am next day — the existing ssrvol flow is
   fully manual (`interactive_login()` prints a URL, waits for pasted
   `auth_code`). **UX gap to design, not yet solved by ssrvol or this doc:**
   the desk needs either (a) a one-click re-auth affordance surfaced in the
   app when `fyers_auth.token_status()` != "ready" (ssrvol already exposes
   `/api/fyers/status`, `/api/fyers/auth-url`, `/api/fyers/auth-code` REST
   endpoints doing exactly this — directly adoptable pattern), or (b) an
   8:45am pre-flight check + Telegram nudge per LIVE_LOOP_FABLE §2.5. Either
   way, don't assume the token is silently valid every morning.
3. **PAPER / dry-run first, always.** `config.get("agents.telegram_live",
   False)` (`manas_os/agents/signals.py:43`) is the existing kill switch —
   confirmed False by default, tested in `test_agent_signals.py` /
   `test_agent_coach.py`. This wave does not flip it. Everything through L8
   is UI-only (badges, ticking numbers) with **no Telegram send path**
   touched at all — Telegram wiring is explicitly out of scope until a
   separate, later, explicitly-approved wave.
4. Fyers credentials live in gitignored `config.yaml` (confirmed pattern —
   `fyers_auth.py`'s `_config_fyers_value()` reads `config.yaml`'s `fyers:`
   block, and `telegram.py`'s `_load_config_yaml_telegram()` does the same
   for `telegram:`) — no credential handling changes proposed here beyond
   reusing that existing precedence (env > config.yaml > settings table).

---

## 8. Honest risks

- **Fyers token expiry mid-session is not cosmetic** — a WS auth-close at
  11am with no graceful handling looks like "the market went quiet," which
  is exactly the "silent death" failure mode LIVE_LOOP_FABLE §2.6/§3.4 warns
  about. L3's acceptance test must include an auth-failure chaos case, not
  just a network-drop case.
- **WS reconnect double-fire** is a real, previously-identified risk
  (LIVE_LOOP_FABLE's #5 ranked blind spot) — the FSM's monotonic `bar_ts`
  guard is the fix, but it must be tested (L1/L2's replay-twice-zero-new-
  transitions assertion), not assumed correct because it's "in the design."
- **Market-hours-only testability.** Real Fyers WS data only exists
  09:00–15:30 IST on NSE trading days — most development time (evenings,
  weekends, the exact time an agent session runs) has zero live data to
  test against. The replay harness (L1) is not optional scaffolding, it is
  the only way this gets built and tested outside market hours; treat it as
  the actual first deliverable, not a nice-to-have.
- **This is the single largest new capability in the plan.** Every other
  wave in `EXECUTOR_PLAYBOOK.md` (Telegram FSM, fundamentals ingestion, etc.)
  reads/writes SQLite on a schedule; this wave introduces the project's
  first long-lived external network connection with real-time state — new
  failure modes (partial ticks, out-of-order delivery, socket half-open)
  that nothing else in the codebase has had to handle. Budget real
  engineering time, not a slice or two.
- **`EXECUTOR_PLAYBOOK.md:129`'s "adopted from ssrvol" framing for the WS
  client is currently wrong** (see §3) — if that line is used to scope Wave
  6 effort without correction, the estimate will be too low.
- **`ChartDrawer.jsx`'s incremental-update readiness is unverified** — confirm
  it supports `series.update()` on an already-mounted series before assuming
  L8 is trivial; if it currently only calls `setData()` on full payload
  reload, L8 needs a small refactor first.

---

## DECISIONS NEEDED FROM USER

1. **Go/no-go on this proposal** — proceed to L1 (replay harness) or hold?
2. **Fyers re-auth UX**: adopt ssrvol's REST-endpoint pattern (manual paste
   of auth_code/URL into the app) as the interim solution, or is a fully
   automated headless re-auth expected? (Fully automated Fyers login without
   user interaction is not something ssrvol does today and may not be
   possible depending on Fyers' 2FA requirements — needs a decision before
   L3/§7.2 is finalized.)
3. **Scope confirmation on MVP** — is Positions-live-P&L + armed-badge
   (L5/L6) the right "first live thing," or does the user want the
   pipeline-status live-poll (L7, zero Fyers risk) shipped alone first as a
   standalone quick win, decoupled from the Fyers work entirely?
4. **Graduation criterion for eventually flipping `agents.telegram_live`** —
   not decided in this doc; LIVE_LOOP_FABLE §3.3 proposes "≥40 paper alerts
   with slippage-adjusted expectancy > 0 and zero dedupe/silent-failure
   incidents" — does the user want to adopt that number now, or defer the
   decision until L1–L8 are actually built and there's real paper data to
   set a bar against?
5. **`EXECUTOR_PLAYBOOK.md:129` correction** — confirm this doc's finding
   (§3) should be folded back into `EXECUTOR_PLAYBOOK.md` Wave 6 language so
   future execution doesn't understate the WS-client effort.
