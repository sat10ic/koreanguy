# ChartsMaze trader-template criteria (user-supplied screenshots, 2026-07-10)

Source: manas_os/design/chartsmaze scans/*.png — exact values transcribed from the site's
own filter UI. These are the 5 trader TEMPLATES; more importantly they reveal ChartsMaze's
UNIVERSAL filter vocabulary used across screeners (turnover formula, circuit exclusion,
mcap/price bands) — direct inputs for WAVE H calibration (H1.1 universe alignment + H2 ports).

## Universal vocabulary (appears across templates — likely inside screeners too)
- Turnover: `Stock Price * MA-N Volume > X` with N ∈ {20, 50}; X seen: 3,00,00,000 (3cr) and
  5,00,00,000 (5cr). ALSO expressed as "50 Days Average Rupee Turnover (Cr.) > 5".
- Circuit exclusion: "Exclude Circuit Stocks: 5% Circuit Limit, ..." (5% band names dropped).
- Market-cap ranges in Cr; stock-price ranges in rupees.
- MA bands: `k_low * MA < Stock Price < MA * k_high` (e.g. 0.98 * 21EMA < P < 21EMA * 4).
- OR-filter blocks: return-range windows (1M/3M/1Y %).

## NITIN template (Scans tab)
- Inside Bar (D) ✓; NR7 ✓
- 1 * 200MA < Price < 200MA * 4
- 0.98 * 21EMA < Price < 21EMA * 4
- 0.98 * 50EMA < Price < 50EMA * 4
- 0.98 * 10EMA < Price < 10EMA * 4
- Stock Price: 25 – 10000
- Market Cap (Cr): 300 – 50,00,000
- 20MA (Price*Volume) > 5,00,00,000  (₹5cr)
- 50MA (Price*Volume) > 5,00,00,000  (₹5cr)
- Exclude Circuit Stocks: 5% Circuit Limit

## CHHIRAG template (Scans tab; unchecked rows shown greyed)
- Market Cap (Cr): 1000 – 2,00,000 ✓
- Stock Price: 10 – 10000 ✓
- 50-Days Average Rupee Turnover (Cr) > 5 ✓
- Exclude Circuit Stocks: 5% Circuit Limit ✓
- (unchecked/available: price vs MA dropdown, 20-day day-range, MA order 20>=50>=200 EMA,
  0.98*10EMA band, OR-filters 1M return -10..100, 3M return -10..300)

## HIMANSHU template (Preset tab)
- Overall RS Range: 70 – 100 ✓
- Volume Gainers ✓
- Gap Up ✓
- Listing Date > 2024/01/01 ✓  (recent-listings lens)
- (unchecked: Near New Highs (1 Month High,3..), 1-Day return range, 200MA Turn Around)

## HIREN template (Scans tab)
- MA-50 Volume > 1,00,000 shares ✓
- Stock Price * MA-20 Volume > 3,00,00,000 (₹3cr) ✓
- Market Cap (Cr): 0 – 50,00,000 ✓
- Stock Price: 1 – 1,50,000 ✓
- Exclude Circuit Stocks: 5% Circuit Limit ✓
- OR Filters: 1M Return 20–100% ✓  OR  3M Return 30–300% ✓  (momentum leg)

## SHASHANK template (Scans tab — fundamentals-heavy)
- YoY % Quarterly EPS Growth > 10 ✓ ; YoY % Quarterly Net Profit Growth > 10 ✓
- YoY % Quarterly Sales Growth > 10 ✓ ; Sales Growth 5Y (%) > 10 ✓
- Net Profit Last 4 Quarters is +ve ✓ ; ROE(%) > 15 ✓ ; ROCE(%) > 15 ✓ ; OPM TTM(%) > 15 ✓
- D/E < 1 ✓ ; EPS Last Year > Preceding Year ✓
- Price Above 200-Day MA ✓ ; Market Cap (Cr): 1000 – 25000 ✓
- 1Y Return Range: 10 – 500% ✓ ; Exclude Circuit Stocks: 5% Circuit Limit ✓

## Implications for WAVE H
1. H1.1 universe alignment should test the ChartsMaze-style turnover filter
   (price × MA20vol > 3-5cr) rather than only our GateConfig's 5cr avg-turnover — try both.
2. Circuit exclusion at the 5% band = confirmed universal — our circuit_bands table feeds this.
3. Screener-level thresholds (volume-spike multiplier etc.) still need calibration, but
   universe mismatch is now largely resolved by this vocabulary.
4. Trader templates themselves become reproducible in-house scans once H2 primitives exist
   (all five are compositions of: MA bands, turnover, mcap/price, circuit, RS range,
   return windows, fundamentals joins — every primitive already in our DB).
