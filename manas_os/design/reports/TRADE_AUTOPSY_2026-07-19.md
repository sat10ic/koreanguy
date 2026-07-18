# Trade Autopsy -- Zerodha Import Round Trips

Chart-level price-action read of every closed zerodha_import round trip, using the tool's own detectors (eod_detectors / discovery_metrics / gates) point-in-time at the entry and exit date. This is the missing chart layer for BROKER_AUDIT_2026-07-18.md's statistical buckets.
Round trips analyzed: 420. Entry point-in-time bar matched: 381. Exit point-in-time bar matched: 379.

## TAXONOMY

| Tag | Count | Total P&L | Avg P&L |
| --- | --- | --- | --- |
| COUNTER_TREND | 84 | Rs 12.92 | Rs 0.15 |
| EXTENDED_ENTRY | 188 | Rs 8,985.36 | Rs 47.79 |
| IN_BASE | 85 | Rs -6,183.36 | Rs -72.75 |
| LATE_EXIT | 86 | Rs -4,380.75 | Rs -50.94 |
| LATE_IN_MOVE | 67 | Rs -5,403.06 | Rs -80.64 |
| NO_BASE | 192 | Rs -5,195.56 | Rs -27.06 |
| PANIC_EXIT | 2 | Rs -576.90 | Rs -288.45 |
| STRUCTURE_EXIT | 322 | Rs 3,727.67 | Rs 11.58 |

## CROSS-ANALYSIS


### EXTENDED_ENTRY x outcome

| Cohort | N | Win rate | Total P&L | Avg P&L |
| --- | --- | --- | --- | --- |
| EXTENDED_ENTRY | 188 | 39.36% | Rs 8,985.36 | Rs 47.79 |
| not EXTENDED_ENTRY | 232 | 27.59% | Rs -11,218.59 | Rs -48.36 |

### IN_BASE x outcome

| Cohort | N | Win rate | Total P&L | Avg P&L |
| --- | --- | --- | --- | --- |
| IN_BASE | 85 | 29.41% | Rs -6,183.36 | Rs -72.75 |
| not IN_BASE | 335 | 33.73% | Rs 3,950.13 | Rs 11.79 |

### STRUCTURE_EXIT vs PANIC_EXIT

| Exit tag | N | Win rate | Total P&L | Avg P&L |
| --- | --- | --- | --- | --- |
| STRUCTURE_EXIT | 322 | 31.37% | Rs 3,727.67 | Rs 11.58 |
| PANIC_EXIT | 2 | 0.00% | Rs -576.90 | Rs -288.45 |

### PANIC_EXIT recovery (10 sessions after exit)

PANIC_EXIT trades: 2. With a usable 10-session-after read: 2. Median % change by session 10 (or last available): 1.83%. Recovered (positive) count: 1/2.

## EXEMPLARS


### 10 biggest losers


#### Loser #1 -- RNBDENIMS (trade_id 313)

- P&L Rs -7,508.50 (-90.60%), qty 50.0, held 75 calendar days
- ENTRY 2026-02-05 @ 165.75
    - extension_21 12.74% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 10.0, range_contraction=True, correction depth 0.07% -> IN_BASE
    - trend-template pass=True objections=['downtrend_structure'] -> trend ok
    - day change 1.33%, rvol 3.03x, pct up from 65d low 49.23% -> not late
- EXIT 2026-04-21 @ 15.58
    - no point-in-time exit bar match (skipped)

#### Loser #2 -- BEML (trade_id 189)

- P&L Rs -2,781.75 (-61.86%), qty 1.0, held 62 calendar days
- ENTRY 2025-10-15 @ 4496.60
    - extension_21 3.88% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 80.0, range_contraction=False, correction depth 1.39% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 2.57%, rvol 2.5x, pct up from 65d low 127.82% -> LATE_IN_MOVE
- EXIT 2025-12-16 @ 1714.85
    - exit_state=Broken, fired_rules=['below-21EMA', 'below-50SMA', 'below-200SMA', 'downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT', 'LATE_EXIT']
    - Broken persisted 30 sessions before this exit

#### Loser #3 -- NETWEB (trade_id 358)

- P&L Rs -1,335.50 (-10.30%), qty 3.0, held 2 calendar days
- ENTRY 2026-05-12 @ 4322.00
    - extension_21 1.04% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 75.0, range_contraction=False, correction depth 10.6% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change -6.5%, rvol 0.82x, pct up from 65d low 33.2% -> not late
