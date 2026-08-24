# HANDOFF — where the next session picks up

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.

---

## To continue

**Wave: Scouting × Wire redesign is COMPLETE (2026-08-24), uncommitted.**
The fourth visual direction (`design/REDESIGN_SCOUTING_WIRE.md`,
owner-approved) is built in full: the docs above it
(`VISUAL_LANGUAGE.md` §1/§1a/§3 superseded; `WIREFRAMES.md` rewritten;
`CONTRACTS.md` §8 extended) were reconciled in the same change. See
`design/handoffs/HANDOFF_scouting_wire_2026-08-24_COMPLETED.md` for the
full evidence list. Baseline before this wave: checks exit 0, 264 tests.
After: checks exit 0 (incl. `golden`, which runs the whole suite), **283
tests pass**, Vite build clean, and the orchestrator's live 1920×1080
production-API probe passed on all seven routes (grid 1680@x=120, zero
overflow, zero console/≥400 errors, bands in fixed order, `--risk` scoped
to Money-moved rows, Market zero-risk with no caution block, ⌘K
navigates, Symbol page renders candles for a validated symbol). Nothing
committed — the maintainer QCs and commits one wave per commit.

**XP (C8) is FIXED and production-recomputed** — do not re-open it without
evidence. Percent convention restored, z reseeds from observed up_4pct,
`backfill` warm-ups 20 sessions (transient discarded, not presented).
Production regime_daily: 431 rows, 0 cap hits, 0 EXTREME, max 81.31,
bands LOW 349/BUILDING 67/STRONG 15, latest-5 parity True. Pre-change
backup: `data/traderlog.db.backup-pre-xpfix-20260824`. Because XP is
fixed, MARKET renders without the §8 caution block by design — re-add it
only if the derivation regresses.

**Known honest gaps (by design, not defects):** the Removed band on TODAY
waits for a real deletion (0 rows today; lifecycle covered by a
disposable-DB browser test); Today's record glosses wait for
`trader_style` ≥10 closed positions (W6); `trader_style` is still empty,
so TRADERS honestly shows "— too few" everywhere; `edu_items` is empty,
so LIBRARY shows its truthful compact empty states.

> ## ⚠ STOP — READ BEFORE EDITING ANY UI FILE
>
> **W3c is COMPLETE and committed. Do NOT execute
> `HANDOFF_W3c_pc_ui_recovery.md`.** Until 2026-08-23 this file told you to
> execute it next; that was stale and contradicted
> `HANDOFF_W3c_pc_ui_recovery_COMPLETED.md`, which was true. All four W3c
> done-tests verify against the working tree today: `NAV_TABS` excludes STYLE,
> `--fs-body` is 14px, the content grid is a centred 1680px, and `thread.css`
> exists.
>
> **Any copy of these files taken before `73457232` is STALE.** Writing a stale
> copy back silently destroys work that no merge will warn you about. Note the
> 2026-08-24 redesign renamed the screens: `Feed.jsx` → `Today.jsx`,
> `Breadth.jsx` → `Market.jsx` (see `design/REDESIGN_SCOUTING_WIRE.md`):
>
> | File | What lives there now |
> |---|---|
> | `ui/src/App.jsx` | `navigate(tab, params)` + `navParams` — powers every cross-screen link; NAV_TABS TODAY/LEDGER/TRADERS/IDEAS/LIBRARY/MARKET |
> | `ui/src/components/ui.jsx` | `Disclosure`, `Segmented`, `SortableTh`, `Bar` aria-label, `Stat` |
> | `ui/src/screens/Today.jsx` | was Feed.jsx: computed bands, review queue, filters, ⌘K targets |
> | `ui/src/screens/Market.jsx` | was Breadth.jsx: quiet hero, ribbon, cumulative A/D |
> | `ui/src/styles/app.css` | scouting tokens in `tokens.css`; screen styles in per-screen css files |
> | `ui/src/styles/tokens.css` | dark scouting token layer (2026-08-24) — the only colour literals |
>
> `git pull`/`git status` before touching any of them. If your brief predates
> `73457232` or `b625ada7`, re-read the files on disk rather than trusting your
> copy.

