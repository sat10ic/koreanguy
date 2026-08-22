# WIREFRAMES — TraderLog

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

Aesthetic: editorial poster, not admin dashboard. Composed canvas per screen,
verdict first and numbers second, light theme, serif display for headline
values, mono for numerals only. Colour carries state — it is never decoration.

Six screens. Shell is a single tab strip; the active tab syncs to `?tab=`.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TRADERLOG    FEED   TRADERS   LEDGER   BREADTH   IDEAS   LIBRARY     ⓘ    │
│               ────                                                         │
│  ⚠ SHOWING MOCK DATA — no posts have been ingested yet   ⟨field is_mock⟩   │
└────────────────────────────────────────────────────────────────────────────┘
```

The mock-data banner is **mandatory** while `is_mock` is true on any payload.
A tool that looks real while showing invented data is the specific failure this
project is built to avoid.

═══════════════════════════════════════════════════════════════════════════════
## 1 · FEED — "what did the traders I follow just say, and what did it mean?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/feed` · `/api/review` · `POST /api/review/{id}`

```
┌── FILTERS ──────────────────────────────────────────────────────────────────┐
│  trader [ all ▾ ]   kind [ all ▾ ]   confidence [ ≥0.0 ▾ ]   [ unresolved ] │
└─────────────────────────────────────────────────────────────────────────────┘

┌── REVIEW QUEUE · 3 open ────────────────────────────────────────── [!] ─────┐
│  These could not be resolved automatically. One click each.                  │
│                                                                             │
│  @caveman_trades  "booked apollo, +18%"                       conf 0.62     │
│  → attach as EXIT ₹2,104 to APOLLOTYRE opened 04 Aug?                       │
│    why: same symbol, only open position, "booked" implies full exit         │
│    but: could be a new same-day trade                                       │
│                                        [ ✓ attach ]  [ ✗ no ]  [ open ↗ ]   │
└─────────────────────────────────────────────────────────────────────────────┘

┌── POSTS ────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  @manas_arora · 14:32 IST                    [TRADE EVENT]     conf 0.91    │
│  "added 25% more at 1847, sl trailed to 1790"                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ APOLLOTYRE   ADD ₹1,847  ·  25%      SL 1,740 → 1,790                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  🖼 chart attached — 2 levels read                    [ thread ]  [ why? ]  │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  @swing_ka_sultan · 09:12 IST                    [BREADTH]     conf 0.84    │
│  "internals soft, staying light until the 4% up count expands"              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ stance RISK-OFF          that day: XP 11.4 LOW · MBI RED · warning ⚠  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                              [ breadth ↗ ]  │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  @nitin_bhatia · 08:40 IST                       [DELETED 11:20]            │
│  "long KPITTECH above 1,610"                                                │
│  ⚠ this post was removed by its author. Kept on purpose.                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Filter row — `⟨field feed.filters⟩`. `unresolved` toggles to posts whose
  position has a non-empty `unresolved[]`.
- Review queue — `⟨field review[]⟩`. Shown **above** posts, always, when
  non-empty. It is work the human owes the tool, not a notification.
  - question `⟨field review[].question⟩`, `why:` `⟨field review[].reasoning⟩`,
    `but:` `⟨field review[].alternatives[]⟩`, conf `⟨field review[].confidence⟩`.
  - Both buttons `POST /api/review/{id}`. **Never a bulk "accept all"** — the
    floor exists because these are genuinely ambiguous.
- Post card — handle/time `⟨field feed[].handle, ts_ist⟩`, text
  `⟨field feed[].text⟩`, kind chip `⟨field feed[].kind⟩`, conf
  `⟨field feed[].confidence⟩`.
- Resolved strip (the inset box) — `⟨field feed[].event⟩`. Shows only fields the
  reconciler actually populated. **A field in `unresolved[]` renders as
  "not stated", never as a blank or a zero.**
- Stop moves render `old → new` `⟨field event.stop.moved_from⟩`.
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
┌── ROSTER ───────────────────────────────────────────────────────────────────┐
│  handle            tier   posts  open  closed   hold   win    preach        │
│  @manas_arora      CORE    412     4     183    11d    58%     74%   ›      │
│  @swing_ka_sultan  CORE    288     2      97     6d    51%     61%   ›      │
│  @nitin_bhatia     WATCH    94     1      22    19d    45%     —     ›      │
└─────────────────────────────────────────────────────────────────────────────┘

┌── @manas_arora ─────────────────────────────────────────────── CORE ────────┐
│                                                                             │
│         58%              1.9R             11d              74%              │
│    stated win rate    avg result     median hold    practices what          │
│      of 183 closed                                    they preach           │
│                                                                             │
│  ── STOP DISCIPLINE ──────────────────────────────────────────────────────  │
│  stop stated on   71% of positions   ████████████████░░░░░░░                │
│  stop honoured    62% of those       ██████████████░░░░░░░░░                │
│  the 9pt gap = stops quietly widened, not hit                               │
│                                                                             │
│  ── WHERE THEY PLAY ──────────────────────────────────────────────────────  │
│  CAPITAL GOODS ████████ 24%   AUTO ██████ 18%   PHARMA ████ 12%   +9 more   │
│                                                                             │
│  ── OPEN NOW · 4 ────────────────────────────────────────────────────────   │
│  APOLLOTYRE   in ₹1,792 + add ₹1,847   SL ₹1,790   19d                      │
│  KPITTECH     in ₹1,610                SL not stated   6d   ⚠               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Roster `⟨field traders[]⟩`; `preach` is `—` when there are no `edu_links` yet,
  never 0%.
- Four hero stats `⟨derive trader_style⟩` — `stated_win_rate`, `avg_r`,
  `median_hold_days`, `preach_score`. Serif, large. The qualifier under each
  ("of 183 closed") is **required**: a win rate over stated exits is not a win
  rate, and the label must not let a reader forget that.
- Stop discipline `⟨derive trader_style.stop_stated_pct, stop_honored_pct⟩`.
  The interpretive line beneath is the single most valuable thing on the screen —
  it is the leak the repo owner's own trade audit found, measured on somebody else.
- Sector tilt `⟨derive trader_style.sector_tilt_json⟩`.
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

┌── POSITIONS ────────────────────────────────────────────────────────────────┐
│ trader          symbol      entry    adds     stop    exit    net   days cf │
│ @manas_arora    APOLLOTYRE  1,792    1×1,847  1,790   —        —     19  ·91│
│ @manas_arora    DIXON       14,200   —        13,800  15,610 +9.9%   23  ·95│
│ @swing_ka_sultan KPITTECH   1,610    —        —       —        —      6  ·58│
│                                                          ⚠ no stop stated   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ ▼ DIXON · @manas_arora · closed +9.9%                                       │
│                                                                             │
│   01 Aug  ENTRY    ₹14,200            "starter, will add on strength"       │
│   01 Aug  SL SET   ₹13,800                                          ↗ post  │
│   09 Aug  SL MOVE  ₹13,800 → ₹14,450  "risk off the table"          ↗ post  │
│   24 Aug  EXIT     ₹15,610  100%      "booked, +9.9%"                ↗ post │
│                                                                             │
│   ┌─────────────────────┐  evidence                                         │
│   │  [chart image]      │  symbol        ← post 1953…                       │
│   │  annotated, 09 Aug  │  entries[0]    ← post 1953…                       │
│   └─────────────────────┘  stop.price    ← post 1955…                       │
│                            exits[0]      ← post 1962…                       │
│   unresolved: position size never stated                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Elements**

- Table `⟨field positions[]⟩`. `net` blank unless the trader stated a result or
  both prices — **never computed from market data**. This log records claims.
- `cf` is confidence, mono, two decimals, no percent sign.
- Row expands to the event timeline `⟨field positions[id].events[]⟩`, each line
  citing its post with a link out `⟨field position_events.post_id⟩`.
- Chart images `⟨field post_media.local_path⟩`, served by the API, never hotlinked
  to X.
- **Evidence block is not optional and not behind a toggle.** It is the reason
  this table can be trusted, and hiding it invites the reader to trust the
  numbers without it.
- `unresolved` line `⟨field positions.unresolved_json⟩`.

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
- XP trend — plain SVG line with the four band thresholds as background rects.
  No chart library.
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
## 5 · IDEAS — "what are they watching, and did it go anywhere?"
═══════════════════════════════════════════════════════════════════════════════

consumes `/api/ideas`

```
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
