# Reactor Scale — the desk's abnormal-activity analogue (R6: context, never a risk input)

**Status:** built, rendered, bounded. **Validation:** never measured as an edge — it is
descriptive context and must stay one until an experiment says otherwise.

## What it is

`momentum/features/activity.py::activity_score` — a clean-room reversal of the
proprietary Reactor Scale, computed from public NSE bhavcopy fields:

```
avg_trade_qty    = volume / num_trades
q_ratio          = today_avg_qty / mean(prior_20_avg_qty)
d_ratio          = today_delivery_pct / mean(prior_19_delivery_pct)
activity_score   = 1.165335·q + 1.04631·d + 1.152161·(q·d)^0.84 − 0.213928
```

Coefficients adopted verbatim from `traderlog/adopted/activity.py`
(provenance: `manas_os/alpha/activity.py`). The one deliberate drift: the prior window is
**exclusive** of the current session — a brief-driven change, not a data-forced one.

## Where it appears

| Surface | Form |
|---|---|
| Candidate cards (Pro) | `RSch <score>` chip, tooltip carries the R6 caveat verbatim |
| Candidates → Accumulation evidence | now / prev / 5D / 10D / streak / 10D trend |
| Bundled data | `activity_score` on each report candidate (symbol, score, q_ratio, d_ratio, avg_trade_qty) |

## R6 — the governing rule

> **The Reactor Scale is context, never a risk input.** It must never be presented as
> institutional identity, trade direction, or a risk number, and it must never enter a
> weighted score, `deriveState`, `compareCandidates`, or the geometry rule.

R6 lives in `plan/ORDERFLOW_BUILD_MANUAL.md` cross-project. This repo enforces it
mechanically: `tests/test_reactor_scale_r6.py` fails if `activity` reaches any scoring
module, `deriveState`, or `compareCandidates`. That test is the finding-proof, not this
document.

## Validation status

Never measured as an edge. Promotion into any decision surface requires an experiment
verdict through the harness (`run_n5_experiment.py`) — same bar as every other
unvalidated feature (KDE §10 containment).
