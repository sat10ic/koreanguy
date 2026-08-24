# TraderLog — backlog

Status: `[x]` done · `[~]` partial/in progress · `[ ]` pending

Keep this current **at every wave close**, not at session end. Manas OS's own
TASKS.md went 12 days stale while work tracked only in a session tool, which is
why that project now has an explicit standing order about it. Same rule here.

Rules for entries:
- Titles are stable; numbers are not. Cross-reference by title.
- `[~]` requires an explicit **DONE** / **STILL OPEN** split. Never mark `[x]`
  on anything with an open remainder.
- Every closed item carries evidence: a measured number, a file:line, or a
  command whose output proves it.
- Nothing disappears silently. Killed items move to DROPPED with a reason.

Controlling plan: `C:\Users\satta\.claude\plans\how-can-you-start-happy-sunrise.md`

---

# OUTSTANDING

## Scouting × Wire redesign wave (2026-08-24) — owner-approved fourth direction

- [x] **Execute `design/REDESIGN_SCOUTING_WIRE.md` — the fourth visual
      direction, built in full.** Dark ground scouting×wire: token layer
      (`--ground/--raised/--sunken/--edge/--hair/--ink ladder/--risk/--up/
      --down/--caution`, radius 0, no shadows), 1680px grid kept, nav renamed
      TODAY/LEDGER/TRADERS/IDEAS/LIBRARY/MARKET (+ route-only STYLE/SYMBOL),
      ⌘K command bar (control-palette over tabs/traders/symbols), Stat
      explained-stat component, all six screens rebuilt — Today's four
      computed bands (Money moved / Names to watch / Background / Removed),
      Ledger's shared time axis (PositionBars → ECharts custom series) with
      outcome-in-words + computed overlap sentence, Traders' one-question-
      at-a-time ranked thresholds ("— too few", never a percentage),
      Ideas' mention heat strips + follow-through, Library's quote-hero +
      raised practice block with the 10-trade minimum, Market's quiet hero +
      worded ribbon legend + cumulative A/D (ECharts), and the new Symbol
      landing page (lightweight-charts candles from `daily_prices`,
      validated only; new `GET /api/symbol/{symbol}`). XP fixed first (C8,
      below) so Market ships WITHOUT the §8 caution block. Evidence:
      `checks` exit 0 (`golden` runs the suite), whole pytest **283 passed**,
      Vite build clean, orchestrator's live 1920×1080 probe PASS on all seven
      routes (grid 1680@x=120, zero overflow, zero console/≥400 issues,
      bands ordered, `--risk` scoped to money rows, Market zero-risk,
      ⌘K navigates), screenshots in `output/playwright/scouting-wire/`.
      Docs reconciled in the same change: `VISUAL_LANGUAGE.md` (supersession
      banner), `WIREFRAMES.md` (rewritten to the direction),
      `design/CONTRACTS.md` §8 (+`/api/symbol`, breadth/traders additive
      fields, screen renames), `design/DECISIONS.md` (dated line),
      `design/AUDIT_LEDGER.md` (C8 closed with recompute evidence).
      See `design/handoffs/HANDOFF_scouting_wire_2026-08-24_COMPLETED.md`.
- [x] **C8 — XP seed transient fixed, production recomputed and verified.**
      Percent inputs restored (retracted C6 conversion removed at the
      `regime_daily.py` call site), reseed z-state seeds from the session's
      own observed `up_4pct`, and `backfill(warmup_sessions=20)` computes the
      first 20 breadth dates in memory and persists nothing — the transient
      is discarded, not presented as data. `compute_xp` untouched. Production
      recompute (pre-change backup
      `data/traderlog.db.backup-pre-xpfix-20260824`): 431 persisted rows,
      **0 at cap, 0 EXTREME, max 81.31**, bands LOW 349/BUILDING 67/STRONG 15,
      reseed_points `['2025-06-20']` (46-day gap seeds from observed
      up_4pct=2.949), latest-5 breadth/regime parity True. Audit G12 records
      the verification catch (initial claim was incomplete; warm-up
      follow-up required before acceptance).
