<!-- SUPERSEDED 2026-08-29 (unidesk DECISIONS D13): this document is retained as
     historical reference for the companion product manual of the LIVE-FIRST architecture. The controlling
     documents are now UNIFIED_DESK_BUILD_MANUAL_V2.md / UNIFIED_DESK_UI_UX_MANUAL_V2.md
     (EOD-first product). Unchanged details referenced by V2 remain valid; live-module
     sections apply only if the optional live module is activated. -->

<!-- In-repo adoption note (2026-08-28) — added when this manual was copied into the repo.
Companion product/UI manual to plan/UNIFIED_DESK_BUILD_MANUAL.md, adopted per
unidesk/DECISIONS.md D1. Precedence rule stands as §0.1 states: data truth and
calculation logic come from the build manual; if UI wording risks
misrepresenting data, the build manual wins and the wording changes.
Repo mapping: `desk/` in the layout = `unidesk/` (D2). UI implementation is a
later phase; nothing here authorizes building UI before Phase 3 data exists. -->

# Unified Momentum Trading Desk — UI / UX Product Manual

**Status:** SUPERSEDED 2026-08-29 (D13). Historical live-first UI spec. Controlling UI spec is `plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md`.  
**Created:** 2026-08-28  
**Scope:** product vision + navigation + screen-by-screen UX + widget library + visual language + interaction rules  
**Relationship to the core build manual:** this manual sits **on top of and separate from** `UNIFIED_MOMENTUM_TRADING_DESK_BUILD_MANUAL.md`

---

# 0. How this manual relates to the previous build manual

Yes — this manual is intentionally **separate from** the previous build manual.

Use the two manuals like this:

```text
BUILD MANUAL
────────────────────────────────────
brain / data / contracts / logic /
research / scoring / validation

UI / UX PRODUCT MANUAL
────────────────────────────────────
face / interaction / navigation /
visual language / charts / workflows /
beginner-friendly presentation
```

The previous build manual answers:

```text
what the system computes
how modules connect
what data is stored
what rules are allowed
how validation works
```

This manual answers:

```text
what the product feels like
what tabs it has
how a beginner navigates it
what charts appear
how the information is visualized
what gets emphasized vs hidden
how to avoid a text-heavy terminal
```

## 0.1 Precedence

If the two manuals ever conflict:

1. **Data truth and calculation logic** come from the core build manual.
2. **Presentation, navigation and visual behavior** come from this manual.
3. If wording in the UI risks misrepresenting the underlying data, the build manual wins and the UI wording must be changed.

Example:

```text
If the UI wants to label something as "Strong institutional buying"
but the build manual forbids such a claim,
the UI must step back to:
"Strong buying pressure" or "Buyer aggression estimate".
```

---

# 1. Product intent

This is not meant to look like:

- a crowded broker terminal,
- a generic AI dashboard,
- a wall of tables and KPI cards,
- a “quant cosplay” interface,
- a text-heavy assistant with charts glued around it.

It should feel like:

```text
part premium trading cockpit
part visual scanner
part game-like tactical dashboard
part clean research workstation
```

The product must be:

- visually exciting,
- quick to scan,
- beginner-friendly,
- low on jargon on the surface,
- graph-first and text-second,
- premium and modern,
- cool without becoming tacky,
- informative without looking like “AI slop”.

---

# 2. Product design principles

## P1 — Visual first, explanation second

The first thing a user should understand on any screen must come from:

```text
color
shape
position
motion
chart structure
```

The second thing can come from text.

If a panel requires three paragraphs to explain itself, the panel is badly designed.

---

## P2 — One core question per panel

Every card or panel should answer one question clearly.

Examples:

```text
"Is the stock strong?"
"How close is the trigger?"
"Is the entry clean?"
"Is live flow confirming?"
"How much room remains?"
"What are traders doing?"
```

Not:

```text
"Here is a random pile of related metrics."
```

---

## P3 — Beginner surface, expert depth

Default experience should be understandable by a motivated beginner.

Advanced detail should be available on:

```text
expand
hover
tap
secondary panel
advanced mode
```

The product should not greet a new user with:

```text
AVWAP | VDU | MFE | MAE | weighted imbalance | absorption | breadth percentile
```

Instead it should greet them with:

```text
Trend
Leadership
Participation
Entry timing
Room to move
Live breakout health
Exit risk
```

and allow expansion into the advanced terminology.

---

## P4 — Show the decision path, not just the score

The product should visually communicate:

```text
Strong stock
    ↓
Valid setup
    ↓
Good / bad current entry
    ↓
Tradable / not tradable
    ↓
Flow confirming / warning
    ↓
Final policy state
```

Users should see how the conclusion was formed.

---

## P5 — Avoid decoration without function

Visual flair is welcome only if it supports:

- scan speed,
- emotional clarity,
- premium feel,
- focus.

Avoid:

- meaningless 3D blobs,
- random gradients,
- empty futuristic frames,
- too many glowing outlines,
- cluttered neon chrome.

---

## P6 — Motion should signal state change

Animation exists to reveal:

- state shifts,
- alerts,
- transition,
- trigger proximity,
- worsening risk,
- improving confirmation.

Animation is not a substitute for information.

---

## P7 — Text density must stay low

Panels should prefer:

```text
bars
meters
sparklines
heatmaps
bands
ladders
timelines
badges
mini-diagrams
```

