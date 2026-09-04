# External Alpha Adoption Map

Date: 2026-07-11 · Branch: `emergent` · Status: research review, read-only pass

Governing rule: `design/ALPHA_LEARNING_CONSTRAINTS.md` §External projects — adopt
**concepts**, never wholesale code or foreign-market assumptions. SQLite records
(`alpha/schema.py`) remain canonical; no external service becomes a source of
truth. Every adopted technique carries an explicit "how we test it on NSE data"
answer per the Research discipline section (point-in-time construction, Indian
costs/circuits/ASM-GSM, walk-forward, baseline comparison, minimum sample,
frozen experiment record, shadow before live influence).

Our stack anchors referenced below:
- `alpha/` — `features.py` (point-in-time features), `memory.py`
  (`record_decision` / `resolve_outcome` / `recall_analogues`), `pipeline.py`
  (`run_features` / `run_memory`), `schema.py` (tables `alpha_feature_snapshots`,
  `alpha_predictions`, `alpha_experiments`, `alpha_model_registry`,
  `decision_memories`, `decision_memory_outcomes`, `memory_analogues`),
  `diagnostics.py` (`bayesian_setup_expectancy`, `competing_risk_summary`,
  `block_bootstrap_diagnostics`).
- `agents/debate.py`, `agents/chart_behavior.py`, `agents/context_pack.py`.
- `scanner/` expectancy layer.
- Wave items 3–5 in `design/handoffs/HANDOFF_CODEX_ALPHA_BEHAVIOUR_WAVE1.md`:
  **W3** setup-family/event outcome resolver (trigger availability, next-open
  slippage, MFE/MAE, +1R/+2R/stop timing, gaps); **W4** ranking/survival
  training behind history + leakage + cost gates vs simple baselines; **W5**
  20+ live shadow sessions + calibration/stability audit before any capped tilt.

---

## 1. Miasyster/QuantGPT

**What it actually is** (verified via repo page): agent-driven alpha-factor
mining engine for the **China A-share** market. Claude drives 15 MCP tools;
custom expression parser (60+ operators, cross-sectional vs time-series
separated), rank-grouping backtester, evolutionary iteration
(`mutation_engine.py`, `crossover_engine.py`, `meta_evolution.py`),
`anti_overfit.py` + `rolling_validator.py`, React dashboard. Data via
baostock/akshare. 393★, MIT, Python 67.7% / TS 24.2% / Rust 6%.

**Honesty flags**: "QuantGPT Cloud" independent validation is an external
closed platform (`quant-gpt.com`) with no visible code; the three "validated
WorldQuant BRAIN factors" are screenshots, not reproducible; the dual-LLM
(DeepSeek) cross-review and knowledge-base persistence read partly as design
intent. Real engineering exists (parser, backtest, walk-forward), but the
autonomy/validation story is over-claimed. Treat as a hybrid: substantive
mechanics, aspirational marketing.

**Adopt (concepts)**

| # | Mechanism | Maps to | NSE validation test |
|---|---|---|---|
| Q1 | **Frozen experiment KB including failed paths** — every hypothesis, its expression, its evaluation and its failure reason persisted so failures are never re-discovered and selection bias is visible | `alpha_experiments` + `alpha_model_registry` in `schema.py`: add `hypothesis_text`, `verdict`, `failure_reason`, `frozen_at` semantics; surface in Alpha Lab | Re-run wave-K style feature studies through the registry; done-test = a repeated idea is auto-flagged as a rediscovery, and the count of failed vs promoted experiments is queryable (guards constraint §Research-6) |
| Q2 | **Multi-layer anti-overfit battery as a promotion gate** — several statistical tests + walk-forward + neutralised simulation must ALL pass before a factor is "found" | **W4** training gates: extend `diagnostics.py` with a `promotion_gate()` battery (walk-forward IC decay, deflated-Sharpe/placebo shuffle, regime/sector subgroup stability, cost-adjusted expectancy vs RS/residual-momentum baseline) | On the 3–5y NSE panel (after W1 history extension): candidate ranking model must beat the simple RS baseline out-of-sample in ≥2/3 walk-forward folds after Indian costs, and survive a label-shuffle placebo; anything failing stays shadow |
| Q3 | **Structured failure diagnosis loop** — when an experiment fails, record *which* gate killed it and the diagnostic detail, feeding the next hypothesis | `alpha/diagnostics.py` + pipeline `_log`: per-experiment gate-by-gate verdict rows rather than one pass/fail | Backfill: run the existing sector-downside model (currently failing its baseline, per wave-1 ledger) through the loop; done-test = the record states the failing gate and the magnitude, not just "failed" |
| Q4 | **Independent cross-review of conclusions** — a second, differently-prompted model must independently score a promotion claim before it stands | `agents/debate.py` chair adjudication: add a reviewer pass (separate prompt/context, ideally separate model) for experiment-promotion claims only (cheap; not per-stock) | Take 10 historical experiment write-ups, inject 2 with deliberately leaked features; done-test = the cross-reviewer flags the leaked ones |

