# BINDING CONSTRAINT — Method-first IA (user order, 2026-07-11)

User verbatim (2026-07-11, after repeated flags): "i asked fow a complete tailoring of the
tool, in a beginner friendly manner..you have retained the same screens and views since the
start... the setups/llms screens is super complex and confusing, and no sign of all the
things like scanning, entry conditions, position sizing and risk management, exit ecreens
at all.. there has been so much step by step instructions for each of these given by both
tradetm and manas arora... but you have just kept on with the same views."

## The rule
The tool's screens must be organized around the TRADER'S WORKFLOW as TradeTM/Arora teach it
— SCAN → ENTRY → SIZE & RISK → MANAGE → EXIT — not around system internals (pipeline,
debate, gates). Every screen walks the method's own step-by-step instructions in beginner
language. LLM debate/model output is EVIDENCE behind verdicts, never the primary surface.

## Done-test (per standing wireframe-fidelity rule)
- WIREFRAMES_V3.md exists with ASCII per screen; every element traces to a corpus rule
  (cite) or a user request (quote). Screenshot-vs-ASCII element-for-element.
- A beginner can execute one full trade cycle (find → plan → size → enter → manage → exit)
  reading ONLY the screens, never a doc.
- "Same screens as the start" must be false: the 5-tab system IA (DESK/DEBATE/MARKET/
  POSITIONS/LEDGER as currently composed) is replaced, not reskinned.

## Standing sub-orders folded in (same turn)
- Live visual progress: real-time progress bars for pipeline runs (stage x/26, ETA,
  "data live ~19:25"), not text-only stamps.
- Charts default: candles + volume + 10/21 EMA + purple dots (user kept PD explicitly);
  e50/stage/shakeout markers behind toggle; no inline e10/e50 text labels.
- LLM inputs must include stage, purple dots, finallynitin volume markers so calls are
  taken from the same picture the user sees.
- HOW TO TRADE THIS and all guides: layman rewrite — one plain sentence per step + why +
  exact broker action; jargon only with inline explanation.

## Amendments (user, 2026-07-11 ~02:40)
1. LLM workflow SHOWN, debate screen STAYS — only language + views become beginner
   friendly. Do not demote debate to hidden evidence.
2. SCAN/WATCHLIST screen: a living watchlist that the LLMs add stocks to / remove stocks
   from (with visible reasons per add/remove). Not just a nightly static list.
3. THE FILTER IS THE DEFECT (user, again, verbatim-class): "if you're only shortlisting to
   1 stock out of 2000, when there are good moves according to classic swing trading
   patterns like EP, IPO, reversals, flags etc.. according to high ADR and RS, there is
   something inherently wrong with your initial filtering." ORDER: discovery bucket feeds
   the LIVE pool (WAVE_M M2), hard gates (RS floor, 52wH nearness, regime family-kill)
   become scored objections (M3). Tradability + risk gates stay hard; NO_TRADE stays hard;
   LOCKED money math unchanged. The recall label-gate no longer blocks this — user
   overrode: breadth first, refusal by evidence not by silent floor.

## The flow (user verbatim, 2026-07-11 ~09:00 — THE product spine, supersedes V3 IA)
"usually the traders have scanners, from which they shortlist few stocks after observing
their long term price behaviour, then move them to a shortlist... based on market
conditions, regime trends, and again observing price and volume on charts, they take a
call to enter, having their own position sizing rules... again based on the stock's
movement and market conditions, they adjust their stops, and try to sell while still on
strength..trying to time it well."
Also: "what's the difference between beginner and expert except journal screen? where is
the page to run different scans as per the traders? LLm/Debate screen? shortlist screen...
charts view?" — beginner/expert must differ visibly on EVERY screen; named trader scanners
(incl ChartsMaze trader templates) must be a real page; shortlist is its own persistent
screen; charts are a first-class split-panel view everywhere.
Agreed direction (Fable proposal, pending user tweaks): nav = MARKET, SCANNERS, SHORTLIST,
DEBATE, POSITIONS, JOURNAL (+ per-stock TRADE PLAN route; chart panel on every stage;
staged LLM roles Scout/Curator/Council/Sizer/Coach; weekly-first chart on scanner hits).
V3 wireframes to be superseded by V4 on this spine.

## Amendment (user, 2026-07-11 ~09:30) — screener + push-to-debate
User shared top-gainers screenshot (IONEXCHANG +16.4%, GODREJIND +16.3%, J&KBANK +14.4%,
MUTHOOTMF, EMSLIMITED, KALYANKJIL, EIEL, SUMICHEM, LLOYDSENGG, EXICOM, TANLA, ... high ADR):
"some more strong stocks not considered by the tool at all..can't we have a screener option
like Chartink.. from which we can push the stock to the debate panel to the llms? on top of
whatever it itself screens"
ORDERS:
1. Chartink-style SCREENER BUILDER on the SCANNERS tab: stackable conditions over existing
   per-stock metrics (close, %change, volume, ADR, RS, %off low/high, EMA position, purple
   dots, delivery), save-as-named-screen. Preset: TODAY'S MOVERS (top %change + volume +
   ADR) — day-1 bursts feed D2 watch per doctrine.
2. PUSH TO DEBATE from any screener row + universal symbol search: on-demand LLM debate of
   any symbol w/ full context pack; card lands on DEBATE tab marked "user-pushed". Tool's
   own screening continues underneath.
Evidence 07-10: 10/17 screenshot names already on agent_watchlist, IONEXCHANG in bucket as
d2_episodic — periphery sees them, surfaces don't show them. Surfaces are the gap.