- [~] **STILL OPEN: observe a real deletion → the Removed band appears.**
      `posts.deleted_at` has 0 rows; the band renders only when non-empty
      (per design §11). The lifecycle is covered by a disposable-DB browser
      test; production needs a real deletion to show it.
- [~] **STILL OPEN: record glosses on Today.** The plain-English record
      glosses (e.g. "He keeps that promise 6 times in 10") depend on
      `trader_style` ≥10 closed positions (W6); until then Today omits them
      rather than inventing, per design §11. Also: first persisted XP session
      (2024-09-30) reads 30.9 BUILDING — cosmetic elevated carry, noted as
      audit I12.

## W3c — 1920×1080 PC UI recovery

- [x] **Recover the desktop evidence desk** — executed
      `design/handoffs/HANDOFF_W3c_pc_ui_recovery.md` (2026-08-23, GLM 5.3
      via ZCode, direct implementation per the handoff's no-delegation
      instruction). The owner rejected the previous visual result; 1920×1080
      was the only acceptance viewport. Delivered: centered 1680px grid on one
      horizontal system with the header; six product tabs (STYLE demoted to
      the `?tab=STYLE` dev route); FEED recomposed as the two-column evidence
      desk (thread workspace primary with the 2px spine signature, filters +
      traders + desk counts in the rail); LEDGER unresolved compressed to
      `⚠ N unresolved` with full strings in expanded detail; expanded-detail
      media containment (`min-width:0` tracks, contained images — the
      1709px RATEGAIN image no longer clips). Reading copy 14px; metadata
      12px. `VISUAL_LANGUAGE.md` §1a and the FEED/LEDGER wireframes were
      reconciled before the code. Evidence: all ten 1920×1080 done-test
      measurements pass (`page` 1680@x=120; `scrollWidth===1920` on every
      expanded detail; zero overflowing panels; zero out-of-bounds images;
      zero console errors/warnings; zero ≥400 responses; filters, sort, and
      all three disclosures verified); 4 new real-browser tests in
      `tests/test_pc_layout.py` including a permanent containment regression
      against the real 1709px archived image; whole suite 175 passed;
      `run_checks.py` exit 0; `git diff --check` clean. After screenshots in
      `output/playwright/traderlog-pc-recovery/`. **STILL OPEN (by design):**
      the reviewing model's orchestrator verification record, and the other
      screens' own compositions at 1920×1080 (out of scope here). See
      `design/handoffs/HANDOFF_W3c_pc_ui_recovery_COMPLETED.md`.

## W3d — evidence-desk completion

- [ ] **Finish the visual direction across all six product screens.** The owner
      confirmed that W3c implemented only part of the intended evidence desk.
      Remaining work includes source-backed evidence thumbnails, narrower
      mono/uppercase use, restrained interior hairlines instead of redundant
      heavy boxes, compact future-wave empty states, and an explicit mobile
      navigation/record-row mode. Execute
      `design/handoffs/HANDOFF_UI_evidence_desk_completion_2026-08-23.md` next.
      Its W1b corpus-import and FEED-pagination dependencies are now closed.

## W1 — ingest (any model)

**LIMITED RESUME BY OWNER (2026-08-23), SUPERSEDED SAME DAY:** the owner
subsequently authorised capture/ingest of posts AND replies for all eight
roster handles — the four active (`@iManasArora`, `@Fastzonetrader`,
`@tradinghustlr`, `@VCPSwing`) plus the four pending (`@StocksNerd`,
`@ChartistEdge`, `@iArpanK`, `@mystocks_in`) — via a fresh Chrome-extension
checkpoint (mechanism decision recorded in `HANDOFF.md`, amended 2026-08-23).
This un-pauses the staged `@tradinghustlr` records (175 in the W1b checkpoint
file) and authorises first capture + atomic activation for the four pending
handles. Strict importer extended 2026-08-23 (`ingest/provisional_import.py`:
8 approved handles, first-capture roster creation); importing is pending the
fresh checkpoint.

