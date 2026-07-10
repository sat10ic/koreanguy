# WAVE L — Risk & Small-Account-Growth Proposal (formal, awaiting user approval)

**Status: PROPOSAL ONLY. No code in `risk/plan.py` has been changed by this doc.**
`risk/plan.py` remains the sole money-math writer (per its own header comment); every value
below is quoted from `design/knowledge/INDIA_PLAYBOOK.md` / `PLAYBOOK_TO_TOOL_MAP.md §I`
against the CURRENT locked table (`risk/plan.py` L19-40, read 2026-07-10). This is the item-5
deliverable of the APPLICATION wave — small-account-growth + risk-management specifics touch
LOCKED money math, which is out of scope for a code change without explicit sign-off.

---

## 1. What the corpus prescribes (backbone = TradeTM, doctrine of record)

| Topic | Backbone value | Cite |
|---|---|---|
| Per-trade risk | ~0.65% (velocity setups) / ~0.5% (baseline) | TTM-D2, TTM-S28 |
| Portfolio open-risk ceiling | ~2-2.5% typical, ~4-5% hard ceiling | TTM-D2, TTM-D3, TTM-S30 |
| Concurrent tight-SL initiations | max 3-4 | TTM-D2, TTM-S31, TTM-S56 |
| Stop width | k×ADR20, nature-relative — do NOT import US 7-10% absolute stops; IPO 4-6% is structurally normal, not wide | TTM-D7, TTM-H-I2, WK mismatch 3 |
| Position cap | ~40% of portfolio (Arora typical working size 25-30%) | TTM-D5, TTM-S29, AR-Growth-Formula |
| MTF (margin) | funds CAPITAL, not risk — size on unleveraged base capital only, leverage never scales the position | TTM-D1, TTM-S34 |
| Pyramid-to-30% ladder | initiate at 1% risk on a clean pullback, add up to ~4 more 1%-risk tranches on successive higher-lows, reach ~30% portfolio allocation only after the trade is already in profit | TTM-H-V1 |
| Two viable India paths | (1) size big + hold magnitude, or (2) size big + many velocity trades — a scatter of many small trades is mathematically doomed | TTM-S57 |

**MTF risk-on-base-capital formula (backbone, TTM-D1/S34):** position size is computed as
`risk₹ ÷ (entry − stop)` using **unleveraged base capital**. If MTF/margin funding is used, the
extra buying power increases the SHARES that can be held at the SAME ₹-risk (funds capital), it
never increases the risk₹ itself (does not fund risk). The tool's `risk/plan.py` today has no MTF
distinction at all — capital passed in is assumed to already be the base; this proposal does not
change that behavior, it documents that the corpus explicitly endorses it (no conflict here).

---

## 2. What `risk/plan.py` currently locks (read 2026-07-10, unchanged by this wave)

```
STOP_CAP_BY_REGIME    = {"RISK_ON": 6.0, "SELECTIVE": 5.0, "DEFENSIVE": 4.0, "NO_TRADE": 0.0}
STOP_CAP_EXCEPTIONAL  = 7.5   # EP / IPO-base only
STOP_CAP_ABSOLUTE     = 8.0   # never exceeded, any setup
RR_FLOOR              = 1.5

PROFILES["aggressive"]["risk_per_trade"]   = {"RISK_ON": (0.75, 1.00), "SELECTIVE": (0.50, 0.75), ...}
PROFILES["aggressive"]["open_risk_cap"]    = {"RISK_ON": 3.0, "SELECTIVE": 2.0, ...}
PROFILES["aggressive"]["max_open_positions"] = 5
PROFILES["standard"]["max_open_positions"]   = 6
```

## 3. Conflicts (from `PLAYBOOK_TO_TOOL_MAP.md §I`, reproduced here as the formal ask)

| # | Backbone (TradeTM) says | Tool LOCKED value | Direction | Proposed change |
|---|---|---|---|---|
| C1 | Per-trade risk ~0.65% velocity / ~0.5% base | aggressive `risk_per_trade` RISK_ON **(0.75, 1.00)** | tool is more aggressive | Lower aggressive RISK_ON base toward **0.65**; keep as a selectable profile, not a silent overwrite. |
| C2 | Portfolio open-risk ceiling ~4-5% | aggressive `open_risk_cap` RISK_ON **3.0** | tool ceiling is tighter | Keep **3.0** as the conservative default; expose **4-5%** as an opt-in "aggressive-magnitude" ceiling for users who explicitly choose it. |
| C3 | Max concurrent tight-SL initiations **3-4** | `max_open_positions` **5** (aggressive) / **6** (standard) | tool allows more | Add a **separate 3-4 cap scoped to tight-SL/velocity initiations specifically** — do not shrink the total positional cap (positional/magnitude trades are a different bucket per §6 templates). |
| C4 | Stops nature-relative / **k×ADR20**; IPO 4-6% is normal, not wide | `STOP_CAP_EXCEPTIONAL` **7.5**, `STOP_CAP_ABSOLUTE` **8.0** (absolute %, regime bands 4-6%) | tool uses absolute % only | Add **k×ADR20** as an alongside stop-cap input (not a replacement) — this is WAVE K's GROWW kill #1, already scoped there, restated here for completeness. |
| C5 | Measured move = **own-history ADR-burst** | `RR_FLOOR` **1.5** off nearest-resistance `structural_target` | tool under-measures fresh-high/IPO names | EXCEPTIONAL-family (EP/IPO) measured move should default to own-history ADR-burst instead of nearest-resistance — WAVE K's GROWW kill #2, restated here. |
| C6 | Position cap ~40% (Arora typical 25-30%) | No single locked 40% cap found; governed indirectly by open_risk × stop math | — | **Note only.** Verify no combination of stop-width + open-risk-cap can silently exceed 40% single-name exposure; if a gap is found, propose an explicit cap in a follow-up wave. |
| C7 (new, this wave) | Pyramid-to-30% ladder: 1% initial + up to 4× 1%-risk adds on higher-lows, reaching ~30% only once already in profit | No pyramid-ladder concept exists in `risk/plan.py` today (single-shot sizing only) | tool has no pyramiding primitive | Add a **pyramid-ladder proposal type** (not applied): tranche schedule = 1% risk initiate, then {1% per confirmed higher-low pullback} × up to 4, cap ~30% portfolio, gated on the position already being profitable before each add. |

## 4. Why this stays a proposal, not a patch

`risk/plan.py`'s own header states it is "the SINGLE WRITER of stop / size / R:R" and that "all
thresholds are the plan's LOCKED table — do not tune here without a LEARNINGS.md entry." The
backbone corpus is the doctrine of record for CONTENT conflicts, but changing LOCKED money math
is a decision that affects live capital and requires the user's explicit sign-off plus a
LEARNINGS.md entry per the file's own contract — this wave's mandate (APPLICATION layer: prompts/
coach/regime) does not include that authorization. **No line in `risk/plan.py` was touched.**

## 5. Recommended next step

If approved, C1/C2/C3/C6/C7 are size/config-table edits (low risk, easily reverted); C4/C5 need
the WAVE K discovery-metric plumbing (ADR20 as a first-class scan metric) to land first since the
k×ADR20 stop cap and own-history measured-move both read off it — sequence C4/C5 after K3/K4/K7
per `PLAYBOOK_TO_TOOL_MAP.md`'s own task numbering, not ahead of it.