**Next: execute the evidence-desk UI handoff.** The existing Manas/Fastzone
corpus is exposed in production and Feed pagination now reaches all 202 posts
without duplicate rows; unknown ancestry is labelled rather than presented as
a root. Execute
`design/handoffs/HANDOFF_UI_evidence_desk_completion_2026-08-23.md`. T2
extraction-yield measurement remains the next data pipeline step, but run the
classifier only when authorised by the owner; record usable `kind`, `symbols`,
and `play_type` yield and never promote model output to golden truth. New X
profile pulls remain paused.

**Owner direction, amended 2026-08-23:** expose the already-captured Manas Arora
and Fast Zone Trader records from the authenticated DOM checkpoint to the tool.
This permission does not resume new profile pulls and does not authorise the
staged Trading Hustler records. Import only records with source identity and
usable post text or archived media. Preserve missing reply ancestry as
unresolved/null rather than synthesising roots or parents. Current verified
staging counts are 90 Manas records and 128 Fastzone records before validation;
the earlier in-window figures were 58 and 117. Checkpoint SHA-256:
`5F03A7D1E41EA1C016D2E2CC814DC63D24EED78E580BD6C27138BE6C5BCF7F5C`.

**Owner direction, amended again 2026-08-23 (supersedes the exclusions above):**
the owner directed capture/ingest of posts AND replies for all eight roster
handles — the four active (`@iManasArora`, `@Fastzonetrader`, `@tradinghustlr`,
`@VCPSwing`) plus the four pending (`@StocksNerd`, `@ChartistEdge`, `@iArpanK`,
`@mystocks_in`) — via the authenticated Chrome route. This un-pauses the staged
`@tradinghustlr` records (175 in the W1b checkpoint file) and authorises first
capture + atomic activation for the four pending handles. Mechanism decision
(2026-08-23): fresh Chrome-extension checkpoint, same format and strict
validator as the W1b provisional import; the Playwright profile route stays
available but was not chosen. Missing reply ancestry remains unresolved; never
synthesise roots or parents. Pre-change backup:
`data/traderlog.db.backup-pre-8handle-20260823`.

**Owner direction, expanded 2026-08-23 (six more handles):** the owner
approved `@rpmrpm4`, `@thechartist26`, `@SakatasHomma`, `@Trading4Bucks`,
`@wealthexpress21`, `@Setups_Swing` for roster + first capture, for the
"strong stocks + market breadth + situational awareness" coverage (breadth/
watch_idea/theme/education kinds). Exact casing above is the roster spelling.
Capture mechanism: the DevTools route (separate Chrome user-data-dir copy with
a debugging port; owner logs in once; read-only capture of posts + replies
tabs; strict provisional import). More handles may follow ("among others").

**Owner direction, expanded again 2026-08-24 (three breadth-candidate handles,
owner-approved after discovery screening):** `@investor_sr33`, `@multibaggerwala`,
`@AdeptMarket` join the roster for first capture (discovered via the
"market breadth Nifty trader" search; the screen scored them 0/0 under
concurrent throttling, so their first real capture doubles as the validation —
duds will be reported honestly and dropped). Roster total: 17 approved.

Production live-ingest correction (2026-08-23): X does not permit the required
login in Playwright's automated Chromium, so neither that profile nor copied
Chrome cookies may be a go-live dependency. Keep Chrome-extension checkpoints
as manual bootstrap/recovery only. The production target is an official X API
v2 app-only Bearer Token adapter behind `fetch_timeline(handle, since)`.
**Owner correction:** ingestion must stay live throughout configured market
hours for immediate Telegram entry updates. Prefer a filtered stream with
`from:` rules for the approved roster when the entitlement supports it; otherwise
poll each public user timeline every 30–60 seconds. Timeline catch-up runs at
market-open, after reconnects, periodically while live, and before shutdown.
Production retrieves only posts newer than each handle's last successful
watermark and does not use the X API for historical backfill. Preserve replies and request
`conversation_id`, `referenced_tweets`, attachments/media expansions, and
created time. Advance a per-handle `since_id` only after archive + media + DB
success. Historical coverage is instead produced by explicitly authorised LLM
backfill work from source evidence into a staged manifest, then passed through
the same strict validator/archive-first importer and human review. Model output
is never golden truth and may not invent text, ancestry, prices, symbols or
events. Paid API usage requires a new owner instruction. Official source:
`https://docs.x.com/x-api/users/get-posts`.

