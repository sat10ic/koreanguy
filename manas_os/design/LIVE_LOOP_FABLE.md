# LIVE INTRADAY LOOP — Fable Architecture Review (Task #21)

Date: 2026-07-06 · Reviewer: Fable (senior systems architect pass)
Scope: stress-test of the proposed HYBRID live loop (loose deterministic net → LLM analyst → Telegram human veto → journal auto-log → weekend retro).
Binding constraints honored throughout: rules-first / explainable, MANUAL execution only, single-user localhost, beginner-safe, public data.

---

## 1. THE BLIND SPOT

### The one that blows it up: **the design has no concept of time — every signal is treated as durable, but every intraday signal has a half-life of minutes.**

Walk the pipeline with a clock in hand:

- Deterministic net fires on a 1-min/5-min bar close: **T+60–300s** after the move starts.
- Haiku first pass: +5–15s. Sonnet deep pass with a rendered chart snapshot: render + upload + inference = **+30–120s**.
- Telegram delivery + notification: +seconds.
- **Human reaction: +5 minutes to +4 hours** (working person, meetings, asleep at 9:15 logic below).
- User taps BUY → system journals **the entry/stop/size/R:R computed at trigger time**.

By confirm time, the gap-and-go move the loose net was built to catch — the fastest-decaying signal in the entire system — has moved 1–3%. The stop distance is now wrong, the position size (computed from that stop) is wrong, and the R:R that justified the alert **no longer exists**. Three failure modes, each worse than the last:

1. **The journal records fiction.** Planned entry ≠ any price the user could have gotten. There are no broker fills in this system (manual execution — the user places the order in the Fyers/broker app separately), so nothing corrects it.
2. **The weekend retro calibrates on fiction.** "Does 0.9 confidence = 90% right?" is measured against P&L from entries nobody took at prices nobody got. The calibration loop — the design's pride — becomes an engine that *systematically miscalibrates*, then "tunes setups" on that poison. This is the compounding failure: not a missed trade, but a feedback loop confidently walking the system away from reality.
3. **The beginner-safety inversion.** The user learns that alerts are always "a bit late," starts chasing extended entries to "not miss it" — the tool trains the exact behavior (chasing, oversized risk from stale stops) it exists to prevent.

The fix is not "make the LLM faster." The fix is: **confirmation must be validated against *current* state, never against the alert snapshot** — and every alert must carry an explicit TTL and an entry *zone*, outside of which the system refuses to journal the plan. Section 2 builds the whole architecture around this.

### The rest, ranked

