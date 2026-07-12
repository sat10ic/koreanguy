# HANDOFF (DESIGN) — Guided system: design the spec GLM → build Gemini

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. You (GLM) have repo access.
This is a **DESIGN** handoff: produce a concrete, buildable design SPEC (+ optional HTML mockup),
NOT production React. Gemini implements it afterward from `HANDOFF_GEMINI_guided_system.md` (#10).
Do NOT git commit. Never print the rupee glyph to console — use "Rs".

## The problem you are solving (the project's #1 unmet request)
The Manas OS desk is 7 honest v5 screens but has ZERO system legibility — a beginner cannot tell
what the tool does end-to-end, what each section is for, how to READ a card, or what to do next.
Read `manas_os/design/UX_AUDIT_FULL.md` (headline + top-10) and
`manas_os/design/ALPHA_LEARNING_CONSTRAINTS.md` §"Non-negotiable UI evidence". The connective tissue
already exists in the backend and was never designed into the UI (see next).

## Load-bearing fact
`GET /api/flow/today` (app.py:2963) already returns the full guided daily flow — curl it live for
the real shape:
`curl "http://127.0.0.1:8000/api/flow/today?date=2026-07-10"` (start the API first:
`python run_manas_api.py`). It returns 6 ordered steps (data → regime → positions → setups → plan
→ done), each with `status` (done/action/locked), plain `detail`, `count`, and `actions[]` with
target symbol + reason. Your design renders THIS.

## Design language (LOCKED — do not re-explore aesthetics)
v5 LIGHT: warm off-white `#f7f6f2` canvas, ink ramp, teal `#0d6c6c` / amber `#8a5a12` / green
`#14713f` / red `#ad2c34`, Fraunces (display) + Public Sans (UI) + IBM Plex Mono (numbers). Tokens
in `desk/src/styles/tokens.v5.css`; the shipped `DebateTab.jsx`/`MarketHomeTab.jsx` + `round4/
debate_merged_light.html` are the visual reference. Plain SVG only, no chart libs. Design for both
beginner and expert modes.

## Deliverables — a DESIGN SPEC covering:
1. **Guided Flow rail** — the persistent spine. Design its layout (top rail vs left rail — argue the
   choice), the visual treatment of the 6 steps + current-step highlight + done/action/locked states,
   each step's ONE primary action button and where it deep-links, and how a locked step shows its
   blocker. Beginner = full rail default; expert = collapsed one-line status strip. Include the exact
   copy for each step's label + how the plain `detail` from the API is presented.
2. **Per-tab purpose header** — a reusable header pattern for all 7 tabs: WHAT THIS IS (1 line) ·
   HOW TO READ IT (1 line — what the key card/number means and how to infer from it) · NEXT → (the
   action that advances the workflow). WRITE THE ACTUAL COPY for all 7 tabs (MARKET, SCANNERS,
   SHORTLIST, DEBATE, TRADE PLAN, POSITIONS, JOURNAL) — describe the TOOL, never give financial
   advice. Ground the "how to read" copy in what each screen actually shows.
3. **Alpha ↔ Debate ↔ Shortlist relationship legend** — design the in-UI explainer + cross-badges
   ("also debated", "on your shortlist"). Make crystal-clear: Alpha = SHADOW cross-sectional ranking
   over the WHOLE universe (research/leaders, not tradable calls); Debate = council verdict on
   GATE-PASSED candidates (tonight's decisions); Shortlist = user-curated watch. Design how/where this
   is surfaced so different-stocks reads as intentional, not chaos.
4. **Status vocabulary** — design the chip system LIVE / SHADOW / WARMING / EXPERIMENTAL / NEEDS-DATA
   (color, shape, tooltip copy) so every gated/experimental/empty organ (HMM regime state, thin
   cohorts) explains itself with one plain line instead of rendering blank or a raw JSON dump.
5. **End-to-end walkthrough** — one annotated narrative of a beginner's full session using the design:
   open → read the flow rail → each step → decide → done. Prove the design makes the tool a SYSTEM.

## Format
A design spec markdown at `manas_os/design/GUIDED_SYSTEM_DESIGN.md` (ASCII wireframes are fine +
exact copy). OPTIONAL but valued: a self-contained HTML mockup of the flow rail + one tab-with-header
in the v5 language (like the round-4 mockup) so the design reads at a glance. Flag any design
decision you are unsure about for the maintainer rather than guessing.

## Output note
End with: the spec file path, the 7 per-tab header copy blocks, and your single strongest design
recommendation for making the tool legible as a system. Real, grounded design — no invented trading
guidance, honest states only.