W1b production exposure (2026-08-23): the approved checkpoint yielded 197
eligible records; 21 were excluded (2 pinned, 19 empty/no-media), 7 already
existed, and 190 were newly archived/indexed with 106 new media files. The
production database now contains 202 real posts and 115 media rows: 84 Manas,
113 Fastzone, 3 VCPSwing, and 2 Trading Hustler. Independent verification found
zero mock posts/media, zero missing or malformed raw archives, zero missing
media files, zero SHA-256 mismatches, and `PRAGMA integrity_check = ok`. The
pre-import database is recoverable at
`data/traderlog.db.backup-pre-w1b-20260823`. Only proved source relationships
were stored; the corpus does not repair the broader reply-ancestry gap.

Feed exposure verification (2026-08-23): `/api/feed` now pages a deterministic
30-row base window with total/offset metadata and thread-root context that does
not advance the cursor. The live 1920×1080 instance loaded
30 → 60 → 90 → 120 → 150 → 180 → 202, ending with 202 unique status URLs,
189 explicitly unknown relationships, zero horizontal overflow, and no
console, request, or HTTP errors. The evidence-desk visual completion remains a
separate handoff; pagination does not claim that redesign is implemented.

Production holds three real cited positions and `check_parse` passes. All
nine archived media have human/Terra-verified vision JSON; the readable
non-chart evidence contract is implemented and tested. The VCPSwing FCL position
uses the successful 2026-08-06 buy order as its entry at 39.05. Manas's RATEGAIN
holding row supplies `size_note` 4,300 shares; its cropped headers are retained
as a caveat. Fastzone FCL still has no entry: 45.68 and 45.75 are current
prices, not stated trade prices.

**Parallel work boundary (2026-08-23):** Claude's neo-brutalist UI pass reported
complete and is under acceptance review. Preserve its six-file surface and make
only bounded, verified corrections. The visualization renderer ladder is now
binding: ECharts core, Vega-Lite custom analytics, Flint agent-generated panels,
Plotly only for deep interactive exploration; see `design/VISUAL_LANGUAGE.md`.

**Deferred, do not invent:** F14 (Library empty-state citation) — the exact
finding/scope was never supplied. The `unresolved_json` free-form-strings risk
is assessed and documented in the W3 COMPLETED handoff; if it ever blocks UI
truthfulness, spec a structured resolution field in `design/CONTRACTS.md` and
add tests BEFORE changing the proposal schema.

---

## Previous entry

**Wave:** W1 has a verified live bootstrap; **seven-day live acceptance remains open.**

Before anything else:

```bash
python traderlog/run_checks.py
```

Expect `ingest` to read `pass` while at least 80% of the four approved traders
have a real capture fetched within 24 hours. The W1 implementation and 59
deterministic tests are complete; see
`design/handoffs/HANDOFF_W1_ingest_COMPLETED.md`.

To close W1 live acceptance:

1. Create an X developer app in the normal user browser and store its app-only
   Bearer Token as a deployment secret; never copy user-session cookies.
2. Implement and test the official X API adapter behind the existing
   `fetch_timeline(handle, since)` contract. Keep it live for seven market
   sessions using filtered stream when entitled or 30–60 second timeline polling
   otherwise, with startup/reconnect/periodic/shutdown catch-up. Do not run an
   API historical backfill; older data enters only through the separate
   source-backed LLM staging/import workflow.
3. Observe at least three real traders throughout that period and one real
   deletion without losing its row or archive.
4. Prove restart/gap recovery, rate-limit backoff, cursor non-regression,
   archive-before-parse ordering, media hashing, and idempotent replay against a
   disposable database before enabling the production scheduler.
5. Re-run `python traderlog/run_checks.py`; ingest must read `pass` or an honest
   `stale_Nd`, never `not_built_yet`.

Live bootstrap (2026-08-23): the user enabled the ChatGPT Chrome extension for
their authenticated secondary X session. Read-only permalink inspection captured
12 real posts across all four approved traders and nine chart files. A strict
`ingest/chrome_import.py` validator rejects unapproved handles, incoherent reply
ancestry, wrong status/media URLs, and malformed timestamps before archive or DB
writes. That first bootstrap had 4 Manas posts, 3 Fastzone posts, 2 Trading
Hustler posts, and 3 VCPSwing posts. Raw-file parity was 12/12 and all nine media
SHA-256 values recomputed. W1b subsequently expanded only the approved
Manas/Fastzone evidence as recorded above. The immutable first source manifest is
`data/raw/chrome_manifests/2026-08-23_approved_live_sample.json`; a SQLite backup
exists at `data/traderlog.db.backup-pre-chrome-20260823`. This authenticated DOM
bootstrap is real evidence, but it is not a substitute for the continuous
Playwright/GraphQL seven-day done-test.

