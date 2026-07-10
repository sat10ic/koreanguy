# PLAYBOOK_TO_TOOL_MAP — Implementation Backlog

Maps every **[CODEABLE]** rule in `INDIA_PLAYBOOK.md` to where it lives (or should) in Manas OS,
whether it exists today, the WAVE K task it feeds, and priority. **[JUDGMENT] rules are excluded**
(they are coach/debate lines, not gates) except where they imply a codeable metric.

**Priority key.** **P0** = directly feeds the recall-baseline fix (the 25%/0% WAVE K2 result — pool
recall must go 25%→≥90%, survivor recall 0%→≥60%). **P1** = high-value, next wave. **P2** = later.

**Tool-location vocabulary.** pool (scanner/candidates.py) · gate (scanner/gates.py) · regime
(engine/eod_detectors, XP/MBI, regime gauge) · risk-proposal (risk/plan.py — sole money-math
writer; changes are PROPOSED not applied) · objection (Stage-2 scored objection, WK K5) · debate
(design/agents/LENS_*) · coach (coach-line surface) · UI.

**Grounding for exists-today:** WAVE_K_SPEC PART A "8 mismatches" + LEARNINGS WAVE K2; locked
tables read from `risk/plan.py` L19–38 and `scanner/gates.py` L21–30.

---

## A. Universe & Liquidity (Playbook §1)

| Rule | Cite | Tool location | Exists today? | WAVE K task | Priority |
|---|---|---|---|---|---|
| U1 NSE EQ only | AR-NSE-Only | pool (universe_filter GateConfig) | yes | — | P2 (done) |
| U2 price floor ₹30 (prefer ₹50) | AR-Min-Price | pool base-eligibility | partial | K4 base-eligibility | P0 |
| U3 turnover floor ≥3cr | TTM-A5/S7, AR | pool base-eligibility | partial | K4 base-eligibility | P0 |
| U4 exclude 5%-circuit band | TTM-A2/S6, AR | gate (gate_tradability) | yes | K5 hard-refuse (keep) | P0 |
| U5 >12% gap+ORB EP skip | TTM-A1/S10 | gate (EP path) | no | K5 objection / EP entry | P1 |
| U6 universe-size stat | TTM-A3/S56 | UI + pool | no | K6 report context | P2 |
| U7 top-100 slippage tier | TTM-A4/S1/S3 | risk-proposal (slippage buffer) | no | NEW | P2 |
| U8 intraday depth check (>3 blank 3–5min bars) | TTM-S5 | gate (pre-trade) | no | NEW | P2 |
| U9 institutional-volume universe | AR-Account-Size | pool velocity | partial | K3 metric (adr/vol) | P1 |
| U10 EP/IPO liquidity re-scan post-trigger; setup-liq rank EP/IPO>breakout>reversal | TTM-A8/A9 | pool | no | K4 archetype rank | P1 |

---

## B. Discovery metrics & the Stage-1 SENSITIVE BUCKET (Playbook §3, §4, §4.1) — the P0 core

These are the corpus-grounded metrics + archetypes that fix recall. **K4 sensitive-bucket
thresholds below are all corpus-cited, NOT invented.** (Metrics = WK K3 one-writer shadow; bucket
assembly = WK K4.)

