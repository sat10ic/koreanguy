# WAVE_M_CONFORMANCE — TradeTM-Conformance Audit (Opus, 2026-07-10)

Posture (user, binding): steelman TradeTM — Indian-market experts; where the tool
contradicts them, DEFAULT = the tool changes, unless our own replay data is hard evidence
against. "OUR WAY TODAY" read from code, not docs.

STRUCTURAL FACT coloring everything: doctrine is ~90% ENCODED (lenses, coach bank, playbook,
discovery metrics) but only ~30% ENFORCED. Production selection = candidates -> gates ->
risk_plan; the WAVE-K discovery layer is COUNTERFACTUAL-ONLY (discovery_bucket never feeds
scan_candidates); the debate is an overlay that cannot admit what the cascade refused.

## Stage gaps (THEIR WAY vs code today)
1. SCAN — STRUCTURAL. Their anchor: >=30-35% off the 65d LOW + velocity-first (purple dots/
   ADR; zero dots = skip) + persistent-momentum scan (20/30/50/150 over 10/20/50/200 EMA,
   ADR sort) + visual RS (no floor). Ours: 52w-high anchor in detector_shortlist AND
   re-imposed in gate_trend_template (nearness>=0.85) + RS_FLOOR=80 hard; ADR display-only;
   all the right metrics exist but only counterfactually. Evidence: pool recall 25%,
   survivor recall 0/12. OVERHAUL (L, evidence-gated): promote discovery.build_bucket to
   the live pool feeder; kill RS floor + nearness refuse -> scored objections.
2. ENTRY — STRUCTURAL (execution), PARTIAL (detection). Their edge is intraday (EP 5-min
   ORB entry + day-low stop + >12% gap+ORB skip; strong-start 2-3-min wait; D2 3 branches
   incl Day-2-open classification; day-0 risk-free test W23; IPO bar-by-bar). Ours: EOD
   only; strong-start/D2 exist ONLY as lens text; entry = prior-20-high pivot. OVERHAUL:
   (M) EOD detectors for strong-start-ready + D2 branches; (L, behind Fyers #21) the
   execution half; own "surface tonight -> execute 9:07-9:30" handoff (matches their own
   working-professional design).
3. HOLD — STRUCTURAL. Velocity/Magnitude/Hybrid templates keyed to setup type (F13/F16),
   persistent-vs-absolute OPPOSITE execution, pyramid 1%+<=4x1% to ~30% profit-gated,
   hybrid 20-25% ride floor (W17), core/tactical split + rebuy-inheriting-stop (W18/19).
   Ours: single-shot sizing; NO position lifecycle at all. OVERHAUL (L, PROPOSAL/approval):
   position-lifecycle module (tag, template map + mismatch flag, ladder, floor).
4. SELL — PARTIAL->STRUCTURAL. Their asymmetry: SL mechanical/hard-in-system; profit-taking
   discretionary — never symmetric (J9/E6/D11); day-low break its own trigger; fight-back/
   tennis-ball structure reads; per-trade MAE/MFE stop calibration; objective-conditioned
   trails. Ours: exit_state classifier + coach lines; managed-exit model is MEASUREMENT not
   live management; single R:R path, no rule-table split. OVERHAUL (M; split = PROPOSAL):
   stop_loss_rules vs profit_taking_rules tables, day-low trigger, structure-decay score,
   MAE/MFE recorder + calibration report.
5. MARKET READING — PARTIAL. Four-phase is a display CAPTION over market_mode, not a real
   breadth-exhaustion classifier (their read: rate-of-change of %-above-MA + NH/NL trend);
   regime still HARD family-kills candidacy (soft only for the debate pool); no choppy
   brake (3-4 stops/week -> break; 10-trade / 4-5% weekly-DD brakes W3/W4). OVERHAUL (M):
   real classifier; family-kill -> scored objection in the CASCADE (recall-verified);
   choppy/DD brakes.
6. RISK — PARTIAL. Conflicts already formalized in WAVE_L (0.65%/trade vs 0.75-1.0; 3-4
   concurrent vs 5/6; 4-5% ceiling): AWAITING USER SIGN-OFF. Stop caps absolute % not
   k*ADR (a documented GROWW kill). Missing: slippage buffer 0.3-0.6%, hard-stop-in-system
   enforcement, gap-down protocol (wait ~10min, trail first-bounce low), far-trail-as-alert.
   OVERHAUL (M, PROPOSAL): k*ADR alongside absolute cap; WAVE_L C1-C3; buffers/brakes.
7. SIZING — PARTIAL. Base-capital sizing correct. Missing: provisional-risk EP staging
   (size at 4% stop, resize on confirmed ~2% — W11), explicit 40% single-name cap
   (unverified — WAVE_L C6), small-account mode (25-30%/favorable-swing target W1/W5).
   OVERHAUL (M, PROPOSAL).

## Verdict
Tool embodies ~30% of their workflow in EXECUTABLE form (knowledge layer ~90%). Top-5
overhaul by leverage: (1) wire sensitive bucket into live pool [0%->60% survivor-recall
fix, evidence-gated]; (2) persistent/absolute template engine + pyramiding lifecycle
[largest missing capability, approval-gated]; (3) intraday confirmation layer (Fyers #21)
[the one replay-VALIDATED lever]; (4) hard gates -> scored objections + k*ADR stop +
own-history measured move [the GROWW/RAIN kill class]; (5) real four-phase classifier +
choppy brake.

## Intraday question (head-on)
REQUIRE intraday: EP 5-min ORB entry/stop + >12% gap+ORB skip; strong-start 2-3-min wait +
first-3-min RVOL; day-0 risk-free test / micro-manage-until-risk-free; D2 Day-2-open branch
+ 1-min->5-min DEMA trail; gap-down 10-min protocol; intraday depth check; IPO bar-by-bar.
HONEST EOD PROXIES: gap% + day RVOL (exist); the EP SETUP itself (results post-close ->
surface tonight, human executes 9:07-9:30 — their own design F11); all discovery metrics;
day-low-break ~ close-below-prior-low; and the buy-stop confirmation lever — our E-B/H3
replays already validated the EOD version (hit_1r 7.5%->38.3% at n=11,462; phantoms medR
-1.82 = worst population found). Tool owns discovery+planning EOD; execution cedes to #21.

## What should NOT change (replay evidence)
1. Don't blanket-widen stops: E-A x2.0 halves stopouts but median R -1.08->-1.03 at 2x
   capital risk — k*ADR must sit ALONGSIDE the absolute guard, paired w/ early entry.
2. Don't tighten leg-freshness: J7 H2 keeps WORSE names than it removes (kept -1.54 vs
   removed -1.11) — shadow posture stays off.
3. Don't silently overwrite LOCKED risk numbers — WAVE_L proposals need explicit sign-off.
4. Don't default the all-or-nothing magnitude hold — unvalidated on our tape (zero RISK_ON
   sessions in window); build the capability, gate the default.