Locked user decisions (2026-08-23): secondary X account; 30-day initial
backfill; India/NSE-only source universe; no handle activated before explicit
user approval. The original six-account starter target was expanded when the
user supplied and approved four additional handles on 2026-08-23. If candidate
research needs authenticated X search or browser-cookie access, ask separately.

Roster approval gate (2026-08-23): the user approved `@iManasArora`,
`@Fastzonetrader`, `@tradinghustlr`, and `@VCPSwing` as the starter live set and
asked ingest work to proceed directly from their recent posts. These four are
active in the production TraderLog database for the initial 30-day backfill;
`@iManasArora` is CORE and the other three use WATCH. The user subsequently
approved `@StocksNerd`, `@ChartistEdge`, `@iArpanK`, and `@mystocks_in` for the
source universe. Their exact live profiles were verified in authenticated
Chrome; they remain inactive only until first capture can land atomically with
activation, so the freshness gate is not made falsely red by empty roster rows.
The earlier proposals `@wetradecharts` and `@afzal_57` are superseded and remain
deferred/inactive.

User-confirmed roster priority: `@iManasArora` is the CORE reference and has the
best trading logs and trade explanations in the set. His lifecycle is commonly
split across replies to the original entry post and chart images. Thin public
search indexing is therefore not negative evidence. Live acceptance must prove
that his entry post, self-reply chain, `conversation_id`/`in_reply_to`, and every
chart image are captured together before W1 can close.

Competing capture note (2026-08-23): while the manual login profile remained
open, a separate clean headless profile attempted all four approved handles.
Every timeline returned no readable `UserTweetsAndReplies` GraphQL payload;
`pipeline_runs` records `fail`, zero rows, and four per-handle errors. No post was
written. Public search/mirror pages exposed only incomplete or internally stale
snippets, so they were not inserted into the canonical archive. Configuration
was restored to the dedicated secondary-account profile.

Dummy-data boundary, superseded (2026-08-23): the user initially authorized
dummy data while authenticated capture was unavailable, then explicitly ordered
all mock rows removed after live capture succeeded. Production
`data/traderlog.db` is now real-data-only. `seed_mock.py` remains test/demo
machinery for explicitly isolated disposable databases; never run it against
production. Synthetic evidence cannot close live acceptance or become W2 golden
parsing truth.

Data-independent hardening (2026-08-23): `check_ingest` now verifies every real
`post_media` path exists and stream-recomputes its SHA-256 before freshness can
pass. Regression tests prove a deleted or altered chart fails the W1 gate. This
closes an integrity gap without requiring or fabricating an X data pull.

Final no-pull hardening (2026-08-23): timeline pagination no longer treats an
old pinned post as proof that the requested cutoff was reached; it stops only
after three stagnant filtered pages (with a 50-scroll safety bound). HTTP and
GraphQL errors, unreadable payloads, and payloads without the requested author
fail conservatively. Successful observations advance (but never regress) each
trader's `last_seen_ts`. The default media downloader accepts HTTPS only from
X's exact media hosts and rejects redirects, credentials, custom ports, local
files, and arbitrary hosts. `post_media.local_path` is now relative to
`data/media/`, matching the schema and API media-path contract.

W2 may now curate candidate golden fixtures from these real archived posts, but
must hand-verify every expected field and should grow the corpus toward the
planned ~30 examples. Mock rows remain forbidden as golden parsing truth.

W2 first verified classification (2026-08-23): the user confirmed Manas's
RATEGAIN `#NewPosition` post `2090713569793126757` is an entry. Investigation
proved it had never been classified: `posts` contained the real row, while
`post_class`, `position_events`, and parse-run history were empty for it. The
new binding-prompt-backed `llm/classify.py` is now the sole `post_class` writer,
and the exact archived post is fixture 1 of the planned ~30. Production stores
the audited human label as `trade_event`, confidence `1.0`, symbol `RATEGAIN`,
`play_type=unclear`, with no conviction words. FEED now renders `trade event`
instead of `unclassified`. The user's more specific `entry` label is retained
as fixture metadata only; no position or event row was fabricated before the
thread reconciler exists. A SQLite-consistent pre-change backup is
`data/traderlog.db.backup-pre-w2-rategain-20260823`.