- EXIT 2026-05-14 @ 3876.83
    - exit_state=Weakening, fired_rules=['below-21EMA', 'distribution-days']
    - exit tags: ['STRUCTURE_EXIT']

#### Loser #4 -- HINDCOPPER (trade_id 249)

- P&L Rs -1,328.00 (-18.29%), qty 10.0, held 7 calendar days
- ENTRY 2026-01-30 @ 726.00
    - extension_21 21.12% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 100.0, range_contraction=False, correction depth 9.76% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change -9.76%, rvol 2.61x, pct up from 65d low 122.33% -> LATE_IN_MOVE
- EXIT 2026-02-06 @ 593.20
    - exit_state=Weakening, fired_rules=['below-21EMA', 'crossed-below-21EMA', 'downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

#### Loser #5 -- TDPOWERSYS (trade_id 413)

- P&L Rs -1,226.75 (-17.98%), qty 5.0, held 14 calendar days
- ENTRY 2026-06-23 @ 1364.70
    - extension_21 8.56% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 70.0, range_contraction=False, correction depth 1.85% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 2.08%, rvol 1.26x, pct up from 65d low 77.01% -> not late
- EXIT 2026-07-07 @ 1119.35
    - exit_state=Broken, fired_rules=['below-21EMA', 'below-50SMA', 'downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT', 'LATE_EXIT']
    - Broken persisted 4 sessions before this exit

#### Loser #6 -- NBCC (trade_id 333)

- P&L Rs -1,208.05 (-21.57%), qty 70.0, held 401 calendar days
- ENTRY 2025-04-02 @ 80.00
    - extension_21 1.4% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 20.0, range_contraction=True, correction depth 20.41% -> neither
    - trend-template pass=False reason=not in a confirmed uptrend (close 82.9 / 50SMA 84.5 / 200SMA 109.1) objections=[] -> COUNTER_TREND
    - day change 1.57%, rvol 0.65x, pct up from 65d low 17.08% -> not late
- EXIT 2026-05-08 @ 97.26
    - exit_state=Broken, fired_rules=['below-200SMA', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT', 'LATE_EXIT']
    - Broken persisted 40 sessions before this exit

#### Loser #7 -- NSDL (trade_id 190)

- P&L Rs -1,144.18 (-17.68%), qty 5.0, held 113 calendar days
- ENTRY 2025-08-25 @ 1294.40
    - no point-in-time entry bar match (skipped)
- EXIT 2025-12-16 @ 1065.56
    - no point-in-time exit bar match (skipped)

#### Loser #8 -- IXIGO (trade_id 188)

- P&L Rs -1,090.50 (-32.28%), qty 10.0, held 53 calendar days
- ENTRY 2025-10-16 @ 337.85
    - extension_21 11.24% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 85.0, range_contraction=False, correction depth 1.06% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 2.57%, rvol 1.86x, pct up from 65d low 96.55% -> LATE_IN_MOVE
- EXIT 2025-12-08 @ 228.80
    - exit_state=Broken, fired_rules=['below-21EMA', 'below-50SMA', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT', 'LATE_EXIT']
    - Broken persisted 26 sessions before this exit

#### Loser #9 -- HINDCOPPER (trade_id 250)

- P&L Rs -1,018.00 (-14.65%), qty 10.0, held 7 calendar days
- ENTRY 2026-01-30 @ 695.00
    - extension_21 21.12% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 100.0, range_contraction=False, correction depth 9.76% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change -9.76%, rvol 2.61x, pct up from 65d low 122.33% -> LATE_IN_MOVE
- EXIT 2026-02-06 @ 593.20
    - exit_state=Weakening, fired_rules=['below-21EMA', 'crossed-below-21EMA', 'downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

#### Loser #10 -- HINDCOPPER (trade_id 247)

- P&L Rs -863.00 (-12.70%), qty 10.0, held 8 calendar days
- ENTRY 2026-01-29 @ 679.50
    - extension_21 37.1% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 100.0, range_contraction=False, correction depth 0.0% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 20.0%, rvol 3.46x, pct up from 65d low 146.37% -> LATE_IN_MOVE
- EXIT 2026-02-06 @ 593.20
    - exit_state=Weakening, fired_rules=['below-21EMA', 'crossed-below-21EMA', 'downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

### 5 biggest winners


#### Winner #1 -- SILVER (trade_id 229)

- P&L Rs 4,274.80 (43.96%), qty 40.0, held 23 calendar days
- ENTRY 2026-01-07 @ 243.13
    - extension_21 13.85% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 45.0, range_contraction=False, correction depth 4.01% -> neither
    - trend-template pass=True objections=[] -> trend ok
    - day change 1.23%, rvol 1.04x, pct up from 65d low 79.23% -> not late
- EXIT 2026-01-30 @ 350.00
    - exit_state=Weakening, fired_rules=['downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

#### Winner #2 -- SILVER (trade_id 230)

- P&L Rs 2,805.48 (28.64%), qty 36.0, held 16 calendar days
- ENTRY 2026-01-14 @ 272.07
    - extension_21 19.83% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 65.0, range_contraction=False, correction depth 0.95% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 5.8%, rvol 1.25x, pct up from 65d low 101.95% -> LATE_IN_MOVE
- EXIT 2026-01-30 @ 350.00
    - exit_state=Weakening, fired_rules=['downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

#### Winner #3 -- AVALON (trade_id 395)

- P&L Rs 2,366.00 (15.85%), qty 10.0, held 36 calendar days
- ENTRY 2026-05-20 @ 1492.90
    - extension_21 19.03% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 75.0, range_contraction=False, correction depth 2.31% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 7.94%, rvol 8.37x, pct up from 65d low 70.99% -> not late
- EXIT 2026-06-25 @ 1729.50
    - exit_state=Weakening, fired_rules=['distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

#### Winner #4 -- BLISSGVS (trade_id 378)

- P&L Rs 2,119.40 (90.22%), qty 10.0, held 60 calendar days
- ENTRY 2026-04-06 @ 234.91
    - extension_21 9.49% (> 8% => EXTENDED_ENTRY) -> EXTENDED_ENTRY
    - tightness pctile 85.0, range_contraction=False, correction depth 2.71% -> NO_BASE
    - trend-template pass=True objections=[] -> trend ok
    - day change 1.32%, rvol 0.82x, pct up from 65d low 55.84% -> not late
- EXIT 2026-06-05 @ 446.85
    - exit_state=Weakening, fired_rules=['downside-reversal-bar', 'distribution-days']
    - exit tags: ['STRUCTURE_EXIT']

#### Winner #5 -- HINDCOPPER (trade_id 231)

- P&L Rs 1,656.00 (30.25%), qty 10.0, held 3 calendar days
- ENTRY 2026-01-27 @ 547.50
    - extension_21 7.32% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 50.0, range_contraction=False, correction depth 2.4% -> neither
    - trend-template pass=True objections=[] -> trend ok
    - day change 4.9%, rvol 0.55x, pct up from 65d low 82.22% -> LATE_IN_MOVE
- EXIT 2026-01-30 @ 713.10
    - exit_state=Weakening, fired_rules=['downside-reversal-bar', 'distribution-days', 'distribution-cluster']
    - exit tags: ['STRUCTURE_EXIT']

### 5 worst PANIC_EXITs


#### Worst PANIC_EXIT #1 -- HFCL (trade_id 357)

- P&L Rs -419.90 (-121.08%), qty 5.0, held 97 calendar days
- ENTRY 2026-02-05 @ 69.36
    - extension_21 7.27% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 70.0, range_contraction=False, correction depth 11.27% -> NO_BASE
    - trend-template pass=False reason=not in a confirmed uptrend (close 71.0 / 50SMA 66.4 / 200SMA 75.7) objections=[] -> COUNTER_TREND
    - day change 3.2%, rvol 1.71x, pct up from 65d low 18.77% -> not late
- EXIT 2026-05-13 @ 153.34
    - exit_state=Intact, fired_rules=none
    - exit tags: ['PANIC_EXIT']
    - 10-session-after-exit read: 10 sessions observed, pct change 13.42% by 2026-05-27

#### Worst PANIC_EXIT #2 -- TRAVELFOOD (trade_id 85)

- P&L Rs -157.00 (-1.37%), qty 10.0, held 0 calendar days
- ENTRY 2025-07-21 @ 1143.00
    - extension_21 5.37% (> 8% => EXTENDED_ENTRY) -> not extended
    - tightness pctile 100.0, range_contraction=False, correction depth 1.55% -> NO_BASE
    - trend-template pass=False reason=insufficient history for 50/200SMA trend template objections=[] -> COUNTER_TREND
    - day change 0.51%, rvol no data, pct up from 65d low 10.47% -> not late
- EXIT 2025-07-21 @ 1127.30
    - exit_state=Intact, fired_rules=none
    - exit tags: ['PANIC_EXIT']
    - 10-session-after-exit read: 10 sessions observed, pct change -9.76% by 2025-08-04

## HONEST CAVEATS

- Point-in-time only: every entry/exit read uses daily_prices up to and including that exact date; there is no intraday data anywhere in this tool, so time-of-day entries (order_execution_time is on the raw broker tradebook, not on journal_trades) are not read.
- Every tag is a mechanical reproduction of an existing gate/detector threshold (gates.EXT21_STALE, the spec's own NO_BASE/IN_BASE/LATE_IN_MOVE cutoffs, eod_detectors.exit_state's fired rules); none of it is a judgment of trader intent.
- The trend-template read always calls gate_trend_template with setup_family='momentum' (journal_trades does not record which setup family the trader believed they were trading), which is the more permissive family for the early-uptrend objection path -- a base/pattern read would COUNTER_TREND more names.
- LATE_EXIT's backward walk stops after 40 trading sessions; a Broken run older than that is reported as exactly 40, not its true age.
- range_contraction_flag returns False (not unknown) when fewer than 65 bars of history exist; combined with a tightness percentile computed off a thin window, NO_BASE can fire on genuinely undecidable early-history names rather than a confirmed non-base.
- PANIC_EXIT recovery uses daily closes only (no intraday high), and truncates to however many trading sessions actually exist in daily_prices within the window -- a short window is reported honestly via n_sessions, not padded.

### Skipped trades (no point-in-time bar match)

- BEL 2025-04-02->2025-05-13 (trade_id=15): no point-in-time exit bar for 2025-05-13
- TITAN 2025-04-09->2025-05-06 (trade_id=11): no point-in-time exit bar for 2025-05-06
- SEJALLTD 2025-05-08->2025-05-13 (trade_id=14): no point-in-time entry bar for 2025-05-08; no point-in-time exit bar for 2025-05-13
- ASTRAMICRO 2025-05-12->2025-05-12 (trade_id=13): no point-in-time entry bar for 2025-05-12; no point-in-time exit bar for 2025-05-12
- ASTRAMICRO 2025-05-12->2025-05-19 (trade_id=21): no point-in-time entry bar for 2025-05-12; no point-in-time exit bar for 2025-05-19
- PARAS 2025-05-12->2025-05-19 (trade_id=24): no point-in-time entry bar for 2025-05-12; no point-in-time exit bar for 2025-05-19
- HAL 2025-05-13->2025-05-14 (trade_id=17): no point-in-time entry bar for 2025-05-13; no point-in-time exit bar for 2025-05-14
- APOLLO 2025-05-15->2025-05-15 (trade_id=19): no point-in-time entry bar for 2025-05-15; no point-in-time exit bar for 2025-05-15
- AZAD 2025-05-15->2025-05-19 (trade_id=22): no point-in-time entry bar for 2025-05-15; no point-in-time exit bar for 2025-05-19
- HAL 2025-05-15->2025-05-19 (trade_id=23): no point-in-time entry bar for 2025-05-15; no point-in-time exit bar for 2025-05-19
- VIMTALABS 2025-05-15->2025-05-29 (trade_id=36): no point-in-time entry bar for 2025-05-15; no point-in-time exit bar for 2025-05-29
- NAZARA 2025-05-19->2025-05-30 (trade_id=37): no point-in-time entry bar for 2025-05-19; no point-in-time exit bar for 2025-05-30
- AARTIPHARM 2025-05-19->2025-06-02 (trade_id=38): no point-in-time entry bar for 2025-05-19; no point-in-time exit bar for 2025-06-02
- ETERNAL 2025-05-19->2025-07-14 (trade_id=68): no point-in-time entry bar for 2025-05-19
- HYUNDAI 2025-05-19->2025-08-19 (trade_id=116): no point-in-time entry bar for 2025-05-19
- BEL 2025-05-19->2026-02-02 (trade_id=236): no point-in-time entry bar for 2025-05-19
- HYUNDAI 2025-05-19->2026-04-17 (trade_id=304): no point-in-time entry bar for 2025-05-19
- KITEX 2025-05-21->2025-05-26 (trade_id=32): no point-in-time entry bar for 2025-05-21; no point-in-time exit bar for 2025-05-26
- TFCILTD 2025-05-22->2025-05-22 (trade_id=27): no point-in-time entry bar for 2025-05-22; no point-in-time exit bar for 2025-05-22
- PARAS 2025-05-22->2025-05-23 (trade_id=28): no point-in-time entry bar for 2025-05-22; no point-in-time exit bar for 2025-05-23
- MAZDOCK 2025-05-22->2025-05-23 (trade_id=30): no point-in-time entry bar for 2025-05-22; no point-in-time exit bar for 2025-05-23
- MAZDOCK 2025-05-22->2025-06-03 (trade_id=39): no point-in-time entry bar for 2025-05-22; no point-in-time exit bar for 2025-06-03
- QPOWER 2025-05-26->2025-05-26 (trade_id=33): no point-in-time entry bar for 2025-05-26; no point-in-time exit bar for 2025-05-26
- BALUFORGE 2025-05-26->2025-06-06 (trade_id=43): no point-in-time entry bar for 2025-05-26; no point-in-time exit bar for 2025-06-06
- QPOWER 2025-05-27->2025-05-28 (trade_id=35): no point-in-time entry bar for 2025-05-27; no point-in-time exit bar for 2025-05-28
- MAZDOCK 2025-05-29->2025-06-06 (trade_id=45): no point-in-time entry bar for 2025-05-29; no point-in-time exit bar for 2025-06-06
- THOMASCOOK 2025-06-02->2025-06-03 (trade_id=41): no point-in-time entry bar for 2025-06-02; no point-in-time exit bar for 2025-06-03
- MANGCHEFER 2025-06-03->2025-06-03 (trade_id=40): no point-in-time entry bar for 2025-06-03; no point-in-time exit bar for 2025-06-03
- IDEAFORGE 2025-06-03->2025-06-06 (trade_id=44): no point-in-time entry bar for 2025-06-03; no point-in-time exit bar for 2025-06-06
- THOMASCOOK 2025-06-03->2025-06-09 (trade_id=49): no point-in-time entry bar for 2025-06-03; no point-in-time exit bar for 2025-06-09
- 63MOONS 2025-06-06->2025-06-06 (trade_id=46): no point-in-time entry bar for 2025-06-06; no point-in-time exit bar for 2025-06-06
- PREMEXPLN 2025-06-06->2025-06-11 (trade_id=50): no point-in-time entry bar for 2025-06-06; no point-in-time exit bar for 2025-06-11
- ADVAIT 2025-07-14->2025-07-14 (trade_id=70): no point-in-time entry bar for 2025-07-14; no point-in-time exit bar for 2025-07-14
- TEMBO 2025-07-28->2025-07-30 (trade_id=99): no point-in-time entry bar for 2025-07-28; no point-in-time exit bar for 2025-07-30
- AXISCADES 2025-07-31->2025-08-01 (trade_id=105): no point-in-time entry bar for 2025-07-31; no point-in-time exit bar for 2025-08-01
- NSDL 2025-08-07->2025-08-07 (trade_id=107): no point-in-time entry bar for 2025-08-07; no point-in-time exit bar for 2025-08-07
- NSDL 2025-08-25->2025-12-16 (trade_id=190): no point-in-time entry bar for 2025-08-25; no point-in-time exit bar for 2025-12-16
- NSDL 2025-09-09->2025-12-16 (trade_id=191): no point-in-time entry bar for 2025-09-09; no point-in-time exit bar for 2025-12-16
- NSDL 2025-09-17->2025-12-16 (trade_id=192): no point-in-time entry bar for 2025-09-17; no point-in-time exit bar for 2025-12-16
- BSE 2026-01-29->2026-02-01 (trade_id=233): no point-in-time exit bar for 2026-02-01
- SILVER 2026-01-30->2026-02-01 (trade_id=232): no point-in-time exit bar for 2026-02-01
- GROWW 2026-01-30->2026-02-01 (trade_id=234): no point-in-time exit bar for 2026-02-01
- RNBDENIMS 2026-02-05->2026-04-21 (trade_id=313): no point-in-time exit bar for 2026-04-21
- TAKE 2026-02-23->2026-02-27 (trade_id=264): no point-in-time entry bar for 2026-02-23; no point-in-time exit bar for 2026-02-27
- STLTECH 2026-06-09->2026-06-11 (trade_id=382): no point-in-time entry bar for 2026-06-09; no point-in-time exit bar for 2026-06-11
