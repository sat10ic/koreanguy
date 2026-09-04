# HANDOFF — Breadth Counts Ingest Module (for GLM, external chat, no repo access)

You are writing code for a repo you cannot see. Everything you need — schema, code
conventions, target DDL, and the exact math — is embedded below. Do not assume any file
contents beyond what is quoted here; where something is ambiguous, say so explicitly
instead of guessing.

## What you own (strict file-ownership split)

This is one lane of a multi-model wave. A second external model (Gemini) is building a
separate analytics module against the table you produce. The repo maintainer wires
everything together by hand. **You may create ONLY these two new files:**

1. `manas_os/sources/breadth_counts.py`
2. `manas_os/tests/test_breadth_counts.py`

Do **NOT** touch, edit, or emit changes to `schema.sql`, `app.py`, `cli.py`, the pipeline
orchestrator, or any other existing file. The maintainer will register your stage and run
your DDL himself. If your module needs the target table to exist, define its DDL as a
module-level string constant inside `breadth_counts.py` (spec below) — do not attempt to
execute a schema migration against a live orchestrator.

## The goal, one line

Given `run_date`, compute ~26 daily breadth COUNT metrics from OUR OWN price universe
(not any external sheet) and upsert one row into a new `breadth_counts` table, keyed by
`trade_date`. This is Step 0 of a larger enrichment wave — a second model builds ratio/
percentage analytics on top of your counts later; you are the raw-count layer.

## Ground truth for every formula: quote it, don't reinterpret it

The counts you must produce are reverse-engineered from a verified source workbook
(`Market Breadth V2.0.xlsm`, documented in `manas_os/design/study/REVERSE_ENGINEERING.md`
in the real repo). The verbatim criteria dictionary (quoted from the workbook's own
"Version History" sheet) is:

| Metric | Criteria (verbatim) |
|---|---|
| Universe | `CMP >= 1;` |
| 4% Advance | `Net Change % > = 4%` |
| 4% Decline | `Net Change % < = -4%` |
| Range Expansion | `Range > = 5.01%` |
| Range Contraction | `Range < = 3%` |
| Above Avg. Volume | `V > 1.5x 20 DMA` |
| Below Avg. Volume | `V < 0.5x 20 DMA` |
| Close > 50% | `Close > 50% of Daily Range on a Range Expansion candle` |
| Close < 50% | `Close <= 50% of Daily Range on a Range Expansion candle` |
| Breakout | `Today High > = 4% from Previous Close` |
| Breakdown | `Today's Low < = 4% from Previous Close` |
| Breakout Sustained | `Closes within 40% (of Range) from highs on Breakout Day` |
| Breakout Failed | `Closes below 40% (of Range) from highs on Breakout Day` |
| Breakdown Sustained | `Closes within 40% (of Range) from lows on the Breakdown Day` |
| Breakdown Failed | `Closes above 40% (of Range) from lows on the Breakdown Day` |

Column dictionary (verbatim headers from the workbook's raw `Data` sheet — this is the
exhaustive list of counts you must compute, one per header):

