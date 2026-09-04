# HANDOFF 10 — Guided system + legibility (THE centerpiece) (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Closes the #1 finding in `manas_os/design/UX_AUDIT_FULL.md`: the desk has component honesty but
ZERO system legibility. A beginner cannot tell what the tool does end-to-end, what each section is
for, how to read a card, or what to do next. Make the whole tool legible AS A SYSTEM.

## Load-bearing fact (verified)
`GET /api/flow/today` is FULLY BUILT (app.py:2963) and returns a 6-step guided daily flow
(data → regime → positions → setups → plan → done) with per-step `status` (done/action/locked),
`detail`, `count`, and `actions[]` (e.g. "1 position flagged EXIT TODAY: HUDCO", "4 setups need
TAKEN/SKIPPED"). It has **zero references in `manas_os/desk/src/`** — built, never rendered. Render it.

## Scope
1. **Persistent Guided Flow rail** (beginner mode default): render `/api/flow/today` as a top/side
   stepper always visible — each step shows label, status, plain-English detail, and its ONE primary
   action button that deep-links to the relevant tab/symbol (e.g. "Manage HUDCO exit →" jumps to
   POSITIONS/HUDCO; "Review 4 setups →" to DEBATE). Locked steps show the plain blocker reason.
   `current_step` is highlighted. Expert mode collapses it to a one-line status strip. Poll/refresh
   with the existing data cadence. This is the spine that turns cards into a process.
2. **Per-tab purpose header** — a standard compact header on EVERY tab: WHAT THIS IS (one line) ·
   HOW TO READ IT (one line: what the key card/number means + how to infer) · NEXT → (the action
   that advances the workflow). Source the copy from the design corpus intent (don't invent trading
   advice; describe the tool). Beginner mode shows it expanded; expert collapses it.
3. **Alpha / Debate / Shortlist relationship legend** — a short in-UI explainer (on ALPHA + a
   shared "how these relate" affordance): Alpha Lab = SHADOW cross-sectional ranking over the WHOLE
   universe (research/leaders, NOT tradable calls); Debate = the council's verdict on GATE-PASSED
   candidates (tonight's decisions); Shortlist = what YOU chose to watch. Add cross-badges where a
   symbol appears in more than one (e.g. "also debated", "on your shortlist"). Different stocks is
   correct — SAY why.
4. **Experimental/warming/empty organs must explain themselves** — every element that renders
   nothing because it's gated/experimental/data-starved (HMM regime state, any n<threshold cohort,
   warming models) must show a plain status chip + one line WHY (e.g. "HMM regime — warming, needs
   more history" / "shadow model — not yet validated, no live influence"), never a blank or a raw
   dump. Add a small `status` vocabulary: LIVE / SHADOW / WARMING / EXPERIMENTAL / NEEDS-DATA.
5. **ALPHA tab legibility** — replace the raw `{"models":[],"experiments":[]}` JSON dump with a real
   v5 panel: what the alpha engine is, the shadow-ranking leaders (real data), and each research
   component's status chip (which quant-adoption pieces are LIVE/SHADOW/NOT-BUILT) so the user can
   tell what any of it does.

## Guardrails
Describe the TOOL, never give financial advice. One-writer/money-math untouched. Real data + honest
states only. `.v5` tokens, plain SVG, a11y AA, reduced-motion. Beginner mode changes the SPINE
(guided flow + expanded headers), not just labels — that's the whole point.

## Output
`HANDOFF_GEMINI_guided_system_COMPLETED.md`: the flow-rail composition, the per-tab header copy
(all 7), the relationship legend, the status-chip vocabulary + where applied, REAL DOM proof the
flow rail renders the 6 live steps, test results. This is the flagship — get it right; flag design
uncertainty for the maintainer rather than inventing.
