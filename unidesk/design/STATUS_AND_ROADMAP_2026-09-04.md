# Where the build actually is — status and roadmap (2026-09-04)

**Written because the plan has fragmented across seven handoffs.** One page: what the
original plan was, what shipped, what is left, and whether Phase 0 can advance.

Every status below is verified from the tree or the data on 2026-09-04, not from commit
messages or completion handoffs.

---

## 1 · The original plan, and where each stage landed

The approved plan had six stages. Status now:

| Stage | Goal | Status |
|---|---|---|
| **1 · Coherence** | one session date across every screen; kill the `SESSION` fixture | ✅ **Done** |
| **2 · Surface the intelligence** | render `stock_quality`, `activity_score`, trust, breadth | ✅ **Done** |
| **3 · Trade geometry** | emit `trigger` / `invalidation` / `rr` per candidate | ✅ **Built** — but placement quality is the open question; see §4 |
| **4 · Correctness debt** | fix the staleness detector, then regenerate the archive on the clean CA basis | ⚠️ **Half done.** Detector fixed (`archive_attach.py` compares `ca_table_hash`). **The regeneration was never run.** |
| **5 · Currency** | a downloader, and a desk that refreshes itself | ✅ **Done** — two downloaders exist, the nightly is scheduled, the desk server + Run button ship |
| **6 · Test for edge** | implement `--experiment a\|b`, wire `compare_edge`, add deflated Sharpe | ❌ **Not done.** See §3 |

**So: four of six shipped. The two that did not are the two that decide whether any of this
makes money.**

## 2 · Stage 4 — the archive is still on three corporate-action bases

Measured today across all 1,571 partitions in `data/market/research/events/`:

| `ca_table_hash` | Partitions | |
|---|---|---|
| `d1b585eb60fd4f82` | 1,178 | current, verified 4-action table |
| `b3b43b561621b11f` | 200 | older pre-audit basis |
| `191ac96a61cdfae7` | 193 | **the explicitly rejected 55-action table** |

**393 of 1,571 (25%) are wrong, unchanged since the 2026-09-02 audit.**

Front-of-book is clean — the newest report reads `actions_applied: 4`. But History and
Research compute over the *whole* archive, so their statistics mix three adjustment bases.

**This is the single highest-leverage unblocked task**, because it gates everything in §3
and §4. Its spec is B2-3 in `HANDOFF_2026-09-02_CORRECTIONS_AND_THRUST_UI.md`. It is a
multi-hour detached job: **verify progress from persisted partition counts, never from
process absence** — that mistake has been made twice on this repo.

## 3 · Stage 6 — the edge test is scaffolded but not wired

| Piece | State |
|---|---|
| `research/experiments.py::compare_edge` | ✅ exists (line 71) |
| `research/significance.py::deflated_sharpe_ratio` | ✅ exists (line 95) |
| `research/walkforward.py` folds + embargo | ✅ exists |
| `run_n5_experiment.py --experiment a\|b` | ❌ **only `dry-run` is real** |

The verdict engine and the significance test are both written. **Nothing calls them for a
real experiment.** This is the "no dormant code" rule being violated in the place it
matters most — the tool cannot currently answer whether any detector has an edge.

Blocked on §2 (a mixed-basis archive makes any verdict meaningless).

## 4 · The open product defect

Median `stop_thrust_days` **0.67**; 37 of 57 inside 0.75. Stops sit inside ordinary daily
movement. Every wave so far fixed how this is *reported* — the newest one now refuses to
rank sub-1R setups as PRIME, which is honest but means **21 of 61 candidates on 2026-09-03
are rejected** for what may be a stop-placement artefact.

Spec: `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md`. Also gated on §2.

---

## 5 · Can Phase 0 advance? Yes — and most of what is left is bookkeeping

`PHASE0_GATE_AUDIT_A01.md` scores 31 checklist items:

| | |
|---|---|
| PASS | 8 |
| PARTIAL | 11 |
| **FAIL** | **11** |
| N/A | 1 |

The gate blocks PART 13 (the AI ladder, A-02…A-07). The 11 FAILs are **not** eleven
separate problems — they cluster into three tiers:

