# Research Prompt — turning Manas AI Trading OS into a true edge/alpha generator

> Paste the prompt below into a capable research LLM (Claude Opus, GPT, Gemini
> Deep Research, etc.) and ATTACH `STATE_OF_TOOL.md`. It asks for concrete,
> buildable-from-our-data research on high-accuracy entries, tight risk, profit
> retention, regime awareness, and Indian-market-mechanics awareness.

---

## PROMPT (copy from here)

You are a quantitative trading systems researcher specializing in the **Indian NSE cash-market momentum/swing-trading** domain. I am building a single-user, manual-execution swing-trading decision tool (full state in the attached `STATE_OF_TOOL.md` — read it fully before answering). An independent review scored its *edge* at 3/10: it currently reskins free data. I need your research to turn it into a genuine edge/alpha generator.

**Hard constraints you MUST respect (do not propose anything that violates these):**
- **Rules-first / no black-box scores** — every signal or score must decompose into named, explainable evidence a beginner can inspect. No opaque ML confidence numbers as the trigger.
- **Manual execution only** — the tool proposes; a human confirms every entry/exit (via app or Telegram). No auto-order routing (keeps it outside SEBI's algo framework). Design the human-in-the-loop as a feature, not a limitation.
- **Single-user, public data only.**
- **Data we HAVE:** NSE daily OHLCV + delivery %, ChartsMaze (RS ratings, 26 technical screeners, sector/industry RS, RRG, ASM surveillance flags, per-stock QoQ/YoY EPS/sales/OPM growth, disclosure feeds: order-wins/announcements/bulk-deals/insider/circuit-revision/episodic-pivot, partial market cap), Fyers API (live + intraday candles, websocket).
- **Data we LACK:** full balance-sheet fundamentals (ROE/D-E/P-E/book value/margins), consensus/forward estimates, options data. Do NOT build a thesis that depends on data we don't have; if a technique needs it, say so and give a proxy from what we have.
- **Anti-mashup:** one metric = one number app-wide; one ranked number per screen; no competing scores.

**Research these five areas. For EACH, give: (a) the specific mechanism/rule, (b) exactly which of our data fields computes it, (c) how it stays explainable, (d) how to VALIDATE it works before trusting it (backtest/forward-test design on our data), and (e) a concrete accuracy/quality metric to track. Rank recommendations by expected impact, and flag anything that is theatre.**

1. **High-accuracy ENTRY signals (in-app + Telegram).** How do disciplined NSE momentum traders achieve high hit-rate entries — not by casting a wide net, but by *refusing* most candidates? Cover: multi-factor confluence that actually raises precision (vs the additive score-saturation problem we have), the role of the market regime as a hard gate on which entries even qualify, "fresh-leg" detection (entering near the origin of a move, not extended), gap-acceptance vs gap-rejection for episodic pivots, opening-range and pre-open behavior for next-day entries, and how a live Telegram alert should be structured (what fields, what triggers a push vs a digest, how the human confirms) so it drives action without spam or chasing. What separates a 60%+ setup from a 40% one in *this* market, measurably?

2. **Tight RISK planning & management.** Stop placement that is both tight and valid (day-low / ATR / structure-based), the maximum acceptable stop distance for a swing entry (we currently leak 27% stops), position sizing tied to stop distance and capital risk %, regime-adjusted risk caps, pyramiding rules on pullbacks, and India-specific hazards (circuit limits capping same-day risk-free exits, illiquid-name slippage, ASM/GSM freeze risk). How should the tool *refuse* to log or alert a trade whose risk math doesn't clear a bar?

3. **PROFIT maintenance / drawdown avoidance.** Trailing methods (10/21-EMA, ATR, structure) and when to switch between them, partial booking into strength vs holding, the "sell into weakness on a new trend / sell into strength on extension" heuristic, exit-signal composites (distribution days, MA loss, downside-reversal), and portfolio-level drawdown control (max open risk, max sector exposure, cutting size when the regime turns) so a single-user account never takes a large drawdown. How do we keep more of each winner while getting stopped small on losers — the asymmetry that actually compounds?

4. **Smart REGIME awareness.** Beyond a breadth dial: how should the market regime dynamically govern the whole tool — how many names the feed shows, what stop/size is allowed, which setup types are favored vs suppressed, and when to sit out entirely? Cover breadth/participation, index trend structure, volatility regime, sector rotation (RRG), and "days like today" historical-analog matching against our own history. How is regime state made *actionable and enforced downstream*, not just displayed?

5. **Market-MECHANICS awareness (Indian NSE specifics).** The structural realities that create AND protect edge in India: circuit dynamics (2/5/10/20% bands, circuit-to-circuit momentum, distinguishing information-driven from operator-driven circuits), delivery % as an accumulation/pump-detection signal, ASM/GSM transitions as regime signals, the post-announcement drift in under-covered small caps (the informational edge), bulk/block-deal footprints, and defensive "pump-signature" detection as an exclusion filter. Which of these are the *real* structural edges a retail single-user can exploit that institutions and free sites don't systematically work?

**Cross-cutting question (answer explicitly):** the tool's intended moat is a compounding private journal→outcome→learnings loop (log every taken/skipped setup → T+5/10/20 forward returns → per-setup/per-regime expectancy fed back onto future signals). How should this feedback loop be designed so it genuinely sharpens entry accuracy and risk rules over time WITHOUT overfitting a small sample, and what is the minimum data before its output should be trusted?

**Deliver:** a prioritized, buildable roadmap of the highest-impact changes — each tied to our actual data, each explainable, each with a validation plan — that would move this from a free-data reskin to a tool with a real, measurable edge. Be specific and opinionated; cut anything that is commodity indicator-porn or that we can't validate on our data.

## (end prompt)
