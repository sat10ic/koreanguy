# WAVE G — "Basic features of a trade-management tool" (user complaint list, 2026-07-10)

User's words, itemized. Each item ships with a done-test. Nothing marked done until the
rendered UI answers the user's sentence.

## G1 — Debate breadth + living watchlist (backend)
> "why is the debate done on only one stock... is only one stock good enough in the entire
> 500 stock universe?... what kind of tool doesn't suggest multiple stocks of interest in
> near term in a watchlist tab, with the llm agents discussing on a daily (later hourly)
> basis whether to promote, demote, or send signals"
- Shortlist floor: debate ALWAYS covers min(10, available) names — gate survivors first,
  then best near-misses from refusals (ranked by fewest failed gates), each tagged
  `tier: PASSED | NEAR_MISS(failed_gate)`. Chair verdicts persist for all.
- New table `agent_watchlist(scan_date, symbol, tier, status, prev_status, reason)` —
  status ∈ PROMOTE/HOLD/DEMOTE/DROP, computed nightly by chair from verdict deltas
  vs previous night. This is the "living" list.
- Chart PNGs generated for EVERY debated name (fixes "why are pngs missing").
- DONE-TEST: run night → ≥10 debated (or all available), watchlist rows with status
  arrows, PNGs exist for each.

## G2 — Beginner explainers everywhere (frontend)
> "what's the point of MBI and XP... when nobody knows what it means... meaning of today's
> laws... activity stream... all the terms used in the debate screen"
- Every term chip/tile gets a hover-or-tap glossary: MBI, XP, R20/R50, day-color, regime
  modes, LAW fields, gate names, conviction, spread, struck, tier, each activity-stream
  stage. One shared GLOSSARY dict (frontend), plain English, one sentence + "why you care".
- Every panel keeps one [B] caption that interprets TODAY's value ("XP 10.2 = weak
  readiness; sit mostly out"), not just defines the term.
- DONE-TEST: click/hover any term on DESK/DEBATE → explanation appears; screenshots.

## G3 — MARKET tab restructure
> "Didn't I ask for a focus on sectors and themes, with the broad indices only being an
> indicator... point of heatmap and indice values of the same thing... movers and big
> delivery show indices instead of stocks... point of the blue circles in deals"
- Hero = sectors & themes (treemap + per-sector drilldown to stocks w/ RS). Broad indices
  shrink to one compact strip (NIFTY/BANKNIFTY/MIDSML/VIX). Kill the duplicate full
  indices grid.
- Movers/Big-delivery panels: STOCKS ONLY (bug: index rows leaking from source query).
- Deals/flows: labeled cards (symbol, qty, buyer/seller, % of mcap) — no anonymous dots.
- DONE-TEST: screenshot vs this list; movers shows tickers not "Nifty ...".

## G4 — Positions = manage + LLM coach daily
> "what's the point of the holdings screen when there's no option to manage/journal the
> trade... no LLM explaining in simple terms when to keep holding, how long, where to
> apply the SL on a daily basis, when to exit"
- POSITIONS tab: per-position coach card surfacing the nightly coach output (backend
  already computes): verdict HOLD/TRIM/EXIT/MOVE_STOP, today's SL level, plain-English
  why, expected hold horizon. Manage actions: edit SL/qty, close (writes journal + exit
  reason tag), add position.
- DONE-TEST: open position shows coach line + SL number + buttons that write to DB.

## G5 — Pine indicator ports on charts + fed to LLMs
> "what happened to lightweight TV charts with these indicators... which the LLMs also
> need to be able to understand to make the calls"
- Port (python, engine/): Burst Power score, Pocket-Pivot/blue-streak, Persistency counts
  (10/21/50/200 EMA w/ decisive exit), Mswing (stock vs NIFTYMIDSML400), RMV 0-100,
  SS-RVOL, Purple Dot. Sources: user's Pine files in Downloads/book/momentum-project/book/.
- Chart drawer: lightweight-charts candles + these overlays/panes per debated symbol.
- context_pack: numeric block per shortlist name (burst_power, persistency_10/21,
  mswing_vs_index, rmv, rvol, pocket_pivot_streak) so the models argue WITH them.
- DONE-TEST: chart opens from DEBATE card w/ indicators; debate prompt contains the block;
  ports snapshot-tested vs hand-computed fixtures.

## G6 — Visible quant/ML layer (layman-explained)
> "no indication of any ML models being used to support the tool at all"
- Surface expectancy/base-rates + outcome stats as "WHAT THE NUMBERS SAY" panel (n, hit
  rate, median R per setup family) with plain-English captions; roadmap panel for Markov/
  regime-analog once ≥150 samples (trust ladder). No fake ML claims.

Order: G1+G3 first (parallel), then G2+G4, then G5, then G6.
Rule reaffirmed: every wave-close = feature-vs-THIS-FILE + rendered screenshots.

## G5 addendum (user, 2026-07-10): Simple Volume must be EXACT
> "remember to use simple volume indicator exactly as it is supposed to work, I could see
> issues last time"
- Port design/pine/simple vol.txt semantics verbatim: up/down bar uses PREV CLOSE by
  default (not open); pocket pivot = up bar whose volume > max DOWN-bar volume of last 10
  bars (down bars only!); bear pocket pivot mirrored vs max UP volume; dry-up = vol <=
  0.20 * SMA50(vol); color priority dry > bull PP > bear PP > high-down > high-up > noise;
  blue-streak = N consecutive bull PPs. Snapshot-test against hand-computed fixtures
  covering: down-bar-max window with zero down bars (na), first-bar edge, streak break.
- DONE-TEST: fixture parity table in the test file, each rule cited to the Pine line.

## G7 — AVWAP as an LLM-decided anchor (user, 2026-07-10)
> "shouldn't a LLM also be deciding AVWAP position, and acting upon the stock relevant to
> that... there needs to be very solid material on AVWAP which it can just refer to and
> follow (needs to be relevant for Indian market)"
- New reference doc manas_os/design/agents/AVWAP_INDIA.md (lens-style, like LENS_*.md):
  when to anchor (earnings gap / breakout day / IPO listing day / major swing low /
  high-volume institutional day / block-deal day), how price-vs-AVWAP reads (support,
  reclaim, loss), Indian-market specifics (circuit days, bulk-deal days as anchors,
  delivery%-weighted significance, T+1 settlement context), entry/exit actions per state.
  Grounded in Brian Shannon's AVWAP methodology adapted to NSE; every rule actionable,
  no vague prose.
- Debate/vision integration: context_pack includes per-name AVWAP block (anchor type,
  anchor date, price vs AVWAP %, reclaimed/lost N days ago) computed by the existing
  engine avwap_auto_anchor; the LLM may OVERRIDE the auto anchor (choose from the last 3
  candidate anchors listed) and must state which anchor and why, per AVWAP_INDIA.md.
  Deterministic engine stays the fallback + validator (anchor must be a real event bar).
- DONE-TEST: doc exists + cited in prompts; debate output contains avwap_anchor choice +
  action; validator rejects fabricated anchor dates.
