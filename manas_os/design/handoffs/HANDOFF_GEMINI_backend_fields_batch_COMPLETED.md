# HANDOFF_GEMINI_backend_fields_batch — COMPLETED

**Executor:** Grok (inline) · **Date:** 2026-07-12 · **No git commit** (per HANDOFF_INDEX)

## Summary

Implemented additive server fields for signal-guide and watchlist, expanded Focus Center catalyst matching, verified data-gap state against on-disk ChartsMaze dumps. Desk UI displays server-owned `rupee_risk` / `management_contract` and family/trigger chips.

## Files changed

| File | Change |
|------|--------|
| `manas_os/agents/signal_guide.py` | `compute_rupee_risk`, `build_management_contract` (+ lens mgmt table) |
| `manas_os/api/app.py` | signal-guide payload fields; watchlist family/next_trigger; focus catalyst matcher |
| `manas_os/desk/src/TradePlanTab.jsx` | Prefer `guide.rupee_risk` + `guide.management_contract` (regex fallback kept) |
| `manas_os/desk/src/ShortlistTab.jsx` | Show `family_label` + `next_trigger` when present |
| `manas_os/tests/test_signal_guide_backend_fields.py` | New unit tests |

## Item results

### 1. `rupee_risk` server-side
- Formula: `final_qty * (entry - stop)` via `signal_guide.compute_rupee_risk`.
- Emitted on `/api/desk/signal-guide` when plan+qty available; morning_setups path returns `null` (honest — no sizer).
- TradePlanTab: uses `guide.rupee_risk` first; multiplies client-side only if old payload lacks field.

### 2. `management_contract` block
- Shape: `{trade_type, trail_rule, normal_behaviour[], source_cite, lens}`.
- Derived from lens template + optional trail step instruction (no client regex required).
- UI falls back to legacy step-regex if field absent.

### 3. Watchlist `family` / `family_label` / `next_trigger`
- Per-symbol lookup into `scan_candidates` after `ensure_schema` (defensive try/except for fixture DBs).
- User-added rows with no candidate → all three fields `null`.
- `next_trigger` = `trigger >= {entry}` when entry present.
- ShortlistTab chips for family_label + next_trigger.

### 4. Bug #37 Focus Center 0-setups
- Prior T3.7a already pulled focus from full ranked list; remaining mismatch risk was narrow `setup_type in {ep, ipo_base}` only.
- Expanded matcher: also `ep*` setup_types, `ipo` substring, earnings labels, catalyst+ep/ipo pattern text.
- Unit test covers EP variants vs pocket_pivot negative.

### 5. Data-gap repair
| Check | Result |
|-------|--------|
| `screener_hits` before 2026-07-04 | Already has rows from **2026-03-28** onward (total **34474** at QC time) |
| ChartsMaze on disk | `legacy/SwingEdge/data/chartsmaze/` has 2026-03-23/24/28, 04-05/10, 07-04..11 |
| `daily_prices` 2026-07-08 | **3270 rows present** (trading day True) — gap described in handoff already repaired in this DB |
| Re-ingest attempt | Optional re-run of `chartsmaze_scanners.ingest` for dated folders — report any failures in follow-up if needed |

**Honest:** Item 5 was largely **already satisfied** in the current database; no destructive rewrite performed. Dates without dump folders remain unavailable (e.g. 2026-07-06 if missing from chartsmaze).

## Tests (QC)

```
python -m pytest manas_os/tests/test_signal_guide_backend_fields.py manas_os/tests/test_desk_endpoints.py -q -k "signal_guide or watchlist or focus"
→ 22 passed, 41 deselected
```

## Curl proofs (manual maintainer)

```bash
# 1-2 signal-guide fields (use a real debated symbol/date from your DB)
curl -s "http://127.0.0.1:PORT/api/desk/signal-guide?symbol=SYMBOL&date=YYYY-MM-DD" | jq '{rupee_risk, management_contract, family}'

# 3 watchlist
curl -s "http://127.0.0.1:PORT/api/desk/watchlist?date=YYYY-MM-DD" | jq '.rows[0] | {symbol, family, family_label, next_trigger}'
```

## Assumptions / uncertainties
- `rupee_risk` uses sizer `final_qty` when present (including 0); does not re-derive from capital.
- management_contract trail text prefers guide step language when a trail/exit step exists.
- Data-gap SKYGOLD pool re-check not re-run (no live scan invocation in this pass).

## Do-not violations
No money-math change to gates/sizing. No git commit. Additive API fields only.
