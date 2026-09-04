# BUILD LOG — unidesk self-driving loop (GLM)

**Started:** 2026-09-04 · **Graph:** BUILD_GRAPH_2026-09-04.md (40 nodes + Risk Desk addendum)
**BUILD_STATE.json:** committed alongside every node. This log is appended every ~5 nodes.

---

## Session 1 — 2026-09-04 (through N-27 + Risk Desk N-40/N-41)

### Completed (18 nodes)

| Node | What | Evidence |
|---|---|---|
| N-1 | Canonical index_id | canonicalise_index_rows + invariant; 4,291 rows |
| N-2 | Sectoral index ingest | 15 sectoral indices, 2025→2026-09 |
| N-3 | Universe snapshot in chain | 1,151 rows for 2026-09-03, 98% industry coverage |
| N-4 | require_float fastpath | equivalence 4/4; calls 374.9M→242.3M (−35%) |
| N-5 | 4a profiler | cProfile output committed; before/after compared |
| N-7 | F-6 repo hygiene | node_modules 5,296→0; gitignore; status 303→104 |
| N-8 | REACTOR_SCALE.md + R6 test | 4 tests: no activity in scoring/deriveState/compareCandidates |
| N-10 | E-1 test fix + ISIN boundary | trading-session units; IPOListingFact adapter; 14/14 |
| N-15 | levels.py + tests + REGISTRY | 10/10; no-lookahead both ways; plateau rule; REGISTRY 28 passed |
| N-18 | E-3 circuit bands | MILKYMIST real-print accepted; controls clean |
| N-19 | E-2 announcements store + ingest | ~10.9k rows; knowability rule; 7 tests |
| N-20 | event_relative verification + REGISTRY | provenance clean; 25 truncation tests passed |
| N-21 | SEBI lock-in dates | rule-verified (AM3+AM4 2021); derived_from_rule; 2 tests |
| N-22 | Events screen | IPO overlay; lab-gated; verified rendering both modes |
| N-24 | Group state store | coverage-honest; tri-state EMA; 4 fixture tests |
| N-25 | Group RS percentile + JdK | warm-up None; 7 tests |
| N-26 | Leadership lifecycle | hysteresis, raw+final; 8 tests |
| N-27 | Concentration/density/size-guard | 8 tests |
| N-41 | FIFO round-trip matching | 6 tests; 973 fills → 278 trips, 55 same-day, exact reconciliation |

### Escalated (1)

| Node | Escalation | Status |
|---|---|---|
| N-40 | **E8** — X-03 charter amendment drafted (X03_AMENDMENT_DRAFT.md) | awaiting owner approval; N-42..N-49 BLOCKED |

### In flight (1)

| Node | What | Status |
|---|---|---|
| N-0 | B2-3 archive remediation (Codex owns) | 111/152 sessions re-attached on d1b585eb; worker alive; ~1-2h remaining |

### Blocked on N-0 (5)

| Node | What | Unblocks when N-0 done |
|---|---|---|
| N-6 | 4c columnar store | heavy tests (test_builders_agree) need no live archive job |
| N-9 | CA-basis sample diff | reads events/** — needs stable archive |
| N-11 | Run experiment a/b for real | single-CA-basis archive required |
| N-19 acceptance | 3 results-gaps proof | reads events/** |
| N-12..N-14 | L1.5 eval + EP/ignition validation | dep N-11 |

### Blocked on owner decisions (BUILD_QUESTIONS.md batch 1)

| Node | Question | Default if unanswered |
|---|---|---|
| N-42.. | E8: X-03 amendment approval | BLOCKED (not reversible — charter change) |
| N-43+ | E9: risk fraction / position cap / open-risk ceiling | BLOCKED (not reversible — capital) |
| N-47 | E10: Governor autonomy | builds propose-and-confirm (conservative) |
| N-23 | E1: ipo_base trust flip | stays BLOCKED (conservative) |
| — | E2: 2,300-session backfill | skipped (reversible via resume driver) |

### Graph position

Wave 0: N-0 RUNNING (Codex). Wave 1: 7/8 done (N-6 deferred on N-0).
Wave 2: harness built, real run blocked on N-0. Wave 3: blocked on N-11.
Wave 4: N-15 DONE, N-16/N-17 blocked on N-0 + N-11. Wave 5: N-18/N-19/N-20/N-22 DONE,
N-21 DONE, N-23 evidence assembled. Wave 6: N-24/N-25/N-26/N-27 DONE,
N-28/N-29/N-30 remain. Wave 7: N-31 eligible. Wave 8: blocked on credentials.

### Next nodes (in loop order)

1. **N-28** — RRG-lite + momentum river (rotation UI, deps N-26/N-27 ✓)
2. **N-29** — Theme system (dep N-27 ✓)
3. **N-30** — Market UI + context ribbon (dep N-28, N-29)
4. **N-31** — Phase 0 re-score (read-only, can go any time)
5. When N-0 completes: N-9 → N-6 → N-11 → B2-2 rerun → N-19 acceptance → N-12..
