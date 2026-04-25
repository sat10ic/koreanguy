# SwingEdge Lite — Master Build Guide for Claude Code

**Repo location:** `~/projects/swingedge_lite/` (or wherever Sunit prefers)
**Primary reference:** `SwingEdge_Lite_Spec_v0_3.docx` — the technical spec. Claude Code MUST read this before touching code.
**Secondary reference:** this file — the sequenced build instructions.

**Status legend for each step:**
- `[MANUAL]` — Sunit does this by hand, no Claude Code involvement
- `[CODE]` — Claude Code executes the prompt, Sunit reviews and runs
- `[REVIEW]` — Pause point where Sunit reads output and decides go/no-go

---

## Before any coding: read this section first

### The non-negotiable rules

**Rule 1 — Decisions come before code.** The spec has 8 open questions (Section 13). Sunit answers all 8 in `decisions.md` BEFORE Step 2. If a decision is "I don't know yet," write that down as the decision and pick a provisional default.

**Rule 2 — Every rejected idea goes to `FUTURE.md`.** If during the build Claude Code suggests a feature that's not in the current step, Sunit does NOT implement it. It goes in `FUTURE.md` with a one-line description. Phase 1 does not expand.

**Rule 3 — Each step must run end-to-end before the next step starts.** Even with stubs. If Step 5 is "implement regime.py," the output of Step 5 must still let `run_daily.sh` execute all 8 stages without error. Stubs downstream are fine; broken pipelines are not.

**Rule 4 — Claude Code reads the spec, not just this guide.** Every prompt in this file starts with "Read `SwingEdge_Lite_Spec_v0_3.docx` sections X, Y, Z." If Claude Code skips this, the output will drift from spec.

**Rule 5 — Tests are part of the deliverable, not an afterthought.** Each step with code must include tests for that code. No exceptions. If Claude Code delivers code without tests, reject the output and request again.

**Rule 6 — Manas's rules are law. Korean builder's patterns are law. Everything else is negotiable.** If Claude Code proposes a deviation from either (e.g., "I simplified the Purple Dot rule," "I merged Layer A and Layer B"), reject it. The source material is the source of truth.

---

### Environment assumptions

