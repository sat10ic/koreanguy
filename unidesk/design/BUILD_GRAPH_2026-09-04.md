# Build graph — run to completion (2026-09-04)

**Executor:** GLM · **Author:** Claude Opus 5 (spec role)
**Method:** explicit task DAG + self-driving loop. No interval stops. The loop selects its
own next node and halts only on the conditions in §4.

---

## 1 · The loop

Maintain `unidesk/design/BUILD_STATE.json`:

```json
{"node_id": {"status": "TODO|RUNNING|DONE|BLOCKED|ESCALATED",
             "evidence": "...", "commit": "...", "updated": "ISO8601",
             "attempts": 0, "note": "..."}}
```

Then repeat until no node is `TODO` with satisfied dependencies:

```
1. READ  BUILD_STATE.json + git log. Never trust memory of prior turns.
2. PICK  the lowest-numbered TODO node whose dependencies are all DONE.
         If several are eligible, prefer the one unblocking the most others.
3. PLAN  restate the node's done-condition in one line before writing code.
4. BUILD small, focused commits. Never mix two nodes in one commit.
5. VERIFY the done-condition MECHANICALLY. Paste the command output.
         A node is not DONE because it looks done.
6. RECORD status + evidence + commit sha in BUILD_STATE.json. Commit that too.
7. LOOP  go to 1.
```

**Verify from persisted artefacts on disk — never from process exit or absence.** That
mistake has been made twice on this repo.

**Attempt limit:** 2 failed attempts on one node → mark `BLOCKED`, write the reason, move
on. Do not grind. A blocked node does not stop the graph; it stops its dependents.

## 2 · Standing rules (violating any of these fails the node)

1. **Never fabricate a value.** Missing → `None`/`—` with a named reason. Never 0, never a
   substituted average, never an interpolation.
2. **Point-in-time is absolute.** Nothing may use data unavailable at the as-of session.
   Windows exclusive of the current bar.
3. **Every new public callable under `features/`, `primitives/`, `scoring/` gets a
   `test_truncation_invariance.py` REGISTRY entry.** Not optional — the thrust wave shipped
   without it and the guard caught it three days late.
4. **No invented weightings or composite scores.** Two honest numbers beat one blended one.
5. **No dormant code.** Wired into a pipeline AND surfaced, or not shipped.
6. **CI is the gate.** Red CI blocks the next node. Fix before proceeding.
7. **Class-level guards.** When you fix an S1, add the invariant that makes the class
   impossible — not just the instance fix.

## 3 · Environment

- Bash tool is **broken** (`echo ok` fails at shell init). Use PowerShell.
- Python: `C:\Users\satta\Downloads\koreanguy\.venv-orderflow\Scripts\python.exe` — absolute.
- CI: `.github/workflows/unidesk.yml` runs pytest + `run_checks.py` + build + playwright.
- Heavy tests: `$env:UNIDESK_HEAVY_TESTS = "1"`. **Never beside a live archive job.**
- RAM is the binding constraint (~4.8 GB job, ~1 GB free). One heavy process at a time.

## 4 · Halt conditions — the ONLY reasons to stop the loop

**Escalate to owner, mark `ESCALATED`, skip the node, keep going on others:**

| # | Decision | Why it is not yours |
|---|---|---|
| E1 | Flipping `ipo_base` trust from BLOCKED to rankable | trust status is owner-gated in `trust.py` |
| E2 | Running the ~2,300-session backfill | changes what Research/History count |
| E3 | Changing `invalidation` placement | needs N13's result against its kill criterion |
| E4 | The CHOP playbook wording | that is trading advice; you may not author it |
| E5 | Changing `MIN_SESSIONS_DEFAULT` (61) | frozen default with documented rationale |
| E6 | Promoting any unvalidated feature into ranking | needs an experiment verdict |
| E7 | Re-stamping partitions without a full re-scan | needs the N-9 sample-diff result |

**Full stop, ask before acting:**
- Anything destructive or irreversible (deleting data, force-push, history rewrite)
- A node whose spec appears wrong in a way that would corrupt the archive

**Not a halt condition:** a node being large, a negative experiment result, or a blocked
dependency. Negative results are real results — record and continue.

---

## 5 · The graph

Dependencies in brackets. `[-]` = none.

### Wave 0 — in flight (Codex owns; do not touch)

| Node | Task | Done-condition |
|---|---|---|
| **N-0** | B2-3 archive remediation | all 1,603+ partitions read `d1b585eb60fd4f82` |

