# Chapter 13 Correction Log — Market Breadth

Source: `Manas Arora/Course Notes/CH13.md`

Cleaned: `Manas Arora/Course Notes/cleaned/Chapter_13.md`

## High-confidence fixes applied inline

| Raw ASR | Cleaned | Reason |
|---|---|---|
| `bread` | `breadth` | Market breadth context throughout. |
| `Europe` | `here` | Phrase: “go really high from here.” |
| `ups` | `upside` | Market upside context. |
| `setters` | `sectors` | Index/sector analysis context. |
| `basis old` | `bases old` | Base-counting context from prior chapters. |
| `stock is above 20` | `stock is above the 20-day moving average` | Breadth-column explanation. |
| `come out before the market takes over` | retained as `come out before the market takes over` | Meaning clear enough: reduce before market reverses/catches up. |

## Flags left in cleaned file

| Query ID | Raw / issue | Best read |
|---|---|---|
| 13-a | “trading also” / “charting also” dashboards | likely TradingView / Chartink; confirm. |
| 13-b | “I’m aggressively trading my trades” at high breadth | likely “I am not aggressively trading” / “I become defensive.” Meaning inversion risk, so flagged. |
| 13-c | “After 200 stocks down, 740 were up” | likely “after 1,200 stocks down,” because previous line says 1,200 down; raw says 200. |
| 13-d | “7th, 4th, 2020” | likely 7 April 2020; date format needs confirmation. |
| 13-e | “the 97 will not really stay for long” | likely refers to low breadth around 90/97; exact number unclear. |
| 13-f | “13 to 1500 trades markets have stayed for days” | likely “1,300 to 1,500 breadth zone”; exact wording unclear. |
| 13-g | transcript ends at “Find stocks with relative…” | dropped clause; likely “relative strength.” |

## Notes

- No market-breadth extreme number was silently changed.
- The cleaned version preserves the key operating rule: use breadth at extremes, not as a daily stop/go switch.
- Action hierarchy at high breadth is preserved: tighten trail → partial exits → reduce gears → neutral if stops keep hitting.