- macOS M1 (Sunit's primary) or Linux (if deployed to Contabo VPS later)
- Python 3.11 in a project-local venv at `.venv/`
- Fyers API v3 credentials in `~/.fyers/` (token refresh handled separately; not in scope for Phase 1)
- `fyers-apiv3` Python package for data fetching
- SQLite 3 (system default)
- Node.js not required (dashboard is vanilla HTML/JS/CSS)
- Telegram bot already created via BotFather; chat_id and token in environment variables

### Things Claude Code MUST NOT do

- No Docker, no containers, no Kubernetes. This is a local tool.
- No FastAPI, Flask, Django, or any web framework. The dashboard is a static HTML file.
- No ORM. Raw SQL with `sqlite3` stdlib or `pandas.read_sql`.
- No React, Vue, Svelte, Next.js, Tailwind. Vanilla HTML + CSS Grid + vanilla JS only.
- No async/await in the daily pipeline. Linear, synchronous, debuggable.
- No Celery, RQ, or job queues. `cron` runs the bash script. That is the scheduler.
- No "while we're at it, let's also..." features. Scope is Phase 1 only.

---

## Step 1 — Repository skeleton `[MANUAL]`

**Sunit does this by hand. Do not invoke Claude Code.**

The point is to own the shape of the repo before automation takes over. Budget: 1–2 hours.

```bash
mkdir -p ~/projects/swingedge_lite
cd ~/projects/swingedge_lite
git init
python3.11 -m venv .venv
source .venv/bin/activate

mkdir -p data output scripts tests
touch config.yaml universe.csv watchlist.csv
touch scripts/fetch.py scripts/indicators.py scripts/regime.py \
      scripts/screen.py scripts/verify.py scripts/track.py \
      scripts/render.py scripts/notify.py scripts/watchlist_helper.py
touch tests/__init__.py
touch README.md FUTURE.md decisions.md requirements.txt .gitignore
```

Create `run_daily.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

echo "[1/8] fetch"      ; python scripts/fetch.py
echo "[2/8] indicators" ; python scripts/indicators.py
echo "[3/8] regime"     ; python scripts/regime.py
echo "[4/8] screen"     ; python scripts/screen.py
echo "[5/8] verify"     ; python scripts/verify.py
echo "[6/8] track"      ; python scripts/track.py
echo "[7/8] render"     ; python scripts/render.py
echo "[8/8] notify"     ; python scripts/notify.py
echo "done."
```

Make each stub script a one-liner:
```python
# scripts/fetch.py
if __name__ == "__main__": print("fetch.py stub — not implemented")
```

Repeat the same stub for all 8 scripts. Substitute the script name.

Create `.gitignore`:
```
.venv/
data/*.db
output/*.csv
output/*.html
output/*.json
logs/
.env
*.pyc
__pycache__/
.DS_Store
```

Commit:
```bash
chmod +x run_daily.sh
./run_daily.sh   # should print 8 "stub" messages
git add -A
git commit -m "Step 1: skeleton"
```

**`[REVIEW]` Done-when check:**
- [ ] `./run_daily.sh` runs and prints all 8 stub messages without error
- [ ] `tree -L 2` shows the directory layout from spec Section 2.2
- [ ] Git shows clean initial commit
- [ ] You can describe in one sentence what each of the 8 scripts will eventually do

If any of those is shaky, do not proceed. Re-read spec Section 2.

---

## Step 2 — Universe, configuration, and databases `[CODE]`

**Prerequisite:** `decisions.md` has answers to all 8 open questions from spec Section 13.

### Claude Code prompt

```
You are building Phase 1 of SwingEdge Lite. Read SwingEdge_Lite_Spec_v0_3.docx
sections 2.2, 3.1, 3.3, 4.5, 6.3, 8.1, 8.2, 9 before writing any code.

TASK: Set up the configuration file, universe data, and empty database schemas.

Deliverables:

1. `config.yaml` — populate with the complete structure from spec Section 9.
   Use placeholder values for secrets (e.g., FYERS_TOKEN env var reference).
   Add a top-level comment noting the file is read by every script.

2. `universe.csv` — seed with 50 liquid NSE names for the initial build.
   Columns: symbol, name, sector, industry, market_cap_cr.
   Do NOT fetch this from the internet. Hard-code 50 names covering:
   - 10 largecap (market cap > 100000 Cr): RELIANCE, TCS, HDFCBANK, INFY,
     ICICIBANK, ITC, LT, BHARTIARTL, SBIN, KOTAKBANK
   - 20 midcap (10000–100000 Cr): ZOMATO, LTTS, POLYCAB, DIVISLAB, PERSISTENT,
     JUBLFOOD, ABBOTINDIA, MPHASIS, INDHOTEL, AUROPHARMA, TORNTPHARM, TVSMOTOR,
     TRENT, DIXON, ASTRAL, COFORGE, OBEROIRLTY, LUPIN, PAGEIND, PIDILITIND
   - 20 smallcap (2000–10000 Cr): KAYNES, POLYMED, HAPPSTMNDS, RAJESHEXPO,
     KIRLOSENG, DATAPATTNS, MAPMYINDIA, TEGA, LATENTVIEW, CYIENT, KPITTECH,
     SONACOMS, FINEORG, HAPPYFORGE, ELGIEQUIP, TITAGARH, IONEXCHANG, BLUESTARCO,
     RADICO, AEGISCHEM

   All symbols must be NSE spot equity tickers without any exchange suffix
   (just "RELIANCE", not "RELIANCE.NS" or "NSE:RELIANCE-EQ").

3. `watchlist.csv` — seed with 15 names from the universe (Sunit's choice,
   but for the initial build, pick: ZOMATO, LTTS, POLYCAB, DIVISLAB, PERSISTENT,
   KAYNES, POLYMED, HAPPSTMNDS, KPITTECH, DATAPATTNS, SONACOMS, TRENT, DIXON,
   LUPIN, MAPMYINDIA).
   Columns: symbol, date_added (today's date), source_reason ("initial build").

4. `scripts/_db.py` — a helper module with functions:
   - `ohlcv_conn()` → returns sqlite3 connection to data/ohlcv.db
   - `features_conn()` → returns sqlite3 connection to data/features.db
   - `portfolio_conn()` → returns sqlite3 connection to data/portfolio_state.db
   - `init_schemas()` → creates all tables if they don't exist, idempotent

   Schemas per spec Sections 3.3, 8.2, 6.3.

5. `scripts/_config.py` — loads config.yaml and exposes it as a typed dict or
   dataclass. Single function: `load_config() → Config`.

6. Update `scripts/fetch.py` stub to call `init_schemas()` so that running the
   pipeline initializes the databases even before real fetch logic exists.

7. `requirements.txt` — pin exact versions:
   pandas>=2.2,<3.0
   numpy>=1.26,<2.0
   pandas-ta>=0.3.14b0
   fyers-apiv3>=3.1.7
   pyyaml>=6.0
   python-telegram-bot>=21.0
   pytest>=8.0
   jinja2>=3.1

   (Check the latest stable versions at the time of running; above are floor
    versions that must work.)

8. `tests/test_db_init.py` — unit test that:
   - Deletes any existing DB files in a tmp_path
   - Calls init_schemas()
   - Verifies all expected tables exist via sqlite_master query
   - Verifies column names match spec

CONSTRAINTS:
- No internet calls in this step. No "fetch the latest universe from NSE." All
  data is hand-seeded.
- No business logic. Schemas and config only.
- config.yaml must be git-committed with placeholder values. A separate file
  `.env` (gitignored) holds real secrets.

After completing, run:
  ./run_daily.sh
  pytest tests/
  sqlite3 data/ohlcv.db .schema
  sqlite3 data/features.db .schema
  sqlite3 data/portfolio_state.db .schema

All three .schema commands should show the expected tables. The pipeline
should still run and print 8 stub messages (init_schemas runs inside fetch.py
stub now).
```

**`[REVIEW]` Done-when check:**
- [ ] All three databases exist and have the right schemas
- [ ] `pytest tests/` passes
- [ ] `universe.csv` has exactly 50 rows, `watchlist.csv` has exactly 15
- [ ] Watchlist is a subset of universe
- [ ] Pipeline still runs end-to-end with stubs
- [ ] `config.yaml` contains every section from spec Section 9 (no truncation)

Git commit: `Step 2: config, universe, schemas`

---

## Step 3 — Data fetch `[CODE]`

### Claude Code prompt

```
Read SwingEdge_Lite_Spec_v0_3.docx sections 3.2, 3.3, 8.1 before writing code.

TASK: Implement fetch.py to pull daily OHLCV from Fyers API for the 50-stock
universe plus two index proxies (Nifty 50 and an equal-weighted composite of
Nifty 500 — for Phase 1 with a 50-stock universe, we'll compute the EW
composite from the universe itself).

Deliverables:

1. `scripts/fetch.py`:
   - Authenticates with Fyers using credentials from env vars (FYERS_CLIENT_ID,
     FYERS_TOKEN).
   - Reads universe.csv.
   - For each symbol, queries Fyers history endpoint with resolution="D".
   - On first run (empty ohlcv table): backfills 2 years (504 trading days).
   - On subsequent runs: fetches only from (last stored date + 1) through today.
   - Upserts into the ohlcv table (PRIMARY KEY symbol, date handles dedup).
   - Also fetches Nifty 50 index (symbol "NSE:NIFTY50-INDEX" in Fyers format)
     and stores in the same ohlcv table with symbol="_NIFTY50".
   - Computes and stores a synthetic "_NF500EW" series by taking the equal-
     weighted mean daily return across the universe and reconstructing a price
     series normalized to 1000 on the earliest available date. Store this in
     ohlcv as symbol="_NF500EW".

2. Error handling:
   - Rate limit (429): exponential backoff, 3 retries max (2s, 4s, 8s).
   - Delisted/renamed symbol (Fyers 404 equivalent): log warning, skip, continue.
   - Expired token: exit with code 2 and message "Fyers token expired. Run
     scripts/refresh_token.py."
   - Network failure: log and continue with partial data; exit code 1 if
     < 95% of universe was updated.

3. Logging:
   - All fetch activity logs to `logs/fetch.log` (create the logs/ dir if absent).
   - Summary line at end: "Fetched N/50 symbols through YYYY-MM-DD. Failures: X, Y."

4. Config additions:
   - Add `fetch.backfill_days: 504` to config.yaml if not present.
   - Add `fetch.batch_delay_ms: 200` to respect rate limits between symbol calls.

5. Tests:
   - `tests/test_fetch.py` with a Fyers API mocked via unittest.mock:
     * test_fresh_backfill: empty DB → 504 rows per symbol inserted
     * test_incremental: DB with data through T-1 → only today's row added
     * test_skip_delisted: one symbol raises 404 → others still succeed
     * test_token_expired: exits with code 2
   - Do NOT make real API calls in tests.

6. A separate manual script `scripts/refresh_token.py` that walks through the
   Fyers OAuth URL flow to get a fresh token. This is run manually by Sunit when
   the daily token expires; it is not part of the cron pipeline.

CONSTRAINTS:
- Do not fetch Nifty 500 yet. Universe is 50 names for this phase.
- Do not compute any indicators. fetch.py only pulls raw OHLCV.
- Do not add a UI, progress bar, or colored output. Plain logging.

Verification after completion:
  ./run_daily.sh
  sqlite3 data/ohlcv.db "SELECT COUNT(*) FROM ohlcv;"
  # Expect ~25,000 rows (50 symbols × ~500 days)
  sqlite3 data/ohlcv.db "SELECT symbol, COUNT(*) FROM ohlcv GROUP BY symbol;"
  # Expect ~500 per symbol, plus 2 rows for _NIFTY50 and _NF500EW
  sqlite3 data/ohlcv.db "SELECT MAX(date) FROM ohlcv;"
  # Expect today or most recent trading day
```

**`[REVIEW]` Done-when check:**
- [ ] Row counts as expected above
- [ ] `_NIFTY50` and `_NF500EW` both present with ~500 rows each
- [ ] Running the pipeline twice doesn't duplicate rows
- [ ] Tests pass without making real API calls
- [ ] `logs/fetch.log` has sensible output

Git commit: `Step 3: fetch.py with Fyers integration`

---

## Step 4 — Indicators and Purple Dot `[CODE]`

### Claude Code prompt

```
Read SwingEdge_Lite_Spec_v0_3.docx sections 2.3 (Purple Dot), 4.3, 8.2 before
writing code.

TASK: Implement indicators.py to compute all per-symbol-per-day features.

Deliverables:

1. `scripts/indicators.py`:
   - Reads all symbols from ohlcv.db (incl. _NIFTY50 and _NF500EW).
   - Computes features incrementally (only for (symbol, date) rows missing
     from features table).
   - Features per spec Section 8.2:
     SMA(20, 50, 200), EMA(10, 20, 50), ATR(14), ADV(20),
     high_126, low_126, ret_1d, ret_5d, ret_21d,
     purple_dot (0/1), purple_dot_count_30d.
   - Use pandas-ta where available; hand-compute only if pandas-ta lacks
     something (it has all of the above).

2. Purple Dot computation (from spec 2.3 / 4.3):
   - pct_move = abs(close / prev_close - 1)
   - Fires if pct_move >= config.purple_dot.pct_move_threshold (default 0.05)
     AND volume >= threshold scaled by market cap:
       - market_cap_cr > 10000: 1,000,000 shares
       - market_cap_cr 2000-10000: 500,000 shares
       - market_cap_cr < 2000: 300,000 shares
   - Market cap is read from universe.csv (which now has market_cap_cr column).
   - For index proxies (_NIFTY50, _NF500EW), Purple Dot is always 0.
   - purple_dot_count_30d is a rolling 30-session sum of purple_dot.

3. Tests in `tests/test_indicators.py`:
   - test_sma_matches_pandas_ta: synthetic 100-day series, SMA(20) matches
     pandas-ta reference exactly.
   - test_ema_matches_pandas_ta: same for EMA(10).
   - test_atr_matches_pandas_ta: same for ATR(14).
   - test_purple_dot_fires: synthetic bar with 6% move + 1.5M volume (largecap)
     → purple_dot = 1.
   - test_purple_dot_no_fire_small_move: 4% move + 2M volume → 0.
   - test_purple_dot_no_fire_low_volume: 6% move + 900K volume (largecap) → 0.
   - test_purple_dot_smallcap_threshold: 6% move + 350K volume on a smallcap
     (market_cap_cr < 2000) → 1.
   - test_purple_dot_count_30d: a sequence of 40 days with purple_dot firing
     on days 5, 10, 15 → count on day 30 = 3, count on day 36 = 2.
   - test_incremental_computation: insert new OHLCV row, re-run indicators,
     verify only that new row's features were computed (not recomputed for
     existing rows).

4. Performance: the full 50-symbol × 504-day backfill must complete in under
   60 seconds on an M1 Mac. If pandas-ta is too slow, drop to pandas rolling
   directly.

CONSTRAINTS:
- No business logic about setups or signals. Only per-row features.
- Do not touch regime or grade computation; those come in later steps.
- Index proxies (_NIFTY50, _NF500EW) get the same features computed except
  purple_dot and purple_dot_count_30d which stay 0.

Verification:
  ./run_daily.sh
  pytest tests/test_indicators.py -v
  sqlite3 data/features.db "SELECT COUNT(*) FROM features;"
  # Expect ~25,000+ rows (matches ohlcv count minus NaN warmup periods)
  sqlite3 data/features.db "SELECT symbol, SUM(purple_dot) FROM features \
    GROUP BY symbol ORDER BY 2 DESC LIMIT 10;"
  # Shows top 10 symbols by cumulative purple dots over 2 years
  # Sanity check: these should be stocks Sunit recognizes as having had
  # big news/volume events.
```

**`[REVIEW]` Done-when check:**
- [ ] All indicator tests pass
- [ ] Purple Dot tests pass including smallcap threshold test
- [ ] Top-10 Purple Dot list passes the eye-test (Sunit recognizes at least 6 of 10)
- [ ] Running the pipeline twice doesn't recompute (check timestamps or add a timing assertion)

Git commit: `Step 4: indicators and Purple Dot`

---

## Step 5 — Regime layer (stubbed, then real) `[CODE]`

### Step 5a — Stub

### Claude Code prompt

```
Read spec Section 3 in full. We are implementing regime.py in two passes:
first a stub that always returns RISK_ON, then the real 4-pillar logic.

This is Step 5a — the stub.

TASK: Implement regime.py to always return RISK_ON and write regime_today.json
per spec Section 3.4.

Deliverable:
- scripts/regime.py that writes output/regime_today.json with:
  - regime = "RISK_ON"
  - pillars_passed = 4
  - pillars with all 4 showing pass=true and placeholder values
  - date = today (use most recent trading date from ohlcv)
  - risk_pct_override = 0.0025

- tests/test_regime_stub.py verifies:
  - File is written
  - JSON is valid
  - regime == "RISK_ON"

Keep this deliberately thin. Real regime logic is Step 5b.
```

### Step 5b — Real regime

### Claude Code prompt

```
Read spec Section 3 in full, especially 3.1 (the 4 pillars) and 3.2
(regime-state gating). Read decisions.md to confirm any user overrides.

TASK: Replace the stub in regime.py with real 4-pillar logic.

Deliverables:

1. regime.py computes the four pillars using data from features.db:

   Pillar 1 — Trend:
     _NF500EW close > _NF500EW SMA(21)
     AND SMA(21) is rising: today's SMA(21) > SMA(21) from 5 sessions ago.

   Pillar 2 — Not overbought:
     Nifty 50 RSI(14) < config.regime.rsi_overbought (default 75).
     (You'll need to add RSI(14) to the indicators in Step 4's features table.
      If it's missing, update indicators.py and re-run.)

   Pillar 3 — Breadth:
     Fraction of universe (EXCLUDING index proxies) with close > SMA(50)
     is >= config.regime.breadth_threshold (default 0.45).

   Pillar 4 — Volatility:
     |Nifty50 close − Nifty50 EMA(21)| < config.regime.vol_atr_multiple
     × Nifty50 ATR(21).
     (If ATR(21) isn't in features, add it in indicators.py.)

2. State assignment:
   - 3 or 4 pillars pass → RISK_ON
   - 2 pillars pass → CAUTION
   - 0 or 1 pillars pass → RISK_OFF

3. Output JSON exactly per spec Section 3.4 schema.

4. Tests tests/test_regime_real.py:
   - test_all_pass_gives_risk_on: construct a features snapshot where all 4
     pillars clearly pass → "RISK_ON", pillars_passed == 4.
   - test_two_pass_gives_caution: 2 pass, 2 fail → "CAUTION".
   - test_zero_pass_gives_risk_off: all 4 fail → "RISK_OFF".
   - test_boundary_three_pass: exactly 3 pass → "RISK_ON".
   - test_missing_data_gracefully: if _NF500EW has no SMA(21) data yet
     (less than 21 days of history), pillar 1 should fail, not crash.

5. If indicators.py was updated to add RSI(14) or ATR(21), also add unit
   tests for those.

CONSTRAINTS:
- Breadth threshold and volatility multiple come from config, not hard-coded.
- The regime output MUST be written even if some pillars could not be computed
  (those pillars fail rather than crashing the script).
- Do not gate downstream layers yet. That happens in verify.py and notify.py
  in later steps.

Verification:
  ./run_daily.sh
  cat output/regime_today.json
  pytest tests/test_regime_real.py -v

Manual sanity check:
  Pick a known bear market week (e.g., mid-March 2025 if the correction
  happened then, otherwise any week where Nifty fell >3%).
  Query features.db for that date range and manually compute what the
  regime should have been. Update a test fixture to lock that in.
```

**`[REVIEW]` Done-when check:**
- [ ] Stub version ran and wrote valid JSON
- [ ] Real version passes all 5 tests
- [ ] Eye-test: pick today's actual market state and see if the regime output matches your intuition
- [ ] Eye-test: pick a known bad day from 2025 and verify regime was CAUTION or RISK_OFF

Git commit: `Step 5a: regime stub` then `Step 5b: regime 4-pillars`

---

## Step 6 — Screen layer `[CODE]`

### Claude Code prompt

```
Read spec Section 4 in full before writing code.

TASK: Implement screen.py to evaluate every universe stock daily against the
bread-and-butter setup and produce screen_today.csv per spec 4.5.

Deliverables:

1. scripts/screen.py:
   - Reads features.db for the most recent trading date and the previous date.
   - For each symbol (excluding index proxies):
     a) Evaluates bread-and-butter setup (spec 4.1):
        - uptrend_pass: close > SMA(200) AND high_126 >= 1.25 * low_126
        - correction_pass: close <= 0.97 * high_126 AND close >= 0.70 * high_126
        - reclaim_pass: today.close > today.sma20 AND
          yesterday.close <= yesterday.sma20
        - setup_pass = 1 if all three; else 0
     b) Computes RS_score = 0.20*ret_1d + 0.30*ret_5d + 0.50*ret_21d
     c) Assigns to Bullish (close > sma50) or Bearish bucket
     d) Within bucket, ranks by RS_score and assigns grade per spec 4.2 table
     e) Computes extended flags (spec 4.4):
        - extended_yellow: close > sma50 + 5*atr14
        - extended_red: close > sma50 + 7*atr14
     f) watchlist_member: 1 if symbol in watchlist.csv else 0

2. Writes output/screen_today.csv with the full column set from spec 4.5.

3. Grade assignment must be deterministic across runs. Use pandas rank with
   method='first' (not 'average') and percentile logic per spec 4.2.

4. For yesterday's grade (grade_yesterday column), re-run the grading for
   yesterday's snapshot and join. Store both.

5. Tests tests/test_screen.py:
   - test_setup_all_three_pass: synthetic stock with uptrend + shallow correction
     + today-reclaim → setup_pass = 1.
   - test_setup_correction_too_deep: 35% pullback → correction_pass = 0,
     setup_pass = 0.
   - test_setup_no_uptrend: stock below SMA200 → uptrend_pass = 0.
   - test_setup_already_above_sma20: yesterday was also above → reclaim_pass = 0.
   - test_grade_bullish_top_5pct: top 5% by RS_score in bullish bucket → A+.
   - test_grade_bearish_worst_5: bottom 5 by RS_score in bearish bucket → G.
   - test_bucket_split_on_sma50: stock exactly at SMA50 goes to Bearish
     (close <= sma50 is Bearish; close > sma50 is Bullish).
   - test_extended_yellow_only: close at sma50 + 5.5*atr → extended_yellow=1,
     extended_red=0.
   - test_watchlist_member_flag: symbol in watchlist.csv → watchlist_member=1.

6. CSV must be sorted by grade (A+ first, G last) then by RS_score descending
   within each grade.

CONSTRAINTS:
- No filtering in screen.py. Every universe stock gets a row.
- No verification logic here (that's Step 7).
- No regime gating here either.
- Index proxies (_NIFTY50, _NF500EW) are excluded from the CSV entirely.

Verification:
  ./run_daily.sh
  wc -l output/screen_today.csv            # ~51 (50 + header)
  head output/screen_today.csv
  # Inspect top of the file: A+ grades should be stocks that were strong recently
  awk -F, '$19==1 {print}' output/screen_today.csv | wc -l
  # Count of setup_pass=1 rows; should be 0-5 on a typical day
  pytest tests/test_screen.py -v

Eye-test:
  Look at the A+ and A rows. Are these stocks you'd expect to be strong?
  Look at the setup_pass=1 rows. Pull up their charts on TradingView and
  check: does each one visibly show uptrend → shallow correction → SMA20
  reclaim today? If more than one is obviously wrong, something is off in
  the implementation.
```

**`[REVIEW]` Done-when check:**
- [ ] `screen_today.csv` has 50 rows plus header, all columns present
- [ ] All tests pass
- [ ] Eye-test on A+ grades passes (Sunit recognizes stocks as strong)
- [ ] Eye-test on setup_pass=1 rows passes (charts actually show the pattern)

Git commit: `Step 6: screen layer with setup evaluation and RS grading`

---

## Step 7 — Verify Layer A `[CODE]`

### Claude Code prompt

```
Read spec Section 5 (Verify), paying close attention to 5.1 (Layer A),
5.3 (Watchlist split), 5.5 (Position sizing).

TASK: Implement verify.py with Layer A only. Layer B is stubbed as always-pass
for this step. Layer B is added in Step 8.

Deliverables:

1. scripts/verify.py:
   - Reads output/screen_today.csv.
   - Filters to setup_pass == 1 (bread-and-butter setup must have fired today).
   - Applies Layer A (spec 5.1):
     a) Fetches last 3 sessions of grades for the symbol from features.db +
        screen history (you may need to snapshot grade history; for Phase 1
        simplicity, recompute screen grades for T-1 and T-2 on the fly).
     b) Layer A checks:
        - Last 3 sessions: grade is A+, A, or A-
        - Average RS_score over last 3 sessions >= 85 (percentile within bullish)
        - No grade downgrades in last 5 sessions
        - Must be in Bullish bucket
   - Layer B stub: always passes (returns True). We implement it in Step 8.
   - Computes suggested_stop, risk_per_share, suggested_size_shares,
     suggested_size_pct per spec 5.5. Reads portfolio_value and risk_pct from
     regime_today.json (use risk_pct_override field).
   - Splits verified candidates into primary (in watchlist) and secondary
     (not in watchlist).
   - Writes output/candidates.csv with the columns from spec 5.4 and a `tier`
     column (primary/secondary).

2. A support module scripts/_grade_history.py with a function
   `get_grade_history(symbol, lookback_days)` that replays screen logic for
   past days. Keep this simple; it can re-run the grade computation across a
   rolling window rather than relying on a persisted history table.

3. Tests tests/test_verify_layer_a.py:
   - test_layer_a_stable: 3 days of A-/A/A+ grades, avg RS 90 → passes.
   - test_layer_a_one_downgrade: sequence that shows a downgrade in the
     last 5 days → fails.
   - test_layer_a_grade_below_threshold: average RS 82 → fails.
   - test_layer_a_bearish_bucket: stock is below SMA50 → fails regardless.
   - test_primary_vs_secondary_split: 5 candidates, 2 in watchlist → 2 primary,
     3 secondary.
   - test_sizing_basic: close=100, atr=2, portfolio=1M, risk_pct=0.25% →
     suggested_size_shares is correct per the formula.
   - test_sizing_stop_capped: close=100, atr=10 → raw stop would be 95, but
     stop_pct capped at 3% → stop=97.
   - test_sizing_stop_floor: close=100, atr=0.05 → raw stop would be 99.975,
     but stop_pct floored at 0.5% → stop=99.5.
   - test_risk_pct_caution: regime=CAUTION → risk_pct is 0.125%, sizing halved.
   - test_risk_pct_risk_off: regime=RISK_OFF → no candidates in output.

CONSTRAINTS:
- Layer B is a stub for this step. Do not implement it yet.
- All thresholds come from config.yaml, not hard-coded.
- If regime is RISK_OFF, candidates.csv is written empty (header only).

Verification:
  ./run_daily.sh
  cat output/candidates.csv
  # Typical day should show 0-5 primary + 0-10 secondary
  pytest tests/test_verify_layer_a.py -v

Sanity check:
  If a setup_pass=1 candidate from screen_today.csv doesn't appear in
  candidates.csv, check its grade history. Did it have stable A-grades? If not,
  Layer A correctly filtered it.
```

**`[REVIEW]` Done-when check:**
- [ ] `candidates.csv` is a strict subset of setup_pass=1 rows from `screen_today.csv`
- [ ] All tests pass
- [ ] Manual spot-check: for each candidate, verify Layer A reasoning

Git commit: `Step 7: verify Layer A and position sizing`

---

## Step 8 — Verify Layer B `[CODE]`

### Claude Code prompt

```
Read spec Section 5.2 (Layer B).

TASK: Replace the Layer B stub in verify.py with real chart-structure checks.

Deliverables:

1. Update scripts/verify.py Layer B function (spec 5.2):
   - require_ema_stack: ema10 >= ema20 >= ema50
   - require_stage2: close > sma50 AND sma50 rising (today's sma50 > sma50
     from 10 sessions ago)
   - not extended: extended_yellow == 0 (i.e., close <= sma50 + 5*atr14)
   - volume confirmation: today.volume >= adv20
   - setup_pass must still be 1 (inherited from screen)

2. Update candidates.csv output so both layers' pass/fail reasoning is
   captured in the `notes` column (free text) for dashboard display:
   "Layer A: 3d stable A avg 88; Layer B: EMA stacked, Stage 2, vol 1.4×adv".

3. Tests tests/test_verify_layer_b.py:
   - test_layer_b_ema_stacked: ema10 > ema20 > ema50 + other passes → passes.
   - test_layer_b_ema_inverted: ema10 < ema20 → fails.
   - test_layer_b_sma50_falling: sma50 today < sma50 10d ago → fails Stage 2.
   - test_layer_b_extended: close above sma50 + 5.1 × atr → fails.
   - test_layer_b_low_volume: volume < adv20 → fails.
   - test_combined_a_and_b: Layer A passes, Layer B passes → candidate.
   - test_combined_a_fail_b_pass: filtered by Layer A → not a candidate
     regardless of Layer B.

4. The candidate count should typically drop from the Layer-A-only filter.
   Expected rough ratio: on a day with 12 setup_pass=1, Layer A leaves
   4-6, Layer B leaves 2-4.

CONSTRAINTS:
- Do not tune thresholds to produce a specific candidate count. Thresholds
  come from config.
- Do not merge Layer A and Layer B into one function. Keep them separate so
  each can be disabled independently for debugging.

Verification:
  ./run_daily.sh
  diff <(cat output/candidates.csv_layer_a_only_backup) output/candidates.csv
  # Sunit should save the Layer-A-only output before running Step 8 to
  # manually verify Layer B is filtering, not expanding.
  pytest tests/test_verify_layer_b.py -v
```

**`[REVIEW]` Done-when check:**
- [ ] Layer A alone → Layer A+B: candidate count monotonically decreases
- [ ] Every candidate's `notes` field has a coherent two-layer explanation
- [ ] All tests pass

Git commit: `Step 8: verify Layer B`

---

## Step 9 — Tracker (portfolio state machine) `[CODE]`

### Claude Code prompt

```
Read spec Section 6 in full.

TASK: Implement track.py — a read-only portfolio state machine that records
what WOULD have happened if every primary signal had been taken and managed
by the rules. No orders are placed.

Deliverables:

1. scripts/track.py:
   - Reads output/candidates.csv (primary tier only).
   - For each primary candidate:
     a) If not already in portfolio_state.db, insert as PENDING_CONFIRM.
     b) Ignore if already present.

   - For each PENDING_CONFIRM in portfolio_state.db:
     a) Fetch today's OHLCV for the symbol.
     b) Confirmation rule (spec 6.1):
        close > prev_close AND today's volume >= adv20 AND close > ema10
     c) If confirmed: transition to ACTIVE, record entry_date=today,
        entry_price=today's close (use next-day open if available; for Phase 1
        simplicity use today's close), stop_price from the candidate row,
        size_shares from the candidate row.
     d) If not confirmed: transition to DISCARDED (terminal).

   - For each ACTIVE position:
     a) Check stop hit: today's low <= stop_price → EXITED_STOP.
        pnl_pct = (stop_price - entry_price) / entry_price.
     b) Check super-extended: today's close > today's sma50 + 7 × today's atr14
        → EXITED_EXTENDED. pnl_pct = (close - entry_price) / entry_price.
     c) Check grade decay: today's grade has dropped 2+ ordinal levels from
        entry grade AND yesterday's grade was also 2+ levels below AND this has
        held for >= 2 consecutive days → EXITED_DECAY.
     d) If none of the above: remain ACTIVE. Update today's unrealized pnl.

2. A helper scripts/_grade_ordinal.py with a function `grade_ordinal(grade_str)`
   that maps A+ → 17, A → 16, ..., G → 0. Used for comparing grade drops.

3. portfolio_state.db schema per spec 6.3. Add a `regime_at_entry` column
   populated from regime_today.json at entry time.

4. Tests tests/test_track.py:
   - test_new_signal_becomes_pending: primary signal → PENDING_CONFIRM.
   - test_confirmation_transitions_active: next-day confirmation rules pass →
     ACTIVE.
   - test_no_confirmation_discards: next-day confirmation fails → DISCARDED.
   - test_stop_hit_exits: ACTIVE position, low <= stop → EXITED_STOP with
     correct pnl.
   - test_super_extended_exits: ACTIVE position, close > sma50+7*atr →
     EXITED_EXTENDED.
   - test_grade_decay_exits: grade drops from A+ (17) to B- (12, drop of 5)
     for 2 consecutive days → EXITED_DECAY.
   - test_grade_decay_single_day_does_not_exit: single-day drop does NOT exit.
   - test_idempotent: running track.py twice on the same day does not create
     duplicate PENDING entries.

CONSTRAINTS:
- No orders, no broker API calls, no real money touched.
- The tracker is idempotent: running it twice on the same day produces the
  same state (use UNIQUE on (symbol, signal_date) or equivalent).
- The tracker never skips days. If run_daily.sh misses a day, the next run
  must process the missed day's transitions. (Keep this simple: use the
  latest OHLCV available.)

Verification:
  ./run_daily.sh
  sqlite3 data/portfolio_state.db "SELECT state, COUNT(*) FROM positions \
    GROUP BY state;"
  pytest tests/test_track.py -v

After running for a few days, inspect:
  sqlite3 data/portfolio_state.db "SELECT * FROM positions \
    ORDER BY signal_date DESC LIMIT 20;"
```

**`[REVIEW]` Done-when check:**
- [ ] State machine transitions work correctly across all test cases
- [ ] Idempotency test passes
- [ ] After 3-4 pipeline runs on successive days, state DB shows plausible history

Git commit: `Step 9: read-only tracker with state machine`

---

## Step 10 — Dashboard `[CODE]`

### Claude Code prompt

```
Read spec Section 7.1 (dashboard layout).

Also read /mnt/skills/public/frontend-design/SKILL.md if building in a sandbox
environment. For local build, vanilla HTML/CSS/JS is sufficient.

TASK: Implement render.py to produce a single self-contained dashboard.html.

Deliverables:

1. scripts/render.py:
   - Reads regime_today.json, screen_today.csv, candidates.csv,
     portfolio_state.db.
   - Uses Jinja2 to render a single HTML template.
   - Output: output/dashboard.html (self-contained: all CSS inline, all JS
     inline, no external dependencies except a Google Font link which is
     optional).

2. Page sections (spec 7.1):

   Header:
   - Date, regime banner (color-coded: green=RISK_ON, amber=CAUTION,
     red=RISK_OFF)
   - 4-pillar mini-grid with pass/fail per pillar
   - Universe summary line

   Primary candidates section:
   - One card per primary signal with symbol, close, suggested_stop,
     size_shares, grade, grade_3d_avg, Purple Dot count, and a "why" block
     showing Layer A and Layer B reasoning

   Positions section (from tracker):
   - PENDING_CONFIRM list (simple table)
   - ACTIVE list with current close, distance to stop, distance to
     super-extension line, unrealized P&L
   - Last 10 EXITED positions with outcome

   Secondary candidates section:
   - Compact table, one row per symbol, grouped by sector
   - "Sunday Review" annotation

   RS Grid section:
   - 18 columns (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, E+, E, F, G —
     note: no E- in spec 4.2, 16 grades total)
   - Each cell shows ticker, RS score, day-on-day delta
   - Watchlist members have a star icon
   - Purple-dot-today cells have a purple tag
   - Extended-yellow cells have a yellow outline; extended-red have red
   - Use CSS Grid for layout; colors are bullish-green (A+ through C-) and
     bearish-red (D+ through G) with increasing saturation toward extremes

   Footer:
   - Last update timestamp
   - Download links for regime_today.json, screen_today.csv, candidates.csv

3. Design constraints:
   - No JS framework. Vanilla only.
   - Mobile-responsive. The RS grid should wrap and remain readable on a
     ~400px-wide screen.
   - Dark mode by default, with a CSS variable scheme. Light mode toggle is
     nice-to-have but not required.
   - Use system-ui font stack primarily; one Google Font is acceptable for
     headings.
   - All colors defined via CSS variables at the top of the <style> block.

4. The template file: templates/dashboard.html.j2. Commit this to the repo.

5. Tests tests/test_render.py:
   - test_renders_without_error: run render.py with a synthetic set of inputs
     → HTML file is written and is parseable.
   - test_regime_banner_color: RISK_OFF → banner div has class
     "banner-risk-off".
   - test_primary_card_per_candidate: 3 primary candidates → 3 primary cards
     in the output.
   - test_rs_grid_all_cells_rendered: every stock from screen_today.csv
     appears in the grid.
   - test_no_external_dependencies_except_fonts: parse the output and assert
     there are no <script src="http..."> or <link href="http..."> tags except
     for the optional Google Fonts link.

CONSTRAINTS:
- Single self-contained file. Opening dashboard.html from disk with no
  network must work (except Google Fonts which can fail silently and fall
  back to system fonts).
- No analytics, no tracking pixels, no CDN JavaScript.

Verification:
  ./run_daily.sh
  open output/dashboard.html   # macOS
  # or
  xdg-open output/dashboard.html   # Linux
  # Visually inspect each section.
  pytest tests/test_render.py -v
```

**`[REVIEW]` Done-when check:**
- [ ] Dashboard opens in browser, no JS errors in console
- [ ] All sections populated
- [ ] RS grid visually matches the Korean builder's reference (colors, layout feel, grade columns)
- [ ] Watchlist stars, Purple Dot tags, extension outlines all visible
- [ ] Mobile-responsive: resize browser to ~400px width, grid still readable

Git commit: `Step 10: dashboard with all sections`

---

## Step 11 — Telegram `[CODE]`

### Claude Code prompt

```
Read spec Section 7.2 (Telegram format).

TASK: Implement notify.py to send the daily Telegram message.

Deliverables:

1. scripts/notify.py:
   - Reads regime_today.json, candidates.csv (primary tier only),
     portfolio_state.db.
   - Formats message exactly per spec 7.2 template.
   - Sends via python-telegram-bot to chat_id from config.
   - In RISK_OFF regime: sends a shorter message with no primary section, just
     regime + positions + heartbeat.
   - Always sends, even with zero signals (heartbeat requirement).

2. Message formatting uses Markdown V2 for Telegram with proper escaping of
   special chars (_ * [ ] ( ) ~ ` > # + - = | { } . !).

3. Error handling:
   - Telegram API failure: log error, exit with code 1 (so cron log shows
     the failure). Do NOT retry with backoff; the next day's run is the retry.
   - Missing chat_id or token: exit with clear setup message.

4. Tests tests/test_notify.py:
   - test_format_risk_on: 2 primary, 3 secondary, 1 active → message matches
     expected template.
   - test_format_risk_off: regime=RISK_OFF → message says "No signals",
     primary section absent.
   - test_markdown_escape: candidate with "-" or "." in symbol → properly
     escaped (though NSE tickers shouldn't have these, test anyway).
   - test_api_failure_exits: mock telegram library to raise → script exits 1.
   - Mock all Telegram calls. Never send real messages in tests.

CONSTRAINTS:
- No charts, no images, no buttons, no inline keyboards. Plain text Markdown.
- No interactive commands (no /signals or /positions replies). Phase 1 is
  one-way broadcast.

Verification:
  ./run_daily.sh
  # Check your Telegram chat for the message
  pytest tests/test_notify.py -v
```

**`[REVIEW]` Done-when check:**
- [ ] Message received on Telegram, formatting looks correct
- [ ] Message is received even when primary signal count is 0
- [ ] Regime banner/state visible at top
- [ ] All tests pass without sending real messages

Git commit: `Step 11: Telegram notify`

---

## Step 12 — Watchlist helper `[CODE]`

### Claude Code prompt

```
Read spec Section 8.3.

TASK: Implement watchlist_helper.py for manual Sunday review.

Deliverables:

1. scripts/watchlist_helper.py:
   - Reads last 7 days of secondary candidates (re-run screen+verify for
     historical dates or query a history if you persisted one).
   - Reads current watchlist.csv.
   - Reads features.db for grade and purple dot history.

   Prints a terminal report with 4 sections:
   a) Secondary signals from past 7 days, grouped by symbol, with frequency
      (e.g., "POLYCAB: 3 times", "BLUESTARCO: 2 times").
   b) Watchlist members with zero signals in last 30 days (drop candidates).
   c) Non-watchlist symbols with >= 2 purple dots in last 30 days (add
      candidates).
   d) Watchlist members whose grade has fallen to C- or lower for 5+
      consecutive days (degrading names).

