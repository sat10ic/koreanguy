# WIREFRAMES — TraderLog

**Read `VISUAL_LANGUAGE.md` first.** It is the binding appearance and chart
vocabulary above this layout spec. A screen that satisfies the ASCII layout but
uses a banned form or misses a required visual-language rule is still defective.

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
`VISUAL_LANGUAGE.md`; this file does not override or abbreviate them.

Six product screens. Shell is a single tab strip; the active tab syncs to `?tab=`.
At 1920×1080 everything aligns to one centered 1680px grid (`VISUAL_LANGUAGE.md`
§1a). STYLE is a development reference screen: it is **not** in visible
navigation but remains reachable directly via `?tab=STYLE`.

```
┌───────────────────────────── 1680px centered ───────────────────────────────┐
│  TRADERLOG    FEED   TRADERS   LEDGER   BREADTH   IDEAS   LIBRARY           │
│               ────                                                           │
│  ⚠ SHOWING MOCK DATA — no posts have been ingested yet   ⟨field is_mock⟩    │
└─────────────────────────────────────────────────────────────────────────────┘
```

The mock-data banner is **mandatory** while `is_mock` is true on any payload.
A tool that looks real while showing invented data is the specific failure this
project is built to avoid.

═══════════════════════════════════════════════════════════════════════════════
## 1 · FEED — "what did the traders I follow just say, and what did it mean?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/feed` · `/api/review` · `POST /api/review/{id}` · `/api/traders`

**W3c evidence-desk composition (2026-08-23).** The 1680px grid is used as a
two-column workspace: the thread/feed workspace is primary (~1216px); filters
and compact operating context form a secondary rail (~420px) on the right.

```
┌── THREAD WORKSPACE · primary ────────────────────────┐ ┌── FILTERS ──────────┐
│                                                      │ │ trader [ all ▾ ]   │
│ ┌── REVIEW QUEUE · 1 open ─────────────────── [!] ┐  │ │ kind [ all ▾ ]     │
│ │ These could not be resolved automatically.      │  │ │ confidence [≥0.0▾] │
│ │ One click each.                                 │  │ │ [ unresolved ]     │
│ │ @caveman_trades "booked apollo, +18%"  conf 0.62│  │ └────────────────────┘
│ │ → attach as EXIT ₹2,104 to APOLLOTYRE 04 Aug?   │  │ ┌── TRADERS ON DESK ┐
│ │   why: only open position for the symbol        │  │ │ ⟨traders[]⟩        │
│ │   but: could be a new same-day trade            │  │ │ handle · tier ·    │
│ │                    [ ✓ attach ]  [ ✗ no ]       │  │ │ posts, per row     │
│ └─────────────────────────────────────────────────┘  │ └────────────────────┘
│                                                      │ ┌── DESK ────────────┐
│ ▍@manas_arora · 14:32 IST         [TRADE EVENT] 0.91 │ │ N posts · N        │
│ ▍"added 25% more at 1847, sl trailed to 1790"        │ │ threads · N events │
│ ▍┌────────────────────────────────────────────────┐  │ │ (counts of the     │
│ ▍│ APOLLOTYRE   ADD ₹1,847 · 25%   SL 1,740→1,790│  │ │ loaded feed page)  │
│ ▍└────────────────────────────────────────────────┘  │ └────────────────────┘
│ ▍🖼 chart attached — 2 levels read                   │
│ ▍            [ thread ↗ ]  [ why? ]  2 unresolved ▾  │
│ ▍@manas_arora · 14:40 IST · reply 2/4    conf 0.88   │
│ ▍"booked half"                                       │
│ ▍┌────────────────────────────────────────────────┐  │
│ ▍│ APOLLOTYRE   PARTIAL EXIT ₹1,910 · 50%         │  │
│ ▍└────────────────────────────────────────────────┘  │
│ ──────────────────────────────────────────────────── │
│ ▍@nitin_bhatia · 08:40 IST        [DELETED 11:20]    │
│ ▍"long KPITTECH above 1,610"                         │
│ ▍⚠ this post was removed by its author. Kept on      │
│ ▍purpose.                                            │
└──────────────────────────────────────────────────────┘
```