over:

```text
dense paragraphs
multiple stacked bullet lists
technical prose
audit-like language
```

---

# 3. User types and experience modes

The product should support two visible modes.

## 3.1 Beginner Mode

Purpose:

- understand opportunities fast,
- avoid jargon overload,
- focus on “what matters now”.

Characteristics:

- plain-English labels,
- more visual hints,
- fewer raw metrics,
- a built-in “What this means” strip,
- color-supported reading,
- guided drill-down flow.

Examples:

| Internal concept | Beginner label |
|---|---|
| Stock Quality | Stock Strength |
| Setup Quality | Setup Quality |
| Entry Quality | Entry Timing |
| AVWAP | Key Cost Zone |
| Breakout Room | Room To Move |
| Flow State | Live Breakout Health |
| Liquidity State | Tradeability |
| Circuit Risk | Exit Risk |
| Social Context | What Traders Are Saying |

---

## 3.2 Pro Mode

Purpose:

- show exact labels and deeper context,
- expose more calculations and history,
- reduce hand-holding.

Characteristics:

- keeps the same screen structure,
- reveals more rows in panels,
- exposes source terms,
- allows multi-window flow views,
- shows more feature breakdown.

Important rule:

```text
Beginner and Pro modes must share the same product structure.
Do not build two different apps.
```

---

# 4. Core information architecture

Top-level navigation should be simple and memorable.

## 4.1 Recommended main navigation

```text
HOME
MARKET
SETUPS
WATCHLIST
STOCK
FLOW
TRADERS
JOURNAL
LAB
SETTINGS
```

### Navigation purpose

- **Home** — “What deserves attention right now?”
- **Market** — overall market, sectors, themes, breadth, leadership.
- **Setups** — all candidates ranked/filterable by quality and timing.
- **Watchlist** — user-tracked names and alert states.
- **Stock** — deep-dive workspace for one selected symbol.
- **Flow** — live trigger-zone and liquidity/flow workspace.
- **Traders** — social context, accepted claims, trader activity.
- **Journal** — trade review and discipline later phase.
- **Lab** — research, replay, backtesting, feature validation.
- **Settings** — mode, thresholds, alert preferences, data status.

This structure gives a clean mental model:

```text
Market
  → Opportunities
      → One stock
          → Live flow
              → Extra context
                  → Research / review
```

---

## 4.2 Navigation shell

Use a three-part shell:

```text
LEFT RAIL     = primary navigation
TOP BAR       = global search, mode toggle, alerts, connection status
MAIN CANVAS   = active workspace
RIGHT RAIL    = contextual detail drawer (optional/collapsible)
```

### Left rail

Fixed icons + text label, clean and memorable.

### Top bar

Should include:

- global symbol search,
- Beginner / Pro toggle,
- data feed status,
- alert bell,
- workspace breadcrumbs,
- quick command launcher.

### Right rail

Use for:

- quick glossary/help,
- evidence drawer,
- selected point detail,
- “why this matters” text,
- advanced metrics when expanded.

---

# 5. Visual style direction

## 5.1 Overall style

Recommended direction:

```text
Dark premium trading cockpit
with controlled neon accenting
and clean card geometry
```

Mood reference:

```text
Figma polish
+ motorsport dashboard focus
+ modern gaming HUD restraint
+ premium fintech cleanliness
```

Not:

```text
cyberpunk mess
or
broker spreadsheet
```

---

## 5.2 Color philosophy

Use a primarily dark canvas so charts and signals pop.

Functional color families:

- **positive / healthy / confirming**
- **warning / mixed / caution**
- **negative / veto / danger**
- **neutral / inactive / unknown**
- **accent / interactive / selected**
- **market / sector / setup category tagging**

Use color consistently across charts, cards and badges.

### Important rule

Do **not** rely on color alone.

Also use:

- icon,
- text,
- line style,
- shape,
- fill,
- pulse/animation.

---

## 5.3 Card shape and composition

Cards should feel premium and slightly tactical:

- medium radius, not bubbly,
- clean borders or soft separation,
- subtle layered depth,
- occasional glow only on selected/high-value states,
- generous spacing,
- clear titles,
- one dominant visual anchor per card.

---

## 5.4 Typography

Hierarchy:

```text
Large numeric or title anchor
Medium label
Small helper / tooltip / secondary text
Monospace only for:
prices, percentages, timestamps, IDs, exact values
```

The product should not look like a code editor.

---

## 5.5 Motion

Use subtle motion for:

- alert pulse,
- trigger proximity ring,
- changing sparkline,
- flow-state shift,
- expanding drawers,
- tab switching,
- chart overlays fading in.

Avoid endless floating animations.

---

# 6. Screen map

The major screens should be:

```text
1. Home Dashboard
2. Market
3. Setups
4. Watchlist
5. Stock Deep Dive
6. Flow Console
7. Traders
8. Journal
9. Lab
10. Settings
```

Each screen below includes:

- role,
- key layout,
- visual hierarchy,
- recommended charts/widgets,
- interaction rules.

---

# 7. HOME — “What deserves attention now?”

## 7.1 Role

Home is the scan-first command center.

It should answer in under 10 seconds:

```text
What is the market condition?
What setups are closest to actionable?
What is heating up?
What is risky?
What changed since I last looked?
```

---

