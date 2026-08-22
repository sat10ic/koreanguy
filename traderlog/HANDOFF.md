# HANDOFF — where the next session picks up

Living document. **Overwrite the "To continue" block; append to the log.**
Read `STATE.json` alongside this — this file is intent, that file is fact.

---

## To continue

**Wave:** W0 complete → **W1 (ingest) is next.**

Before anything else:

```bash
python -m traderlog.checks
```

Expect W0 subsystems `pass` and W1–W7 subsystems `not_built_yet`. If anything
reads `fail`, fix that before starting new work — a wave that begins on a broken
base produces findings nobody can attribute.

**Your packet:** `traderlog/design/handoffs/HANDOFF_W1_ingest.md`. It names the
files you own, the files you must not touch, the interface contract, and the
done-test.

**W1's job**, in order:

1. `ingest/xfetch.py` — Playwright over a persistent profile directory. The
   interface is already fixed in `design/CONTRACTS.md §7`:
   `fetch_timeline(handle, since) -> list[RawPost]`. Honour it; the rest of the
   pipeline is written against that shape.
2. `ingest/archive.py` — write post JSON and every image to `data/raw/` and
   `data/media/` **before** anything parses them. sha256 per media file.
3. `ingest/deletions.py` — stamp `posts.deleted_at`, keep the row and the archive.
4. Flip the `ingest` check in `checks/__main__.py` from `not_built_yet` to a real
   assertion. **A wave that does not flip its own check leaves the harness
   decorative** — this is finding I1 in the audit ledger.

**Blocked on the user** (`TASKS.md` → USER-SIDE ONLY): logging into X by hand in
the profile directory, and deciding main vs secondary handle. W1 can be written
and unit-tested against saved HTML fixtures without this; it cannot be run live.

**Do not** start W2 (parsing) before W1 produces real posts. The golden fixtures
that W2 depends on must be built from real captured posts, not invented ones —
inventing them would bake this session's guesses about how Indian traders write
into the thing that is supposed to measure exactly that.

---

## Log

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