- [x] **Existing Manas/Fastzone corpus import** — the strict W1b importer
      validated 218 staged records, excluded 2 pinned and 19 empty/no-media
      records, preserved 7 existing posts, and archived/indexed 190 new posts
      plus 106 new media files. Production now exposes 202 real posts total:
      84 Manas, 113 Fastzone, 3 VCPSwing, and 2 Trading Hustler. All 202 raw
      archives parse, all 115 media files exist and match their stored SHA-256,
      and no mock rows are present. Missing ancestry remains null/unresolved.
      This closes corpus exposure only; it does not satisfy the separate
      seven-day live-observation done-test or authorise new X pulls.

- [~] **Browser X fetcher — bootstrap/recovery only** — `ingest/xfetch.py`.
      Persistent browser profile the user logs into by hand; no password touched
      by any script. Poll each
      active trader's timeline **including replies** (self-replies are where adds
      and exits live, and they do not fire bell notifications — this is why the
      email-notification route was rejected outright). Group by `conversation_id`.
      Interface is fixed by `CONTRACTS.md`: `fetch_timeline(handle, since) -> list[RawPost]`.
      **DONE:** persistent-profile, read-only `/with_replies` GraphQL capture,
      exact `conversation_id`/`in_reply_to`, long-form text, configured jitter,
      idempotent DB writes, 30-day first backfill, stagnant-page scrolling, and
      no-raise multi-trader `run()`, and isolated manual `--login` mode; 59 tests pass in
      `pytest traderlog/tests -q` on 2026-08-23.
      No-pull hardening also rejects HTTP/GraphQL/error-only or wrong-author
      responses, prevents old pinned posts from ending pagination early,
      advances non-regressing trader watermarks, and restricts media downloads
      to non-redirecting HTTPS requests for X's exact media hosts.
      An isolated seven-day/three-trader dummy replay additionally proves archive
      parity, reply identity, chart hashing, deduplication, deletion stamping,
      and the ingest check without writing synthetic rows to production.
      A strict authenticated-Chrome manifest importer has now bootstrapped 12
      real posts across all four approved traders with nine chart files; the
      production ingest check passes 4/4 and an isolated real-manifest replay
      proves idempotency and archive parity. **PRODUCTION AUTH DECISION
      (2026-08-23):** automated Chromium login is not a supported live
      dependency. Build an official X API v2 app-only adapter behind the same
      `fetch_timeline(handle, since)` contract. **CORRECTION BY OWNER:** production
      ingestion stays live throughout configured market hours so entry posts can
      reach Telegram immediately. Prefer one filtered-stream connection with
      `from:` rules for the approved roster when the entitlement supports it;
      otherwise poll public user timelines every 30–60 seconds using the last
      successful per-handle watermark. Run a timeline catch-up at market-open,
      after every reconnect, and before shutdown. Preserve replies, conversation
      fields, referenced posts and media expansions. Do not run production API
      historical backfills or paid overage without a new owner instruction.
      Historical data is a
      separate model-assisted, source-backed staging/import workflow with human
      review; it may not write inferred facts directly to production.
      Browser/extension capture remains a manual bootstrap or recovery route
      only. **STILL OPEN:** official-API market-hours adapter, immediate
      entry-alert path, and continuous live done-test — 3 real traders over 7
      market sessions.

