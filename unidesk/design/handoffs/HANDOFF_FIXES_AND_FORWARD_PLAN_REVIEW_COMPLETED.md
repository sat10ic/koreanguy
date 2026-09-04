# HANDOFF — deep review of F1/F3/F4 fixes + BananaPatterns/IPO-EP/AVWAP forward plan

Date: 2026-08-30. Read-only Opus review, requested by owner explicitly to
(a) verify the four just-landed fixes beyond spot-checking, (b) review the
BananaPatterns/IPO-EP/AVWAP forward plan for soundness. No code changed.
Orchestrator independently re-verified the two most consequential claims
against source before recording them here (see "Orchestrator verification"
under each).

Attribution-ID: attr-unidesk-fixes-and-forward-plan-review-claude-opus-20260830-001

## Part 1 — fix verdicts

**F3 (stop-aware R-multiples, `03778ecd`) — correct but incomplete.**
`attained_1r/2r/3r` correctly derive from the new `r_multiple`, and both
production paths (`candidates.attach_outcomes`, `walkforward.simulate_long`)
route through the same `long_outcome` primitive, so they agree on sign and
`stop_hit`. **But `r_multiple = -1.0 if stop_hit else potential_r_multiple`
assumes a fill exactly at the stop.** On a gap-through (entry 100, stop 95,
next bar opens at 80), the true loss is roughly −4R; the label still reads
−1.0. **Orchestrator-verified**: `long_outcome` (`labels.py:86-101`) takes
only `entry, stop, highs, lows, horizon` — it never receives or uses the
stop-triggering bar's open. `opens` is loaded in `candidates.py:211` for the
entry fill only; nothing equivalent exists for exit. This systematically
**understates loss magnitude on exactly the gappy/illiquid names most
likely to produce a spurious apparent edge** — the single most consequential
finding in this review, because the archive regeneration running
concurrently is building the whole event store on this exact code.

Two smaller issues: `walkforward.simulate_long` has no `PARTIAL` framing for
a short future window the way `candidates.attach_outcomes` does (same
short-horizon trade reported as complete in one path, partial in the
other); the archive stores `gross_bps` only, no net-of-cost figure, despite
every promotion gate in the plan being phrased "net-of-cost."

**F4 (`base_breakout`, `cb67bc91`) — pivot fix is correct; `blue_sky` has a
real, currently-latent gameable path.** `close_cleared_pivot` correctly
uses the 20-bar-prior base high excluding today's bar
(`inputs.py:100-103`). **`blue_sky` is not what its name claims** —
`inputs.py:111-112` sets `prior_listing_high = max(h[:-1])`, the whole
loaded window's high, not a true listing high. **Orchestrator-verified**:
when `n <= base_window + 1` (≤21 bars), `h[-base_window-1:-1]` and `h[:-1]`
are the identical slice, so `pre_breakout_pivot == prior_listing_high`
exactly, and `close_cleared_pivot=True` mechanically forces
`blue_sky=True` — the room-check bypass fires automatically for any
short-history symbol. `MIN_SESSIONS_DEFAULT = 61` (`scan.py:31`) keeps this
out of the default nightly scan today, but it is a property of
`compute_setup_inputs` itself, not of the scan's floor, and will bite any
caller (a shorter-window backtest, a different min-sessions config) that
doesn't happen to inherit that floor. Also: `trust.py` still marks
`base_breakout` `BLOCKED`/`rankable=False` with a reason string describing
the pre-fix defect — fail-closed and safe, but stale and needs re-audit
before this fix has any actual ranking effect.

**F1 (CA quarantine before RS, `334ab9a6`) — correct and complete on the
leak it targets; two latent scoping issues, both fail-closed.** Detector
isolation is genuinely closed: a quarantined symbol is excluded from the
RS percentile denominator (`scan.py:123`) and again before any `SymbolScan`
is built (`scan.py:152`) — no path lets a quarantined symbol fire a
detector on a stale rank. Un-quarantine correctly matches
`(symbol, ex_date)` against confirmed actions. Two things to track: (a)
`scan.py:113`'s `as_of.date()` is a UTC date compared against IST exchange
sessions — for runs before 05:30 IST this can fail *open* (fails toward
under-quarantining, not over), currently masked by an independent
`available_at` gate so it's latent rather than live; (b) `gold.py:74` calls
`scan_universe` with no `actions`, so every detected split candidate
quarantines its symbol including already-confirmed ones during gold-fixture
generation — fail-closed but silently changes which symbols reach the
calibration set.

**Gap-2 (archive-wide adjustment-basis trap) — needs re-measurement, not
re-citation.** The guard logic itself is sound
(`candidates.py:199-209`, tested), but the empirical "0 mismatch cases
across 904,221 events" figure describes the now-superseded, pre-label-fix
archive. Must be re-measured against the regenerated archive before being
quoted again.

## Part 2 — BananaPatterns / IPO-EP / AVWAP forward plan

1. **Clean-room/non-promotion boundary is sound by convention, not
   enforced in the emitted JSON.** `base_episodes` entries carry no
   `rankable`/`trust` key at all (unlike `candidates` rows, which do) —
   `report_json.py`'s `_episode_dict` (lines 48-75) omits it entirely. A
   consumer joining episodes to candidates, or sorting by `verdict`, has
   nothing in the payload stopping it. Worse precedent already exists:
   `rankable=False` is already advisory-only for the six `BLOCKED`/
   `REVIEW_REQUIRED` legacy detectors — their candidates ship in the array
   regardless. Cheap fix: hard-code `{"rankable": false, "research_only":
   true}` on every episode and add a test that fails if any `base_episodes[].symbol`
   reaches a ranked path without an explicit allowlist.

