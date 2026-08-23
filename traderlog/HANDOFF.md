# HANDOFF — where the next session picks up

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.

---

## To continue

**Wave:** W0 · W1 · W2 · design wave all landed. **W3 (cross-thread linking) is
next**, with **W2b (vision non-chart evidence) queued ahead of it** if you want
the strongest evidence in the corpus recovered first.

**One decision is waiting on the repo owner, and nothing should proceed past it
silently:** three hand-verified positions exist as golden fixtures but have not
been written to the production database. A W2 agent attempted the write and was
blocked by the permission classifier; it correctly stopped rather than working
around it. Until that write happens, `check_parse` reads `not_built_yet` and the
LEDGER screen is empty — the reconciler is built and tested, but production holds
no position rows. The rows are real (hand-verified from archived post text and
images, no LLM involved), so they satisfy the real-data-only rule; the call is
still the owner's, because they deliberately purged this database.

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

1. Use a secondary X account and log in by hand once at
   `ingest.browser_profile_dir` with
   `python traderlog/run_xfetch.py --login`; no script handles credentials
   and login mode never runs ingest.
2. Run the persistent-profile fetcher for the four approved traders with the
   configured 30-day first backfill, then keep
   `python traderlog/run_xfetch.py --forever` for seven days.
3. Observe at least three real traders throughout that period and one real
   deletion without losing its row or archive.
4. Resolve the cross-wave FEED gap: the database has an exact VCPSwing
   self-reply chain, but `/api/feed` omits `conversation_id`/`in_reply_to`, so
   the current screen lists the posts without visibly threading them. W1 must
   not edit `api/` or `ui/`; route that change through the owning wave.
5. Re-run `python traderlog/run_checks.py`; ingest must read `pass` or an honest
   `stale_Nd`, never `not_built_yet`.

Live bootstrap (2026-08-23): the user enabled the ChatGPT Chrome extension for
their authenticated secondary X session. Read-only permalink inspection captured
12 real posts across all four approved traders and nine chart files. A strict
`ingest/chrome_import.py` validator rejects unapproved handles, incoherent reply
ancestry, wrong status/media URLs, and malformed timestamps before archive or DB
writes. Production now has 4 Manas posts, 3 Fastzone posts, 2 Trading Hustler
posts, and 3 VCPSwing posts. Raw-file parity is 12/12; all nine media SHA-256
values recompute; `check_ingest` passes 4/4. The immutable source manifest is
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