## 7.2 Home layout

```text
┌──────────────────────────────────────────────────────────────┐
│ TOP BAR                                                     │
├───────┬──────────────────────────────────────────────────────┤
│ LEFT  │ HERO BAND                                           │
│ RAIL  │ Market state | Opportunity count | Alerts | Mode    │
│       ├──────────────────────────────────────────────────────┤
│       │ SECTION A — Opportunity Radar                        │
│       │ Large visual strip of top candidates                 │
│       ├──────────────────────┬───────────────────────────────┤
│       │ SECTION B            │ SECTION C                     │
│       │ Sector Heatmap       │ Trigger Zone Queue            │
│       ├──────────────────────┼───────────────────────────────┤
│       │ SECTION D            │ SECTION E                     │
│       │ Watchlist Pulse      │ Flow / Risk Snapshot          │
│       ├──────────────────────┴───────────────────────────────┤
│       │ SECTION F — Timeline of recent changes               │
└───────┴──────────────────────────────────────────────────────┘
```

---

## 7.3 Home hero band

Primary widgets:

### A. Market State Capsule

Shows:

```text
Market regime
Breadth
Leadership quality
Risk tone
```

Visual form:

- compact circular or segmented gauge,
- 3–4 colored status bars,
- tiny sparkline for breadth trend.

Beginner label:

```text
Market mood
```

---

### B. Opportunity Count Cluster

Show counts like:

```text
Strong setups
Near trigger
Flow-confirming
Warn / risk
New since last visit
```

Visual form:

- small number tiles with glow on “new”,
- category icons,
- click opens filtered Setups tab.

---

### C. Alert Pulse

Animated strip for the latest important events:

```text
ABC entered trigger zone
XYZ liquidity warning
DEF confirmed breakout
```

Visual form:

- slim ticker or pulse strip,
- minimal text,
- severity color,
- click opens related symbol.

---

## 7.4 Opportunity Radar

This is the signature Home widget.

### Goal

Present the best candidates visually, without dumping a table.

### Recommended form

A horizontally scrollable **opportunity card rail** where each card shows:

```text
symbol
setup type
price
Stock Strength
Entry Timing
trigger distance
live breakout health
room to move
```

Visual composition:

```text
Top: symbol + category badge
Middle: 3 stacked bars (Stock / Setup / Entry)
Right: trigger distance ring
Bottom: mini sparkline + policy badge
```

### Why it matters

This instantly looks different from generic terminals.

---

## 7.5 Sector Heatmap

Purpose:

```text
Which sectors/themes are actually leading?
```

Visual:

- rectangular heat grid,
- size = number of active candidates or market relevance,
- color intensity = sector momentum / breadth,
- hover reveals top names and trend sparkline.

Beginner label:

```text
Where momentum is clustering
```

---

## 7.6 Trigger Zone Queue

Purpose:

```text
Which stocks are closest to doing something now?
```

Visual:

- vertical stack,
- trigger-distance bar,
- status chip:
  - Far
  - Approaching
  - Testing
  - Confirming
  - Failed

Could look like an airport departure board meets tactical queue.

---

## 7.7 Watchlist Pulse

Purpose:

```text
What changed in the user's important names?
```

Visual:

- compact list of watched symbols,
- each line has a pulse dot,
- mini sparkline,
- one dominant state chip.

Examples:

```text
Near trigger
Extended
Flow improving
Social activity rising
```

---

## 7.8 Flow / Risk snapshot

Split card:

Left:

```text
live flow confirmations count
liquidity warnings
unknown/stale flow count
```

Right:

```text
circuit risk names
earnings-nearby names
social disagreement names
```

Use icon-led compact warnings rather than text blocks.

---

## 7.9 Recent changes timeline

Visual event timeline:

```text
09:28  ABC moved into testing
09:33  DEF confirmed breakout
09:41  XYZ spread widened
09:49  PQR new accepted trader entry
```

Keep it visual:

- event icon,
- time,
- short label,
- color-coded severity.

---

# 8. MARKET — “What is the environment?”

## 8.1 Role

This tab gives context rather than trade entry.

It should answer:

```text
Is the market helping or fighting momentum?
Which sectors/themes are leading?
Where is breadth expanding or collapsing?
Which stocks are the current leaders?
```

---

## 8.2 Layout

```text
Hero row:
- Market mood
- Breadth trend
- Sector leadership
- Risk tone

Main area:
- Sector heatmap
- Breadth time-series
- leadership ladder
- theme cluster panel
- top gainers / leaders panel
```

---

## 8.3 Key visualizations

### A. Breadth Trend Line

Simple clean chart:

- adv/dec type breadth or custom breadth score over time,
- regime background bands,
- clear annotated turning points.

Beginner label:

```text
Market participation
```

---

### B. Sector Heatmap

Already used on Home, but here larger and interactive.

Clicking a sector opens:

- top leaders,
- sector RS trend,
- breadth internals,
- active setup count.

---

### C. Sector Rotation Arc / Rank strip

Purpose:

```text
Which sectors are improving vs fading?
```

Could be visualized as:

- slope/rank ribbon chart,
- horizontal ladder with change arrows,
- rotating carousel of strongest sectors.

Keep it understandable; avoid overly academic charts.

---

### D. Leaderboard strip

Shows top stocks by:

- Stock Strength,
- Setup count,
- RS,
- fresh triggers.

Prefer a visual ladder rather than a plain table.

---

### E. Theme Bubble Map

Optional but visually strong.

Bubbles represent themes (defence, railways, power, etc.) sized by activity and colored by momentum.

Click bubble -> see related stocks.

---

# 9. SETUPS — “Show me the opportunities”

## 9.1 Role

This is the main opportunity browser.

Unlike Home, this can be denser, but still visual.

It must answer:

```text
What are the strongest setups?
Which ones are near actionable?
Which ones are strong stocks but bad entries?
Which ones are risky or extended?
```

---

## 9.2 Layout

```text
Top:
- filter chips
- sort control
- beginner/pro toggle
- saved views

Main:
- visual candidate grid/list hybrid

Optional right rail:
- quick details for selected symbol
```

---

## 9.3 Candidate card design

This is one of the most important pieces in the app.

Each card should contain:

```text
symbol
company / sector
setup type
price
3-layer quality bars
trigger distance
room-to-move meter
tradeability badge
live breakout health badge
small chart sparkline
policy state
```

### Signature visual pattern: the 3-Layer Quality Stack

Use a stacked tri-bar or tri-column widget:

```text
STOCK
SETUP
ENTRY
```

This becomes a brand-defining motif.

Why it matters:

It visually teaches users that a stock can be great while the entry is poor.

---

## 9.4 Sorting and views

Recommended sort options:

```text
Best now
Near trigger
Strongest stock
Best setup
Best entry timing
Best flow
Safest tradeability
Most improved today
```

Saved views:

```text
Momentum burst
IPO base
Pullback
Near trigger
Watch only
High-risk / high-reward
Beginner clean setups
```

---

## 9.5 Filters

Use compact chips rather than dropdown hell.

Examples:

```text
Setup type
Sector
Theme
Flow state
Trigger distance
Stock strength band
Entry timing band
Exit risk
Watchlisted
Social activity
```

---

## 9.6 Visualizations inside Setups tab

### A. Candidate scatter plot

A strong overview plot:

```text
x-axis = Entry Timing
y-axis = Stock Strength
bubble size = Setup Quality
bubble color = Flow state
```

This gives an immediate “map” of opportunity quality.

A beautiful and useful differentiator.

---

### B. Trigger ladder

Vertical ranked ladder showing how close names are to triggers.

---

### C. Room-to-move histogram

Shows distribution of breakout-room quality across current candidates.

Useful for understanding whether today's market is full of extended names.

---

# 10. WATCHLIST — “My names”

## 10.1 Role

A cleaner and more personal version of Setups.

This is where the user tracks specific stocks.

---

## 10.2 Layout

Watchlist should be card-first, not table-first.

Possible sections:

```text
Near action
Need patience
Risk rising
Missed / extended
Recent changes
```

---

## 10.3 Watch card widgets

Each watch card includes:

- symbol,
- latest price,
- mini price strip,
- trigger status,
- key risk,
- latest alert,
- one-line plain-language summary.

Example summary:

```text
Strong stock, valid setup, still slightly extended.
Wait for trigger test or tighter reset.
```

This is a place where the advisory text is acceptable because it is personal and concise.

---

## 10.4 Extra watchlist visuals

### Watchlist storyboard

A timeline strip per symbol:

```text
Added
Setup detected
Near trigger
Flow improved
Failed
Recovered
Triggered
```

Visually appealing and useful.

---

# 11. STOCK — Deep Dive Workspace

## 11.1 Role

This is where the user spends real analysis time on one symbol.

It should feel like a clean, cinematic tactical workspace rather than a random dashboard.

---

## 11.2 Layout concept