W2 second verified classification (2026-08-23): the user identified Fastzone's
FCL `Sold 1/3rd` post `2089923284565700807` as another missed event. Its exact
archived text is fixture 2; production stores `trade_event`, confidence `1.0`,
symbol `FCL`, `play_type=unclear`, and no conviction words. The more specific
`partial_exit` label is fixture metadata for the future reconciler; positions
and events remain empty rather than being fabricated early.

W2 readiness is intentionally still open. Verification exposed and fixed two
false-green checks: one fixture no longer completes the planned ~30-fixture
golden corpus, and seven mock-only positions no longer count as real parsing.
Golden reports `2/30 fixtures verified`; parse remains `not_built_yet` until at
least one real position is reconciled with the evidence invariants intact.

---

## Log

### 2026-08-23 — W3 runtime producer built and verified (GLM 5.3 via ZCode orchestration + unnamed implementation subagent)

Answered the audit's Action 1 (`HANDOFF_W3_link_AUDIT_FEEDBACK.md`):
`run_link_pass` in `llm/link.py` selects eligible classified standalone
trade-event posts (backs no event, no `link_event` review row in ANY status,
non-empty symbols, at least one same-handle/symbol open-like candidate) and
runs each through the existing `propose_link` → `route_link_proposal` path.
Idempotency is structural: a second pass makes zero provider calls and zero
writes; rejected posts are never re-queued; per-post errors are isolated and
the pass never raises. Implementation by an unnamed ZCode subagent (executor
ledger record `attr-w3-producer-unknown-executor-20260823-001`); orchestration
and personal verification by GLM 5.3. Browser-test teardown hardened against
the audit's unproven flake (server thread joined, loud failure). Verified:
focused 61 passed, browser suite 5 passed twice consecutively, whole suite 171
passed, `run_checks.py` exit 0 with the attribution check green. Boundary kept
honest: the producer is a library entrypoint with no production caller; wiring
belongs to the future W2 parse orchestration. Attribution per
`design/MODEL_ATTRIBUTION.md`: separate executor and orchestrator records in
`design/MODEL_WORK_LOG.jsonl`; see
`design/handoffs/HANDOFF_W3_producer_COMPLETED.md`.

### 2026-08-23 — W3 review UI complete; linker orchestration remains open (GLM 5.3 via ZCode + subagent)

Closed the W3 continuation slice. The continuation shipped in-session refresh after
review decisions (review list + posts event join + health badge, no reload),
single-item decisions with disabled/`aria-busy`/inline-error feedback, a
held-response double-click guard proving exactly one POST, a data-URI favicon
that removes the cold-load 404, and five disposable-database browser acceptance
tests in `tests/test_browser_review.py`. Production DB untouched throughout.
Orchestrator personally re-verified everything: focused suite 50 passed, whole
suite 153 passed, `npm run build` clean, `run_checks.py` exit 0,
`git diff --check` clean, real-browser inspection with zero console/page
errors, zero >=400 responses, zero favicon requests, 0px overflow at 375×812,
and a post-accept hard reload showing an empty review queue with both event
strips present. Two verification catches worth recording: the implementation
subagent falsely claimed it had not edited `App.jsx` (it had — edit correct,
report wrong), and a small-model vision read of the mobile screenshot
hallucinated a reappeared review queue (disproven by the reload probe and the
`accepted` row in the disposable DB). Nothing committed.

**Correction added by the W3 audit:** the continuation is complete, but the
overall W3 runtime producer/batch orchestration does not yet invoke the linker
for eligible canonical posts. Do not read the preceding log entry as an
end-to-end linker completion. Provenance and feedback:
`design/MODEL_ATTRIBUTION.md` and
`design/handoffs/HANDOFF_W3_link_AUDIT_FEEDBACK.md`.

### 2026-08-23 — W2b non-chart vision evidence + production reconciliation (Codex + Terra)

