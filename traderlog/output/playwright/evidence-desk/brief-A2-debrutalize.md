# Orchestrator brief — Slice A2: THOROUGH de-brutalist pass (owner decision 2026-08-23)

Owner reviewed the live FEED and directed (decision recorded; supersedes the conservative
VISUAL_LANGUAGE §1a uppercase allowance for headers): the remaining "neo-brutalist dashboard"
treatment must go — this is the evidence desk, part exchange blotter, part research notebook.

OWNER'S EXACT TELLS (from the live FEED screenshot): excessive uppercase everywhere
(POSTS / FILTERS / TRADERS ON DESK / DESK headers + UNCLASSIFIED / CORE / WATCH chips +
UNRESOLVED button), heavy boxed panel chrome (2px black boxes with filled gray header strips),
KPI-style desk counts ("31 posts shown / 25 threads / 2 events"), loud majority-state chips
(UNCLASSIFIED on nearly every post today).

SCOPE DECISION: THOROUGH — the whole shell AND every product screen's chrome, including the
remaining dashboard-y compositions (BREADTH dial tiles, TRADERS hero-stat row, IDEAS/LIBRARY
chrome), converted to notebook-style evidence blocks. Keep EVERY wireframe element and its
data; restyle presentation only.

## Binding rules that still hold (do not violate)

- tokens.css is the ONLY colour literal file; new colours never; colours only via tokens; slate
  the palette paper/ink with blue (interaction) / amber (unresolved) / red+green (stated states).
- Centered 1680px grid at 1920x1080; zero document overflow; html/body overflow-x hidden.
- No border-radius (0), no gradients/glows, no blur shadows (only --press), no new shadows.
- Reading prose 14-15px; metadata 11-12px; NO label below 11px anywhere; mono for numbers,
  dates, confidence, identifiers only — never prose.
- Accessibility: focus ring (2px ink outline, never removed), min hit targets 28px (existing
  .disclosure pseudo-element pattern), contrast via token -ink variants, colour never the sole
  carrier (greyscale survival), role/aria preserved (esp. chart wrappers role="img" + exact
  finding labels — do NOT touch charts.jsx).
- ECharts/Vega-Lite render only real data; compact .chart-empty blocks stay (charts.jsx is
  OWNED by a completed slice — do NOT edit charts.jsx).
- All six product tabs + STYLE dev route unchanged; ?tab= deep links preserved.

## Work (files owned: tokens.css, app.css, thread.css, ui.jsx, ALL six screens/*.jsx, App.jsx if nav-affecting; do NOT touch charts.jsx, api.js, tests, docs, api/, ingest)

1. Sentence-case headers: panel titles, section labels (.sub-label), event kinds, filter labels,
   desk keys, dial/ratio keys, tl-kind, hero keys — sentence case, medium weight, muted ink-2.
   RETAIN uppercase ONLY for genuinely compact operational labels (nav tabs, chips, buttons,
   the UNRESOLVED toggle). Chips: keep data but quiet the chrome — lighter 1px treatment,
   sentence case content, smaller visual footprint, no bold-caps wall. UNCLASSIFIED (the
   majority kind today) must read quietly, not as a boxed badge on every post.
2. Panel chrome: replace the gray filled header strips (.panel-head surface-2 band) with a
   restrained header — sentence-case title + thin bottom hairline only; the panel keeps its
   ONE 2px structural border (major regions per evidence-desk revision). No nested heavy boxes
   anywhere (verify pass exists).
3. Notebook evidence blocks:
   - BREADTH: the three dial tiles + ratio row → one understated evidence block: the XP value,
     XP band, MBI day colour, warning flag, and r10/r20/r50/r4.5 ratios as ledger rows / inline
     evidence lines (same data, same orders; no fake bar or gauge visuals).
   - TRADERS: the hero-stats row (stated win rate dominant number stays the ONE dominant number
     per screen) → convert the 4-stat grid to a compact evidence card/block with a supporting
     line; keep stated_win_rate emphasis via size, not box.
   - IDEAS/LIBRARY: strip boxed chrome from mention strips / practice blocks to hairlines and
     fills; keep quotes verbatim and the minimum-n rule.
   - FEED: post cards keep the 2px spine + reply rail; interior uses hairlines; the event strip
     stays a contained evidence line (1px) not a box.
4. Reduce uppercase-prose density app-wide: audit every text-transform:uppercase user and
   demote non-operational ones (the verify pass checks upperProse; add a check for header
   uppercase if possible).
5. Keep all existing class names in the screens' JSX unless a rename is unavoidable; CSS-first
   restyle. If a class must change, update BOTH css and its JSX usage in the same pass.
6. The 31-vs-30 desk count inconsistency on FEED ("31 posts shown" while panel says "30 of
   202"): investigate root cause (mergeFeedPage loadedBaseCount accumulates pagination.returned
   across pages including thread-root augmentations?) and fix so the desk count reflects the
   panel's number; do NOT change pagination semantics.

## Done-test

npm run build clean; pytest traderlog/tests -q all pass (baseline 251); run_checks.py exit 0;
git diff --check clean (files are untracked — run a manual whitespace scan too). Self-smoke via
the running API at :8100 at 1920x1080 (scratch script under OUTPUT dir, delete after, do NOT
delete other files in output/playwright/evidence-desk/ — the orchestrator keeps capture tooling
there): screenshots + no console errors + zero doc overflow; verify the FEED screenshot shows
sentence-case headers, quiet chips, restrained panel heads; BREADTH/TRADERS evidence blocks.

## Orchestrator checkpoint after return

Capture-verify pass at 1920x1080 (deterministic computed-style checks: header uppercase count,
panel-head styling, sub11px labels, nested2px, upperProse, monoProse, radius/blur, grid/overflow);
compare fresh FEED screenshot against the owner's complaint list; then continue to Slice C.