# MANAS — Task Board

**Last updated: 2026-07-26.** Before this it sat untouched since 2026-07-14 while work
tracked only in the session tool — that is why it is now rewritten as a live backlog
rather than a finished-phase board. Keep it current at every wave close.

Canonical plan: `C:\Users\satta\.claude\plans\c-users-satta-downloads-manas-os-v2-md-woolly-peacock.md`
(LOCKED thresholds live there — use verbatim). Research: `manas_os/design/Feedback/`.
Numbers in `(#nn)` are session-task ids; they are not stable across sessions, the
titles are.

Status: `[x]` done · `[~]` partial/in progress · `[ ]` pending

---

# READ FIRST — 2026-07-30 edge findings

`manas_os/design/EDGE_FINDINGS_2026-07-30.md` holds everything measured during the
A1 audit plus the practitioner specs the user supplied that day. Read it before
touching setups, grading, or ranking. Headlines:

- **Recall 12.1%** — 331 stocks gained ≥10%/10 sessions; the tool listed 40, while
  showing 139–281 names a night.
- **The rank is noise** — top-10% of ranked names returned −1.43%, bottom-25%
  −1.21%. A gap of −0.21pp. Ordering does not sort by outcome. For a 1–2 trade/night
  user this, not gate membership, is the binding deficiency.
- **Precision ≈ random** — our picks −0.488R vs random liquid −0.508R over the same
  falling tape. One regime, 7 sessions; distinguishes nothing either way.
- **A+ is structurally unreachable** — `candidates.py:1417` caps grade at B on any
  objection; ~87% carry `regime_family` outside RISK_ON. 100% of 1,734 candidates
  are grade B. By the user's own A+ spec that degradation is correct; the defect is
  that the tool then lists 281 B's instead of showing zero.
- **Only `pocket_pivot` has positive expectancy** (+1.30R, 33% win, n=30, PRE-M3
  code). `watchlist_timing` is the biggest producer (639) and worst performer
  (1% win, −1.70R).
- **Entry/stop mechanics are NOT the problem** — replaying with previous-day-high
  entry and 2–3% stops was worse on every variant.
- **The measurement trap** — gate code changed 07-11/19/21/22/30 while outcomes need
  10–20 sessions. Three of my own "findings" were measured against dead code. Freeze
  and version-stamp before concluding anything.

# OUTSTANDING

Sequenced by Fable 2026-07-25 into waves. Wave 1 = stop showing the user false or
missing things. Wave 2 = make the substrate true. Wave 3 = the visual/IA restructure
as one pass, not dribs.

## WAVE 1 — stop displaying falsehoods + long-standing repeat asks

