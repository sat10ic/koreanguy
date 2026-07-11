# Review — "Manas OS Rework: TradeTM-First Indian Trading Doctrine" (PLAN 1)

Reviewer: Opus main thread, 2026-07-11. Every "done" call below was checked against the
live repo (file / grep / commit), not asserted from memory. Verdict, then a done-vs-greenfield
map, then the genuine gaps and a recommended reframe.

## Verdict

**Doctrinally the strongest statement of intent this project has had — but written as a
greenfield 9-phase waterfall when ~half of it is already built or in flight, and it gates all
product work behind a full corpus re-audit.** Adopt its teacher hierarchy and evidence
discipline as the constitution; do NOT execute its sequence literally, or you re-do done work
and delay the concrete things the user actually feels missing.

The one genuinely new doctrinal idea worth lifting immediately: **attach Arora/Stocksgeeks
rules to a TradeTM *stage* rather than run them as equal competing lenses.** The current debate
injects lenses roughly in parallel; making TradeTM the spine that Arora/SG hang off is a real,
contained upgrade.

## Done vs. what the plan treats as greenfield

Legend: ✅ built · 🟡 partial · ⬜ genuinely greenfield.

| Plan item | State | Evidence in repo |
|---|---|---|
| Workflow: Today→Discover→Watch→Decide→Plan→Manage→Learn | ✅ | V4 IA shipped as MARKET·SCANNERS·SHORTLIST·DEBATE·(TRADE PLAN)·POSITIONS·JOURNAL (`desk/src/App.jsx`) |
| Four-phase situational model (Demand/Supply Domination, Lack of Demand/Supply) | ✅ | `regime/four_phase.py` (M9), all 4 phases; surfaced on MARKET home + tonight's-call |
| Regime as **scored objection**, only safety states hard-block | ✅ | `scanner/gates.py` — 42 objection refs; NO_TRADE stays hard; regime family-ban → objection (M3) |
| Judgment NOT silently turned into hard numeric gates | ✅ (as of today) | today's candidacy-relax: fresh-leg extension / trend-template / delivery → visible objections for mover families, not silent kills (commit `d236b5ef`) |
| Living watchlists (what confirmation is missing, character change, source) | ✅ | `agent_watchlist` + curator_delta + dated PROMOTE/HOLD/DEMOTE/DROP events; SHORTLIST tab |
| Arora scanners under TradeTM opportunity categories | 🟡 | SCANNERS tab has 19 practitioner presets grouped by owner; NOT yet reorganized *under TradeTM stages* |
| Stocksgeeks IPO / inside-bar / MBI specialist detections | 🟡 | ipo_base, ipo_inside_bar, long_tail detectors live; MBI = `regime/snapshot.py` burst/warning-day; J-curve/AOI still absent |
| Agents reason TradeTM-context-first | 🟡 | `LENS_TRADETM_CORE.md` injected first in `agents/context_pack.py`; but seats are not yet *staged* (TradeTM→Arora→SG→devil's-advocate→risk) as the plan specifies |
| Evidence-status ladder (VALIDATED/PROMISING/EXPERIMENTAL/UNPROVEN/CONTRADICTED) | 🟡 | only `EXPERIMENTAL` + `UNPROVEN` labels used in code; a *different* trust-ladder exists (`scanner/expectancy.py`: n<20 descriptive → operational). The 5-label alpha-status system is NOT implemented |
| Deterministic risk sovereign; fixed-% audited vs ADR via replay before change | ✅ (policy) | risk gate stays hard/LOCKED; WAVE_L holds ADR-vs-fixed changes pending replay + user sign-off |
| Progressive disclosure (plain view + Evidence drawers) | ✅ | beginner/expert toggle app-wide (DensityContext); [E] drawers on MARKET/DEBATE/JOURNAL |
| **Setup-specific management templates** (persistent/absolute/velocity/magnitude/hybrid/EP/D2/IPO/reversal each own entry-hold-trail-sell) | ⬜ | the single largest unbuilt capability. WAVE_M flagged it as the "position-lifecycle module", approval-gated. 17 grep hits are lens/doctrine *text*, not a template engine |
| **Durable job/event layer + SSE live streaming** (no refresh) | ⬜ | no `text/event-stream`/`StreamingResponse` in `api/`; pipeline status is *poll*. This is exactly the `FYERS_LIVE_LOOP_PLAN.md` proposal — designed, not built, gated on user go |
| Persistent/absolute momentum distinction; velocity/magnitude/hybrid | 🟡 | persistent_momentum archetype exists; the velocity/magnitude/hybrid *trade-type taxonomy* and their differing management do not |
| Results-season / event-window context for EP | 🟡 | EP + D2 detectors + morning-setups exist; a results-calendar context layer does not |
| Cost-aware model routing (cheap extract / mid analyze / strong chair / vision on finalists) | 🟡 | accuracy-weighted chair + modern seats live; the explicit cheap→mid→strong *routing policy* + shadow-eval harness is partially there |

## Corpus-audit reality (the plan's phase-1 premise)

The plan gates everything on "complete the corpus audit; zero unexplained gaps." Checked
`TRADETM_INDEX.md`:

- **~66 files FULL/DIGESTED**, 27 DUP, **~38 GAP + 8 PARTIAL + 14 SAMPLED** remaining.
- So the audit is *neither done nor redundant*: there is a real long tail of ~60 gap/partial/
  sampled items. The plan's "10 partials, 33 gaps" is roughly accurate, **not** invented.
- BUT: `WAVE_M_CONFORMANCE.md` already maps doctrine→code per stage, and the knowledge layer is
  substantially digested (`TRADETM_NUANCES{,_SHARDS,_HINDI,_COMPLETION}`, `ARORA_SHARDS`,
  `STOCKGEEKS`, `INDIA_PLAYBOOK`, `PLAYBOOK_TO_TOOL_MAP`, `PRACTITIONER_SCREENERS`). Restarting a
  from-scratch ledger would re-do most of this.

## Genuine gaps the plan is right to target

1. **Per-trade-type management templates** — the biggest missing capability; the tool has no
   position-lifecycle differentiation (persistent vs absolute, pyramiding, template-vs-thesis
   management). Approval-gated in WAVE_M.
2. **Seats staged by hierarchy** — TradeTM context seat → Arora setup seat → SG specialist seat
   → devil's-advocate → deterministic risk. Contained prompt/agent change; do this early.
3. **Full 5-label evidence-status system** on every setup/edge (only 2 of 5 labels exist).
4. **Durable job/event + SSE** — the live-feel wave (`FYERS_LIVE_LOOP_PLAN.md`), gated on user.
5. **Close the ~60 corpus gap/partial/sampled items** — real, but should run in parallel, not
   as a blocking gate.

## Where the plan is wrong as an execution plan

1. **Front-loaded waterfall.** Phases 1-4 (audit → ledger → reconcile → audit-current) are all
   analysis before any building; acceptance test "zero SAMPLED status remains" makes re-reading
   14 sampled files a prerequisite to the rebuild. For a solo user frustrated by slow *visible*
   progress, this sequencing is backwards.
2. **No current-state acknowledgement.** Reads greenfield; ~half of "Trading-System Changes" and
   "Product/Live UX" already exists. Executed literally → duplicated work.
3. **Buries the big lift.** Per-trade-type management templates get one bullet; it's the largest
   real build in the document.

## Recommended reframe (keep the constitution, invert the order)

- **Keep as north star:** the teacher hierarchy, "record contradictions don't average", JUDGMENT-
  not-numbers, the 5-label evidence ladder, replay-before-locked-risk-change.
- **Do a *delta* audit, not a from-scratch ledger** — start from `WAVE_M_CONFORMANCE.md` + the
  digested knowledge; only the ~60 gap items need new extraction, running in parallel on cheap
  models (per the plan's own routing).
- **Ship the contained doctrinal upgrade now:** stage the debate seats TradeTM-first.
- **Sequence the real gaps by felt value:** (1) per-trade-type management templates [approval-
  gated — needs user sign-off on the sizing/hold rules], (2) full evidence-status labels, (3)
  SSE/live-feel [user go], (4) corpus gap-completion in parallel throughout.
- **Don't pause current shipping** for the audit — the movers-surfacing fix, Strong-Start list,
  and V4 polish are exactly the felt improvements the user has been asking for.

## What I could NOT verify (flagged honestly)

- **The "118-file external corpus."** `study/` holds 170 tracked files (a large raw corpus, so
  the reference isn't fabricated), but whether "118 unique external" is a real prior count or an
  estimate I can't confirm — verify before committing to "read all 118."
- Whether the 17 persistent/velocity/magnitude grep hits include any real management logic vs
  pure doctrine text — I read them as text-only, but a deeper read could reclassify one or two.
- This is a review of a document against repo state; if a second corpus or a prior audit exists
  that I haven't seen, the audit-phase judgment could shift.
