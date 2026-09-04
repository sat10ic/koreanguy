# HANDOFF 4 — Alpha memory upgrade + promotion gates (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Governing docs: `manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md` (§Learning loop, §Research
discipline — every rule binds) + `manas_os/design/knowledge/EXTERNAL_ALPHA_ADOPTION_MAP.md`
(adoption items; concepts only, native reimplementation, SQLite canonical).

## Scope (4 adoption items, all shadow-only — nothing here influences live ranking)
1. **Outcome-weighted analogue retrieval** (tradememory-protocol concept) — upgrade
   `alpha/memory.py::recall_analogues` to multiplicative scoring `Q·Sim·Rec·Conf`:
   outcome quality Q = sigmoid of realized R-multiple (from the outcome resolver's resolutions;
   PENDING/UNRESOLVABLE analogues get a neutral shrunk Q, labelled), context similarity Sim =
   Gaussian kernel over the stored decision-time features, recency Rec = power-law decay,
   confidence Conf = sample-size shrinkage. Add the **anti-resonance check**: report whether the
   top-k analogues' outcomes OPPOSE the proposed direction — surfaced into the debate context as
   the "strongest contradiction" input. Tests: hand-computed scores on seeded records; opposing-
   analogue case flags correctly.
2. **Anti-overfit promotion battery** (QuantGPT concept) — new `alpha/promotion_gates.py`:
   given any candidate signal/feature series (cross-sectional daily scores) run: walk-forward
   folds vs the simple RS/residual-momentum baseline AFTER Indian costs (STT+brokerage+slippage
   constants documented), placebo/permutation test (shuffles + time-shifts; real must beat 95th
   pct), regime-split stability (by market_mode; needs sign consistency in >=2 of 3), sub-sample
   stability (random 30% universe, 70% sign consistency), min-sample floors. Emits a frozen
   verdict record. Pure functions + tests with synthetic known-good/known-overfit series.
3. **Leakage audit** (xtquantai concept) — `alpha/leakage_audit.py`: T-1 truncation perturbation
   over `alpha/features.py` output (recompute features with data truncated at T-1; any feature
   whose value at T changes when only future rows are removed = leak). Test with a deliberately
   leaky fixture feature.
4. **Frozen experiment KB** — extend the alpha experiment registry (see `alpha/schema.py` /
   `alpha/diagnostics.py`) so every promotion-gate run (pass AND fail) writes an immutable
   experiment record (hypothesis, config, per-gate results, verdict, date); add
   `already_failed(hypothesis_signature)` lookup the debate/research loop can query. Test:
   re-running a failed idea is flagged as rediscovery.

## Do NOT
Wire anything into live ranking/sizing/gates. No model training in this handoff (that's wave
item 4 AFTER these gates exist). No external services.

## Output
`HANDOFF_GEMINI_alpha_memory_gates_COMPLETED.md` per standing rules: function contracts, the
cost constants used, worked-example tables, full-suite result, wiring notes.
