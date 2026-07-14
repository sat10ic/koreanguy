# HANDOFF — RS-line-new-high + prior-momentum-leg leadership features (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md
(no commit; `_COMPLETED.md`; absolute python; real data; "Rs" not the glyph). SHADOW-FIRST — read
`manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md` (point-in-time, walk-forward, no score controls
sizing/gates until validated).

## Why (the leadership tell missing for choppy/FII-outflow tapes)
Qullamaggie/Minervini/Luk/Tanmay all buy the stocks that hold RS while the index corrects. We
have RS *rating* + sector-adjusted momentum but NOT (a) the Mansfield **RS line** (stock ÷
benchmark) making new highs, nor (b) the **prior big advance → tight base** precondition that
separates a leader resting from a random range. Verified absent (grep: no rs_line / prior_leg).

## Scope — NEW FILE `manas_os/alpha/leadership.py` + tests (do not touch gates/candidates yet)
1. **RS line**: `rs_line(symbol_bars, benchmark_bars)` = stock_close / benchmark_close series
   (benchmark = NIFTY 500 if in `nse_indices`, else NIFTY 50; document choice). Features per
   as_of (point-in-time, prior data only): `rs_line`, `rs_line_52w_high` (bool), `rs_line_new_high_days`,
   and the KEY one — `rs_line_high_while_price_below_high` (RS line at/near new high WHILE price is
   NOT within X% of its own 52w high = leadership emerging before price). Also `rs_line_slope_20`.
2. **Prior-momentum-leg**: `prior_leg(bars)` → `{leg_present: bool, leg_gain_pct, leg_weeks,
   base_after_leg: bool, base_depth_pct, base_len_bars}`. Definition (tune + document): a
   volume-supported advance of >= ~25-30% (or a big EP gap) over a recent window, FOLLOWED by a
   contraction/base. This is the "leader that already moved, now resting" precondition.
3. **Persist + expose as EVIDENCE (display-only, direction-neutral)**: a new additive table /
   columns keyed by (as_of, symbol); an API field on the candidate/debate payload so the UI can
   show chips "RS-line new high (before price)" and "prior +38% leg → 6-wk base". Chips are
   EVIDENCE, not gates — they do NOT change rank/verdict/size yet.
4. **Validation (the gate to any influence)**: wire both features through
   `alpha/promotion_gates.py` — does "fresh-breakout WITH rs_line_high_while_price_below_high" and
   "WITH prior_leg" beat the same setup WITHOUT them at T+10 after Indian costs, walk-forward,
   across regimes, vs the existing RS-rating/sector-momentum baseline? Emit the frozen verdict.
   Only if it passes may a later handoff let it tilt rank (flag that; don't do it here).
5. Tests: RS-line math on a fixture (stock up vs flat benchmark → line new high); the
   before-price case; prior-leg present/absent fixtures; leakage check (T-1 truncation, style of
   `alpha/leakage_audit.py`).

## Guardrails
Shadow/display only; not imported by gates.py/sizer/candidates ranking/debate verdict (grep-prove
in the completion). Point-in-time (only data <= as_of). No money-math touch. Additive DB only.

## Output
`HANDOFF_GEMINI_rsline_priorleg_COMPLETED.md`: feature contracts, the leader-before-price
definition + thresholds chosen, promotion-gate verdict (honest pass/fail per gate), grep proof of
no live influence, real example (a current name showing RS-line-high-before-price), tests.
