# HANDOFF W3 runtime producer -- COMPLETED

## Outcome

The W3 runtime producer exists: `run_link_pass` in `traderlog/llm/link.py`
selects every eligible canonical post (classified `trade_event`, standalone,
backing no `position_events` row, with no `review_queue` row of kind
`link_event` in ANY status), applies the fine filter (non-empty parsed symbols
plus at least one same-handle/symbol open-like candidate via the existing
`_symbols` / `_candidate_positions` gates), then runs each post through the
existing `propose_link` -> `route_link_proposal` flow. Below-floor proposals
queue open review items; at/above-floor proposals auto-apply. Idempotency is
structural: processed posts are excluded by the coarse filter itself, so a
second pass makes zero provider calls and zero writes, a rejected post is
never re-queued, and an open item is never re-proposed. Per-post errors are
recorded in `LinkPassResult.failures` and the pass never raises outward.
Existing functions in `llm/link.py` are untouched; the producer is appended.

Boundaries: the producer is a library entrypoint. No production pipeline
invokes it yet.

## Attribution

Attribution-ID: attr-w3-producer-unknown-executor-20260823-001

Attribution-ID: attr-w3-producer-glm53-orchestrator-20260823-001

Implementation was performed by the unnamed ZCode subagent (first ID);
orchestration, supervision, and personal verification by GLM 5.3 via ZCode
(second ID). These are separate contributions and must not be collapsed.

## Files changed

- `traderlog/llm/link.py` -- appended the frozen `LinkPassResult` dataclass and
  the `run_link_pass` producer entrypoint; one docstring line added. No existing
  function modified.
- `traderlog/tests/test_link_pass.py` -- new. Eleven disposable-database tests:
  below-floor and at/above-floor flows each with second-pass idempotency,
  rejected-never-requeued, seven parametrized ineligibility gates that must
  never reach the provider, and two-trader per-post failure isolation.
- `traderlog/tests/test_browser_review.py` -- teardown hardening only: the
  harness fixture now keeps the server thread reference, joins it for 5s after
  `should_exit`, and `pytest.fail`s loudly if it is still alive. No other
  change.
- `traderlog/design/MODEL_WORK_LOG.jsonl` -- appended exactly one executor
  record (`attr-w3-producer-unknown-executor-20260823-001`).
- `traderlog/design/handoffs/HANDOFF_W3_producer_COMPLETED.md` -- this report.

## Verification

Baseline before any edit: focused suite `50 passed, 2 warnings in 22.10s`;
`run_checks.py` reported `attribution 7 records, 2 completed handoffs` and
`STATE.json updated. No failures.`

After the changes, from the repository root:

```text
$ python -m pytest traderlog/tests/test_link.py traderlog/tests/test_link_pass.py traderlog/tests/test_api_review.py traderlog/tests/test_reconcile.py traderlog/tests/test_browser_review.py -q
61 passed, 2 warnings in 32.00s

$ python -m pytest traderlog/tests/test_browser_review.py -q        # run 1 of 2
5 passed, 2 warnings in 17.31s

$ python -m pytest traderlog/tests/test_browser_review.py -q        # run 2 of 2
5 passed, 2 warnings in 19.09s

$ python -m pytest traderlog/tests -q
171 passed, 2 warnings in 43.62s

$ python traderlog/run_checks.py
  OK    db         W0   25 tables
  OK    ingest     W1   4/4 traders fresh
  OK    parse      W2   3 real positions, all cited
  OK    golden     W2   5 fixtures, prompts current
  OK    attribution W0   8 records, 3 completed handoffs
  ..    derive     W4   no breadth ingested yet (W4)
  OK    ui         W0   7 screens, dist present
  --    telegram   W7   sending disabled in config
  STATE.json updated. No failures.
```

## Honest partials

- The producer is not wired into any production pipeline; no batch or W2 parse
  orchestration calls `run_link_pass` yet. That wiring is future work, per the
  audit's Action 1 boundary.
- Orchestrator verification complete (GLM 5.3 via ZCode, record
  `attr-w3-producer-glm53-orchestrator-20260823-001`): the executor's commands
  were personally re-run — focused suite 61 passed, browser suite 5 passed
  twice consecutively, whole suite 171 passed, `run_checks.py` exit 0 with the
  attribution check green — and the implementation was read line-by-line
  against the audited contract before this report was finalized.
- The audit's one-off browser flake (1 failure / 152) cause remains unproven.
  The teardown hardening is defensive only; two consecutive green browser runs
  do not prove the original flake is eliminated, only that the failure is now
  visible instead of silent if it recurs.
- `run_link_pass` has no runtime caller, so its behavior in the production
  corpus is exercised only through disposable-database tests; the current
  production corpus has zero eligible posts, which the audit already expected.