### Wave 1 — unblocking and hygiene

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-1** | [-] | Canonical `index_id`. `indices.parquet` has `NIFTY 50` (1240) **and** `Nifty 50` (59) — same index, two source tiers; also 500 / MIDCAP / SMALLCAP | one canonical row per index per session; invariant added that fails on a duplicate |
| **N-2** | [N-1] | Ingest NSE **sectoral** indices (IT, BANK, AUTO, PHARMA, FMCG, METAL, REALTY, ENERGY, INFRA). **There are currently zero.** Dated, content-hashed snapshot, `first_seen_at` — mirror `run_ingest_listing_calendar.py` | sectoral index history on disk; depth reported |
| **N-3** | [-] | Add the universe snapshot to the nightly. `universe_snapshots.parquet` stops at 2026-08-20 | newest `as_of_date` == newest report session |
| **N-4** | [-] | `require_float` hot path. 375M calls / 262s = 35% of runtime; `participation.py:35` builds an f-string per element | re-profile shows the reduction; `test_store_equivalence` byte-identical |
| **N-5** | [N-0] | Run the 4a profiler; report where time actually goes | profile output pasted |
| **N-6** | [N-4,N-5] | 4c columnar store, ~4.5 GB → ~1-1.5 GB | add columnar builder to `_BUILDERS`; `test_builders_agree` green |
| **N-7** | [-] | F-6 repo hygiene: `node_modules` still tracked (5,296 files), ~260 untracked at root | `git status --porcelain` < 20 lines; tracked node_modules == 0 |
| **N-8** | [-] | `REACTOR_SCALE.md` + port the R6 rule into this repo's tests | test asserts `activity_score` absent from every weighted score, `deriveState`, `compareCandidates` |
| **N-9** | [N-0] | CA-basis sample diff (`run_ca_basis_sample_diff.py`, already written) | verdict pasted; **escalate E7 either way** |
| **N-10** | [-] | Fix the failing `test_listing_calendar` (`assert 2 == 4`) and commit the E-1 work | that suite green; ingest re-run idempotent |

### Wave 2 — the roadmap step

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-11** | [N-0] | Run `--experiment a\|b` for **real** (harness exists on fixtures) | verdict artifact with hypothesis, arms, n, coverage, DSR, `ca_table_hash` |
| **N-12** | [N-11] | Evaluate **L1.5** (`research/analogue.py`) vs the rule baseline | measured result, coverage reported. **First real answer on the North Star's core capability** |

### Wave 3 — validate the built edges

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-13** | [N-11] | Validate **edge 6 (EP)** — built, never tested | verdict + DSR + coverage |
| **N-14** | [N-11] | Validate **edge 2 (ignition)** — built, never tested | verdict + DSR + coverage |

### Wave 4 — structural levels

Spec: `HANDOFF_2026-09-04_STRUCTURAL_LEVELS_KDE.md`

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-15** | [-] | `features/levels.py` + `test_levels.py` + REGISTRY entry | §1-§2 acceptance tests pasted |
| **N-16** | [N-15] | Emit `support_*` / `resistance_*`. **Do not touch `invalidation`** | three symbols hand-checked; null rate reported |
| **N-17** | [N-16,N-11] | The stop-geometry experiment | full table + DSR + coverage. **Kill criterion fixed in advance: median `stop_thrust_days` > 1.0 while median R:R ≥ 1.13, else rejected.** Then **escalate E3** |

### Wave 5 — event track (IPO + EP)

Spec: `HANDOFF_2026-09-04_EVENT_TRACK_IPO_EP.md`

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-18** | [-] | E-3 circuit bands, interim: locked when `high==low==close` **or** `close/prev_close` within a tick of ±2/5/10/20% | MILKYMIST 2026-09-01 flagged locked; a mere close-on-high **not** |
| **N-19** | [N-10] | E-2 announcements. **Broadcast timestamp, not date** — post-close filing belongs to the NEXT session | three known results gaps with `available_at` proven. Also closes Phase 0 #26 |
| **N-20** | [N-10,N-18,N-19] | `features/event_relative.py` (§4 of that handoff) + REGISTRY | tests green |
| **N-21** | [N-10] | Lock-in dates derived from listing date. **Verify current SEBI periods yourself**; store as `derived_from_rule` | rule cited, never stored as observed fact |
| **N-22** | [N-20] | Events screen (§5) — a lens, never a second ranking | ranked order byte-identical with the screen present/absent |
| **N-23** | [N-20] | IPO edge unblock prep | evidence assembled → **escalate E1** |

### Wave 6 — market rotation