2. The script does NOT modify watchlist.csv. It only prints suggestions.

3. Use plain terminal output with minimal formatting. Bold section headers,
   regular text rows. Colors via ANSI escape codes are acceptable but optional.

4. Tests tests/test_watchlist_helper.py:
   - test_identifies_frequent_secondary: synthetic 7-day history where symbol
     X appears 4 times in secondary → listed with count 4.
   - test_flags_inactive_watchlist: watchlist member with no signals in 30
     days → flagged.
   - test_flags_purple_dot_hot_non_members: stock with 3 purple dots, not in
     watchlist → flagged as add candidate.

CONSTRAINTS:
- Not part of cron. Sunit runs it manually on Sunday.
- No side effects. No edits to any file.

Verification:
  python scripts/watchlist_helper.py
  # Inspect output for sensibleness
  pytest tests/test_watchlist_helper.py -v
```

**`[REVIEW]` Done-when check:**
- [ ] Report prints cleanly
- [ ] Each section has at least one entry (given first week of data)
- [ ] Tests pass

Git commit: `Step 12: watchlist helper`

---

## Step 13 — Expand to Nifty 500 `[CODE]`

### Claude Code prompt

```
TASK: Expand the universe from 50 names to the full Nifty 500.

Deliverables:

1. Update universe.csv to the full Nifty 500 constituents as of the most
   recent NSE rebalance.
   - Source: NSE monthly reports or a static CSV committed to the repo.
   - Columns unchanged: symbol, name, sector, industry, market_cap_cr.
   - Do NOT auto-scrape in Phase 1. Hand-maintain or use a committed reference
     file.

