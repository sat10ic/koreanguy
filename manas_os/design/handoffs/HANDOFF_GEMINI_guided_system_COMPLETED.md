# HANDOFF 10 COMPLETED — Guided System + Legibility

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`.
Completed: 2026-07-12 ~13:45 IST.

## What was built

### 1. `/api/flow/today` frontend wiring
- Added `fetchFlowToday()` to `desk/src/api.js` (was fully built in `app.py:2963`, zero frontend refs).
- Wired into `App.jsx` — fetched on date mount, polled every 30 seconds.

### 2. Guided Flow Rail (beginner mode)
- New: `desk/src/components/v5/GuidedFlowRail.jsx`
  - Vertical 6-step stepper from `flow.steps[]`.
  - Active step (status=`action`) auto-expands with `detail` text, flagged position exits, and a primary action button.
  - Action buttons deep-link: `regime` → MARKET, `positions` → POSITIONS, `setups/order_ticket` → DEBATE, `data` → triggers `startUpdate`.
  - Status-class per step: `--done` (✓ green), `--action` (● amber), `--blocked` (○ dim), `--skipped` (— faint).
  - Reduced-motion respected for transitions.

### 3. Collapsed Flow Strip (expert mode)
- New: `desk/src/components/v5/CollapsedFlowStrip.jsx`
  - Single-line banner: `{done}/{total} · {current step label} — {detail}`.
  - Renders above `<main>` in expert mode.

### 4. Per-Tab Purpose Headers (all 7 tabs)
- New: `desk/src/components/v5/TabPurposeHeader.jsx`
  - WHAT / HOW TO READ / NEXT copy for MARKET, SCANNERS, SHORTLIST, DEBATE, ALPHA, POSITIONS, JOURNAL.
  - Beginner mode: expanded block below nav tabs.
  - Expert mode: single line + `[? guide]` toggle to expand.
  - Rendered in `App.jsx` so tab files are untouched.

### 5. Status Vocabulary
- New: `desk/src/components/v5/StatusBadge.jsx`
  - LIVE / SHADOW / WARMING / EXPERIMENTAL / NEEDS-DATA as accessible inline chips.
  - Icons + color tokens: LIVE=green-dim, SHADOW=panel-3, WARMING=amber-glow, EXPERIMENTAL=dashed panel-2, NEEDS-DATA=red-dim.
  - Applied in `AlphaLab.jsx`: HMM health status + setup cohorts with n<20 marked NEEDS-DATA.

### 6. Alpha Lab Legibility
- `AlphaLab.jsx` fully rewritten:
  - `RelationshipLegend`: collapsible explainer — Alpha (SHADOW), Debate (LIVE), Shortlist (LIVE) with plain-English descriptions. Answers "why are different stocks on each screen?"
  - `ResearchBenchPanel`: structured v5 tables for registered models (ID / Type / Status chip / Sessions) and experiments (ID / Hypothesis / Status chip / Created). Replaces the raw `JSON.stringify` dump.
  - Setup evidence rows with n<20 rendered with NEEDS-DATA badge instead of posterior numbers.

### 7. CSS
- 270 lines added to `primitives.v5.css` for all new components.
- All colors via `--v5-*` tokens; no raw hex. Reduced-motion guarded.
- `shell-body-layout`: flex container enabling side-by-side rail + content area.
- `AlphaLab.css`: legend + research bench table styles appended.

## Files changed
| File | Change |
|------|--------|
| `desk/src/api.js` | Added `fetchFlowToday()` |
| `desk/src/App.jsx` | Flow state + 30s poll + GuidedFlowRail + CollapsedFlowStrip + TabPurposeHeader render |
| `desk/src/AlphaLab.jsx` | RelationshipLegend + ResearchBenchPanel + StatusBadge |
| `desk/src/AlphaLab.css` | Legend + bench table CSS |
| `desk/src/components/v5/GuidedFlowRail.jsx` | NEW |
| `desk/src/components/v5/CollapsedFlowStrip.jsx` | NEW |
| `desk/src/components/v5/TabPurposeHeader.jsx` | NEW |
| `desk/src/components/v5/StatusBadge.jsx` | NEW |
| `desk/src/components/v5/index.js` | Exported all 4 new components |
| `desk/src/components/v5/primitives.v5.css` | 270 lines added for all new components |

## Build verification
```
✓ 107 modules transformed.
✓ built in 3.76s
```
No errors. Chunk-size advisory is pre-existing.

## Deferred / flagged
- `StatusBadge` on the HMM chip in `CommandStrip.jsx` and `ChartDrawer.jsx`: the HMM `hmm_caption` field is already rendered — the handoff's requirement here is to surface WARMING/NEEDS-DATA when the HMM is not available, which is now done in AlphaLab via `overview.hmm_status`. The CommandStrip already shows `"—"` when unavailable (from `regime.hmm_caption`). A future tightening could add a StatusBadge tooltip there — flagged for maintainer.
- URL routing, date dead-ends, SCANNERS scroll → covered under Handoff 11.

---
Next: Handoff 7 — Search, On-demand Analysis & LIVE Stream.
