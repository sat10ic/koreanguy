# AUDIT — per-section currency + per-stock metric correctness — 2026-09-01

Author: Claude (Opus 5). This audit exists because the previous one checked
whether things *rendered*, not whether the numbers were *right*. The owner
called that out. This one recomputes metrics independently from raw NSE
bhavcopy rather than importing pipeline code (so it tests the output, not the
code against itself), and maps every screen's real data vintage.

Subject: `tonight_2026-08-28.json` as regenerated `2026-08-31T19:24Z`
(73 candidates), plus the live app at `localhost:5183`.

---

## A. STOP-WORK — dead and stale symbols are presented as live candidates

**9 distinct symbols (10 of 73 rows, 14%) had no trade on the session date.**
The report shows them with a current-looking price, rank, and entry trigger.

| Symbol | Last actual trade | Staleness | Reported close | rs_rank | trigger |
|---|---|---|---|---|---|
| UJJIVAN | **2024-05-02** | **~2.3 years** | 589.50 | 84.7 | 592.9 |
| BARBEQUE | 2025-04-29 | ~16 months | 309.60 | 83.5 | 324.0 |
| BODALCHEM | 2026-05-25 | ~3 months | 75.80 | 70.4 | 80.75 |
| QUICKHEAL | 2026-06-03 | ~3 months | 181.71 | 73.1 | 196.5 |
| BLISSGVS | 2026-07-02 | ~2 months | 527.10 | 87.1 | 547.4 |
| PPAP | 2026-07-14 | ~6 weeks | 338.02 | 95.8 | 379.5 |
| SHALPAINTS | 2026-08-05 | ~3 weeks | 86.19 | **99.2** | 89.8 |
| UFBL | 2026-08-11 | ~2 weeks | 811.05 | 71.6 | 845.0 |
| ALPHAGEO | 2026-08-19 | ~1 week | 345.41 | **99.4** | 368.0 |

### This is not random noise — the bias runs the wrong way

**The stalest names rank the highest.** ALPHAGEO (99.4) and SHALPAINTS (99.2)
are the top two `rs_rank` values in the entire report, and both stopped
trading before the session date. The mechanism is straightforward: a symbol
that stops printing has a **frozen price**. If the universe drifts down around
it, its relative return looks outstanding. Relative strength computed against a
stale price manufactures leaders out of dead names.

So the desk's highest-conviction rows are systematically enriched with symbols
that cannot be traded. This is a direct answer to "the individual stock metrics
are not up to date" — and it is more serious than staleness, because it
actively promotes the stale ones.

**Required:** a liveness gate before RS ranking — a symbol with no print on the
session date must be excluded (or emitted `UNRESOLVED` with a named reason),
never ranked. Phase 0 spec §35 already requires `traded_today` / `suspended` /
`series_active` status fields; none are enforced here.

---

## B. Duplicate candidates inflate the list

73 rows, **71 distinct symbols**. `FILATEX` and `UJJIVAN` each appear twice —
the same symbol emitted once per firing detector (UJJIVAN as both `ipo_base`
and `momentum_burst`).

Consequences: "73 candidates" overstates the real count; a user scanning the
list sees the same name twice; and any per-candidate aggregate double-counts
those names. Either dedupe to one row per symbol carrying a list of detectors,
or state plainly that the grain is symbol×detector, not symbol.

---

## C. The 16-year backfill is not reaching the scan

`data/bhavcopy/` holds **4,007 distinct sessions (2010-06-10 → 2026-08-31)**.
The nightly deliberately ingests **"MOST RECENT files only" — 600 files**
(`nightly_bg_raw.log`: `Using 600 files: sec_bhavdata_full_05062023.csv -> ...`).