Completed W2b. All 9/9 archived media now have human/Terra-verified vision JSON,
including the readable non-chart evidence contract and its tests. The three real
cited positions are now in production. VCPSwing FCL records entry 39.05 on
2026-08-06 from the successful buy-order image. Manas RATEGAIN records
`size_note` 4,300 shares from the holding row; the image headers are cropped, so
its displayed average cannot establish the constituent purchases. Fastzone FCL
still has no entry: 45.68 and 45.75 are visible current prices only, not trader-
stated entry prices. W3 cross-thread linking is next.

### 2026-08-23 — production mock purge + Fastzone FCL fixture (Codex + Terra)

The user made production real-data-only and identified Fastzone's FCL sale as a
partial exit. A preflight audit found 59 legacy mock `post_class` rows wrongly
flagged `is_mock=0`; `seed_mock.add_post` had omitted the flag. The clear path is
now transactional, covers all 15 mock-capable tables, follows child-to-parent
foreign-key order, and also deletes legacy rows by mock parent provenance.
Production was backed up to
`data/traderlog.db.backup-pre-mock-purge-20260823`, then 268 mock-provenance rows
were removed. Preserved state: four real traders, 12 real posts, nine real media
rows/files, and the verified RATEGAIN classification. Added the verified FCL
classification, leaving two real `post_class` rows and zero positions/events.
SQLite `foreign_key_check` is empty; the API and rendered FEED report no mock
data, 12 posts, and FCL as `trade event` at `1.00`.

### 2026-08-23 — first human-verified real classification (Codex + Terra)

Root-cause tracing showed W1 had captured Manas's RATEGAIN evidence correctly,
but no W2 classifier had run. Added the strict classifier writer, direct golden
fixture, and regression tests. Primary review caught a shortened-prompt defect
in the first implementation before production; the corrected classifier loads
the complete binding `llm/prompts/classify.md`. The verified production row and
the rendered FEED both report `trade event`; positions/events remain untouched.

### 2026-08-23 — authenticated Chrome live bootstrap (Codex + Terra)

Connected read-only to the user's authenticated Chrome session and verified the
four approved X profiles directly. Imported 12 source-backed real posts and nine
charts through a strict archive-first Chrome manifest importer. The sample
includes Manas's RATEGAIN entry/explanation chain, Fastzone's FCL management
thread, Trading Hustler's breakout reply, and a three-post VCPSwing FCL
self-reply lifecycle. No credentials, cookies, local storage, likes, follows,
replies, posts, or DMs were read or changed.

Verified on production: 12/12 raw archives, 9/9 media files with recomputed
SHA-256, exact VCPSwing `conversation_id`/`in_reply_to`, media endpoint HTTP 200,
and `python traderlog/run_checks.py` passing ingest for 4/4 traders. The FEED
shows all live posts and media counts. At that checkpoint its banner still used
mock-only copy because mock rows coexisted; the later production purge removed
the banner without an API/UI code change. Visible reply ancestry remains an
API/UI owner gap outside W1.

### 2026-08-23 — W1 deterministic ingest implementation (Codex)

Built read-only Playwright capture against X's `/with_replies` browser GraphQL
responses, preserving exact conversation and parent-post ids. The persistent
profile is user-authenticated by hand; code performs navigation and scrolling
only. `run()` processes all active real traders, archives every new post and
media file before any DB insert, deduplicates by `post_id`, uses the configured
jittered cadence, logs pipeline outcomes, and never raises outward.

Deletion marking is conservative: only holes between the oldest and newest posts
actually returned by a successful fetch are eligible. Rows and immutable
archives remain; only `deleted_at` changes. The ingest check now verifies every
real post archive and the 80%/24h freshness rule.

Historical checkpoint before the authenticated Chrome bootstrap:

```
pytest traderlog/tests -q            -> 35 passed
python -m compileall -q traderlog/ingest traderlog/checks -> exit 0
python traderlog/run_checks.py       -> exit 1; ingest fails honestly, no real posts
```

At that deterministic checkpoint, live markup reliability, a seven-day run, a
real deletion, and a self-reply in FEED were unverified. The authenticated live
bootstrap logged above supersedes the old no-corpus state; continuous
Playwright/GraphQL observation and visible FEED threading remain open.

The user also supplied binding `design/VISUAL_LANGUAGE.md`; the workflow,
canonical map, wireframes, and decision index now point to it. W1 made no screen
changes.

### 2026-08-23 — W0, the frame and the UI shell (Claude Opus 5)

Built the scaffolding that lets a different model continue this project each
session without re-deriving the repo.

