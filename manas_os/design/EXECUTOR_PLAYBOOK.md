# EXECUTOR PLAYBOOK — Manas OS, remaining build (wave-by-wave, zero-judgment)

You are the EXECUTOR. Every wave below names its spec file — the spec is the law; this
playbook is the map and sequence. Do NOT re-decide thresholds, layouts, or scope. If a step
is impossible as written, STOP that step, write one line in TASKS.md under "Execution log",
and continue to the next independent step. Never fake a pass.

## Standing rules (apply to every wave)
- Repo: `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Python:
  `C:\Users\satta\AppData\Local\Programs\Python\Python314\python.exe` (fallback Python312).
- After every task: `python -m pytest manas_os/tests -q` (NEVER below the baseline you
  started the wave with) and `cd manas_os/frontend && npm run build` (must pass) — these
  prove it COMPILES, they are NOT the done-test. The done-test is per-wave below.
- NEVER touch: `scanner/gates.py`, `risk/plan.py`, `regime/governor.py`,
  `backtest/replay.py` — unless the wave names them explicitly. Never commit
  `manas_os/config.yaml` or `manas_os/data/` (gitignored).
- LOCKED numbers live in the plan file (`~/.claude/plans/c-users-satta-downloads-manas-os-
  v2-md-woolly-peacock.md`) — stop caps, R:R floor, regime caps, risk profiles, trust
  ladder. Quote them; never re-derive.
- One writer per metric. A number the payload already states is NEVER re-derived in JSX.
- UI fidelity = TWO DIRECTIONS vs `manas_os/design/WIREFRAMES.md` ASCII (see
  CODEX_WIREFRAME_BUILD.md "The one rule"): every ASCII block present in order AND nothing
  extra. LIGHT THEME STAYS — dark reskin is cancelled (RESKIN_DARK.md header).
- Every threshold change or study result → dated entry in `manas_os/design/LEARNINGS.md`.
- Tick your work in `manas_os/TASKS.md` + the wave's spec file checkboxes as you go.

## WAVE 0 — verify what is already in flight (do FIRST, it's cheap)
Spec refs: CODEX_WIREFRAME_BUILD.md (STATUS + DETAIL-AUDIT LEDGER), ADVISOR_SPEC.md.
0.1 Run pytest + build; record the true baseline count.
0.2 Verify D1-D5 ledger fixes landed (each has an exact check written in the ledger):
    D1 funnel lists ALL by_gate gates; D2 regime strip uses rank_of; D3 gate-dot hovers
    carry evidence; D4 journal rows have no chip cluster; D5 refused cohort n scoped to
    20 sessions. Fix any that didn't land, per the ledger text.
0.3 FOCUS tab: with a session where focus_candidates is non-empty (re-run
    `candidates.run` on latest date if needed), confirm catalyst-only cards render
    base_age / days_since_listing / circuit-state fields. If the payload lacks a field,
    add it to the existing /api/setups focus slice — no new endpoint.
0.4 ADVISOR module (built by a prior batch — verify against ADVISOR_SPEC.md): tests
    mock-only, guard rejects novel numbers + imperatives, run() no-ops without api_key,
    endpoints /api/advisor/today + note-action live, AdvisorStrip renders muted with the
    advisory chip. Fix deviations from the spec, spec wins.
0.5 CHART DRAWER audit (CODEX_WIREFRAME_BUILD.md SCREEN 6): open drawer from a symbol
    click; SETUP/TREND/EXIT tabs switch overlays; lightweight-charts candles+vol; EMA
    10/21/50; AVWAP with anchor reason; buy-zone band + stop line + entry/exit arrows +
    pocket-pivot markers; ONE-line legend; [E] RS + TTM panes. Fix only what fails.
DONE-TEST W0: pytest+build green; all five sub-checks pass with evidence (paste the
check output/text-snapshot lines into the report).

## WAVE 1 — edge verdict + calibration (backend; the most important wave)
Spec refs: LEARNINGS.md 2026-07-07 near-miss entry, backtest/replay.py, VIZ_BRAINSTORM A1/A2.
1.1 The full-history replay on the DB copy writes
    `<scratchpad>/replay_verdict.json` (see SESSION_HANDOFF for scratchpad path; if the
    file is absent, re-run `_replay_copy.py`-style: copy manas.db, run
    `backtest.replay.replay(conn, MIN(trade_date), MAX(trade_date), "cascade")`).
1.2 Write the verdict entry in LEARNINGS.md: per (family × regime) cells (n, hit, median R,
    stop), PLUS passed-vs-refused near-miss comparison IN R TERMS (the raw-% caveat in the
    2026-07-07 entry explains why % is not enough).
1.3 Calibration decision procedure (mechanical): for each gate where the refused cohort
    beats the passed cohort in median R with n>=75: propose ONE threshold change (the
    smallest step: extension 8→9%, RS 80→75, delivery_z 0→-0.25), re-run replay A/B with
    the changed config on the copy, and record both runs in LEARNINGS. Apply the change to
    the live config ONLY if the A/B improves passed-cohort median R without cards/day
    exceeding regime caps. Maximum ONE change per gate per quarter (LOCKED rule).
1.4 MFE/MAE excursions: extend `scanner/outcomes.py` to also record per-candidate MFE/MAE
    in R (max favorable/adverse excursion over the horizon, vs the plan stop) — additive
    columns on `outcomes`, backfill for completed rows, tests with hand-computed fixtures.
    This unblocks the Journal MFE/MAE scatter (currently an honest empty state).
DONE-TEST W1: LEARNINGS has the dated verdict + (if any) A/B calibration entry;
outcomes carries mfe_r/mae_r with tests; Journal scatter renders real points.

## WAVE 2 — VIZ_BRAINSTORM Tier-1 charts (frontend; spec: VIZ_BRAINSTORM.md Part 1)
Build in this order, each with its stated data source (all exist after W1):
2.1 #1 Near-miss verdict chart → Journal (below four-cohort strip): rolling passed vs
    refused-near-miss median T+10 R. Backend: extend /api/journal/visuals with the two
    series (SQL over outcomes + refusals; no client math).
2.2 #2 Gate proximity map + #3 "what would it take" chip → near-miss lane entries
    (SetupsPage + FocusPage): per refused name, distance-to-pass per gate from
    refusals.evidence_json (helper `_distance_to_pass` already exists in api/app.py).
2.3 #4 Trade lifecycle river → Watchlist coach card expand: sessions-since-entry vs open-R
    with phase bands from trail_plan; data = journal_trades + bars + existing coach helper.
2.4 #5 Regime ribbon with outcomes → Regime expert accordion: market_mode ribbon +
    journal trade entry/exit markers. Data: regime_snapshots + journal_trades.
Two-direction rule still applies: these charts go WHERE VIZ_BRAINSTORM/WIREFRAMES place
them; no new panels elsewhere.
DONE-TEST W2: each chart renders with real data in the named location; build clean;
screenshot per chart in the report.

## WAVE 3 — hand-holding completion (spec: plan T3.8/T3.9 + BEGINNER_EXPERT_SPEC.md)
3.1 Verify /api/flow/today implements ALL six steps of plan T3.8 (data check, regime read,
    positions-first with coach actions, setups review gating step 5, order ticket with
    copyable text, done-for-today; NO_TRADE variant; Friday weekly step). Extend to spec
    where short; tests per state fixture.
3.2 Position Coach endpoints (C11-C13 in CODEX_HANDOFF.md BATCH 3) — verify against that
    spec: /api/positions/{id}/coach shape, early-exit 409 guard writing mistake tags,
    late-exit banner with session count. Fix to spec.
3.3 Beginner/expert Axis D (deferred earlier): Setups/Watchlist column reduction in
    beginner per BEGINNER_EXPERT_SPEC.md; safety states identical in both modes.
DONE-TEST W3: flow endpoint fixture tests for all states; coach guard tests; beginner vs
expert DOM text-snapshots differ exactly as the spec says.

## WAVE 4 — Telegram slice 2 (spec: plan T4.1 + LIVE_LOOP_FABLE.md; CODEX_HANDOFF C14 done)
4.1 FSM replay harness FIRST (per Fable build-order note): recorded/mocked WS session →
    IDLE→ARMED→TRIGGERED→ALERTED(25min TTL)→CONFIRM_PENDING→CONFIRMED/EXPIRED, zero
    duplicate-alert assertion. No network in tests.
4.2 Digest SEND path: telegram bot token/chat under `telegram:` in config.yaml (document
    keys in a comment; config gitignored); send the nightly digest (armed_list from C14) —
    one message, caps 5/3/1/0 by regime, refusal count line. Failure-safe: send errors log
    a pipeline_runs fail row, never crash the pipeline.
4.3 TAKE/SKIP replies → journal capture (reuse /api/setups/decision logic; no second
    writer). Push cap 1/symbol/day. `/halt` kill-switch that never silences exit alerts.
4.4 PAPER MODE only: everything runs against paper flags for >=1 month before any real
    intraday push (graduation criterion written into LEARNINGS when paper starts).
DONE-TEST W4: FSM harness green incl. dedupe; a dry-run digest renders correct caps from a
fixture DB; kill-switch test; no live push code path enabled by default.

## WAVE 5 — fundamentals + data depth (spec: TASKS.md T5.1 notes)
5.1 Ingest quarterly fundamentals (EPS/sales/OPM history) via the finstack import scripts
    already in `scripts/` (import_finstack_history.py etc.) into a `fundamentals` table —
    point-in-time (report_date + as_of), additive migration.
5.2 Wire the EP catalyst leg to REAL fundamentals where available (growth checks read the
    table first, ChartsMaze dump values as fallback) — one writer: a single
    `growth_for(symbol, as_of)` helper.
5.3 Earnings-calendar events for the advisor context pack + Watchlist "earnings soon" chip
    (if a forward calendar source exists in the imports; else skip with a TASKS note).
DONE-TEST W5: fundamentals table populated (row counts logged), EP tests updated, no
regression in scan output for symbols lacking fundamentals.

## WAVE 6 — live intraday loop (spec: plan P4/T4 + legacy/ssrvol as the seed; LAST wave)
6.1 Fyers WS client adopted from legacy/ssrvol (adopt-not-import): reconnect + dedupe
    tested with a fake WS server fixture.
6.2 Strong-Start trigger detection on the armed_list names only (gap-up open, holds prev
    close, crosses prev-day high, early RVOL supportive, stop distance valid) — LOCKED
    formulas from the plan; regime-gated via governor.push_allowed.
6.3 Intraday push through the W4 FSM (paper first), TAKE/SKIP reply → journal.
6.4 Session-state persistence + 09:20 heartbeat (absence = the alert).
DONE-TEST W6: simulated WS session fires exactly one alert under gated conditions,
reconnect double-fire test, heartbeat test, regime NO_TRADE suppresses all entry pushes.

## FINAL WAVE — close-out
F.1 OWNERS_GUIDE.md refreshed to cover advisor, coach, flow, telegram, calibration loop.
F.2 Full browser QC: all 6 screens × beginner/expert × {normal, empty, stale} states —
    screenshot set + two-direction audit each.
F.3 LEARNINGS quarterly-review template appended; NORTH_STAR scorecard updated.
F.4 Weekly ops runbook (one page): daily run-eod, Fyers re-auth, dump ingestion, backup.