Evidence in the output: the maximum `sessions` value any candidate reports is
**570**, and 31 candidates report exactly 570 (the store's full depth). Against
raw bhavcopy, established names have far more:

```
FMGOETZE    report=570    raw=3800   (+3230)
SHILPAMED   report=570    raw=3802   (+3232)
APARINDS    report=570    raw=3802   (+3232)
INDSWFTLAB  report=454    raw=3485   (+3031)
```

63 of 73 candidates show a truncated history. This is a deliberate performance
choice, not a parser bug — but it has consequences that are not disclosed
anywhere in the UI:

- every long-window metric (52-week high/low, 252-session distance) is computed
  against at most ~2.3 years of history
- the 4y/1y walk-forward folds (`walkforward.py:75-83`, needs ~1,260 sessions)
  cannot be satisfied from a 600-file scan
- the archive that N5 will read inherits whatever depth was ingested

**Required:** either raise the nightly window, or disclose the effective history
depth in the honesty footer so a "52-week high" is not silently computed from a
shorter window.

---

## D. The UI ignores a backend that has largely caught up

Since the last audit the backend improved substantially. **The UI renders almost
none of it.**

| Field | In JSON | Rendered in UI |
|---|---|---|
| `trigger` | **73/73** | no |
| `invalidation` | **73/73** | no |
| `rr` | **72/73** | no |
| `stock_quality` | **73/73** | no — shows "NO QUALITY SCORE COMPUTED" |
| `setup_quality` | **73/73** | no |
| `entry_quality` | **73/73** | no |
| breadth analytics (`net_nh_nl`, `volatility_ratio`, `volume_ratio`, `up_down_close_pct`) | present | no |
| `composite` | 0/73 | n/a — genuinely absent |

### D.1 The front page shows the OPPOSITE market call

`honesty_footer.regime_note` now reads:

```
CHOP (breadth 56.4% above EMA50, breadth_only; 2026-08-28 already scored)
regime_built: True
```

The screen shows a large green **BULL · 12 sessions** with breadth 65.9% /
64.5% / 22.4% / 6.1%.

Those come from the hardcoded `REGIME` fixture (`fixtures.ts`, wired at
`Tonight.tsx:97` via `regime={REGIME}`), whose `aboveEma50Pct: 65.86` is the
stale July figure. The real header on the same screen reads **56.4%**.

**The regime is now genuinely computed, and the UI overrides it with a fixture
that says the opposite.** Worse, the earlier "ILLUSTRATIVE PREVIEW — NOT THE
REAL CLASSIFIER" caption has been softened to "Market mood — R0 breadth-only
classifier (N2)", which reads as a real system output. A wrong market regime on
the front page is the single most dangerous item in this audit.

### D.2 Header still reports a two-month-old date

`TopBar.tsx:43` renders `As of {SESSION.date}` → **"As of 2026-07-03"** on every
screen, from the stale `SESSION` fixture (`fixtures.ts`). `History.tsx:52-53`
and `Settings.tsx:51,55,59` read the same object. This is the "month old" the
owner reported, and it persists.

---

## E. Verified CORRECT — credit where due

Independently recomputed from raw bhavcopy across all 73 candidates:

- **`close`: 0 mismatches / 73.** Every reported price matches the exchange
  print exactly. (Cross-check: TRENT's real close 2898.00 vs TradingView 2892 —
  0.2% apart. The data layer is sound.)
- **`adr_pct`: 1 deviation / 73** (AUTOIND 6.481 vs recomputed 5.943; AUTOIND is
  one of the 2 CA-adjusted symbols, which plausibly explains it).
- **CA basis is fixed**: `actions_applied: 4`, `adjusted_symbols: 2` — down from
  the rejected 55/33.
- **Fabricated candidates removed**: `ALL_CANDIDATES` is now an empty array
  (`fixtures.ts:106`). The TRENT-class fabrication is gone.
- **Currency is improving**: `tonight_2026-08-31.json` exists and is registered
  in `reportRegistry.ts`; a bhavcopy for 2026-08-31 is on disk.
- Regime is now really computed (`regime_built: true`) and breadth analytics are
  really emitted — both just not displayed.

---

## F. Ranked actions

1. **Liveness gate (§A).** Exclude symbols with no print on the session date
   from the candidate list and from RS ranking. This currently promotes dead
   names to the top of the desk.
2. **Kill the `REGIME` fixture (§D.1).** Drive the regime badge from
   `honesty_footer.regime_note`, or show nothing. The front page is currently
   asserting BULL when the system computed CHOP.
3. **Kill the `SESSION` fixture (§D.2).** Point `TopBar`, `History`, `Settings`
   at the selected report.
4. **Render what already exists (§D).** trigger / invalidation / rr /
   stock_quality / setup_quality / entry_quality / breadth analytics are all in
   the JSON and all invisible.
5. **Dedupe or re-grain the candidate list (§B).**
6. **Disclose or raise the history depth (§C).** A "52-week high" from a
   600-file window must say so.

## G. Method and limits

- Metrics recomputed from `data/bhavcopy/sec_bhavdata_full_*.csv` (3,804 files,
  4,053 symbols) with an independent implementation of the documented ADR
  definition (20-session exclusive prior window).
- **Not verified:** `rvol`, `delivery_ratio`, `contraction`, `rs_rank` values
  were not independently recomputed — their definitions depend on pipeline
  internals (median windows, universe composition) where an independent
  reimplementation would risk false alarms from convention mismatch rather than
  real defects. `rs_rank` is nonetheless implicated by §A on structural grounds.
- **Not verified:** whether the archive under `data/market/research/events` has
  been regenerated on the 4-action basis since the CA quarantine. Last checked,
  all 396 partitions carried the rejected `ca_table_hash 191ac96a61cdfae7`.
- Scripts used are in the session scratchpad: `metric_audit.py`,
  `stale_symbols.py`, `section_vintage.py`, `check_new_report.py`.
