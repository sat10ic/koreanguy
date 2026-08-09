# HANDOFF — Weekly breakout timeframe scan COMPLETED

## Resample Approach
1. **Source Data**: The `daily_prices` table in `manas.db` is queried for the target symbol.
2. **Aggregation**: Daily price bars are resampled to weekly timeframe (Mon-Fri) by grouping daily bars by their ISO Year and ISO Week.
   - `open`: Open price of the first trading day of the week.
   - `high`: Maximum high price among all trading days in the week.
   - `low`: Minimum low price among all trading days in the week.
   - `close`: Close price of the last trading day of the week.
   - `volume`: Sum of volume for all trading days in the week.
   - `delivery_pct`: Rupee-weighted average (total delivery quantity / total volume * 100.0).
   - `prev_close`: Shifted close of the prior weekly bar.

## Function Contract
Defined in `manas_os/engine/eod_detectors.py`:
- `resample_daily_to_weekly(daily_bars: list[dict[str, Any]]) -> list[dict[str, Any]]`
- `detect_weekly_breakout(daily_bars: list[dict[str, Any]]) -> bool`
  - Returns `True` if:
    1. Weekly close > 20-week high pivot (highest weekly high of the preceding 20 weeks).
    2. Weekly volume >= 1.2x 20-week average weekly volume.
    3. Weekly close is in the upper portion of the weekly range: `(close - low) / (high - low) >= 0.7`.

## Preset & Hit Counts (2026-07-10)
- Registered Preset: `"weekly_base_breakout"` in `scanner_presets.py`.
- **Status**: `LIVE`.
- **Hit Count on 2026-07-10**: Exactly 20 symbols (governed by the archetype cap size control of 20).
- **Hits list**:
  - `AZAD`, `BETA`, `BLUEJET`, `EMSLIMITED`, `FILATEX`, `GANDHAR`, `GODREJIND`, `GREAVESCOT`, `HIKAL`, `INDOBORAX`, `INDSWFTLAB`, `LODHA`, `MUTHOOTMF`, `PPAP`, `RAYMOND`, `RML`, `SKYGOLD`, `STYL`, `UNICHEMLAB`, `WABAG`.

## Test Results
- Added standalone unit tests to `manas_os/tests/test_eod_detectors.py`:
  - `test_resample_daily_to_weekly`: Verifies daily-to-weekly OHLCV resampling math and date aligning.
  - `test_detect_weekly_breakout_math`: Verifies pivot, volume-confirm (1.2x), and close-position (>=0.7) trigger logic.
- All unit tests passed successfully.

## Wiring Notes
- Added `"weekly_base_breakout"` setup family and discovery archetype mapping to `manas_os/scanner/candidates.py` and `manas_os/scanner/discovery.py`.
- Allowed `"weekly_base_breakout"` setups in `gates.py` for `"RISK_ON"` and `"SELECTIVE"` regimes.
- Registered `"weekly_base_breakout"` preset in `scanner_presets.py`.