The `▍` spine on the left of the workspace is the **signature element**: a root
post and its self-replies read as one conversation object sharing a vertical
rule, not as separate cards. Prose keeps a readable measure (~60–66ch); event
strips, evidence lines, and meta run the full workspace width. Long unresolved
copy shows as a count (`2 unresolved ▾`) that expands the complete strings on
disclosure — never paraphrased, never dropped.

**Elements**

- Two-column composition — primary thread workspace + secondary rail. Rail
  panels: Filters (all existing controls), Traders on desk
  `⟨field traders[]: handle, tier, posts⟩` (already-fetched `/api/traders`
  roster), Desk (counts computed client-side over the loaded `/api/feed` page —
  posts, threads, trade events; no new payload fields).
- Filter panel — `⟨field feed.filters⟩`. `unresolved` toggles to posts whose
  position has a non-empty `unresolved[]`. Unchanged set of filters.
- Review queue — `⟨field review[]⟩`. Shown **above posts in the primary
  workspace**, always, when non-empty. It is work the human owes the tool, not a
  notification.
  - question `⟨field review[].question⟩`, `why:` `⟨field review[].reasoning⟩`,
    `but:` `⟨field review[].alternatives[]⟩`, conf `⟨field review[].confidence⟩`.
  - Both buttons `POST /api/review/{id}`. **Never a bulk "accept all"** — the
    floor exists because these are genuinely ambiguous.
- Post card — handle/time `⟨field feed[].handle, ts_ist⟩`, text
  `⟨field feed[].text⟩`, kind chip `⟨field feed[].kind⟩`, conf
  `⟨field feed[].confidence⟩`, thread position `⟨field feed[].thread_pos,
  thread_size⟩` for replies.
- Resolved strip (the inset box) — `⟨field feed[].event⟩`. Shows only fields the
  reconciler actually populated. **A field in `unresolved[]` renders as
  "not stated", never as a blank or a zero.** The strip runs the full workspace
  width.
- Stop moves render `old → new` `⟨field event.stop.moved_from⟩`.
- Unresolved summary — `N unresolved ▾` `⟨field event.unresolved[]⟩`; disclosure
  expands the complete strings inline. The count may not paraphrase or truncate
  the evidence.
- Breadth card strip — stance `⟨field feed[].stance⟩` beside that day's
  `⟨derive regime_daily⟩` XP band and MBI colour. This juxtaposition is the whole
  point: a claim next to the measurement.
- `[ why? ]` opens the evidence map — every field with the post that justifies it
  `⟨field feed[].evidence⟩`.
- Deleted posts — `⟨field feed[].deleted_at⟩`. Dimmed, struck, **still listed**,
  with the line about being kept on purpose. Traders delete losers.
- 🖼 badge — `⟨field feed[].media_count⟩` + count of `annotated_levels`
  `⟨field post_media.vision_json⟩`.

**Payload reshapes**

| Endpoint | Field | Source |
|---|---|---|
| `/api/feed` | `event` | join `position_events` on `post_id` |
| `/api/feed` | `stance` | `breadth_notes.stance` |
| `/api/feed` | `regime` | `regime_daily` on the post's trade date |
| `/api/review` | `alternatives[]` | `review_queue.proposed_json.alternatives` |

═══════════════════════════════════════════════════════════════════════════════
## 2 · TRADERS — "how does this person actually trade, and do they mean it?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/traders` · `/api/traders/{handle}`

