# WIREFRAMES — TraderLog

**Read `VISUAL_LANGUAGE.md` first.** It is the binding appearance and chart
vocabulary above this layout spec. A screen that satisfies the ASCII layout but
uses a banned form or misses a required visual-language rule is still defective.

**Scouting × Wire revision (2026-08-24).** This file is reconciled against
`design/REDESIGN_SCOUTING_WIRE.md`, the binding fourth direction. It supersedes
the earlier FEED/BREADTH compositions: FEED is now **TODAY** (triage bands),
BREADTH is now **MARKET** (quiet, accent-free). Where anything below conflicts
with `REDESIGN_SCOUTING_WIRE.md`, the redesign document wins. The renderer
ladder and the truth/evidence rules carry over unchanged.

**Binding layout spec.** Screens are built to these ASCII mockups
element-for-element. Done-test: screenshot each screen and diff it against its
section here. A screen that renders something not listed below is a defect, and
so is a listed element that does not render.

Convention adopted from `manas_os/design/WIREFRAMES_V4.md`. Every element carries
a provenance tag and **nothing may be invented without one**:

| Tag | Means |
|---|---|
| `⟨field x.y⟩` | reads an existing key in the endpoint payload |
| `⟨derive m⟩` | computed by module `m`, persisted, then read |
| `⟨cite src⟩` | traces to a named external source or practitioner |
| `⟨NEW ...⟩` | a payload change that must be built before the element can render |

**Rule inherited from Manas OS: every number on screen must exist in a payload
today. An invented metric is a defect, not a placeholder.**

Aesthetic details and the pre-completion visual audit are canonical in
`VISUAL_LANGUAGE.md`; this file does not override or abbreviate them. The
scouting tokens (dark ground, ink ladder, `--risk` = money was risked and
nothing else) are canonical in `REDESIGN_SCOUTING_WIRE.md` §3.

Six product screens. Shell is a single tab strip; the active tab syncs to `?tab=`.
At 1920×1080 everything aligns to one centered 1680px grid. STYLE and SYMBOL are
route-only (`?tab=STYLE`, `?tab=SYMBOL&symbol=X`) — not in visible navigation.

```
┌───────────────────────────── 1680px centered ───────────────────────────────┐
│  TRADERLOG      TODAY  LEDGER  TRADERS  IDEAS  LIBRARY  MARKET              │
│                 ─────                                                       │
│  ⚠ SHOWING MOCK DATA — no posts have been ingested yet   ⟨field is_mock⟩    │
│  ⌘K                    (Ctrl/Cmd+K opens the command bar)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The mock-data banner is **mandatory** while `is_mock` is true on any payload.
A tool that looks real while showing invented data is the specific failure this
project is built to avoid.

**Command bar (⌘K)** — `⟨control⟩`. Global `Ctrl/Cmd+K` opens a keyboard
palette: type-to-filter over the six tabs, every trader (`/api/traders`), and
every symbol in the corpus (positions + watch ideas). Arrow keys highlight,
Enter navigates (tabs directly; traders → `?tab=TRADERS&handle=…`; symbols →
`?tab=SYMBOL&symbol=…`), Esc/click-outside closes. `role="dialog"` + aria-label
"Command bar", focus management on open.

═══════════════════════════════════════════════════════════════════════════════
## 1 · TODAY — "what did they do, and does any of it matter to me today?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/feed` · `/api/review` · `POST /api/review/{id}` · `/api/traders`

**Scouting × Wire composition (2026-08-24).** Four computed bands in fixed
order — Money moved, Names to watch, Background, then Removed — each headed by
a kicker label and one line explaining *why these are grouped* (never a
description of the group). Banding is computed from payload fields (Rule 2),
never editorial.