2. Run fetch.py — expect ~5-10 minutes for the full backfill.

3. Verify all downstream scripts handle the larger universe:
   - indicators.py: should complete in under 5 minutes after the first full
     run (subsequent incremental runs should be <30 seconds).
   - screen.py, verify.py, track.py, render.py, notify.py: linear scaling,
     should complete in seconds.

4. Add a performance check tests/test_pipeline_end_to_end.py:
   - Runs run_daily.sh inside a test harness and asserts total runtime < 10 min.
   - Asserts all expected files are written.
   - Asserts no errors in any log.

5. If any script becomes unacceptably slow:
   - Profile with cProfile.
   - Vectorize any per-row pandas loops.
   - Add sqlite indexes where helpful.
   - Do NOT add parallelism or async. Keep it synchronous.

CONSTRAINTS:
- No change in methodology, only scale.
- The dashboard RS grid now has 500 cells; ensure layout still works.
- Expand the watchlist if desired, but keep it <= 50 names.

Verification:
  time ./run_daily.sh   # full run
  pytest -v
  open output/dashboard.html
```

**`[REVIEW]` Done-when check:**
- [ ] Full Nifty 500 fetch completes
- [ ] End-to-end run under 10 minutes
- [ ] Dashboard still renders correctly with 500 cells
- [ ] All tests pass

Git commit: `Step 13: expand to Nifty 500`

---

## Step 14 — Walk-forward sanity check `[CODE]`

### Claude Code prompt

```
Read spec Section 10.2 (walk-forward) carefully.