**Do NOT adopt**: baostock/akshare A-share data stack; WorldQuant BRAIN
submission workflow; "QuantGPT Cloud" external validation (violates SQLite-
canonical rule); the evolutionary mutation/crossover engines as-is — an
expression-mutation factory without our gates is an overfitting machine and
contradicts the behaviour-first alpha hierarchy; any of its factor library as
strategy content.

**Licence**: MIT — no issue for concept or even code reuse in a private tool.

---

## 2. dfkai/xtquantai

**What it actually is** (verified): NOT a research platform — it has pivoted
(v0.2.0, Jun 2026) into an **Agent Skills collection for QMT** (China's
Windows-only quant terminal). One production skill, `qmt-inner-backtest`:
turns a strategy description / research PDF / screenshot into a QMT backtest
script, with factor-logic interpretation, Barra-style processing, and an
**anti-future-function (look-ahead) check**. Three further skills are
"planning" only. 145★, MIT, Python.

**Adopt (concepts)**

| # | Mechanism | Maps to | NSE validation test |
|---|---|---|---|
| X1 | **Research-to-backtest specification step** — a structured intermediate spec (universe, signal definition, timing convention, cost model, evaluation windows) is generated and reviewed BEFORE any backtest code runs | New lightweight spec record attached to each `alpha_experiments` row; the debate/lab flow writes the spec, `pipeline.py` executes only from a spec | Author specs for 3 known TradeTM/Arora setups; done-test = a second reader (or cross-reviewer, Q4) can tell from the spec alone whether next-open vs same-close execution is assumed — the ambiguity the spec exists to kill |
| X2 | **Automated look-ahead / anti-future-function checklist** — mechanical scan of feature code for future references (e.g. using day-T close in a day-T decision, unshifted rolling windows, post-event fields) | `alpha/features.py` `compute_daily_features` + **W1** point-in-time universe checks: a `leakage_audit()` in `diagnostics.py` that shifts inputs by one day and asserts prediction invariance for decision-time features | Perturbation test on the real panel: recompute all features with data truncated at T-1; any feature whose decision-time value changes is leaking; done-test = zero leaking features before W4 training starts |
| X3 | **Document-grounded strategy interpretation** — the skill reads a practitioner document and extracts testable rules | Already our pattern (`design/knowledge/` TradeTM/Arora/StocksGeeks digests feeding `agents/context_pack.py`); adopt only its discipline of emitting *testable* rule statements with explicit parameters | For one nuance doc section, emit rules and confirm each has a machine-checkable predicate; done-test = rule fires correctly on 5 hand-labelled historical NSE charts |

**Do NOT adopt**: QMT runtime, Windows terminal execution model, China
universe/instrument handling, Barra-CN factor conventions, the skill-package
distribution mechanism. All explicitly out of scope per the constraints doc.

**Licence**: MIT. **Thinness**: real but narrow — 1 of 4 skills shipped;
value to us is the spec + leakage-check pattern only.

---

## 3. "Awesome Vibe Trading Bot.MD" (gameworkerkim/vibe-investing)