| Metric / archetype | Corpus threshold (cited) | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|---|
| **Base eligibility** (bucket entry gate) | NSE EQ; price≥30; 30d avg vol ≥2 lakh sh; turnover ≥3cr; exclude 5%-circuit/ETF/ASM | TTM-A2, AR, WK groww3/CHARTSMAZE | pool | partial | K4 | **P0** |
| **pct_up_from_65d_low** (buying force) | **≥30–35% up from 65-day LOW** (NOT 52w-high nearness) | WK groww2, CH3.1; TTM-C11 | pool metric | **no** (52w-high anchor instead) | K3+K4 | **P0** |
| **adr20** (velocity/volatility) | ADR20 in top universe percentile; sort scan by ADR desc | TTM-H-III3, WK | pool metric (symbol_timing adr display-only today) | partial (display only, no gate) | K3+K4 | **P0** |
| **purple_dot_count_60d** (velocity) | dot per >5% move on >5 lakh vol / 60d; **0 dots = skip** | WK groww2, CH3.1 | pool metric | **no** | K3+K4 | **P0** |
| **persistency counts** (persistent-momentum) | close **>10EMA ≥20d, >20EMA ≥30d, >50EMA ≥50d, >200EMA ≥150d**; decisive-exit buffer | **TTM-H-III1/III2** | pool (maps to ported `engine/manas_indicators` persistency) | partial (indicator ported, not a bucket archetype) | K3+K4 NEW archetype | **P0** |
| **correction_depth_from_leg_high** | pullback **≤25–30%** from leg high (>30% avoid); reject **>40–50% fall** (down-base) | WK groww2; SG-50%-Fall | pool metric | **no** | K3+K4 | **P0** |
| **prev_day_tightness_pctile** (Strong-Start-ready) | prev-day range in bottom pctile of own 20d ranges + uptrend | WK Tightness Study | pool metric | no | K3+K4 archetype a | P1 |
| **range_contraction_flag** (VCP coil) | ATR20 bottom pctile; successive contracting pullbacks; no heavy-red-day | WK groww4/2; TTM-S14 | pool metric | no | K3+K4 archetype c | P1 |
| Archetype **b Pullback-to-rising-MA** | close near rising 10/20 SMA; depth ≤30%; buy pullback to 20/50 EMA (persistent) | WK, 6 Manas Entry; TTM-C10, TTM-H-III4 | pool archetype | no | K4 | **P0** |
| Archetype **d Reversal** | strong prior uptrend + down 3–5 days on declining volume | WK 6 Manas Entry; AR-Undercut | pool archetype | no | K4 | **P0** |
| Archetype **e D2/episodic** | Day-1 **≥10%** expansion (or 20% circuit) out of consolidation | TTM-B5b | pool archetype | no | K4 | P1 |
| Archetype **f EP / IPO base** | existing detectors | TTM-B1, LENS_EP/IPO | pool (detectors exist) | yes | K4 wire-in | P1 |
| AOI (base above prev weekly consolidation) | current consolidation ABOVE prev weekly; below = secondary | SG-AOI | pool metric | no | K3 | P2 |
| base width:depth ≥1–1.5 | long frustration + shallow depth | TTM-F20 | pool metric | no | K3 | P2 |

**Why P0:** WK K2 showed 9/12 master picks (all reversals + off-highs pullbacks) never entered the
pool because of the 52w-high anchor (mismatch 1) and the missing velocity gate (mismatch 2). The
bolded-P0 metrics/archetypes are exactly the ones that admit those names.

---

## C. Regime (Playbook §2)

| Rule | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|
| Four-phase model (Demand/Supply/Lack-of-Demand/Lack-of-Supply) as gauge | TTM-C1/S20 | regime | partial (XP/MBI 4-mode maps, not four-phase) | NEW (lens/regime) | P1 |
| Regime = SOFT gate, not family kill (D2/momentum in muted tapes) | TTM-C4, WK m6 | gate→objection | no (ALLOWED_FAMILIES hard-drop) | K5 | **P0** |
| Lack-of-Demand → swap momentum-burst → base/break EP variant | TTM-C3/S21 | regime+gate | no | NEW | P1 |
| Only Bear-Volatile truly dead (6 market types) | TTM-C5/C6 | regime | partial | NEW | P1 |
| EP-reaction-quality rolling signal | TTM-C8/C9 | regime | no | NEW | P2 |
| Open-risk-ceiling breach = choppy signal | TTM-D3 | regime | no | NEW | P2 |
| MBI bands + warning-day + green-lead | SG-MBI/Warning/Green | regime (MBI exists) | partial | NEW | P1 |
| 3–4 stops/week → pause; pre-event tricky-week | AR-Poor-Signal/Before-Events | regime+coach | no | NEW | P1 |

---