### Tier A — provenance bookkeeping · 6 of the 11 · cheap, no research needed

| # | Item |
|---|---|
| 2 | SHA256 manifest populated |
| 24 | Source manifest |
| 25 | Build manifest |
| 26 | Availability ledger (20-session first-seen) |
| 30 | Deterministic rebuild hashes |
| 31 | Release tagged `PHASE0_DATA_V1.0.0` |

**All six are the same job:** hash every raw file, record when it was first seen, stamp
which inputs produced which build, make a rebuild reproducible, tag it. No new data, no
modelling, no research. This is exactly the kind of work the last two waves did well (CI,
invariants, refusal reasons), and it is **more than half the gate**.

### Tier B — security identity · 2 of the 11 · real engineering

| # | Item |
|---|---|
| 4 | Security identity is effective-dated |
| 5 | Symbol/series history preserved |

Everything is keyed on the SYMBOL string, so a renamed ticker becomes a new instrument and
its history disappears. **You have already been bitten by this** — the ALPHAGEO / UJJIVAN
staleness the 2026-09-01 audit found is a symptom. Real design work, but bounded, and it
fixes a live bug rather than only ticking a box.

### Tier C — needs data you may not have · 3 of the 11 · scope these before committing

| # | Item | Obstacle |
|---|---|---|
| 14 | PIT membership reconstructed | needs historical index constituents |
| 19 | Breadth uses PIT Nifty 500; denominator stored | same |
| 12 | F&O dynamic-band distinction | needs an F&O band source |

Historical index membership is the classic Phase 0 stopper — it is often simply not
purchasable at a retail price. **Scope the data availability before promising these.** If
they cannot be sourced, the honest resolution is an amended acceptance criterion recorded
as a decision, not a fudged PASS.

### Verdict on the question

**Yes, Phase 0 can advance, and further than it looks.** Six of eleven FAILs are one
mechanical wave. Two more are a bounded engineering task that also fixes a real bug. Only
three depend on data acquisition, and those should be scoped before they are scheduled.

The 11 PARTIALs are open remainders on things already built — they need closing notes and
small completions, not new construction.

---

## 6 · What blocks what

```
B2-3 archive regen (§2)
   ├── Stage 6 edge test (§3)
   └── structural-levels experiment (§4)

Phase 0 Tier A (bookkeeping)  ──┐
Phase 0 Tier B (identity)     ──┼── Phase 0 gate ── PART 13 (AI ladder, L1.5 onward)
Phase 0 Tier C (data, scope)  ──┘

F-6 repo hygiene ── independent of everything, blocks nothing
```

Note that **the AI work is the most gated thing on the board** and the least urgent. L1.5
(`research/analogue.py`) is built but has never been evaluated for edge.

## 7 · Recommended order

1. **B2-3 archive regeneration.** Unblocks two workstreams. Detached, multi-hour, verify
   from partition counts on disk. Nothing else should run in the same wave.
2. **Phase 0 Tier A** — the six-item provenance wave. Independent of B2-3, so it can run
   in parallel by a different agent. Takes the gate from 11 FAIL to 5.
3. **Stage 6 — wire `--experiment a|b`** to the existing `compare_edge` + deflated Sharpe.
   Only after B2-3. This is the first time the tool will be able to say whether it works.
4. Then either the structural-levels experiment (§4) or Phase 0 Tier B, depending on
   whether trade quality or data integrity feels more pressing.

**F-6 (repo hygiene)** can be picked up by anyone at any time; it blocks nothing but makes
everything else easier to see.

## 8 · What this document does not claim

- Verified today: the CA hash tally, the N5 runner state, the presence of `compare_edge`
  and `deflated_sharpe_ratio`, and the Phase 0 verdict counts.
- **Not re-verified today:** the individual PASS/PARTIAL evidence rows in
  `PHASE0_GATE_AUDIT_A01.md` (dated 2026-09-01, by a different auditor). Several waves have
  landed since; some rows may have improved without being re-scored. **Re-score the
  checklist before planning a Phase 0 wave** — it is three days and six commits stale.
- No effort estimates. Tier A is small, Tier B is bounded, Tier C is unknown until the data
  question is answered. Anyone quoting a date from this document is guessing.