```
┌── REVIEW QUEUE · 1 open ────────────────────────────────────────────────┐
│  work the human owes the tool — one decision at a time                  │
│  "@fastzone sold 1/3rd FCL"  conf 0.62   why: …  but: …                 │
│                        [ ✓ attach ]  [ ✗ no ]      (aria-busy while    │
│                                                    pending; no double  │
│                                                    submit)             │
└─────────────────────────────────────────────────────────────────────────┘
┌── MONEY MOVED ──────────────────────────────────────────────────────────┐
│  Money on the table is the only thing that's verifiable.                │
│  ▍ ENTRY   @manas_arora · 14:32 · 2/4  "added 25% more at 1847,         │
│  ▍                                  sl trailed to 1790"                 │
│  ▍   Put money on APOLLOTYRE at ₹1,847.              ↗ source           │
│  ▍ ADD     @manas_arora · 14:40 · reply   "booked half"                 │
│  ▍   Booked APOLLOTYRE at ₹1,910 — half the position.                  │
├─────────────────────────────────────────────────────────────────────────┤
│  WATCH    @fastzone · 08:40   "FCL above 45 on volume"                  │
│           A name to watch — FCL.                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  BREADTH  @nitin_bhatia · 09:12   "staying light — market is thin"      │
│           His read on the market that day.                              │
│  NOISE    @fastzone · 16:02   "cricket highlights 🏏"                   │
│           Not about the market.                                         │
└─────────────────────────────────────────────────────────────────────────┘
[ filters: trader ▾ kind ▾ confidence ≥0.0 ▾ unresolved ]  [ load older ]
```

**Elements**

- Review queue — `⟨field review[]⟩` above the bands, always, when non-empty.
  It is work the human owes the tool, not a band. Question `⟨field
  review[].question⟩`, `why:` `⟨field review[].reasoning⟩`, `but:` `⟨field
  review[].alternatives[]⟩`, conf `⟨field review[].confidence⟩`. Both buttons
  `POST /api/review/{id}`; one decision at a time; disabled/`aria-busy` while
  pending; double-click guard; inline error; in-session refresh of list, posts
  and the TODAY tab badge. Never a bulk "accept all".
- Bands — computed client-side from `⟨field feed.posts[]⟩`, in fixed order
  Money moved → Names to watch → Background → Removed:
  - **Money moved** — `kind = 'trade_event'` AND a stated price or stop
    (`⟨field feed.posts[].event.price⟩` present).
  - **Names to watch** — `kind = 'watch_idea'`.
  - **Background** — `kind IN ('breadth','theme','education','noise')`, plus
    unclassified, plus anything the rules cannot place (incl. `trade_event`
    with no stated price).
  - **Removed** — `deleted_at IS NOT NULL`, always its own band, always kept,
    struck + dimmed. The band renders **only when non-empty** (empty today
    until a real deletion is caught). Protected note verbatim: "⚠ this post
    was removed by its author. Kept on purpose — traders delete losers, and
    dropping them would bias every derived metric."
  - Band why-lines (≤13 words): Money moved "Money on the table is the only
    thing that's verifiable." · Names to watch "A name to watch — with or
    without a trigger level." · Background "Everything else — commentary,
    themes, principles, banter." · Removed "People delete losers, and
    forgetting them would flatter everyone's record."
