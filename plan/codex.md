# TraderLog recovery plan — turn the archive into a trading intelligence desk

**Status:** Proposed by Codex on 2026-08-26  
**Purpose:** Recover TraderLog from a collection of disconnected screens and make it a reliable, current, evidence-backed engine for answering what traders are doing, what the tape did afterward, and what patterns recur.  
**Acceptance viewport:** 1920×1080 only.  
**Canonical authority:** This document is a planning artifact. Before execution, accepted work must be reconciled into `traderlog/TASKS.md`, `traderlog/HANDOFF.md`, `traderlog/design/CONTRACTS.md`, and the binding visual specifications.

---

## 1. Outcome

TraderLog should answer seven operational questions without requiring the user to read thousands of posts:

1. **What changed today?** New entries, adds, trims, stop changes, exits, watch ideas, themes, and market views—deduplicated and grouped into threads.
2. **What is actually open now?** A current ledger whose position state follows the latest cited event, not an old entry post.
3. **Where are traders converging?** Symbol- and theme-level co-attention, with who arrived first, who followed, and who went quiet.
4. **What did the stock do afterward?** Reproducible tape-after-mention returns and price action, clearly separated from what a trader claimed.
5. **What levels and setups matter?** Exact text- or image-stated entries, stops, targets, support, resistance, and watch levels overlaid on real NSE price data.
6. **How does each trader actually operate?** Timing, entry style, partial-exit behavior, stop discipline, recurring playbook rules, and evidence-backed counterexamples.
7. **What is the market context?** Fresh breadth, trader chorus, dissent, and theme rotation—not a stale breadth snapshot.

The product is an **evidence desk**, not a social feed and not a recommendation engine. Every conclusion must retain its source post, image, timestamp, derivation policy, sample size, and missing-data state.

---

## 2. Current baseline and truth gaps

### Confirmed by `STATE.json`

- [x] 17 tracked traders.
- [x] 3,395 real posts and no production mock posts.
- [x] 305 position records exist.
- [x] Database, parse, attribution, derive, and UI checks were recorded as passing in the last generated state.
- [ ] The last generated state records the golden suite as failing: 2 failed, 449 passed.

### Reported in `HANDOFF.md`, but must be re-audited before being treated as accepted

- [~] All 3,395 posts classified.
- [~] Vision transcription complete for 1,274 media items, with no eligible media left unread.
- [~] 305 positions derived from the classified corpus.
- [~] TradingView Lightweight Charts and stock analytics endpoints implemented.
- [~] Feed, Ledger, Traders, Breadth, Radar, and Library redesigned.

These reports conflict with the user-visible result and, in places, with the generated state. Phase 0 therefore treats the running application, SQLite rows, API payloads, source citations, and browser output as the truth—not completion reports.

### Product failures to correct

- [ ] The Feed is visually noisy and does not synthesize insight.
- [ ] Ledger state is not trusted: old entries dominate, Manas Arora closes are missing or mislinked, and closed positions are not reliably visible.
- [ ] Traders is descriptive but not analytically useful.
- [ ] Breadth is stale.
- [ ] Stock-level analytics and Lightweight Charts are absent, inaccessible, or not connected to the visible workflow.
- [ ] Library is an archive rather than a reconstructed, testable playbook.
- [ ] Layout has out-of-bounds and containment defects.
- [ ] The actual served instance does not consistently expose the latest source work.

---

## 3. Product map

The visible product becomes six primary workspaces plus one routed symbol view:

| Workspace | Question answered | Primary content |
|---|---|---|
| **Now** | What changed and needs attention? | New position events, changed threads, unresolved work, fresh watch ideas, themes, and market views |
| **Ledger** | What is open, changed, and closed? | Current active book, recent changes, closed history, cited lifecycle detail |
| **Radar** | Where is independent attention converging? | Symbol co-attention, tape after mention, level density, evidence rail |
| **Traders** | How does this trader operate? | Activity, lifecycle quality, timing fingerprint, style, open book, recurring methods |
| **Market** | What environment are they trading in? | Fresh breadth, trader chorus/dissent, theme rotation, regime history |
| **Playbook** | What repeatable methods are visible? | Derived rules, supporting posts, linked behavior, counterexamples, sample sizes |
| **Symbol** | What is the complete case for this stock? | NSE candles, volume, trader markers, image levels, tape metrics, activity, mentions, positions |