TASK: Create an offline walk-forward replay script that reports signal quality
over the past 12 months.

Deliverables:

1. scripts/walkforward.py (NOT called by cron — manual run only):
   - For each trading day in the past 252 sessions:
     a) Snapshot features.db as of that date.
     b) Run regime, screen, verify logic as if that date were today.
     c) Take the primary candidates and simulate the tracker's state machine
        forward through time (up to 30 days per signal for outcome tracking).
     d) Record outcomes: entry date, exit date, exit reason, pnl_pct, R-multiple.

2. Generate a report output/walkforward_report.html (or markdown) with:
   - Total signals, by regime at entry
   - Hit rate (wins: EXITED_EXTENDED or position held above entry for 10+ days
     after first trim; losses: EXITED_STOP; neutral: EXITED_DECAY with small
     P&L).
     Note: Phase 1 has no trim logic yet, so treat "closed above entry price"
     as a win for this report.
   - Mean and median R-multiple
   - Worst 5 drawdowns in hypothetical equity curve
   - Breakdown by regime at entry (RISK_ON vs CAUTION performance)
   - Breakdown by sector
   - Distribution chart of R-multiples (histogram, simple ASCII or SVG)

3. Pass criteria printed at the bottom of the report:
   - Hit rate in 35-55% range → PASS
   - Mean R-multiple > 1.0 → PASS
   - Worst drawdown < 15% → PASS
   - Overall: three PASS = go-live; any FAIL = review parameters