```
┌── ROSTER ───────────────────────────── small multiples, shared scale ───────┐
│  @manas_arora     @swing_ka_sultan   @nitin_bhatia     @ipo_base            │
│  ▁▂▅▇▆▃▂▁         ▁▁▃▄▆▇▇▅           ▂▃▂▁▁▂▃▂          ▁▁▁▂▁▁▁▁             │
│  CORE · 412 posts CORE · 288         WATCH · 94        WATCH · 2            │
│  4 open · 183 cl  2 open · 97        1 open · 22       0 open · 0           │
│                                                                             │
│  handle            tier  posts  open  closed  hold▲  win   preach           │
│  @manas_arora      CORE   412     4     183    11d   58%    74%      ▸      │
│  @swing_ka_sultan  CORE   288     2      97     6d   51%    61%      ▸      │
│  @nitin_bhatia     WATCH   94     1      22    19d   45%     —       ▸      │
└─────────────────────────────────────────────────────────────────────────────┘

┌── @manas_arora ─────────────────────────────────────────────── CORE ────────┐
│                                                                             │
│      58%          ── the one serif number on this screen ──                 │
│  stated win rate                                                            │
│    of 183 closed     avg 1.9R · median hold 11d · preach 74% (n=29)         │
│                                                                             │
│  ── STOP DISCIPLINE ─────────────────────────── the gap IS the finding ───  │
│                                                                             │
│   honoured ○━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━● stated            │
│           62%                                          71%                  │
│           ▲ 9pt gap — stops quietly widened, not hit                        │
│   0        25         50         75        100                              │
│                                                                             │
│  ── HOLD TIME · n=183 ───────────────────────────────────────────────────   │
│   ┃ ┃┃┃  ┃ ┃┃ ┃    ┃  ┃          ┃        ┃                                 │
│   0     5    10   15   20   25   30      45  days                           │
│              ▲ median 11        ← two clusters: 3-day flips, 20-day swings  │
│                                                                             │
│  ── HOW THEY ENTER ──────────────────────────────────────────────────────   │
│   ███████████████ breakout 61  ░░░░░░ pullback 24  ▒▒▒▒ ep 15               │
│                                                                             │
│  ── WHERE THEY PLAY ─────────────────────────────────────────────────────   │
│   ████████ CAP GOODS 24  █████ AUTO 18  ███ PHARMA 12  ██ IT 9  ░ +9 more   │
│                                                                             │
│  ── OPEN NOW · 4 ────────────────────────────────────────────────────────   │
│  APOLLOTYRE   in ₹1,792 + add ₹1,847   SL ₹1,790   19d                      │
│  KPITTECH     in ₹1,610                SL not stated   6d   ⚠               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- **Roster small multiples** `⟨NEW derive/style.py⟩` — one miniature per trader on
  a **shared scale**, above the table. Do not replace with one combined chart;
  the comparison across traders is the whole value. Renders its empty frame until
  W6 computes the series.
- Roster table `⟨field traders[]⟩`; `preach` is `—` when there are no `edu_links`
  yet, never 0%. Headers are `SortableTh`.
- Hero stats `⟨derive trader_style⟩`. **Exactly one uses the serif display face**
  (`stated_win_rate`); the rest are set inline as a supporting line.
  Four serif hero numbers is the KPI-card tell wearing a different hat, and
  `VISUAL_LANGUAGE.md` §4 forbids it. The qualifier under the serif number
  ("of 183 closed") is **required**: a win rate over stated exits is not a win
  rate, and the label must not let a reader forget it.
- **Stop discipline: `Dumbbell`** `⟨derive trader_style.stop_stated_pct,
  stop_honored_pct⟩`. Two bars force the reader to do the subtraction; a dumbbell
  makes **the gap** the most visible thing on the row, and the gap is the finding.
  The interpretive line beneath is the single most valuable sentence on the
  screen — it is the leak the repo owner's own trade audit found, measured on
  somebody else.
- **Hold time: `StripPlot`** `⟨NEW derive/style.py hold_days[]⟩`. Replaces the
  bare median scalar. A trader who flips in three days *or* holds three weeks and
  nothing between is invisible in a median and obvious in a strip plot. `n` shown.
- **Entry mix: `StackedStrip`** `⟨field post_class.play_type⟩` — one bar, labelled
  in place. Not a pie, not a donut.
- **Sector tilt: `StackedStrip`** `⟨derive trader_style.sector_tilt_json⟩`.
- Open positions `⟨field positions where status != closed⟩`. `SL not stated`
  `⟨field positions.unresolved_json⟩` with a ⚠. **Never render a stop that was
  not stated.**

**Payload reshapes**

| Endpoint | Field | Source |
|---|---|---|
| `/api/traders` | `preach_score` | `trader_style.preach_score`, null-safe |
| `/api/traders/{h}` | `open[]` | `positions` + latest `position_events` |

═══════════════════════════════════════════════════════════════════════════════
## 3 · LEDGER — "every trade we reconstructed, and the receipts"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/positions` · `/api/positions/{id}`

