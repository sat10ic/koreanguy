# STRONG START / ARORA FOCUS LIST — spec (user order, 2026-07-11)

User: a sub-tab in the WATCHLIST (SHORTLIST) screen replicating finallynitin's SS RVOL
dashboard + Manas Arora CH3.1 scans. Move a stock from watchlist/screener into it
directly; the LLMs get a SEPARATE push-to-focus option when a name matches Arora's
requirements.

## Sources (pin verbatim — do not paraphrase the numbers)

### finallynitin SS RVOL Pine (© finallynitin; personal-use port only, DO NOT redistribute)
- **Strong Start flag (SS ★):** `open > prev_close AND day_low >= prev_close * 0.995`
  (SS_LOWMULT = 0.995). Gap-up-and-hold: opened above yesterday's close and did not
  fall back below ~prev close. Computable from EOD OHLC (open, low, prev_close).
- **RVOL:** `volume / SMA(volume, 20)` (lookback default 20; 10 to match the screener).
  Displayed as percent (rv*100) or ratio.
- **Chg%:** `(close - prev_close)/prev_close * 100`.
- **Row color:** green if chg% >= +1.5, red if <= -1.5, amber between (chgFlag=1.5).
- **Sort:** RVOL | Chg% | SS (SS on top, RVOL-ranked within).

### Manas Arora CH3.1 (Course Notes) — watchlist-elimination scans
- **Buying power:** % up from 52-week low AND % up from 65-day (3-month) low — higher =
  stronger momentum ("stock is up 57% => lots of buying power"). Elimination lever when
  choosing among ~20 names.
- **Not extended (KEY):** distance of price from the 10-week (weekly) / 20-day (daily) MA.
  "I ideally want the distance on the lower side, like 8, 9, 10%. 12% acceptable. But
  25, 30, 40% — I'm not touching that stock." Smaller caps run to upper-30s/40s; large
  caps rarely past ~17% — so the cap is RELATIVE to the stock's own history, not one fixed
  number. Practical rule: flag/deprioritize when dist-from-20DMA is high vs the stock's own
  ADR/history; the SS list should lean toward names NOT already extended.
- **Purple dots (fast-mover proof):** a dot prints when the stock moves >5% in either
  direction on >500k volume. "If a great setup has no dot, I skip it — I don't want a
  slow-moving stock." ZERO dots (recent window) = disqualify.
- **% off 52-week high:** near the high = better.
- **Relative strength vs midcap/smallcap index:** outperforming the index (esp. in bad
  markets) = future leader. (RS metric already exists.)

## ARORA STRONG-START QUALIFY (the deterministic rule the LLM push checks)
A name qualifies for the focus list when ALL hold (all metrics already exist except SS):
1. **Momentum today:** SS ★ (gap-up-and-hold) OR RVOL20 >= ~1.5x (volume surge).
2. **Buying power:** pct_up_from_65d_low strong (corpus: "up strongly in last 3 months").
3. **Fast mover:** purple_dot_count_60d > 0 (zero dots = skip, Arora's own rule).
4. **Not over-extended:** distance from 20DMA not in the high band relative to the stock's
   ADR (avoid the 25-40% "I'm not touching it" zone) — use adr20 to scale, not a fixed %.
Thresholds are corpus-anchored, not label-tuned. NBIFIN-class illiquid names are already
excluded upstream at tradability — the focus list inherits that.

## Build
BACKEND (testable — Sonnet):
- `engine/eod_detectors.py`: `strong_start_today(bars)` per the Pine flag; `rvol20(bars)`.
- `scanner/`: `arora_strong_start_qualifies(metrics) -> {qualifies: bool, reasons: [...]}`.
- New table `focus_list(scan_date?, symbol, source, reason, added_at)` (persistent, not
  nightly-regenerated) OR a `tier='FOCUS'` convention on agent_watchlist — pick the cleaner.
- Endpoints: `POST /api/desk/focus-list/add {symbol, source, reason}`,
  `POST /api/desk/focus-list/remove`, `GET /api/desk/focus-list?date=` returning each
  symbol's SS-RVOL row {symbol, rvol20, chg_pct, ss_flag, pct_up_65d_low, dist_20dma_pct,
  purple_dot_count, near_52w_high, rs, arora_qualifies}. Reuse the watchlist input-guard
  (regex + must exist in daily_prices).
- LLM/curator push: the debate/curator path may call add with source='llm' ONLY when
  `arora_strong_start_qualifies` is true; reason records which conditions matched.
FRONTEND (Codex per user pref, after backend verified):
- STRONG START segmented sub-tab in SHORTLIST (ShortlistTab): table styled like the SS RVOL
  dashboard — Symbol | RVOL | Chg% | SS★ | %up-low | dist-MA | dots | near-high; row color
  by chg% (green/red/amber); sort RVOL|Chg%|SS. ★ move-to-focus button on SHORTLIST and
  SCANNERS rows. "pushed by AI (Arora match)" badge for source='llm' rows.