- [ ] **Official X API market-hours live adapter** — new production W1 path;
      browser capture remains recovery-only. Implement behind the existing
      `fetch_timeline(handle, since) -> list[RawPost]` boundary so archive,
      storage and downstream parsing do not depend on the transport.
  - [ ] Add app-only Bearer Token authentication from a deployment environment
        secret. Never persist or log the token; fail closed when it is absent,
        rejected or lacks the required read entitlement.
  - [ ] Resolve approved handles to immutable X user IDs and cache that mapping.
        Reject author mismatches and never activate an unapproved handle from an
        API response.
  - [ ] Request full source fields required by TraderLog: post ID, author,
        created time, full text/note text, `conversation_id`, reply/reference
        identifiers, attachments and media expansions. Do not exclude replies.
  - [ ] During the configured exchange-session window, prefer one filtered
        stream with roster `from:` rules when the entitlement supports it.
        Otherwise poll each timeline every 30–60 seconds. The schedule must use
        the configured exchange calendar/timezone rather than the host clock or
        a hard-coded weekday assumption.
  - [ ] Run bounded timeline catch-up at process start/market open, after every
        disconnect, periodically while live, and before market-close shutdown.
        Use per-handle `since_id` watermarks and fair rotation so a noisy trader
        cannot consume all capacity before CORE/other approved handles are read.
  - [ ] Enforce a configurable daily Post-resource ceiling defaulting to the
        owner's free allowance. Reserve capacity for catch-up/reconciliation,
        stop before paid overage, expose remaining usage in health/STATE, and
        require explicit owner approval before any paid or higher-cap mode.
  - [ ] Send every accepted post through the existing archive-before-parse path;
        download/hash media before DB visibility, keep ingestion idempotent, and
        advance a watermark only after raw archive + media + DB success.
  - [ ] Implement rate-limit/backoff and reconnect behavior for 401/403/429/5xx,
        malformed payloads, half-open streams and process restarts. Never turn a
        missing timeline row into a deletion without explicit lookup evidence.
  - [ ] Bridge accepted posts to the fast entry classifier and W7 outbox. Explicit
        text entries target a cited Telegram enqueue within 60 seconds of source
        receipt. Image-dependent entries send an immediate evidence notice and
        a later vision-enriched amendment; ambiguous posts go to review.
  - [ ] Keep historical collection out of this service. Older posts enter only
        through explicitly authorised, source-backed LLM staging manifests and
        the strict archive-first importer; model output is not golden truth.
  - [ ] Disposable acceptance covers stream delivery, polling fallback, replies,
        media, duplicates, cursor non-regression, restart catch-up, daily-cap
        exhaustion, 401/403/429/5xx, market-window start/stop and Telegram outbox
        latency without sending a real message.
  - [ ] Live acceptance: at least 3 real traders across 7 market sessions; no
        missed post after forced reconnect, no duplicate alert, no paid overage,
        complete archive/hash parity, and measured receipt→outbox latency. Real
        Telegram sending remains disabled until W7 acceptance and owner enable.

- [x] **Immutable archive** — `ingest/archive.py`. Post JSON + every image written
      to `data/raw/` and `data/media/` **before** anything parses them, keyed by
      `post_id`, with a sha256 per media file. Nothing downstream may re-fetch:
      threads run for weeks and X's search window does not.
      Evidence: `test_archive_post_writes_raw_and_media_once_with_sha256` and
      `test_store_posts_archives_everything_before_any_database_insert` pass.
      The W1 check also fails if any indexed real media file is missing or its
      recomputed SHA-256 differs from the first-sight value. Media paths are
      stored relative to `data/media/`, matching the schema and API contract.
      Production evidence: 12 real post rows match 12 immutable raw files and
      all 9 indexed chart files pass SHA-256 recomputation.

- [~] **Deletion detection** — `ingest/deletions.py`. A post seen before and now
      gone gets `deleted_at` stamped; the row and its archive are **kept**.
      Traders delete losers, so dropping them silently would bias every derived
      style metric toward flattery.
      **DONE:** marking is limited to the oldest/newest posts actually returned,
      keeps rows and archives, and logs `ingest.deletions`; regression tests pass.
      **STILL OPEN:** observe a real deletion during the seven-day live done-test.

## W2 — parse (needs a strong model)

