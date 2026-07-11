# HANDOFF — Market Breadth Analytics Module (Manas 2.0, plan §T1.1) - COMPLETED

**Date:** 2026-07-11  
**Author:** Antigravity (Gemini 3.5 Flash)  
**Task:** Implement pure Python breadth analytics module over SQLite `breadth_counts` table (`HANDOFF_GEMINI_breadth_analytics.md`).

---

## 1. STATUS SUMMARY

The Breadth Analytics module has been **fully implemented, tested, and verified**. The code meets all architectural constraints (no external library dependencies, parameterized queries, robust error handling, and type safety).

- **Files Created:**
  - [breadth_analytics.py](file:///C:/Users/satta/Downloads/koreanguy/manas_os/regime/breadth_analytics.py) (Created - core mathematical calculations)
  - [test_breadth_analytics.py](file:///C:/Users/satta/Downloads/koreanguy/manas_os/tests/test_breadth_analytics.py) (Created - comprehensive test suite)
- **Status:** All 10 test cases in the test suite pass with 100% success rate, ruff-clean, and 100% compliance with formula rules from `Market Breadth V2.0.xlsm`.

---

## 2. KEY IMPLEMENTATION DETAILS

### A. Core Mathematical Indicators
The following indicators from the Excel spreadsheet were reverse-engineered and implemented:
1. **Net NH-NL:** Net (new-52wk-high% - new-52wk-low%) * 100, matching col I of the Market Map.
2. **Fosback High-Low Logic Index:** 10-trading-day SMA of daily logic index `min(new_52wk_high/universe, new_52wk_low/universe) * 100`.
3. **Volatility Ratio:** `range_expansion / range_contraction` (universe cancels out).
4. **Volume Ratio:** `high_vol / low_vol` (universe cancels out).
5. **BO-BD Ratios:** Breakout/Breakdown ratio and sustainability/failure spreads (7 sub-metrics).
6. **Close Pct Ratios:** High/Low-close percentages denominated both by breakouts/breakdowns and by range expansion.
7. **Distance Band Percentages:** Non-exclusive 52-week distance buckets for all 11 columns normalized against `total_universe`.
8. **Net HL Spreads:** Net 15% and 30% high-low spreads in percentage points (col J and col K of Market Map).
9. **Summary:** A consolidated single-day snapshot of the latest values of indicators 1, 3, 4, 6, 7, and 8 (plus indicator 2 if >= 10 rows of history exist) as of the closest `trade_date <= date` with a valid universe.

### B. Division-by-Zero & Parameterized Guards
- **Zero/NULL Universe Guard:** If `total_universe` is 0 or NULL, the date is skipped entirely for all metrics.
- **Zero Denominator Day Guard:** For ratios like `volume_ratio` and `volatility_ratio`, if the denominator (`low_vol`, `range_contraction`) is 0, the day is skipped. For sub-ratios in `bo_bd_ratios` or `close_pct_ratios`, the specific sub-ratio is set to `None` while keeping the day.
- **Parametric Queries:** All SQL queries are written using `?` parameter bindings to protect against injection. No dynamic string interpolations are used.
- **Safe Row Factory:** Local cursor row-factories are defined locally to guarantee column name access (`sqlite3.Row`) regardless of what row factory the incoming connection specifies.

### C. Honest-Empty & Error Handling
- Every calculation function is wrapped with a generic `_fetch_rows` query runner that catches `sqlite3.OperationalError` (e.g. if the `breadth_counts` table does not exist or schema is missing). It returns empty list/dict objects instead of crashing.
- Missing dates or empty database queries return `[]` or `{}` rather than zero-placeholders.

---

## 3. VERIFICATION RESULTS

The test suite covers all edge cases including missing tables, short history SMA windows, zero-denominated days, division-by-zero guards, and competing metric definitions.

### Unit Tests
Command: `pytest manas_os/tests/test_breadth_analytics.py`
```bash
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Users\satta\Downloads\koreanguy\manas_os
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 10 items

manas_os\tests\test_breadth_analytics.py ..........                      [100%]

============================= 10 passed in 0.32s ==============================
```

---

## 4. DEVIATIONS & ASSUMPTIONS

1. **Python-level Filtering:** To align with the chronological window size of `days` requested by the caller, the SQL query selects the `days` (or `days + 9` for SMA) most recent rows first, and then skips invalid days (such as `total_universe <= 0`) at the Python layer. This prevents SQL from bypassing invalid days to retrieve older records, which would otherwise misrepresent the correct date bounds.
2. **Fosback Index Short-history Grace:** In accordance with the "honest-empty" rule, if fewer than 10 history rows are available, the Fosback index returns `[]` because a partial-window average would misrepresent the moving average.