Replay AFFIRMS their confirmation discipline (buy-stop lever) and their own thesis: "the
detectors, not the exits, are wrong" == their "90% of failures are entry failures" (F17).

## Tasks (Sonnet-sized)
M1 [evidence] re-run recall vs current build_bucket; gate M2 on >=90% pool / >=60% survivor.
M2 [L] replace detector_shortlist w/ build_bucket as pool feeder; RS_FLOOR + nearness ->
   scored objections; verify recall + pool sanity.
M3 [M] ALLOWED_FAMILIES hard-drop -> scored regime objection in run_cascade (NO_TRADE stays
   hard); no recall regression.
M4 [M PROPOSAL] k*ADR20 alongside absolute stop cap; EXCEPTIONAL measured move = own-history
   ADR-burst. Proposal diff + LEARNINGS, not applied.
M5 [config PROPOSAL] WAVE_L C1-C3 as selectable profile edits; await sign-off.
M6 [L PROPOSAL] position-lifecycle module (persistent/absolute tag, template map + mismatch
   flag, pyramid ladder, core/tactical + 20-25% floor).
M7 [M] EOD strong-start-ready + D2 three-branch detectors from existing metrics.
M8 [M PROPOSAL] exit rule-table split + day-low trigger + structure-decay score + MAE/MFE
   recorder/calibration.
M9 [M] real four-phase classifier + choppy brake (3-4 stops/wk, weekly-DD kill-switch) +
   results-calendar EP window.
M10 [L behind #21] intraday layer: ORB entry, 2-3-min confirm, day-0 risk-free, gap-down
   protocol, depth check; until then the 9:07-9:30 handoff checklist (signal guide).
M11 [M PROPOSAL] staged provisional-risk EP sizing (W11); explicit 40% single-name cap
   verification+enforcement; small-account mode.

Files of record: scanner/{candidates,gates,discovery,discovery_metrics}.py, risk/plan.py,
design/knowledge/{INDIA_PLAYBOOK,PLAYBOOK_TO_TOOL_MAP}.md, WAVE_L_RISK_PROPOSAL.md,
LEARNINGS.md (Round-4 ~L461-565, J7 ~L802-866, K2/K3 ~L878-945), design/agents/LENS_*.md.