- [~] **Golden fixtures first** — build ~30 real posts with hand-verified expected
      JSON in `tests/golden/` BEFORE trusting any parser output. These also
      measure the real extraction yield, which is the project's biggest unknown.
      Twelve authenticated real posts are now archived and may seed candidate
      fixtures after field-by-field human verification; continue capture toward
      the planned ~30-example corpus. The old 59-post mock corpus was removed
      from production and remains forbidden as golden truth.
      **FIRST VERIFIED FIXTURE:** the user confirmed Manas's RATEGAIN post
      `2090713569793126757` is an entry. Its exact archived text now has a
      machine-checked classifier fixture: `trade_event`, symbol `RATEGAIN`,
      `play_type=unclear`, no stated conviction words. Event label `entry` is
      metadata only until reconciliation exists. **SECOND VERIFIED FIXTURE:**
      the user confirmed Fastzone's FCL `Sold 1/3rd` post
      `2089923284565700807` is a partial exit; its post-level fixture is
      `trade_event`, symbol `FCL`, `play_type=unclear`, with `partial_exit` kept
      as reconciliation metadata only. **STILL OPEN:** ~28 diverse hand-verified
      real examples.
- [~] **Classifier** (`cheap` tier) — post → `trade_event | breadth | watch_idea | theme | education | noise`.
      `llm/classify.py` now strictly validates the binding prompt contract and is
      the sole `post_class` writer for provider results and audited human labels.
      The verified RATEGAIN label is live in production and FEED renders it as
      `trade event`. **STILL OPEN:** batch orchestration and prompt/model accuracy
      evaluation against the completed ~30-fixture corpus.
- [ ] **Vision pass** (`vision` tier) — annotated chart → levels + structure + any
      text in the image. Exits are frequently a chart plus the word "booked".
- [ ] **Thread reconciler** (`smart` tier) — the core. Whole thread → full position
      state, re-derived in full on every change, cached on `thread_hash`.
      Never incremental: LLM state-diffing drifts within days.

## W2b — vision reads non-chart trade evidence (found during W2 review)

- [x] **`vision.md` threw away the best evidence in the corpus.** Rule 5 said
      "if the image is not a price chart... set `unreadable: true`". Read
      literally — correctly — that covers broker order confirmations, holdings
      tables and watchlists: **3 of the 9 real archived images**, one of which is
      a buy-order confirmation showing a fill price of **39.05**. A broker
      confirmation is arguably *stronger* evidence than a chart, because it is
      the trade itself rather than a picture of one. It is currently discarded by
      design, and the FCL/VCPSwing fixture records that loss in `unresolved`.
      Done 2026-08-23: `non_chart_evidence` now covers order confirmations,
      holdings, and watchlists with transcription rules distinct from
      `unreadable`. All nine archived media have human/Terra-verified vision
      JSON, and the readable non-chart evidence contract is implemented and
      tested.

## W3 — cross-thread linking

- [~] **Symbol linker** — standalone posts referencing a symbol with an open
      position ("booked XYZ +18%", no reply link to a 3-week-old entry). This is
      the accuracy ceiling of the whole tool. **Proposes** links only; anything
      under `reconcile.link_confidence_floor` (0.8) goes to `review_queue`.
      **DONE:** proposal JSON contract, queue schema, confidence-floor config,
      read API/UI shell, strict `llm/link.py`, deterministic confidence routing,
      pre-provider source/candidate gates, auditable auto-acceptance, and atomic
      accepted application through sole-writer `llm/reconcile.py` now exist.
      Focused W3/reconcile suite: 45 passed; whole suite: 148 passed on
      2026-08-23. **STILL OPEN:** production invocation — nothing schedules or
      calls the linker pass yet; wiring belongs to the W2 parse orchestration,
      which is not built.