2. **IPO/EP anchor timezone handling is clean; there is a real same-day
   dissemination defect.** The UTC comparison logic itself is correct for
   both boundary cases named in the review brief (15:35 IST → next session;
   09:00 IST → same session). **The actual defect**: the anchor rule is
   "first session that *completes* after the news," not "first session that
   *starts* after the news" — for a result disseminated intra-session (e.g.
   12:00 IST, routine given India's 30-minute post-board-approval filing
   window), the anchor becomes that same session, and its AVWAP includes
   the pre-news 09:15–12:00 volume. **This is a spec defect
   (`bananapatterns_recovery_plan.md` Slice 6a's own wording) propagated
   faithfully into code, not an implementation slip** — the contract needs
   a session-open instant, which is structurally absent from
   `completed_at_by_session`. Also unvalidated: `anchor_for_ipo_listing`
   never checks `available_at` against `listing_date`, out of character for
   a codebase that fails closed everywhere else. And `anchored_vwap` is a
   daily HLC/3-weighted approximation, not true intraday VWAP — the
   `volume_basis` field that's supposed to disclose this is a free-form,
   unvalidated string.

3. **Slice 5 (external comparison harness) methodology is procedurally
   sound but validates the wrong thing.** Held-out discipline, ISIN-first
   crosswalk, separate precision/recall/coverage reporting, archived source
   hashes — all genuinely good practice. But agreement with one vendor's
   public output is a **reimplementation-fidelity test, not an edge test**;
   it rewards matching BananaPatterns' own idiosyncrasies and cannot
   distinguish "we disagree because we're wrong" from "we disagree because
   they're wrong." Current calibration base is n=1 (one symbol, one date,
   per the cleanroom completion report) — Slice 5 raises that to n=universe
   but along the same single axis. **Cheaper, better validation is
   available and missing from the plan**: once the archive regenerates
   under stop-aware labels, join `BaseEpisode.verdict` against
   `r_multiple`/`stop_hit`/`breakout_hold` on the shared `(symbol, session)`
   key — no vendor fetch, no crosswalk, survives the vendor's page
   changing. Recommendation: keep Slice 5 but demote it to a
   fidelity/provenance check; add outcome-based validation as primary
   acceptance evidence, gated behind the regeneration.

4. **Slice 6a's promotion gate is under-specified enough to be satisfied
   by a p-hacked result.** It names the right dimensions (per setup family,
   per regime, event-time embargo, held-out period, net-of-cost vs
   baseline) but attaches no decision rule to any of them. Missing,
   concretely: an effect-size floor and significance test with
   multiple-comparison correction (8 detector families × several regimes =
   20-30 implicit comparisons, uncorrected); which metric wins ties
   (r_multiple vs net_bps vs hit rate vs expectancy will not agree); the
   baseline's precise definition (EMA21-anchored, already used by
   `pullback`, vs no anchor at all); a pre-registration requirement so
   family/regime cuts are declared before looking; a rule that the held-out
   period is read exactly once; the embargo length as a number (likely
   `walkforward.DEFAULT_EMBARGO = 5`, but the gate doesn't say so); a
   minimum-n floor per family×regime cell (NSE IPO/EP cadence will produce
   single-digit-n cells); and pinning the gate to a `COSTS_VERSION` so a
   later cost-assumption change doesn't silently invalidate a passed gate.

5. **Sequencing: partly out of order, and the split runs through Slice 3.**
   Slices 1, 2, 6, and the event contracts (`IPOListingFact`,
   `EarningsResultEvent`) are correctly sequenced — they unblock an existing
   foundational gap (`ipo_base` is `BLOCKED`/`"listing_age_is_not_verified"`
   precisely because listing age is currently inferred from bar count, not
   an authoritative source), not add a new one. **Slice 3 (terminal/Screens
   integration) should wait**: it surfaces `BaseEpisode` in a UI exactly
   where the unenforced boundary from point 1 becomes a shipped affordance,
   over a universe F5 still leaves ungated and against a regime/quality
   context F2 still leaves unwired — building it now means rebuilding it
   after F5 lands. **Slice 5 as scoped should wait** per point 3 (external
   dependency bought before the internal validation it should be measured
   against exists). **Everything downstream of Slice 4** (the archive
   regeneration) is correctly gated on it already in the plan's own
   dependency graph — that ordering just isn't enforced anywhere in code or
   process, and Slice 3 in particular is not gated on F5 at all despite
   consuming F5's output.

## The one thing needing owner attention first

**The `-1.0` gap-through understatement in `labels.py:101`.** The archive
regeneration is running on this exact code right now. Every downstream
consumer (N5's three conditions, Slice 4 itself, Slice 5's proposed
outcome-based alternative, Slice 6a's promotion gate) inherits whatever
bias ships in this pass. The fix is small and the data already exists
(`candidates.py:211` loads `opens` for entry only) — use the open of the
stop-triggering bar as a floor when it gaps below the stop, rather than a
constant −1.0.

**Orchestrator's call on sequencing**: not blocking the in-flight
regeneration for this — even an imperfect fixed −1.0 is a large
correctness improvement over the pre-fix state where 58%+ of stopped-out
trades were recorded as wins. Recorded here as the top-priority follow-up
slice, queued immediately after the current regeneration completes and is
verified, not before.