```text
┌──────────────────────────────────────────────────────────────┐
│ Symbol header: price | setup | policy | key badges          │
├───────────────────────────────┬──────────────────────────────┤
│ Main chart                    │ Decision Card               │
│                               │ Stock / Setup / Entry       │
│                               │ Flow / Tradeability         │
├───────────────────────────────┼──────────────────────────────┤
│ Momentum panel                │ Trade Geometry panel        │
├───────────────────────────────┼──────────────────────────────┤
│ Flow panel                    │ Social / Evidence panel     │
├───────────────────────────────┴──────────────────────────────┤
│ History / Research / Timeline                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 11.3 Symbol header

Include:

- symbol,
- company,
- sector/theme tags,
- price and % change,
- setup type chip,
- policy state chip,
- feed state,
- watchlist toggle.

Do not overload with 15 badges.

---

## 11.4 Main chart

This is the visual center of the product.

### Must include

- candles,
- volume,
- EMA21,
- EMA50,
- relevant AVWAPs / key cost zones,
- trigger line,
- invalidation line,
- selected resistance/hurdle zone,
- optional shaded confluence zones.

### Nice to have

- replay scrubber,
- annotation markers,
- setup overlay framing the pattern,
- view presets:
  - Setup
  - Entry
  - Flow
  - History

### Important rule

The chart should remain beautiful and readable.

It should **not** become a spaghetti plot.

---

## 11.5 Decision Card

This is the anchor panel beside the chart.

Show:

```text
Stock Strength
Setup Quality
Entry Timing
Tradeability
Live Breakout Health
Room To Move
Main Risks
Unknowns
Policy state
```

This card should be visually sharp and high contrast.

It is the “answer card” for the selected stock.

---

## 11.6 Momentum panel

Use a compact **Momentum State Panel** inspired by the earlier concept.

Show visually:

- RS Market,
- RS Sector,
- Sector Momentum,
- Peer Rank,
- RVOL,
- Delivery Expansion,
- ADR,
- distance from EMA21,
- distance from Key Cost Zone,
- distance from 52W high.

Prefer bars, rings and aligned numeric tiles over text paragraphs.

---

## 11.7 Trade Geometry panel

This is crucial and visually differentiating.

Recommended widgets:

### A. Trigger Distance Meter

A ring or bar showing how close current price is to the trigger.

### B. Room-To-Move Meter

A horizontal bar showing:

```text
entry point
nearest hurdle
projected open space
```

### C. R:R Ladder

Simple vertical ladder or stepped ruler:

```text
entry
stop
1R
2R
3R
nearest hurdle
```

### D. Extension Meter

Show whether current price is:

```text
near key cost zone
normal momentum
extended
chase risk
```

This could be a banded bar with the current position marked.

### E. Correction Type Widget

Very simple icon/diagram:

```text
TIME correction
PRICE correction
MIXED
```

Could appear as a small pattern diagram rather than text.

---

## 11.8 Flow panel

This is a mini version of the dedicated Flow tab.

Show:

- flow state,
- confidence,
- spread quality,
- persistence,
- price response,
- liquidity state,
- recent state timeline.

Use tiny bar matrices or a radar-like strip rather than large text.

---

## 11.9 Social / Evidence panel

Compact by default.

Show:

- recent accepted trader actions,
- trader handles,
- claim type,
- time,
- evidence thumbnail,
- disagreement or unresolved badge.

Must feel inspectable, not noisy.

---

## 11.10 History / Research strip

Small lower section showing:

- prior similar setups,
- setup outcome history,
- MFE/MAE snapshot,
- replay button,
- notes or journal link.

---

# 12. FLOW — Live Breakout Console

## 12.1 Role

The Flow tab is for active monitoring of names near decision points.

It should feel more alive and real-time than the rest of the app.

---

## 12.2 Layout

```text
Left:
- trigger-zone queue

Center:
- selected symbol live flow view

