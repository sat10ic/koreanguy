# Chapter 14 Correction Log — Outperforming Sectors

Source: `Manas Arora/Course Notes/ch14.md`

Cleaned: `Manas Arora/Course Notes/cleaned/Chapter_14.md`

## High-confidence fixes applied inline

| Raw ASR | Cleaned | Reason |
|---|---|---|
| `good rates` | `good trades` | Trading context. |
| `Market Smith` | `MarketSmith` | Product name. |
| `buy demand rank` | `Buyer Demand rank` | Likely MarketSmith label; flagged in prose because exact UI label may need confirmation. |
| `Bank of Oda` | `Bank of Baroda` | Clear bank example context. |
| `20 DM` / `20 DML` | `20-DMA` | Moving-average context. |
| `low lows` | `lower lows` | Chart structure phrase. |
| `out of form` | `outperforming` | Relative-strength context. |
| `CYE NT` | `Cyient` | High-confidence ticker/name reconstruction. |
| `Zinsar tech` | `Zensar Tech` | High-confidence ticker/name reconstruction. |
| `KBIT` | `KPIT` | High-confidence ticker/name reconstruction. |
| `Sacksoft` | `Saksoft` | High-confidence ticker/name reconstruction. |
| `Aztec` | `Mastek` | Context: directly discussing Mastek under IT; cleaned where clear. |

## Flags left in cleaned file

| Query ID | Raw / issue | Best read |
|---|---|---|
| 14-a | `Hyreg` in 2019 consumer electronics examples | no safe fix; possibly Havells / HIRECT / another consumer-electronics stock. |
| 14-b | `10 moving average line` on MarketSmith group chart | likely 10-week moving average, but timeframe needs confirmation. |
| 14-c | `PSB very low priced` | likely Punjab & Sind Bank / PSB group reference; exact ticker/name unclear. |
| 14-d | `CIGB technologies` | likely Cigniti Technologies. |
| 14-e | `one lap market cap` | likely one lakh crore market-cap cutoff / scan depth, but exact unit unclear. |
| 14-f | `Same end stocks` | likely cement stocks; context lists IT, cement/construction, oil. |
| 14-g | transcript ends after `then you select proper...` | likely “proper entry,” but clause is cut. |

## Notes

- Sector-rank logic and examples were preserved in source order.
- No uncertain ticker was silently promoted without a flag/query.
- The chapter is usable as a cleaned source, but high-value ticker confirmations should be resolved before the book rewrite uses them as named proof.

