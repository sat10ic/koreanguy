# Manas OS — AI Agentic Workflow Architectural Audit

---

## A. Preventing Agentic Risks

### A1. Overfitting to Recent Price Action

The core danger: your LLM sees only the last 20 bars and a snapshot of fundamentals. It has no memory of how often this exact pattern failed historically, so it pattern-matches on recency.

**Concrete mitigations:**

| Layer | What to do | Why it works |
|-------|-----------|--------------|
| **Regime context injection** | Pass the current market regime (RISK_OFF / SELECTIVE / RISK_ON) *and* how long the regime has been active into the prompt. Add a field like `regime_age_days: 3` | During transitional regimes (first 5 days of a new RISK_ON after a correction), breakout failure rates are 2-3× higher. The LLM needs this context to discount recent bullish action. |
| **Base-rate anchoring** | Prepend a short "base rates" block to the system prompt: *"Historical win rate for breakouts in SELECTIVE regime: 38%. For pullbacks: 52%. Adjust confidence accordingly."* | Forces the LLM to reason from population statistics rather than just the single chart in front of it. Without this, it will default to narrative reasoning ("this looks strong") which is exactly overfitting. |
| **Multi-timeframe input** | Include a 50-day summary (weekly closes, not just daily) so the LLM can see whether the 20-day action is a fresh leg or the tail end of an extended move. | A stock up 40% in 20 days looks bullish in isolation. With 50 days of context, the LLM can see it's 60% above the 50-EMA — an extension, not an entry. |
| **Mandatory "what could go wrong"** | Structure the prompt so the Bear agent must list at least 2 specific risks with probability estimates before the Risk Manager can issue a TAKE. | This is a debiasing technique. LLMs anchored on bullish narratives will skip superficially over bear cases unless the schema forces depth. |

### A2. Look-Ahead Bias in Backtests

This is the most dangerous risk for any LLM-in-the-loop system, because **the LLM's training data already contains historical market outcomes**.

**Hard rules:**

1. **Date-fence all inputs.** Every piece of data passed to the LLM must have a `as_of_date` field. The pipeline must enforce `as_of_date <= backtest_date` programmatically — not by trusting the LLM to ignore future data.

2. **Strip model knowledge.** Add an explicit instruction to the system prompt during backtests:
   ```
   IMPORTANT: You are evaluating this stock as of {date}. You must NOT use any 
   knowledge of what happened to this stock or the broader market after {date}. 
   If you recognize this stock from your training data, base your analysis ONLY 
   on the numerical data provided below.
   ```
   This is necessary but **insufficient** — the LLM may still leak. Therefore:

3. **Blind the symbol name.** During backtests, replace `AARTIIND` with `STOCK_A`. This prevents the LLM from recalling specific price histories from its training corpus. This is the single most effective debiasing technique.

4. **Never backtest with news/sentiment.** If you add news feeds later, they must be sourced from a timestamped archive (e.g., stored RSS dumps), never from live search. The LLM's internal knowledge of "what happened next" after a news event is the most common source of look-ahead contamination.

### A3. Hallucination Guardrails

The LLM will confidently output `entry: 712.65, stop: 700, target: 774` — and these numbers may be internally inconsistent or violate your risk rules. **You cannot trust the LLM's arithmetic.**

**Programmatic post-validation layer** (implement in Python, not in the prompt):

```python
def validate_trade_params(entry, stop, target, max_stop_pct=0.08, min_rr=2.5):
    """Hard mathematical guardrails applied AFTER LLM output parsing."""
    errors = []
    
    # Stop cannot be above entry (for longs)
    if stop >= entry:
        errors.append(f"Stop {stop} >= entry {entry}")
    
    # Max stop-loss percentage
    stop_pct = (entry - stop) / entry
    if stop_pct > max_stop_pct:
        errors.append(f"Stop distance {stop_pct:.1%} exceeds {max_stop_pct:.0%} cap")
    
    # Minimum reward-to-risk
    risk = entry - stop
    reward = target - entry
    rr = reward / risk if risk > 0 else 0
    if rr < min_rr:
        errors.append(f"R:R {rr:.1f} below minimum {min_rr}")
    
    # Target must be above entry
    if target <= entry:
        errors.append(f"Target {target} <= entry {entry}")
    
    # Sanity: stop and target within 20% of entry
    if abs(target - entry) / entry > 0.20:
        errors.append(f"Target {target} is >20% from entry — likely hallucinated")
    
    return errors
```

**If validation fails**: Do not silently fix the numbers (that creates a false audit trail). Instead, either:
- **Reject the candidate** and log `"LLM output failed risk validation"`, or
- **Re-query once** with the specific error appended: `"Your stop of 650 is 8.7% below entry. Maximum allowed is 8%. Revise."` — but cap retries at 1 to avoid cost spirals.

---

## B. Hybrid Integration: Legacy Deterministic + LLM Agent

There are two viable architectures. Here is the honest trade-off:

### Option 1: **Math generates → LLM filters** (Recommended)

```
Universe (3,500) → Deterministic cascade (regime/tradability/trend/fresh-leg) → ~15-30 candidates
    → LLM debate (score, rank, Bull/Bear, narratives) → Top 3-5 picks with explanations
```

| Dimension | Assessment |
|-----------|-----------|
| **Precision** | High. The math gates are provably correct — a stock either passes the 50-day MA test or it doesn't. No hallucination risk at this stage. |
| **Recall** | Lower. Hard thresholds will miss edge cases (stock 0.5% below trend-template but about to break out). |
| **Cost** | Low. LLM only evaluates 15-30 pre-screened names, not 3,500. |
| **Explainability** | Excellent. You can trace exactly *why* a stock reached the LLM (which gates it passed) and then *why* the LLM liked or rejected it. |
| **Hallucination surface** | Minimal. The LLM scores and narrates but doesn't calculate entries/stops — the math does that. |

