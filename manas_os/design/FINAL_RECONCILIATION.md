# FINAL RECONCILIATION — orchestrator pass (2026-07-12)

Branch `emergent`, 291 commits ahead of `main`. Working tree clean of uncommitted code.
Suite: **779 pass / 1 known fail** (sector-downside baseline, pre-existing, unrelated).
Desk: build clean, 37/37 vitest.

## 1. What shipped this arc (verified)
- **UI overhaul complete** — all 7 screens on the v5 light system (MARKET, SCANNERS, SHORTLIST,
  DEBATE, TRADE PLAN, POSITIONS, JOURNAL); UI-7 retired 3689 lines of App.css, unified primitives.
- **Live Work** (UI-2): durable jobs/events + SSE, streaming inspector.
- **Market Breadth V2.0** enrichment: `breadth_counts` (38 metrics, 85 sessions) + `breadth_analytics`
  (Fosback/NH-NL/volatility/BO-S-F) → MARKET panels + Tier-0 DEBATE context.
- **Alpha behaviour wave**: 5y point-in-time history (286→1238 sessions) + symbol identity;
  behaviour-first debate context (EMA/slopes/RS/ADR/base/volume + competing archetypes);
  outcome resolver; weighted analogue memory; promotion-gate + leakage-audit + experiment-KB infra.
- **Live loop** stage 1 (paper): Fyers WS engine + armed-list FSM + replay; stage 2 armed-zone schema.
- **Guru checklists** (Arora-first, corpus-cited, advisory).

## 2. Guardrail audit — ALL HOLD
- **Money-math LOCKED**: gates.py / risk/plan.py / snapshot.py / governor.py / sizer.py / candidates.py
  show ZERO diff across the whole arc. Verified per-commit.
- **One-writer-for-risk**: breadth/analytics/checklists/live all display server values; UI computes
  no stop/qty/target/risk. TRADE PLAN's old client capital-math was removed (a real fix).
- **One breadth universe / one-opinion**: MARKET, DEBATE context, and regime all read the same
  `breadth_analytics`/`regime_snapshots`; net_breadth 5.75 ⇄ r4p5 2400 traced to the same source.
- **Paper-first LOCKED**: `agents.telegram_live: false`; live send double-gated (flag AND a written
  graduation doc that does not exist). Live authors nothing.
- **Shadow-only alpha**: promotion_gates/leakage_audit not imported by any decision code; no model
  promoted; nothing influences live ranking/sizing.
- **Anti-mashup**: classify_universe + mentor_checklists wired into pipeline/API (not dormant);
  promotion-gate infra is tested and intentionally ahead of the promotions it will gate.

## 3. Vision alignment (locked hierarchy: regime → ranking → chart-reading → risk → forecasts 2nd)
Achieved in architecture: the debate now receives a causal behavioural chart description and reasons
over competing archetypes (EP/VCP/flag/IPO-base/Stage-2/pocket-pivot/reversal), with gates demoted
to tradability/risk governor and forecasts as secondary evidence. LIVE-first mode is the locked
default experience; EOD is the confirmatory evidence layer.

## 4. Honest gaps / not-done (nothing hidden)
- **Fyers intraday backfill BLOCKED** on auth — machinery ready, needs a valid token (user re-auth).
  Until run, the tool is EOD-real; intraday is paper/shadow.
- **Live-default desk UI is PARTIAL** (stage-2 backend in; live-ticking frontend incomplete) — follow-up handoff.
- **Guru TRADE PLAN panel** not built (API/seed done) — follow-up handoff.
- **No alpha model promoted** — by design: needs the 3-5y gate (now met on data) PLUS walk-forward +
  20 live shadow sessions + calibration before any ranking tilt. Promotion infra exists; promotion doesn't.
- **sector-downside test** fails vs its baseline (pre-existing ML model, not a regression).
- Untracked stray design docs (WAVE_K9/K10 specs) — harmless, unrelated to this arc.

## 5. Process note
Gemini's breadth-tier0 completion doc contained a FABRICATED "simulated" curl (values didn't match
reality; code was actually correct). Standing instruction added: external coders must paste REAL
command output. Maintainer re-verifies every completion against the live DB regardless.

## 6. Verdict
Coherent, guardrail-clean, EOD-live on real data across all 7 screens. The edge architecture
(behaviour-reading debate + memory + validated-promotion discipline) is in place but honestly
pre-promotion. Blockers are user-side (Fyers auth) or by-design (shadow accumulation). No mashup,
no silent money-math drift, no fake data in production paths.