**What it actually is** (verified against the raw file, ~51KB / 976 lines):
a **Korean-language comparative research report** by an independent researcher
(v2.0, updated 2026-06-10) inside `gameworkerkim/vibe-investing` (276★, MIT,
active). It compares 9 traditional crypto bots (Freqtrade, Hummingbot, Jesse,
Gekko[archived], …) and 8 AI/LLM bots (TradingAgents, FinRL, FinGPT, FinRobot,
OctoBot, Sibyl, LLM-TradeBot, qrak/LLM_trader), with pros/cons tables and an
honest 10-item red-flags section (hallucination, cost blowup, look-ahead bias,
single-LLM overconfidence, backtest impossibility). Entirely crypto-focused;
zero NSE/equities content; it references **none** of our other four target
repos (grep of the full raw text: zero hits).

**Adopt (concepts)**

| # | Mechanism | Maps to | Validation test |
|---|---|---|---|
| V1 | **Two-tier cost-aware model routing** — cheap/local model does first-pass filtering; only the frontier model gets final judgment | Scanner nightly output → tier-1 cheap-model behaviour triage; `agents/debate.py` chair adjudication (expensive model) runs only for the shortlist that survives tier-1 | Agreement study on ~100 historical candidates: tier-1 triage vs full-pipeline verdicts; done-test = bounded false-negative rate on eventual TAKE/strong-WATCH decisions at a large cost reduction |
| V2 | **Verdict caching per identical market state** — don't re-pay the LLM for an unchanged chart | Cache debate/behaviour outputs keyed on (symbol, date, setup-signature/context-pack hash) in SQLite | Replay a week of nightly runs; done-test = cache hits only where the context pack is byte-identical, with zero verdict drift on hits |
| V3 | **Mode discipline** — deep/extended reasoning reserved for research and backtesting; production nightly runs use standard mode | Alpha Lab experiment runs vs nightly `pipeline.py` + debate invocations | Cost ledger comparison over 2 weeks; done-test = nightly cost flat while research-phase quality is unchanged |
| V4 | **Reference index** — keep the catalogue as a watchlist for future external reviews (FinGPT/FinRobot/TradingAgents in one place) | No stack contact; docs bookmark only | None needed |

Its rough cost ladder (single-stock daily ~$15–50/mo; multi-agent debate
~$500–2,500/mo) is a sanity check only — do not import the numbers.

**Do NOT adopt**: all 17 bot designs/strategies (crypto bots — market-making,
RL execution, LSTM hybrids — constraints doc: "not a validated alpha source");
"LLM sentiment → RL trading signal" pipelines (the doc itself flags this as a
structural risk); any of its cost figures as planning inputs.

**Licence**: MIT. **Verdict**: real and current, but a survey document — the
only mechanisms worth taking are the routing/caching/mode-discipline patterns
above.

---

## 4. tradermonty/claude-trading-skills

**What it actually is** (verified, including SKILL.md sources): real, large,
actively maintained (commits through 2026-07-11; 2.3k★, MIT, Python). 70+
Claude skills across market regime, portfolio, swing screening, trade
planning, **trade memory/journaling**, strategy research, plus workflows and
skillsets. Confirmed journal/postmortem machinery in `trader-memory-core`:
thesis lifecycle `IDEA → ENTRY_READY → ACTIVE → CLOSED/INVALIDATED`,
append-only `status_history`, immutable `raw_provenance`, per-thesis
postmortems with MAE/MFE. No thesis-vs-antithesis debate structure exists
there — ours is richer on that axis.

**Adopt (concepts)**