4. Tests tests/test_walkforward.py:
   - test_with_synthetic_trending_universe: all stocks in uptrend, regime
     RISK_ON → majority of signals should be wins; report should show
     hit rate > 50%.
   - test_with_synthetic_bear_universe: most stocks in downtrend, regime
     mostly RISK_OFF → few signals should fire; report should show
     signal count near zero, not negative returns.

CONSTRAINTS:
- Read-only. Walk-forward does not modify production DBs.
- Use a separate tmp database for the replay if needed.
- No curve-fitting. Run with exactly the thresholds in config.yaml. Do NOT
  tune thresholds in this step.

Verification:
  python scripts/walkforward.py
  open output/walkforward_report.html
  pytest tests/test_walkforward.py -v

The report output is Sunit's go/no-go decision document. Review it in detail.
```

**`[REVIEW]` Done-when check:**
- [ ] Report generates for the last 252 sessions
- [ ] All three pass criteria evaluated
- [ ] Sunit reads the report in full and writes a go/no-go decision in `decisions.md`

Git commit: `Step 14: walk-forward replay`

---

## Step 15 — Cron and heartbeat `[CODE]`

### Claude Code prompt

```
TASK: Schedule the daily pipeline via cron, with heartbeat monitoring.

Deliverables:

1. scripts/install_cron.sh:
   - Installs a crontab entry for run_daily.sh at 16:30 IST every weekday.
   - Writes cron logs to logs/cron.log.
   - Documents how to uninstall (crontab -e, remove the line).

