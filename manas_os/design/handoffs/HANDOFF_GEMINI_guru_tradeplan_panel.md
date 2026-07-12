# HANDOFF 9 — Guru checklist panel on TRADE PLAN + DEBATE (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Finishes the flagged follow-up from HANDOFF_GEMINI_guru_checklists_COMPLETED.md (API + seed done).

## Context
`scanner/mentor_checklists.py` + `mentor_checklists.yaml` (Arora entry discipline, source-cited)
are live with an evaluate endpoint (`/api/checklists/.../evaluate` or the `_mentor_checklist_by_id`
route in app.py — verify the exact path). AUTO items map to real payload fields; MANUAL items are
user-tickable. No UI surfaces it yet.

## Scope
1. **TRADE PLAN panel** (primary): a compact v5 checklist panel on `desk/src/TradePlanTab.jsx` —
   each row: check state + item text + source-cite chip; AUTO rows show the actual evaluated value
   ("stop 4.1% <= 5% cap ✓"); MANUAL rows are user-tickable (persist per symbol+date via the
   existing endpoint). Overall read: "N of M — and which HARD items fail". A failing HARD item is
   amber ADVISORY text only — it does NOT block or alter the deterministic plan/CTA (surface it
   near, but visually subordinate to, the execution ticket).
2. **DEBATE deep-dive** (secondary): the same checklist as a collapsible disclosure on the debated
   symbol's deep-dive.
3. Config affordance: let the user toggle checklist items on/off / pick which mentor checklist is
   active (CRUD endpoints exist — wire the UI; no free-text item creation, keeps source-fidelity).
4. Tests: panel renders AUTO evaluated values + MANUAL tick persistence + a HARD-fail renders
   advisory-only (never disables the ticket) — vitest pure helpers where possible.

## Guardrails
Checklist state NEVER feeds gates/sizing/verdicts/plan (advisory only — verified in the backend,
keep it so in UI). No US-guru content; every item keeps its source cite. `.v5` tokens only, a11y AA.

## Output
`HANDOFF_GEMINI_guru_tradeplan_panel_COMPLETED.md`: the panel composition, AUTO-value examples on
real data, the advisory-not-blocking proof, test results (REAL output).
