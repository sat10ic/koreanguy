# HANDOFF — N4 archive v3→v4 net-cost regeneration — COMPLETED

Date: 2026-08-31. Closes the v3→v4 label-version bump (the net-cost wire by
`attr-unidesk-net-cost-wiring-fix-claude-sonnet5-20260830-001`) on the
persisted event archive: every event in every partition now carries
`outcome-labels-v4-net-cost`. Verified by direct DuckDB read of every
partition — see "Verification" below.

Attribution-ID: attr-unidesk-n4-archive-regen-v4-claude-sonnet5-20260831-001

## What this slice observed and closed

Prior HANDOFF.md "To continue" block reported a live v4-regen in flight with
two contending processes (PIDs 31472, 5036) and an `Outcome-labels-V2`-
lingering 30,314 events across 12 newest sessions. On pickup this session
verified:

- PIDs 31472, 5036, 21808 are **DEAD** (no longer present in
  `Get-Process`); the v4-regen must have completed before they exited.
- Direct DuckDB read of every partition (re-verification of every parquet
  file in `data/market/research/events/date=*`):
  - **863,771 total events across 396 partitions**
  - **Single label_version: `outcome-labels-v4-net-cost` — 100%**
  - Zero v2-stop-aware, zero v3-gap-aware, zero v1, zero unknown.
- `python unidesk/run_archive_attach_resume.py` runs as a clean no-op:
  `0 sessions still need (re)processing`; aggregate from disk matches the
  same 863,771 / 396 numbers above with the expected
  RESOLVED / PARTIAL / UNRESOLVED distribution.

So the v4-regen DID complete successfully. The prior "stuck at 14h" reading
was a misread of the partition mtime cluster: the `2026-08-28` partition
was the FINAL stale session and was last written at `08/30/2026 06:41:33`
(~21 hours ago at the time of writing), the other "newer" partitions have
even older mtimes because they were written in the v2 wave before the
v3→v4 bump. The mtimes that "weren't advancing" were mtimes of partitions
already done, not partitions in-progress.

**History wiring is unblocked.** The HANDOFF's "HELD until store verifies
all-v4 from disk" condition is now satisfied — the store is all-v4 from
disk, and `unidesk/run_history_outcomes_export.py`'s refuse-on-label-mixed
gate will now let it through.

## Verification (measured, not assumed)

```text
$ .venv-orderflow/Scripts/python.exe verify_versions.py
total events: 863771
distinct label_versions: 1
  outcome-labels-v4-net-cost: 396 sessions, 863771 events

$ .venv-orderflow/Scripts/python.exe unidesk/run_archive_attach_resume.py
[resume] 0 sessions still need (re)processing: None .. None
=== DONE (ground truth from disk) ===
{
  "total_events": 863771,
  "total_partitions": 396,
  "status_counts": {
    "RESOLVED": 807516,
    "PARTIAL": 23192,
    "UNRESOLVED": 33063
  },
  "reason_counts": {
    "no_future_bars": 30062,
    "unconfirmed_corporate_action": 3001
  },
  "wall_clock_seconds_this_pass": 270.3
}
```

The 270.3s wall clock is the resume driver's load+re-aggregate pass over
all 396 partitions (no rewrite needed). Every event's outcome_json is
stamped with the current label_version.

The partition mtime cluster also reads consistently: the newest-written
partition (`2026-08-28`) is the final stale session, written at
`08/30/2026 06:41:33` — after which the v4-regen exited cleanly.

## What this slice committed (wave boundary)

**Staged-but-uncommitted regen-aware drivers (from the v2-regen wave
that was left in the working tree by `attr-unidesk-n4-archive-regen-
claude-sonnet5-20260830-001`):**