| Header | Meaning |
|---|---|
| Total Universe | Count of stocks with CMP >= 1 (the denominator for all breadth %, but here you emit the raw COUNT) |
| 4% Up | # stocks with net change % >= +4% |
| 4% Down | # stocks with net change % <= -4% |
| High Vol | # stocks with volume > 1.5x 20-day avg volume |
| Low Vol | # stocks with volume < 0.5x 20-day avg volume |
| Range <3% | # stocks with daily range <= 3% (contraction) |
| Range 5.01%+ | # stocks with daily range >= 5.01% (expansion) |
| Close Upper Half | # stocks closing in top 50% of daily range, **on an expansion candle** |
| Close Lower Half | # stocks closing in bottom 50% of daily range, on an expansion candle |
| Breakouts | # stocks whose high >= prev_close * 1.04 |
| Breakout Sustained | # breakouts closing within 40% of range from the high |
| Breakout Failure | # breakouts closing below 40% of range from the high |
| Breakdowns | # stocks whose low <= prev_close * 0.96 |
| Breakdown Sustained | # breakdowns closing within 40% of range from the low |
| Breakdown Failure | # breakdowns closing above 40% of range from the low |
| 15% up in 5 days | # stocks up >= 15% over 5 trading days |
| 15% down in 5 days | # stocks down >= 15% over 5 trading days |
| 25% up in 20 days | # stocks up >= 25% over 20 trading days |
| 25% down in 20 days | # stocks down >= 25% over 20 trading days |
| 10% above 10 DEMA | # stocks >= 10% above their 10-day EMA |
| 10% below 10 DEMA | # stocks >= 10% below their 10-day EMA |
| Above 10 DEMA | # stocks above 10-day EMA |
| Above 20 DEMA | # stocks above 20-day EMA |
| Above 50 DEMA | # stocks above 50-day EMA |
| Above 200 DEMA | # stocks above 200-day EMA |
| 52 Week High | # new 52-week highs today |
| 52 Week Low | # new 52-week lows today |
| 15% from 52WH | # stocks within 15% of their 52-week high (close >= high * 0.85) |
| 30% from 52WH | # stocks within 30% of their 52-week high |
| 50% from 52WH | # stocks within 50% of their 52-week high |
| 70% from 52WH | # stocks within 70% of their 52-week high |
| 70% Plus From 52WH | # stocks >70% from their 52-week high (deep laggards) |
| 15% from 52WL | # stocks within 15% of their 52-week **low** (measured from the low) |
| 30% from 52WL | # stocks within 30% of their 52-week low |
| 50% from 52WL | # stocks within 50% of their 52-week low |
| 90% from 52WL | # stocks within 90% of their 52-week low |
| 150% from 52WL | # stocks within 150% of their 52-week low |
| 150% Plus From 52WL | # stocks >150% above their 52-week low (extended leaders) |

### §12 quirk decisions — BINDING, do not "correct" these

