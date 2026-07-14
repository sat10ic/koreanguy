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