2. Update run_daily.sh to:
   - Log start and end timestamps to logs/cron.log.
   - Send a heartbeat Telegram message at the end of each run regardless of
     signal count ("SwingEdge Lite ran at HH:MM. Regime: X. Signals: N.").
   - If any step fails, send an error Telegram message.

3. A simple watchdog scripts/watchdog.py (run manually or via separate cron):
   - Checks logs/cron.log for the most recent run timestamp.
   - If no run in the last 28 hours on a trading day, sends a
     "SwingEdge Lite has not run" Telegram alert.

4. Documentation in README.md:
   - Setup steps for first-time install
   - How to check logs
   - How to manually re-run
   - How to pause during holidays or vacations
   - How to refresh the Fyers token

CONSTRAINTS:
- cron schedule must respect NSE trading calendar (Mon-Fri, excluding
  holidays). For Phase 1, running on holidays and having fetch.py gracefully
  return zero new data is acceptable.
- No systemd services, no launchd plists. Cron only.

Verification:
  bash scripts/install_cron.sh
  crontab -l   # verify entry is present
  # Wait until tomorrow 16:30 IST
  # Verify Telegram message received
  # Verify logs/cron.log updated
```

**`[REVIEW]` Done-when check:**
- [ ] cron installed and visible in `crontab -l`
- [ ] At least 2 consecutive trading days of unattended runs completed successfully
- [ ] Heartbeat received both days
- [ ] If either day failed, error message was sent

Git commit: `Step 15: cron and heartbeat`

---

## Step 16 — Documentation and handoff `[MANUAL + CODE]`

**Sunit does this with Claude Code assistance, not autonomously.**

### Prompt for Claude Code

```
TASK: Produce final documentation.

