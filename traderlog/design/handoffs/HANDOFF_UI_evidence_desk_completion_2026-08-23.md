# HANDOFF — evidence-desk completion

Status: READY. The W1b existing-capture import and FEED pagination dependencies
closed on 2026-08-23. Re-read the working tree before starting and preserve
their importer, pagination, unknown-ancestry, and evidence-integrity behavior.

## Goal

Finish TraderLog as an evidence desk — part exchange blotter, part research
notebook — across the six product screens. Remove the remaining generic
neo-brutalist-dashboard treatment without adding decorative “AI dashboard”
chrome.

## Read first, in order

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md`
6. `traderlog/design/CONTRACTS.md`
7. `traderlog/design/VISUAL_LANGUAGE.md`
8. `traderlog/design/WIREFRAMES.md`

The `Evidence-desk completion revision, 2026-08-23` in
`VISUAL_LANGUAGE.md` supersedes conflicting older “every panel is a box” and
large empty-frame clauses.

## Verified starting point

Already present; preserve it:

- centered 1680px desktop grid at 1920×1080;
- FEED two-column evidence workspace and secondary rail;
- 2px thread spine for known reply ancestry;
- unresolved prose collapsed to a count/disclosure;
- LEDGER archived images contained inside expanded detail;
- paper/ink palette and the ECharts/Vega-Lite renderer ladder;
- production is real-data-only.

Still open:

- FEED shows only an image count, not evidence thumbnails;
- 9–10px global label tokens and pervasive uppercase remain;
- nested panels still create redundant heavy boxes;
- future-wave screens still render large framed empty charts;
- mobile navigation and compact record-row layouts are not implemented;
- mono/uppercase usage is broader than operational data and labels;
- the enlarged W1 corpus needs paginated access without losing the thread rail.

## Work slices

### Slice A — shell, type and structural hierarchy

- Reading prose: 14–15px, sentence case, grotesk/sans.
- Metadata: 11–12px. Remove 9–10px production labels.
- Mono only for prices, percentages, dates, confidence and identifiers.
- Uppercase only for compact operational labels.
- Keep one 2px border around each major region; replace nested heavy boxes with
  1px evidence-row rules.
- Do not introduce card grids. The palette stays paper/ink with blue for
  informational/navigation emphasis, amber for caution, and genuine red/green
  only for real negative/positive state; color never carries the meaning alone.
- Preserve the centered 1680px desktop system and zero document overflow.

Checkpoint: verify FEED, TRADERS, LEDGER, BREADTH, IDEAS and LIBRARY at
1920×1080 before proceeding.

### Slice B — evidence rail and archived-image thumbnails

- Keep the known post → reply → trade-event spine as the signature element.
- Mark unproven/null ancestry as “thread unknown”; never present it as a
  confirmed root.
- Show contained, source-backed `/api/media/...` thumbnails beside the extracted
  evidence they support. Never hotlink X, invent a chart, or show only an image
  count when archived media exists.
- Clicking a thumbnail may open the existing evidence/detail disclosure; do not
  create a modal unless the current information architecture requires one.
- Keep unresolved issues as a concise count with full text in disclosure.
- Preserve FEED pagination, filtering, deduplication and whole-thread behavior.

Checkpoint: verify a real media post, a text-only post, a known reply thread and
an unknown-ancestry post at 1920×1080.

### Slice C — sparse/future-wave states

- Replace large framed empty charts on future-wave screens with one compact
  explanatory block stating what evidence is unavailable and which upstream
  capability will provide it.
- Do not create fake KPIs, demo series, ornamental graphics or placeholder
  visualizations.
- A compact chart-specific empty state is allowed only inside an otherwise
  data-bearing analytical screen.
- Use ECharts for terminal/time-series work and Vega-Lite for custom analytics
  only when the payload contains real data.

Checkpoint: test zero-row disposable data for every screen and confirm no blank
giant SVG/frame dominates the viewport.

### Slice D — explicit mobile mode

- All six product destinations remain reachable; silently hiding tabs is a
  defect.
- Use an explicit mobile nav mode (compact menu or contained horizontal tab
  strip with clear affordance).
- Convert non-comparison tables into compact record rows.
- Permit local horizontal scrolling only for genuine side-by-side comparison
  tables; the document itself must not scroll horizontally.
- Preserve evidence order, disclosures, citations and filter access.

Acceptance viewport: 390×844 unless the owner specifies another before this
slice starts. This mobile slice is newly reopened by the owner; it was excluded
from the earlier 1920×1080-only recovery.

## Exact source-file scope

- `traderlog/ui/src/App.jsx`
- `traderlog/ui/src/components/ui.jsx`
- `traderlog/ui/src/components/charts.jsx`
- `traderlog/ui/src/screens/Feed.jsx`
- `traderlog/ui/src/screens/Traders.jsx`
- `traderlog/ui/src/screens/Ledger.jsx`
- `traderlog/ui/src/screens/Breadth.jsx`
- `traderlog/ui/src/screens/Ideas.jsx`
- `traderlog/ui/src/screens/Library.jsx`
- `traderlog/ui/src/styles/tokens.css`
- `traderlog/ui/src/styles/app.css`
- `traderlog/ui/src/styles/thread.css`
- `traderlog/tests/test_browser_review.py`
- `traderlog/tests/test_pc_layout.py`

Do not edit source files outside this list without an amended handoff. Do not
touch ingest, LLM prompts, classification, reconciliation, production data,
Manas OS, package dependencies, API contracts, or any documentation except the
required completion handoff and attribution ledger. If a payload is missing,
stop and report the exact field instead of inventing it.

## Done-test

- `npm run build` passes.
- Full TraderLog pytest suite passes.
- `python traderlog/run_checks.py` exits zero (honest freshness warnings allowed).
- At 1920×1080: 1680px centered grid, zero document/panel/image overflow, clean
  console/network, readable 14–15px prose and 11–12px metadata.
- At 390×844: all six destinations reachable, zero document overflow, no hidden
  controls, record rows readable, and any horizontal scrolling is local to a
  named comparison container.
- Capture browser evidence for both named viewports: route/screen coverage,
  real-versus-disposable data source, document and panel overflow results, and
  clean console/network output. Keep the resulting screenshots or test artifacts
  with the completion report rather than describing an unobserved visual pass.
- Real archived thumbnails render beside evidence and never hotlink X.
- Unknown ancestry is labelled; known reply threads retain their rail/order.
- No large future-wave empty chart frames, decorative charts, card grids, fake
  KPIs, gradients, glows, random icons or redundant nested borders. Blue/amber
  remain restrained semantic accents; red/green denote genuine state only.
- Append an executor record to `design/MODEL_WORK_LOG.jsonl` using the exact
  model/host identity when documented and cite its `Attribution-ID` in the
  completion handoff. The root adds separate orchestrator/reviewer records only
  after personal verification; do not collapse their claims into the executor
  record. Write the completion handoff from `COMPLETION_TEMPLATE.md`; do not
  commit.

## Risks

- This is a multi-screen change. Close each slice independently and keep the
  app green; do not perform one bulk CSS rewrite followed by a single final
  screenshot.
- The current wireframes contain older box-heavy examples. The latest
  evidence-desk revision is binding when they conflict.
- Data sparsity must stay visible. Better empty-state styling may not imply that
  classification, trader-style or validation data exists.