The raw post archive remains accessible through evidence rails and drill-downs. It is not a primary navigation destination.

---

## 4. Delivery plan

Each phase is a vertical slice. It must leave the running instance more truthful and useful than before it started.

### Phase 0 — Establish runtime truth and stop false completion

**Goal:** Identify exactly what code, database, API, and frontend build the user is seeing.

**Work**

- Resolve the served-instance chain: launcher → API process → database path → UI source → built `dist` → browser origin.
- Compare the working tree with the files actually served. Eliminate stale processes and stale frontend builds.
- Run the full checks and focused tests; reconcile the golden-suite contradiction before accepting later work.
- Inventory every visible route and endpoint against the current source, using the production API and the real database.
- At 1920×1080, record screenshots, overflow measurements, console errors, failed requests, and a short finding for every route.
- Produce one data-coverage table: posts, classified posts, media, vision rows, trade-event posts, position events, positions by status, closed positions by trader, last event date, daily-price freshness, breadth freshness, and unresolved link candidates.

**Acceptance criteria**

- [ ] One command starts the actual TraderLog instance and serves the current UI build against `traderlog/data/traderlog.db`.
- [ ] The browser visibly changes when a harmless source marker is rebuilt, proving there is no stale-instance ambiguity.
- [ ] `python traderlog/run_checks.py` and the focused golden suite have an explained, reproducible outcome.
- [ ] Every later phase has a measured baseline rather than relying on a handoff claim.

**Checkpoint:** Do not redesign or re-reconcile until this phase identifies the real runtime and records the baseline.

### Phase 1 — Make the Ledger correct before making it attractive

**Goal:** Reconstruct current trade lifecycles, especially Manas Arora, so the tool knows what is open, partial, closed, scratched, or unclear.

**Work**

- Build a reconciliation coverage report by trader and symbol: classified trade-event posts, threaded events, standalone candidate events, linked events, positions, and unresolved items.
- Audit Manas Arora first using a recent, source-backed sample that includes entries, self-reply updates, chart images, partial exits, and final closes.
- Fix systemic linkage failures, not individual rows: reply ancestry, standalone same-symbol closes, multiple overlapping positions in one symbol, image-only prices, and ambiguous “booked” language.
- Re-run full-thread reconciliation after any new event; never patch LLM state incrementally.
- Keep uncertain links in review. Never invent entry, exit, stop, quantity, ancestry, or status.
- Derive a position’s `last_event_at`, `closed_at`, current status, latest stop, and last cited update from its accepted event stream.
- Add coverage and freshness metadata to the Ledger payload so the UI can state when a book is incomplete.

**Acceptance criteria**

- [ ] A hand-verified recent Manas sample matches the X evidence event for event, including closes.
- [ ] Every populated lifecycle field resolves to an archived post or image citation.
- [ ] A position with an accepted full exit appears in Closed; a partial exit remains Partial; an ambiguous close remains Unclear/review.
- [ ] Ledger defaults to currently open positions plus recent closes, ordered by latest accepted event—not entry age.
- [ ] Re-running reconciliation is idempotent and does not duplicate positions or events.

**Checkpoint:** The user reviews the Manas sample and the Active/Changed/Closed counts before the remaining traders are bulk-reconciled.

### Phase 2 — Ship the Symbol intelligence workbench

**Goal:** Make every symbol a connected analytical case rather than a ticker scattered across tabs.

**Work**

- Expose a stable Symbol route from Ledger, Radar, Traders, Now, and Market.
- Render only NSE-validated `daily_prices` in TradingView Lightweight Charts: daily candles, volume, date/price scales, crosshair, and responsive resize.
- Overlay accepted trader events as markers: watch, entry, add, trim, stop move, exit. A marker opens the exact evidence.
- Overlay text- and image-stated levels without merging conflicts: entry, stop, target, support, resistance, trigger. Each level shows trader, date, source type, confidence, and thumbnail.
- Surface existing tape metrics and activity signals where they are actually available: ADR, tightness/VCP proxy, moving-average and 52-week location, relative volume/activity bursts, and data freshness.
- Add a chronological evidence rail containing posts, replies, chart thumbnails, positions, and unresolved items.

