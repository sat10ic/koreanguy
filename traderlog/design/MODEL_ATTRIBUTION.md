# Model-work attribution

TraderLog records who performed each distinct model-role contribution so a later
review can distinguish implementation, orchestration, review, and vision work.
It records evidence, not guessed identities.

## Canonical ledger

`design/MODEL_WORK_LOG.jsonl` is append-only JSON Lines: one object per distinct
contribution. Do not rewrite, reorder, delete, or merge old records. Correct a
mistake with a new record whose `notes_limitations` names the correction.

Every record must contain these fields:

| Field | Requirement |
|---|---|
| `id` | Stable `attr-...` identifier, unique for the life of the ledger. |
| `completed_at` | ISO-8601 timestamp with timezone, or date-only `YYYY-MM-DD` when a historical record has no documented time. Never invent a time. |
| `wave`, `deliverable` | Wave and concrete slice, not a vague project label. |
| `role` | One of `executor`, `orchestrator`, `reviewer`, `vision`. |
| `model`, `host_tool` | Exact model and execution host/tool when documented. Use `unknown` or `exact-model-unavailable`; never infer. |
| `identity_basis` | `self_reported`, `host_verified`, or `unknown`. |
| `scope`, `files` | What was handled and the exact repository files in scope. |
| `completion_report` | Relative repository path to the report that cites this ID. |
| `status` | `completed`, `partial`, or `blocked`. |
| `verification_status` | `unverified`, `verified`, or `partial`. |
| `notes_limitations` | Boundaries, unknowns, or verification limits. |

`status` belongs to the concrete contribution/deliverable in that record, not
to the parent wave. A completed backend or bootstrap slice stays `completed`
when a different wave-level acceptance or orchestration remainder is open; put
that remainder in `notes_limitations` and the wave backlog.

## Completion rule

Every future `design/handoffs/*_COMPLETED.md` must include a `## Attribution`
section containing one or more exact lines:

```text
Attribution-ID: attr-example
```

The executor appends its own record and cites it after finishing. The
orchestrator adds a separate record only after personally running the stated
verification; a reviewer or vision contributor gets a separate record when
applicable. A completion report is incomplete without these IDs.

`python traderlog/run_checks.py` runs the deterministic `attribution` check. It
fails for malformed JSONL, duplicate IDs, invalid required values, missing or
unknown completed-handoff IDs, and mismatched report paths. It reads no
production data.

## Backfilled governance entry

Attribution-ID: attr-governance-attribution-terra-20260823-001

Attribution-ID: attr-governance-attribution-gpt5-orchestrator-20260823-001

Attribution-ID: attr-governance-attribution-gpt5-reviewer-20260823-001

This entry records the attribution-governance implementation and W3 audit
feedback, its orchestration, and its independent review. It is a governance
completion, not a claim that a new product wave completed.