| # | Mechanism | Maps to | NSE validation test |
|---|---|---|---|
| T1 | **Append-only status-history ledger** — every thesis state transition is appended, never overwritten | `alpha/memory.py` / `decision_memories`: add a transition-log table keyed to our debate states (WATCH→TAKE→resolved etc.) so decision evolution is auditable | Replay N resolved decisions; done-test = every state change has a timestamped row; any overwrite is the defect this prevents |
| T2 | **Immutable `raw_provenance`** — the exact screener/context payload frozen at thesis creation, separate from evolving fields | `agents/context_pack.py` output stored verbatim in `decision_memories.evidence` at debate time (already partially true — verify, don't assume) | Pick 10 historical decisions; done-test = the exact context pack that fed the original debate is reproducible byte-for-byte from SQLite |
| T3 | **Structured postmortem with MAE/MFE + lessons field** | **W3 outcome resolver directly**: the resolver's MFE/MAE, +1R/+2R/stop-timing outputs populate a per-decision postmortem record; lessons grounded in TradeTM/Arora invalidation language, fed back through `recall_analogues` | Generate postmortems for the last 20–30 resolved NSE decisions; a human independently labels failure modes for 10; done-test = substantial overlap between human labels and resolver+diagnostics output |
| T4 | **Verdict-gate output contract** — pre-trade discipline gate returns hard verdicts (OK / WARN / REVIEW_REQUIRED / RULE_VIOLATION / COOL_DOWN), not advice prose | `agents/debate.py` final adjudication: emit a typed verdict enum alongside the thesis, so downstream (sizing, UI) consumes structure, while deterministic gates remain the actual governor | Run the verdict contract over historical decisions where a rule violation was flagged post-hoc; done-test = the structured gate would have surfaced it pre-trade |
| T5 | **Performance digest by thesis source** — expectancy/profit-factor/R-multiples broken out by category | `alpha/diagnostics.py`: aggregate resolved outcomes by *methodology lens* (TradeTM vs Arora vs StocksGeeks vs reversal) and setup family, matching the UI-evidence requirement "which teacher/execution lens generated the thesis" | Run on existing decision history once W3 lands; done-test = per-lens expectancy with sample sizes and shrinkage (reuse `bayesian_setup_expectancy`); a systematically weak lens is a real, actionable signal |

**Do NOT adopt**: FMP/FINVIZ/Alpaca US data integrations; US-calibrated
regime/circuit-breaker thresholds (re-derive from NSE breadth/volatility);
its screener/signal skills (generic, not TradeTM/Arora/StocksGeeks-grounded —
importing them violates the anti-mashup rule); the `.skill` packaging/upload
mechanism (irrelevant; SQLite + our agents stay canonical).

**Licence**: MIT — clean.

---

## 5. mnemox-ai/tradememory-protocol

**What it actually is** (verified down to source files): a real, local-first
Python project (1.4k★, MIT, ~10MB, 1,400+ tests, pushed 2026-06) — pip library
+ MCP server (17–20 tools), SQLite storage by default (`db.py`), with an
optional paid hosted API (`mcp.mnemox.ai`, $29–299/mo) that we do not touch.
The core math is openly documented and implemented:

- **Comparable-condition retrieval** (`src/tradememory/owm/context.py`): a
  `ContextVector` (regime, volatility_regime, session, ATR at multiple
  timeframes, spread, drawdown_pct); `context_similarity()` = weighted blend
  of exact-match categorical fields + Gaussian-kernel similarity on numeric
  fields `exp(-0.5*((v1-v2)/(bandwidth*|v1|))^2)`, hardcoded weights (regime
  0.25, volatility_regime 0.15, session 0.10, atr_d1 0.15, …), neutral 0.5
  when nothing overlaps.
- **Outcome-weighted recall** (`owm/recall.py`): `score = Q·Sim·Rec·Conf·Aff`,
  multiplicative factors in (0,1]: Q = `sigmoid(k·pnl_r/sigma_r)` (k=2.0,
  sigma_r=1.5, R-multiple based); Rec = power-law decay
  `(1+age_days/tau)^-d` with type-specific constants (episodic tau=30/d=0.5,
  semantic tau=180/d=0.3); Conf = `0.5 + 0.5·confidence`; Aff = affective
  modulation in [0.7,1.3].
- **Anti-resonance** (`owm/anti_resonance.py`, v0.5.2): a consonance score —
  do the retrieved analogues support or oppose the proposed trade direction —
  with a suppression flag when counter-evidence dominates.

Unusually candid `LIMITATIONS.md`: empirical validation only n=40 (target
≥100), Postgres track unfinished, and a self-disclosed **failed** validation
(Phase 5 "INVALID… 0/100 DSR PASS" — apparent improvement was an artifact of
the agent skipping 97% of trades). Adopt the math; trust none of their
performance claims.

**Adopt (concepts — via native adapter only; this is the pre-locked stance)**

| # | Mechanism | Maps to | NSE validation test |
|---|---|---|---|
| M1 | **Multiplicative outcome-weighted analogue scoring** `Q·Sim·Rec·Conf` (drop their Aff term) — Q as a bounded sigmoid over realised R-multiple, not raw PnL | `alpha/memory.py::recall_analogues` + `memory_analogues`: compute the product per candidate analogue instead of similarity alone; matches the constraints doc's required weighting (similarity, recency, sample size, data quality, realised outcome) almost term-for-term | Held-out calibration test over ≥100 resolved decisions (aligns with **W5**): do debates fed outcome-weighted analogues produce better-calibrated expected-path/invalidation claims than unweighted retrieval? Brier/hit-rate vs resolver outcomes; also compare linear vs sigmoid outcome transform; shadow-only until it wins |
| M2 | **Gaussian-kernel numeric + exact-match categorical context similarity**, and **power-law recency decay with type-specific tau** (fast for episodic regime-specific analogues, slow for structural/setup-family patterns) | Similarity metric behind `memory_analogues`; decay parameter in `recall_analogues` (currently time-filtered by `as_of` only). Context vector = our own NSE fields (regime/breadth phase, sector RS, ADR, setup family) — not their forex fields | Retrieval quality: 20 hand-labelled known-similar/known-dissimilar decision pairs, precision/recall vs current metric; decay: grid a few tau values in the same calibration harness, done-test = beats no-decay out-of-sample and is stable across regimes (log in frozen experiment record per Q1) |
| M5 | **Anti-resonance / consonance gate** — score whether retrieved analogues support or oppose the proposed direction; flag when counter-evidence dominates | `agents/debate.py`: present the consonance score with the analogue block; a dominance of adverse analogues becomes explicit "strongest contradiction" evidence (fits the debate contract's antithesis requirement) | On resolved decisions where the debate proceeded despite adverse analogues: would a consonance flag (<0.4-style threshold, re-derived on our data) have disproportionately marked the losers? |
| M3 | **Decision-time confidence logged, then scored** — the agent's stated conviction is captured at decision time and later audited against outcomes | `decision_memories`: persist the debate's stated conviction/uncertainty; `diagnostics.py` adds a calibration report (conviction decile vs realised hit rate) | After 20+ shadow sessions (**W5** gate), plot conviction vs outcome; done-test = a monotonicity/calibration read; systematic overconfidence becomes visible evidence in the UI, never a sizing input (constraint: no LLM confidence controls size) |
| M4 | **Tamper-evident hash chain over decision records** — SHA-256 chaining makes the "immutable" claim checkable | `decision_memories`: add `record_hash` + `prev_hash` at `record_decision` time; cheap, pure-SQLite | Integrity sweep: mutate one historical row in a scratch copy; done-test = chain verification detects it; run verification in nightly pipeline |

**Do NOT adopt**: the hosted API / SaaS billing layer as memory backend
(directly violates "SQLite records remain canonical"; commercial dependency);
its MCP-server architecture as a runtime component (we need the algorithms as
native Python in our own schema, not a standing server); MT5/forex connectors
and session labels (asia/london/newyork — replace with NSE session concepts);
the unfinished Postgres/Alembic track; the **Aff (affective/emotional) term**
(behavioural discipline for a manual Indian swing trader belongs in our own
gate design, not an agent "emotion" model); their hardcoded similarity weights
and decay constants (re-derive on NSE data); zkML / chain-anchoring / MiFID
compliance claims (unbuilt or irrelevant). Its n=40 validation — with one
self-disclosed invalid study — is *below our own bar*; we require our own
≥100-decision test before M1 influences anything.

**Licence**: MIT for the OSS core; the formula-level math is openly documented
and independently reimplementable with no IP concern. Note the open-core/SaaS
trajectory; take no import dependency.

---

## Prioritized adoption backlog (effort × expected value)

Effort: S < M < L. EV judged against the primary alpha hierarchy (regime →
ranking → chart interpretation → risk context → forecasts-secondary) and the
learning-loop constraints. Everything lands shadow-first.

| Pri | Item | Source | Effort | EV | Wave anchor |
|---|---|---|---|---|---|
| 1 | Postmortem records with MFE/MAE, +1R/+2R/stop timing, lessons (T3) — the resolver is already wave item 3; this defines its output contract | claude-trading-skills | S (rides W3) | High — unlocks the whole learning loop; everything below consumes resolved outcomes | **W3** |
| 2 | Outcome-weighted analogue retrieval: `Q·Sim·Rec·Conf` scoring, kernel similarity, recency decay (M1, M2) | tradememory-protocol | M | High — directly implements the constraints doc's required memory weighting; measurable via calibration | **W5** (needs resolved outcomes from W3) |
| 3 | Anti-overfit promotion-gate battery + gate-by-gate failure diagnosis (Q2, Q3) | QuantGPT | M | High — the hard gate wave item 4 must pass through anyway; codifies it | **W4** |
| 4 | Leakage audit: automated look-ahead check on all decision-time features (X2) | xtquantai | S | High — cheap insurance on the single most fatal research bug; precondition for W4 | **W1/W4** |
| 5 | Frozen experiment KB incl. failed paths + rediscovery flagging (Q1) | QuantGPT | S–M | Med-High — constraint §Research-6 made queryable; compounds over time | **W4** |
| 6 | Decision-time conviction logging + calibration audit (M3) | tradememory-protocol | S | Med — feeds the W5 calibration audit; evidence-only, never sizing | **W5** |
| 7 | Per-lens/setup-family performance digest (T5) | claude-trading-skills | S | Med — fulfils the UI-evidence requirement "which teacher lens"; needs W3 outcomes first | **W3→UI** |
| 8 | Verdict-gate output contract + append-only transition ledger + provenance check (T1, T2, T4) | claude-trading-skills | S | Med — auditability hardening of what already exists; T2 starts as a verification task, not a build | memory/debate hygiene |
| 9 | Research-to-backtest spec step per experiment (X1) | xtquantai | S | Med — kills execution-timing ambiguity in every study | **W4** |
| 10 | Anti-resonance/consonance score on retrieved analogues as explicit antithesis evidence (M5) | tradememory-protocol | S–M | Med — strengthens the debate contract's "strongest contradiction" requirement; testable retrospectively | **W5** |
| 11 | Two-tier model routing + verdict caching + mode discipline (V1–V3) | vibe catalogue | M | Med — pure cost efficiency, no alpha claim; do after the pipeline shape stabilises so the cache key (context-pack hash) is stable | ops/cost |
| 12 | Hash-chained decision records (M4) | tradememory-protocol | S | Low-Med — makes "immutable" checkable; cheap | memory hygiene |
| 13 | Cross-review of promotion claims by an independent model pass (Q4) | QuantGPT | M | Low-Med — only for experiment promotion, not per-stock; defer until W4 produces claims to review | **W4/W5** |

**Explicitly not adopted / not worth it**
- Awesome Vibe Trading Bot catalogue: all 17 crypto-bot designs/strategies and
  its cost figures; only the routing/caching/mode-discipline patterns and the
  reference-index role survive.
- QuantGPT: evolutionary expression mutation/crossover engines, QuantGPT
  Cloud, WorldQuant/A-share content, unreproducible "validated factor" claims.
- xtquantai: everything except the spec + leakage-check patterns (QMT runtime,
  China universe); 3 of its 4 skills are unshipped.
- claude-trading-skills: US data vendors, US-calibrated thresholds, generic
  screeners, .skill packaging.
- tradememory-protocol: any service/MCP/REST dependency, the affective term,
  MT5/forex assumptions, hardcoded weights/constants, zkML/compliance vapor
  items.

**Licences**: all five are MIT. No GPL/AGPL exposure anywhere; and since the
rule is concept-adoption with native reimplementation, licence risk is nil.
The only commercial caution is tradememory-protocol's open-core/SaaS
direction — never take it as a dependency.