- Row anatomy — `band label · @handle · date+time · thread chip · verbatim
  text · gloss · meta`. The verbatim post is never paraphrased or truncated.
  The gloss (`--ink-2`) is the plain-English meaning derived from payload
  fields only (Rule 1); on Money-moved rows it follows the copy appendix
  patterns (e.g. "Put money on SYMBOL at PRICE." / "Added at PRICE." / "Booked
  SYMBOL at PRICE — the whole position." / "Stated a stop at PRICE."). An
  unstated stop appends "⚠ He never said where he'd get out." Trader-record
  glosses are omitted while `trader_style` has <10 closed positions (§11).
  Prices via `Num()` (₹ prefix; 2dp below ₹100, 0dp at or above). Symbol →
  `?tab=SYMBOL&symbol=…`; handle → `?tab=TRADERS&handle=…`; source ↗ → x.com.
- Threads — posts in a known conversation (`thread_pos`/`thread_size > 1`)
  keep a 1px spine and their position chip; self-replies render beneath their
  root in the same band; unknown ancestry renders plainly, never faked as a
  root.
- Money rows carry the single `--risk` marker (a small square) — the ONLY
  accent use on the screen. Nothing else may use `--risk`.
- Deleted rows — struck text, `--ink-4`, no link, protected note + gloss
  "Up HH:MM, gone by HH:MM." (`ts_ist` → `deleted_at`).
- Filters toolbar — `⟨field feed filters⟩`: handle, kind (incl. unclassified),
  min confidence, unresolved toggle — mapping to `/api/feed` params exactly.
- Pagination — "load older" through `⟨field feed.pagination.next_offset⟩`;
  posts land in their band by rule regardless of page.
- Empty states — one compact muted line, never a framed graphic: unfiltered
  and filtered variants naming the reason.

**Payload reshapes**: none in this wave — banding is client-side over the
existing `/api/feed` payload (`kind`, `event`, `deleted_at`, `ts_ist`,
`thread_pos/size`).

═══════════════════════════════════════════════════════════════════════════════
## 2 · LEDGER — "every trade we reconstructed, and the receipts"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/positions` · `/api/positions/{id}`

**Positions on one shared time axis — the signature element, not negotiable
(§4.2).** One lane per position; a table sorted by symbol destroys the one
thing this view exists to show: that two traders were in the same name at the
same time.

```
┌── WHEN THEY WERE IN ────────────── shared time axis · ECharts custom series ┐
│         Jul 20         Aug 01         Aug 15         Aug 22                 │
│ DIXON   ▓━━━━━━━━━━━━━━━▲━━━━━━━━━━━━━━━━━━━━━━━━━○   booked +9.9%        │
│ FCL     ▓━━━━━━━━━━━━━━━▲━━━━━━━━━━━━━━━━━━━━━━━━━▶   still open ⚠ stop   │
│ KPITTECH    ▓━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶   never stated        │
│          ▓ open ─ risk   ● add   ▲ stop move   ○ exit   ▶ still open        │
│  Fastzone and Manas were both in FCL at the same time.  (computed)          │
└─────────────────────────────────────────────────────────────────────────────┘

┌── POSITIONS ─────────────────────────────────────────────────────────────┐
│  trader  symbol  entry   adds   stop   exit   net   days  cf   ▸          │
│  (SortableTh headers; filters: trader ▾ status ▾ symbol conf ≥0.0 ▾)       │
│  ▸ @manas DIXON   14,200  1×1,847  13,800 15,610 +9.9%  23   ·95          │
│    01 Aug ENTRY ₹14,200 "starter…"  ↗ post                                │
│    09 Aug SL MOVE 13,800→14,450 "risk off the table" ↗ post               │
│    24 Aug EXIT ₹15,610 100% "booked, +9.9%" ↗ post                        │
│    evidence: symbol ← post 1953… · entries[0] ← 1953… · exit ← 1962…      │
│    [chart image — contained ≤ media box, never widens the doc]            │
│    unresolved: position size never stated                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- **Shared time axis — `PositionBars`** `⟨field positions[]⟩` +
  `⟨field positions[].events[]⟩`. One lane per position (`--sunken`), clip
  spanning entry→exit on one domain (min start → max end/today). Clip colour:
  `--risk` open · `--up` stated positive · `--down` stated negative ·
  `--ink-4` unstated. Event markers on the lane (add, stop up/down, exit)
  `⟨field positions[].events[]⟩`. Row click → expanded table row.
- **Outcome in words** — beside/below the axis, per lane: "booked +9.9%" /
  "still open" / "not stated", with a `--caution` line naming what is missing
  verbatim from `unresolved[]` (e.g. "⚠ stop never stated").
- **Overlap sentence** — `⟨derive client-side⟩`: one sentence naming what the
  overlap shows, computed from real intervals (densest pair; same-symbol
  preferred), or the honest "No two positions overlapped in this window."
  Never a placeholder.
- Table `⟨field positions[]⟩` — `net` blank unless the trader stated a result
  or both prices — never computed from market data. `cf` mono 2dp, no %.
  SortableTh headers; filters trader/status/symbol/confidence/unresolved toggle.
- Row expands via a `Disclosure` caret (not a bare row click) to the event
  timeline `⟨field positions/{id}.events[]⟩`, each line citing its post with a
  link out; the **evidence block is not optional and not behind a toggle**
  `⟨field positions/{id}.evidence⟩`; `unresolved[]` expanded with complete
  strings, never paraphrased.
- Media `⟨field positions/{id}.media[]⟩` — served by `/api/media`, never
  hotlinked; **contained** per W3c rules: `display:block; width:100%;
  max-width:100%; height:auto; object-fit:contain`; intrinsic size must never
  enlarge the grid, panel, or document (real 1709px-wide archived image is the
  regression case).
- Protected footnote verbatim: "Results are what the trader *said* — never
  computed from market data."

═══════════════════════════════════════════════════════════════════════════════
## 3 · TRADERS — "does what he says he'll do, and does he mean it?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/traders` · `/api/traders/{handle}` · `/api/feed`

**One question at a time, ranked, with the sample size visible (§4.3).** Not a
card grid, not four hero stats side by side.

```
┌── Does what he says he'll do — how often a trader who names an exit ────────┐
│   price actually uses it.                                                   │
│  [ stop-kept | win rate | avg R | hold | preach ]   (Segmented)            │
│                                                                             │
│  @fastzone      ████████████████████░░░░░  62%   n=25                       │
│  @iManasArora   ████████████████░░░░░░░░░  58%   n=11                       │
│  @stocksnerd    ░░░░░░░░░░░░░░░░░░░░░░░░  — too few                         │
│                                                                             │
│  A dim bar means too little history to lean on. A dash means we won't       │
│  guess.                                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  handle  tier  posts  open  closed  hold  win  preach  ▸ (SortableTh)       │
│  ── four charts with labelled empty states: hold-time StripPlot, stop-      │
│     discipline Dumbbell, play-type StackedArea, posting CalendarGrid ──     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Question selector — `Segmented` over stop-kept (default, verbatim question
  string from §4.3), win rate, avg R, median hold, preach. Each question is
  stated in plain English above the ranking.
- Ranking — one row per trader, sorted by the metric; every percentage shows
  its `n`. **Thresholds (§6):** below 10 closed positions (or 10 linked trades
  for preach) the bar dims to `--ink-4` and the value renders an em dash +
  "too few" — never a percentage. `trader_style` is empty today (W6 not
  built): every row honestly shows the dash/"too few" state.
- Verbatim one-liner beneath the ranking: "A dim bar means too little history
  to lean on. A dash means we won't guess."
- Roster table `⟨field traders[]⟩` — handle, tier, posts, open, closed, hold,
  win, preach with SortableTh; keyboard-reachable rows (`Disclosure`);
  selecting opens the profile `⟨field traders/{handle}⟩` restyled per the
  direction: lead stat with meaning, open positions (open = `--risk` dot),
  unstated fields "—"/"not stated". Handle cross-links to
  `?tab=TRADERS&handle=…` and symbol → `?tab=LEDGER&symbol=…` / SYMBOL page.
- Charts — `StripPlot` (hold-time, from `closed[]` holding_days), `Dumbbell`
  (stated vs honoured stop), `StackedArea` (play-type mix over time — renders
  its labelled empty state until the feed payload carries `play_type`),
  `CalendarGrid` (posting cadence from feed `ts_ist`). Every chart `.chart-empty`
  with a reason when data is absent — never null, never a zero-height SVG.

═══════════════════════════════════════════════════════════════════════════════
## 4 · IDEAS — "what are they watching, and did it go anywhere?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/ideas` · `/api/positions`

**Grouped by symbol, never by trader (§4.4)** — three people on one name is
the finding, and per-trader grouping hides it.

```
┌── FCL · 3 traders · first 04 Aug ───────────────────────────────────────────┐
│  ░▒▓░░░░▓░░  (mention-density heat strip, inline SVG)  N mentions across   │
│                    D days · darker is denser                               │
│  @fastzonetrader 04 Aug  WATCH  "FCL above 45 on volume"  (verbatim)        │
│  @manas_arora    06 Aug  EP      "post-results gap, watching the base"      │
│  → who actually bought it: @manas at ₹39.05 on 06 Aug     (or "nobody has  │
│                                              bought it" when true)          │
├─────────────────────────────────────────────────────────────────────────────┤
│  THEMES  DEFENCE ████████ 12 mentions · 4 symbols · last 21 Aug             │
└─────────────────────────────────────────────────────────────────────────────┘
   This screen reports what was said and who acted, not who was right.
   Whether the stock moved is deliberately not shown — a different question.
```

**Elements**

- Grouped by symbol `⟨field ideas[]⟩` (trader_count desc, then symbol); a
  **heat strip** per symbol showing mention density over time — inline SVG
  (no library): cells = days (span ≤14d) or weeks (≤52 cells), intensity ∝
  mentions per bucket, `role="img"` + aria-label stating the finding in words,
  axis labels first/last date mono. `.chart-empty` with a reason when no
  mention dates exist.
- Each mention quoted **verbatim** with handle and date; kind chip
  (WATCH/EP/IPO/THEME) differentiated by fill weight, never hue.
- **Follow-through line** — from `⟨field ideas[].taken_by⟩` + positions:
  "who actually bought it: @handle at ₹price on date", or the verbatim
  "nobody has bought it" when true. The money phrase is the screen's only
  `--risk`.
- Footnote verbatim (protected): "This screen reports what was said and who
  acted, not who was right. Whether the stock moved is deliberately not shown
  — a different question."
- Ticker leaderboard (client-side from `/api/positions` + `/api/ideas`) and
  themes `⟨field themes[]⟩` kept from the earlier composition.

═══════════════════════════════════════════════════════════════════════════════
## 5 · LIBRARY — "what do they teach, and do they follow it?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/library`

**The quote is the hero at full size (§4.5); the record sits beneath it.**

```
┌── STOPS · 14 items ────────────────────────────────────────────────────────┐
│                                                                             │
│  @manas_arora · 12 Jul                                                      │
│  "the stop goes where the idea is wrong, not where your loss feels big"     │
│                                                              ↗ post          │
│  ┌── practised? (--raised) ────────────────────────────────────────────┐    │
│  │  Followed in 18 of 25 trades where he named a stop. Of the 7 he     │    │
│  │  didn't, each one is cited below.                                   │    │
│  │  Score: 72% of 25.                                                  │    │
│  │  ✗ DIXON 09 Aug (widened) — cit… · ✗ TATAELXSI 22 Jul (widened) …   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  (below 10 linked trades the block dims to --ink-4 and says: "Not enough    │
│   to say yet — only N trades link to this. We won't score it until 10."     │
│   NO percentage at all below the minimum.)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Topic tabs `⟨field library.topics[]⟩` (first-topic default; chips).
- Principle text `⟨field edu_items.principle_text⟩` — **verbatim, quoted, at
  full size, attributed and dated** (`@handle`, `stated_at`), linked to the
  original post.
- Practice block `⟨derive edu_links⟩` on `--raised` ground — the record in
  WORDS from real followed/violated/na numbers ("Followed in N of M trades
  where he named a stop…"), with `na` acknowledged when >0, and **the
  10-linked-trade minimum enforced**: below it the block dims to `--ink-4`
  with the "Not enough to say yet" line and no percentage at all.
- Violations list cites each position `⟨field edu_links.evidence⟩` — a
  "violated" verdict a reader cannot check is an accusation, not a
  measurement. Every verdict cites its position; evidence visible, never
  behind a toggle.
- `edu_items` is empty today: one compact muted empty line naming the reason.

═══════════════════════════════════════════════════════════════════════════════
## 6 · MARKET — "what did they say about the market, and was it right?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/breadth`

**Deliberately quiet. No accent anywhere (§4.6).** Only `--up`/`--down` for
day colours. No `--risk`, no `--caution` (XP is fixed this wave; the §8 block
is removed — a stale disclaimer is its own kind of dishonesty).

```
┌── TODAY · 21 Aug 2026 ─────────────────────────────────────────────────────┐
│  Only a few stocks are pushing higher. Breakouts fail more often in a       │
│  market like this.  (hero value 7.7 · meaning · as of 2026-08-21)           │
│                                                                             │
│  r10  38 RED   r20  44 RED   r50  71 WHITE   r4.5 31 RED   MBI RED ⚠         │
├─────────────────────────────────────────────────────────────────────────────┤
│  DAY COLOUR · last 60 sessions   ▇▇▁▇▇▇▁▁▃▇▇▇▁▃▃▁▁▇▇▁▃▇▇▇▁▁▁▃▃▇  (inline │
│  SVG, one hard block per session)                            SVG ribbon)   │
│  ■ most stocks rose   ■ roughly even   ■ most fell   · = warning day        │
├─────────────────────────────────────────────────────────────────────────────┤
│  CUMULATIVE ADVANCE–DECLINE · advances − declines   (ECharts line)          │
│  ———— labelled axes + zero reference line; .chart-empty names the reason    │
├─────────────────────────────────────────────────────────────────────────────┤
│  date  trader        stance    XP/MBI that day   agreed?                    │
│  …     (stances table + agreement bars, n= always shown)                    │
│  It measures agreement with one particular breadth model — not whether      │
│  the trader was right.                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Hero `Stat` `⟨field breadth.today.xp_value, xp_band⟩` with its plain-English
  meaning (band gloss: LOW/BUILDING/STRONG/EXTREME sentences — LOW verbatim
  from the microcopy table) **and its age** (as of `trade_date`; stale ≥6 days
  adds "This reading is N days old — the market has moved since.").
- Four ratio tiles `⟨derive regime_daily.r10,r20,r50,r4p5⟩` with their bands
  (r50 uses its own 85/60 cutoffs) + MBI day colour/score + warning flag.
- **Day-colour ribbon** — inline SVG (no library), one hard block per session
  over the last 60 sessions `⟨field breadth.history[]⟩`; GREEN→`--up`,
  RED→`--down`, WHITE→`--ink-3`, none→`--ink-4`; warning dot on
  warning_day cells; **legend in words**: "■ most stocks rose · ■ roughly even
  · ■ most fell".
- **Cumulative advance–decline** — ECharts line (via the `BandLine` contract
  or screen-local equivalent) from `⟨NEW breadth.history[].advances/declines⟩`;
  labelled axis or reference line required; `.chart-empty` names the reason
  when the payload lacks the counts. Partial data says "counted X of Y
  sessions".
- Stances `⟨field breadth.stances[]⟩` beside that date's XP/MBI with the
  crude three-way `agreed?` match; agreement bars `⟨field breadth.agreement[]⟩`
  with `n=` always shown; neutral ink — an agreement rate is not good/bad.
- Protected footnote verbatim: "It measures agreement with one particular
  breadth model — **not** whether the trader was right."

**Payload reshapes** — `/api/breadth` history rows carry `advances`/`declines`
joined from `breadth_daily` on `trade_date` (additive; null when absent).

═══════════════════════════════════════════════════════════════════════════════
## 7 · SYMBOL — the landing page
═══════════════════════════════════════════════════════════════════════════════

consumes `⟨NEW /api/symbol/{symbol}⟩`

```
┌── RATEGAIN ────────────────────────────────────────────────────────────────┐
│  Last close ₹… — N sessions of NSE history, newest <date>.  (one-line     │
│  meaning; no bare number)                                                  │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │  lightweight-charts candles from daily_prices (bhavcopy)      │          │
│  │  ONLY when validated: rows exist for the symbol. Otherwise:  │          │
│  │  "This symbol has no price history on the NSE." /            │          │
│  │  "Nothing in the corpus for this symbol."                    │          │
│  └──────────────────────────────────────────────────────────────┘          │
│  POSITIONS for RATEGAIN (link → LEDGER)  ·  MENTIONS (verbatim, → TRADERS) │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Route `?tab=SYMBOL&symbol=X`, reached from Today glosses, Ideas mentions,
  Ledger rows, and the ⌘K palette.
- Candles `⟨field /api/symbol/{symbol}.prices[]⟩` — lightweight-charts, the
  ONLY place it is used (renderer ladder). A candle chart may only render bars
  that exist in `daily_prices` for a validated symbol; `validated` = rows
  present (bhavcopy is canonical NSE EQ). Either missing part names itself in
  the labelled empty state. Never a chart of an invalid instrument.
- Corpus context: positions for the symbol (LEDGER-style rows) and verbatim
  watch-idea mentions with handle + date.

---

## Not built, deliberately

- No search across all posts. Filters cover the known questions; full-text
  search is a W9+ addition once there is enough corpus to need it.
- No per-trader alerting configuration in the UI — Telegram routing is config,
  W7, and putting it on screen before it exists would be dormant UI.
- No editing of extracted data. If the reconciler is wrong, the fix is the
  prompt and the golden fixtures, not a hand-patched row that the next
  reconciliation silently overwrites.
- The Market `--caution` block (REDESIGN §8) is removed: XP was fixed in the
  2026-08-24 wave (C8: percent convention + observed-z reseed + 20-session
  warm-up). Re-add it only if the XP derivation regresses — a stale disclaimer
  is its own kind of dishonesty.