Right:
- liquidity / warning / alert rail
```

---

## 12.3 Trigger-zone queue

Every row should show:

- symbol,
- stage:
  - Approaching
  - Testing
  - Confirmed
  - Failed
- trigger distance,
- tradeability badge,
- flow pulse,
- time since state change.

This should be highly scanable.

---

## 12.4 Live flow view

For selected symbol show:

### A. Flow Pulse Matrix

A compact matrix across windows:

```text
5s   15s   1m   5m
```

Rows:

```text
imbalance
persistence
price response
spread
liquidity
stability
```

Use bars / intensity blocks, not raw paragraphs.

### B. Flow State Timeline

A mini timeline showing:

```text
Approaching → Testing → Confirming → Failed
```

with timestamps.

### C. Liquidity Ladder

A visual ladder or stacked horizontal bars showing top-of-book quality and concentration.

### D. Breakout Health Gauge

Large expressive widget for:

```text
CONFIRMING
MIXED
WEAK
BREAKOUT RISK
UNKNOWN
```

This should be one of the flashiest but most useful elements.

---

## 12.5 Flow alerts panel

Slim chronological rail for:

- spread widened,
- flow improved,
- failure detected,
- liquidity deteriorated,
- feed stale.

Icons and short messages only.

---

# 13. TRADERS — Social Context

## 13.1 Role

This tab is not the trading engine.

It provides:

```text
what traders are discussing
who has taken actions
what evidence exists
where there is agreement or disagreement
```

It should look more like an “evidence map” than a social feed.

---

## 13.2 Layout

Sections:

- Activity overview
- Recent accepted claims
- Symbol attention map
- Trader cards
- Evidence drawer

---

## 13.3 Key visualizations

### A. Symbol Attention Map

Bubble or ranked strip showing which symbols are being discussed most.

### B. Claim Timeline

For a chosen symbol:

```text
entry
add
stop move
partial exit
full exit
lesson
```

in chronological visual form.

### C. Trader Style Cards

Each trader card shows:

- handles,
- recent action,
- sectors/themes active in,
- sample size,
- focus style tags.

### D. Agreement / Disagreement strip

Quickly tells if multiple traders are aligned or mixed.

---

## 13.4 Important UX rule

Do not make this tab feel like Twitter inside the app.

It should feel like:

```text
curated evidence
```

not

```text
scrolling social noise
```

---

# 14. JOURNAL — Discipline / Review

## 14.1 Role

Later-phase workspace for reviewing execution quality.

It should visually highlight behavioral leaks, not feel like bookkeeping.

---

## 14.2 Core sections

- trade outcome overview,
- behavior leak dashboard,
- trade timeline,
- right-tail capture panel,
- weekly review notes.

---

## 14.3 Key visualizations

### A. R Distribution Curve

Shows actual realized R distribution.

### B. MFE vs Realized Exit Scatter

Powerful and intuitive.

Purpose:

```text
Did you leave too much on the table?
```

### C. Rule Violation Heatmap

Examples:

```text
late entries
premature exits
ignored vetoes
oversized risk
excess trading
```

### D. Weekly timeline

Simple chronological review of trades and mistakes.

---

# 15. LAB — Research and Replay

## 15.1 Role

This is the “under the hood” workspace.

Pro-focused.

Still should remain visually clear.

---

## 15.2 Sections

- replay,
- feature ablation,
- setup expectancy,
- validation summaries,
- negative findings,
- model/version status.

---

## 15.3 Key visualizations

### A. Ablation Ladder

A stepped comparison chart:

```text
Baseline
+ Setup
+ Geometry
+ Liquidity
+ Flow
+ Social
+ Judge
```

Show changes in expectancy / drawdown / false breakouts.

### B. MFE/MAE box or violin plots

For setup families.

### C. Feature contribution panels

For optional GBT model or score decomposition.

### D. Replay timeline

Allows stepping through a past session or setup.

### E. Negative Findings board

Very important and visually distinctive.

Could show “retired” features with reasons.

---

# 16. SETTINGS

Must not be an afterthought.

Should include:

- Beginner / Pro,
- light optional theme if ever supported,
- alert preferences,
- watchlist defaults,
- glossary level,
- metric units/formatting,
- active feature flags,
- feed/source status,
- version info.

Advanced configuration can remain hidden under an “Advanced” section.

---

# 17. Widget library

This section defines the visual building blocks that make the product distinctive.

---

## W1 — 3-Layer Quality Stack

Purpose:

```text
show Stock / Setup / Entry distinctly
```

Formats:

- three aligned bars,
- three vertical thermometers,
- three adjacent columns.

Must be reusable everywhere.

---

## W2 — Trigger Distance Ring

Purpose:

```text
how close current price is to trigger
```

A circular progress ring with a small center label works well.

---

## W3 — Room-To-Move Meter

Purpose:

```text
how much open space remains before nearby resistance/hurdle
```

Horizontal band with green/yellow/red zones.

---

## W4 — Extension Meter

Purpose:

```text
near cost zone
normal momentum
extended
chase risk
```

Could visually mirror the room meter but in the opposite semantic direction.

---

## W5 — Breakout Health Gauge

Purpose:

```text
flow confirmation state
```

High-value widget for Flow screen and Stock panel.

---

## W6 — Liquidity Ladder

Purpose:

```text
quality of tradeability / exit ability
```

Use stacked depth-style bars or a stability ladder.

---

## W7 — Flow Pulse Matrix

Purpose:

```text
multi-window view without a paragraph
```

Rows = features, columns = windows, cell intensity = value/quality.

---

## W8 — Momentum State Panel

Purpose:

```text
show RS / sector / participation / extension compactly
```

Can be a branded panel style for the app.

---

## W9 — Opportunity Radar Cards

Purpose:

```text
scan top candidates visually
```

Home and Setups use them.

---

## W10 — Sector Heatmap

Purpose:

```text
where leadership is clustering
```

A must-have.

---

## W11 — Candidate Scatter Map

Purpose:

```text
opportunity landscape
```

A visually striking differentiator.

---

## W12 — R:R Ladder

Purpose:

```text
entry / stop / key levels
```

Useful and intuitive.

---

## W13 — Storyboard Timeline

Purpose:

```text
show setup or watch progression over time
```

Good for Watchlist and Journal.

---

## W14 — Evidence Rail

Purpose:

```text
social proof chain
```

Selected symbol or trader evidence on the right side.

---

## W15 — Replay Scrubber

Purpose:

```text
move through a historical setup / session
```

Powerful for Lab and education.

---

# 18. Chart catalog

The app should deliberately prefer a specific set of chart types.

## 18.1 Primary charts

Use frequently:

- candle chart with overlays,
- sparkline,
- horizontal/vertical bar chart,
- heatmap,
- scatter plot,
- timeline,
- ladder chart,
- gauge / meter,
- banded bar,
- step-line state chart.

## 18.2 Secondary charts

Use selectively:

- bubble map,
- violin/box plot,
- area chart,
- radial summary.

## 18.3 Avoid or heavily limit

- 3D charts,
- pie charts for critical decisions,
- decorative radar charts for core data,
- overloaded treemaps,
- sankeys unless clearly justified,
- super-dense tables by default.

---

# 19. Wording system and glossary translation

The product should carry a deliberate translation layer from internal jargon to surface labels.

## 19.1 Recommended surface wording

| Internal term | Surface label | Helper text |
|---|---|---|
| Stock Quality | Stock Strength | Overall leadership and trend quality |
| Setup Quality | Setup Quality | How clean the pattern/setup is |
| Entry Quality | Entry Timing | Whether the current price is attractive |
| Liquidity State | Tradeability | How easy it may be to enter/exit |
| Order Flow | Live Breakout Health | Near-price action around the trigger |
| Breakout Room | Room To Move | Space before nearby resistance |
| AVWAP | Key Cost Zone | A reference cost area from an important event |
| Delivery Expansion | Stronger Participation | Whether real participation is expanding |
| Sector Breadth | Sector Participation | How many names in the group are supporting the move |
| Circuit Risk | Exit Risk | Risk of limited exit flexibility |
| Social Context | What Traders Are Saying | Recent evidence-backed trader activity |
| Confluence | Alignment | How well multiple factors support each other |
| Invalidation | Failure Level | Level where the setup weakens |

Use the advanced term as hover/help text in Beginner Mode, and the internal term directly in Pro Mode.

---

# 20. Interaction design rules

## I1 — Single-click progression

Clicking a symbol should move the user naturally:

```text
Home / Setups / Watchlist
      → Stock
          → Flow / Traders / Research