- [~] **Capital / sizing correctness** (#67)
      DONE 2026-07-26: `trader_profile.account_capital` was 100,000 against a real
      150,000 — every position sized 33% small, feeding the user's own logged
      MICRO-SIZE leak. Now set to 150,000, verified, nothing else touched. A typical
      SELECTIVE position goes qty 10 → 16, notional ₹9,245 → ₹14,792, which also
      lifts it above the tool's own `TARGET_NOTIONAL_MIN` of ₹10k that it had been
      silently violating.
      STILL OPEN:
      (a) `risk/plan.capital()` still falls back to config default **1,000,000** when
          the row is missing or ≤0. Must REFUSE with a named reason
          ("account capital not set — open Profile"), never size on a guess. Live for
          any fresh install.
      (b) Show the capital actually used on every sizing output. Had this existed the
          1L-vs-1.5L gap would have been caught on day one, not by a DB query.
      (c) Auto-compound (user's rule 10): derive equity from starting capital +
          journal realised P&L (`journal_trades.broker_realized_pnl`, 420 closed
          rows) so risk grows with the account. Note `completed_trade_count` is 0
          against those 420 rows — the counter is incremented nowhere. Keep it
          inspectable: starting capital, realised P&L, current equity.
- [ ] **Cards that contradict their own evidence** (#58) — "Strong Start" rendering at
      rvol 0.05. A card must not assert what its own numbers deny.
- [ ] **Exclude ETFs from the footprint universe** (#50). Fresh evidence 2026-07-26:
      the Stockbee up-day persistence ladder returned liquid/cash ETFs as the top 10
      names in the whole universe (P252=249, R²=0.999, +1.3% in 63 days) — accrual
      instruments that tick up by construction. Independently, nexus's own taxonomy
      excludes ETFs entirely; 403 of our 2,389 symbols are unmapped by them and are
      overwhelmingly ETFs.
- [ ] **ChartsMaze session expiry as an auth-needed state** (#59), like Fyers already
      is. Currently it just goes quiet. USER-SIDE until then: `cd chartsmaze_extractor
      && python login.py` (OTP).
- [ ] **Label the gate UNPROVEN** — it has no demonstrated edge (passed −0.67% vs
      refused −0.09% at T+5). Either show the label or stop implying authority.
- [ ] **Strip TAKE/SKIP authority from the LLM council** (#57) — grade it or stop
      rendering its verdicts as decisions.
- [ ] **Fix MARS** (#53) — read `sector_index_prices` instead of re-fetching from
      Fyers. Root cause of the blank-since-day-one MARS column: the evening run has
      no valid Fyers token (expires 06:00 IST).
- [ ] **Restructure the sector/theme table** (#54) — add RMV and RS over 1W/1M.
      Asked for repeatedly and skipped repeatedly. Fold in the two nexus UX wins:
      (i) ticker COUNT on every row — a 2-stock theme and a 72-stock theme currently
      look identical; (ii) all seven timeframes SIDE BY SIDE (1D/1W/1M/3M/6M/12M/YTD)
      instead of the current toggle, because acceleration is only readable across a
      row. `MICROFINANCE +10.4% 1M → +29.9% 3M → +33.0% 6M` = sustained;
      `TELECOM & NETWORK INFRA −8.0% 1M but +44.6% 6M` = rolling over. That second
      shape IS the short-lived-theme detector the user keeps asking for, and it needs
      no new data — only column layout.

## WAVE 2 — make the substrate true

- [ ] **Data-integrity holes the calendar check exposed** (#56).
- [ ] **Trading-day guards on the 4 daily entrypoints** (#55) — a Saturday no-op is
      success, not a gap to backfill.
- [ ] **Recompute footprint 2026-07-17..07-24** (#51) — stale pre-fix lanes.
- [ ] **Scorecard: read-only connection + the fake funnel** (#61).
- [~] **Revive the 4 dormant modules** (#66)
      DONE 2026-07-26: `conviction.py` (24 KB, imported by the API) and
      `theme_pulse.py` (13 KB, a registered pipeline stage) were both UNTRACKED and
      one `git clean` from deletion — now committed (`b32b694a`), along with
      `ep_quality.py` and `token_prewarn.py`.
      STILL OPEN: actually wiring them.
      · `token_prewarn.py` → register an 08:45 Windows task (StartWhenAvailable,
        WakeToRun, not DisallowStartIfOnBatteries). Fixes the daily MARS token death.
      · `scheduled_update.py` → "catch up every incomplete session, honestly log";
        this is literally the by-hand catch-up done on 07-25. Point
        `nightly_update.cmd` at it. Must respect the #55 trading-day guard.
      · `alpha/leakage_audit.py` → run as-is, report, then fold into
        `integrity/checks.py` as a data-level twin of the static `check_lookahead`.
        Needed before trusting ANY scorecard verdict (68 thresholds vs ~11
        independent evaluation dates).
      · `sources/chartsmaze_migrate.py` → never ran, which is why manas_os still
        reads ChartsMaze from `legacy/`, violating the project's own anti-mashup
        rule. Coordinate with #59; the extractor's `output_root` must move too or the
        scraper writes where nothing reads.
      · `ep_quality.py` → FIX then wire. Concrete blocker found 2026-07-26:
        `classify()` gates SWING_EP on `fresh_base_breakout`, which needs
        `breakout_age ≤ FRESH_BASE_BREAKOUT_AGE_MAX (3)`, but the measured median
        breakout_age is **172**. SWING_EP is unreachable; everything degrades to
        INTRADAY_SIP or AVOID. The fix is the pivot semantics, not new detection.
      · DEFER: `alpha/resolver.py`, `backtest/entry_variants.py`,
        `backtest/pead_study.py` (after this wave). LEAVE: `breadth_sheet.py`
        (documented fallback), `trade_autopsy.py`, `calibrate.py` (legit CLIs).

## WAVE 3 — the visual / IA restructure, as ONE pass

- [ ] **One concept = one page, question-shaped names** (#63, absorbs #62) — the
      earningspulse pattern. Tames EXPERT mode's 17 stacked panels and 14 explainers
      that don't teach. Study: `design/COMPETITOR_STUDY_EARNINGSPULSE_2026-07-25.md`.
- [ ] **Finish the 33-chip band work** (#52) — extract shared bar + sparkline
      primitives, convert the text-only panels.
- [ ] **Divergence detection across breadth metrics** (#64) — the "Worms Disagree"
      pattern.
- [ ] **Source-tagged WHY on every mover/candidate** (#65), and say so when there
      isn't one. Now unblocked by the nexus crosswalk: RAIN → niche "Carbon Black",
      and CARBON BLACK ran +12.2% 1M / +42.2% 3M / +47.6% 6M. The theme explains the
      move — that is the WHY, available as a join.
- [ ] **Beginner/Expert progressive disclosure made real** (#29) + fix the Regime
      beginner view.
- [ ] **Regime page UX rework** (#1) — posture, dials trend, stickers, history strip.

## WAVE 4 — conditional / larger

- [ ] **SMART MONEY section as its own screen** (#49) — persistence + absorption +
      accumulation. Gated on ingest proof.
- [ ] **Live intraday loop** (#21, in progress) — Fyers WS Strong-Start → Telegram
      confirm → auto-journal. New argument for finishing it, from the HTF
      transcripts: our stops are 4–6× wider in ADR terms than an intraday entry's
      (we cap at 1.0–1.5× ADR; the 12-min-tutorial target is 0.25–0.33× ADR under a
      5-minute opening-range bar). Since `qty = capital × risk% / (entry − stop)`,
      the same rupee risk buys 4–6× fewer shares. Intraday confirmation is what earns
      the tighter stop, and the tighter stop is what earns the size.
- [ ] **Airtight-loop fix waves from the audit ledger** (#47, in progress).
- [ ] **Breadth-enrichment wave** (#44) — Market Breadth V2.0 → decision support.
- [ ] **Weekly/monthly breakout timeframe scan** (#45).
- [ ] **Critical edge review** (#48) — where the edge actually is, and the full
      edge-play.
- [ ] RRG as a lens (demoted by Fable; not a trigger).

---

# ADDED 2026-07-26

- [~] **Shadow metrics: up-day persistence, 10EMA respect, symmetry, linearity** (#68)
      DONE: all four computed and committed (`0bf4afe7`, `d61b9b50`). Measured on
      2,042 symbols as of 07-24.
      · `ema10_respect` is the find — % of last 60 sessions closing above the 10EMA,
        plus `shakeout_holds` (low pierced it, close held). It sorts the user's own
        names far better than Stockbee persistence: SIS rank 14, CUPID 43, RAIN 53
        (the ones that worked) vs NILKAMAL 480, NUVOCO 481, EXICOM 375 (the choppy
        ones). Persistence scattered the same names 151..1570.
      · Three genuinely different questions, worth keeping distinct:
        `persistency_counts` = unbroken RUN above an EMA; `leg_linearity` =
        SMOOTHNESS of the path; `up_day_persistence` = FREQUENCY of up-closes. Only
        frequency survives a pullback intact, which is why Stockbee uses it to
        qualify pullback buys.
      STILL OPEN: no unit tests for `up_day_persistence` or `ema10_respect`; neither
      is wired into `discovery.py` metrics_json; shadow-only holds by absence, not by
      a guard test. THEN, separately and needing explicit authorisation because it is
      money math: feed `respect_pct` into exit-mode selection so a ≥85% name gets the
      10EMA trail and a <70% name gets the wider 21EMA/structure trail.
- [ ] **High Tight Flag as a scan + a regime gauge** (#68)
      Scratch detector works: 41 candidates on 07-24, 12 at the US textbook ≥90% pole.
      I predicted zero (every source says HTF needs a raging bull) — unresolved
      whether the 60% India-adapted threshold is too loose or the tape genuinely has
      more speculative appetite than DEFENSIVE implies. CUPID validates the detector
      (named in the source video, found independently from price data). Promote
      `scratchpad/htf_scan.py` into `scanner/`, surface the COUNT as a regime gauge,
      report ≥90% separately from ≥60%.
      MUST SHIP GATED: HTF fires on pump-and-dump by construction (a 100% move in 8
      weeks IS the pump signature), so the existing MAX/lottery and pump-signature
      exclusions must run BEFORE it, and the governor must gate it. Knowledge digest:
      `design/knowledge/HIGH_TIGHT_FLAG_2026-07-26.md`.
- [ ] **The weekly watchlist follow-through test** — probably the single most useful
      item in the five HTF transcripts, and the tool does not have it. Leif: go back
      and check whether anything on your list actually broke out this week; if the
      whole right side looks weak and rolling over, stop yourself trading. It is a
      breadth read computed from the USER'S OWN shortlist rather than the index, it is
      fully computable from our ~40 sessions of scan history, and it targets the
      logged over-trading leak directly.
- [~] **Nexus theme taxonomy** (#69)
      DONE: extracted (215 industries / 2,676 tickers) via the site's own "Copy TV
      Watchlist" export, committed (`9b3b3829`); crosswalked onto our 24 sector keys
      and committed (`e41ff35a`) — 201 mapped, 12 aliased, 2 unmapped, 61/61 agreement
      with our existing table on overlapping concepts and zero contradictions.
      Overrode the first draft's power-chain → UTILITIES mapping: UTILITIES has
      `index: None` while ENERGY has NIFTY ENERGY, so that routing would have stripped
      ~34 power tickers of any benchmark and silently broken MARS for the group.
      STILL OPEN: nothing reads `nexus_crosswalk.py`; no tests. Then the schema —
      `themes(theme_key, level[pillar|cluster|niche], parent_key, display_name)` +
      `symbol_themes(symbol, theme_key, source, confidence, verified_at)` as a JOIN
      TABLE. Many-to-many belongs at the THEME layer (avg 1.86, max 4 per ticker);
      the INDUSTRY layer is strictly one-to-one — measured, zero symbols in >1
      industry. Source every row (`nexus`, `chartsmaze`, `nse-official`);
      NSE-official wins where it exists.
      THE HEADLINE FINDING — the tool's blindness is granularity, not missing buckets.
      Only 2 of 215 industries have no home. But 213 industries collapse into 24
      lines: FINANCIAL_SERVICES swallows 20, FMCG 18, CONSUMER_DURABLES 17,
      CAPITAL_GOODS 16, METAL 15, CHEMICALS 13. CARBON BLACK, FLUOROCHEMICALS and
      DYES & PIGMENTS all vanish into one "Chemicals" row. That is why theme plays go
      unseen.
      NOT GROUND TRUTH: five spelling-duplicate pairs misfile 41 tickers (a 65-ticker
      specialty-chemicals industry split near-half by Speciality/Specialty); semantic
      duplicates exist beyond those; the site's own header claims 221/172 while the
      export gives 215; industry and niche layers disagree on the same ticker (SIS is
      "Other Consumer Services" in one and "Events & Weddings" in the other, and it is
      a security-services firm). Five low-confidence mappings still unresolved:
      Trading-Minerals→METAL (dominated by ADANIENT, a conglomerate), Rubber→CHEMICALS,
      Electrodes & Refractories→METAL, Granites→INFRASTRUCTURE, Ceramics→CONSUMER_DURABLES.
- [ ] **Versioned-snapshot polling** (#69) — copy nexus's
      `{version, versionId, generatedAt, payloadKey}` manifest plus a cheap
      `/version?version=<id>` "has this changed?" check separate from the expensive
      fetch. Directly serves #55/#56 and the "data didn't update today" state. Also
      copy their prominent `SERVER · 45H OLD` staleness badge — they admit their own
      lag on screen; we should too.

---

# DROPPED / DEFERRED BY DECISION

Recorded so nothing disappears silently. Reverse any of these by saying so.

- **On-demand debate surviving a server restart** (#60) — Fable 2026-07-25: defer
  indefinitely. It dies on restart and does not tell the user; the cheap partial fix
  is to at least SAY it died, which is folded into the Wave 1 honesty work.
- **Tame EXPERT mode as its own task** (#62) — deleted as a duplicate of #63; the
  one-concept-one-page restructure subsumes it.
- **The "build half" of the earningspulse study** — dropped; only the IA/visual
  lessons are being taken.
- **RRG** — demoted from a trigger to at most a lens (Wave 4, conditional).
- **Analog matching / "days like today"** — expert-toggle descriptive only, never a
  gate, and only with an n≥15 sample floor. Listed in the plan's DO-NOT-BUILD theatre
  section along with: more detector chips, pre-open triggers, LLM confidence scores,
  and FII/DII (exploit on-disk data first).

---

# USER-SIDE ONLY

- [ ] ChartsMaze OTP login: `cd chartsmaze_extractor && python login.py` (session
      expired; until #59 lands there is no in-app prompt).
- [ ] Decide `telegram.dry_run` — currently `true`, so the integrity watchdog computes
      alerts and transmits nothing.
- [ ] Fyers OAuth paste when the token expires (06:00 IST daily).

---

# COMPLETED — phase history (2026-07-04 → 2026-07-15)

Full detail is in git history and `design/LEARNINGS.md`; kept compressed here because
the per-task Codex sandbox notes were noise.

- **PHASE 0 — Truth & Measurement**: T0.1 data-integrity clamps · T0.2 replay/backtest
  harness (found: legacy generator has no screener history, so the cascade must detect
  from point-in-time OHLCV).
- **PHASE 1 — The Gate**: T1.1 `scanner/gates.py` deterministic cascade (19 tests) ·
  T1.2 `risk/plan.py` as single writer of stop/size/R:R · T1.3 `regime/governor.py`
  regime-as-law · T1.4 `candidates.py` rewired to cascade + ordinal rank, additive
  score and the 300-symbol union killed · T1.5 refusal ledger + `/api/setups/refusals`
  · T1.6 CHECKPOINT PASSED — fill-checked replay, pullback×SELECTIVE +0.44R median,
  3.6% stops, 30% hit (n=73).
- **PHASE 2 — Edge modules + journal moat**: T2.1 `sources/disclosures.py` · T2.2 PEAD
  study (catalyst leg proven load-bearing) · T2.3 journal capture + `expectancy.py`
  (k=25 shrinkage, trust ladder) · T2.4 adaptive exits (3 modes, two-strike, +1R
  breakeven/book-⅓) + portfolio heat · T2.5 cheap-edge batch (sector-adjusted momentum
  tiebreak, nearness/stacking/template chips, ADR% surface, range-expansion confirm).
- **PHASE 3 — Visual rebuild**: T3.1 refusal-funnel hero · T3.2 governor panel ·
  T3.3 journal equity curve + expectancy matrix · T3.4 heat gauge · T3.5 ChartDrawer →
  lightweight-charts · T3.6 AVWAP auto-anchor · T3.7 Focus Center fix + beginner/expert
  · regime history strip · poster type system and grammar pass · T3.8 Guided Daily Flow
  · T3.9 Position Coach.
- **PHASE 4**: T4.1 Telegram armed-list workflow — digest + armed list, FSM replay
  harness, dry-run send path, TAKE/SKIP reply capture, `/halt` kill-switch. Live entry
  pushes remain disabled by default.
- **Later**: T5.1 fundamentals ingest (`sources/fundamentals.py` → `symbol_fundamentals`,
  registered in run-eod). W5.3 earnings-calendar chip skipped — no forward
  earnings-calendar source exists in current imports.
- **2026-07-25**: integrity module + watchdog · market-calendar corrections · absorption
  lane made reachable · treemap ResizeObserver fix · JOURNAL-vs-POSITIONS copy fix ·
  stat-tile bands · ADR-scaled stop caps.
