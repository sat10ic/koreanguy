# DESK DESIGN SPEC

## Overview
Manas Desk is a trading decision-support interface for disciplined traders following a systematic process. The design prioritizes information density, real-time feedback, and visual hierarchy to enable rapid pattern recognition and decision-making.

**Theme:** Dark mode (charcoal/black background with cyan/purple/green accents)  
**Target Audience:** Beginner trader adopting a trading system discipline  
**Interaction Model:** Rich (hover states, tooltips, expandable rows, drag interactions)  
**Data Density:** Compact — all critical information visible without scrolling, minimal whitespace

---

## Color Palette

| Role | Color | Usage |
|------|-------|-------|
| **Primary Accent** | `#00d4ff` (cyan) | Active tabs, live indicators, key metrics |
| **Secondary Accent** | `#b366ff` (purple) | Secondary highlights, agent identity |
| **Tertiary Accent** | `#00ff66` (neon green) | Positive signals, bullish indicators |
| **Background** | `#0a0a0a` (near-black) | Main canvas |
| **Surface** | `#141414` (charcoal) | Cards, panels, headers |
| **Divider** | `#2a2a2a` (dark gray) | Borders, separators |
| **Text Primary** | `#e0e0e0` (light gray) | Body copy, default text |
| **Text Secondary** | `#999999` (medium gray) | Labels, inactive states, secondary info |
| **Text Muted** | `#666666` (dark gray) | Disabled, stale data |
| **Error** | `#ff4444` (red) | Failures, urgent states (exit now) |
| **Warning** | `#ffaa00` (orange) | Degraded states, stale data banners |

---

## Typography

| Element | Font | Size | Weight | Line Height |
|---------|------|------|--------|-------------|
| **Header Title** | Helvetica | 16px | 700 | 1.2 |
| **Tab Labels** | Helvetica | 13px | 500–600 | 1.4 |
| **Section Headers** | Helvetica | 14px | 600 | 1.3 |
| **Body Copy** | Helvetica | 13px | 400 | 1.5 |
| **Data Values** | Helvetica Mono | 13px | 400 | 1.4 |
| **Labels/Captions** | Helvetica | 11px | 400 | 1.3 |

**Line height:** 1.5 for body, 1.2–1.3 for headings (tight, energetic feel)  
**Letter spacing:** Minimal; use weight contrast instead of letter-spacing for hierarchy

---

## Component Library

### 1. Header (Global Shell)
**Height:** 56px  
**Background:** `#141414` with bottom border `1px solid #2a2a2a`

**Layout:** Flex row, space-between
- **Left:** Logo text "MANAS DESK" (14px, bold)
- **Center:** Date scrubber with `<` `>` arrows + dropdown date picker (13px)
- **Right:** Regime chip (SELECTIVE/LIVE), day-color dot, XP score badge, DRY-RUN/LIVE toggle

**Interaction:**
- Date arrows: scrub back in time, all tabs respond to ?date= parameter
- Regime dropdown: shows current regime + age_days
- Live dot (◔): pulses cyan when pipeline running
- Help text on hover for each element

### 2. Tab Navigation
**Height:** 44px  
**Background:** `#141414` with bottom border `1px solid #2a2a2a`

**Tabs:** [ DESK ] DEBATE POSITIONS LEDGER

**Styling:**
- **Inactive:** `color: #999`, `border-bottom: 2px solid transparent`
- **Active:** `color: #00d4ff`, `font-weight: 600`, `border-bottom: 2px solid #00d4ff`
- **Transition:** all 200ms ease
- **Hover:** `color: #00d4ff` (preview)

**Right corner:** Live pipeline dot + "pipeline running" text (if applicable)

### 3. Alert Banners (Stale Data)
```
┌─────────────────────────────────────────────────────────┐
│ ⚠ Data fresh only through 2026-07-07 — last night's    │
│   run did not complete.                                  │
└─────────────────────────────────────────────────────────┘
```

