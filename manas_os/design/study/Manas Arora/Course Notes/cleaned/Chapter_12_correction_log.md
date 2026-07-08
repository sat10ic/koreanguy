# Chapter 12 Correction Log — How Fast Can You Really Grow Your Account?

Source: `Manas Arora/Course Notes/ch12.md` / `ch12.txt`

Cleaned: `Manas Arora/Course Notes/cleaned/Chapter_12.md`

## High-confidence fixes applied inline

| Raw ASR | Cleaned | Reason |
|---|---|---|
| `write these moves` / `writing the position` | `ride these moves` / `riding the position` | Confirmed recurring garble in holding/selling context. |
| `moving out line` | `moving average line` | Clear moving-average context. |
| `20 dmr` / `20 dm a` / `20 DM stock` | `20-DMA` / `20-DMA stock/trailing line` | Clear trading-term context; preserved ambiguity where the full sentence was unclear. |
| `closing bases` | `closing basis` | Common trading phrase. |
| `flat week based breakout` | `flat weekly-base breakout` | Grammar + chart context. |
| `this dog went` | `this stock went` | Clear ASR substitution. |
| `five x second no time` | `5x in no time` | Clear phrase-level garble. |
| `entire alley` | `entire rally` | Market context. |
| `rating your start skill` | `rating your chart-reading skill` | Clear from the sentence about judging one price bar. |
| `one or two games` | `one- or two-day gains` | Profit-taking context. |

## Flags left in cleaned file

| Query ID | Raw / issue | Best read |
|---|---|---|
| 12-a | HEG numbers conflict: `2072 to 5000` and later `200 to 3000` | Possible split-adjusted/raw-price mix; both preserved. |
| 12-b | Unnamed post-HEG weekly-base example: `257 to 400`, then `374 to 681` | Ticker not recoverable from transcript. |
| 12-c | Unnamed 2014 winner: `25 to 86` | Ticker not recoverable from transcript. |
| 12-d | `matchdoc` | Likely Mazdock / Mazagon Dock, but ticker identity cannot be silently fixed. |
| 12-e | Rain phrase: `more than a percent` | Likely “more than 100%”; number-related, so flagged. |
| 12-f | `BSC` | Possibly BSE Ltd; same recurring unresolved item as Ch6. |
| 12-g | Unnamed 2022 example: October/November 2021 to January 2022; `250 to 500` June-August | Ticker not recoverable from transcript. |
| 12-h | Mirza cost-reduction sentence after selling half | Calculation wording garbled. |
| 12-i | `the all is again I am stopped out here` | Exit/trailing-stop sentence unclear. |
| 12-j | `train` example, cost around `60` | Likely Rain, but ticker identity cannot be silently fixed. |
| 12-k | `120% allocation` producing `18%` portfolio return from `93%` stock move | Likely `20% allocation`; raw number preserved and flagged. |

## Notes

- No source order was changed.
- No number, price, percentage, ticker identity or date was silently changed.
- The chapter is usable as a cleaned source, but the flagged items should be answered before book-level rewrite uses them as firm examples.
