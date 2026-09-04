# HANDOFF W3 CONTINUE — FEED + browser close

This is the next-LLM handoff requested by the owner. The previous task paused at
the verified W3 backend deliverable boundary. Complete this continuation and do
not resume X ingestion.

## Read first, in order

1. `traderlog/AGENTS.md`
2. `traderlog/CANONICAL.md`
3. `traderlog/STATE.json`
4. `traderlog/HANDOFF.md`
5. `traderlog/TASKS.md`
6. `traderlog/design/CONTRACTS.md`
7. `traderlog/design/VISUAL_LANGUAGE.md`
8. `traderlog/design/WIREFRAMES.md`
9. `traderlog/design/handoffs/HANDOFF_W3_link.md`
10. this file

Run `python traderlog/run_checks.py` before edits and again at the end. Do not
commit. Preserve all unrelated dirty-worktree changes.

## Certain current state

Backend implementation is present, uncommitted, in:

- `traderlog/llm/link.py`
- `traderlog/llm/prompts/link.md`
- `traderlog/llm/reconcile.py`
- `traderlog/api/app.py`
- `traderlog/tests/test_link.py`
- `traderlog/tests/test_api_review.py`

It has been independently reviewed twice. Final evidence:

```text
pytest traderlog/tests/test_link.py traderlog/tests/test_api_review.py traderlog/tests/test_reconcile.py -q
45 passed

pytest traderlog/tests -q
148 passed in 16.76s

python traderlog/run_checks.py
exit 0; db/ingest/parse/golden/ui pass; derive not built yet
```

The local API was restarted from current source as PID `33928`; health reports
4 traders, 12 posts, 3 positions, 0 review items, and no mock data.

## Owned continuation scope

The next executor may edit only these unless an acceptance defect proves a
backend change is necessary:

- `traderlog/ui/src/App.jsx`
- `traderlog/ui/src/api.js`
- `traderlog/ui/src/screens/Feed.jsx`
- `traderlog/ui/src/styles/app.css` only if the existing contract cannot express
  a required state
- `traderlog/ui/index.html` for the cold-load favicon 404
- new focused UI/API integration tests or browser fixture helpers under
  `traderlog/tests/`
- `traderlog/HANDOFF.md`, `traderlog/TASKS.md`, and a completion report at close

Do not rewrite the linker/reconciler, vision, ingest, production data, golden
fixtures, or visualization components. If backend behavior fails an acceptance
test, report the exact failing invariant before changing an owned-backend file.

## Work to complete

1. After `resolveReview`, refresh the open review list, FEED posts, and the
   health-derived FEED badge without a page reload. Accepted standalone events
   must become visible through the existing `/api/feed` event join; rejected
   items must simply disappear from review.
2. Keep accept/reject actions single-item only. Preserve disabled/loading/error
   feedback so a double click cannot submit two decisions. Do not add bulk
   accept.
3. Remove the cold-load `/favicon.ico` 404 with a bounded `index.html` favicon
   declaration or real static asset; verify a fresh browser context has no
   console errors.
4. Build a disposable-database browser acceptance fixture. Never seed or mutate
   `traderlog/data/traderlog.db`. The fixture must show one below-floor queued
   link, accept it, prove the item disappears and the event appears, then repeat
   with rejection and prove the position is unchanged.
5. Re-run focused backend tests, the full suite, UI build, real-browser mobile
   check at 375×812, and `python traderlog/run_checks.py`.

## Acceptance

- Accept response is `applied: true`; reject is `applied: false`.
- Review count/list and feed state refresh in the same browser session.
- Duplicate interaction is prevented in the UI and remains idempotent in the
  API.
- No bulk accept, no mock production rows, no X calls, no console errors, no
  horizontal overflow at 375×812.
- `npm run build`, 148+ Python tests, `git diff --check`, and final TraderLog
  checks pass.

## Known risk to assess, not silently guess

`unresolved_json` contains free-form strings. Deterministically applying a linked
event preserves that array rather than guessing which prose item the new event
resolves. A future item may therefore remain conservatively unresolved even
after a linked stop/target/exit supplies evidence. Do not keyword-delete these
strings. If this blocks UI truthfulness, specify a structured resolution field
in `design/CONTRACTS.md` and add tests before changing the proposal schema.

The earlier Claude report also left F14 (the Library empty-state citation) open
because its exact finding/scope was unavailable. Do not invent the intended copy;
leave it deferred unless the owner supplies F14 or explicitly expands scope.

## Close

Only when every acceptance item passes, write
`traderlog/design/handoffs/HANDOFF_W3_link_COMPLETED.md`, update the W3 statuses
in `TASKS.md` and the top of `HANDOFF.md`, and stop without committing.