```

No user should need to open five nested menus to inspect one stock.

---

## I2 — Selection persistence

Selected symbol remains persistent across tabs unless user changes it.

Example:

```text
User selects ABC in Setups
→ opens Stock
→ clicks Flow
→ Flow opens on ABC
→ clicks Traders
→ Traders opens symbol context for ABC
```

This makes the app feel coherent.

---

## I3 — Progressive disclosure

Default: compact.

Expand only when asked.

Panels should support:

- compact,
- expanded,
- full-screen where necessary.

---

## I4 — Glossary help on demand

A beginner should be able to hover or tap on any advanced label and see a **one-line plain explanation**.

Not a tutorial essay.

---

## I5 — Keyboard efficiency

Support:

- slash search,
- quick open,
- arrow navigation in candidate list,
- enter to open symbol,
- hotkeys for tabs.

This adds premium feel without cluttering the screen.

---

## I6 — Visual state consistency

If “warning” is amber in one place, it should not be teal elsewhere.

If “Confirming” is a pulsing positive state in Flow, the same concept should not appear as a static neutral chip in another tab.

---

## I7 — Drill-down hierarchy

The app should let the user move from:

```text
market
→ sector/theme
→ symbol
→ setup
→ live flow
→ evidence
→ history
```

without losing orientation.

Use breadcrumbs and active filters clearly.

---

# 21. Beginner onboarding design

This app should not require a long tutorial.

Instead, the UI itself should teach.

## 21.1 First-run overlay

Minimal, maybe 5 steps:

1. Market mood
2. Opportunity cards
3. The 3-layer quality stack
4. Stock deep dive
5. Flow confirmation

Keep it visual.

---

## 21.2 “What matters now?” hints

In Beginner Mode, selected screens can show a one-line helper ribbon.

Examples:

```text
Focus first on Stock Strength + Setup Quality.
Then check Entry Timing.
Only then worry about live flow.
```

or:

```text
A strong stock is not always a good entry.
That is why Entry Timing is shown separately.
```

---

## 21.3 Inline glossary chips

A small “?” chip beside advanced items can reveal a short definition drawer.

---

# 22. Visual anti-patterns to avoid

Do not let the app turn into any of the following:

## A. KPI cemetery

Too many floating cards with numbers and no decision logic.

## B. Table prison

A dense grid with 30 columns and tiny unreadable cells.

## C. Futuristic junkyard

Random neon lines, fake HUD corners, glowing boxes, meaningless animation.

## D. AI wallpaper

Huge assistant panel with text blurting out opinions while the visuals do very little.

## E. Quant overreach

Using academic chart types or jargon-heavy panels where a simpler visual would do.

## F. Broker clone

Looking like every commodity broker terminal from a decade ago.

---

# 23. Brand and emotional feel

The product should emotionally communicate:

```text
focus
clarity
momentum
speed
control
edge
```

Not:

```text
chaos
hype
prediction magic
mysticism
```

Good emotional reference words:

- tactical,
- premium,
- sharp,
- alive,
- lucid,
- confident.

---

# 24. Recommended screen-by-screen visual priority

## Home
**Priority:** wow + scan speed

- opportunity cards
- heatmap
- trigger queue
- alert pulse

## Market
**Priority:** environment clarity

- breadth
- sectors
- leadership

## Setups
**Priority:** compare opportunities

- candidate cards
- scatter map
- filters

## Watchlist
**Priority:** personal monitoring

- watch cards
- timeline
- change highlights

## Stock
**Priority:** one-stock decision clarity

- chart
- decision card
- geometry
- flow

## Flow
**Priority:** real-time state

- trigger queue
- pulse matrix
- health gauge

## Traders
**Priority:** evidence context

- claims timeline
- attention map
- trader cards

## Journal
**Priority:** behavior insight

- R distribution
- rule leak charts
- MFE vs realized exit

## Lab
**Priority:** proof and validation

- ablation ladder
- expectancy plots
- replay

---

# 25. Suggested implementation sequence for UI

This manual is separate, but it must be buildable in stages.

## UI Phase 1 — V1 usable shell

Build:

- navigation shell,
- Home,
- Setups,
- Stock,
- basic Flow,
- core widgets:
  - quality stack,
  - trigger ring,
  - room meter,
  - decision card,
  - sector heatmap.

## UI Phase 2 — richer experience

Add:

- Market tab,
- Watchlist,
- flow pulse matrix,
- candidate scatter map,
- symbol research strip,
- alert center,
- Beginner/Pro mode.

## UI Phase 3 — social + journal + lab

Add:

- Traders,
- Journal,
- Lab,
- evidence rail,
- replay,
- ablation views.

## UI Phase 4 — polish

Add:

- animations,
- keyboard shortcuts,
- saved views,
- command palette,
- onboarding,
- micro-interactions,
- premium empty/error states.

---

# 26. UI acceptance criteria

A screen is not accepted merely because it renders.

## 26.1 Universal acceptance checklist

- [ ] The screen answers one primary user question.
- [ ] The first scan works without reading long text.
- [ ] Visual hierarchy is obvious in under 3 seconds.
- [ ] Color, icon and text agree.
- [ ] Unknown data is visibly unknown.
- [ ] No stale data appears current.
- [ ] Card density is comfortable at desktop resolution.
- [ ] No panel requires a paragraph to be useful.
- [ ] The selected symbol context is obvious.
- [ ] The screen works in Beginner and Pro mode.
- [ ] There is at least one distinctive visualization, not just cards and tables.
- [ ] Error/empty states are compact and human-readable.

---

## 26.2 Home acceptance

- [ ] User can identify top opportunities in under 10 seconds.
- [ ] User can tell whether the market is supportive or hostile.
- [ ] Opportunity Radar cards are visually scanable.
- [ ] Trigger queue is obvious and clickable.
- [ ] Heatmap highlights leadership clearly.

---

## 26.3 Setups acceptance

- [ ] User can understand Stock vs Setup vs Entry visually.
- [ ] Sorting by “Best now” produces intuitive results.
- [ ] Candidate scatter plot is understandable.
- [ ] Filter chips do not overwhelm the interface.
- [ ] A selected symbol can be opened with one click.

---

## 26.4 Stock acceptance

- [ ] Main chart is readable and uncluttered.
- [ ] Decision Card is the clear answer panel.
- [ ] Trade Geometry is visually explained, not text-dumped.
- [ ] Flow and Social context are visible but not overwhelming.
- [ ] User can tell why the setup is attractive or unattractive.

---

## 26.5 Flow acceptance

- [ ] Trigger-stage state is obvious.
- [ ] Flow Pulse Matrix reads quickly.
- [ ] Breakout Health Gauge is expressive and useful.
- [ ] Stale flow is visibly marked.
- [ ] Alert rail is compact and non-spammy.

---

## 26.6 Traders acceptance

- [ ] Social tab feels like evidence, not a social feed.
- [ ] Claim types are distinguishable.
- [ ] Evidence can be opened easily.
- [ ] Agreement/disagreement is visible.
- [ ] Unresolved claims are not misrepresented as fact.

---

## 26.7 Journal acceptance

- [ ] Behavioral leaks can be seen visually.
- [ ] MFE vs actual exit is understandable.
- [ ] The screen encourages review, not guilt-wall bookkeeping.
- [ ] Rule violations are grouped clearly.

---

## 26.8 Lab acceptance

- [ ] Ablation comparisons are visually intuitive.
- [ ] Replay is usable.
- [ ] Negative findings are visible, not hidden.
- [ ] Validation data does not require reading raw logs.

---

# 27. Example user flow

## Scenario: beginner scans opportunities

```text
Open app
  ↓
