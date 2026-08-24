# REDESIGN — Scouting × Wire, in plain English

**Status:** specified, not built. Owner-approved direction, 2026-08-24.
**On build, this supersedes `VISUAL_LANGUAGE.md` §1, §1a and §3 in full.** The
renderer ladder (§2), the component contract (§6), the truth/evidence rules and
the empty-state contract carry over unchanged.

This is the **fourth** visual direction. The first three failed for a reason
worth recording, because it explains why this one is shaped differently:

| Direction | Why it failed |
|---|---|
| Editorial poster | Inherited from Manas OS, never chosen for this tool |
| Neo-brutalist | Followed the prose literally, produced a poor instrument at 1920×1080 |
| Quiet editorial terminal | Correct and calm, but generic — could be any data product |

All three were **surface treatments**. None came from what this product actually
is. This one does.

---

## 1. What this product actually is

You track **14+ individuals**, their public claims, their track records, and
their consistency. The daily question is *"what did they do, and does any of it
matter to me today?"*

That is not a terminal and it is not a notebook. It is **scouting** — the same
shape as a football scouting database or a cricket almanac: named people, form
over time, discipline metrics, ranked comparison.

And the feed specifically is a **newswire**: timestamped dispatches from named
sources, ranked by how much they cost the person to say. Wire language even has
a word for a retracted story — a *kill* — which is exactly what a deleted post
is, and why keeping them matters.

**Scouting gives comparison. Wire gives triage.** The corpus is 50% noise
(227 of 453 posts), so triage is not decoration — it is the difference between
a usable feed and a scroll.

**The third ingredient is plain English**, and it is the one that makes this
tool usable by someone who is not already an expert in it.

---

## 2. The three binding rules

Everything below follows from these. A screen that breaks one is a defect.

### Rule 1 — No number appears without saying what it means

Never `62%`. Always *"he keeps that promise about 6 times in 10."*
Never `XP 7.3 LOW`. Always *"only a few stocks are pushing higher — breakouts
fail more often in a market like this."*

This is not friendliness. It is **honesty enforcement**: writing the sentence
forces you to state the denominator, the age of the data, and the limits of the
claim. A bare number hides all three.

### Rule 2 — Priority is computed, never editorial

The feed's bands are derived from data, not from a judgement about what is
interesting:

| Band | Rule |
|---|---|
| **Money moved** | `post_class.kind = 'trade_event'` AND a price or stop was stated |
| **Names to watch** | `kind = 'watch_idea'` |
| **Background** | `kind IN ('breadth','theme','education','noise')` |
| **Removed** | `posts.deleted_at IS NOT NULL` — always its own band, always kept |

The tool must never decide something "matters" on a hunch. If the rule cannot
place a post, it goes to Background.

### Rule 3 — The accent means exactly one thing: money was risked

Citrus (`--risk`) marks a post or position where someone actually took a
position, and nothing else. Not emphasis, not headings, not decoration, not
hover. **BREADTH carries no accent at all**, because market internals never
involve anyone risking money.

One meaning, whole app. If you want emphasis, use weight or size.

---

## 3. Token layer

Dark ground. The accent only earns its meaning against dark, and the earlier
light directions kept pulling the tool toward "document".

```css
/* ground + structure */
--ground:      #0f1115;   /* canvas */
--raised:      #141821;   /* explained-stat blocks, callouts */
--sunken:      #181b21;   /* timeline lanes, track backgrounds */
--edge:        #23262d;   /* region border, 1px */
--hair:        #1c1f25;   /* row separator, 1px */

/* ink ladder */
--ink:         #e9eaed;   /* primary */
--ink-2:       #8b929d;   /* the plain-English gloss — Rule 1 lives here */
--ink-3:       #6f7681;   /* labels, handles, metadata */
--ink-4:       #5d626b;   /* timestamps, struck text */

/* meaning */
--risk:        #c6f24e;   /* MONEY WAS RISKED. Nothing else. */
--up:          #2f9e63;   /* a stated positive result */
--down:        #8a4a3f;   /* a stated negative result, or a removed post */
--caution:     #c9a227;   /* we do not trust this number */
--caution-bg:  #2a1f14;

--radius: 0;
--shadow: none;
```

**Colour rules.** Every colour is state- or meaning-bearing. Greyscale must
still read: the ink ladder carries hierarchy, colour only adds meaning on top.
`--caution` never appears except on a number the tool is actively disclaiming.