## D. Entry execution (Playbook §3)

| Rule | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|
| EP Day-0: 5-min ORB high, day-low stop, skip>12% | TTM-B2/S10 | gate/entry (LENS_EP) | partial | K5/entry | P1 |
| EP pullback 10/21 EMA | TTM-B3/S11 | entry/debate | partial | debate | P1 |
| D2 three branches (strong/Wick/gap-down reversal) | TTM-B5c/S13 | entry | no | NEW | P1 |
| Strong Start: gap≥prevHigh, low≥prevClose, wait 2–3min, RVOL bonus | AR-Strong-Start | entry/debate (LENS_STRONG_START) | partial (lens) | debate | P1 |
| Gap chase: EP≤12%, breakout/strong-start≤5–7% | TTM-A1, AR-Gap-Limit | gate | partial | K5 objection | P1 |
| Pullback>breakout in strong uptrend; buy 20/50 EMA (persistent) | TTM-C10, TTM-H-III4 | entry/debate | no | debate/entry | **P0** (feeds archetype b) |
| Undercut-and-recover (below 10&20 MA then reclaim) | AR-Undercut | pool/entry | no | K4 (archetype d) | **P0** |
| IPO first/double inside bar; crow/hook/fast-flag | SG-IPO/Inside-Bar/Crow | entry/debate (LENS_IPO) | partial | debate | P1 |
| IPO overlap>50%+contraction reversal; J-curve entry | TTM-H-I3/I1/I6 | entry (LENS_IPO) | no | debate/entry | P1 |
| VCP tightness (ATR) not volume rules | TTM-S14 | pool | no | K3 range_contraction | P1 |
| Downside-expansion absorption buy; squat; ORB clean-charts-only | TTM-S15/S16/S17 | entry/debate | no | debate | P2 |
| No pattern in a range (require prior trend) | TTM-B6 | debate/gate | no | debate | P2 |
| Shorts: persistent-momentum-then-break ("popcorn") | TTM-B11/C6 | pool/debate | no | NEW | P2 |

---

## E. Risk & sizing (Playbook §5, §6) — mostly risk/plan.py PROPOSALS

| Rule | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|
| Position size = risk₹÷(entry−stop); MTF on base capital | TTM-D1/S27/S34 | risk (validate) | yes | — | P2 (done) |
| Persistent vs Absolute → opposite SL/trail; enforce+flag | TTM-H-II1 | gate/template select | no | NEW | **P0** (drives template map & GROWW-class fix) |
| Setup-type→template (Velocity/Magnitude/Hybrid), flag mismatch | TTM-F13/F16 | gate/template | no | NEW | P1 |
| Stop cap as **k×ADR20** (not absolute %) | TTM-D7, WK m3/PART C | risk-proposal | no (absolute 7.5/8.0) | **K7 proposal** | **P0** |
| Measured move = own-history ADR-burst (not nearest resistance) | WK m5/PART B | risk-proposal | no | **K7 proposal** | **P0** |
| Initial stop >4% cuts expectancy; IPO 4–6% normal | TTM-D4/S35, TTM-H-I2 | risk-proposal | partial | K7 | P1 |
| Slippage buffer 0.3–0.6% | TTM-D8/S4 | risk-proposal | no | NEW | P2 |
| Hard stop always in system; exit-at-market on hit | TTM-D11/D13, AR-Stop-Hit | risk/UI | partial | — | P1 |
| Far-trailing as alert (2–4%), initial stop hard | TTM-D10/S37 | UI/exit | no | NEW | P2 |
| Trailing math ₹0.5/₹1; pyramid each add≤prev | AR-Trailing/Pyramiding | risk/exit | no | NEW | P2 |
| Pyramid-to-30% ladder (1% risk → +4 tranches on higher-lows) | TTM-H-V1 | risk (pyramid template) | no | NEW | P1 |
| DD hard stop (~3%) halts all trading | SG-Drawdown | risk/regime | partial (open_risk_cap exists) | NEW | P1 |
| Graduated deployment on MBI green (10%→2–4×) | SG-Size-Scaling | risk | no | NEW | P2 |
| Fire-power: flag entry needing >15% to risk-free | TTM-H-I5 | risk/entry | no | NEW | P2 |
| ADR-normalized R (not raw %) | TTM-E7/E6 | risk-proposal | no | NEW | P1 |
| Story-bucket tag as catalyst-strength | TTM-H-IV1 | pool/gate tag | no | NEW | P2 |

