# LEARNINGS — equialpha N.E.X.T (next.equialpha.com), 2026-07-14

User: "this is exactly the kind of tool I wanted, but you made ours so complicated." Read the site
live. This is the honest teardown + what we adopt. The headline lesson is SIMPLIFICATION, not more
features.

## What N.E.X.T is (the whole product)
A swing-trading research tool built as **one 4-step linear spine**: **N**avigate · **E**valuate ·
**eX**ecute · **T**rade. Positioning: "The systematic edge for swing traders", "a research tool,
not a tip service — it shows you what's working, you decide what to trade", "**15 minutes, after
market close**", "**No tab-switching across 5 tools. No 2-hour research sessions.**"

The 4 steps (this IS the entire app):
1. **Navigate — Market Tracking.** Market mood/breadth/index → "be aggressive, cautious, or on the
   sidelines before looking at a single stock." One number: "MARKET MOOD Bullish · 72".
2. **Evaluate — Industry Momentum.** 70+ industries → filter to "the 10-15 that matter today." Stage
   tags: **Dull → Accelerating** (they call the transition "the highest-conviction signal").
   INDUSTRY FIRST, stock second.
3. **eXecute — Stock & Industry Rating.** A proprietary **5-way rating combined into ONE number**:
   "TATAMOTORS · 9/12 · Bullish" with 4 chips: Trend 5/5, Industry 2/3, RS 1/2, 52W 1/2. "Decide in
   seconds, not minutes."
4. **Trade — Journal.** Position sizing, open-risk in real time, "SL @ Cost", held-days, P&L heatmap.

"A day with N.E.X.T: Open → See today's Leading Industries → Filter leading stocks → Add to
watchlist → Plan entry/exit/stop." That's it.

## Why it feels right (and ours doesn't)
| N.E.X.T | Ours (current) |
|---|---|
| 4 named steps = the whole app | 7+ tabs + guided rail + Alpha Lab + Debate council + SMF screener + breadth-V2 + live-work |
| ONE rating (X/12) + 4 evidence chips | gate cascade + readiness + alpha rank + SMF score + conviction + debate verdict — many competing "quality" numbers |
| Industry-first (leading industries are the hero) | regime + a 237→0 funnel + debate are the hero; sectors buried |
| 15-min bounded ritual | open-ended, many surfaces, easy to get lost |
| "you decide" — clean inputs, no council | an LLM debate council + alpha research bench up front |
| Market mood = one number + session guidance | XP/MBI/4.5R/breadth-V2/HMM/Fosback... many dials |

## The learnings we ADOPT
1. **Collapse to a 4-step spine as the DEFAULT product.** Navigate (market mood → risk posture) →
   Evaluate (leading industries) → eXecute (one stock rating) → Trade (journal). This is what the
   Guided Daily Flow (`/api/flow/today`) should BE — the whole front door, not a rail bolted onto 7
   complex tabs. We already built the flow endpoint; make it the product, not an accessory.
2. **Industry-first.** Lead with a Leading-Industries watchlist (the 10-15 accelerating groups,
   momentum-ranked, 3 tickers each, stage tag). We HAVE the sector/industry data (ChartsMaze RS,
   industry_metrics, INDUSTRY_TO_SECTOR) — we just don't lead with it. The "Dull → Accelerating"
   transition is a concrete, buildable, high-conviction signal.
3. **One glanceable rating per stock.** A single X/12-style score + a few evidence chips (trend /
   industry / RS / 52W), replacing the pile of competing numbers on our cards. Our gate cascade +
   readiness + alpha + SMF should COLLAPSE into one headline score with expandable evidence — not
   six badges fighting for attention.
4. **One market-mood number + session guidance**, not a wall of dials. XP/MBI/4.5R/breadth-V2/HMM
   become the EXPANDABLE detail behind a single "Mood: Cautious · 42 — trade small / sit out" line.
5. **Bound the ritual: "15 minutes after close."** The default view answers "what do I do today" in
   one screen; everything else is opt-in depth.

## What we have that they DON'T — keep as OPTIONAL depth, never the front door
Debate council, Alpha Lab, SMF/Reactor, Market-Breadth-V2, outcome-resolver, live-work streaming,
promotion-gates. These are real differentiators for a power user — but they are EXPERT DEPTH behind
the simple spine, reached by drilling in, never the entry experience. The mistake was making the
depth the front door.

## Honest self-assessment
Our tool has genuine engine depth N.E.X.T lacks (deterministic risk, journal-expectancy moat,
regime law, real refusal). The failure is PACKAGING: we surfaced all of it at once. N.E.X.T wins on
restraint. The fix is not to delete our depth — it is to hide it behind a 4-step, industry-first,
one-rating, 15-minute default and let the user opt into complexity.