**Type.** System grotesk for prose; mono with `tabular-nums` for every numeral,
date, price, confidence and identifier — never for prose. Hero numbers are
800 weight, `-0.03em` tracking. Section kickers are 9.5px, `0.13em` tracking,
uppercase, 800. Prose is sentence case everywhere.

**Scale.** `hero 33 · value 15 · body 12.5 · gloss 11.5 · meta 10.5 · kicker 9.5`.
Rows ~26px plain, ~30px where a control lives (28px hit target minimum).

---

## 4. Screens

### 4.1 Today (was FEED)

Three bands in fixed order — Money moved, Names to watch, Background — then
Removed. Each band carries a one-line explanation of *why these are grouped*,
not a description of the group.

Each row: `band label · handle · what they said (verbatim) · what it means · time`.

- **The verbatim post is never paraphrased.** The gloss sits beneath it.
- The gloss may cite the trader's own record: *"He keeps that promise 6 times
  in 10"* — but only when `trader_style` has enough closed positions (§6).
- Removed posts render struck, dimmed, and **kept**, with the reason stated:
  *"People delete losers, and forgetting them would flatter everyone's record."*

### 4.2 Ledger

**Positions on one shared time axis** — this is the signature element and it is
not negotiable. A table sorted by symbol destroys the one thing this view
exists to show: that two traders were in FCL at the same time.

- One lane per position, `--sunken` background, clip spanning entry→exit.
- Clip colour: `--risk` open · `--up` stated positive · `--down` stated
  negative · `--ink-4` unstated.
- Markers on the lane for adds and stop moves.
- Right column: the outcome in words, and a `--caution` line for anything
  unstated (*"⚠ no exit price given"*).
- Below the axis, one sentence naming what the overlap shows.

The table stays, beneath the axis, sortable and filterable.

### 4.3 Traders

**One question at a time, ranked, with the sample size visible.** Not a card
grid, not four hero stats side by side.

- The question is stated in plain English above the ranking: *"Does what he says
  he'll do — how often a trader who names an exit price actually uses it."*
- Bar dims to `--ink-4` below the confidence threshold (§6).
- Below threshold shows an em dash and *"too few"*, never a percentage.
- One line under the ranking: *"A dim bar means too little history to lean on.
  A dash means we won't guess."*

### 4.4 Ideas

Grouped **by symbol, never by trader** — three people on one name is the
finding, and per-trader grouping hides it.

- Heat strip per symbol showing mention density over time.
- Each mention quoted verbatim with handle and date.
- A follow-through line: who actually bought it, or *"nobody has bought it"*.
- Footnote: whether the stock moved is deliberately not shown — a different
  question, and this screen answers what was said and who acted.

### 4.5 Library

The quote is the hero at full size; the record sits beneath it.

- Verbatim principle, attributed, dated.
- A `--raised` block: *"Followed in 18 of 25 trades where he named a stop. Of the
  7 he didn't, all 7 he moved the stop further away rather than taking the loss."*
- Below the minimum sample, the block goes `--ink-4` and says *"Not enough to
  say yet — only 2 trades link to this. We won't score it until 10."*

The finding is the product here. No chart is required.

### 4.6 Market (was BREADTH)

**Deliberately quiet. No accent anywhere.** Only `--up`/`--down` for day
colours, and `--caution` when a number is disclaimed.

- A hero number with its plain-English meaning and **its age**.
- A caution block above it whenever the number is known to be unreliable,
  naming *which parts* are sound and which are not. This is currently required
  (see §8).
- Day-colour ribbon, legend in words: *"■ most stocks rose"*.
- Trader stances against what the market did, with the honest footnote that
  matching is not the same as being right.

---

## 5. Charts — mapped to the binding ladder

| Need | Renderer | Where |
|---|---|---|
| Positions on a shared time axis | **ECharts** custom series | Ledger |
| Cumulative advance–decline | **ECharts** line | Market |
| Day-colour ribbon | inline SVG (trivial, no library) | Market |
| Hold-time distribution | **Vega-Lite** strip | Traders |
| Stop-discipline gap | **Vega-Lite** dumbbell | Traders |
| Play-type mix over time | **ECharts** stacked area | Traders |
| Posting cadence | **ECharts** calendar | Traders |
| Mention heat per symbol | inline SVG strip | Ideas |
| Attention treemap | **ECharts** treemap | Heatmap (W9) |
| Price candles | **lightweight-charts** | Symbol page |