**Acceptance criteria**

- [ ] RATEGAIN, FCL, and two additional data-rich symbols render real candles and source-backed markers at 1920×1080.
- [ ] Clicking a marker or level opens its archived post/image evidence.
- [ ] No price, marker, level, or metric appears when its source is missing.
- [ ] Invalid or uncovered symbols show one compact, explicit missing-data state.
- [ ] The chart and evidence rail stay inside the centered 1680px grid with zero document overflow.

### Phase 3 — Replace the Feed with “Now”

**Goal:** Turn incoming posts into an operational briefing.

**Work**

- Group posts into changed conversation threads rather than independent cards.
- Create explicit sections: New positions, Position changes, Exits, Watch/Setup formation, Themes/Market reads, and Needs review.
- Rank by event recency and operational significance; preserve a chronological “All activity” fallback.
- Show the thread rail as the signature: root → reply → classified event → position change → image evidence.
- Summarize only deterministic facts: symbol, event type, stated numbers, current lifecycle effect, source count, and unresolved count.
- Keep exact post text and media one disclosure away; do not replace evidence with generated prose.

**Acceptance criteria**

- [ ] A new entry, add, partial exit, close, watch idea, and market-view post each lands in the correct section.
- [ ] The same thread does not appear as several disconnected cards.
- [ ] Every summary links to the exact evidence and resulting Ledger or Symbol state.
- [ ] Empty sections do not render as large framed placeholders.
- [ ] The page has one clear reading path and no nested card grid.

### Phase 4 — Complete the intelligence surfaces

#### 4A. Radar: attention plus the tape’s verdict

- Finish tape-after-mention with the locked IST/no-look-ahead anchor and 1/5/10/20-session returns.
- Add entry/holding/exited counts separately from bare mentions; never sum talk and money into one unlabeled score.
- Add level density using exact vision/text levels and source thumbnails.
- Show who arrived first, who followed, and who stopped mentioning the symbol.
- Preserve coverage debt and missing-price counts.

**Done when:** the user can select a symbol and understand attention, timing, subsequent tape, levels, positions, and evidence without leaving the workspace.

#### 4B. Market: fresh breadth plus trader chorus

- Repair daily-price/bhavcopy and breadth freshness before changing presentation.
- Show current XP/MBI, regime history, and raw breadth with explicit source date.
- Add distinct-trader Risk-on/Risk-off/Neutral chorus, dissent, and exact cited posts.
- Add theme rotation: distinct traders, symbols, first/last mention, 7/30-day acceleration, and tape follow-through where coverage permits.

**Done when:** stale data is visibly labeled, fresh data is dated, and the screen distinguishes measured breadth from trader opinion.

#### 4C. Traders: behavior, not profile decoration

- Show last-30-day activity and lifecycle coverage before performance metrics.
- Add timing fingerprints: entry-to-trim, entry-to-close, stop-to-cost timing, and hold distribution using trading sessions where appropriate.
- Show explicit style mix, recurring terms, sector/theme concentration, open book, recent closes, and unresolved coverage.
- Compare stated results with reproducible tape only as separate fields; do not create a composite credibility score.
- Suppress percentages below their required sample threshold and always show `n`.

**Done when:** selecting Manas or Fastzone explains how they trade, how complete the archive is, and which examples support each conclusion.

#### 4D. Playbook: reconstructed methods with counterevidence

- Replace Library’s quote archive with candidate rules derived from recurring exact phrases and accepted behavior.
- Each rule must show supporting posts, linked trades, counterexamples, confidence, and sample size.
- Separate “what they say” from “what accepted lifecycles show.”
- If evidence cannot support a rule, fall back to a cited vocabulary/setup index instead of generated doctrine.

**Done when:** no rule can appear without expandable source evidence and an honest contradictory-example state.

### Phase 5 — Production freshness and immediate alerts

**Goal:** Keep the intelligence current during Indian market hours without depending on Chrome cookies.

**Work**