**Background:** `#2a2a00` (dark olive)  
**Text:** `#ffaa00` (orange warning)  
**Icon:** ⚠ (left-aligned)  
**Height:** 40px, center-aligned  
**Margin:** 12px horizontal padding, 8px vertical

---

## Tab Panels (Content Areas)

### DESK Tab
**Background:** `#0a0a0a`  
**Padding:** 20px  
**Gap:** 16px between sections

#### Morning Brief Card
- **Background:** `#141414`
- **Border:** `1px solid #2a2a2a`, `border-radius: 4px`
- **Padding:** 16px
- **Typography:** 13px line-height 1.5
- **Content:** Narrative summary of the night's activity (from run_card.morning_brief)

#### Regime Strip (Two Explicit Keeps)
Horizontal flex row, equal-width columns

**MBI Column:**
- Dot chip (day-color, size 12px)
- Label "MBI"
- Values: adv/dec ratio, day breadth (312/188 ▲)
- Help text: "[B] Market breadth indicator"

**XP Column:**
- Score value (62) with direction arrow (▲/▼)
- Dial/gauge (optional: compact SVG dial)
- Help text: "[B] Desk readiness score"

#### Activity Stream
**Layout:** Vertical list, reverse-chronological  
**Row height:** 36px  
**Spacing:** 8px gap

**Each row:**
- **Time:** 13px, `#999`, 50px fixed width
- **Agent Chip:** Color-coded identity (Sizer = purple, Vision = green, etc.), 8px badge
- **Message:** Body copy, left-aligned
- **Expand arrow:** `▸` right-aligned, opacity 0.6, hover opacity 1.0

**Expand state:** Row expands to reveal transcript/chart/plan (height: variable, animation: 200ms)

#### In-Flight Row
**Background:** `#1a1a1a` (slightly lighter)  
**Border-left:** 2px solid `#00d4ff`  
**Padding:** 12px 16px

**Content:**
- Agent chip + message + running indicator (◔ + "running (started Ns ago)")

### DEBATE Tab
**Background:** `#0a0a0a`  
**Padding:** 20px  
**Gap:** 20px between symbols

#### Symbol Card (e.g., KPIL)
**Background:** `#141414`  
**Border:** `1px solid #2a2a2a`, `border-radius: 4px`  
**Padding:** 16px

**Header Row:**
- **Symbol + Lens:** "KPIL · lens STRONG START · CHAIR: TAKE"
- **Font:** 14px, bold

**Conviction Section:**
- Label "Conviction"
- Per-agent dots (● ● ○ etc.) with count (3/5)
- Spread indicator if disagreement exists
- **Font:** 12px, `#999`

**Bull Case / Bear Case (2-column):**
- **Background:** Each side `#0a0a0a`
- **Padding:** 12px
- **Border-left:** 2px solid `#00ff66` (bull), `#ff4444` (bear)
- **Typography:** 13px, tight line-height

**Vision Strip (if charts available):**
- Image container: 120px × 80px each
- Images: agent_charts/{date}/{SYM}_daily.png + _weekly.png
- Stamp text below: "[agent reasoning] ✓ +1"
- **Font:** 11px, `#999`

**Plan Section:**
- Labels: "entry 892.0 · stop 861.5 · target 953.0 · RR 2.0 · base qty 34"
- **Font:** 13px, monospace
- Sizer row: "0.75x → final qty 25 · [reasoning]"
- **Background:** `#1a1a1a`, padding 12px

**Footer:**
- Base rate chips: "STRONG_START: 6/13 (46%)"
- Per-agent record: "Nemotron on STRONG_START: 5/9"
- **Font:** 11px, `#666`

### POSITIONS Tab
**Background:** `#0a0a0a`  
**Padding:** 20px  
**Gap:** 16px

#### Position Card (e.g., HUDCO)
**Background:** `#141414`  
**Border:** `1px solid #2a2a2a`, `border-radius: 4px`  
**Padding:** 16px