---

## F. Exits (Playbook §7)

| Rule | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|
| Day-low break = own trigger | TTM-E2 | exit | no | NEW | P1 |
| MAE/MFE per-trade calc (calibrate stop from own dist) | TTM-E1/S43 | risk/journal | no | NEW | P1 |
| Objective-conditioned trail (intraday vs swing MA) | TTM-E5/B5d | exit | no | NEW | P2 |
| Fight-back score (wick/close-position); tennis-ball; eating-own-bottom | TTM-E4/B8/B10 | exit | no | NEW | P2 |
| Sell-into-strength (90°+6× vol); half-sell 15–20% | AR-Selling/90-Deg/Half-Sell; SG-Trailing | exit | no | NEW | P2 |
| Never-doubt-trend / mechanical trail below X% | TTM-H-II4 | exit/coach | no | NEW | P2 |

---

## G. Calendar / events (Playbook §8)

| Rule | Cite | Tool loc | Exists? | K task | Prio |
|---|---|---|---|---|---|
| Results-season gates EP-primary window | TTM-H3/S53 | regime/gate | no | NEW | P1 |
| Event-day scenario-branch planner (budget/elections/Fed) | TTM-C13/H1 | regime/UI/coach | no | NEW | P2 |
| Pre/post big-event pause | AR-Before-Events | regime | no | NEW | P1 |
| Gap-down: wait ~10min, trail to first-bounce low | TTM-C12 | exit/coach | no | NEW | P2 |
| Earnings ≤3d cushion 8–10%; dividends hold; splits close pre-record | AR-Earnings/Div/Splits; TTM-S32 | gate/UI calendar | no | NEW | P2 |
| Broad-crash correlation → tighten/cut regardless of chart | TTM-S55 | regime/risk | no | NEW | P2 |

---

## H. P0 LIST (feeds the recall-baseline fix — the whole point of WAVE K)

Everything that moves pool recall 25%→≥90% and survivor recall 0%→≥60%:

1. **Base-eligibility bucket gate** (price≥30, vol≥2 lakh, turnover≥3cr, exclude 5%-circuit) —
   K4. [U2/U3/U4]
2. **pct_up_from_65d_low ≥30–35%** replaces the 52w-high anchor (mismatch 1) — K3+K4. [Playbook §4]
3. **adr20** promoted from display-only to a bucket metric + scan sort (mismatch 2) — K3+K4.
4. **purple_dot_count_60d** velocity gate; 0 dots = skip (mismatch 2) — K3+K4.
5. **Persistency counts 20/30/50/150 over 10/20/50/200 EMA** as a P0 archetype (maps to ported
   `manas_indicators`) — K3+K4 NEW archetype. [TTM-H-III1]
6. **correction_depth_from_leg_high ≤30%** (reject >40–50% fall) — K3+K4.
7. **Archetype b Pullback-to-rising-MA** + **archetype d Reversal / undercut-and-recover** — the
   two archetypes that admit BSOFT/Zentec/NCC/PARAGMILK/TATAINVEST/EMS/INTELLECT — K4.
8. **Regime = soft gate, not family kill** — recast ALLOWED_FAMILIES hard-drop into scored
   objection (mismatch 6) — K5.
9. **Stop cap as k×ADR20** + **measured move from own-history ADR-burst** — the two GROWW kills —
   K7 proposals to risk/plan.py (PROPOSED, not applied).
10. **Persistent-vs-Absolute template enforcement** — the GROWW-class execution mismatch; also the
    backbone's most-emphasized dual-mode rule — NEW.
