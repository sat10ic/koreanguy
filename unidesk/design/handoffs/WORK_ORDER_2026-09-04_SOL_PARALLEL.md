# Work order — Sol, parallel to GLM (2026-09-04)

**Purpose:** keep two agents working the same branch without collision. GLM owns the
corporate-action and infrastructure lane. Sol owns the research-harness lane. The two do
not share a file.

**Verified at issue time:** archive still `d1b585eb60fd4f82` 1178 / `b3b43b561621b11f` 200 /
`191ac96a61cdfae7` 193 across 1,571 partitions — **B2-3 has not started.** F-6 landed
(`fd77287f`, `14b5385e`). CI is live and caught two real bugs on its first run
(`132d9b62`).

---

## 1 · GLM's lane — do not touch these

| Task | Files Sol must not open |
|---|---|
| B2-2 CA detector false positive | `momentum/data/splits.py`, `run_ca_review_queue.py`, `tests/test_archive_attach.py` |
| **B2-3 archive remediation** | `data/market/research/events/**`, `run_archive_attach_resume.py` |
| F-6 hygiene | `.gitignore`, git index surgery, `git gc` |
| F-1 CI watch | `.github/workflows/**`, `requirements.txt` |
| B2-7 calendar gate | `run_scheduled_refresh.py`, `nightly_desk.cmd`, `TradingCalendar` |
| B2-8 UI statement | `unidesk_terminal/src/lib/veto.ts`, Desk pre-trade panel |
| F-4.3 server persistence | `unidesk/server/**`, `screens/Desk.tsx`, `lib/positions.ts` |

**Two hard rules beyond the file list:**

1. **Do not read or write the event archive while B2-3 runs.** It is RAM-gated and
   multi-hour. A second heavy reader will thrash it and may observe a half-rewritten
   archive. Sol's work in §2 is built against **fixtures**, not the archive.
2. **Do not run `git gc`, `git rm --cached`, or any index surgery.** GLM may take another
   F-6 pass. Commit normally, small and often; if a push races, rebase — never force.

---

## 2 · Sol's lane, in order

### S-1 · Wire the experiment harness — the highest-value item on the board

**Spec:** `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` §11.2 step 2.
**Files (none shared with GLM):** `run_n5_experiment.py`, `research/experiments.py`,
`research/significance.py`, new `unidesk/tests/test_n5_experiment.py`.

`run_n5_experiment.py` implements only `dry-run`; `--experiment a|b` raises
`cmd_not_implemented`. Meanwhile `compare_edge` (`experiments.py:71`) and
`deflated_sharpe_ratio` (`significance.py:95`) are both written and **called by nothing**.
Until this is wired, no edge hypothesis in the North Star can be confirmed or killed.

**Do:**
1. Implement `--experiment a` and `b` end to end: load events → apply walk-forward folds
   and the same-symbol embargo (`leakage.embargo_overlapping_events`) → call
   `compare_edge` → deflated Sharpe → write a verdict JSON.
2. **Build and test entirely on fixtures.** Do not point it at the real archive until GLM
   confirms B2-3 complete — results computed across three CA bases are meaningless and
   would have to be thrown away.
3. Report **coverage alongside quality**. A filter that fires on 20% of events is a
   different object from one that fires on 90%; the verdict is unreadable without it.
4. Verdict JSON is a durable artifact, not a log line — §12.3 of the levels handoff will
   render it. Include hypothesis, arms, n, coverage, DSR, verdict, date, and the
   `ca_table_hash` the events carried.

**Acceptance:** `--experiment a` exits 0 on fixtures with a real verdict; a deliberately
null signal **fails** promotion under DSR (build that fixture and paste both runs).

### S-2 · KDE structural levels — module and tests only

**Spec:** same handoff §1 and §2. **New files:** `momentum/features/levels.py`,
`unidesk/tests/test_levels.py`, plus a REGISTRY entry in `test_truncation_invariance.py`.

**Stop before §3.** Emission wires into `scan.py` / `report_json.py`, and those are better
touched once GLM's lane is quiet. Module + tests + registry entry only.

The no-lookahead test is the one that matters: a pivot at bar *i* must be invisible at
`as_of_index = i + right - 1` and visible at `i + right`.

### S-3 · Reactor Scale doc + R6 test

**Spec:** `STATUS_AND_ROADMAP_2026-09-04.md` §4. **New files:**
`unidesk/design/REACTOR_SCALE.md`, plus a test in this project's suite.

Reactor Scale is implemented here (`features/activity.py`, rendered as `RSch`) but its
governing rule — **R6, "context, never a risk input"** — lives only in
`plan/ORDERFLOW_BUILD_MANUAL.md`. A cross-project constraint with no local statement is one
a future agent violates without knowing it exists.

Port the R6 assertion into `unidesk`'s own tests: `activity_score` appears in no weighted
score, not in `deriveState`, not in `compareCandidates`.

### S-4 · Re-score the Phase 0 gate audit

**Read-only. Zero conflict.** `PHASE0_GATE_AUDIT_A01.md` is dated 2026-09-01 by a different
auditor; roughly ten commits have landed since. Its counts were verified on 09-04 but its
individual evidence rows were not.

Re-score all 31 items, mark which changed, and keep the same PASS/PARTIAL/FAIL vocabulary.
Do not plan a Phase 0 wave off the stale version.

---

## 3 · Sequencing between the lanes

```
GLM:  B2-2 ─→ B2-3 (long, exclusive) ─→ B2-7 / B2-8 / F-4.3
Sol:  S-1 (fixtures) ─→ S-2 ─→ S-3 ─→ S-4
                    ↘
                     after GLM confirms B2-3: run S-1 for real
```

**The join:** the moment B2-3 completes, S-1 runs against a single-basis archive and the
first real edge verdict becomes possible. That is the point of running these in parallel —
the harness is ready the instant the data is trustworthy.

**Do not let S-1 wait for B2-3.** Building the harness is the long pole; the archive job is
mostly waiting.

## 4 · What neither agent should do yet

- **Do not change `invalidation`.** Structural stops stay descriptive until the §4
  experiment returns a result against its stated kill criterion.
- **Do not build the §12 research cockpit yet.** It renders experiment verdicts; with no
  verdicts it is a set of empty frames. It lands after S-1 has run for real.
- **Do not start order-flow P1/P2.** Last, by owner directive.
