# Where the build actually is — the real roadmap (2026-09-04)

**Correction to the first version of this file.** It mapped the six-stage *remediation*
plan and called it the roadmap. That was wrong. The product roadmap is:

- `plan/AI_NATIVE_EDGES_NORTH_STAR.md` — six edge hypotheses, 1,600 lines
- `plan/AI_NATIVE_INDIAN_SWING_RESEARCH_CONSTITUTION.md` — the L0→L5 ladder and its rules
- `plan/ORDERFLOW_BUILD_MANUAL.md` — the live order-flow engine, P0→P2
- `plan/PHASE0_DATA_BUILD_SPEC.md` — the data gate everything else waits on

Everything shipped in the last two weeks is **foundation**, not roadmap. That distinction
is the point of this document.

Statuses verified from the tree on 2026-09-04.

---

## 1 · The six edge hypotheses — the actual product

From the North Star. This is what the tool is ultimately *for*.

| # | Edge | Built? | Evidence |
|---|---|---|---|
| **6** | **Episodic Pivot quality engine** | 🟡 **L0/L1 built** | `detectors/ep_signature.py` — S_ep, five weighted components (gap significance, RVOL anomaly, close quality, prior compression, delivery shock), with `circuit_ep` and `climax_on_climax` guards. Detector emits 1 candidate on 09-01. |
| **2** | **Bull-market pre-breakout ignition** | 🟡 **L0/L1 built** | `detectors/base_pattern.py`, `base_episode.py`, `setups.py`; the UI's "Ignition Stack" (`QualityStack.tsx`) is this edge's surface. |
| **5** | **IPO base maturity** | 🟠 **built but handicapped** | `ipo_base` detector exists, trust = **BLOCKED** ("listing age is not verified"), and the 61-session universe floor means it structurally **cannot see a real IPO** (audit S1-9c). |
| **3** | **Bear-market downside refusal / future leaders** | ❌ **not started** | no `downside_refusal` / `future_leader` anywhere. (An earlier keyword sweep appeared to find it — that was a false positive on B2-8's `symbol_refusals`.) |
| **4** | **Choppy-market failed-breakout intelligence** | ❌ **not started** | no `failed_breakout` / `range_maturity` anywhere. |
| **1** | **AI Information Reaction Gap** | ❌ **not started** | no `airg` / `reaction_gap`. Needs a news/event corpus that does not exist in this repo. |

**Two of six exist at the rule/score rungs. One is built but blind. Three do not exist.
And critically: none of the six has ever been validated**, because the edge test is not
wired (§4).

The North Star's own suggested order was **EP → IPO → Bull ignition → Bear resilience →
Chop failure → AIRG**. The build followed it faithfully for the first three.

## 2 · The core AI capability — historical state retrieval

The North Star names one capability that all six edges share: *retrieve historically
similar states and show what happened next.* In ladder terms that is **L1.5**.

| | |
|---|---|
| `research/analogue.py` | ✅ built (11.8 KB), 11 constraint tests passing |
| Constraint compliance | ✅ cosine only, k ∈ {25,50}, same-symbol embargo, PIT rank-normalisation |
| **Measured edge** | ❌ **never evaluated** |
| Surfaced in the UI | ❌ deliberately not — the Phase 0 gate is open |

**This is the single most important unfinished thing on the roadmap.** It is the mechanism
behind every edge hypothesis, it is already built, and nobody knows whether it works.

## 3 · Order-flow engine — the live half

`plan/ORDERFLOW_BUILD_MANUAL.md`, separate project (`orderflow/`), owner-gated feed.

| Task | Status |
|---|---|
| P0.1 Feed capability audit | ✅ `P0.1_CAPABILITY_AUDIT_COMPLETED.md` |
| P0.2 Recorder | ✅ `N2_OFFLINE_RECORDER_CORE_COMPLETED.md` |
| N1 Launcher | ✅ built; live session prep **stopped** (`N1_LIVE_SESSION_PREP_STOP.md`) |
| P1.1 Universe & subscription tiers | ❌ not started |
| P1.2 Features that survive a slow feed | ❌ not started |
| P1.3 Liquidity gate with position capacity | ❌ not started |
| P2.1 Flow score, confidence, state | ❌ not started |
| P2.2 Ablation before production scoring | ❌ not started |

**P0 is done; all of P1 and P2 are not.** The manual's own sequencing puts this behind the
EOD desk, which is correct — a flow score on an unvalidated EOD spine would compound two
unknowns.

## 4 · Reactor Scale — you were right, it has no home

**Implemented:** `momentum/features/activity.py` — clean-room reversal from public NSE
bhavcopy fields (volume, num_trades, delivery_pct), frozen V2 coefficients, exclusive prior
window. Emitted on 88/88 candidates. Rendered on the card as `RSch`.

**Governed by:** `plan/ORDERFLOW_BUILD_MANUAL.md` **R6** — *"Reactor Scale is context, never
a risk input"* — plus a required test (manual line 369) asserting `activity_score` appears
in no weighted score.

**The gap:** its rule lives in the **order-flow** manual while its implementation lives in
**unidesk**, and `unidesk/design/` contains **zero** references to it. A cross-project rule
with no local statement is exactly the kind of constraint that gets violated by a future
agent who never reads the other project's manual.

**What it is actually for**, and why it deserves a section: it is a direction-neutral
abnormal-participation signal. It answers *"is something unusual happening in this name
that price alone does not show"* — which is the observable half of the North Star's
AIRG hypothesis (edge 1) and a natural confirmation input for ignition (edge 2). It is the
one piece of "flow" intelligence available **without** a live feed, which makes it the
bridge between the EOD desk and the order-flow engine.

**Required (not optional):**

1. Write `unidesk/design/REACTOR_SCALE.md` — definition, provenance chain
   (traderlog → manas_os `alpha/activity.py`), the frozen coefficients, the R6 constraint
   **verbatim**, and its intended role against edges 1 and 2.
2. Port the R6 test into `unidesk`'s own suite. A rule enforced only in another project's
   test file is not enforced here. Assert `activity_score` appears in no weighted score,
   in `deriveState`, or in `compareCandidates` — this folds naturally into the §10
   containment invariant of the levels handoff.
3. State its ladder rung. It is an engineered feature (L1), not a prediction — so it is
   eligible for the main desk as *context*, which is what it already does.

## 5 · How the last two weeks relates

None of it was roadmap work. It was the foundation the roadmap stands on:

| Wave | What it actually bought |
|---|---|
| Coherence, surfacing, geometry | the desk stopped contradicting itself |
| Currency, scheduler, desk server | the desk updates without you |
| CI, invariants, error boundaries, refusal reasons | findings stop regenerating |
| Thrust metrics, structural levels spec | the trade-quality defect got measured |

That was the right order — the North Star's own **Backtesting Standards** section demands
point-in-time data, embargo, and beating a simple baseline before any edge claim. You
cannot test six hypotheses on an archive that mixes three corporate-action bases.

But it means: **on the actual roadmap, you are still at the start of Phase 1.**

## 6 · The two things that gate everything

**(a) The archive is on three CA bases.** 393 of 1,571 partitions stale or rejected —
unchanged since 09-02. Any edge test over the archive is meaningless until this is
remediated (spec: B2-3).

**(b) The edge test is scaffolded but unwired.** `research/experiments.py::compare_edge`
and `research/significance.py::deflated_sharpe_ratio` both exist. `run_n5_experiment.py`
implements only `dry-run`. **Nothing calls them.** Until this is wired, no hypothesis in §1
can be confirmed or killed — which is the entire point of the North Star.

**Phase 0 gate** (blocks the AI ladder, PART 13): 31 items — 8 PASS, 11 PARTIAL, 11 FAIL.
The FAILs cluster: **six are one mechanical provenance wave** (SHA256/source/build
manifests, availability ledger, deterministic rebuild, release tag); **two are security
identity** (symbol-keyed history — the ALPHAGEO/UJJIVAN staleness bug is a symptom);
**three need index-membership or F&O data** that may not be purchasable and should be
scoped before scheduling.

## 7 · Where you actually are

```
North Star Phase 1 (EP)        ── detector built, NEVER VALIDATED  ← you are here
North Star Phase 2 (IPO)       ── built, blocked, structurally blind
North Star Phase 3 (Ignition)  ── built, never validated
North Star Phases 4-6          ── not started
Core retrieval (L1.5)          ── built, never evaluated, gated
Order-flow P1/P2               ── not started (correctly deferred)
```

## 8 · Recommended order

1. **B2-3 archive regeneration.** Detached, multi-hour, verify from partition counts on
   disk. Unblocks everything below.
2. **Wire `--experiment a|b`** to `compare_edge` + deflated Sharpe. **This is the roadmap
   step, not a chore** — it is the first time the tool can say whether EP or ignition has
   an edge, and a negative result is a real result.
3. **Evaluate L1.5.** Retrieval is built; measure it against the rule baseline. This
   decides whether the North Star's core capability is real.
4. **Reactor Scale doc + R6 test** (§4). Small, and closes a live governance hole.
5. **Phase 0 Tier A** — the six-item provenance wave, parallelisable, takes the gate from
   11 FAIL to 5.

Steps 2 and 3 are the ones that convert this from a well-engineered scanner into a tested
research tool. Everything else is preparation.

## 9 · Caveats

- Edge-hypothesis statuses come from module inspection and keyword sweeps, not from reading
  each detector against its North Star section. A module existing is not proof it
  implements the hypothesis faithfully — **treat §1 as a map, not an audit.**
- `PHASE0_GATE_AUDIT_A01.md` is dated 2026-09-01, by a different auditor, and six commits
  have landed since. I verified its counts, not its individual evidence rows. **Re-score it
  before planning a Phase 0 wave.**
- Order-flow status is read from handoff filenames plus the manual's task list; I did not
  inspect that project's source.
- No effort estimates anywhere in this document.