### Option 2: **LLM generates → Math validates**

```
Universe (3,500) → Basic liquidity filter → Top 10 RS leaders
    → LLM debate (full autonomous: TAKE/SKIP + entry/stop/target) → Math validates outputs
```

| Dimension | Assessment |
|-----------|-----------|
| **Precision** | Variable. Depends entirely on model quality and prompt engineering. |
| **Recall** | Higher. The LLM can recognize novel setups the deterministic cascade would miss. |
| **Cost** | Higher. Sending 10 full symbol contexts with 20 bars each is a large prompt. |
| **Explainability** | Weaker. You get narratives, but the *why* is opaque — the LLM's internal reasoning isn't auditable. |
| **Hallucination surface** | Large. The LLM calculates entry, stop, target, quantity — all subject to arithmetic errors. |

### Recommendation

**Use Option 1 (Math → LLM) as your production pipeline.** The LLM's strength is *narrative reasoning and pattern recognition across multiple factors simultaneously* (combining technicals + fundamentals + regime in a way hard-coded rules can't). Its weakness is *arithmetic and threshold precision*. Play to the strengths.

Concretely:
- Keep your deterministic cascade for gates 1-5 (regime, tradability, trend-template, fresh-leg, participation).
- Let the deterministic math compute entry, stop, target, and position size.
- Use the LLM *only* for: (a) scoring/ranking the 15-30 survivors, (b) generating Bull/Bear narratives for the UI, and (c) flagging hidden risks the math can't see (e.g., "this stock has an upcoming earnings date in 3 days — consider waiting").

---

## C. Component Adoption from Reference Projects

### High-Value Adoptions

| Component | Source Project | Effort | Impact | Recommendation |
|-----------|---------------|--------|--------|----------------|
| **Learn-from-losses database** | RakshaQuant | Medium | **Very High** | **Adopt.** Store every TAKE decision with outcome (win/loss, R-multiple, holding period). After 50+ closed trades, inject a summary into the system prompt: *"In the last 50 trades, breakouts in SELECTIVE regime had a 34% win rate vs 52% for pullbacks. Your stop was hit within 2 days on 60% of losses."* This is the single highest-ROI improvement — it turns your LLM from a static reasoner into an adaptive one without fine-tuning. |
| **Post-validation math layer** | (Internal) | Low | **Very High** | Already discussed above in A3. Non-negotiable. |
| **Symbol blinding for backtests** | (Novel) | Low | **High** | Replace ticker names with anonymous IDs during replay to prevent training-data leakage. |

### Medium-Value Adoptions

| Component | Source Project | Effort | Impact | Recommendation |
|-----------|---------------|--------|--------|----------------|
| **Context compression** | Vibe-Trading | Medium | **Medium-High** | When your symbol count grows beyond 10, compress the per-symbol context (20 bars × 8 fields = 160 data points per symbol) into a structured summary: `{trend: "up", ema_alignment: "10>21>50", distance_from_50ema_pct: 7.2, volume_trend: "rising", stage: 2}`. This cuts token cost by ~70% and actually *improves* LLM reasoning by removing noise. |
| **News sentiment layer** | Artha-Analytics | High | **Medium** | Useful but dangerous. NSE-specific news sources are noisy (MoneyControl, ET) and hard to parse reliably. If you add this, start with **corporate actions only** (board meetings, earnings dates, stock splits) from BSE announcements — these are structured and machine-readable. Avoid free-text news until you have a validated sentiment model. |
| **Persistent session logs** | Vibe-Trading | Low | **Medium** | Log every LLM call (prompt, response, latency, token count, parsed result, validation outcome) to a `scan_agent_logs` SQLite table. Essential for debugging and for feeding the learn-from-losses loop. |

### Low-Value / Premature Adoptions

| Component | Source Project | Why Not (Yet) |
|-----------|---------------|---------------|
| **Git-commit prompt optimizer** | atlas-gic | Premature. You need 200+ closed trades with outcomes before prompt optimization has enough signal. Running it now will optimize on noise. Revisit after 6 months of live trading. |
| **Deep RL pattern detection** | AI-Trader | Overkill for an EOD swing system. RL shines in high-frequency intraday execution, not in once-daily batch scans. The engineering cost is enormous and the edge is unproven for your timeframe. |
| **Multi-call swarm (LangGraph)** | TradingAgents, NSETradeAgents | Over-engineered for a local CLI tool. Your single-call debate already captures 80% of the value. Multi-call swarms make sense for institutional systems with dedicated GPU inference — not for a personal tool paying per-token on OpenRouter. |
| **Parallel bull/bear agent calls** | india-trade-cli | Conceptually identical to what you already do in-prompt. Splitting into parallel API calls doubles cost and latency with marginal quality gain for a 10-symbol batch. |

---

## Implementation Roadmap

```
Week 1:  Post-validation math layer (A3) — non-negotiable safety net
Week 2:  Hybrid pipeline (B, Option 1) — math generates, LLM scores/narrates
Week 3:  Persistent agent logs table + learn-from-losses schema
Week 4:  Context compression for prompt efficiency
Month 2: Corporate actions feed (earnings dates, board meetings)
Month 6: Git-commit prompt optimizer (once you have 200+ trade outcomes)
```

---

> **Bottom line**: Your single-call debate architecture is a pragmatic and defensible choice for a local EOD tool. The critical gap is not in the *agent orchestration pattern* — it's in the **absence of post-output validation and outcome feedback loops**. Fix those two, and the system becomes genuinely useful. Without them, you're trusting an LLM to do arithmetic and learn from nothing — which is exactly where LLMs fail.