- [x] **W3 runtime producer / batch orchestration** — select only eligible
      classified standalone trade-event posts, invoke the existing proposal
      route, and prove no duplicate reviews/events on a second run. This is the
      missing end-to-end linker path; without it, production correctly remains
      at zero review rows even though the backend and review UI are present.
      (2026-08-23) `run_link_pass` in `llm/link.py` implements it: coarse SQL
      eligibility (classified `trade_event`, standalone, backs no
      `position_events` row, no `link_event` review row in ANY status) plus the
      existing fine gates (`_symbols`, `_candidate_positions`), then
      `propose_link` → `route_link_proposal` per post. Idempotency is
      structural — processed posts are excluded by the filter itself, so a
      second pass makes zero provider calls and zero writes; rejected posts are
      never re-queued; per-post errors are isolated in
      `LinkPassResult.failures` and the pass never raises. Evidence: 11
      disposable-database tests in `tests/test_link_pass.py`; focused suite 61
      passed; whole suite 171 passed; `run_checks.py` exit 0 including the
      attribution check. Browser-test teardown also hardened (server thread
      joined, loud failure) against the audit's unproven flake. See
      `design/handoffs/HANDOFF_W3_producer_COMPLETED.md`. **Boundary:** this is
      a library entrypoint — no production pipeline invokes it yet; production
      stays at zero review rows (correctly: the corpus currently has zero
      eligible posts).
