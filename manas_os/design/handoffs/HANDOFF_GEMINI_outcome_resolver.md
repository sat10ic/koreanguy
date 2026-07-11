# HANDOFF — Alpha outcome resolver (Gemini)

Date 2026-07-11 · Repo `C:\Users\satta\Downloads\koreanguy` · Branch `emergent`
You have repo access (Antigravity). Do NOT git commit — the maintainer reviews and commits.
Absolute python path for tests (bare `python` may misresolve). No rupee glyph to console — "Rs".

## Goal
Item 3 of the alpha wave (`manas_os/design/handoffs/HANDOFF_CODEX_ALPHA_BEHAVIOUR_WAVE1.md`
§Next executable wave): a **setup-family/event outcome resolver** that turns immutable debate
decision records into path-dependent outcomes — the learning loop's ground truth. Governing
constraints: `manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md` (point-in-time, no leakage, shadow
labels, deterministic risk untouched).

## Read first
- `manas_os/alpha/memory.py` + `manas_os/alpha/pipeline.py` — how decision records are captured
  (schema, keys, what evidence is stored at decision time).
- `manas_os/scanner/outcomes.py` — the existing T+5/10/20 forward-return plumbing (mirror its
  point-in-time query discipline; do NOT duplicate what it already computes — extend the alpha side).
- `manas_os/db/schema.sql` — alpha tables + daily_prices.

## Scope — NEW FILES ONLY
Own exactly: `manas_os/alpha/resolver.py` + `manas_os/tests/test_alpha_resolver.py`.
(The maintainer registers any pipeline stage + API exposure himself — put wiring notes in your
completion file, do not edit cli/app.py/schema.sql.)

`resolver.py` responsibilities, per decision record (TAKE/WATCH/SKIP/gate-blocked alike):
1. **Trigger availability** — did the recorded trigger level actually trade within the validity
   window (next N sessions)? If never triggered: outcome = `NO_TRIGGER` (that IS an outcome).
2. **Entry realism** — next-open slippage vs the recorded trigger (gap-through = enter at open,
   record the slippage); flag gap-over-invalidation (untradeable) honestly.
3. **Path outcomes** from entry: MFE/MAE in R (R = recorded entry−stop distance), time-to +1R /
   +2R / stop (whichever first, with session counts), gap behaviour (overnight gaps against the
   position), and terminal T+5/10/20 R.
4. **Resolution writes** are append-only (never mutate the decision record; a resolution row keyed
   to the decision id, additive DDL as a module-level constant the maintainer applies).
5. **Point-in-time discipline**: resolver may only read market data with trade_date > decision
   date (it resolves the future of a past decision — never leaks future data INTO decision fields).
6. Honest partials: a decision too recent to resolve → `PENDING` with sessions_elapsed; missing
   price data → `UNRESOLVABLE(reason)`. Never fabricate.

## Tests (in your test file)
Seeded daily_prices + decision fixtures with hand-computed expectations: triggered-then-stopped
(MAE first), +2R runner, NO_TRIGGER, gap-through entry slippage, gap-over-invalidation,
PENDING, idempotent re-run (0 new rows). Full suite must stay green
(`python -m pytest manas_os/tests -q`; known allowed fails: sector-downside baseline).

## Guardrails
Money math LOCKED — R uses the recorded plan's entry/stop verbatim; the resolver sizes/authors
nothing. Append-only. No edits outside your two files. Shadow semantics: resolution rows are
evidence, they influence nothing until the validated-promotion gates (wave items 4-5) pass.

## Output
Write `manas_os/design/handoffs/HANDOFF_GEMINI_outcome_resolver_COMPLETED.md`: the resolution
DDL, function contracts, worked-example test table, full-suite result, BACKEND WIRING NOTES
(stage registration point + suggested API exposure), assumptions, and anything ambiguous flagged
rather than invented.
