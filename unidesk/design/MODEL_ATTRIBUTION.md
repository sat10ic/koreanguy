# Model-work attribution (unidesk)

Adopted by copy from `traderlog/design/MODEL_ATTRIBUTION.md` on 2026-08-28
(provenance per DECISIONS.md D5; the traderlog original remains that package's
canonical copy — this file is unidesk's, and drift here does not affect
traderlog). Records who performed each distinct model-role contribution so a
later review can distinguish implementation, orchestration, review, and
vision work. It records evidence, not guessed identities.

## Canonical ledger

`unidesk/design/MODEL_WORK_LOG.jsonl` is append-only JSON Lines: one object
per distinct contribution. Do not rewrite, reorder, delete, or merge old
records. Correct a mistake with a **new** record whose `notes_limitations`
names the correction.

Every record must contain these 14 fields (machine-checked by
`python unidesk/run_checks.py`):

| Field | Requirement |
|---|---|
| `id` | Stable `attr-...` identifier, unique for the life of the ledger; regex `attr-[a-z0-9][a-z0-9-]*`. |
| `completed_at` | ISO-8601 timestamp with timezone, or date-only `YYYY-MM-DD`. Never invent a time. |
| `wave`, `deliverable` | Wave (e.g. `U-P0`) and the concrete slice, not a vague project label. |
| `role` | One of `executor`, `orchestrator`, `reviewer`, `vision`. |
| `model`, `host_tool` | Your ACTUAL model identifier and the execution host. Check the host environment/system prompt before falling back; `unknown` is for the genuine case only. |
| `identity_basis` | `self_reported`, `host_verified`, or `unknown`. |
| `scope`, `files` | What was handled; `files` a non-empty list of exact repo paths. |
| `completion_report` | Repo-relative path to the report citing this record's ID. |
| `status` | `completed`, `partial`, or `blocked`. |
| `verification_status` | `unverified`, `verified`, or `partial`. Your own claim that it works is `unverified`. |
| `notes_limitations` | What you did NOT do, could not verify, or left open. |

## Completion rule

Every `design/handoffs/HANDOFF_*_COMPLETED.md` must contain exact
`Attribution-ID: <id>` lines — one per ledger record it reports — and every
record's `completion_report` must point back at a report containing its ID.
The check is bidirectional and `python unidesk/run_checks.py` fails on any
violation. A completion report is incomplete without these IDs.

Differences from the traderlog original (deliberate, tested here):

- `completion_report` paths are **repo-relative** (e.g.
  `unidesk/design/handoffs/HANDOFF_..._COMPLETED.md`), because unidesk
  records may lawfully point at reports in other packages (e.g.
  `orderflow/design/handoffs/...`).
- Root `MODEL_WORK_LOG.jsonl` is legacy and outside this schema (D5).

## Bootstrap entries

Attribution-ID: attr-unidesk-governance-glm53flash-20260828-001

Attribution-ID: attr-unidesk-contracts-glm53flash-20260828-002

Attribution-ID: attr-unidesk-crosswalk-glm53flash-20260828-003
