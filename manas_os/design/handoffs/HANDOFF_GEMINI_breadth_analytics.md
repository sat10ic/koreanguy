# HANDOFF — Breadth Analytics Module (for Gemini, external chat, no repo access)

You are writing code for a repo you cannot see. Everything you need — the upstream
table's schema, code conventions, and the exact math — is embedded below. Do not assume
any file contents beyond what is quoted here; where something is ambiguous, say so
explicitly instead of guessing.

## What you own (strict file-ownership split)

This is one lane of a multi-model wave. A second external model (GLM) is separately
building the raw-counts ingest module that populates the table you read from. The repo
maintainer wires everything together by hand. **You may create ONLY these two new
files:**

1. `manas_os/regime/breadth_analytics.py`
2. `manas_os/tests/test_breadth_analytics.py`

Do **NOT** touch, edit, or emit changes to `schema.sql`, `app.py`, `cli.py`, the pipeline
orchestrator, GLM's ingest module, or any other existing file.

## The goal, one line

Write pure Python functions that read the `breadth_counts` table (defined below — build
against this contract now; GLM's module that populates it lands separately and may not
exist yet when you write this) and derive the workbook's ratio/percentage/index
analytics: net NH-NL, Fosback HL-Logic-Index, volatility ratio, volume ratio, BO/BD
ratio + sustained/failure ratios, up/down-close %, and 52-week distance-band
percentages + net H-L spreads.

## The upstream contract: `breadth_counts` table (verbatim DDL)

GLM's module upserts one row per `trade_date` into this table. Build against this exact
schema — every column is an `INTEGER` count, one row per trading day, `trade_date` as
the primary key (ISO `'YYYY-MM-DD'` string):

```sql
-- One row per trade_date. All counts are point-in-time (computed once for that date's
-- close, never revised). Additive with breadth_daily; does not replace it.
CREATE TABLE IF NOT EXISTS breadth_counts (
    trade_date            TEXT PRIMARY KEY,
    total_universe        INTEGER,
    up_4pct               INTEGER,
    down_4pct             INTEGER,
    high_vol               INTEGER,
    low_vol                INTEGER,
    range_contraction      INTEGER,  -- range <= 3%
    range_expansion         INTEGER,  -- range >= 5.01%
    close_upper_half        INTEGER,  -- expansion candles only
    close_lower_half        INTEGER,  -- expansion candles only
    breakouts               INTEGER,
    breakout_sustained      INTEGER,
    breakout_failed         INTEGER,
    breakdowns              INTEGER,
    breakdown_sustained     INTEGER,
    breakdown_failed        INTEGER,
    up_15pct_5d             INTEGER,
    down_15pct_5d           INTEGER,
    up_25pct_20d            INTEGER,
    down_25pct_20d          INTEGER,
    above_10pct_10dema      INTEGER,
    below_10pct_10dema      INTEGER,
    above_10dema            INTEGER,
    above_20dema            INTEGER,
    above_50dema            INTEGER,
    above_200dema           INTEGER,
    new_52wk_high           INTEGER,
    new_52wk_low            INTEGER,
    from_52wh_15pct         INTEGER,
    from_52wh_30pct         INTEGER,
    from_52wh_50pct         INTEGER,
    from_52wh_70pct         INTEGER,
    from_52wh_70pct_plus    INTEGER,
    from_52wl_15pct         INTEGER,
    from_52wl_30pct         INTEGER,
    from_52wl_50pct         INTEGER,
    from_52wl_90pct         INTEGER,
    from_52wl_150pct        INTEGER,
    from_52wl_150pct_plus   INTEGER,
    source                  TEXT DEFAULT 'breadth_counts',
    ingested_at             TEXT DEFAULT (datetime('now'))
);
```

