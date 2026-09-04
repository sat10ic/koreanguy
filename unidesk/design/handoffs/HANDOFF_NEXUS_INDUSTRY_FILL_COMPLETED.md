# HANDOFF Nexus industry-map fill — COMPLETED

Date: 2026-08-29.

Attribution-ID: attr-unidesk-nexus-industry-fill-grok46-20260829-001
Attribution-ID: attr-unidesk-d18-industry-spec-grok46-20260829-001

## Outcome

Chartsmaze did not cover every name. UniDesk now fills gaps from
`manas_os/data/nexus_industry_map.csv` (read-only; no `import manas_os`).

Measured on the live parquet:

| | n |
|---|---:|
| Chartsmaze (kept) | 2,423 |
| Nexus offered | 2,676 |
| Overlap (Chartsmaze wins) | 2,327 |
| Nexus-only filled | 349 |
| **Total mapped** | **2,772** |
| Nexus parse skipped | 0 |

The two taxonomies disagree on every overlapping symbol (e.g. Chartsmaze
`M&M` = Auto Manufacturers, nexus = Diversified Companies). Mixing them
would silently rewrite the primary table, so overlay is fill-only.
`source_tier` is `CHARTSMAZE` or `NEXUS_INDUSTRY_MAP`.

## Files

- `unidesk/momentum/data/reference_ingest.py`
- `unidesk/tests/test_reference_ingest.py`
- `data/market/reference/industry_mapping.parquet`
- `unidesk/momentum/DATA_POLICY.md`
- `plan/UNIFIED_DESK_BUILD_MANUAL_V2.md` (D18 / R-R / §12.8.1)
- `unidesk/DECISIONS.md` (D18)
- `plan/PHASE0_DATA_BUILD_SPEC.md`, `plan/SWING_EDGES_TECHNICAL_SPEC.md`
- `unidesk/design/PHASE0_GAP.md`
- `unidesk/TASKS.md`, `CANONICAL.md`, `HANDOFF.md`

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest unidesk/tests/test_reference_ingest.py -q
→ 9 passed
fill_industry_mapping_from_nexus(data/market)
→ filled 349, blocked_overlap 2327, total 2772
M&M / TRENT remain CHARTSMAZE
```

## Honest partials

- Nexus labels are a themetracker dump (captured 2026-07-26), not NSE
  official industry. Same provisional class as Chartsmaze.
- New nexus industries are not rolled into Chartsmaze sector names;
  `sector_of` falls back to the industry string.
- Not PIT membership and not 2016 history.
- Did not import `manas_os`. Did not copy `daily_prices`.
