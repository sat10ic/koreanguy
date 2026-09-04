# Review — "Manas OS Rework: Delta Plan Grounded in Current State" (PLAN 2)

Reviewer: Opus main thread, 2026-07-11. This is the revision of PLAN 1 after my
`PLAN1_REVIEW.md`. Verdict, what it fixed, the genuine remaining risks, and execution watch-outs.

## Verdict

**Sound and executable — approve, with three refinements below.** PLAN 2 absorbed nearly
every PLAN1 correction: it preserves shipped V4 work by name, runs the corpus audit in
parallel instead of as a blocking gate, elevates the trade-lifecycle engine to "the primary
doctrinal build," completes the evidence-status service, and repeats the locked-risk discipline
(paper/advisory mode, replay-before-change) throughout. The plan changed; my standard didn't —
the earlier objections were about sequencing and current-state blindness, and both are fixed.

## What it fixed (vs PLAN1_REVIEW)

| PLAN1 objection | PLAN2 resolution |
|---|---|
| Greenfield waterfall, ignores shipped work | Summary preserves V4/four-phase/objections/shortlist/pipeline by name; "do not rebuild completed systems" |
| Full corpus re-audit blocks product work | §6 delta audit in parallel; "reconcile the conflicting ledgers first"; read only GAP/PARTIAL/SAMPLED |
| Biggest lift (lifecycle templates) buried | §2 is now "the primary doctrinal build", fully specified |
| Evidence ladder half-built, unaddressed | §3 unified evidence service, maps the existing expectancy trust-ladder in (not a competing authority) |
| The one new idea (staged seats) not prioritized | §1 first implementation change + delivery-order step 2 |
| SSE/live greenfield unacknowledged | §4 durable jobs/events + SSE + Live Work drawer, WebSocket/Fyers correctly isolated to later |

## Genuine remaining risks (the value-add of this review)

1. **The lifecycle engine is the plan's own biggest trap for its own rule.** §2 templates encode
   confirmation / hold-style / profit-management / pyramiding per trade type — and §6 rightly
   forbids "silently converting judgment into numbers." These collide: a "management template"
   is exactly where doctrine like *tightness, demand resumption, structural decay, ride-the-
   trend* gets pressured into hard numbers. The plan already says "separate mechanical stops
   from discretionary profit-taking" — good — but that separation must be **enforced**: stops
   are mechanical (numeric, deterministic), profit-management stays JUDGMENT (e.g. "trail the
   10EMA / sell into strength", not "exit at +Nx"). Add an explicit template rule: any numeric
   profit-target in a template requires a validation-status ≥ PROMISING with an Indian outcome
   sample; otherwise it renders as a judgment principle with the evidence shown, not a trigger.

2. **The evidence service will honestly show mostly EXPERIMENTAL/UNPROVEN for a long time —
   plan for that, don't let it read as failure.** VALIDATED requires point-in-time Indian
   outcomes + sample size + net R. The journal is near-empty and most `setup_expectancy`
   cohorts are n<20. So at launch, almost everything is UNPROVEN/EXPERIMENTAL — which is the
   *correct, honest* state, but it will look like "nothing is proven." The UI copy must frame
   this as "we don't fake conviction we haven't earned" (matches the tool's own honesty ethos),
   and the service should show the **n-gap to the next status** so the user sees a path, not a
   wall. Do not let pressure to show green labels lower the bar.

3. **"Reconcile the conflicting ledgers" needs a single normalized status vocabulary.**
   `TRADETM_INDEX.md` currently mixes case/synonyms (DIGESTED/Digested/digested, FULL/Full/full,
   GAP/Gap/gap) — that inconsistency is *why* the counts conflict. Step 1 of the audit must
   define one canonical status set {FULL, DUP, GAP, PARTIAL, SAMPLED, META} and rewrite the
   index to it before any count is trusted; otherwise "zero unexplained gaps" can't be proven.

## Continuity with current state (so the plan doesn't re-spec live work)

- **Delivery step 1 ("current-state contract; classify every prior-plan item shipped/partial/
  missing/obsolete") is already ~80% done** — `PLAN1_REVIEW.md` has the done-vs-greenfield
  table. Extend that file; don't regenerate it.
- **Work landing *this session* already fits the plan's frame:** the candidacy-relax (movers
  surface with scored objections) IS the plan's "scored objections, judgment-not-hard-numbers";
  the Strong-Start / Arora focus list IS an Arora-overlay scanner under §1/§5; the in-flight
  momentum measured-move fix is a §2-adjacent target-computation done *without* touching locked
  thresholds. Fold these in rather than re-planning them.

## One optional ordering suggestion

Delivery order is defensible, but consider pulling **the Live Work drawer (step 5) earlier**.
It's the lowest doctrinal risk and the highest *felt* value — it directly answers the user's
most-repeated complaint ("I can't see your latest updates / no live feel") and needs no
approval gate. The lifecycle engine (step 3) is the highest doctrinal value but is
approval-gated (paper mode + sign-off on hold rules), so it will move slower regardless —
let it proceed on its own cadence while the Live Work win ships sooner.

## Execution watch-outs

- **Staged seats (§1) will grow prompt size/latency/cost** — the cost-routing in §7 must apply
  here (don't run the full 5-stage reasoning on every candidate; reserve the strong chair +
  full stack for disagreement/finalists, per §7).
- **Advisory templates must be provably unable to alter deterministic entry/stop/target/qty** —
  the plan says this (§2, test plan); make it a hard architectural boundary (one-writer risk),
  not a convention.
- **Keep the accuracy-weighted chair + tuned modern seats** — staging is a prompt-structure
  change, not a seat-roster change.

## What I could not verify / caveats

- I did not re-run repo checks for this review; the current-state claims carry over from
  `PLAN1_REVIEW.md`'s verified map (four-phase built, objections built, evidence labels 2-of-5,
  lifecycle + SSE greenfield, corpus ~66 FULL / ~60 GAP-PARTIAL-SAMPLED).
- The "conflicting ledgers" claim rests on the mixed-case statuses I observed in
  `TRADETM_INDEX.md`; if a second coverage ledger exists that I haven't seen, step-1 scope may
  differ.
- This reviews a document; execution will surface details (esp. template numeric-vs-judgment
  boundaries) that only fixture-building will pin down.

## Bottom line

PLAN 2 is ready to execute. Start with the two low-risk high-clarity items — stage the debate
seats (§1) and reconcile the corpus ledger vocabulary (§6 step 1) — while the lifecycle engine
(§2) enters its paper-mode + sign-off cycle and the Live Work drawer (§4) ships the felt "live"
win. Hold the line on locked risk exactly as the plan says.