**Header:**
- Symbol + status (open/closed)
- Entry date + price
- **Font:** 14px, bold

**R-Path Chart (ASCII):**
```
  +2R ─┤          ╭──╮
  +1R ─┤     ╭────╯  ╰─╮
   0  ─┤╭────╯          ╰──
```
- **Size:** 200px wide × 80px tall
- **Lines:** Current price (now +1.4R), trail stop (228)
- Phase bands: INITIATION | TREND | EXTENSION

**Coach Signal:**
- **Background:** `#1a1a1a`, padding 12px
- **Icon:** ●
- **Text:** "HOLD — wobble normal until 892 breaks."
- **Font:** 13px, cyan

**Original Thesis Box:**
- **Background:** `#0a0a0a`, padding 12px, border-left 2px solid `#999`
- **Label:** "ORIGINAL THESIS (Nemotron, Jul 3)"
- **Content:** "[bull case verbatim]"
- **Font:** 12px

**Telegram Mirror:**
- **Background:** `#1a1a1a`, padding 12px
- **Content:** "✔ sent 18:44 · [message] (dry-run: shown, not sent)"
- **Font:** 11px, `#999`

**Urgent Variant (EXIT NOW):**
- **Background:** `#330000` (dark red)
- **Icon:** ⛔
- **Text:** "EXIT NOW — two strikes fired"
- **Font:** 14px, bold `#ff4444`

### LEDGER Tab
**Background:** `#0a0a0a`  
**Padding:** 20px  
**Gap:** 20px

#### Agent Track Records Table
**Layout:** CSS Grid, columns: AGENT | LENS | REGIME | HIT | AVG R | n | TREND

**Header row:**
- **Background:** `#1a1a1a`, padding 8px 12px
- **Font:** 11px, bold, `#999`

**Data rows:**
- **Background:** `#141414`, padding 8px 12px
- **Border-bottom:** `1px solid #2a2a2a`
- **Font:** 12px

**Trend arrow:** ▲ (green) / ▼ (red)

#### Lessons Diary
**Background:** `#141414`, padding 12px, margin-bottom 12px  
**Border-left:** 2px solid `#00d4ff`

**Content:**
- **Date:** "2026-06-28"
- **Symbol:** "SYRMA"
- **Tag:** "[right-process-loss]" (cyan)
- **Body:** Lesson text (13px)

#### Digest In Force
**Background:** `#0a0a0a`, padding 12px  
**Border-left:** 2px solid `#00ff66`

**Content:**
- Bullet points (11px)
- Light gray text

#### Sections
- Trade Journal (table)
- Equity Curve (line chart)
- Expectancy Matrix (grid)

---

## Chart Drawer (Overlay Modal)

**Background:** `#141414` with semi-transparent dark backdrop  
**Width:** 600px  
**Border:** `1px solid #2a2a2a`  
**Padding:** 16px  
**Border-radius:** 4px

**Header:**
- Symbol name "KPIL" (14px, bold)
- Close button ✕ (top-right)

**Chart Area:**
- Lightweight Charts (TradingView) embed
- ~120 daily bars visible
- EMA 10/21/50 overlays (cyan/purple/green)
- Buy-zone band (semi-transparent green)
- Stop line (red)
- Volume panel below (30% of height)

**Footer:**
- Vision note: "[agent reasoning]"
- **Font:** 11px, `#999`

---

## States & Variants

### Empty States
Each tab displays a single line explaining why empty + when data arrives:
- DESK: "No run for [date] yet. The desk runs after market close (~18:30)."
- DEBATE: "No debate for this date — shortlist was empty or the debate stage didn't run."
- POSITIONS: "No open positions. Entry signals appear here once the desk takes a name."
- LEDGER: "No closed outcomes yet — track records and lessons fill in as trades resolve."

**Font:** 13px, `#666`