2. **The human veto is fiction at 9:15 for a working person.** Either the user misses everything (tool is ceremony) or rubber-stamps from a meeting (the "manual confirm" degrades into de-facto auto-trading psychology — one tap, no judgment — while keeping none of automation's consistency). Unaddressed, this decides whether the product exists. Fixed via the **evening pre-arm ritual + two fixed digest windows + auto-expire** (§2.3).
3. **Opening-window data quality.** "Volume surge" at 9:16 is statistically meaningless (surge vs *what* baseline — one minute of volume?). Pre-open auction prints, wide spreads, and circuit-limit opens land exactly when the loose net is loosest. The high-recall net will fire on dozens of NSE names in the first 15 minutes — the false-positive flood arrives precisely when the LLM budget, the human, and the data are all at their weakest. Fix: time-of-day-normalized RVOL (the ssrvol Pine port already computes this — adopt it), no volume triggers before the first 15-min bar completes, ASM/GSM/circuit exclusion from the ChartsMaze flags you already ingest.
4. **LLM on the critical path.** As proposed, alerts wait for the analyst layer. A timeout, rate-limit, or budget exhaustion silently delays the deterministic alert — the one part that's actually time-critical. The LLM must *enrich*, never *gate* (§2.4).
5. **Double-fire on reconnect / no idempotency story.** Fyers WS drops mid-session (it will), reconnect replays or re-delivers ticks, the net re-triggers, the user gets the same alert twice — or worse, a "fresh" alert for a now-extended name. Needs keyed, persisted, monotonic state (§2.2).
6. **Silent death.** APScheduler process crashes at 9:05, token expired at 8:59, WS never connects — and the user's phone stays quiet, which looks identical to "no setups today." Absence must be made loud (§3.3).
7. **Retro overfitting a tiny sample.** ~5 alerts/day ≈ 100/month. Weekly "tuning" on ~25 outcomes is fitting noise. Report weekly; *tune* quarterly, by human decision, with confidence intervals shown (§2.6).
8. **Look-ahead in "prior-big-move" / "fresh-leg".** If computed live from intraday-inclusive data, today's move contaminates its own precondition. All arming features must be computed **the previous evening from EOD data only** (§2.1) — which also happens to solve half of problem #3.
9. **Calendar edge cases.** NSE holidays, Muhurat special session (evening!), half-days, and the 9:00–9:08 pre-open auction. One session-clock table, not scattered `if` checks (§2.7).

---

## 2. THE FOOLPROOF REDESIGN

Center of gravity moves in two directions: **decision-making moves to the evening** (where latency is free and the user is available), and **execution-window interaction compresses into fixed digest checkpoints** (where a working human can actually show up). The live loop itself becomes a dumb, fast, deterministic machine whose every message carries a TTL.

### 2.1 Evening pre-arm (the real brain, runs at ~19:00 with the EOD pipeline)

- The existing EOD engine (Setups feed + watchlist) produces tomorrow's **armed list**: max ~10–15 names.
- For each armed name, compute **the night before, from EOD data only**: trigger level, entry *zone* [zone_lo, zone_hi] (e.g., pivot to pivot + 0.5×ATR), stop, size (from user's fixed per-trade risk), min R:R floor, "prior-big-move" and "fresh-leg / not-extended" flags. No intraday computation of arming features, ever → look-ahead structurally impossible.
- **This is where the LLM does its deep work** — Sonnet, chart snapshot, full datapoints, no latency pressure, one batch, predictable cost. Verdict {is_clean_fresh_leg, confidence, cited_evidence, plain_english_read} attaches to the armed record.
- **Pre-authorization of intent:** the user reviews the armed list in the evening (in the app or via one Telegram digest) and marks each name APPROVED / SKIP. Approval means: "if this triggers inside its zone tomorrow, I intend to place this order manually." This is the human judgment, exercised when the human has judgment to give. It is *not* order routing — the user still types the order into the broker app — so the manual-only / outside-SEBI-algo posture is fully preserved, and arguably strengthened: the human decision is now deliberate rather than a 9:17 panic tap.
- A small **wildcard budget** (≤3/day) lets the loose net surface un-armed movers (the "dynamic strong moves" the owner doesn't want to miss) — but wildcards get Haiku-only enrichment and are clearly badged UNPLANNED in the digest. If the user finds over months that wildcards underperform armed names (the ledger will show it), cut them.

### 2.2 Per-symbol state machine (persisted in SQLite, single writer)

```
IDLE → ARMED(evening) → TRIGGERED → ALERTED → CONFIRM_PENDING → CONFIRMED → IN_TRADE
                              ↘ EXPIRED(ttl) ↘ EXPIRED_MOVED(revalidation fail)   ↓
                                                                    EXIT_ALERTED → CLOSED
```

- **Key = (symbol, trade_date, setup_id).** Every transition is an idempotent INSERT-or-ignore on this key plus a monotonic bar-timestamp guard: a transition is legal only if `bar_ts > last_transition_bar_ts`. WS reconnect replaying ticks/candles cannot re-fire — the FSM row already says TRIGGERED. One trigger per symbol per day, hard.
- All state in SQLite (you already run it), WAL mode, so a process restart mid-session resumes exactly — the loop reloads FSM rows at boot and continues. No in-memory-only state anywhere.
- **TRIGGERED → ALERTED** requires: price inside [zone_lo, zone_hi] ∧ time-of-day-normalized RVOL ≥ threshold (first 15-min bar onward only) ∧ not ASM/GSM/circuit ∧ market_mode ≠ DEFENSIVE (regime gate — reuse the existing regime page output; in DEFENSIVE the loop arms nothing and says so at 9:20).
- **ALERTED carries a TTL** (default 25 min, and immediately expires early if price exits the zone). Expiry is not failure — it transitions to EXPIRED/EXPIRED_MOVED and is *logged as a tracked counterfactual* (what would this have done from trigger price?). The missed-trade ledger is first-class data.

### 2.3 The human veto, redesigned for someone with a job

- **No tick-by-tick stream. Two (configurable) digest checkpoints: 09:25 and 14:30**, plus immediate pings *only* for pre-APPROVED armed names (the user already decided about these last night) and for exit alerts on open positions (stops are sacred — those always ping instantly).
- The 09:25 digest is **one Telegram message, edited in place** as states change (Telegram `edit_message_text`) — a ranked table: `SYMBOL · state · trigger px · now px · zone status · TTL left · AI one-liner`. One notification, not fifteen. Alert spam is solved structurally, not by discipline.
- **Confirm = revalidation, the core fix.** When the user replies `BUY RELIANCE`, the loop re-fetches LTP *at that moment*:
  - LTP inside zone ∧ recomputed R:R ≥ floor → CONFIRMED. Journal logs **both** `planned_entry` and `confirm_ltp`; the user is prompted at EOD for `actual_fill` (one tap on a pre-filled number). Three prices, honestly labeled.
  - LTP outside zone or R:R below floor → **the system refuses**: "RELIANCE moved to 2942, outside your 2890–2915 zone; R:R now 0.8. Not journaling this plan. Reply OVERRIDE to log as an off-plan trade." Off-plan trades are journaled in a separate bucket and *excluded from setup calibration*. The tool never co-signs a chase — that's the beginner-safety teeth.
- User asleep / in a meeting → everything auto-expires with counterfactuals logged. Zero pressure to respond is a feature: the weekend view of "trades you missed and what they did" is honest data about whether this loop suits the user's life at all.

### 2.4 LLM placement: off the critical path, hard-capped

- **Intraday, the LLM never gates an alert.** The deterministic alert is complete by itself (rules-first — the numbers ARE the signal). Haiku runs *in parallel* with a **20s timeout**; its one-line read is edited into the digest when ready, or the field says "AI: n/a". Timeout/failure changes nothing about alert delivery.
- Deep analysis (Sonnet/Opus + chart snapshot) is **evening-only** (§2.1). Intraday chart-snapshot vision is cut (see §4).
- **Hard ceilings, enforced in code:** ≤1 Haiku call per (symbol, day); daily intraday LLM spend cap (e.g., ₹-denominated token budget); when exhausted, alerts continue deterministic-only with a "budget" badge. The loose net's false-positive flood can never run up a bill or a queue.

### 2.5 Connection, token, process hygiene

- **Token:** the existing 6:00 re-auth flow is the primary path; the loop *verifies token validity at 8:45* and pings Telegram if invalid ("re-auth before open"). Mid-session 401/WS auth-close → immediate `⚠ DATA DOWN` Telegram message + FSM freeze (no transitions on stale data) + auto-retry with backoff. Degraded is loud, never silent.
- **WS reconnect:** exponential backoff; on reconnect, backfill the gap from Fyers 1-min history API, replay through the FSM (idempotent, so safe), then resume live. A gap the history API can't fill → DATA DOWN message; the loop never pretends continuity it doesn't have.
- **Process:** run under a supervisor (Windows Task Scheduler / NSSM restart-on-exit). All timestamps IST from the exchange calendar, not wall-clock assumptions.

### 2.6 Calibration that respects its sample size

- Weekly retro **reports**: per-setup hit-rate from *trigger price* (MFE/MAE from trigger — deliberately independent of the user's fills, so LLM/setup calibration is decoupled from execution slippage), confidence-bucket reliability, taken vs missed counterfactuals.
- **No automated tuning.** Parameter changes are a *quarterly human decision*, presented with sample sizes and intervals ("32 trades; hit-rate 56% ± 17% — not distinguishable from coin-flip yet"). At ~100 alerts/month you need a quarter-plus before any bucket says anything. A weekly auto-tuner is an overfitting machine; kill it.

### 2.7 Session clock

One `trading_sessions` table: NSE holiday list (refreshed from the published calendar), half-day closes, Muhurat sessions (evening — the scheduler must read the table, not assume 9:15–15:30), pre-open auction window 09:00–09:08 during which **no ticks feed the FSM**. Every scheduler decision queries this table. No scattered date logic.

---

## 3. VERIFICATION & SAFETY — prove it before rupees

1. **Replay harness (build this first, before the live loop).** Record a full session of Fyers WS ticks to disk (or reconstruct from 1-min history); a `--replay <date> --speed 60x` mode drives the identical FSM code through it. Assertions: expected alerts fire once; **replaying the same day twice produces zero new transitions** (the dedupe proof); TTL expiries fire at the right virtual times. This is also your regression suite forever.
2. **Chaos drills in replay:** kill WS at 10:02, inject a 401 at 11:30, deliver duplicate ticks, restart the process mid-session — assert DATA DOWN messaging, FSM freeze, and clean resume every time.
3. **Paper mode, default-ON for the first month minimum.** Identical loop, journal rows tagged PAPER, digest badged 📄. Graduation criterion is written down in advance: e.g., ≥40 paper alerts with slippage-adjusted expectancy > 0 and zero dedupe/silent-failure incidents. No criterion met → no live mode.
4. **Heartbeat — absence is the alert.** 09:20 daily Telegram: "Loop alive · token OK · WS OK · N armed · mode: RISK_ON." The user's standing instruction: *no 09:20 message = the system is down; assume no coverage today.* Silence is never ambiguous. A second heartbeat at 13:00 catches midday deaths.
5. **Kill switch:** Telegram `/halt` (and a `HALT` file flag for when Telegram itself is the problem) → FSM freezes, one confirmation message, no alerts until `/resume`. Exit alerts on open positions are the only thing `/halt` does *not* silence — stops stay sacred.

---

## 4. THE EDGE, HONESTLY

**Where the real alpha is:**
1. **The evening pre-arm ritual.** Deliberate plans with pre-committed zones/stops/sizes, made calmly at 19:00 instead of 9:17 — this is 80% of the value and it's mostly your *existing EOD engine* plus a review UI. It would be worth building even if the live loop never existed.
2. **Consistent trigger math + the refusal-to-chase revalidation.** A machine that says "this plan no longer exists, I won't journal it" delivers discipline no human sustains alone. For a beginner, the *rejections* are the product.
3. **The taken/missed counterfactual ledger.** Nobody tracks the trades they missed; this does, automatically, and it's the only honest way to learn whether intraday triggering beats simply entering the EOD list at next open.

**What is theatre — cut it:**
- **Intraday Sonnet/Opus deep-dives and chart-snapshot vision.** Too slow to beat the signal's half-life, too expensive against a false-positive flood, and the deterministic plan is already the decision. Move all deep LLM work to the evening; intraday LLM is one Haiku line, off the critical path, or nothing.
- **Weekly auto-tuning retro.** Sample-starved overfitting dressed as science. Report weekly, tune quarterly, human decides.
- **The "loose, high-recall net" as specified.** High recall with no arming discipline is an alert cannon pointed at your attention. Recall comes from the wildcard budget (≤3/day); everything else earns its ping the evening before.
- **Tick-by-tick Telegram pushes.** One edited digest message + pings only for pre-approved names and exits.

**The honest claim:** this loop does not pick better stocks than your EOD engine — the picks *are* the EOD engine's. What it adds over "check the Setups list at 9:15 yourself": you don't have to be present; the trigger math is computed identically every day without emotion; every plan is pre-committed and revalidated at confirm time; and misses become data instead of vibes. That's real, it compounds, and it's honest about being process-alpha rather than selection-alpha. Everything in the original design that pretended to selection-alpha at intraday speed — the deep LLM layer racing the tape — was the part most likely to blow up, and it's gone.

**Build order:** replay harness → FSM + session clock + heartbeat → evening pre-arm + digest → paper month → live. The LLM analyst is the *last* thing wired in, not the first.
