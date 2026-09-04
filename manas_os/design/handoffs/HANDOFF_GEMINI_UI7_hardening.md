# HANDOFF — UI-7 hardening / close-out (Gemini)

Date 2026-07-11 · Repo `C:\Users\satta\Downloads\koreanguy` · Branch `emergent` · API :8000, desk :5174
You have repo access (Antigravity). Do NOT git commit — the maintainer reviews and commits.
Never print the rupee glyph to a Windows console (cp1252) — use "Rs".

## Context
All 7 desk screens are now on the v5 LIGHT design system (tokens `desk/src/styles/tokens.v5.css`,
primitives `desk/src/components/v5/`, pattern reference `DebateTab.jsx`/`MarketHomeTab.jsx`).
The old 84KB `desk/src/App.css` still serves the SHELL (old header/nav under the v5 CommandStrip),
ChartDrawer, glossary, toasts, and stragglers. Controlling plan: `manas_os/design/UI_OVERHAUL_HANDOFF.md`
§6 "UI-7" + §7 QC loop.

## Scope (in order; verify app boots + `npm run build` + `npx vitest run` after EACH step)
1. **Primitive generalization** (single-writer debt):
   a. `components/v5/VerdictChip.jsx` → accept arbitrary tone+label (keep TAKE/SKIP defaults +
      every existing call-site working); migrate PositionsTab's local `PositionsVerdictPill` to it.
   b. `components/v5/Sparkline.jsx` → optional band/reference-line props; migrate PositionsTab's
      local `RPathSparkline` only if it fits cleanly (else leave + document why).
   c. LedgerTab's `v5-jr-status-*` evidence chip → shared `EvidenceStatusChip` primitive if a second
      screen would use it; else document as intentionally local.
2. **Dead code**: delete LedgerTab.jsx's dead DEMO fixtures (`USE_DEMO_DATA` is false — remove the
   flag + fixtures + demo path entirely, keep the live fetch). Sweep desk/src for provably
   unreferenced v4 leftovers (grep every class/import before deleting).
3. **Old-CSS retirement** (no two live shells): inventory which App.css selectors are still
   REFERENCED by live JSX; delete only zero-reference selector blocks (grep-verify each).
   Do NOT delete shell styles still in use — list what remains + why. Report App.css size before/after.
4. **A11y + states pass** (all v5 surfaces): keyboard + `:focus-visible` everywhere interactive;
   AA contrast (watch panel-2 + ink-mute edge); `prefers-reduced-motion` covers every animation
   (tape, ribbons, pulses); no full-surface "Loading…" that erases confirmed data — fix stragglers;
   grep `window.prompt|alert|confirm` across src/ and replace any remainder with inline validated UI.
5. **Beginner walk** (verify, don't build): drive MARKET → SCANNERS → SHORTLIST → DEBATE →
   TRADE PLAN → POSITIONS → JOURNAL on real 2026-07-10 data. At each screen: can a beginner answer
   its ONE question; is the primary action obvious; do all numbers render real values. Ledger every
   defect found (fix only in-scope ones).

## Guardrails
No backend edits. No token VALUE changes. Keep all routes/actions working. One-writer-for-risk
untouched. Real data only. `.v5`-scoped CSS only. If blocked, flag — don't improvise architecture.

## Acceptance
`npm run build` clean; `npx vitest run` green; all 7 tabs DOM-verified on real data; App.css
delta reported; zero native prompts; reduced-motion + focus-visible verified.

## Output
Write `manas_os/design/handoffs/HANDOFF_GEMINI_UI7_hardening_COMPLETED.md`: files changed/deleted,
App.css before/after size, primitive-migration notes, the beginner-walk findings ledger, anything
deferred + why, and assumptions. Flag uncertainty rather than inventing.
