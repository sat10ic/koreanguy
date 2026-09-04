# HANDOFF W3 — cross-thread linking

## Goal

Turn a standalone, source-backed trade-event post into an auditable proposal to
attach one cited event to an existing position, auto-applying only at or above
the configured confidence floor and routing every lower-confidence proposal to
one-click human review.

This wave uses archived fixtures and disposable test databases only. X ingestion
is paused by the owner. Production remains real-data-only and must not be seeded
or mutated by tests.

## Binding sources

Read `AGENTS.md`, `CANONICAL.md`, `STATE.json`, `HANDOFF.md`, `TASKS.md`,
`design/CONTRACTS.md`, `design/VISUAL_LANGUAGE.md`, and
`design/WIREFRAMES.md` before implementation. In particular:

- `llm/reconcile.py` remains the sole writer of `positions` and
  `position_events`.
- `llm/link.py` inserts link proposals into `review_queue`; `api/app.py` resolves
  them but delegates any accepted position mutation to `llm/reconcile.py`.
- Every applied numeric field cites the standalone source `post_id`. Never infer
  an unstated price, quantity, stop, target, result, or date.
- Below `reconcile.link_confidence_floor` (default `0.8`) never auto-merges.
- Repeating a proposal or an accept/reject request is idempotent.

## Vertical slices

### 1. Validated proposal and candidate boundary

Implement a strict link-proposal validator and smart-tier prompt. A candidate
post must exist, be a standalone classified `trade_event`, name a symbol, and
not already back a position event. Candidate positions must belong to the same
handle and symbol and be in an open-like state. Reject unknown keys, invalid
event kinds, foreign posts/positions, non-finite numbers, and confidence outside
`[0,1]`.

Acceptance:

- Invalid or cross-handle/cross-symbol proposals perform zero writes.
- The provider call uses tier `smart`, the complete binding prompt, and the
  audited provider result type.
- Focused tests cover one valid proposal and adversarial validation cases.

### 2. Confidence routing and audit row

At or above the configured floor, record an auditable accepted proposal and
apply it. Below the floor, insert exactly one open `review_queue` row. Re-running
the same post/proposal must not duplicate review items or events.

Acceptance:

- `0.79` queues and changes no position; `0.80` applies under the default.
- The queue stores the exact proposed event, reasoning, alternatives, post, and
  position.
- Repeated routing is byte-/row-idempotent.

### 3. Sole-writer application path

Add a public helper in `llm/reconcile.py` that applies one validated accepted
link proposal to the complete canonical position state, revalidates evidence,
and replaces derived event rows transactionally. Accepted linked posts must be
included in later thread re-derivation/hash inputs so a future reconcile cannot
silently erase the human-confirmed cross-thread event.

Acceptance:

- Accepting an exit/partial/add/stop/target proposal updates `state_json`,
  `evidence_json`, `position_events`, status, and thread hash coherently.
- A future unchanged reconciliation costs zero provider calls and preserves the
  linked event.
- Any failure rolls back both queue resolution and position mutation.

### 4. API and FEED completion

`POST /api/review/{id}` rejects invalid decisions, rejection mutates only the
queue status, acceptance invokes the reconcile-owned apply path, and both are
idempotent with an explicit response. After a decision, FEED refreshes review,
posts, and health-derived counts so the effect is visible without a page reload.

Acceptance:

- API tests prove accepted=`applied: true`, rejected=`applied: false`, missing or
  already-resolved behavior is explicit, and rollback is atomic.
- Browser test proves a queued item disappears and the accepted event appears;
  no bulk accept exists.
- Neo-brutalist visual and accessibility contracts remain intact.

## Verification

Run focused W3 tests first, then:

```bash
pytest traderlog/tests -q
cd traderlog/ui && npm run build
python traderlog/run_checks.py
```

Also run `git diff --check` and inspect the local UI in a real browser. Do not
commit. Write `HANDOFF_W3_link_COMPLETED.md` only when every acceptance item is
personally re-verified by the orchestrator; otherwise leave explicit open items
in `HANDOFF.md` and `TASKS.md`.