## Suggested next move
A SIMPLIFICATION wave: make the guided 4-step flow the default landing (Navigate→Evaluate→eXecute→
Trade); add a Leading-Industries hero (industry-first) from data we already have; collapse the
per-stock badges into one rating + evidence chips; demote Debate/Alpha/SMF/breadth-V2 to
drill-in-only. Everything else stays, just moves behind the door.

---
## DEEPER REVIEW (logged in, live app — 2026-07-14)

### The "Navigate" (Today's Market) screen — what it actually is
ONE long, well-ordered scroll (not 7 tabs), top-to-bottom:
1. **Index strip** (Nifty 50 / MidSmall 400 / all sector indices, % today) — the ticker.
2. **MARKET MOOD METER = one 0-100 number** (62 · Bullish) with a transparent 3-part breakdown:
   Price Structure 30/30 · Breadth 24/40 · Industry Strength 8/30. Plus "Mood unchanged from last
   session", a **30-DAY MOOD HISTORY**, and a **"How Mood is Calculated"** explainer.
3. **Market Snapshot**: Advancing 474 / Declining 1,458 / Unchanged 80 / 52W H 59 / L 15 / A/D 0.33.
4. **Market Health — % Above EMA 20/50/200** with a 1M/3M/All toggle (50% / 58% / 50%).
5. **52-Week Highs & Lows** — sortable tables (symbol/close/change%/sector).
6. **Top 20 Gainers & Losers**.
7. **Sector Breadth table** (Sector⇄Industry toggle): per group — total / today% / adv / dec /
   **adv% / above20% / above50% / above200%**, sorted, + **TOP-5-by-each-EMA** lists.
8. **NSE Sector Indices**: price / today% / **1W / 1M / 3M**.

### Sharper learnings from the real UI
1. **"Simple" ≠ sparse. It's ONE well-ordered page per step.** Every metric we compute is here too —
   but as one calm top-down scroll with a single hero number, not competing dials across tabs.
2. **ONE mood number with transparent components beats our dial-farm.** Their regime = 62/100 =
   Price+Breadth+Industry, with 30-day history + "how it's calculated". Ours = XP + MBI + 4.5R + HMM +
   Fosback + breadth-V2 all at once. Collapse to: one 0-100 mood, 3 named components, an expander.
3. **The Sector-Breadth table is the industry-first hero** — per-sector adv% + %aboveEMA20/50/200 +
   top-5 lists. We have ALL these inputs (breadth_counts + classify_universe). We just never render
   the scannable per-sector table. This is the single highest-value screen to copy.
4. **Teaching + transparency are built in**, not bolted on: every metric has an "i" / "How
   calculated", plus Onboarding, a "routine video library", "What is Market Mood?", Free Masterclass.
   The tool teaches the process as you use it (our guided-system goal, done lightweight).
5. **It is a pure research tool — NO LLM debate, NO alpha lab, NO SMF, NO forecast bench up front.**
   Just clean data → "you decide what to trade." Our debate council / alpha / SMF as the front door
   is the mismatch with what this user base actually wants.

### Concrete simplification plan (proposed wave — the real fix for "too complicated")
Make our tool a 4-step scroll, industry-first, one-number-per-step; everything else drills in.
- **Navigate (regime):** rebuild the MARKET page to N.E.X.T's shape — one Mood 0-100 (Price/Breadth/
  Industry components + 30-day history + "how calculated"), snapshot row, %aboveEMA toggle, the
  **Sector-Breadth table** (adv% + aboveEMA20/50/200 + top-5), 52wH/L, gainers/losers, indices
  1W/1M/3M. Demote XP/MBI/4.5R/HMM/Fosback/breadth-V2 to an "advanced breadth" drawer.
- **Evaluate (industries):** a Leading-Industries view — 65+ industries scored, filtered to the
  ~10-15 accelerating, "Dull → Accelerating" stage tag, 3 leader tickers each. From data we have.
- **eXecute (stock rating):** collapse our gate-cascade/readiness/alpha/SMF badges into ONE
  glanceable rating (X/12-style) + 4 evidence chips (Trend / Industry / RS / 52W). Deterministic
  risk/plan on drill-in.
- **Trade (journal):** the journal we already have — position size, open risk, SL@cost, P&L heatmap;
  clean it to N.E.X.T's calm layout.
- **Demote to drill-in only:** Debate council, Alpha Lab, SMF/Reactor, Breadth-V2, live-work,
  promotion-gates. Real differentiators, but behind the door — never the entry experience.
- **Add lightweight teaching:** an "i / how calculated" on every number + a short routine walkthrough
  (this is what the guided flow should feel like — help, not a wall).

Keep every engine we built; change only the PACKAGING. The edge stays; the front door gets calm.