`total_universe` is the denominator for every percentage below. If `total_universe` is
`0` or `NULL` for a row, treat every ratio/percentage derived from it as unavailable for
that date (skip the row from time-series output rather than dividing by zero or
inserting a fabricated `0`/`None` placeholder that looks like real data — see "honest
empty" rule below).

## Ground truth for every formula — quote it, don't reinterpret it

These are reverse-engineered from a verified source workbook
(`Market Breadth V2.0.xlsm`, documented in `manas_os/design/study/REVERSE_ENGINEERING.md`
in the real repo, §2a "Criteria dictionary" and §2 "Formula map", quoted verbatim below).
Ground every function's docstring in the matching line.

### Criteria dictionary (verbatim from the workbook's own "Version History" sheet)

| Metric | Criteria (verbatim) |
|---|---|
| Volatility Ratio | `Range Expansion / Range Contraction` |
| Volume Ratio | `Above Avg. Volume / Below Avg. Volume` |
| UH/LH Ratio | `Close > 50% / Close < 50%` |
| BO / BD Ratio | `Breakout / Breakdown` |
| Up Close % | `4% Advance / Breakout` |
| Down Close % | `4% Decline / Breakdown` |
| BO S/F Ratio | `Breakout Sustained / Breakout Failed` |
| BD S/F Ratio | `Breakdown Sustained / Breakdown Failure` |
| 15% H/L Ratio | `Within 15% from 52 WH / Within 15% from 52 WL` |
| 30% H/L Ratio | `Within 30% from 52 WH / Within 30% from 52 WL` |

### Formula map (verbatim cell logic, from `Breadth` and `Market Map` sheets)

```
NET BREADTH        = (4up% - 4dn%) * 100                          [percentage points]
VOLUME RATIO        = (high_vol/universe) / (low_vol/universe)
                     = high_vol / low_vol                          [simplifies; universe cancels]
VOLATILITY RATIO     = (range_expansion/universe) / (range_contraction/universe)
                      = range_expansion / range_contraction        [simplifies; universe cancels]
UP CLOSE %            = (close_upper_half/universe) / (range_expansion/universe)
                       = close_upper_half / range_expansion        [Breadth col P; "Close > 50% of Range-Exp"]
DOWN CLOSE %          = close_lower_half / range_expansion         [Breadth col Q]
UH/LH NET (pp)        = (UP_CLOSE_% - DOWN_CLOSE_%) * 100           [Breadth col R]
BO/BD RATIO           = breakouts / breakdowns                      [Breadth col S; note: universe cancels here too]
UP CLOSE % (alt, BO-denominated)  = up_4pct / breakouts              [Breadth col U — this is the "Up Close %"
                                                                        definition the Dashboard actually surfaces,
                                                                        per REVERSE_ENGINEERING.md §2b quirk 3]
DOWN CLOSE % (alt, BD-denominated) = down_4pct / breakdowns          [Breadth col Z]
BO SUSTAINED RATIO     = breakout_sustained / breakouts               [Breadth col V]
BO FAILED RATIO        = breakout_failed / breakouts                  [Breadth col W]
BO S/F RATIO           = breakout_sustained / breakout_failed         [Breadth col X]
BD SUSTAINED RATIO      = breakdown_sustained / breakdowns             [Breadth col AA]
BD FAILED RATIO         = breakdown_failed / breakdowns                [Breadth col AB]
BD S/F RATIO            = breakdown_sustained / breakdown_failed       [Breadth col AC]
NET NH-NL (pp)           = (new_52wk_high/universe - new_52wk_low/universe) * 100   [Market Map col I]
NET 15% H-L (pp)          = (from_52wh_15pct/universe - from_52wl_15pct/universe) * 100   [Market Map col J]
NET 30% H-L (pp)           = ((from_52wh_15pct + from_52wh_30pct)/universe
                              - (from_52wl_15pct + from_52wl_30pct)/universe) * 100   [Market Map col K]
FOSBACK HL LOGIC CALC        = min(new_52wk_high/universe, new_52wk_low/universe) * 100   [Market Map col W]
```

### §2b quirks — BINDING, resolved for this port (do not "correct" these back)

1. **"Up Close %" has two competing definitions in the original workbook** (different
   denominators): `close_upper_half / range_expansion` (Breadth col P) vs.
   `up_4pct / breakouts` (Breadth col U). The workbook's Dashboard surfaces the
   **breakout-denominated** one (col U). This port keeps **both**, distinctly named:
   expose `up_close_pct_range_denom` (range-expansion-denominated, col P/Q logic) AND
   `up_close_pct` / `down_close_pct` (breakout/breakdown-denominated, col U/Z logic — the
   one that matches the criteria-dictionary line `Up Close % = 4% Advance / Breakout`).
   Do not silently drop one; label clearly.
2. **Net breadth and net NH-NL and net H-L spreads are percentage points**, i.e.
   `(fractionA - fractionB) * 100`, not raw fractions and not raw counts. Keep this
   convention for every "net" function you write.
3. **Universe cancels out of most ratio formulas** (e.g. `volume_ratio`,
   `volatility_ratio`, `bo_bd_ratio`) because both numerator and denominator are
   `count/universe` — so you may compute directly from the raw counts
   (`high_vol/low_vol` etc.) without re-deriving the percentage first. This is
   mathematically equivalent to the workbook's two-step formula and is the simpler,
   correct implementation. Still guard the zero-denominator case explicitly.
4. **Fosback Hi-Low Logic Index**: `min(newHighs%, newLows%) * 100`, where
   `newHighs% = new_52wk_high / total_universe` and `newLows% = new_52wk_low /
   total_universe`. Fosback's insight (embed in your docstring): in a healthy trend,
   either highs OR lows dominate breadth (one side is near zero); when BOTH new-highs%
   and new-lows% are simultaneously elevated, the market is internally conflicted — a
   transition/panic signal. **The workbook's own daily-index value ("HL LOGIC INDEX",
   Market Map col X) had no discoverable formula in the source** — it is documented in
   the workbook's changelog as "Added Hi-Low Logic Index (v2.0.5)" but the live cell was
   empty in every sampled row. The standard/canonical Fosback construction (which this
   port adopts, since the raw daily value alone is just `min(nh%, nl%)*100` per col W)
   is a **10-trading-day simple moving average of the daily `HL LOGIC CALC` value**
   (col W). Implement `fosback_hl_logic_index` as: compute the daily
   `min(nh%, nl%) * 100` series, then return its trailing 10-session SMA. Flag this in
   your response as a documented assumption (the raw workbook cell was blank; the
   10-day SMA is the standard public formulation of the Fosback index, not literally
   read off a cell) — do not present it as if verified against the workbook.