### Degraded Night (Failed Models)
- Failed agent chips render greyed (opacity 0.5)
- Reason shown on hover: "429 / truncated / struck"
- Morning brief explains: thin shortlist, zero-take, struck (INTENTIONAL, never error red)

### Stale Data Banner
- Global banner above tab nav when scrubbed date's pipeline != ok
- Orange warning, yellow text, centered

### DRY-RUN vs LIVE
- Header badge: ⦿DRY-RUN / ●LIVE
- Telegram rows: label mirrors mode
- DRY-RUN shows exact message, marked "not sent"
- Exit/urgent coach signals surface in BOTH modes (never suppressed)

---

## Interaction Patterns

### Hover States
- **Buttons:** Opacity increase, cursor pointer
- **Expandable rows:** Background fade to `#1a1a1a`, shadow appear
- **Text links:** `color: #00d4ff`
- **Chart areas:** Tooltip fade-in on hover

### Animations
- **Tab switches:** Content fade-in 300ms ease-out
- **Row expand:** Height animate 200ms ease
- **Live dot pulse:** Infinite pulse @ 1s cycle, opacity 0.5 → 1.0
- **Staggered reveals:** Activity stream rows appear 50ms apart on load

### Interactions
- Date scrubber: Click arrows or open dropdown, all tabs re-fetch with ?date=
- Agent chip click: Expands row or opens full transcript
- Chart symbol click: Opens modal Chart Drawer (600px overlay)
- Drag-to-reorder: Activity stream rows (future: drag to pin favorites)

---

## Responsive Behavior
**Primary breakpoint:** 1920px (standard desk width)  
**Secondary:** 1440px (laptop)  
**Minimum:** 1280px (tab overflow: horizontal scroll)

Data density is maintained; font sizes do NOT shrink below minimums.

---

## Backend Integration Notes

### Endpoints Required
1. `GET /api/desk/feed?date=` — activity stream logs
2. `GET /api/desk/run-card?date=` — morning brief, regime, pipeline status
3. `GET /api/agents/verdicts?date=` — debate data (conviction, bull/bear, vision)
4. `GET /api/agents/track-records?date=` — agent hit rates, avg R (BACKEND-GAP-4)
5. `GET /api/watchlist` — coach field + journal + agent_signals
6. `GET /api/agents/charts/{date}/{SYM}_{daily,weekly}.png` — vision strip images (BACKEND-GAP-3)
7. `GET /api/lessons?date=` — lesson .md files + _digest.md (BACKEND-GAP-5)
8. `GET /api/mbi?date=` — MBI breadth + XP (BACKEND-GAP-1)

### Missing Fields (Backend Gaps)
- **BACKEND-GAP-1:** MBI day-color, adv/dec ratio, XP score
- **BACKEND-GAP-2:** run_card.morning_brief narrative string
- **BACKEND-GAP-3:** HTTP route for agent chart PNGs
- **BACKEND-GAP-4:** Per-agent track record aggregation (hit%, avg R)
- **BACKEND-GAP-5:** Lesson .md + _digest.md endpoints

---

## Accessibility

- **Color contrast:** All text meets WCAG AA on dark backgrounds
- **Focus states:** Visible outline (cyan) on keyboard nav
- **ARIA labels:** Buttons and interactive elements labeled
- **Keyboard nav:** Tab order follows visual hierarchy
- **Help text:** [B] indicators provide beginner context on hover

---

## File Structure
```
Desk.dc.html                    (Main Design Component)
├── Template (streaming)
│   ├── <helmet> (fonts, styles)
│   ├── Header + date scrubber
│   ├── Tab navigation
│   ├── Stale data banner
│   ├── Tab content (DESK, DEBATE, POSITIONS, LEDGER)
│   └── Chart Drawer modal
├── Logic class (state management)
│   └── activeTab state + switchTab handler
└── Props (none — full-page component)

support.js                      (Injected by DC runtime)
DESIGN_SPEC.md                  (This file)
```