11. **Pullback-buy>breakout on persistent names (20/50 EMA)** — feeds archetype b entry logic.

(RS visual/no-80-floor, mismatch 7, is a P0-adjacent gate recast — listed in the conflicts section
below because it collides with a LOCKED threshold; recast to objection under K5.)

---

## I. CONFLICTS WITH LOCKED THRESHOLDS (proposals only — plan.py stays sole money-math writer)

Backbone (TradeTM) value is the doctrine of record; these are surfaced as PROPOSALS, never
silently applied. Locked values read from `risk/plan.py` L19–38, `scanner/gates.py` L21–30.

| # | Playbook (backbone) says | Tool LOCKED value | Direction | Proposal |
|---|---|---|---|---|
| C1 | Per-trade risk **~0.65% velocity / ~0.5% base** [TTM-D2/S28] | aggressive `risk_per_trade` RISK_ON **(0.75, 1.00)**, SELECTIVE (0.50,0.75) | tool is **more aggressive** | propose lowering aggressive RISK_ON base toward 0.65; keep as profile choice |
| C2 | Portfolio open-risk ceiling **~4–5%** [TTM-D2/S30] | aggressive `open_risk_cap` RISK_ON **3.0**, SELECTIVE 2.0 | tool ceiling is **tighter** (both recorded) | backbone permits up to 4–5%; keep tool 3.0 as conservative default, expose 4–5% as an aggressive-magnitude ceiling |
| C3 | Max concurrent tight-SL initiations **3–4** [TTM-D2/S31/S56] | `max_open_positions` **5** (aggressive) / **6** (balanced) | tool allows **more** | propose 3–4 cap for tight-SL/velocity initiations specifically (not total positional) |
| C4 | Stops **nature-relative / k×ADR**, don't import US 7–10% [TTM-D7]; IPO 4–6% normal [TTM-H-I2] | `STOP_CAP_EXCEPTIONAL` **7.5**, `STOP_CAP_ABSOLUTE` **8.0**, regime caps 4–6% | tool uses **absolute %** | K7: add **k×ADR20** alongside the absolute ceiling (GROWW kill #1) |
| C5 | Measured move = **own-history ADR-burst** [WK m5] | `RR_FLOOR` **1.5** off nearest-resistance `structural_target` | tool under-measures fresh-high/IPO | K7: EXCEPTIONAL-family measured move defaults to own-history burst (GROWW kill #2) |
| C6 | **RS is visual, no rating floor** [TTM-S22, WK m7] | `RS_FLOOR` **80.0** hard gate | tool hard-floors | recast to scored objection (K5), remove hard floor |
| C7 | Buying force = **≥30% from 65d low** [WK] | pool anchored to **52-week high** (nearness ≥0.85) | opposite anchor | add 65d-low anchor to bucket (K4); keep 52w-high as one archetype, not the gate |
| C8 | Regime works on **individual strength**; only Bear-Volatile dead [TTM-C4/C5] | `ALLOWED_FAMILIES` **hard-drops** whole families per regime | tool over-restricts | recast to soft objection (K5) |
| C9 | Position cap ~40% [TTM-D5] / Arora 25–30% typical [AR] | (no single locked 40% cap found; governed by open_risk×stop) | aligned | note only — verify no path exceeds 40% single-name |

**Internal backbone conflict resolved by hierarchy (recorded, not a tool conflict):** far-trailing
stop as alert [TTM-D10] vs hard-stop-always [TTM-D11] → initial near-price hard stop is mandatory;
far-trailing-as-alert applies only once trailing well above it. (Playbook R12/R13.)

**Gap-chase layering (not a conflict — setup-dependent):** EP tolerates ≤12% (circuit band)
[TTM-A1]; breakout/Strong-Start ≤5–7% [AR-Gap-Limit]. Encode per-setup, not one global cap.

---

*End PLAYBOOK_TO_TOOL_MAP.md. K4 sensitive-bucket thresholds are the corpus-cited values in §B;
none invented. Conflicts in §I are proposals — no plan.py edit is authorized by this document.*
