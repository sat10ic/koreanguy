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

---

## 9 · ADDENDUM 2 — Outcome semantics + progressive disclosure (added 2026-09-05)

Source: `tonight_page_review_outcome_model.md` (owner-supplied UX/product review).
**Appended, not renumbered.** N-0..N-49 keep their ids and state. Add N-50..N-60 as `TODO`.

### 9.1 · One dependency amendment to an EXISTING node — read this first

**N-11 (run `--experiment a|b` for real) now depends on N-50, N-51 and N-52.**

**Outcome semantics are a BASIS, exactly like the corporate-action table.** Every verdict
computed under one outcome definition is invalid under another. B2-3 taught this lesson at
the cost of a multi-hour rerun; do not learn it twice. If N-11 runs before the outcome
model is settled, every experiment result must be recomputed.

No other node changes.

### 9.2 · The real gap in the current labeller — verified, not assumed

`research/labels.py:89-98` is already careful and says so: *"OHLC cannot determine intrabar
ordering, so a bar which both reaches a target and touches the stop must never be recorded
as a captured positive R. Optimistic-by-default is forbidden."* The review's
`PATH_AMBIGUOUS` concern is therefore **already handled within a bar**, by the conservative
policy the review itself lists as acceptable (§14).

**The gap is across bars, and neither existing field closes it:**

- `r_multiple` is **stop-dominant**: `stop_hit = any(lo <= stop for lo in l)` over the whole
  horizon, so a trade that reached +1.8R on bar 2 and stopped on bar 9 is labelled **-1R**.
- `potential_r_multiple` is **stop-blind**: MFE over the whole horizon, including moves that
  occurred *after* the stop would have fired.

So today you cannot distinguish **"the setup failed"** from **"the setup worked and gave it
back"**. That distinction is the review's `WORKED` state, and it is the single most useful
thing in the document.

Note what this does *not* mean: `r_multiple` is not wrong. It correctly answers *"what
happened to a fixed-stop position held to the horizon"*. It simply does not answer *"did
+1R arrive before -1R"*, and nothing else does either.

### 9.3 · The nodes

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-50** | [-] | **First-touch ordering.** Compute `time_to_1r`, `time_to_2r`, `time_to_stop` per event and derive the 8-state model: `NO_TRIGGER · WORKED · WIN · STOPPED · FLAT · OPEN · NO_DATA · PATH_AMBIGUOUS`. `WORKED` = +1R before −1R; `WIN` = +2R before −1R. **Keep `r_multiple` and `potential_r_multiple` unchanged** — this is an added dimension, not a replacement | on a hand-built fixture: +1.8R on bar 2 then stop on bar 9 returns `WORKED`, while stop on bar 1 returns `STOPPED`. Both still report `r_multiple = −1R`. Paste both |
| **N-51** | [-] | **Setup-family review horizons**, configurable and versioned. One 10-bar horizon for every family is wrong — EP resolves in 3-5 bars, IPO base in 10-15. Ship the review's table as **defaults, not truth**, in the frozen-config registry | horizons versioned and readable from config; **never silently tuned after observing performance** — that is the review's own rule and it is the one most likely to be broken |
| **N-52** | [N-50,N-51,N-0] | **Re-label the archive on the new outcome basis.** Same shape as B2-3: a basis change requires a rewrite, not a patch | every partition carries the new `outcome_basis_version`; tally reported before and after |
| **N-53** | [-] | **Four distinct missing-value states** internally: `NOT_APPLICABLE · MISSING_DATA · NOT_COMPUTED · INSUFFICIENT_HISTORY`. Today every one of them renders as `—`, which the honesty layer treats as equivalent when they are not | tooltip exposes the specific state; the four are distinguishable in the report JSON |
| **N-54** | [N-53] | **Sample-confidence labels + coverage-based column hiding.** `Power Play n=1` must never visually compete with `Inside Bar n=3586`; a metric under 70% coverage is hidden from Beginner by default | `INSUFFICIENT SAMPLE` renders instead of a headline hit rate; coverage counts shown in the Columns menu |
| **N-55** | [N-52] | **Prior Calls scorecard** on the new model, with the basis stated on screen: `+1R = worked · +2R = win · −1R = stopped · family horizon` | the panel shows all 8 states with counts, avg outcome, avg MFE, avg MAE. **No average printed without saying what entered the denominator** |
| **N-56** | [-] | **Jargon translation matrix** (review §103) as a single centralised dictionary — MFE → "best move after entry", right-censoring → "some calls are too new to judge", etc. Beginner tooltips still show the technical term | one module, no per-screen duplication; every Beginner surface reads from it |
| **N-57** | [N-56] | **Beginner/Pro/Lab density separation** on Desk, History, Research (review §58, §104). Beginner = interpretation, Pro = trading evidence, Lab = scientific evidence | the §104 matrix implemented; ranked order still byte-identical across modes (§10.6) |
| **N-58** | [N-56] | **Cumulative-R reframe.** It currently reads as account equity and is not. Beginner: "Scanner results over time — this is NOT account profit". Pro: "Scanner expectancy curve" with gross/net status, call count, overlap warning | the words "NOT ACCOUNT PERFORMANCE" visible in both modes |
| **N-59** | [-] | **Candidates progressive disclosure** (review §26-§56): research presets, filter wall behind `More filters`, Beginner table to ~6 columns, column toggles into a Columns menu, checkboxes either wired to Compare/Watchlist or removed | Beginner default shows ≤6 columns; every landscape mode carries a plain-language explanation |
| **N-60** | [N-59] | **Research Lens becomes operational** (review §32-§36). Today it is a regime label with a sentence. Clicking "Show strongest CHOP fits" must apply named filters and **show exactly what changed** | applied filters listed explicitly with a `Clear lens` control. **Never an opaque action** |