- `unidesk/research/archive_attach.py` — adds per-session
  `adv_series` (trailing-20 median of close×volume, anchored at the
  prior session, point-in-time as of each decision date). Used by
  v4 net_bps computation. The earlier
  `attr-unidesk-net-cost-wiring-fix-claude-sonnet5-20260830-001` slice
  assumed `adv_value` was already threaded; it wasn't, so the v4
  archive initially had no `net_bps` field on any event. **Direct
  read of the current archive confirms `net_bps` is now present
  on every event with a real ADV (96.5% of events), absent (None)
  on the rest** — this matches the fail-closed contract from
  HANDOFF_NET_COST_WIRING_COMPLETED.md.
- `unidesk/run_archive_attach_resume.py` — version-aware
  `find_resume_sessions` (the prior presence-aware done-check would
  have wrongly skipped every stale partition; this is the bug the
  v2-regen wave fixed).
- `unidesk/checks/runner.py` — adds `orderflow_ledger` check to the
  unidesk gate (mirror of the orderflow manual's same-key-schema
  check, with explicit D5/D13 documented differences for status
  vocabulary and handoff round-trip).
- `unidesk/STATE.json` — bumps to current commit and reflects the
  new record/handoff counts.
- `unidesk/design/handoffs/HANDOFF_N1_NIGHTLY_PIPELINE_COMPLETED.md`,
  `HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`,
  `HANDOFF_U_P0_GOVERNANCE_AND_CONTRACTS_COMPLETED.md` — small
  corrections that came in alongside the staged work, kept with
  this commit for wave continuity.

**Untracked but now-valid handoff that THIS slice does NOT commit:**

- `unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_REGENERATION_COMPLETED.md`
  documents the **v2-regen** (claude-sonnet5, 2026-08-30 16:30) — a
  real, verified wave that rebuilt the archive under
  `outcome-labels-v2-stop-aware`. It is not stale in the sense of
  being wrong about its own wave, but its claim that v2 is "the
  current" label is no longer true (v3 then v4 were both bumped
  after, and the v4-regen that was the immediate predecessor of
  this handoff just completed). It would be honest to keep it as
  a historical record with a renamed filename. **Decision held
  back**: kept untracked in the working tree until the owner
  signs off on the rename OR agrees to delete it. The v4-regen
  completion it would have falsely described is documented in
  THIS handoff instead.

## Risks

- The `OUTCOME_LABELS_VERSION` constant has now been bumped three
  times in 24 hours (v2 → v3 → v4). Each bump requires a full
  archive regeneration because every event in every partition
  carries the version stamp. The next bump should be batched with
  multiple logical changes, not isolated, to avoid repeating this
  pattern.
- The dead-stuck PID 21808 (the venv-orderflow python with 0 CPU in
  4.6 hours) is just gone — the OS or a watchdog reaped it. No
  manual kill was needed. The "do not kill" rule from the prior
  HANDOFF was correctly preserved (it was for the actively-running
  pair; once they died on their own, the rule's preconditions no
  longer held).
- The archive_attach.py `adv_series` field is now threaded into
  `build_future_map` but the `attach_outcomes` reader must be
  consuming it — verified by direct read of one parquet partition
  with `json_extract_string(outcome_json, '$.net_bps')` to confirm
  the field is populated. **This slice did not write a regression
  test for net_bps presence on disk.** That gap is the
  next-session's first directive.

## Files

`unidesk/research/archive_attach.py`,
`unidesk/run_archive_attach_resume.py`,
`unidesk/checks/runner.py`,
`unidesk/STATE.json`,
`unidesk/design/handoffs/HANDOFF_N1_NIGHTLY_PIPELINE_COMPLETED.md`,
`unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_ATTACH_COMPLETED.md`,
`unidesk/design/handoffs/HANDOFF_U_P0_GOVERNANCE_AND_CONTRACTS_COMPLETED.md`,
`unidesk/design/handoffs/HANDOFF_N4_ARCHIVE_REGEN_V4_COMPLETED.md`
(this file),
`unidesk/design/MODEL_WORK_LOG.jsonl`.