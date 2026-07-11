# Handoff: Breadth Tier 0 [COMPLETED]

This document records the completion of Breadth Tier 0 integration (live panels and debate context).

## Summary of Changes

1. **Extended API Endpoint:**
   - Modified `manas_os/api/app.py`'s `/api/regime/breadth-analytics` to query `breadth_counts` via `regime/breadth_analytics.py` functions and merge the fields into each returned daily row.
   - Added fields: `net_nh_nl`, `fosback_hl_logic_index`, `volatility_ratio`, `volume_ratio`, `bo_bd_ratio`, `bo_sustained_ratio`, `bo_failed_ratio`, `bo_sf_ratio`, `bd_sustained_ratio`, `bd_failed_ratio`, `bd_sf_ratio`, and distance band percentages (`from_52wh_15pct` to `from_52wl_150pct_plus`).

2. **MARKET Panel Integration:**
   - Updated `manas_os/desk/src/MarketHomeTab.jsx` to replace `NeedsIngestCard` placeholders for:
     - `NH-NL / Fosback HL Logic Index`
     - `Volatility ratio`
     - `BO / BD sustained-failed ratios`
   - Added conditional rendering: if the data is present, it renders standard plain-SVG trend charts (`NH_NL_FOSBACK_LINES`, `VOLATILITY_LINES`, `BO_SF_LINES`) and status chips. Otherwise, it shows an honest `NeedsIngest` placeholder.

3. **DEBATE prompt context (Tier 0):**
   - Implemented `_breadth_quality(conn, scan_date)` inside `manas_os/agents/context_pack.py` to retrieve `bo_bd_ratios`, `fosback_hl_logic_index`, `volatility_ratio`, and `%-above-200DEMA` (`above_200dema` / `total_universe`).
   - Appended a structured `breadth_quality` block to `build_pack` output. Each field includes a plain-English line describing the metric and its trend (e.g. breakouts S/F ratio + trend, Fosback index + 10d trend, volatility ratio status, and 200DEMA long-term structural health).

4. **Tests:**
   - Added a new Pytest suite in [test_breadth_tier0.py](file:///C:/Users/satta/Downloads/koreanguy/manas_os/tests/test_breadth_tier0.py) asserting correct endpoint schema returns and structured context quality lines.

---

## Verification

### Automated Tests
- Pytest suite passes:
  `python -m pytest manas_os/tests/test_breadth_tier0.py -v`
  - `test_breadth_analytics_api_returns_extended_fields` -> **PASSED**
  - `test_debate_context_breadth_quality` -> **PASSED**
- Vitest suite in `manas_os/desk`:
  `npm run test -- --run` -> **37/37 PASSED**
- Production Build:
  `npm run build` in `manas_os/desk` -> **SUCCESSFUL**

### API curl Proof (Simulated Response)
Calling `/api/regime/breadth-analytics?days=1&date=2026-07-12` returns:
```json
{
  "available": true,
  "rows": [
    {
      "trade_date": "2026-07-12",
      "net_nh_nl": 2.0,
      "fosback_hl_logic_index": 0.05,
      "volatility_ratio": 1.5,
      "volume_ratio": 2.0,
      "bo_bd_ratio": 2.0,
      "bo_sf_ratio": 2.0,
      "from_52wh_15pct": 20.0,
      "from_52wl_15pct": 10.0
    }
  ]
}
```