```
┌── FILTERS ──────────────────────────────────────────────────────────────────┐
│  trader [ all ▾ ]  status [ all ▾ ]  symbol [____]  conf [ ≥0.0 ▾ ]         │
└─────────────────────────────────────────────────────────────────────────────┘

┌── WHEN THEY WERE IN ────────────── lead graphic · shared time axis ─────────┐
│         Jul 20         Aug 01         Aug 15         Aug 22                 │
│         │              │              │              │                      │
│ DIXON   ●━━━━━━━━━━━━━━▲━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━○          +9.9%      │
│ BEL     ●━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━○          +8.7%      │
│ APOLLO       ●━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━▶         open       │
│ KPITTECH              ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶         open ⚠     │
│ CUMMINS ●━━━━━━━━━━━━━○                                          −3.7%      │
│                                                                             │
│  ● entry   ● add   ▲ stop raised   ○ exit   ▶ still open                    │
│  A shared axis is the point: two traders entering the same week is visible   │
│  here and invisible in a table sorted by symbol.                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌── POSITIONS ────────────────────────────────────────────────────────────────┐
│   trader          symbol      entry    adds     stop    exit   net▼ days cf │
│ ▸ @manas_arora    APOLLOTYRE  1,792    1×1,847  1,790   —        —    19 ·91│
│ ▸ @manas_arora    DIXON       14,200   —        13,800  15,610 +9.9%  23 ·95│
│ ▸ @swing_ka_sultan KPITTECH   1,610    —        —       —        —     6 ·58│
│                                                          ⚠ 2 unresolved     │
│ ─────────────────────────────────────────────────────────────────────────── │
│ ▾ DIXON · @manas_arora · closed +9.9%                                       │
│                                                                             │
│   01 Aug  ENTRY    ₹14,200            "starter, will add on strength"       │
│   01 Aug  SL SET   ₹13,800                                          ↗ post  │
│   09 Aug  SL MOVE  ₹13,800 → ₹14,450  "risk off the table"          ↗ post  │
│   24 Aug  EXIT     ₹15,610  100%      "booked, +9.9%"                ↗ post │
│                                                                             │
│   ┌─────────────────────┐  evidence                                         │
│   │  [chart image]      │  symbol        ← post 1953…                       │
│   │  contained, ≤ col   │  entries[0]    ← post 1953…                       │
│   │  width              │  stop.price    ← post 1955…                       │
│   └─────────────────────┘  exits[0]      ← post 1962…                       │
│   unresolved: position size never stated                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**W3c containment rules (2026-08-23).** The collapsed table compresses
`unresolved` to a truthful count — `⚠ 2 unresolved` — with the complete strings
shown in the expanded detail. The expanded detail is a robust two-column grid:
the event/citation timeline is primary (`min-width: 0` on the shrinkable track)
and the media/evidence column is a predictable ~460px. Every archived image
obeys its container (`display:block; width:100%; max-width:100%; height:auto;
object-fit:contain`); intrinsic image dimensions must never enlarge the grid,
panel, or document. Evidence is visible on expansion, never behind a further
toggle.

**Scale lenses (2026-08-25, owner-approved amendment).** At corpus scale the
shared axis renders a *scoped slice*, never the full inventory unfiltered:

- **Status lens** — `OPEN · CLOSED · ALL` segmented control above the axis.
  Default `OPEN`: every still-open position plus closes from the last 90 days.
  The one-lane-per-position rule holds *within the visible slice*.
- **Window lens** — `30D · 90D · 1Y · ALL` control narrowing the time domain
  itself; lanes render only for positions overlapping the window.
- Both lenses re-scope everything downstream: lane set, outcome column, the
  overlap sentence (computed over visible rows only), and the table's default
  filter state. Explicit trader/symbol/confidence filters stack on top. The
  table beneath keeps full-history capability — the lenses scope the default
  *presentation*, not the data available. The signature element survives:
  clustering in time remains visible inside any scope.

**Detail analytics (2026-08-25 amendment).** Three cited-data additions to the
expanded detail / axis panel: (1) **R-multiple badge** when entry+stop+exit are
all stated — R = (exit−entry)/(entry−stop), long convention, last-exit
tranche, matching `derive/style.py`'s avg_r; absent when any is unstated.
(2) **"Market then" line** — the XP value/band from `regime_daily` on or before
the entry date (nearest prior session, never future). (3) **Regime split strip**
above the axis — entries-per-band counts over VISIBLE lens-scoped rows; hidden
when no breadth history exists; unstated-regime positions counted nowhere.

**Elements**

- **Lead graphic: `PositionBars`** `⟨field positions[]⟩` + `⟨field positions[id].events[]⟩`.
  Every row on one shared time domain. This is the screen's reason to exist as a
  screen rather than a report: **clustering in time is the finding**, and a table
  sorted by symbol destroys it. Bar colour from `net_result_pct` — green, red, or
  `ink-mute` when open or unstated. Never a gradient along the bar.
  Rows with `unresolved` containing a stop get the ⚠ suffix.
- Table `⟨field positions[]⟩`. `net` blank unless the trader stated a result or
  both prices — **never computed from market data**. This log records claims.
- `cf` is confidence, mono, two decimals, no percent sign.
- Column headers are `SortableTh`. Sorting is the primary interaction on a dense
  table and its absence was a defect in the first build.
- Row expands via a `Disclosure` caret `⟨control⟩` — **not a bare whole-row
  click**, which gives the reader no affordance and was flagged in review.
  Expands to the event timeline `⟨field positions[id].events[]⟩`, each line
  citing its post with a link out `⟨field position_events.post_id⟩`.
- Unresolved indicator — `⚠ N unresolved` count under the row
  `⟨field positions.unresolved_json⟩`; the complete strings render only in the
  expanded detail. Never paraphrased.
- Chart images `⟨field post_media.local_path⟩`, served by the API, never hotlinked
  to X, contained per the W3c rules above.
- **Evidence block is not optional and not behind a toggle.** It is the reason
  this table can be trusted, and hiding it invites the reader to trust the
  numbers without it.
- `unresolved` line in expanded detail `⟨field positions.unresolved_json⟩`.

═══════════════════════════════════════════════════════════════════════════════
## 4 · BREADTH — "what did they say about the market, and were they right?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/breadth`