Spec: `HANDOFF_2026-09-04_MARKET_ROTATION_FULL.md`

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-24** | [N-1,N-2,N-3] | Group state store; coverage on every percentage; suppress < 0.80 | `INSUFFICIENT COVERAGE` renders, never a bare number |
| **N-25** | [N-24] | Group RS + acceleration + breadth deltas. Both normalisations: percentile default, JdK in Pro/Lab | ~60-session warm-up returns `None`, not partial |
| **N-26** | [N-25] | Leadership lifecycle with hysteresis | `raw_state` + `final_state` + `state_age_sessions` stored |
| **N-27** | [N-25] | Concentration, density, setup mix, persistence, small-theme guard (`member_count < 4` → LOW_SAMPLE) | guards fire on a constructed case |
| **N-28** | [N-26,N-27] | RRG-lite + momentum river. INTRADAY renders `Unavailable` — **never synthesised from EOD** | ≤15 groups visible; bubble size = `breadth_ema21 × valid_member_count` |
| **N-29** | [N-27] | Theme system. `INFERRED` is **Lab-only**, excluded from production ranking | membership carries `effective_from/to`, `source_type`, `confidence` |
| **N-30** | [N-28,N-29] | Market UI + **§34 stock context ribbon** (highest product value) + §33 candidate linkage | ranked order byte-identical; regime preserved through the link |

### Wave 7 — Phase 0 gate

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-31** | [-] | Re-score `PHASE0_GATE_AUDIT_A01.md` (dated 09-01, ~15 commits stale) | all 31 items re-marked with evidence |
| **N-32** | [N-31] | Phase 0 **Tier A** — SHA256 manifest, source manifest, build manifest, availability ledger, deterministic rebuild, release tag. **Six of eleven FAILs are this one wave** | gate goes 11 FAIL → 5 |
| **N-33** | [N-32] | Phase 0 **Tier B** — effective-dated security identity. Fixes the live ALPHAGEO/UJJIVAN staleness bug | rename continuity test passes |
| **N-34** | [N-31] | Phase 0 **Tier C** — scope PIT index membership + F&O band availability. **Report feasibility; do not promise** | written finding; amended criteria if unobtainable |

### Wave 8 — order-flow (LAST, by owner directive)

Spec: `plan/ORDERFLOW_BUILD_MANUAL.md`. P0.1 and P0.2 are complete.

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-35** | [N-30,N-32] | P1.1 universe + subscription tiers | per manual |
| **N-36** | [N-35] | P1.2 features that survive a slow feed | per manual |
| **N-37** | [N-36] | P1.3 liquidity gate with position capacity | per manual |
| **N-38** | [N-37,N-11] | P2.1 flow score, confidence, state | per manual |
| **N-39** | [N-38] | **P2.2 ablation before anything reaches production scoring** | manual's validation method satisfied |

**Order-flow needs credentials the owner holds.** Reaching N-35 without them = `ESCALATED`,
not blocked-forever. **Never handle broker credentials yourself.**

---

## 6 · Reporting

Update `BUILD_STATE.json` every node. Every ~5 nodes, append to
`unidesk/design/BUILD_LOG.md`: nodes completed, evidence, escalations pending, current
graph position. That file is the owner's window into an unattended run — keep it truthful,
including the parts that failed.

## 7 · The one thing to get right

This graph exists because the build kept stopping between waves and losing context. But
**speed is not the goal — an unattended run that produces unverified work is worse than
stopping**, because nobody knows which parts to trust.

Every node's done-condition is mechanical for that reason. If you cannot verify a node,
mark it `BLOCKED` and say why. Do not mark it `DONE` and move on.

---

## 8 · ADDENDUM — Risk Desk wave (added 2026-09-04, after the graph was issued)

Spec: `handoffs/HANDOFF_2026-09-04_RISK_DESK.md`
Source: `risk_trade_management_engine_technical_spec_v1.md`

**Appended, not renumbered.** N-0..N-39 keep their ids and their state. If your
`BUILD_STATE.json` predates this section, add N-40..N-49 as `TODO` and leave everything
else untouched.

### Why this wave exists

The desk is a **selection** instrument: regime → sector → candidate → trigger, all "what to
trade". This wave supplies the other half — how much, when to leave, what happens when
wrong. Three facts:

- The tool's **worst measured number is a risk number**: median `stop_thrust_days` **0.67**.
- The owner's **audited leaks** are late entries, late exits, micro-sizing, over-trading.
  Three of four are risk and exit management.
- **No exit logic exists.** `trail` / `partial_exit` / `scale_out` / `move_stop` /
  `take_profit` return only trailing *windows*, never a trailing *stop*.

### New escalations — add to §4

