# GLM execution plan — KDE structural levels + event track (2026-09-04)

**Integrates:** `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md` (governing, §10 containment)
+ `HANDOFF_2026-09-04_EVENT_TRACK_IPO_EP.md` (For: Sol, contained by KDE §10)
+ `WORK_ORDER_2026-09-04_SOL_PARALLEL.md` (lane boundaries)
+ my in-flight B2-3 continuation (`HANDOFF_B2_3_REQUIRE_FLOAT_FASTPATH_PAUSED_FOR_GLM.md`).

**Lane reality check (verified in tree):** Sol's S-1 is in flight (`run_n5_experiment.py`
modified, `test_n5_experiment.py` new). Sonnet's E-1 is in flight (`listing_calendar.py`,
`run_ingest_listing_calendar.py`). `momentum/features/event_relative.py` (225 lines) +
tests already exist uncommitted — provenance unverified; before the event track's §4 is
counted done, someone must confirm it mirrors `thrust.py` conventions and has REGISTRY
entries, or it repeats the thrust wave's three-day-late discovery.

---

## The dependency spine (what actually orders this work)

```
B2-3 finish (me)  ──→  single-CA-basis archive
      │                        │
      │                        ├──→ G-4 structural-stop experiment ──→ G-5 (only if pass)
      │                        └──→ S-1 harness run-for-real (Sol)
      │
Target-1: equivalence gate ──→ re-profile ──→ before/after ──→ split note
      (decides fastpath keep/revert → resume speed of the last 149)
```

Everything experimental hangs off one hard gate: **one corporate-action basis**.
1,454 of 1,603 partitions are current; 149 still carry the rejected hash. The experiment
(G-4), Sol's first real S-1 run, and any event-track backtest are all meaningless until
those 149 flip.

## Wave 0 — finish the paused B2-3 continuation (me, now)

In the handoff's stated order, no deviations:

1. **Equivalence gate** — running now (`_b23_equivalence_gate.log`; fresh ingest vs the
   1.16 GB snapshot, byte-identical digests on a probe session).
   - PASS → keep the `require_float` fast path; commit the slice
     (participation.py + its tests + equivalence test + `run_archive_attach_resume.py`
     fingerprint guard + `store_fingerprint.py` — the slice is wider than the handoff's
     file list because the fingerprint guard test is wired to it).
   - FAIL → `git checkout` the fast path (participation.py + its test). **Do not** weaken
     the assertion. Skip the "after" profile — there is nothing optimized to measure —
     and record Target-1 as attempted-and-reverted.
2. **Re-profile** (`profile_scan_session.py --sessions 3`; writes the 3 probe sessions —
   no worker live while it runs). Compare against Codex's before: total 739s,
   `require_float` 262s / 374,929,071 calls, `participation._series` 163s,
   split candidates 217s. Report measured numbers only.
3. **Split-detection design note** (written analysis, no code): the bar window grows each
   session, so a symbol-keyed memo is forbidden; establish the incremental rule or prove
   historical output cannot change.
4. **Attribution + slice commit**; preserve Codex's record.
5. **Then stop and ask the owner to resume the archive writer** — the pause directive is
   explicit that the worker restarts only on the owner's word after Target-1 measurement.

## Wave 1 — close B2-3 (me, after owner resumes)

- Resume worker (`--stale-partitions-only` no longer correct — attempt-3 was a full-run
  worker at 96/249; the resume recomputes from disk: 149 rejected-basis partitions remain).
  With the snapshot + (if kept) fast path, the re-ingest is ~1 min and processing should
  be measurably faster — record the rate.
- Acceptance: hash tally shows 1,603/1,603 on `d1b585eb60fd4f82`;
  `sessions_needing_label_refresh` → only recent label-pending. Paste both.
- B2-2 test rerun (`test_archive_attach.py`) — same ingest; run in the same window.
- **B2-3 closed** unlocks G-4 and S-1-for-real. Announce on the branch.