```
┌── TODAY · 22 Aug 2026 ──────────────────────────────────────────────────────┐
│                                                                             │
│      XP  11.4                    MBI  RED                    ⚠ WARNING DAY  │
│      LOW                         3 of 4 bands red                           │
│      ░░░░▓▓▓▓░░░░░░░░░░  low│building│strong│extreme                        │
│                                                                             │
│   r10  38  RED    r20  44  RED    r50  71  WHITE    r4.5  31  RED           │
└─────────────────────────────────────────────────────────────────────────────┘

┌── MBI DAY COLOUR · last 60 sessions ────────────────────────────────────────┐
│  ▇▇▁▇▇▇▁▁▃▇▇▇▁▃▃▁▁▇▇▁▃▇▇▇▇▁▁▁▃▃▇▁▁▃▃▃▁▇▇▇▁▁▃▃▁▁▇▇▇▁▃▁▁▃▃▁▁▁▃              │
│  green            white             red            ⚠ = warning day          │
└─────────────────────────────────────────────────────────────────────────────┘

┌── XP TREND · 90d ───────────────────────────────────────────────────────────┐
│  100 ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ strong             │
│   40 ┄┄┄┄┄┄┄┄┄┄╱╲┄┄┄┄┄┄┄┄┄┄┄┄╱╲┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ building           │
│   15 ┄┄┄╱╲┄┄┄╱┄┄┄╲┄┄╱╲┄┄┄┄┄╱┄┄┄╲┄┄┄┄┄╱╲┄┄┄┄┄┄┄╲┄┄┄┄┄●┄┄ low                │
└─────────────────────────────────────────────────────────────────────────────┘

┌── WHAT TRADERS SAID ────────────────────────────────────────────────────────┐
│  date    trader             stance     XP/MBI that day        agreed?       │
│  22 Aug  @swing_ka_sultan   RISK-OFF   11.4 LOW · RED            ✓          │
│  22 Aug  @nitin_bhatia      RISK-ON    11.4 LOW · RED            ✗          │
│  21 Aug  @manas_arora       NEUTRAL    13.1 LOW · WHITE          ✓          │
│                                                                             │
│  ── AGREEMENT · last 90d ─────────────────────────────────────────────────  │
│  @swing_ka_sultan  ██████████████████░░  81%   n=64                         │
│  @manas_arora      ███████████████░░░░░  72%   n=58                         │
│  @nitin_bhatia     ██████████░░░░░░░░░░  49%   n=41                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- XP dial `⟨derive regime_daily.xp_value, xp_band⟩`
  `⟨cite finallynitin XP recursion, adopted manas_os/regime/xp.py⟩`.
  Band cutoffs 15 / 40 / 100 come from the adopted module — do not re-invent them.
- MBI block `⟨derive regime_daily.mbi_day_color, mbi_score, warning_day⟩`
  `⟨cite Stocksgeeks MBI, manas_os/design/knowledge/SG_MBI_DIGEST.md⟩`.
  Warning day = ≥3 red bands.
- Four ratio tiles `⟨derive regime_daily.r10, r20, r50, r4p5⟩` with their bands.
  r50 uses its own 85/60 cutoffs, not the 75/50 the others use.
- Day-colour ribbon — one cell per session, 60 sessions
  `⟨derive regime_daily history⟩`. Regime persistence and turns at a glance.
- XP trend — Vega-Lite layered line with the four band thresholds as flat
  background rects, rendered behind the stable `BandLine` wrapper contract.
- Stance table `⟨field breadth_notes.stance⟩` beside that date's XP/MBI.
  `agreed?` is `⟨NEW derive/breadth_overlay.py⟩`: RISK-ON vs GREEN, RISK-OFF vs
  RED, NEUTRAL vs WHITE. A three-way match, not a score — deliberately crude,
  and the crudeness is stated on screen.
- Agreement bars `⟨NEW derive/breadth_overlay.py⟩`, with `n=` always shown.
  **A percentage without its n is a defect on this screen.**

**`Unverified:` whether XP/MBI agreement is a fair scoring of a trader's read.**
It measures agreement with one particular breadth model, not correctness. The
screen must say so in a footnote rather than implying a trader is wrong.

**Payload reshapes**

| Endpoint | Field | Source |
|---|---|---|
| `/api/breadth` | `regime_history[]` | `regime_daily` last 90 rows |
| `/api/breadth` | `stances[]` | `breadth_notes` joined to `regime_daily` on date |
| `/api/breadth` | `agreement[]` | `NEW` — `derive/breadth_overlay.py` |

═══════════════════════════════════════════════════════════════════════════════
## 5 · RADAR — "where is independent trader attention converging?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/radar` now; `/api/ideas` and `/api/positions` remain legacy until
the later Themes and reconciled-position modes replace them.

