# HANDOFF W1 — ingest

**For the model picking this up.** Read `traderlog/AGENTS.md` first if you have
not. Run `python traderlog/run_checks.py` before you start.

---

## Goal

Fetch posts from the tracked traders' X timelines **including their replies**,
archive everything immutably on first sight, and detect deletions. No parsing, no
LLM calls — W1 is deterministic plumbing only.

## Why replies matter more than anything else here

Adds, stop moves and exits are almost always the author replying to their own
entry post. Bell notifications do not fire for those, which is why the original
email-based design was scrapped outright. **A fetcher that returns only top-level
posts satisfies the type signature and silently defeats the entire tool.** If you
build one thing carefully in this wave, build this.

## Files you own

Create:
- `traderlog/ingest/xfetch.py`
- `traderlog/ingest/archive.py`
- `traderlog/ingest/deletions.py`
- `traderlog/tests/test_ingest.py`

Modify:
- `traderlog/checks/runner.py` — `check_ingest` only (see "flip your check")

**Do not touch** anything under `traderlog/llm/`, `traderlog/api/`,
`traderlog/ui/`, `db/schema.sql`, or anything in `manas_os/`.

## Contract you must honour

`design/CONTRACTS.md §7`, verbatim:

```python
def fetch_timeline(handle: str, since: str | None) -> list[RawPost]: ...
```

`RawPost` fields: `post_id, handle, conversation_id, in_reply_to, ts_utc, text,
url, media: list[RawMedia], raw: dict`.

Everything downstream is written against this shape. If it turns out to be wrong,
change `CONTRACTS.md` in the same commit and say so in your `_COMPLETED.md` — do
not quietly return something different.

## Requirements

1. **Playwright, persistent profile.** Launch with a user-data-dir from
   `config.get("ingest.browser_profile_dir")`. The user logs in **by hand, once**.
   Never store, prompt for, or type a password. Never automate the login form.
2. **Read-only.** No likes, follows, replies, posts, or DMs. Navigation and
   scrolling only.
3. **Archive before parse.** Write `raw` to `data/raw/<handle>/<post_id>.json` and
   each media file to `data/media/<post_id>_<idx>.<ext>` with a sha256, **before**
   inserting the DB row. Nothing downstream may re-fetch: threads run for weeks,
   X's search window does not, and posts get deleted.
4. **Idempotent.** Re-running for the same `since` must not duplicate rows.
   Dedupe on `post_id`. Existing rows are never overwritten — the only field a
   later run may set is `deleted_at`.
5. **Deletions.** A post previously captured and now absent gets `deleted_at`
   stamped. Keep the row and the archive. Log it to `pipeline_runs`.
6. **Human cadence.** Jittered intervals from `ingest.poll_interval_minutes` and
   `ingest.jitter_pct`. Do not hammer.
7. **Never raise out of `run()`.** Follow the adopted ingestor pattern: catch,
   log `fail` to `pipeline_runs`, return 0. One bad fetch must not stop the others.

## Flip your check

`check_ingest` in `checks/runner.py` currently returns `not_built_yet`. Replace
that with the real assertion: fresh posts within 24h for at least 80% of active
non-mock traders, and every `posts.raw_path` pointing at a file that exists.

**This is part of the wave, not optional.** A check left on `not_built_yet` after
its wave shipped makes the harness decorative — that is finding **I1** in
`design/AUDIT_LEDGER.md`.

## Done-test

```bash
python traderlog/run_checks.py     # ingest check must read pass or stale_Nd, not not_built_yet
pytest traderlog/tests -q
```

Plus, manually: three real traders ingested over seven days; `posts` row count
matches the file count under `data/raw/`; at least one self-reply thread visible
in the FEED screen with `in_reply_to` populated.

## Blocked on the user

- Logging into X by hand in the profile directory.
- Deciding main handle vs secondary. **Recommend secondary** — this route
  violates X's ToS and risks suspension. That was flagged and accepted; do not
  re-litigate it, but do not quietly point it at the main account either.
- The actual trader roster. Until it exists, develop against saved HTML fixtures
  and the mock rows.

You can write and unit-test everything here without a live login. Do that first.

## Watch out for

- **`Unverified:` how much of X's current markup Playwright can reliably parse**,
  and whether timeline-with-replies is reachable from a logged-in profile without
  rate limiting. This wave proves or kills it. If it turns out to be unworkable,
  say so plainly in your `_COMPLETED.md` — the fallback (official API) is already
  designed for and is a one-file change. **Do not** paper over a flaky scraper
  with retries and call it done.
- Timestamps: store both `ts_utc` and `ts_ist`. Every UI surface is IST.
- Indian tickers in text are noisy; **do not** try to extract symbols here. That
  is the classifier's job in W2.

## When you finish

Write `HANDOFF_W1_ingest_COMPLETED.md` beside this file: files changed, test
results, wiring notes, assumptions made, and anything you were unsure about.
Update `traderlog/TASKS.md` and `traderlog/HANDOFF.md`.

**Do not git commit.** The maintainer QCs and commits, one commit per verified wave.