| # | Decision | Why it is not yours |
|---|---|---|
| **E8** | The X-03 charter amendment (§ N-40) | scopes what the tool may compute about capital |
| **E9** | Any default risk fraction, position cap, or open-risk ceiling | the owner's capital, not a spec's defaults |
| **E10** | Enabling any *automatic* Risk Governor action | the only component that would act on the owner's behalf |

### The nodes

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-40** | [-] | **Draft** the X-03 amendment. `UI_BUILD_SPEC_V1` X-03 says the playbook "never emits a number"; read literally that blocks this whole wave. The spec resolves it: a **model** authoring risk stays forbidden (§22.1 `AI score → risk multiplier = FORBIDDEN`), deterministic arithmetic is a calculator. Draft the amendment scoping X-03 to the regime→playbook mapping. **Do not self-approve** | amendment drafted and committed → **ESCALATE E8**. N-42+ blocked until approved |
| **N-41** | [-] | **Round-trip matching over the broker fills.** `trades.json` carries `side: BUY\|SELL` for 472 fills but nothing matches them; `sameDayRoundTrips: 64` in `broker.ts:41` is a hand-entered audit constant, not a computation. FIFO or the broker's own convention — **state which**. Pure computation over data already on disk | realised R per round trip for the tradebook; count reconciles against the 472 fills with unmatched fills **reported, not dropped** |
| **N-42** | [N-40✓] | P0 freeze: risk ontology, objective enums (VELOCITY/MAGNITUDE/HYBRID/PERSISTENT), stop-candidate types, policy config, **source-preset registry** | every §2.3 threshold stored as `SOURCE_PRESET` with source, period, strategy context — **never a silent default** → **ESCALATE E9** for the actual defaults |
| **N-43** | [N-42] | P1 Trade Planner: Trade Contract, stop candidates, risk-based size, position cap, open-risk cap, portfolio impact preview | hand-calculation reproduced exactly; **the binding constraint is displayed** ("final qty 2,240 ← liquidity cap binding") |
| **N-44** | [N-43] | P2 Portfolio Heat: planned / stress / open / profit-at-risk as **four distinct fields**, sector clusters, event exposure | sector clusters work today; theme clusters `—` until N-29. Planned risk can never go negative; stress never masquerades as planned |
| **N-45** | [N-43] | P3 Live Trade Manager: state machine, current stop, protection event, profit-at-risk, partials, tranches, pyramiding | protection supports structural anchors, **not only `+1R → breakeven`**; each tranche stored separately |
| **N-46** | [N-41,N-45] | P4 Risk Lab: MAE/MFE, capture ratio, stop simulator, drawdown decomposition | **share the simulator with N-17** — same machinery, opposite side of the same question. Sample-size bands enforced (<20 insufficient). Output reads `Observation`, never `you should` |
| **N-47** | [N-46] | P5 Risk Governor — **manual-confirm only** | proposes a state change with its deterministic reason; owner accepts. Automatic action → **ESCALATE E10** |
| **N-48** | [N-12,N-46] | P6 analogue MAE/MFE as **evidence only** into the planner | `AI score → risk multiplier` remains forbidden and is asserted by a test |
| **N-49** | [N-11,N-46] | P7 challenger research: dynamic risk variants, **offline** | promotion requires monotonic calibration + out-of-sample stability + no regime concentration + drawdown or expectancy lift, hard ceilings unchanged |

### Two things to get right in this wave

**1. N-41 is the cheapest high-value item on the whole board.** It is one matching function
over data already on disk, and it unblocks every calibration in N-46 through N-49. It has
no dependencies — the loop's tie-break rule ("prefer the node unblocking the most others")
should surface it early. Do not leave it until the wave's turn.

**2. Do not build the stop simulator twice.** N-17 asks *"would structural stops beat the
current rule on the archive?"*; N-46's simulator asks *"would a different stop distance have
beaten it on my own trades?"* Same counterfactual machinery, same leakage rule: **no future
swing low may decide a historical trailing stop, and a stopped trade that later rallies
stays stopped** unless a re-entry rule is explicitly modelled.

### Constraints that must survive

- **Never render certainty language** — no "safe trade", "guaranteed stop", "risk-free
  position". Use `CAPITAL PROTECTED UNDER CURRENT STOP`; gap and liquidity risk remain.
- **MTF sizing uses base equity**, never equity + borrowed. Never display "MTF does not
  increase risk" unqualified.
- **Data not available, do not fake:** ASM/GSM flags, broker MTF haircuts, spreads. Circuit
  bands arrive with N-18. Render `—` with the gap named.
- Every risk-changing event is an **immutable audit record** answering "why did my risk
  change?"