- [x] **Review queue wired to the UI** so a human can resolve in one click.
      (2026-08-23, GLM 5.3 via ZCode — continuation slice, browser tests, and
      close-out; backend acceptance from the prior session's W3 close.)
      FEED renders open items with accept/reject actions; backend
      acceptance applies atomically and idempotently through the sole writer
      and rejection never mutates the position. After a decision, FEED
      refreshes the review list, the posts (accepted standalone events appear
      via the `/api/feed` event join), and the health-derived badge in the same
      session — no reload. Decisions are single-item with disabled/`aria-busy`
      pending state and inline error feedback; a held-response double click
      submits exactly one POST; no bulk accept. Cold-load favicon 404 fixed
      with an inline SVG data URI. Evidence: 5 disposable-database browser
      tests in `tests/test_browser_review.py` (accept flow, reject flow,
      double-click guard, clean cold load, 375×812 no overflow); whole suite
      153 passed; `run_checks.py` exit 0; orchestrator re-verified in a real
      browser including a post-accept hard reload. See
      `design/handoffs/HANDOFF_W3_link_COMPLETED.md`.

## W4 — breadth + XP/MBI

- [x] **Complete and root-accepted (2026-08-23).** Adopted bhavcopy, raw and
      NIFTYMIDSML400 breadth, XP, and MBI produce 446 matching daily date sets
      from 467 source dates and 1,327,505 `daily_prices` rows; XP/z/MBI fields
      are non-null. Canonical index breadth enforces 85% actual-date coverage
      (340/400), rejects `DATE1` mismatches, and blocks downstream derivation at
      failed stage boundaries. The derive check requires five-date breadth/regime
      parity plus non-null XP/MBI and honestly reports `stale_9d`.
      `universe_breadth.py` and the constituents CSV remain required because XP
      is calibrated on that universe; breadth-ratio/HL analytics are deferred
      without a named consumer. Root's acceptance used real API/DB data at
      1920×1080 with document width 1920, zero panel overflows, no long decimals,
      and `Trend: 90 points, latest 7.3 (low).` in the BandLine aria label. See
      `design/handoffs/HANDOFF_W4_breadth_COMPLETED.md`.

## W5 — volume reverse-engineering

- [ ] Adopt `alpha/activity.py` (Reactor Scale) + `alpha/schema.py` +
      `engine/universe_filter.py`.
      **`Assumption:` this is what "the volume based reverse engineer" refers to.**
      It is the only manas_os module that is both purely volume/delivery-derived
      and explicitly a reverse-engineering exercise. If wrong, the alternates are
      `up_day_persistence` / `ema10_respect` / `base_symmetry` in
      `manas_os/scanner/discovery_metrics.py:249-473`. Confirm before starting.

## W6 — derived intelligence

- [ ] **Trader style profiles** — hold-time distribution, stated-exit win rate,
      average R, sector tilt, entry-type mix, and stop discipline (stated vs honored).
- [ ] **Practice-vs-preach** — link `edu_items` to `position_events` by topic,
      score adherence.

## W7 — Telegram

- [ ] Adopt the transactional outbox; digests + high-confidence event pushes.
      Starts in `dry_run`, same as Manas OS.

## W8 — local LLM

- [ ] Ollama backend behind `provider.py`. Done-test: golden fixtures still green
      on the local model. `llm_runs` shows the cost delta.

## W9 — attention engine + heatmap

Spec: `design/ATTENTION_ENGINE.md`. Depends on W2, W4, W5, W6 — every input is
missing until those land. Do not start early.

- [ ] **`derive/attention.py`** → `symbol_attention`. Weighted event sum where an
      entry WITH a stated stop counts ~6x a bare mention. Talk and money must
      never be summed into one count.
- [ ] **The freshness decay is the point, not a detail.** Score must fall with
      sessions since first mention (1.00 at 0-2d → 0.10 at 16d+). Eight traders
      over three weeks must rank BELOW three traders inside two sessions. A
      version where attention monotonically increases the score is a machine for
      buying crowded tops — reject it in review.
- [ ] Herding discount: echo posts inside a 24h window carrying no new level and
      no entry count 0.6, not 1.0. Six mentions can be one idea and five echoes.
- [ ] `regime_mult` from `regime_daily` — bad breadth DAMPENS (0.35 on a RED
      warning day), never zeroes. A leader emerging in a bad tape is information.
- [ ] `activity_mult` from `alpha_activity_signals` — the only input not derived
      from what people said, and the highest-value term in the formula.
- [ ] Negative signals surfaced as an explicit `caution` flag, not netted away:
      cluster exits, deleted entry posts, stop violations.
- [ ] HEATMAP screen: ECharts treemap + ranked table + per-row "why" drill-down
      showing every multiplier. The old `squarifyTreemap` idiom in
      `manas_os/desk/src/viz.js` is algorithmic reference only; new visualization
      work follows the renderer ladder in `design/VISUAL_LANGUAGE.md`.

## W10 — does the signal actually work?

- [ ] **`derive/attention_validate.py`** — forward return at +5/+10/+20 sessions
      vs NIFTYMIDSML400 median, bucketed by score decile, over every historical
      cluster.
- [ ] **Ship criterion: top decile beats universe median at +10d across ≥60
      clusters.** Until it passes, the HEATMAP ranks by raw attention and states
      on screen that priority is unproven. An unvalidated prioritisation number
      is worse than none, because it will be trusted.
- [ ] "Is this signal real?" panel showing the current validation result,
      including when it fails.

---

# COMPLETED

- [x] **W0 — the frame + UI shell** (2026-08-23). Governance docs
      (`CANONICAL.md`, `AGENTS.md`, `HANDOFF.md`, `DECISIONS.md`, `CONTRACTS.md`,
      `WIREFRAMES.md`), `db/schema.sql` + `db/__init__.py` with the prod-DB test
      guard, `llm/provider.py` with tier routing and the `llm_runs` cost ledger,
      the `checks/` harness writing `STATE.json`, mock seed data, and the six-screen
      UI rendering end-to-end against a real SQLite DB.
      Evidence: see `HANDOFF.md` for the verification output.

---

# DROPPED / DEFERRED BY DECISION

Recorded so nothing disappears silently. Reverse any of these by saying so.

- **W4 breadth ratio/HL-logic analytics** (`manas_os/regime/breadth_analytics.py`)
  — deferred 2026-08-23. It had no named TraderLog API/UI consumer, so retaining
  the adopted module would violate the no-dormant-code rule. Revisit only with a
  specified payload and screen element.

- **X email/bell notifications as the ingest trigger** — dropped 2026-08-22.
  A trader's replies to their own posts do not fire bell notifications, and adds,
  stop moves and exits are almost always self-replies. The notification stream
  structurally cannot see the most important events. Replaced by timeline-with-
  replies polling.
- **Incremental LLM state updates** — dropped at design time. Full thread
  re-derivation on every change is idempotent and cheap; incremental diffing
  drifts and cannot be tested against fixtures.
- **Inbound Telegram bot** (resolving review items by replying to a message) —
  deferred. Needs a webhook receiver that exists in neither project. Review
  resolution happens in the UI for now; the Telegram nudge links into it.
- **Official X API v2 — required production path.** X rejects the automated
  Chromium login needed by the current Playwright route. Use an app-only Bearer
  Token stored as a deployment secret, never source/DB/browser cookies. Poll
  a filtered stream during configured market hours when available, with
  `GET /2/users/{id}/tweets` and per-handle `since_id` watermarks as startup,
  reconnect, periodic and shutdown catch-up. If streaming is unavailable on the
  entitlement, use 30–60 second timeline polling. Production retrieves only
  unseen live posts; it does not use the X API for historical backfill. Keep the
  existing archive-first, hash, idempotency and source-citation gates unchanged.

- **Instant Telegram entry path.** Archive and index source evidence first. For
  explicit text entries, run the bounded fast classifier and enqueue a cited
  Telegram alert immediately; target at most 60 seconds after receipt. For
  image-dependent entries, send an immediate “new entry evidence” notice with
  the source link, then amend it after vision extraction rather than inventing
  unread prices. Ambiguous posts go to review and must not masquerade as a
  confirmed entry. Telegram sending remains disabled until W7 acceptance and
  explicit owner enablement.

---

# USER-SIDE ONLY

- [ ] Create an X developer app in the normal user browser, configure the
      available free daily Post-read allowance and a hard no-overage cap, and
      place its app-only Bearer Token in the deployment secret store. Do not
      paste it into chat, source, config committed to git, SQLite, logs, or a
      browser profile. Paid credits/streaming require separate owner approval. A
      Playwright-profile login is no longer a production prerequisite.
- [x] Fetcher account: secondary, chosen by the user on 2026-08-23. This route
      risks suspension; stop on any account warning or challenge.
- [ ] Confirm the W5 assumption about which module is "the volume reverse engineer".
- [~] Approve the initial source universe. No proposed handle becomes active
      until the user approves it. **ACTIVE STARTER LIVE SET:** `@iManasArora`,
      `@Fastzonetrader`, `@tradinghustlr`, `@VCPSwing`. **APPROVED, CAPTURE
      AUTHORISED 2026-08-23 (all eight handles):** `@StocksNerd`, `@ChartistEdge`,
      `@iArpanK`, `@mystocks_in` (first capture + atomic activation authorised;
      awaiting the fresh Chrome-extension checkpoint; strict importer ready).
      **SUPERSEDED PROPOSALS / INACTIVE:** `@wetradecharts`, `@afzal_57`.
      `@iManasArora` is user-confirmed CORE: his best trade logs combine an entry
      post, self-reply updates, explanations, and chart images, so public search
      snippets are not an adequate quality test. The user authorized direct work
      on supplied accounts' recent posts; the original four are active in the
      production database for the initial 30-day backfill. Activate each newly
      approved handle atomically with its first real capture so empty rows do
      not fail the freshness gate. **STILL OPEN:** first capture for the four
      newly approved handles and the continuous live acceptance evidence.
- [x] Dummy-data scope, superseded: the user initially authorized mock rows for
      W1 mechanics/UI work, then explicitly ordered their removal from production
      on 2026-08-23 after real capture landed. Production is real-data-only.
      `seed_mock.py` is retained solely for disposable test/demo databases;
      dummy evidence never closes live W1 or seeds W2 golden truth.
- [ ] Telegram bot token + chat id, when W7 is reached.
