# HANDOFF_GEMINI_alpha_memory_gates — COMPLETED

**Executor:** Grok · **Date:** 2026-07-12 · **No git commit** · **Shadow-only**

## Delivered

### 1. Outcome-weighted analogue retrieval (`alpha/memory.py`)
- Score **Q·Sim·Rec·Conf**:
  - **Q** = sigmoid(R-multiple); PENDING/UNRESOLVABLE → neutral 0.5
  - **Sim** = categorical field match + optional Gaussian kernel on `query_features`
  - **Rec** = power-law `(1+days)^(-0.5)`
  - **Conf** = cohort shrinkage `n/(n+10)` for family+regime
- **Anti-resonance**: `anti_resonance.active` when top-k outcomes oppose `proposed_direction`

### 2. Promotion gates (`alpha/promotion_gates.py`)
- Cost constants: STT 0.10% sell + brokerage 0.03%×2 + slippage 0.05%×2 → **round-trip 0.26%**
- Gates: min_sample, walk_forward vs baseline, placebo (shift+shuffle / constant edge), regime stability, subsample stability
- `run_promotion_battery` → frozen verdict dict (`shadow_only: true`)

### 3. Leakage audit (`alpha/leakage_audit.py`)
- Pollutes history with future bars; flags features whose values change
- Fixtures: `clean_feature_fn`, `deliberately_leaky_feature_fn`

### 4. Experiment KB (`alpha/schema.py`)
- `record_promotion_experiment(conn, verdict)` → `alpha_experiments`
- `already_failed(conn, hypothesis_signature)` rediscovery lookup

## Tests (QC)
```
pytest manas_os/tests/test_alpha_memory_gates.py -q
→ 5 passed
```

## Not wired
Nothing influences live ranking/sizing (per Do NOT). Debate loop can call `recall_analogues(..., proposed_direction=)` and `already_failed` later.

## Worked example (Q)
R=2 → Q = sigmoid(2) ≈ 0.8808 (asserted in test).