5. **52-week distance bands are NOT mutually exclusive "just this band" buckets.**
   `from_52wh_30pct` includes stocks also captured in `from_52wh_15pct` (a stock within
   15% of its high is definitionally also within 30%). When computing percentages,
   divide each band's raw count by `total_universe` directly — do not attempt to
   subtract inner bands to get an "exclusive" bucket; that is not how the source counts
   were defined (see GLM's ingest handoff, decision 11, for the same binding
   non-exclusivity rule on the count side).

## Function contract

All functions take `(conn, on_or_before, days)` except `summary`, which takes
`(conn, date)`. Signature and behavior, exactly:

```python
def net_nh_nl(conn, on_or_before: str, days: int) -> list[dict]:
    """Net (new-52wk-high% - new-52wk-low%) * 100, per REVERSE_ENGINEERING.md Market Map
    col I. One dict per trading day in the window: {"trade_date": str, "value": float}.
    Returns [] if breadth_counts has no rows in the window, or if every row in the
    window has total_universe NULL/0 (nothing to divide by) — never fabricate.
    """
```

Every time-series function follows this shape:
- `conn`: an open `sqlite3.Connection` to a DB containing `breadth_counts`.
- `on_or_before`: ISO date string; the window is the `days` most recent trading days
  with a `breadth_counts` row where `trade_date <= on_or_before` (order by `trade_date`
  ascending in the returned list — oldest first, so callers can plot/chart directly).
