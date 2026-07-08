# Chapter 8 Correction Log — Ride or Sell

Source: `../CH 8.md`

Cleaned output: `Chapter_8.md`

## High-confidence corrections applied

| Raw ASR | Cleaned term | Reason |
|---|---|---|
| `write or sell` / `write it` | ride or sell / ride it | Chapter is about riding profitable trades; recurring ASR error. |
| `trading stock loss` / `trading stock` | trailing stop-loss / trailing stop | Stop-management context. |
| `BQN` | breakeven | Stop moved so trade cannot lose money. |
| `Zentec` / `Zendik` | Zen Technologies | Known ticker/name from earlier chapters. |
| `PTM` | Paytm | Known ticker/name from earlier chapters. |
| `TDPOW system` / `trading power systems` / `ED power system` | TD Power Systems | Strong acoustic/context match; stock example in trade-management chapter. |
| `weekends` | weak hands | Pullback/flushing context. |
| `4-bays` / `four pieces` / `basis old` | four bases old | Base-counting context from earlier chapters. |
| `20 pure line` / `20 period moving average line` | 20-DMA / 20-period moving average | Moving-average trailing context. |
| `five-year moving average` | 5-period moving average / 5-DMA | Context is short-period trailing line, not five-year average. |
| `MNC stop` | emergency stop | Same stop concept used throughout chapter. |

## Important source facts preserved

- Sell side is harder than buy side because losses have clear stops, but profits create confusion.
- Market environment decides whether to ride aggressively or sell quickly.
- In a young market, Manas rides winners, adds to them if valid setups appear, and lets trailing stops take him out.
- On **29 March**, he observed leaders already making new highs before the market fully moved.
- A stock up around **9% on day one** led him to move stop to breakeven, not because 9% is a fixed threshold, but because a stop-hit would imply a massive ugly red bar.
- A **20-DMA** trailing line is used on a convincing closing basis, with an emergency stop below recent swings.
- When the move becomes old or extended, he stops waiting for the trailing line and sells into strength.
- Extension warnings preserved: several bases old, 50% / 30% type extension, many green days, angle shifting toward **90 degrees**, high volume near top, second extension in a short time.
- NCC example: about **seven positions**, roughly **78,000 shares** ⚠, first sale on **3 May**, more on **5 May**, majority around **8 May**, sale around **₹125**, stock about **27%** up.
- TD Power Systems example: bought **24 April** around **₹161**, young market, later about **33%** up from base, switch from 20-DMA to 10-DMA when old/extended.
- Olectra example: bought around **₹682**, sold **75%** around **9:40** on **13 June**, stock around **27-30%** up from base, angle around **80 degrees**, market overheated around **14-15 June**.
- MRPL example: bought around **₹66.45**, stock up **22% in three days**, sold around **60%** ⚠ on **19 June**, retained around **40%**, switched to 10-DMA due to market extension.
- JBM Auto example: moved from around **₹662** to **₹845**, up **82%** from one point and **26%** from latest base, around **21 June** market no longer young, use partial profit + 10-DMA / 5-DMA for smaller leftover, **14 bars in a row**, last two bars highest volume, around **30 June** upside limited.
- Emergency-stop concept preserved: minor closes below moving averages are acceptable in a young move if emergency stop is intact and selling pressure is not severe.
- Example preserved where closing too soon would miss another **27%** move and a **13%** bounce.
- Final market-weather rule preserved: in late markets, book smaller gains; in young supportive markets, ride leaders.

## Unresolved or confirmation-needed items

| ID | Raw ASR | Probable correction / handling | Why flagged |
|---|---|---|---|
| 8-a | `C295` / `C295 out of my portfolio, 56 names` | No safe fix. Possibly "new highs" / 52-week highs / portfolio count phrase. | Important 29 March portfolio observation but raw wording is unclear. |
| 8-b | `Electra` / `Olectra` | Probable Olectra Greentech in the ₹682 example; earlier "Electra" could also be Elecon in other chapters. | Ticker must be confirmed before final book tables. |
| 8-c | `Solata software` | Probable Sonata Software. | Acoustic fit, but confirm. |
| 8-d | `GBMA` / `JBMA` | Probable JBM Auto in some contexts, but not always certain. | Member-trade references unclear. |
| 8-e | first long ride example ticker | Probable Zen Technologies, but raw has garbles including `intake trade`. | The example references Zen-like behaviour and later ₹340 sale, but exact identity should be confirmed. |
| 8-f | `sold 607` in MRPL | Probable "sold 60%" / "sold 60-70%". | Percentage/quantity matters; cleaned as around 60% with flag. |
| 8-g | NCC `closed 28` from 78,000 shares | Probable 28,000 shares sold, but raw is unclear. | Position-size detail should be confirmed. |
| 8-h | `Masdoc` | Probable Mazdock / Mazagon Dock. | Final-summary example list; ticker confirm needed. |
| 8-i | `RBNL` | Probable RVNL. | Final-summary example list; ticker confirm needed. |
| 8-j | `1 is to 500` | Probable 1:50 / R-multiple discussion. | Raw phrase conflicts; cleaned around 1:50 because context says 15 mistakes/risks. |

## Book-build caution

This chapter is a core trade-management source. It should likely become two book chapters or one large chapter with strong visual structure:

1. **Ride while the market and move are young** — 20-DMA trailing, closing basis, emergency stop, add on valid reactions.
2. **Sell into strength when the move is old** — extension warnings, 10-DMA / 5-DMA tightening, partial exits, market-weather shift.

Do not reduce it to “trail with moving averages.” The nuance is the whole lesson: the same moving average means different things in a young move versus an old, extended move.