### 9.4 · What this review gets right that the audit missed

- **Outcome semantics as the central unresolved product issue.** The audit found symptoms
  (frozen prior calls, a censored 0% hit rate) and GLM repaired them. This names the
  underlying cause: there is no outcome *model*, only a labeller.
- **`WORKED` vs `WIN`.** A binary win/stopped collapses "setup worked, exit was late" into
  "setup failed". Those need different fixes.
- **Family-specific horizons.** One 10-bar rule across eight setup families is a real flaw
  and nobody had flagged it.
- **Four missing-value states.** The honesty layer renders `—` correctly but conflates four
  distinct causes behind it.

### 9.5 · What NOT to do

- **Do not run N-11 before N-52.** Outcome semantics are a basis; verdicts computed under
  the old one are not comparable to verdicts under the new one.
- **Do not replace `r_multiple`.** It answers a valid question correctly. Add the ordering
  dimension beside it.
- **Do not tune review horizons after observing performance.** The review says this
  explicitly and it is the rule most likely to be broken quietly.
- **Do not let the Research Lens apply hidden filters.** If the user cannot see what
  changed, it is an opaque action regardless of how deterministic it is underneath.
- **Do not simplify away research capability** (review §56) — reduce default *exposure*,
  keep the depth in Pro/Lab.

---

## 10 · ADDENDUM 3 — Group / theme linkage (added 2026-09-05, owner-raised)

Owner: *"sectors and themes have a very strong influence on stock movements, especially in
such choppy markets, and that is not being leveraged by the tool well enough."* Named
examples: milk-based stocks last week; cables and AI/Datacenter currently working;
`STLTECH`, `SETL`, `WELCORP`, `MANIND` carrying no such linkage.

**Appended, not renumbered.** N-61..N-68 are new and `TODO`.

### 10.1 · Measured state — all figures from `tonight_2026-09-03.json` and the bundled files

| Fact | Value |
|---|---|
| Sector/industry/theme fields on a candidate row | **zero — absent, not null** |
| Candidates resolvable to sector+industry via the vendor file | **61 / 62 (98%)** — the data exists |
| UI consumers of `rotation.json` (351 KB, bundled) | **zero** — exported, shipped, read by nothing |
| `rotation.json` sector names joining to `sector_mapping.json` sectors | **3 of 15** (`Auto`, `FMCG`, `Realty`) |
| `run_export_rotation.py` references to "industry" or "theme" | **0 and 0** — index-level only |
| Rotation session vs report session | **2026-09-04 vs 2026-09-03** — they disagree |
| Distinct sectors / industries in the vendor mapping | **22 / 234** |
| Industries with ≥5 members | **119 of 234, covering 2,522 of 2,772 symbols (91%)** |

So the mapping is good, the RRG math exists, and **the two are not connected to each other
or to a candidate.** This is a §2.5 dormant-code violation, not a missing feature.

### 10.2 · Why sector-level rotation cannot answer the owner's question

His four named symbols sit in **four different sectors**:

| Symbol | Vendor sector | Vendor industry |
|---|---|---|
| `STLTECH` | Information Technology | Computer-Networking |
| `SETL` | Capital Goods | Industrial Products & Manufacturing |
| `WELCORP` | Metals & Mining | Iron & Steel |
| `MANIND` | **not in the mapping at all** | — |

He groups them by theme; the taxonomy scatters them across four buckets. **A 15-index
sector RRG structurally cannot express this.** Checked against the 234 industries:

- **"milk"** → `Dairy Products` (5 members). **Industry level holds it.**
- **"cables"** → `Cables - Electricals` (13) **and** `Cables - Electricals Companies` (7) —
  the same theme split across two vendor buckets. A dedupe defect, not a taxonomy limit.
- **"pipes"** (`WELCORP`, `MANIND`) → **no industry contains the word.** Both fall into
  `Iron & Steel` (96 members) alongside everything else ferrous.