**Governance.** `CANONICAL.md` (repo map — which DB is live and which three are
decoys, which of five frontends is served, single-writer-per-table, what is
adopted from Manas OS and what is deliberately left behind), `AGENTS.md`
(read-first chain), `TASKS.md` (wave backlog with a DROPPED section),
`design/DECISIONS.md` (dated locked-decision index), `design/AUDIT_LEDGER.md`
(W0 self-audit: 0 critical, 1 important, 3 verified-good).

**Contracts.** `db/schema.sql`, `db/__init__.py` with the production-DB test
guard adopted from Manas OS, `design/CONTRACTS.md`, `design/WIREFRAMES.md`.

**Runtime.** `llm/provider.py` with tier routing and per-call cost logging,
`checks/` harness writing `STATE.json`, mock seed data, the six-screen UI.

**Verified, not assumed:**

```
python traderlog/run_checks.py     -> exit 0
  db      OK  23 tables
  parse   OK  7 positions, all cited        <- the evidence invariant, on mock data
  ui      OK  6 screens, dist present
  ingest / golden / derive  not_built_yet   <- W1 / W2 / W4 own these
npm run build (traderlog/ui)       -> 40 modules, 172 kB, no errors
API on :8100                       -> all 11 endpoints 200
```

All six screens opened in a browser against the real SQLite database and read
back element-by-element against `design/WIREFRAMES.md`. Three defects found and
fixed in the same pass: `—%` rendering where a win rate was null (no data and a
genuine zero must not look alike), "1 ITEMS" pluralisation, and a `regime` field
that returned a tuple instead of null when a date had no breadth row.

**Two environment facts that will waste your time otherwise:**
- This machine's python runs with `safe_path` on and **ignores `PYTHONPATH`**, so
  `python -m traderlog.checks` fails on a fresh clone. Use
  `python traderlog/run_checks.py` and `python traderlog/run_api.py` — shims that
  fix sys.path, same pattern as the existing `run_manas_api.py`.
- The console here is cp1252. Keep CLI output ASCII; box-drawing and typographic
  characters mangle.

**Two design reversals during the session, both from the user:**

- *XP/MBI adopted after all.* Originally excluded. On inspection both are
  reverse-engineered practitioner constructs and pure functions over a
  `breadth_daily` row (~225 lines, `math` only). Taken; the surrounding governor
  layer (pillars, market_mode, quadrant, four_phase, choppy_brake) is not — that
  gates the user's own trades, which is outside what this tool does. See
  `DECISIONS.md` 2026-08-23 for the two constraints that will bite W4 (XP is a
  date-ordered recursion; its weights are calibrated on NIFTYMIDSML400).
- *Per-tier fallback chains.* Prompted by a request to use **Ox Alpha**, a
  stealth model. Stealth endpoints get renamed or withdrawn without notice, so
  each tier is an ordered list and `llm_runs.model` records which model actually
  served each call.

**Attention engine specified (not built).** `design/ATTENTION_ENGINE.md` — a
heatmap of what the trader pool is converging on, scored against breadth, sector,
play type and Reactor Scale activity. Slotted as W9/W10; every input is missing
until W2/W4/W5/W6 land, so **do not start it early**.

One piece was pulled forward into W0 deliberately: the classifier now captures
`play_type` and `conviction_words`. Adding those at W9 would have meant re-running
every historical post through an LLM to backfill them. `post_class` gained both
columns via the migration path.

That exposed a schema rule now written into `db/schema.sql`: **schema.sql may
only index columns present in its own CREATE statement.** It runs before
`_migrate_add_columns`, so an index there on a migration-added column fails on
any database that already exists. Indexes on migrated columns go in
`db/__init__.py` after the ALTERs.

**Open, carried forward:**

- `Unverified:` the OpenRouter slug for Ox Alpha — postdates this session's model
  knowledge and was deliberately not guessed. Find it with
  `curl -s https://openrouter.ai/api/v1/models`, put it first in the `smart` and
  `vision` chains in `config.yaml`. No code change needed.
- `Assumption:` "the volume based reverse engineer" = `manas_os/alpha/activity.py`
  (Reactor Scale). Affects W5 only. Alternates named in `TASKS.md` if wrong.
- Extraction yield on real posts is the project's largest unknown and stays
  unknown until W2's golden fixtures exist. Measure it before building anything
  on top of the reconciler.
