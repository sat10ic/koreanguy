# AESTHETIC BAR — LOCKED (user-stated, 2026-07-07, second strike)

The user has now stated this twice. It is a bar, not a suggestion. Every frontend
task — main thread or delegated — carries this file's path in its prompt.

## The exemplar

`Market Quadrant 27/2026` by @finallynitin (image shared 2026-07-07 in chat; user: "I had
asked for this kind of font and this kind of a market regime screen"). That poster IS the
target for the Regime screen. Its properties:

1. **Editorial poster layout, not dashboard panels.** One big composed canvas per screen:
   labeled sections (MOMENTUM / SWING / TREND / BIAS) as bold pill badges with status dots,
   charts flowing full-width, annotations layered ON the charts.
2. **Bold condensed display font** for headings/verdicts (think Archivo Black / Oswald /
   condensed grotesque, uppercase), monospace only for small data tables. NOT the current
   uniform small-mono terminal look.
3. **Hand-annotated feel**: curved arrows pointing from verdict text to the exact chart
   feature, underlined verdict phrases ("SWING is UP"), plain-language captions under each
   verdict ("more than half of the stocks are above their 10MA").
4. **Verdict-first hierarchy**: each section leads with a one-line human verdict at large
   size; numbers are secondary, in compact side tables with green/red cell shading.
5. **Color = state, everywhere**: green/amber/red fills on the chart background bands, not
   just chips. The chart itself shows the regime, not a legend.

## The identity bar

"Edge intelligence engine", not "recycled free tool". Test for every screen: would a
screenshot of it look at home next to the exemplar poster, posted by a paid research desk?
If it looks like a default-styled admin panel or a free screener, it fails regardless of
how correct the data is.

## Visual QC bar (why this file exists)

Data-correctness QC alone is NOT a done-test for frontend work. Every frontend pass must
also eyeball rendered output for: duplicate/garbled figures (e.g. two "%" on one number),
truncated lists (e.g. one index rendering where N should), overlapping/misaligned elements.
The 2026-07-07 verification pass passed all endpoints and still shipped these — that is the
failure mode this bar closes.

## Where this applies

- Regime screen: rebuild toward the exemplar (this is the flagship screen).
- All other screens: same font system, verdict-first hierarchy, poster spacing — even if
  less illustrated.
- Every Codex/subagent frontend prompt must include: "Follow manas_os/design/AESTHETIC_BAR.md;
  the exemplar is law. Do not default to compact mono dashboard styling."

## Shell and comprehension defects — user-locked (2026-07-11)

The user rejected the mixed implementation where a legacy black workspace sits inside the
Round-4 white shell. The following are release blockers across the entire desk:

1. **One visual system per viewport.** Round-4 light is the sole canvas. No black/dark legacy
   island may appear inside it, including tab bodies, panels, tables or empty states.
2. **One MANAS identity/header.** Do not render MANAS/logo/title in both the command strip and a
   second shell header. Utility controls may occupy a second row, but branding appears once.
3. **Unpopulated tables are not finished UI.** A table must contain real rows, or be replaced by
   a clear empty/loading/error explanation that says what data is missing and how it becomes
   available. Never show a mostly blank grid as content.
4. **Beginner meaning precedes dense evidence.** Every dense regime/table/model section needs a
   one-sentence layman read: what it means, why it matters, and what the user should do. Raw
   acronyms/metrics remain secondary or expert-only; a beginner must not need prior trading
   vocabulary to understand the primary screen.
5. **Product name is `sat10ic os`.** This replaces MANAS OS / MANAS DESK in all user-facing
   titles, headers, browser metadata and product copy. Internal module/database paths may retain
   `manas_os` to avoid an unrelated destructive migration.