Deliverables:

1. Update README.md with:
   - One-paragraph system description
   - Architecture diagram (ASCII, from spec Section 2)
   - Setup instructions (clone, venv, config, Fyers auth, cron install)
   - Daily operation (what happens, what to check)
   - Weekly operation (watchlist helper on Sunday)
   - Troubleshooting (common failures and fixes)
   - How to interpret the dashboard

2. Create OPERATIONS.md:
   - Telegram message format examples
   - Dashboard section-by-section walkthrough with screenshots (optional)
   - What to do when:
     * Fyers token expires
     * A symbol is delisted
     * A corporate action (split/bonus) happens
     * Holiday schedule changes

3. Update FUTURE.md with everything we rejected during the build (this should
   already be populated by Sunit throughout; if empty, review all steps and
   capture the ideas that were deferred).

4. Tag the repo:
   git tag v1.0.0 -m "Phase 1 complete"

5. Write a brief retrospective in decisions.md under a new "Phase 1 Retro"
   section:
   - What worked
   - What surprised you
   - What to do differently in Phase 2
```

**`[REVIEW]` Final done-when check:**
- [ ] README gives a new reader enough to set up and run the system from scratch
- [ ] OPERATIONS.md covers the expected failure modes
- [ ] FUTURE.md has all the deferred ideas captured
- [ ] Tag v1.0.0 exists
- [ ] Retrospective written

---

## After Phase 1: the 30-day gate

Do not start Phase 2 until Phase 1 has run live for 30 consecutive trading days. During those 30 days:

- Run the system daily
- Review the tracker state DB weekly
- Run walkforward.py monthly to recompute historical signal quality
- Populate FUTURE.md with every Phase 2 idea that comes to mind, but do not build any of it

At day 30:

1. Run a final walkforward.py
2. Review the tracker's 30-day outcomes
3. Compute real hit rate and R-multiple from the tracker
4. Compare real vs walkforward-predicted performance
5. If real performance is within 20% of predicted: Phase 1 is validated, proceed to Phase 2 planning
6. If real performance is materially worse: spend a week on diagnosis before doing anything else. The methodology may not work as-is on your universe, in which case Phase 2 is premature

The 30-day gate is not negotiable. The entire point of this spec is to build a small thing, validate it, and only then expand. Skipping the gate returns you to SwingEdge V6 territory — a large complicated thing of uncertain value.

---

## Appendix A — Anti-patterns Claude Code will try to introduce

Watch for these during code review and reject them:

- **Speculative generality.** "I added a plugin system so you can swap indicators." → No. We have one set of indicators. Hard-code them.
- **Framework creep.** "I used FastAPI to serve the dashboard." → No. Static HTML.
- **Premature optimization.** "I parallelized the indicator computation with multiprocessing." → No. Synchronous and slow is fine at this scale.
- **Clever abstractions.** "I made an abstract BaseSignal class with a register_signal decorator." → No. Direct function calls.
- **Library explosion.** "I added scikit-learn for the grade ranking." → No. Pandas rank is sufficient.
- **Unnecessary async.** "I made fetch.py async for performance." → No. One HTTP request at a time.
- **Configuration sprawl.** "I moved the setup rules into a separate setups.yaml." → No. One config.yaml.
- **Test sprawl.** "I added 50 tests covering edge cases." → Review. Cover the rules in the spec, not every theoretical edge case.
- **README rewrites.** "I rewrote README as a 200-line marketing page." → No. README is setup + ops.

If any of these show up, explicitly say "revert that and do the minimal version."

---

## Appendix B — The golden questions

Before every code generation with Claude Code, ask these:

1. Does the spec require this?
2. Is this the simplest thing that could work?
3. Will Sunit be able to read this code in 6 months?
4. Does this add a new dependency, service, or concept to the system?
5. What happens if this component fails?

If the answer to #4 is yes and the spec didn't require it, stop.

---

End of build guide. Keep this file in the repo as `BUILD_GUIDE.md` and refer to it for every step.