## Wave 2 — parallel, disjoint files

**Me (infrastructure lane):**
- **G-3 emission** — `scan.py` / `report_json.py`, six support/resistance fields nested
  under `experimental` per §10.3 (NOT flat; promotion after G-4 is a separate commit).
  `scan.py` is quiet once B2-3's worker is done — this is why G-3 waits for Wave 1.
- **§10.4 containment invariants** — `check_experimental_fields_not_in_decision_path` +
  `check_experimental_surfaces_labelled` in `checks/published_invariants.py` (my file),
  each proven to fire on a planted defect (F-7 pattern).
- **Review Sol's S-2 `levels.py`** when it lands: verify the no-lookahead contract is in
  the signature, the REGISTRY entries are `kind='series'` with real truncation checks, and
  the KDE provenance docstring matches the clean-room convention.

**Sol (research lane, unchanged order):** S-1 finish on fixtures → S-2 levels module +
tests + registry → S-3 → S-4 → then E-3 step 1 (exact circuit-locked check; acceptance:
MILKYMIST flagged, a high-close non-frozen name not) → E-2 announcements ingest (the
long pole; `available_at` semantics; doubles as availability-ledger gate #26) → §4 event
features (verify `event_relative.py` provenance + registry first) → §5 Events screen last.

**Neither lane touches `invalidation`, `deriveState`, or `compareCandidates`.**

## Wave 3 — G-4, the experiment (needs: B2-3 done + S-1 done + G-3 emitted)

- Counterfactual structural stop via `nearest_below(levels, trigger)` − stated ATR
  fraction buffer; re-run the **existing** stop-aware labeller; compare against the
  metrics table; `compare_edge` + deflated Sharpe + same-symbol embargo; coverage
  alongside quality; **kill criterion frozen now**: median `stop_thrust_days` > 1.0 while
  median R:R ≥ 1.13, else rejected-and-recorded.
- Executor: me (archive-side), with Sol's harness; verdict JSON as the durable artifact.

## Wave 4 — only on a G-4 pass

G-5 promotion (flat fields + chart levels + card chip + the render invariant), each cited
to the experiment commit. On a fail: negative-findings board entry, levels stay nested and
Lab-badged.

## Wave 5 — Events screen + Mode ladder (Sol, after its E-chain lands)

§10.2 `Mode = beginner | pro | lab` (monotonic, `atLeast()`, never default, loud banner) —
built by whoever lands first UI that needs it, before any Lab surface renders. §10.6
containment tests: byte-identical ranked order across modes (the diff must be empty),
tier badges, both invariants green + proven to fire. §6 lock-in countdown: verify current
SEBI periods from the rule source; store as `derived_from_rule`.

## Conflicts and coordination rules

| Risk | Rule |
|---|---|
| `test_truncation_invariance.py` REGISTRY — three agents add entries | Small commits, rebase never force; entries are append-only per module block |
| `scan.py` / `report_json.py` — G-3 (me) vs event features reading reports | G-3 waits for Wave 1; event track reads reports, doesn't write them |
| `data/market/research/events/**` — archive writers vs readers | One writer at a time, ever; readers only when no writer is live (gate/profile obey this) |
| RAM sequencing | Never two heavy jobs: gate → profile → resume worker, strictly serial |
| `experimental` nesting | Backend nests; `deriveState`'s flat type makes leakage a compile error; the invariant proves it at runtime |
| Working tree is multi-agent | Commit small and often; only my slice's files per commit; never index surgery on others' paths |

## Explicitly deferred (unchanged)

§6 regime-conditioned geometry (after G-4), §8.3 conformal intervals (after L1.5 has a
measured result), §12 research cockpit (after S-1 runs for real), order-flow P1/P2 (owner
directive), F-4.3 server-side confirmation, CI green watch (fixes pushed; observing).
