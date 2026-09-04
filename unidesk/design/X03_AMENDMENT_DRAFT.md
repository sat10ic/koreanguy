# AMENDMENT DRAFT — UI_BUILD_SPEC_V1 X-03 (Risk Desk scoping)

**Status:** DRAFT — awaits owner approval (escalation **E8**). Nothing in the
Risk Desk wave (N-42..N-49) is built until this amendment is approved or amended.
**Author:** GLM (draft role). **Base text:** UI_BUILD_SPEC_V1, X-03 clash entry.
**Attribution-ID:** attr-unidesk-x03-amendment-glm53flash-20260904-001

---

## The current rule (verbatim, to be amended in place)

> `X-03` Playbook (`H1-07`) vs size evidence (`D-04`) — different scopes
> Both speak to exposure and will look contradictory if unmanaged.
> - `H1-07` is **market-level** and a **heuristic** — qualitative only
>   (`EXPOSURE: REDUCED`). It must emit **no numbers**.
> - `D-04` is **position-level** and **descriptive of the owner's own record**.
> **Rule:** the Playbook never states a size, a rupee amount, or a position count.
> **Accept:** no numeric exposure figure appears in `H1-07`.

## The problem, stated precisely

Read literally, "the Playbook never states a size, a rupee amount, or a position
count" blocks the entire Risk Desk wave: the Trade Planner's only job is to
compute `quantity = floor(risk_budget / risk_per_share)` from the owner's OWN
inputs. That is not the Playbook speaking — but the amendment must draw the
line so precisely that a future agent cannot blur it.

## The distinction the amendment encodes

| | Model output (FORBIDDEN as risk) | Deterministic arithmetic (allowed) |
|---|---|---|
| Example | an AI score scaled into a risk multiplier | `qty = floor(risk_budget / risk_per_share)` |
| Provenance | a model's weights decided the number | the owner's inputs + a documented formula |
| Changes when weights retrain | yes | never |
| Spec §22.1 verdict | `AI score → risk multiplier = FORBIDDEN` | not a model output — a calculator |

## Proposed replacement text

> `X-03` Playbook (`H1-07`) vs size evidence (`D-04`) vs the Risk Desk
> (`R-*`) — three scopes, one boundary.
>
> - `H1-07` (regime → playbook) remains **market-level, qualitative only**
>   (`EXPOSURE: REDUCED`). It emits **no numbers**. Unchanged.
> - `D-04` remains **descriptive of the owner's own record**. Unchanged.
> - `R-*` (Risk Desk) computes deterministic arithmetic **from owner-supplied
>   inputs**: risk fraction, account equity, entry, stop. Every output names
>   its inputs and shows the binding constraint. It authors nothing the owner
>   did not supply: **no model output may author a stop, a size, or a risk
>   number** (charter, unchanged). The Risk Governor PROPOSES with a
>   deterministic reason; the owner accepts. Automatic action is out of scope
>   (escalation E10).
>
> **Rule:** the Playbook never states a size, a rupee amount, or a position
> count. The Risk Desk never does so from a model output — deterministic
> arithmetic over owner-supplied inputs is a calculator, not a prediction.
> **Accept:** (a) no numeric exposure figure in `H1-07`; (b) every Risk Desk
> number is reproducible from named inputs by the documented formula;
> (c) removing the owner's risk-fraction input makes every size output
> disappear — never a fallback default.

## What this does NOT license

- No default risk fraction, position cap, or open-risk ceiling (escalation E9 —
  the owner's numbers, or the field stays empty).
- No automatic Risk Governor action (escalation E10).
- No neural/ML output anywhere in the size path (charter §22.1, unchanged).
- No loosening of the H1-07 qualitative-only rule (unchanged).