The source-of-truth doc (`REVERSE_ENGINEERING.md` §12) documents several quirks in the
original workbook. The maintainer has made these explicit, binding decisions for this
port (embedded verbatim so you don't silently pick the wrong branch):

1. **CHG% / net-change convention: divide by PREV_CLOSE, not current close.** The
   original workbook's SBE sheet has a bug where CHG% divides by the *current* price
   (`(B3-B2)/B3`) instead of the previous price (`(B3-B2)/B2`). This port explicitly
   **corrects** that: `net_change_pct = (close - prev_close) / prev_close`. All "4% Up",
   "4% Down", "15%/25% move" thresholds use this corrected `/PREV` convention — verified
   numerically in REVERSE_ENGINEERING.md (the raw workbook value 0.0100839 vs the
   standard 0.0101866 for NIFTY on 2026-07-10; we use the standard `/prev` form).
2. **52-week LOW distance bands are measured from the LOW, not the high.** The
   workbook's "Version History" sheet has a copy-paste typo labeling the low-distance
   criteria as "from 52 Week High" — this is a documented authoring bug. The actual
   formula behavior (confirmed against the `Data` sheet's AJ-AO columns) measures
   distance **from the 52-week low**: e.g. "15% from 52WL" means
   `close <= low_52wk * 1.15` (within 15% ABOVE the low), not anything relative to the
   high. Use formula behavior, never the mislabeled text.
3. **BO/BD threshold is 4% from previous close** (the workbook's v2.0.1 changelog
   changed this from an earlier 5.01% — 4% is current and correct):
   `breakout: high >= prev_close * 1.04`, `breakdown: low <= prev_close * 0.96`.
4. **Volume thresholds:** high-vol = `volume > 1.5 * avg_volume_20d`,
   low-vol = `volume < 0.5 * avg_volume_20d`. `avg_volume_20d` is the trailing 20-trading-day
   average volume **excluding today** (i.e., the 20 sessions strictly before `trade_date`).
   If fewer than 20 prior sessions exist for a symbol, skip that symbol from both the
   high-vol and low-vol counts (insufficient history) — do not fabricate a partial average.
5. **Range bands:** `daily_range_pct = (high - low) / low * 100` (percentage of the
   day's low). Contraction = `<= 3%`, expansion = `>= 5.01%`. These are mutually
   exclusive; a day with range strictly between 3% and 5.01% counts toward neither band.
6. **Close upper/lower half is defined ONLY on expansion candles** (range >= 5.01%).
   On a non-expansion candle, the stock contributes to neither "Close Upper Half" nor
   "Close Lower Half" for that day. Upper half: `close >= (high + low) / 2`. Lower half:
   `close < (high + low) / 2`.
7. **Breakout/breakdown sustained vs failed** is evaluated only among that day's
   breakouts/breakdowns, using "40% of range from the high/low":
   - Breakout sustained: `close >= high - 0.40 * (high - low)` (closed within the top
     40% of the day's range, measured down from the high).
   - Breakout failed: `close < high - 0.40 * (high - low)`.
   - Breakdown sustained: `close <= low + 0.40 * (high - low)` (closed within the
     bottom 40% of the day's range, measured up from the low).
   - Breakdown failed: `close > low + 0.40 * (high - low)`.
   - If `high == low` for a stock that day (zero range), exclude it from both
     sustained and failed counts for that side (undefined ratio) rather than dividing
     by zero or guessing a side.
8. **15%-in-5-days / 25%-in-20-days** are computed as the % move from the close N
   trading sessions ago to today's close, using OUR `daily_prices` calendar (not
   calendar days): `pct_move = (close_today - close_n_sessions_ago) / close_n_sessions_ago`.
   Up-move counts use `pct_move >= 0.15` / `>= 0.25`; down-move counts use
   `pct_move <= -0.15` / `<= -0.25`. If a symbol has fewer than N prior sessions, skip it
   from that count.
9. **DEMA = exponential moving average** (the workbook's "DEMA" is the vendor's name for
   a standard EMA, not the "double EMA" technical indicator — treat it as a plain EMA
   with the stated period, seeded by SMA of the first `period` closes, standard EMA
   recursion thereafter). "10% above/below 10 DEMA" means
   `close >= dema10 * 1.10` / `close <= dema10 * 0.90`. "Above N DEMA" means
   `close > demaN`. Compute DEMA10/20/50/200 per symbol from the trailing close series
   in `daily_prices` (there is no separate indicators table available to this module —
   compute EMA yourself, in pure Python, from a per-symbol close-price query ordered by
   `trade_date`). If a symbol has fewer closes than the EMA period requires for a stable
   seed, exclude it from that DEMA-based count for that day.
10. **New 52-week high/low** use a trailing 252-trading-session window (approximately
    52 weeks) of OUR `daily_prices` `high`/`low` columns, **not** calendar-week
    counting: `is_52wk_high = high_today >= max(high over trailing 252 sessions
    including today)`, `is_52wk_low = low_today <= min(low over trailing 252 sessions
    including today)`. If a symbol has fewer than 252 prior sessions total, still compute
    the high/low over whatever history exists (do not fabricate); this is a documented
    assumption — flag it in your response as an assumption, since it means early-history
    stocks can trivially register "new highs".
11. **52-week distance bands** (both from-high and from-low) also use the trailing
    252-session extremes computed in decision 10.
    - From-high bands, e.g. "15% from 52WH": `close >= high_52wk * (1 - 0.15)`. Bands
      are **inclusive of nearer ones being counted again in farther ones** — i.e. these
      are NOT mutually exclusive "just this band" buckets; a stock within 15% of its
      high is also, definitionally, within 30/50/70%. Compute each band count
      independently against its own threshold (do not subtract inner bands out). "70%
      Plus From 52WH" is `close < high_52wk * 0.30` (i.e., more than 70% below the
      high) — this one IS the strict complement, per the workbook's "deep laggards"
      framing.
    - From-low bands, e.g. "15% from 52WL": `close <= low_52wk * (1 + 0.15)`. Same
      non-exclusive-band logic. "150% Plus From 52WL" is `close > low_52wk * 2.50`
      (more than 150% above the low) — the strict complement, per "extended leaders."

## Universe filter (binding, all counts share it)

For a given `run_date`, the eligible universe is every row in `daily_prices` where:
`trade_date = run_date AND series = 'EQ' AND close >= 1`.

`Total Universe` count = the count of rows passing that filter. Every other count is a
subset of this same filtered set — do not apply a different universe definition per
metric.

## The real repo's `daily_prices` schema (verbatim `CREATE TABLE`, from `manas_os/db/schema.sql`)

```sql
-- One row per symbol per trading day. Delivery fields come from bhavcopy sec_bhavdata_full.
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    series        TEXT DEFAULT 'EQ',
    open          REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price    REAL, avg_price REAL,
    volume        INTEGER,
    turnover      REAL,
    num_trades    INTEGER,
    delivery_qty  INTEGER,
    delivery_pct  REAL,
    source        TEXT,                 -- 'fyers' | 'bhavcopy'
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, series)
);
```

Dates are ISO `'YYYY-MM-DD'` strings (SQLite has no native date type). `prev_close` is
already populated per row — you do not need to self-join to get the previous close, but
you WILL need to query prior sessions' `high`/`low`/`close`/`volume` for the rolling-
window metrics (volume avg, DEMA, 52wk extremes, 5d/20d moves), which `prev_close` alone
does not give you. Query by `symbol` with `trade_date <= run_date` ordered ascending,
per symbol, to build those windows.

## The target table you must emit as a DDL constant (do NOT execute a migration — just
## define this string in your module; the maintainer applies it)

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

The column NAMES above are exact and must not be renamed, reordered, or dropped.

## Repo source-module conventions — copy this pattern exactly

Every ingest/compute stage in `manas_os/sources/` follows the same shape. Here is the
**verbatim template**, `manas_os/sources/breadth_sheet.py`, showing the `run(conn,
run_date)` entry point and the `_log_run` pipeline-tracking pattern you must replicate
(adapted to your compute, not fetch, but the skeleton is identical):

```python
"""Breadth Google Sheet ingestion adapter (P0).

The breadth sheet is published as CSV. We fetch it, parse each row into a
`breadth_daily`-shaped dict, and upsert idempotently on the trade_date PK. A
`pipeline_runs` row (stage='ingest_breadth') records the outcome.

Network access is isolated in `_fetch_csv`/`run`; `parse_breadth_csv` is pure
and covered by a fixture test.
"""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime

import requests

from manas_os import config

STAGE = "ingest_breadth"
SOURCE = "breadth_sheet"

# ... column maps, parsing helpers, _norm/_clean_number/_to_int/_to_float/_to_iso_date ...

def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, dur, detail),
    )


def run(conn, run_date: str) -> dict:
    """Fetch + parse + upsert the breadth sheet; write a pipeline_runs row.

    Returns {status, rows_affected, detail}. Failures are recorded (status='fail')
    and re-raised so the orchestrator's per-stage isolation reports them.
    """
    started = time.monotonic()
    url = config.get("sources.breadth_sheet_csv_url", "")
    if not url:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "skip", 0, dur, "no breadth_sheet_csv_url configured")
        conn.commit()
        return {"status": "skip", "rows_affected": 0, "detail": "no url configured"}
    try:
        text = _fetch_csv(url)
        rows = parse_breadth_csv(text)
        written = upsert_rows(conn, rows)
        dur = time.monotonic() - started
        detail = f"parsed {len(rows)} rows, upserted {written}"
        _log_run(conn, run_date, "ok", written, dur, detail)
        conn.commit()
        return {"status": "ok", "rows_affected": written, "detail": detail}
    except Exception as exc:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "fail", 0, dur, f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
```

Your `STAGE` constant should be `"breadth_counts"` and `SOURCE` should be
`"breadth_counts"`. Your module has no network fetch — replace `_fetch_csv` with your
pure-SQL/python computation reading from `daily_prices`. Keep the exact same shape:
a private pure-compute function (unit-testable without a live DB connection beyond the
fixture), a public `run(conn, run_date) -> dict` that computes, upserts one row into
`breadth_counts`, logs to `pipeline_runs` with `stage="breadth_counts"`, commits, and
returns `{"status", "rows_affected", "detail"}`, catching and re-raising exceptions after
logging a `"fail"` row (mirror the try/except exactly).

`pipeline_runs` verbatim DDL (for reference — you write to it, you don't create it):

```sql
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    stage       TEXT NOT NULL,          -- ingest_breadth | ingest_bhavcopy | indicators | regime | scan | ...
    source      TEXT,
    status      TEXT,                   -- ok | fail | skip
    rows_affected INTEGER DEFAULT 0,
    duration_s  REAL,
    detail      TEXT,
    ran_at      TEXT DEFAULT (datetime('now'))
);
```

## Dependency constraints

- **Stdlib + sqlite3 only.** Do not import `pandas` or `numpy`. `breadth_sheet.py` (your
  template) uses only stdlib (`csv`, `io`, `time`, `datetime`) plus `requests` for its
  network fetch, which you don't need. Some other modules in this repo use pandas, but
  your module must not — it needs to be dependency-light since it runs on every EOD
  pipeline pass.
- Use parameterized SQL (`?` placeholders) everywhere; never string-format values into
  SQL.
- Match the repo's docstring/comment style: a module docstring explaining role +
  boundaries (see template), then inline comments on any non-obvious threshold.

## Function contract

```python
def run(conn, run_date: str) -> dict:
    """Compute breadth_counts for run_date from daily_prices and upsert the row.

    Idempotent: safe to re-run for the same run_date (upsert on trade_date PK).
    Returns {"status": "ok"|"skip"|"fail", "rows_affected": int, "detail": str}.
    """
```

- `run_date` is an ISO date string, e.g. `"2026-07-10"`.
- If there are zero eligible universe rows for `run_date` (e.g. date not yet ingested),
  return `{"status": "skip", "rows_affected": 0, "detail": "no eligible daily_prices rows for <date>"}`
  and log a `"skip"` pipeline_runs row — do not raise, do not insert a row of zeros.
- On success, insert/update exactly one row in `breadth_counts` for `trade_date =
  run_date`, log an `"ok"` pipeline_runs row, commit, return `{"status": "ok",
  "rows_affected": 1, "detail": ...}`.
- Factor the actual counting logic into pure, unit-testable helper functions (e.g. one
  function that takes a connection + run_date + a rolling-history lookup and returns the
  dict of counts) so your test file can exercise the math directly without going through
  the full `run()` orchestration, mirroring how `parse_breadth_csv` is separated from
  `run` in the template.

## Tests — `manas_os/tests/test_breadth_counts.py`

Build a seeded in-memory `sqlite3` fixture: `CREATE TABLE daily_prices` (use the exact
DDL above) plus your `breadth_counts` DDL constant, insert enough symbols/sessions by
hand to hand-compute expected counts for at least 2-3 worked examples covering:

1. A simple case: 3-4 symbols, one clean 4% breakout with sustained close, one 4%
   breakdown with failed close, one flat/no-signal stock, verifying `total_universe`,
   `up_4pct`/`down_4pct`, `breakouts`/`breakdowns`, `breakout_sustained`/
   `breakout_failed` all compute correctly by hand.
2. A volume + range case: symbols with hand-picked volume histories crossing the 1.5x/
   0.5x 20-day-avg thresholds, and range values straddling the 3%/5.01% bands, verifying
   `high_vol`/`low_vol`/`range_contraction`/`range_expansion`/`close_upper_half`/
   `close_lower_half`.
3. A 52-week / DEMA case: a short synthetic price history (you don't need real 252-day
   history — pick a small window and note in your test the assumption-10 caveat about
   partial history) verifying `new_52wk_high`/`new_52wk_low` and at least one distance
   band, plus one DEMA-based count (`above_10dema` or `above_10pct_10dema`).
4. Idempotency: call `run()` twice for the same `run_date` and assert exactly one row
   exists in `breadth_counts` with the same values (upsert, not duplicate insert).
5. The skip path: call `run()` for a date with no `daily_prices` rows and assert
   `status == "skip"` and no row is written to `breadth_counts`.

Show your hand-computed expected values in code comments next to each assertion so the
maintainer can verify your arithmetic without re-deriving it.

## Constraints (repeat, binding)

- **NEW FILES ONLY**: `manas_os/sources/breadth_counts.py` and
  `manas_os/tests/test_breadth_counts.py`. Do not edit `schema.sql`, `app.py`, any CLI
  entrypoint, or any other existing file, and do not emit a diff against them.
- stdlib + sqlite3 only (no pandas/numpy).
- Match repo code style (docstrings, type hints via `from __future__ import annotations`,
  parameterized SQL, the `run(conn, run_date)` / `_log_run` shape).
- Output = two complete files, plus a short list of your assumptions and anything you
  found ambiguous while implementing (e.g. edge cases in the quirk decisions above that
  weren't fully pinned down).

---

Reply with the complete files in separate code blocks + BACKEND WIRING NOTES for the
maintainer + assumptions. Your code will be reconciled and QC'd; flag uncertainty rather
than inventing.