- Implement the official X API adapter behind the existing `fetch_timeline(handle, since)` contract; browser capture remains manual recovery/backfill only.
- Capture posts and replies, referenced-post identity, conversation IDs, media expansions, and timestamps.
- Use per-handle watermarks that advance only after archive, media hash, and database success.
- Prefer filtered stream when the entitlement supports it; otherwise use fair 30–60-second market-hours polling with catch-up at startup, reconnect, periodically, and shutdown.
- Enforce the owner’s configured daily read ceiling and no-overage policy. Prioritize the CORE account and rotate fairly rather than silently exhausting the allowance.
- Connect accepted explicit text entries to the transactional Telegram outbox; image-dependent items send a cited evidence notice first and an enriched follow-up after vision.
- Keep real Telegram delivery disabled until dry-run latency, deduplication, restart recovery, and owner enablement pass.

**Acceptance criteria**

- [ ] Three real traders observed over seven market sessions with replies and media retained.
- [ ] No missed post after forced reconnect, no duplicate archive row, and no duplicate Telegram outbox item.
- [ ] Explicit text entry receipt-to-outbox latency is measured and at most 60 seconds under normal operation.
- [ ] No secret appears in source, SQLite, logs, browser storage copied by the tool, or completion reports.
- [ ] Daily usage stops before paid overage and is visible in health/state.

### Phase 6 — Visual completion and release gate

**Goal:** Apply one restrained, professional visual system after the underlying questions are answerable.

**Binding direction**

- Quiet editorial evidence desk: warm paper/ink surfaces, deep blue interaction, amber unresolved, red/green only for genuine measured state.
- Sentence case for prose; uppercase only for the compact navigation rail and single-word column labels.
- Mono only for prices, percentages, dates, confidence, and identifiers.
- One 1px structural border per major region, restrained hairlines inside, no nested boxes.
- No card grids, gradients, glows, rounded corners, fake KPIs, random icons, ornamental charts, or large framed empty states.
- ECharts for terminal/time-series analytics; Vega-Lite for custom analytical graphics; Flint only as a reviewed generation path; Plotly only where deep interaction justifies it; Lightweight Charts only for price panes.

**Acceptance criteria**

- [ ] Every visible screen is inspected in the actual running instance at 1920×1080.
- [ ] Content and header align to the centered 1680px grid.
- [ ] Document width is exactly the viewport width; no panel, table, chart, image, or disclosure escapes its bounds.
- [ ] Zero console errors/warnings, zero failed requests, and no stale build/process mismatch.
- [ ] Keyboard navigation, disclosures, filters, sorting, source links, and cross-screen symbol links work.
- [ ] Every percentage/average shows its sample size; every chart has an accessible finding label and a scale.

---

## 5. Interfaces and data changes

The implementer must lock these contracts before parallel UI work begins:

- **Position freshness:** add or guarantee `last_event_at`, `closed_at`, accepted event count, unresolved count, and reconciliation coverage state in position payloads.
- **Now payload:** return changed threads/events with deterministic section labels and links to affected position/symbol records; preserve exact posts and citations.
- **Symbol payload:** combine validated OHLCV, tape metrics, activity signals, cited levels, mentions, position lifecycles, event markers, media, and freshness metadata without fabricating missing inputs.
- **Trader payload:** expose coverage denominators, recent activity, accepted timing observations, style mix, cited rule candidates, and recent lifecycle summaries.
- **Market payload:** expose source date/freshness, breadth history, cited trader chorus, and cited theme clusters separately.
- **Health/state:** expose served build identity, database path identity without leaking secrets, last successful run per pipeline, price/breadth freshness, ingest allowance usage, and reconciliation coverage.

Any shape change must update `traderlog/design/CONTRACTS.md` in the same change. Each derived metric has one writer. Missing values stay null/unknown; they never become zero.

---

## 6. Execution discipline and model ownership

- Codex/orchestrator defines contracts, scopes executor work, reviews diffs, runs checks, and personally verifies the browser. Executor self-reports are not acceptance.
- Implementation is split into one bounded handoff per vertical slice. Each handoff names owned files, forbidden files, required specs, and a measurable done-test.
- Every model appends its exact contribution to `design/MODEL_WORK_LOG.jsonl` and includes the matching Attribution-ID in its completion report.
- Shared API contracts are completed before backend/UI tasks are parallelized.
- No executor edits another executor’s owned files without an explicit re-scope.
- No production mock data, inferred trade numbers, silent manual row patches, or uncited conclusions.
- No commit until the owner has reviewed the verified deliverable, unless the owner explicitly orders a commit.