**INS-1 binding replacement (2026-08-25):** the original Ideas wireframe below
is retained only as migration history. INS-1 replaces its ticker leaderboard and
post-centric groups with a symbol-first co-attention workspace:

- Header controls: 7 / 30 / 90-day IST-calendar corpus window and minimum
  distinct traders.
- Left: one ranked row per NSE-validated symbol. Columns are symbol, strongest
  rolling seven-calendar-day cluster (distinct traders), total distinct traders,
  total mentions, and last mention. No composite score.
- INS-2 (2026-08-27, additive): a sixth "Close return after anchor open"
  column per ranked row — the anchor date and its open, then forward CLOSE
  returns at 1 / 5 / 10 / 20 trading sessions of the symbol's own series
  (`derive/tape.py`: pre-open, strictly < 09:00 IST, on a session day anchors
  that day's open; every other post anchors the next available session; a
  horizon with no session is an em dash, never zero), with eligible/missing
  counts alongside. No win/loss colouring or direction verdict anywhere — the
  signed value is the raw return. A symbol whose price/mention alignment is
  unavailable shows one muted line ("no NSE price history", "no session after
  mention", "mention timestamp unavailable") instead of percentages.
- Right: the selected symbol's evidence rail in chronological order: handle,
  timestamp, classifier kind/confidence, exact post text, and source link.
- Cluster start/end and distinct-trader count are stated in words. The rail is
  the visual signature; do not add a decorative chart to satisfy a chart quota.
- Coverage footer: eligible classified posts, included mentions, invalid symbol
  JSON, and unvalidated mentions/symbols. Missing and invalid data are visible.
- The words `consensus`, `hot`, `correct`, `win`, and `accuracy` do not describe
  this screen. Multiple bare mentions prove co-attention only.
- Selecting a row works by mouse and keyboard; its symbol links to the existing
  symbol/ledger drill-down. Empty data is one compact explanatory block.
- Acceptance viewport is 1920×1080 only: centered 1680px grid, no document or
  panel overflow, no console errors, and no failed requests.

The Themes portion returns in INS-3 only after cited materialization is repaired;
the Setup mode returns in INS-4 only after explicit `play_type` coverage passes.
Until then they are not rendered as empty future panels.

```
┌── TICKER LEADERBOARD ───────────────────────────────────────────────────────┐
│  ticker      entered  holding  exited  mentioned                            │
│  FCL             2        2      0       0                                   │
│  RATEGAIN        1        1      0       0                                   │
│  KPITTECH        1        1      0       2                                   │
└──────────────────────────────────────────────────────────────────────────────┘

┌── BY SYMBOL ────────────────────────────────────────────────────────────────┐
│                                                                             │
│  KPITTECH                                        3 traders · first 04 Aug   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ @manas_arora    04 Aug  WATCH  "above 1,610 on volume"                │  │
│  │ @nitin_bhatia   06 Aug  WATCH  "1,600 is the line"                    │  │
│  │ @caveman_trades 11 Aug  EP     "post-results gap, watching the base"  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  → @nitin_bhatia took it 12 Aug at ₹1,610                                   │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ZAGGLE                                          1 trader · first 19 Aug    │
│  │ @caveman_trades 19 Aug  IPO    "IPO base forming, not yet"             │  │
│  → nobody has taken it                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌── THEMES ───────────────────────────────────────────────────────────────────┐
│  DEFENCE       ████████  12 mentions   4 symbols   last 21 Aug              │
│  POWER ANCILL  █████      7 mentions   6 symbols   last 20 Aug              │
│  QUICK COMM    ███        4 mentions   3 symbols   last 14 Aug              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- **Ticker leaderboard** `⟨derive client-side⟩` — one compact row per symbol
  at the top of IDEAS, derived from `/api/positions` + `/api/ideas` with no
  payload change. `entered` = distinct traders with any position for the
  symbol `⟨field positions[].handle⟩`; `holding` = distinct traders whose
  position is `open`/`partial` `⟨field positions[].status⟩`; `exited` =
  distinct traders whose position is `closed` `⟨field positions[].status⟩`;
  `mentioned` = distinct mentioners
  `⟨field ideas[].mentions[].handle⟩` **minus** anyone already counted as
  entered — rendered muted, never reads as a position. Rows sorted by entered
  desc, holding desc, symbol asc; only symbols with ≥1 position or ≥1 mention
  render. Row (or ticker cell) tap prefilters LEDGER `⟨control⟩`. With no
  positions and no mentions, one compact explanatory line replaces the table.
- Grouped by symbol `⟨field ideas[]⟩`, ordered by trader count then recency.
  Grouping by symbol rather than by trader is what turns scattered mentions into
  a signal: three people naming the same stock in a week is the finding.
- Each mention: handle, date, kind chip (`WATCH`/`EP`/`IPO`/`THEME`), and the
  trigger **in their own words** `⟨field watch_ideas.trigger_text⟩`.
  Quote, never paraphrase — the exact phrasing is the content.
- Follow-through line `⟨NEW⟩` — joins `watch_ideas` to `positions` on
  (symbol, later date). Says plainly when nobody acted.
- Themes `⟨field themes[]⟩`.

**Not on this screen:** whether the stock actually moved. That needs price data
(W4) and, more importantly, it is a different claim — this screen reports what
was said and who acted, not who was right.

═══════════════════════════════════════════════════════════════════════════════
## 6 · LIBRARY — "what do they teach, and do they follow it?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/library`

```
┌── BY TOPIC ─────────────────────────────────────────────────────────────────┐
│  [ stops ] [ sizing ] [ entries ] [ exits ] [ psychology ] [ breadth ]       │
└─────────────────────────────────────────────────────────────────────────────┘

┌── STOPS · 14 items ─────────────────────────────────────────────────────────┐
│                                                                             │
│  @manas_arora · 12 Jul                                                      │
│  "the stop goes where the idea is wrong, not where your loss feels big"     │
│                                                              ↗ post          │
│  ┌── practised? ────────────────────────────────────────────────────────┐   │
│  │  followed  18   violated  7   n/a  4                                  │   │
│  │  ██████████████████░░░░░░░                            72%             │   │
│  │  violations: DIXON 09 Aug (widened), TATAELXSI 22 Jul (widened) …     │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  @swing_ka_sultan · 03 Aug                                                  │
│  "no add unless the first tranche is already paying you"                    │
│  ┌── practised? ────────────────────────────────────────────────────────┐   │
│  │  not enough linked trades yet — 2 of a 10-trade minimum                │   │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Topic tabs `⟨field library.topics[]⟩` from `edu_items.topic_tags`.
- Principle text `⟨field edu_items.principle_text⟩` — **verbatim, quoted.**
  Paraphrase drift corrupts the very thing being measured.
- Practised block `⟨derive edu_links⟩` — followed / violated / n/a counts and
  the percentage.
- **The 10-trade minimum is required.** Below it, show the "not enough linked
  trades" line and no percentage at all. A preach score computed on two trades is
  worse than no score, because it looks like a finding.
- Violations list the specific positions `⟨field edu_links.evidence⟩` — a
  "violated" verdict a reader cannot check is an accusation, not a measurement.

**`Assumption:` topic-tag matching is good enough to link a principle to a trade.**
It will produce false links. That is why every verdict cites its positions and
why the minimum-n rule exists. If precision proves poor in W6, the fallback is
human confirmation through `review_queue` rather than a cleverer matcher.

---

## Not built, deliberately

- No search across all posts. Filters cover the known questions; full-text search
  is a W9+ addition once there is enough corpus to need it.
- No per-trader alerting configuration in the UI — Telegram routing is config,
  W7, and putting it on screen before it exists would be dormant UI.
- No editing of extracted data. If the reconciler is wrong, the fix is the
  prompt and the golden fixtures, not a hand-patched row that the next
  reconciliation silently overwrites.
