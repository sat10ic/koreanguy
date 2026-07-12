# HANDOFF_GEMINI_guru_checklists — COMPLETED

**Executor:** Grok · **Date:** 2026-07-12 · **No git commit** · **Advisory only**

## Seeded checklist: `arora_entry_v1`

Mentor: **Manas Arora** · Title: **Arora entry discipline** · 12 items (all with `source_cite`)

| id | kind | eval | auto_field | cite (short) |
|----|------|------|------------|--------------|
| breadth_ok | hard | AUTO | regime_mode_not_no_trade | ARORA_SHARDS + INDIA_PLAYBOOK regime |
| rs_leadership | soft | AUTO | rs_ge_50 | ARORA LF/leadership |
| stop_distance_sane | hard | AUTO | stop_pct_le_8 | ARORA tight stop |
| position_size_from_risk | hard | AUTO | has_final_qty | ARORA + PLAYBOOK R1 |
| no_chase_huge_gap | hard | MANUAL | — | ARORA gap limit |
| wait_after_open | hard | MANUAL | — | ARORA Strong Start 3min |
| no_averaging_down | hard | MANUAL | — | ARORA pyramiding |
| pyramid_size_cap | soft | MANUAL | — | ARORA pyramiding |
| live_stop_order | hard | MANUAL | — | PLAYBOOK R12 |
| journal_before_entry | soft | MANUAL | — | TRADETM process |
| vcp_or_base_quality | soft | MANUAL | — | ARORA VCP/consolidation |
| home_run_patience | soft | MANUAL | — | ARORA outcome distribution |

Also retained existing `manas_arora_daily` checklist with added cite/kind metadata.

## Endpoints
- `GET /api/mentor/checklists` (existing; now includes arora_entry_v1)
- `GET /api/checklists/{id}/evaluate?symbol=&date=` — AUTO from plan/regime/metrics; MANUAL from ticks
- `POST /api/checklists/{id}/ticks` — `{symbol, date, item_id, checked}`
- Existing date-only responses endpoints unchanged

## AUTO mapping table
| auto_field | payload source |
|------------|----------------|
| regime_mode_not_no_trade | `regime_snapshots.market_mode` |
| rs_ge_50 | `scanner_screener.metrics_for_symbol` RS |
| stop_pct_le_8 | `scan_candidates.entry/stop` |
| has_final_qty | `agent_verdicts` sizer `final_qty` |

## Files
- `design/mentor_checklists.yaml` — Arora entry seed
- `scanner/mentor_checklists.py` — evaluate + symbol ticks schema
- `api/app.py` — evaluate + ticks endpoints
- `tests/test_guru_checklists.py`

## UI
Not fully mounted on TRADE PLAN panel this pass (API ready). Wire panel next: render evaluate payload rows + amber HARD fails; never disable plan buttons.

## Tests (QC)
```
pytest manas_os/tests/test_guru_checklists.py -q → pass (with suite: 21 passed including alpha/live/backend)
```

## Do-not
`blocks_plan` always false. No US-guru content. No uncited items.
