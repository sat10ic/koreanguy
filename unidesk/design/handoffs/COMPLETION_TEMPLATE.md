# HANDOFF <WAVE> <topic> -- COMPLETED

> Cloned from `traderlog/design/handoffs/COMPLETION_TEMPLATE.md` on 2026-08-28
> (provenance per unidesk DECISIONS.md D5). Rules are identical: state only
> what was actually completed; name remainders under "Honest partials"; every
> Attribution-ID must already exist as an append-only record in
> `design/MODEL_WORK_LOG.jsonl`.

State only what was actually completed. If an orchestration, live-acceptance,
or verification remainder exists, keep the parent backlog item partial and
name it under `## Honest partials`.

## Outcome

<Concrete result and boundaries.>

## Attribution

Attribution-ID: <executor-ledger-id>

Attribution-ID: <orchestrator-or-reviewer-ledger-id>

The IDs must already exist as separate append-only records in
`design/MODEL_WORK_LOG.jsonl`. Use `unknown` for an undocumented exact model;
never replace it with a plausible identity.

## Files changed

- `<path>` -- <what changed>

## Verification

```text
<commands actually run and their outputs>
```

## Honest partials

<What was NOT done, could not be verified, or was left open.>