- `days`: window size (int). If fewer than `days` rows exist at/before `on_or_before`,
  return whatever rows DO exist (don't pad or fabricate to reach `days`) — except where
  a specific function needs a minimum lookback to be meaningful (e.g. the Fosback
  10-day SMA needs at least 10 raw daily values to produce even its first SMA point;
  if fewer than 10 raw rows exist, return `[]` for that function specifically, since a
  partial-window SMA would misrepresent the index — note this exception in your
  docstring).
- Each dict has `"trade_date"` plus the metric-specific value key(s) (e.g. `"value"` for
  single-metric functions, or named keys for multi-value functions like
  `bo_bd_ratios` below).
- **Honest-empty rule (binding):** if the table is empty, missing entirely (a caught
  `sqlite3.OperationalError` on a missing table should NOT crash the whole analytics
  call — catch it and return `[]`), or has no rows with usable denominators in the
  window, return `[]`. Never return a list of `0.0`s or `None`s dressed up as real data
  points — an empty list is the honest signal that there is nothing to show.

Functions to implement (one function per row, exact names):

1. `net_nh_nl(conn, on_or_before, days) -> list[dict]` — `{"trade_date", "value"}`, pp.
2. `fosback_hl_logic_index(conn, on_or_before, days) -> list[dict]` — `{"trade_date",
   "value"}`; the 10-day-SMA-of-daily-min construction per quirk 4 above. `days` here
   means days of **output** (post-SMA) points, so internally you need `days + 9` raw
   rows of history to produce `days` SMA points.
3. `volatility_ratio(conn, on_or_before, days) -> list[dict]` — `{"trade_date",
   "value"}` = `range_expansion / range_contraction` (guard `range_contraction == 0` ->
   skip that day's point rather than raising or inserting `inf`).
4. `volume_ratio(conn, on_or_before, days) -> list[dict]` — `{"trade_date", "value"}` =
   `high_vol / low_vol` (same zero-guard).
5. `bo_bd_ratios(conn, on_or_before, days) -> list[dict]` — one dict per day with:
   `"trade_date"`, `"bo_bd_ratio"` (breakouts/breakdowns), `"bo_sustained_ratio"`
   (breakout_sustained/breakouts), `"bo_failed_ratio"` (breakout_failed/breakouts),
   `"bo_sf_ratio"` (breakout_sustained/breakout_failed), `"bd_sustained_ratio"`
   (breakdown_sustained/breakdowns), `"bd_failed_ratio"`
   (breakdown_failed/breakdowns), `"bd_sf_ratio"`
   (breakdown_sustained/breakdown_failed). Any individual sub-ratio whose denominator is
   0 for that day is set to `None` in that day's dict (not dropped, not `inf`) — only
   drop the whole day if `total_universe` itself is missing.
6. `close_pct_ratios(conn, on_or_before, days) -> list[dict]` — one dict per day with:
   `"trade_date"`, `"up_close_pct"` (up_4pct/breakouts, the Dashboard-surfaced
   definition), `"down_close_pct"` (down_4pct/breakdowns),
   `"up_close_pct_range_denom"` (close_upper_half/range_expansion),
   `"down_close_pct_range_denom"` (close_lower_half/range_expansion). Same
   zero-denominator -> `None` per sub-value rule as #5.
7. `distance_band_pct(conn, on_or_before, days) -> list[dict]` — one dict per day with
   `"trade_date"` plus a percentage (count/total_universe * 100) for each of:
   `from_52wh_15pct`, `from_52wh_30pct`, `from_52wh_50pct`, `from_52wh_70pct`,
   `from_52wh_70pct_plus`, `from_52wl_15pct`, `from_52wl_30pct`, `from_52wl_50pct`,
   `from_52wl_90pct`, `from_52wl_150pct`, `from_52wl_150pct_plus` (11 keys, named
   identically to the source columns, values as percentages 0-100).
8. `net_hl_spreads(conn, on_or_before, days) -> list[dict]` — one dict per day with
   `"trade_date"`, `"net_15pct_hl"` (= `(from_52wh_15pct - from_52wl_15pct) /
   total_universe * 100`), `"net_30pct_hl"` (= `((from_52wh_15pct + from_52wh_30pct) -
   (from_52wl_15pct + from_52wl_30pct)) / total_universe * 100`, per the Market Map col
   K formula which sums the 15% and 30% bands before netting).
9. `summary(conn, date) -> dict` — the latest values as of `date` (i.e. the
   `breadth_counts` row with `trade_date <= date` closest to `date`, or exactly `date`
   if present), flattening the single-day outputs of functions 1, 3, 4, 6, 7, 8 (and, if
   at least 10 raw days of history are available at/before `date`, function 2) into one
   dict keyed by metric name plus `"as_of"` (the actual `trade_date` used, which may be
   earlier than `date` if `date` itself has no row). Return `{}` (empty dict, not `None`
   and not a dict of `None`s) if there is no usable `breadth_counts` row at or before
   `date`.

## Dependency constraints

- **Stdlib + sqlite3 only.** No pandas, no numpy. These are pure Python functions over
  a `sqlite3.Connection` — every windowed computation is a single parameterized SQL
  query (`ORDER BY trade_date DESC LIMIT ?` then reverse in Python, or `ORDER BY
  trade_date ASC` with a subquery — your choice) plus Python-level list/dict
  arithmetic. No global mutable state; every function takes `conn` explicitly (no
  module-level connection caching).
- Parameterized SQL only; never string-format a value into a query.
- Match repo docstring style: each function's docstring should open by naming which
  REVERSE_ENGINEERING.md formula it implements (as done in the contract example above),
  so a reviewer can trace code back to source without re-deriving the math.

## Tests — `manas_os/tests/test_breadth_analytics.py`

Seed an in-memory `sqlite3` connection with the `breadth_counts` DDL above and insert a
small number of hand-picked rows (5-15 trading days is enough, except for
`fosback_hl_logic_index` which needs >=10 rows to produce any output — seed at least 12
for that test) with realistic-looking counts. For each function, hand-compute the
expected output for at least one row and assert against it, showing your arithmetic in
a comment, e.g.:

```python
# day 3: breakouts=40, breakdowns=25 -> bo_bd_ratio = 40/25 = 1.6
```

Cover:
1. `net_nh_nl` — one worked example, plus a case where `total_universe` is 0/NULL for
   one row in the window and confirm that row is excluded (not a 0.0/None entry).
2. `fosback_hl_logic_index` — a 12-row fixture, confirm the function returns exactly
   `12 - 9 = 3` SMA points (first point needs days 1-10, etc.) with one hand-computed
   value, AND a separate fixture with only 5 rows confirming it returns `[]`.
3. `volatility_ratio` and `volume_ratio` — one normal worked example each, plus a
   zero-denominator day confirming that day is skipped (not `inf`/crash).
4. `bo_bd_ratios` — one worked example covering all 7 sub-ratios, plus a case where
   `breakouts == 0` for a day confirming the affected sub-ratios are `None` while
   `total_universe` being present still keeps the day's dict in the output.
5. `close_pct_ratios` — one worked example covering all 4 keys, demonstrating the two
   different "Up Close %" definitions produce genuinely different numbers on the same
   fixture row (to prove quirk 1 is actually honored, not collapsed to one value).
6. `distance_band_pct` — one worked example checking at least 3 of the 11 keys.
7. `net_hl_spreads` — one worked example for both `net_15pct_hl` and `net_30pct_hl`.
8. `summary` — one worked example asserting the flattened dict contains the expected
   keys/values for a seeded date, AND a case with an empty table asserting `summary`
   returns `{}` and every list-returning function returns `[]` (the honest-empty rule).

## Constraints (repeat, binding)

- **NEW FILES ONLY**: `manas_os/regime/breadth_analytics.py` and
  `manas_os/tests/test_breadth_analytics.py`. Do not edit `schema.sql`, `app.py`, any
  CLI entrypoint, GLM's ingest module, or any other existing file, and do not emit a
  diff against them.
- stdlib + sqlite3 only (no pandas/numpy).
- Match repo code style (docstrings citing the source formula, type hints via `from
  __future__ import annotations`, parameterized SQL).
- Honest-empty always: never fabricate a data point when the underlying count is
  missing or zero-denominator; return `[]`/`{}`/`None` per the rules above instead.
- Output = two complete files, plus a short list of your assumptions and anything you
  found ambiguous while implementing (especially the Fosback 10-day-SMA construction in
  quirk 4, since the workbook's own cell was blank and this is a documented judgment
  call, not a verified read).

---

Reply with the complete files in separate code blocks + BACKEND WIRING NOTES for the
maintainer + assumptions. Your code will be reconciled and QC'd; flag uncertainty rather
than inventing.