See Market mood = supportive
  ↓
Look at Opportunity Radar
  ↓
Spot ABC: high Stock Strength, high Setup Quality, moderate Entry Timing
  ↓
Open ABC Stock page
  ↓
See chart + Decision Card
  ↓
Check Room To Move + Trigger Distance
  ↓
Notice Flow = MIXED
  ↓
Switch to Flow tab
  ↓
See testing state, price response still weak
  ↓
Decide to wait rather than chase
```

This is the intended feel:

```text
visual
fast
guided
not text-heavy
```

---

# 28. Example screen copy tone

Tone should be:

- direct,
- short,
- clear,
- non-corny,
- non-hypey.

Good:

```text
Strong stock. Entry still a bit extended.
Wait for cleaner trigger behavior.
```

Good:

```text
Live breakout health is weakening.
Spread widened and price response faded.
```

Bad:

```text
The confluence matrix suggests the probability-weighted bullish thesis remains compelling.
```

Bad:

```text
Our AI strongly believes this is a once-in-a-lifetime breakout.
```

---

# 29. Product-wide Definition of Done

The UI/UX layer is considered mature when all of the following are true:

- [ ] The app has a clear top-level navigation.
- [ ] Home gives a strong visual overview.
- [ ] Market context is understandable.
- [ ] Setups can be scanned visually rather than only in tables.
- [ ] Stock / Setup / Entry distinction is a consistent visual motif.
- [ ] The Stock workspace supports one-symbol decision-making.
- [ ] Flow feels live and useful.
- [ ] Traders feels evidence-based, not social-feed-like.
- [ ] Beginner Mode is meaningfully simpler in language.
- [ ] Pro Mode reveals deeper detail without changing app structure.
- [ ] The product has at least 5 strong signature visual widgets.
- [ ] The interface feels premium and distinct from generic terminals.
- [ ] Visualizations do more work than paragraphs.
- [ ] Unknown/stale data remains honest.
- [ ] The product feels coherent across screens.
- [ ] The UI supports the deterministic decision flow rather than obscuring it.

---

# 30. Final product philosophy

The product should feel like this:

```text
SEE THE MARKET
      ↓
SPOT THE OPPORTUNITIES
      ↓
UNDERSTAND THE SETUP
      ↓
CHECK THE ENTRY
      ↓
CHECK TRADEABILITY
      ↓
CHECK LIVE BREAKOUT HEALTH
      ↓
OPTIONAL SOCIAL CONTEXT
      ↓
DECIDE
```

The most important visual lesson the tool must teach is:

```text
Great stock
≠
Great setup
≠
Great entry
```

If the UI successfully teaches that through its structure and visuals, then it is doing something genuinely better than the usual trading terminal.

And if the app still looks cool while doing that, even better.
