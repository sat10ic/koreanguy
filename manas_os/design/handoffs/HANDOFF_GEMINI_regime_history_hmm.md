# HANDOFF 12 — Regime-history replay + HMM data fix (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Absolute python path. No rupee glyph.

## The problem (diagnosed)
HMM regime state renders nothing. Root cause is DATA, not hmmlearn (installed, 0.3.3):
- `regime_snapshots` has only **286 sessions from 2025-03-19**, even though `daily_prices` now
  spans **1238 sessions back to 2021-07-12** (the 5y backfill). The regime/breadth series were never
  replayed over the extended history.
- `regime_hmm_states` table **does not exist** — the `regime_hmm` stage isn't persisting (failing/
  gated silently).

## Scope
1. **Replay regime history over the full 5y**: run `manas_os/cli backfill-snapshots` (see
   `_cmd_backfill_snapshots`) so `breadth_daily`/`regime_snapshots` extend back as far as the
   underlying inputs allow (daily_prices to 2021-07-12; note honestly where an input series starts
   later — e.g. the Google breadth sheet vs computed breadth). Respect XP's day-over-day recursion
   order. Report before/after `regime_snapshots` count + date span. Parity: a replayed recent day
   must match what the live pipeline wrote (existing backfill parity discipline).
2. **Fix the HMM stage persistence**: find why `regime_hmm_states` (or whatever `regime_hmm.run`
   should write) isn't created/populated — run the stage, surface the real error (missing table
   DDL? exception swallowed by failure-safe skip? gate never satisfied?). Ensure the stage creates
   its table (additive DDL) and persists states once the history bar is met (it trains on the now-
   longer regime_snapshots). Keep it EXPERIMENTAL/display-gated per its existing contract — it must
   not feed gates/risk. If it legitimately can't run (e.g. a real data dependency still short), make
   it report a clear WARMING/NEEDS-DATA status the UI can show, not a silent nothing.
3. **Expose regime HMM state honestly** via the API so the UI (handoff 10's status-chip work) can
   render LIVE vs WARMING vs NEEDS-DATA with the reason — no blank organs.
4. Tests: backfill idempotency (re-run adds 0); HMM stage creates+persists on a seeded long-history
   fixture; honest WARMING status when history too short.

## Guardrails
Additive/point-in-time; never mutate existing rows; HMM stays experimental/display-only (no gate/
risk influence); failure-safe (a bad HMM run must not break run-eod).

## Output
`HANDOFF_GEMINI_regime_history_hmm_COMPLETED.md`: regime_snapshots before/after span, the HMM
root-cause + fix, whether HMM now produces states or reports WARMING (with the honest reason),
tests, wiring notes. Real command output.
