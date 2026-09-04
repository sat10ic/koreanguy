# DECISION RECORD — open decisions adopted by best assessment (2026-09-04)

**Authorised by:** owner's "go with your best assessment for the open decisions"
**Decision framework:** recommendations from the handoffs, adopted with the
trading-intent values stated as owner-delegated defaults (reversible — each
carries the override path).

---

## D1–D5: Delayed EP (ADDENDUM_2026-09-04_DELAYED_EP_DRAFT.md)

| Decision | Value adopted | Reasoning |
|---|---|---|
| **D1** definition | **A** — circuit-stalled repricing | The detector already stubs it (`circuit_ep` flag); `gap_significance` provably under-scores multi-session repricers |
| **D2** anchor | Announcement-knowable (catalyst features) + first-movement (price-structure features). Completion is outcome-side only | Preserves §8.4: features never see hindsight |
| **D3** identity | Separate detector `episodic_pivot_delayed`, REVIEW_REQUIRED at birth | Delayed geometry differs from same-day EP; must not ride episodic_pivot's VERIFIED trust |
| **D4** delay bound | **k = 10 sessions** | Owner-delegated default. Two trading weeks is enough for a repricing to complete on NSE; beyond that it becomes a base, not an event. Override path: edit the frozen constant in the module. |
| **D5** lane | GLM builds (taken over from Sol's event track) | Owner directed "take over these as well" |

## E2: 2,300-session never-attached backfill

**Decision: SKIP (reversible).** Sessions 2010–2016 predate the detector suite —
events from those eras would come from a different regime than anything the desk
validates against. The resume driver picks them up any time; skipping is not
destructive.

## E4: CHOP playbook wording

**Fixed:** "favour: Mean reversion, range setups" → "favour: Tight compression
setups, episodic catalysts". The desk has no mean-reversion detector — all eight
are breakout-family — so the old wording recommended strategies it cannot execute.
The replacement names what it actually detects in chop conditions.

## Q7: Account equity and MTF

**₹50,000 · MTF not in use.** Stored as SOURCE_PRESET in risk_presets.py with
provenance. The planner renders rupee outputs from this equity; percent outputs
work without it.