Suggested execution order:

1. Runtime truth audit.
2. Manas lifecycle/close audit and reconciliation fix.
3. Ledger current-state UI.
4. Symbol workbench end to end.
5. Now workspace.
6. Radar tape/levels.
7. Market freshness/chorus/themes.
8. Trader behavior and Playbook.
9. Official live adapter and Telegram dry run.
10. Cross-screen visual and release acceptance.

Phases 2–4 use the existing corpus and can proceed without new X pulls once Phase 1 makes the event graph trustworthy. Phase 5 is the only phase that requires production X credentials/entitlement and live-session observation.

---

## 7. Global test matrix

### Data integrity

- Every populated extracted field cites an input post.
- Every media path exists and matches its first-sight SHA-256.
- No orphan events, duplicate post IDs, duplicate lifecycle events, or regressing watermarks.
- Same thread input produces byte-equivalent reconciled state.
- Missing prices, timestamps, sessions, or horizons render unknown—not zero.

### Golden cases

- Manas: entry → self-reply explanation → add/stop update → partial exit → final close.
- Fastzone: entry context → day-one risk-free update → one-third at 3R → trailing remainder → close/unknown close.
- Image-only level and broker confirmation.
- Standalone same-symbol exit with one open candidate and with multiple candidates.
- Two overlapping positions in one symbol.
- Deleted post retained and visibly marked.
- Corporate-action or price-gap case that must not be misread as trader performance.

### Browser acceptance at 1920×1080

- Actual served instance, production API, real-data database.
- Every primary route plus Symbol.
- Zero horizontal document overflow and zero out-of-bounds descendants.
- Clean console and network.
- Filters, sorting, keyboard selection, disclosures, chart resize/crosshair, source links, and cross-screen navigation.
- Visual comparison against the binding quiet-editorial language, not neo-brutalist or generic AI-dashboard conventions.

---

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Completion reports overstate working behavior | High | Phase 0 verifies DB → API → UI → browser independently before accepting claims |
| Manas replies/closes remain unlinked | High | Recent source-backed golden lifecycle set; systemic linker fixes; ambiguous cases stay reviewable |
| Reconciler creates plausible but false state | High | Whole-thread input, strict citations, no inferred numbers, idempotence fixtures, human spot checks |
| Visual redesign masks bad data | High | Ledger truth and Symbol data paths ship before global visual polish |
| Stale bhavcopy/breadth makes insights misleading | High | Freshness is explicit in payload and UI; stale analytics never present as current |
| Phrase mining creates AI-slop playbooks | High | Every rule requires citations, behavior links, counterexamples, confidence, and `n`; otherwise show vocabulary only |
| X free allowance cannot cover the roster at required latency | High | Measure real post-resource consumption, prioritize CORE fairly, stop before overage, require owner approval for a higher tier |
| Parallel models overwrite work | Medium | File ownership per handoff, contract-first sequencing, mandatory attribution, orchestrator diff review |
| Charts look authoritative when data is missing | High | Validate NSE series, render honest compact empty states, never synthesize candles or levels |

---

## 9. Final definition of done

TraderLog is ready for owner acceptance only when:

- [ ] The served instance and repository source are proven to be the same build.
- [ ] Recent Manas and Fastzone lifecycles—including closes—pass source-by-source audit.
- [ ] Ledger answers what is open, what changed, and what closed using latest accepted events.
- [ ] Symbol pages show real NSE candles, trader events, image/text levels, metrics, and evidence.
- [ ] Now synthesizes new information instead of presenting a raw card feed.
- [ ] Radar combines attention with honest tape-after-mention and coverage debt.
- [ ] Market is fresh or explicitly stale and separates breadth measurements from trader opinion.
- [ ] Traders and Playbook show derived behavior with citations, counterexamples, and sample sizes.
- [ ] All primary screens pass the 1920×1080 containment, console, network, keyboard, and visual-language gates.
- [ ] `python traderlog/run_checks.py`, the full pytest suite, UI build, and focused browser tests pass.
- [ ] Model attribution and completion reports match the actual diff and verification evidence.

The final product must feel like a brain because it connects evidence across time, traders, symbols, price action, and market context—not because it adds more panels.