- **"AI / Datacenter"** → **no bucket at any level.** Spans IT, Capital Goods, Power and
  Metals by construction.

**Conclusion:** industry (234 buckets) carries *most* of what he means and is entirely
uncomputed — that is the cheap, high-value win. A true theme layer is needed only for the
cross-sector cases, and it cannot be derived from any NSE or vendor taxonomy.

### 10.3 · The governance constraint — read before designing N-63

`unidesk_terminal/src/lib/sectors.ts:1-4` records D-10: *"this is reference data, never
merged into candidate rows by the backend — the UI joins it for display only."*

**Do not break D-10 to make this easier.** The join stays in the UI. What the backend owes
the UI is the *group's rotation state* in a consumable file — not sector labels stapled onto
candidate rows. If a node appears to require backend merging, that is an escalation, not a
judgment call.

### 10.4 · The nodes

| Node | Dep | Task | Done-condition |
|---|---|---|---|
| **N-61** | [-] | **Industry-level group RS.** Extend the N-28 RRG maths from 15 sectoral indices to equal-weight synthetic baskets over the **119 industries with ≥5 members**. Same RS_Ratio / RS_Momentum, same percentile normalisation. Membership floor is a **frozen, versioned constant** with its rationale | `rotation.json` gains an `industries` array with ≥110 entries; coverage count and the excluded-industry count both reported. `Dairy Products` and both `Cables` buckets present |
| **N-62** | [-] | **Fix the join and the buckets.** (a) An explicit crosswalk table between the 15 index names and the 22 vendor sectors — **a literal table, never fuzzy string matching**. (b) Merge `Cables - Electricals` + `Cables - Electricals Companies` and sweep the other 234 for the same defect. (c) Reconcile the rotation/report session mismatch | crosswalk covers all 15 index names or names the unmatched ones explicitly; duplicate-bucket sweep reports every pair found and merged; rotation session == report session or the gap is displayed |
| **N-63** | [N-61,N-62] | **Group context reaches the UI, D-10 intact.** The desk server serves industry+sector rotation state keyed by group name; the UI joins symbol → industry → state. **No sector field is added to a candidate row** | `sectorFor()` gains a sibling `groupStateFor(symbol)` returning the group's rotation state or `null` with a named reason. `rotation.json` has consumers |
| **N-64** | [N-61] | **Theme layer, two sources.** (a) `config/themes.yaml` — an owner-curated cross-sector seed (cables, dairy, pipes, AI/datacenter), symbols listed explicitly, versioned. (b) A co-movement cluster job as a **discovery aid** that proposes candidate groupings. **Ships empty until the owner supplies (a)** — see E10 | schema + loader + tests land with an empty seed; clustering job outputs proposals to a review file, never straight into the product |
| **N-65** | [N-63] | **Surface it where he looked and found nothing:** `CandidateCard.tsx` (the Tonight feed card — currently has no sector reference at all) gains its industry and that group's state; Tonight gains a "what is working" strip ranked by group RS with the member count per group | a Tonight card for a `Dairy Products` name shows the industry and its rotation state; an unmapped symbol shows a named reason, never a blank |
| **N-66** | [N-62] | **Unmapped-symbol coverage as a visible number.** `MANIND` is absent from a 2,772-symbol vendor file and `MOREALTY` was unmapped in tonight's 62. Publish the count and the list | coverage % in the honesty footer; the unmapped list is reachable from the UI |
| **N-67** | [N-63,N-11] | **Validate before it influences anything.** Does group strength actually separate outcomes? Run it as an experiment with a kill criterion fixed in advance | verdict + DSR + coverage. **Until this passes, group state is context-only** |
| **N-68** | [N-64] | Theme-level RS once a seed exists, same maths as N-61 | per-theme RS with member counts; themes below the floor excluded and named |

### 10.5 · New escalation — append to §4

| # | Decision | Why it is not yours |
|---|---|---|
| E10 | **Authoring theme membership** — deciding which symbols constitute "AI/Datacenter", "cables" or any theme | a theme is a claim about market narrative, not a computable fact. Same class as E4. You may build the schema, the loader, the maths and the clustering *proposals*; the owner authors the list |

### 10.6 · What NOT to do

- **Do not put group state into ranking or scoring before N-67 passes.** That is E6 and §2.4.
  Context beside a candidate is not the same as a factor inside its score.
- **Do not break D-10** (§10.3) to simplify the join.
- **Do not fuzzy-match sector names.** 3 of 15 match exactly; a similarity function would
  silently mis-join the other 12. Use a literal crosswalk that fails loudly.
- **Do not invent theme membership**, including "obvious" cases. E10.
- **Do not compute a group RS over a 1-member group.** The floor exists so a single stock
  cannot masquerade as a working theme — this is the `Power Play n=1` problem (N-54) in a
  new place.
- **Do not blend group strength into `setup_quality` or any composite.** §2.4.