`echarts`, `vega-lite` and `vega-embed` are already dependencies.
**No p5, no CDN scripts, no generative decoration.** A mark that cannot say what
it encodes gets deleted.

---

## 6. Thresholds — where the tool refuses to speak

| Claim | Minimum | Below it |
|---|---|---|
| A trader's rate (win, stop-kept) | 10 closed positions | em dash + "too few" |
| Practise-vs-preach score | 10 linked trades | "not enough to say yet" |
| Any percentage anywhere | its `n` shown | do not render |
| A trader-record gloss in Today | 10 closed | omit the gloss, keep the post |

These are not styling. They are the difference between a ranking and a lie.

---

## 7. Microcopy — the actual deliverable

Roughly 40–60 strings, and they are the product. Bad glosses make this **worse**
than terse labels, because they add words without adding understanding.

**Voice:** a sharp colleague who respects your time. Direct, specific, unhedged,
occasionally blunt. Never chirpy, never a tutorial, never talking down.

**Patterns:**

| Instead of | Write |
|---|---|
| `Stop honoured 62%` | "He keeps that promise about 6 times in 10." |
| `Avg 1.9R` | "A typical winner is about twice what he risked." |
| `XP 7.3 LOW` | "Only a few stocks are pushing higher. Breakouts fail more often in a market like this." |
| `unresolved: stop` | "⚠ He never said where he'd get out." |
| `noise` | "Not about the market." |
| `partial_exit 3R` | "Took profit at three times what he risked. Still holding the rest." |
| `deleted_at 11:20` | "Up 08:40, gone by 11:20." |
| `n=2` | "Only 2 trades — we won't score it until 10." |

**Rules:** state the denominator · state the age when a number is stale · never
imply certainty the data lacks · never explain the mechanism when the meaning
will do.

**Strings that already exist and must survive verbatim** — the copy audit
identified these as the tool's best writing:

- the deleted-post note about traders deleting losers biasing every metric
- the footnote that agreement measures one breadth model, **not** who was right
- "Results are what the trader *said* — never computed from market data"

---

## 8. Currently required: the Market caution block

XP is known to be unreliable as of 2026-08-24 (see `AUDIT_LEDGER.md`). Until it
is fixed, Market renders a `--caution` block above the hero number naming which
parts are sound:

> **Don't rely on this number yet.** The market-strength reading is being
> calculated wrongly — we found the fault and haven't finished fixing it. The
> day-by-day colours below are sound; the big number is not.

**Remove this block when XP is fixed.** A stale disclaimer is its own kind of
dishonesty.

---

## 9. Banned

Everything from the previous directions' banned lists still applies, plus:

| Banned | Why |
|---|---|
| Accent used for anything but "money was risked" | Destroys Rule 3 |
| A bare percentage without its `n` | Rule 1 |
| A number without a plain-English meaning | Rule 1 |
| Editorial priority ("interesting", "hot") | Rule 2 |
| Card grids of hero stats | The pattern all three prior directions kept regressing to |
| Rounded corners, gradients, glow, glass, soft shadows | — |
| Serif type | — |
| p5 / generative decoration / CDN scripts | Not on the ladder; encodes nothing |
| Colour-coding traders by hue | 14 hues breaks state-only colour |

---

## 10. Build order

1. **Token layer + shell** — `tokens.css`, nav, the explained-stat component.
2. **Today** — bands, rows, glosses. Carries the whole system's voice.
3. **Ledger** — the shared time axis (ECharts). The signature element.
4. **Traders** — ranked question + thresholds.
5. **Ideas**, **Library** — lower risk, follow the established patterns.
6. **Market** — last, and **only after XP is fixed**. Do not reskin a screen
   whose numbers are wrong; fix the number, then dress it.

The three approved additions land alongside: the ⌘K command bar, the symbol
landing page (where lightweight-charts goes), and the new charts above.

**Microcopy is not delegated cheaply.** It is writing, not styling, and it is
what makes this direction work at all.

---

## 11. Open and unverified

- **`Unverified:` these are mockups, not the running app.** They prove the
  direction reads well; they do not prove it survives real payload shapes, long
  symbol names, or 453 rows at 1920×1080.
- The Removed band is currently **empty** — `posts.deleted_at` has 0 rows, so
  it will not appear until a real deletion is caught.
- Trader-record glosses in Today depend on `trader_style`, which W6 has not
  built. Until then, omit the gloss rather than inventing one.
- The owner chose dark. If that is revisited, the accent must be rechosen — it
  carries its meaning against dark and would need a different value on light.
