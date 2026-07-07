# NORTH STAR — what "done" means (user escalation, 2026-07-07)

The user's bar is NOT the task checklist. It is this product identity, restated by the user
across multiple sessions (this is the third statement — it must never need a fourth):

> An **edge-making intelligence engine** for NSE swing trading: proves its setups have edge,
> shows the proof on every card, learns from outcomes (self-learning loop later), coaches
> positions with real depth, and looks like a paid research desk product (AESTHETIC_BAR.md)
> — not "vague regime analytics + black-box setups + a basic coach".

Progress claims are made against THIS bar. Checklist-% is meaningless to the user.

## Honest scorecard vs the user's asks (2026-07-07)

| User ask | State | Honest % |
|---|---|---|
| Edge PROOF ("will these setups work?") | Replay exists but last result showed REFUSED beating PASSED — edge unproven; nothing on the cards says "this setup family: +0.4R avg over N trades" | 20% |
| Feedback-folder research (8 docs) visible in product | Distilled into gates/thresholds (invisible plumbing); the distinctive ideas (near-miss verdicts, override ledger, adaptive percentile thresholds, LLM devil's advocate) NOT built | 30% |
| Self-learning loop foundation | Journal + expectancy plumbing exists but empty; no calibration loop, no outcome-feedback into ranks | 15% |
| Non-black-box setups | Gate dots + refusal funnel exist, but no per-family historical stats on cards, no near-miss context | 40% |
| Position coach with depth | trail_plan/two_strike/verdict/guard/banner shipped — mechanically real but thin UX, no chart-anchored visuals | 45% |
| Aesthetic (AESTHETIC_BAR.md exemplar) | BATCH 7 in flight; before it: ~10% | in flight |
| Deterministic machinery (gates, plans, regime, journal plumbing) | Genuinely built + tested (174 green) | 85% |

Weighted against the user's bar: **~35-40% done**, not 75-80. The 75-80 figure measured the
plumbing checklist. Plumbing is necessary but is not the product.

## Re-sequenced queue (edge-first, in order — supersedes "pick next unclaimed slot")

1. **E1 — Edge verdict, full history** (main thread, RUNNING 2026-07-07): 2y replay on the
   backtest DB copy. Output: passed vs refused cohort forward returns. If refused ≥ passed,
   the gate thresholds get recalibrated (percentile-fit per VIZ_BRAINSTORM A1) BEFORE any
   more features. An edge engine without edge is a UI.
2. **E2 — Put the proof on the cards**: every setup card shows its family's replay stats
   ("IPO BASE: n=34, avg +0.62R at T+10, win 58%" — or an honest "UNPROVEN: n=6"). Kills
   black-box feeling with one feature. (Backend: replay stats table + endpoint; frontend:
   chip on card.)
3. **E3 — Near-miss verdict chart** (VIZ_BRAINSTORM #1): refused-names forward performance
   vs passed — the "what did the gate cost us" view, visible in the UI, updated by replay.
4. **E4 — Override ledger** (A5): user can override a refusal WITH a reason; tool tracks
   override outcomes vs gate outcomes. First real learning loop — data starts accruing.
5. **E5 — Adaptive thresholds** (A1): quarterly percentile-fit of gate thresholds from
   replay, proposed as a diff the user accepts/rejects (determinism in decision preserved).
6. **E6 — LLM devil's advocate** (L2): per-card LLM critique with acceptance ledger; never
   gates, never sizes.
7. BATCH 7 aesthetics (in flight) + coach UX depth ride alongside as frontend waves.

Rules unchanged: LLM proposes, never decides. One writer per metric. No dormant code.

## Spec-compliance audit (2026-07-07, verified against code — not skimmed)

WIREFRAMES.md: Regime/Setups/Watchlist/Journal/ChartDrawer skeletons built. NOT built:
FOCUS tab+screen (§3, missing entirely); Health tab still present (wireframe wanted it
replaced by a staleness chip); Journal four-cohort strip (taken/pushed-skipped/armed-skipped/
refused) + MFE/MAE scatter (the pushed-skipped cohort IS the "do I skip winners" edge read).

BEGINNER_EXPERT_SPEC.md: only the Regime flagship (§3.1) is density-aware. NOT built:
signalCopy.js (§4); density-gating on Setups/Watchlist/Journal/ChartDrawer (§3.2-3.6 — none
import useDensity, so beginner==expert on 4 of 5 screens); Focus Center (§3.3); onboarding
coach-marks + daily strip (§5); the §6/§8 QC gate. The toggle is still cosmetic everywhere
except Regime — the exact state the spec existed to fix.

Queue additions (fold into the edge-first order): **E7 — Focus tab/screen** (wireframe §3 +
spec §3.3, one lens over existing setups engine); **E8 — density pass on Setups/Watchlist/
Journal/Chart** (spec §3.2-3.6 + signalCopy.js + QC grep gate); **E9 — Journal four-cohort
strip + MFE/MAE** (edge-relevant: surfaces skip-quality); **E10 — onboarding + daily strip**
(spec §5); decide Health-tab removal. These are aesthetics/UX rows, sequenced AFTER the E1
replay verdict and E2 proof-on-cards unless the user reprioritizes.

## Visualization debt (user-flagged 2026-07-07, exemplar = finallynitin Market Quadrant)

- **E11 — Four-pillar finallynitin-style charts (NEXT ACTIVE, after CODEX_PATCH_BATCH lands + is
  verified).** Confirmed 2026-07-07: never built. Current Regime pillars (RegimeSummary.jsx
  ~L154-199): POSTURE = caption+tape+table (no chart); SWING = caption+table + one shared XP
  line chart; TREND = caption + sentence note ONLY (no chart/table); BIAS = caption + sentence
  note ONLY. The exemplar gives EACH pillar its own time-series histogram. Build one grounded
  chart per pillar, all from data we actually persist (no invented series):
    - **MOMENTUM** → daily `up_4pct` (green, up bars) vs `down_4pct` (red, down bars) histogram
      from `breadth_daily` — the honest breadth-thrust analog of Homma MSwing. NOTE: `up_4pct`/
      `down_4pct` are NOT yet in `/api/regime/history` or `/api/regime/breadth-history`; add them
      to `breadth_history`'s SELECT (same pattern as the P6 pct_above_10dma add). (POSTURE badge
      stays; MOMENTUM becomes its own pillar chart, matching the exemplar's 4 params
      MOMENTUM/SWING/TREND/BIAS — reconcile with the current POSTURE naming.)
    - **SWING** → `pct_above_10dma` + `pct_above_20dma` bar/line history (60 sessions). Data ready
      once P6 adds 10dma. Replace the shared XP chart placement with this pillar-specific one.
    - **TREND** → `pct_above_40dma` + `pct_above_50dma` history (already in breadth-history). This
      pillar currently has NO viz — highest-value add.
    - **BIAS** → exemplar uses %>200DMA. **We do NOT track 200-DMA breadth** (`breadth_daily` stops
      at 50dma; the caption already admits this). OPEN SUB-DECISION (user, 2026-07-07, not yet
      answered): (a) add a real 200-DMA breadth computation to the breadth pipeline (correct, more
      work — touches sources/universe_breadth.py + schema), or (b) ship BIAS as a %>50DMA history
      explicitly LABELED "50-DMA proxy — 200-DMA not tracked yet". Default to (b) for the first
      pass so BIAS gets a truthful chart now; (a) is a follow-up.
  Each pillar: chart IS the explanation; caption shrinks to a one-line READ, drop the redundant
  table echo (AESTHETIC_BAR.md). Reuse the existing EChart wrapper + tokens; no new colors.
  Serialize AFTER the patch batch — both touch RegimeSummary.jsx, do not run concurrently.
- **E12 — Refusal funnel redesign.** DONE 2026-07-07 (commit affeb739): Setups funnel rebuilt with
  token colors (muted/info/warn/bull), inside labels, no truncation. (This was the Setups-screen
  funnel; Regime has no funnel.)
- **Sectors RS vs index return labeling.** STILL OPEN. Fixed the indices panel to broad caps only
  (Realty no longer collides there); Sectors panel's "RS%" still needs a timeframe/metric label so
  it isn't mistaken for a return.

## Process rule (why this file exists)

Every progress report to the user states % against THIS scorecard, updates the table above,
and names what moved. Orchestration = each wave must move at least one row of the scorecard,
or it doesn't run.
