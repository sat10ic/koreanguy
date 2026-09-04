# Sector / Industry / Theme Linkage — Cross-Product Technical Specification
## Momentum OS | Indian Equity Momentum & Swing Trading
**Version:** 1.0  
**Status:** BUILD SPEC  
**Purpose:** Make sector, industry, theme, peer-group, and leadership-state context a first-class layer across the entire product rather than a standalone Market-page feature.

---

# 0. Executive Summary

The current product already has:

```text
Market regime
Setup detection
Candidate ranking
Stock detail
Watchlist / trigger proximity
History
Research
Desk / portfolio
```

The missing architectural layer is:

```text
SECTOR
INDUSTRY
THEME
PEER CONFIRMATION
LEADERSHIP STATE
```

These must become global context objects attached to every stock and propagated through:

```text
Tonight
Market
Candidates
Stock Detail
Watchlist
History
Research
Desk / Portfolio
Alerts
```

The intended product flow is:

```text
MARKET
  ↓
REGIME
  ↓
SECTOR / INDUSTRY / THEME
  ↓
LEADERSHIP STATE
  ↓
PEER CONFIRMATION
  ↓
STOCK
  ↓
SETUP
  ↓
ENTRY READINESS
```

This is especially important in CHOP, where broad market participation may be mediocre while narrow thematic pockets produce most of the usable momentum.

---

# 1. Core Product Thesis

A stock should not be presented as an isolated ticker.

Every actionable candidate should be understood in the context of:

```text
1. Broad market regime
2. Sector trend
3. Industry trend
4. Theme / narrative cluster
5. Theme acceleration
6. Breadth of participation
7. Peer confirmation
8. Stock leadership role inside the group
9. Setup quality
10. Entry quality
```

The system must answer:

> Is this stock strong because of a broad group move, an emerging theme, a company-specific catalyst, or only its own chart?

---

# 2. Scope

This specification covers:

```text
Sector mapping
Industry mapping
Theme mapping
Theme confidence
Theme lifecycle
Leadership state
Theme acceleration
Theme breadth
Peer confirmation
Leader / follower role
Theme setup density
Cross-product UI propagation
Ranking integration
Watchlist promotion / demotion
Alerts
History validation
Research experiments
Portfolio concentration
Beginner / Pro / Lab behavior
API contracts
Data contracts
Build sequencing
Validation rules
```

This specification does **not** define:
- new trading execution rules,
- automated position sizing,
- guaranteed theme-edge assumptions,
- unvalidated AI theme scores.

---

# 3. Governing Research Principle

Theme/sector context must not become a hard production rule merely because it is intuitively plausible.

Use:

```text
OBSERVE
  ↓
REPRESENT
  ↓
MEASURE
  ↓
VALIDATE
  ↓
PROMOTE
```

Do not use:

```text
theme strong
→ therefore buy stock
```

Theme context should initially enter as:

```text
DISPLAY CONTEXT
+
FILTER
+
RESEARCH FEATURE
```

Only later, if validated, can it become:

```text
RANK FEATURE
```

or:

```text
SETUP-SPECIFIC GATE
```

---

# 4. Global Data Hierarchy

Every stock should resolve to:

```text
SECURITY
  ├─ primary_sector
  ├─ primary_industry
  ├─ themes[]
  ├─ theme_roles[]
  ├─ theme_membership_confidence[]
  └─ peer_groups[]
```

Example:

```text
STLTECH

Sector:
Telecom / Communications Equipment

Industry:
Optical / Network Infrastructure

Themes:
AI / Data Centre Infrastructure
Fibre / Network Capex

Theme roles:
AI / DC Infrastructure → Leader
Fibre / Network Capex  → Confirmed Leader
```

Another:

```text
WELCORP

Sector:
Industrials

Industry:
Pipes

Themes:
Oil & Gas Capex
Pipeline Infrastructure
Water Infrastructure
```

A stock may belong to multiple themes.

---

# 5. Theme Is Not Sector

This distinction must be explicit everywhere.

## Sector

Relatively stable classification.

Example:

```text
Capital Goods
Auto
Chemicals
Financial Services
```

## Industry

More granular operating category.

Example:

```text
Heavy Electrical Equipment
Auto Components
Specialty Chemicals
Housing Finance
```

## Theme

Cross-sector investment narrative / economic linkage.

Example:

```text
AI / Data Centres
Power T&D
Defence Electronics
Dairy / Milk
Railway Capex
Pipeline Infrastructure
Renewable Capex
```

Themes can span multiple sectors.

---

# 6. Theme Membership Data Model

```ts
type ThemeMembership = {
  themeId: string
  securityId: string

  effectiveFrom: string
  effectiveTo?: string

  confidence:
    | 'VERIFIED'
    | 'STRONG'
    | 'MANUAL'
    | 'INFERRED'

  sourceType:
    | 'FILING'
    | 'ORDER_DISCLOSURE'
    | 'EARNINGS_COMMENTARY'
    | 'SEGMENT_EXPOSURE'
    | 'POLICY_LINK'
    | 'MANUAL'
    | 'AI_INFERRED'

  sourceReference?: string

  exposureType?:
    | 'DIRECT'
    | 'SUPPLIER'
    | 'CUSTOMER'
    | 'ENABLER'
    | 'BENEFICIARY'
    | 'ADJACENT'

  exposureStrength?: number
}
```

`exposureStrength` must not be invented unless derived from explicit structured logic.

---

# 7. Theme Confidence Rules

## VERIFIED

Direct company disclosure or explicit segment/order evidence.

Examples:
- company reports data-centre revenue,
- order win explicitly tied to power T&D,
- filing identifies specific customer/theme exposure.

## STRONG

Multiple corroborating structured sources.

## MANUAL

Human-curated mapping.

## INFERRED

Model or heuristic inference only.

Production v1 rule:

```text
VERIFIED
STRONG
MANUAL
```

may be used in display / research.

`INFERRED` must:
- be clearly labeled,
- remain excluded from production ranking by default.

---

# 8. Theme Lifecycle State

Each theme should have a state:

```text
DORMANT
AWAKENING
EMERGING
LEADING
MATURE
FADING
WEAK
```

Conceptual flow:

```text
DORMANT
  ↓
AWAKENING
  ↓
EMERGING
  ↓
LEADING
  ↓
MATURE
  ↓
FADING
  ↓
WEAK
```

This state must be derived from transparent group metrics.

Do not use an LLM to freely assign lifecycle state.

---

# 9. Theme State Evidence

Candidate inputs:

```text
theme_rs
theme_rs_acceleration
breadth_ema21
breadth_delta_5d
breadth_delta_20d
leader_count
leader_count_delta
candidate_count
candidate_density
new_20d_high_pct
new_52w_high_pct
persistence
state_age
```

The exact threshold rules should be versioned and tested.

---

# 10. Theme Acceleration

Absolute strength is insufficient.

The system must show:

```text
CURRENT
+
CHANGE
```

Example:

```text
Cables

RS             82 → 94
Breadth        48% → 76%
Leaders         3 → 9
Candidates      1 → 7

State
EMERGING FAST
```

This is often more useful than:

```text
RS = 94
```

alone.

---

# 11. Theme Freshness

Store:

```text
state_start_date
state_age_sessions
```

UI examples:

```text
Cables            6 sessions     EMERGING
Data Centres     18 sessions     LEADING
Dairy            39 sessions     FADING
Railways         74 sessions     MATURE
```

Freshness is not quality.

It is a timing/context variable.

---

# 12. Theme Breadth

For each theme:

```text
member_count
valid_member_count
pct_above_ema10
pct_above_ema21
pct_above_sma50
pct_above_sma200
pct_near_20d_high
pct_near_52w_high
```

Always store:

```text
numerator
denominator
coverage
```

Example:

```text
EMA21 breadth
9 / 12 = 75%
```

Do not display `75%` without being able to expose the denominator.

---

# 13. Breadth Acceleration

Required:

```text
breadth_delta_1d
breadth_delta_5d
breadth_delta_20d
```

Example:

```text
AI / DATA CENTRES

EMA21 breadth

5D ago        44%
Now           72%

Δ5D          +28 pp
```

This should be a primary signal for emerging leadership.

---

# 14. Peer Confirmation

Every candidate should have peer-context evidence.

Recommended fields:

```text
theme_member_count
strong_peer_count
pct_peers_above_ema21
pct_peers_rs_gt_80
pct_peers_near_20d_high
theme_candidate_count
theme_actionable_count
```

Classification:

```text
BROAD_CONFIRMATION
PARTIAL_CONFIRMATION
ISOLATED_LEADER
WEAK_CONFIRMATION
```

Do not treat `ISOLATED_LEADER` as automatically bad.

---

# 15. Theme Leader / Follower Role

Each stock may have a role inside each theme:

```text
LEADER
CONFIRMED_LEADER
FOLLOWER
LAGGARD
ISOLATED
```

Potential evidence:

```text
stock_rs_vs_theme
stock_rs_acceleration_vs_theme
stock_breakout_date_vs_theme
stock_strength_start_date
stock_contribution_to_theme_move
```

Example:

```text
STLTECH

Theme role:
LEADER

Reason:
Stock strength began before most peers
and remains above theme RS.
```

---

# 16. Setup-Specific Treatment of Theme Context

Theme context must not be applied identically to all setup families.

## Base Breakout

Theme confirmation can be highly relevant.

Potential evidence:

```text
strong theme
broad peers
candidate density
theme acceleration
```

## Pullback

Theme state can help distinguish:
- healthy continuation,
- isolated pullback in fading group.

## Momentum Burst

Theme acceleration can strengthen the context.

## IPO Base

Theme support may help but should remain secondary to IPO structure.

## Episodic Pivot

Important exception:

```text
company-specific catalyst
may be the first stock to reveal a theme
```

Therefore:

```text
lack of peer confirmation
≠ automatic rejection
```

EP should support:

```text
ISOLATED LEADER
```

as a legitimate positive/neutral state.

---

# 17. Global Stock Context Object

```ts
type StockLeadershipContext = {
  securityId: string
  tradeDate: string

  marketRegime?: string

  sectorId?: string
  sectorState?: string
  sectorRs?: number
  sectorRsDelta5d?: number

  industryId?: string
  industryState?: string
  industryRs?: number

  themes: Array<{
    themeId: string
    themeName: string
    themeState?: string
    themeRs?: number
    themeRsDelta5d?: number
    breadthEma21?: number
    breadthDelta5d?: number
    freshnessSessions?: number
    role?: string
    peerConfirmation?: string
    membershipConfidence?: string
  }>

  stockRs?: number
  stockRsDelta5d?: number

  availableAt: string
}
```

---

# 18. Tonight — Market State Integration

The Tonight page currently shows:

```text
Market State
Breadth
Opportunity Funnel
Playbook
```

It should add:

```text
LEADERSHIP POCKETS
```

especially in CHOP.

Example:

```text
LEADERSHIP POCKETS                         CHOP

THEME / GROUP          STATE       5D Δ   BREADTH   CANDS
──────────────────────────────────────────────────────────
Cables / Conductors    EMERGING     ↑↑↑      76%       7
AI / Data Centres      LEADING      ↑↑       71%       6
Pipes / Capex          EMERGING     ↑↑       68%       5
Dairy / Milk           FADING       ↓        54%       2
Railways               MATURE       →        63%       4
```

Summary:

```text
Tonight's opportunity:
Narrow leadership concentrated in
Cables · Data Centres · Industrial Capex
```

---

# 19. Tonight — Beginner View

Beginner copy:

```text
WHERE STRENGTH IS CLUSTERING

Cables
Getting stronger quickly

AI / Data Centres
Strong and still broad

Pipes / Capex
New momentum pocket
```

Avoid:

```text
RS percentile
breadth acceleration
candidate density
```

unless expanded.

---

# 20. Tonight — Pro View

Show:

```text
Theme
State
RS
RS Δ5D
Breadth
Breadth Δ5D
Candidates
Actionable
Freshness
```

---

# 21. Setup Feed — Theme Context

Every candidate row should carry compact context.

Example:

```text
STLTECH   [chart]   RS 96   READY

Cables · AI/Data Centre
Theme ↑↑ · Breadth 76% · 5 peers confirming
```

Do not add a giant panel per stock.

One compact secondary line is enough.

---

# 22. Setup Feed — Beginner Mode

Example:

```text
STLTECH
Momentum Burst

AI / Data Centres
Strong theme · getting stronger

READY
```

---

# 23. Setup Feed — Pro Mode

Example:

```text
STLTECH
Momentum Burst

Theme      AI / Data Centres
State      EMERGING
Theme RS   92
RS Δ5D     +14
Breadth    76%
Peers      6 / 9 strong
```

---

# 24. Setup Feed Sorting

Optional future sort:

```text
Theme-backed setups
```

or:

```text
Strongest leadership context
```

Do not enable until theme metrics are validated enough for ranking.

---

# 25. Candidates — New Theme Filters

Add:

```text
Theme
Theme state
Theme freshness
Theme breadth
Theme acceleration
Peer confirmation
Theme role
```

These belong behind advanced filters.

Beginner should not see all of them simultaneously.

---

# 26. Candidates — Beginner Preset

Add:

```text
[ Stocks in strong themes ]
```

Description:

```text
Find candidates whose sector or theme is also gaining strength.
```

Another:

```text
[ Emerging theme leaders ]
```

Description:

```text
Find strong stocks inside newly accelerating themes.
```

---

# 27. Candidates — Pro Filters

Example:

```text
Theme State
□ Awakening
□ Emerging
□ Leading

Theme RS
> threshold

Breadth Δ5D
> threshold

Peer confirmation
□ Broad
□ Partial
□ Isolated leader

Freshness
< N sessions
```

---

# 28. Candidates — New Landscape Modes

Add:

```text
THEME STRENGTH × STOCK QUALITY
```

Example:

```text
                       STOCK QUALITY
                            HIGH
                             ↑

      GOOD STOCK            │       PRIORITY
      WEAK THEME            │
                            │      ● STLTECH
────────────────────────────┼──────────────────→ THEME STRENGTH
                            │      ● WELCORP
                            │
       IGNORE               │       THEME PLAY
                            │       stock weaker
```

Add:

```text
THEME ACCELERATION × ENTRY QUALITY
```

This can help find fresh theme leaders before entries become extended.

---

# 29. Candidates — Beginner Naming

Instead of technical axis names:

```text
Theme Strength × Stock Quality
```

use:

```text
[ Strong stock + strong theme ]
```

Subtitle:

```text
Theme strength × Stock quality
```

For:

```text
Theme acceleration × entry quality
```

use:

```text
[ Emerging themes + good entries ]
```

---

# 30. Research Lens — Theme Integration

The CHOP Research Lens should add:

```text
Theme acceleration
Sector leadership
Peer confirmation
```

Recommended CHOP emphasis:

```text
HIGH PRIORITY
Theme acceleration
Sector leadership
Peer confirmation
RS acceleration
Entry precision
Tightness

MEDIUM
RVOL
Setup quality

LOWER
Standalone breakout with weak group support
```

---

# 31. Research Lens — Beginner

Example:

```text
CHOP LENS

Look for:
✓ Strong themes
✓ Themes getting stronger
✓ Several peers confirming
✓ Strong stock RS
✓ Precise entry
✓ Tight structure

Be careful with:
✕ Isolated weak-sector breakouts
✕ Late / extended entries
```

---

# 32. Research Lens — Pro

Example:

```text
CHOP LENS

Theme acceleration     High
Sector RS              High
Peer confirmation      High
Stock RS               High
Entry quality          High
Tightness              High
RVOL                    Medium
Setup quality           Medium
```

---

# 33. Research Lens — Lab

Expose:

```text
theme feature thresholds
state rules
coverage
validation status
weighting hypotheses
version
```

No opaque hidden "Theme Fit" score unless validated.

---

# 34. Stock Detail — Required Context Ribbon

Every stock page should include:

```text
MARKET        CHOP
SECTOR        TELECOM EQUIPMENT · LEADING
INDUSTRY      OPTICAL / NETWORK INFRA · LEADING
THEME         AI / DATA CENTRES · EMERGING ↑↑
THEME BREADTH 72% · +19 pp / 5D
STOCK RS      96 ↑
```

---

# 35. Stock Detail — Peer Strip

Add:

```text
THEME PEERS

STLTECH      96   ↑↑
SETL         93   ↑↑
ABC          88   ↑
XYZ          82   →
```

This should be compact.

Clicking a peer opens its Stock Detail.

---

# 36. Stock Detail — Beginner

Example:

```text
THEME

AI / Data Centres
Strong and getting stronger

6 related stocks are also strong

This stock:
One of the leaders
```

---

# 37. Stock Detail — Pro

Example:

```text
THEME · AI / DATA CENTRES

State              EMERGING
RS percentile      91
RS Δ5D            +14
EMA21 breadth      72%
Breadth Δ5D       +19 pp
Strong peers        6 / 9
Candidate density  44%
Freshness            7D
Role              LEADER
```

---

# 38. Stock Detail — Lab

Expose:

```text
membership evidence
mapping confidence
theme constituents
group index construction
normalization method
source references
```

---

# 39. Watchlist — Theme-Aware Promotion / Demotion

Watchlist state transitions should be allowed to consider theme context.

Example:

```text
BACKUP → FOCUS
```

Reason:

```text
Theme breadth        48% → 72%
Theme RS             71 → 89
Peer leaders          3 → 8
Stock still near pivot
```

---

# 40. Watchlist Promotion Example

```text
STLTECH
BACKUP → FOCUS

Why:
+ AI/Data Centre theme accelerating
+ Cables breadth expanding
+ 6 peers confirming
+ Stock remains near trigger
```

---

# 41. Watchlist Demotion Example

```text
WELCORP
FOCUS → BACKUP

Why:
Theme still strong,
but peer momentum is fading.
```

Important:

Do not demote automatically on one weak theme reading.

Use hysteresis / persistence rules.

---

# 42. Trigger Proximity — Theme Context

Current Home 4 groups:

```text
At Trigger
Approaching
Getting Late
Far
```

Add a compact contextual marker:

```text
STLTECH
+0.8% to trigger
Theme: AI/DC · EMERGING ↑↑
Peers: 6/9 strong
READY
```

Beginner:

```text
Theme strong
```

Pro:

```text
Theme RS 92 · breadth +19 pp
```

---

# 43. Theme Alerts

Add group-level alerts.

Example:

```text
THEME ALERT

CABLES
AWAKENING → EMERGING

Breadth       44% → 69%
RS rank       58 → 83
Leaders        3 → 8
Candidates     1 → 5
```

---

# 44. Theme Cooling Alert

```text
DATA CENTRES
LEADING → MATURE

RS remains high
but breadth and leader count are declining.
```

---

# 45. Alert Types

Supported:

```text
THEME_AWAKENING
THEME_EMERGING
THEME_LEADING
THEME_FADING
THEME_BREADTH_EXPANSION
THEME_BREADTH_COLLAPSE
PEER_CONFIRMATION_INCREASE
PEER_CONFIRMATION_DECREASE
STOCK_BECOMES_THEME_LEADER
```

---

# 46. Theme Setup Density

For each theme:

```text
member_count
candidate_count
actionable_count
candidate_density
```

Example:

```text
CABLES / CONDUCTORS

Members            17
Candidates           8
Actionable           5

SETUP MIX
Momentum Burst       3
Base Breakout        2
EP                   1
Pullback             2
```

This can reveal group-wide setup clustering.

---

# 47. Candidate Density Change

Store:

```text
candidate_count_1d
candidate_count_5d
candidate_density_1d
candidate_density_5d
```

Example:

```text
Candidates
1 → 7 in five sessions
```

This is strong evidence of emerging participation.

---

# 48. History — Theme Context Validation

History should be able to test:

```text
setup
×
market regime
×
theme state
```

Examples:

```text
Base Breakout
Emerging theme
vs
No strong theme
```

```text
EP
Isolated leader
vs
Peer-confirmed
```

```text
Theme state:
Emerging
Leading
Mature
Fading
```

---

# 49. Required Historical Metrics

Measure:

```text
trigger rate
worked rate
win rate
avg R
median R
MFE
MAE
failure rate
coverage
sample size
```

Do not promote theme context based only on visual intuition.

---

# 50. History — Beginner View

Example:

```text
THEME EFFECT

Base Breakouts historically did better
when their theme was also strengthening.

Best:
Emerging themes

Weaker:
Fading themes

Evidence:
Moderate
```

Only show if statistically supportable.

---

# 51. History — Pro View

Example:

```text
BASE BREAKOUT

THEME STATE     N     AVG R    MFE    MAE
Emerging       183   +0.71R   ...
Leading        291   +0.54R   ...
Mature         244   +0.21R   ...
Fading         102   -0.09R   ...
No theme       418   +0.18R   ...
```

---

# 52. Research — Theme Feature Experiments

Research should test:

```text
Baseline setup
vs
+ sector strength
vs
+ theme strength
vs
+ theme acceleration
vs
+ peer confirmation
vs
+ theme freshness
```

This should live in:

```text
Research → Experiments
```

---

# 53. Theme Ablation Example

```text
BASE BREAKOUT

Baseline                  +0.18R
+ Sector RS               +0.26R
+ Theme state             +0.33R
+ Theme acceleration      +0.41R
+ Peer confirmation       +0.44R
```

Only show finalized values after proper experiments.

---

# 54. Theme Feature Promotion Rule

Promote a theme feature only if it improves:

```text
QUALITY
COVERAGE
STABILITY
```

Required:
- multiple walk-forward folds,
- enough samples,
- no one-theme concentration,
- no single-year dependence,
- acceptable coverage.

---

# 55. Desk / Portfolio — Theme Concentration

Portfolio page should expose thematic concentration.

Example:

```text
PORTFOLIO

Sector concentration
Defence                 31%

Theme concentration
AI / Data Centres       27%
Power T&D               19%
```

---

# 56. Pre-Trade Theme Impact

Example:

```text
NEW TRADE: STLTECH

Theme:
AI / Data Centres

Current theme exposure      18%
After trade                 31%

Result:
Theme concentration would become high.
```

This is useful even when stocks sit in different formal sectors.

---

# 57. Cross-Sector Correlation

Themes may create hidden concentration.

Example:

```text
Stock A  Capital Goods
Stock B  Telecom
Stock C  Real Estate
```

may all belong to:

```text
Data Centres
```

The portfolio should warn on theme overlap, not only sector overlap.

---

# 58. Market Page — Discovery Integration

The dedicated Market rotation page remains responsible for:

```text
discovering
ranking
visualizing
sector / theme leadership
```

The rest of the product should **consume** that context.

The architecture is:

```text
MARKET PAGE
Discovers leadership

        ↓

GLOBAL CONTEXT SERVICE
Publishes sector/theme state

        ↓

Tonight / Candidates / Stock / Watchlist / History / Desk
consume the same state
```

Do not recompute separate theme states independently on each page.

---

# 59. Global Leadership Context Service

Recommended service:

```text
LeadershipContextService
```

Responsibilities:

```text
resolve sector
resolve industry
resolve themes
fetch group states
fetch peer confirmation
fetch stock role
fetch freshness
fetch breadth
fetch acceleration
```

---

# 60. API — Stock Context

```text
GET /stocks/{symbol}/leadership-context
```

Response:

```json
{
  "market_regime": "CHOP",
  "sector": {
    "name": "Telecom Equipment",
    "state": "LEADING",
    "rs": 88
  },
  "industry": {
    "name": "Optical / Network Infrastructure",
    "state": "LEADING",
    "rs": 91
  },
  "themes": [
    {
      "name": "AI / Data Centres",
      "state": "EMERGING",
      "rs": 92,
      "rs_delta_5d": 14,
      "breadth_ema21": 0.72,
      "breadth_delta_5d": 0.19,
      "freshness_sessions": 7,
      "peer_confirmation": "BROAD_CONFIRMATION",
      "role": "LEADER",
      "confidence": "VERIFIED"
    }
  ]
}
```

Numbers above are examples only.

---

# 61. API — Theme Summary

```text
GET /themes/{theme_id}/state
GET /themes/{theme_id}/members
GET /themes/{theme_id}/leaders
GET /themes/{theme_id}/candidates
GET /themes/{theme_id}/history
```

---

# 62. API — Leadership Pockets

```text
GET /market/leadership-pockets?horizon=5d
```

Returns:

```text
theme / group
state
RS
RS delta
breadth
breadth delta
leaders
candidates
actionable
freshness
```

---

# 63. Cache Strategy

EOD context:

```text
cache by:
trade_date
theme_id
sector_id
industry_id
```

Intraday context later:

```text
refresh every 5–15 minutes
```

only when reliable intraday data exists.

---

# 64. Beginner / Pro / Lab Translation Matrix

| Concept | Beginner | Pro | Lab |
|---|---|---|---|
| Theme state | Strong / Getting stronger / Fading | Emerging / Leading / Mature / Fading | Raw rule state |
| Theme RS | Strong vs market | RS percentile / ratio | Formula |
| Breadth | Many peers participating | EMA21 breadth % | Numerator / denominator / coverage |
| Breadth acceleration | More peers joining | Δ5D pp | Raw series |
| Peer confirmation | Several related stocks are also strong | 6/9 strong peers | Constituent-level evidence |
| Freshness | New move / established move | 7 sessions | State transition history |
| Theme role | Leader / Follower | LEADER / FOLLOWER / ISOLATED | Role formula |
| Theme confidence | Verified / Curated | VERIFIED / STRONG / MANUAL | Source evidence |
| Candidate density | Many setups forming | 44% | Constituent scan join |
| Theme concentration | Many positions depend on same theme | 27% account exposure | Exposure calculation |

---

# 65. Beginner Copy Rules

Prefer:

```text
Strong theme
Getting stronger
Several peers confirming
New move
Mature move
Theme fading
```

Avoid by default:

```text
RS percentile
breadth delta
candidate density
peer-confirmation ratio
state hysteresis
```

---

# 66. Pro Copy Rules

Use exact metrics:

```text
Theme RS 92
RS Δ5D +14
Breadth 72%
Breadth Δ5D +19 pp
Peers 6 / 9
Candidate density 44%
Freshness 7D
```

---

# 67. Lab Copy Rules

Expose:

```text
theme membership source
confidence
group construction
normalization
coverage
state transition rules
raw constituent list
version
```

---

# 68. Missing Data Rules

If theme mapping is unavailable:

```text
Theme context unavailable
```

Do not invent one.

If breadth coverage is low:

```text
Low coverage
```

Do not show a confident theme state.

If peer count is too small:

```text
Small peer group
```

Do not overstate confirmation.

---

# 69. Small Theme Guard

Suggested:

```text
member_count < 4
→ LOW_SAMPLE
```

Such themes may still be displayed but should not receive strong breadth labels without warning.

---

# 70. Theme Duplication / Overlap

A stock may belong to multiple overlapping themes.

Example:

```text
AI / Data Centres
Network Infrastructure
Fibre Capex
```

Do not double-count the same underlying exposure in portfolio concentration without overlap handling.

Store:

```text
theme_parent_id
theme_cluster_id
```

where useful.

---

# 71. Theme Taxonomy Governance

Theme taxonomy needs versioning.

```text
theme_taxonomy_version
membership_version
effective_date
```

Changes must preserve history.

Do not rewrite old theme assignments retroactively without versioning.

---

# 72. Theme Discovery — Later AI Layer

Future pipeline:

```text
filings
news
orders
earnings calls
policy events
co-movement
candidate clustering

      ↓

AI theme proposal

      ↓

human / rule review

      ↓

VERIFIED / STRONG / MANUAL

      ↓

price + breadth confirmation
```

AI proposes.

The production system decides using structured evidence.

---

# 73. Theme Read-Through

Future advanced feature:

```text
EVENT AT STOCK A
      ↓
A reacts strongly
      ↓
related names begin strengthening
      ↓
theme breadth expands
```

Store event linkage:

```text
origin_event
origin_stock
related_theme
peer_reaction_start
breadth_expansion_date
```

This can later support thematic propagation research.

---

# 74. Theme Read-Through UI

Example:

```text
THEME READ-THROUGH

Origin:
Stock A earnings / order event

Theme:
Cables

Reaction:
5 peers strengthened over 2 sessions
Breadth 41% → 68%
```

Research-only initially.

---

# 75. Theme Role in EPs

EP-specific rule:

```text
EP can be:
ISOLATED
LEADING
PEER_CONFIRMED
```

Do not penalize isolated EPs automatically.

An EP may become the first evidence of a new theme.

---

# 76. Theme Role in Base Breakouts

Base Breakout can use:

```text
Theme confirmation
Theme acceleration
Peer breadth
```

as research features.

These may eventually improve ranking if validated.

---

# 77. Theme Role in Pullbacks

Pullback quality may improve when:

```text
theme remains leading
stock remains leader
peer breadth stays healthy
```

A pullback in a fading theme may deserve lower priority.

Again: research first.

---

# 78. Theme Role in Momentum Bursts

Momentum Burst should capture:

```text
theme acceleration
candidate density spike
peer expansion
```

because bursts often cluster.

---

# 79. Theme Role in IPO Bases

IPO Base should show theme context but remain primarily structure-led.

Potential presentation:

```text
IPO structure strong
Theme support present
```

rather than requiring theme confirmation.

---

# 80. Theme-Aware Watchlist State Machine

Current:

```text
DEVELOPING
→ BACKUP
→ FOCUS
→ TRIGGERED
```

Theme context may influence transitions but should not solely determine them.

Example:

```text
BACKUP
→ FOCUS

requires:
stock readiness improves
AND/OR
theme context improves
```

The reason list should identify which factor changed.

---

# 81. Audit Trail

Every automatic watchlist transition should record:

```text
old_state
new_state
timestamp
stock_reasons[]
theme_reasons[]
sector_reasons[]
```

Example:

```text
theme_reasons:
- breadth +18 pp
- state AWAKENING → EMERGING
```

---

# 82. Ranking Transparency

If theme features affect candidate rank later, expose:

```text
WHY THIS RANKS HIGH

+ Stock RS 96
+ Theme emerging
+ Breadth expanding
+ 6 peers confirming
+ Entry near trigger

− Stop room only fair
```

Do not hide theme contribution inside one composite.

---

# 83. Beginner Ranking Explanation

Example:

```text
WHY THIS IS INTERESTING

Strong stock
Strong theme
Several related stocks confirming
Entry still reasonable
```

---

# 84. Pro Ranking Explanation

Example:

```text
Stock RS              96
Theme RS              92
Theme RS Δ5D         +14
Breadth               72%
Breadth Δ5D          +19 pp
Peer confirmation      6 / 9
Entry quality          81
```

---

# 85. History — Theme Edge Research Design

Test:

```text
SETUP × THEME STATE
SETUP × THEME ACCELERATION
SETUP × PEER CONFIRMATION
SETUP × STOCK ROLE
```

Examples:

```text
Base Breakout × Emerging Theme
Base Breakout × No Theme
EP × Isolated Leader
EP × Peer Confirmed
Pullback × Leading Theme
Pullback × Fading Theme
```

---

# 86. Research Controls

For valid experiments, condition on:

```text
market regime
liquidity
market cap
setup family
sector
time period
```

Avoid attributing theme edge to hidden confounders.

---

# 87. Anti-Leakage Rules

Historical theme state must be point-in-time.

Do not use current theme membership to backfill old dates unless historically valid.

Do not use:
- future theme labels,
- later company disclosures,
- later peer membership,
- future breadth.

Every theme record needs:

```text
effective_from
effective_to
available_at
```

---

# 88. Historical Theme Membership

If a company only became associated with a theme later, do not assume it belonged to the theme historically.

Theme mapping must be temporal.

---

# 89. Theme Index Construction

For each theme:

Recommended v1:

```text
equal-weight member index
```

Also optionally store:

```text
liquidity-weighted index
```

Do not use a single mega-cap-dominated index for breadth analysis.

---

# 90. Theme Relative Strength

Possible:

```text
theme_rs_ratio =
theme_index / NIFTY_500
```

Store:

```text
rs_1d
rs_5d
rs_20d
rs_60d
rs_126d
```

---

# 91. Theme Acceleration Formula

Recommended:

```text
short_slope =
slope(theme_rs_ratio over 5 sessions)

medium_slope =
slope(theme_rs_ratio over 20 sessions)

theme_rs_acceleration =
short_slope - medium_slope
```

Freeze formula/version.

---

# 92. Peer Strength Definition

Define a peer as strong using explicit rules, e.g.:

```text
RS percentile >= configured threshold
AND
price above EMA21
```

Do not let "strong peer" be free-form.

Version the rule.

---

# 93. Theme Candidate Density

```text
candidate_density =
candidate_count / valid_member_count
```

Show:

```text
candidate_count
actionable_count
density
```

---

# 94. Leadership Concentration

Theme strength can be broad or narrow.

Potential metric:

```text
top3_contribution
```

UI:

```text
BROAD
MIXED
CONCENTRATED
```

Example:

```text
AI / Data Centres
Breadth 72%
Top-3 contribution 31%
Leadership quality BROAD
```

---

# 95. Theme State Confidence

Store:

```text
state_confidence
coverage
member_count
```

If:
- too few members,
- too much missing data,
- mapping confidence low,

then:

```text
state = UNCERTAIN
```

---

# 96. Global Theme Badges

Badges should be minimal.

Beginner:

```text
Strong theme
Emerging theme
Theme fading
```

Pro:

```text
EMERGING
LEADING
MATURE
FADING
```

Do not add a badge for every theme metric.

---

# 97. UI Density Rule

Theme context should not turn every row into a paragraph.

Recommended:

```text
Primary line:
Stock / Setup / State

Secondary line:
Sector · Theme · Theme state

Tooltip / expand:
all metrics
```

---

# 98. Data Quality Indicator

If theme data is incomplete:

```text
Theme data partial
```

Pro:

```text
Coverage 7/11 members
```

Lab:
full missingness.

---

# 99. Build Order

## Phase 1 — Data foundation

Build:
- sector mapping
- industry mapping
- theme taxonomy
- theme membership
- versioning
- confidence
- effective dates

## Phase 2 — Group state engine

Build:
- theme index
- RS
- breadth
- acceleration
- freshness
- lifecycle state
- peer confirmation
- leader/follower role

## Phase 3 — UI propagation

Integrate into:
- Tonight
- Setup Feed
- Candidates
- Stock Detail
- Watchlist
- Trigger Proximity

## Phase 4 — History / Research

Build:
- theme-state outcome studies
- setup × theme tests
- ablations
- promotion criteria

## Phase 5 — Portfolio

Add:
- theme concentration
- hidden cross-sector concentration
- pre-trade theme exposure impact

## Phase 6 — Theme discovery

Research-only AI proposal layer.

---

# 100. Acceptance Tests

## Tonight

User should answer:

```text
Which themes are working tonight?
Which are emerging?
Which are fading?
```

within 10 seconds.

## Candidate Row

User should answer:

```text
Is this stock part of a broader move?
```

without opening Market page.

## Stock Detail

User should answer:

```text
What sector/theme is driving this?
How broad is the confirmation?
Is this stock a leader or follower?
```

within one screen.

## Watchlist

User should understand whether:

```text
stock improved
theme improved
or both
```

caused promotion.

## History

User should be able to compare:

```text
setup with theme confirmation
vs
setup without theme confirmation
```

## Desk

User should see hidden theme concentration across sectors.

---

# 101. Visual QA Fail Conditions

Reject implementation if:

- theme is only a single column with no state,
- sector and theme are treated as synonyms,
- theme state is shown without breadth/RS evidence,
- current strength is shown without acceleration,
- theme mapping has no confidence/source,
- inferred themes are presented as facts,
- no point-in-time membership exists,
- EPs are penalized for missing peer confirmation,
- watchlist state changes silently depend on theme context,
- portfolio only measures sector concentration,
- theme metrics create excessive row clutter.

---

# 102. Anti-Hallucination Rules

The system MUST NOT:

1. infer theme membership from ticker name alone,
2. invent a theme because several stocks rose together,
3. call a theme "institutional" without direct evidence,
4. call a peer group broad when member coverage is low,
5. treat an AI-suggested theme as verified,
6. backfill current theme membership into historical dates without evidence,
7. fabricate peer confirmation when membership is incomplete,
8. hard-code theme ranking advantage before validation,
9. treat an isolated EP as automatically weak,
10. silently change theme taxonomy historically.

---

# 103. Final Cross-Product Architecture

```text
                         MARKET
                            │
                         REGIME
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
         SECTOR                           THEME
            │                               │
            └───────────────┬───────────────┘
                            ▼
                    LEADERSHIP STATE
                            │
                   ┌────────┴────────┐
                   ▼                 ▼
               PEER GROUP          STOCK
                   │                 │
                   └────────┬────────┘
                            ▼
                         SETUP
                            │
                            ▼
                     ENTRY READINESS
                            │
                            ▼
                        WATCHLIST
                            │
                            ▼
                         DESK
                            │
                            ▼
                        HISTORY
                            │
                            ▼
                       RESEARCH
```

---

# 104. Final Product Principle

The Market page should **discover** leadership.

The rest of the product should **consume and explain** that leadership.

The tool should no longer present:

```text
STLTECH
Momentum Burst
RS 96
READY
```

as an isolated setup.

It should present:

```text
STLTECH
Momentum Burst
READY

AI / Data Centres
Emerging theme
Broad peer confirmation
Stock is one of the leaders
```

with Pro/Lab modes exposing the exact evidence.

That turns sector/theme context from a decorative tag into a **first-class decision layer across Momentum OS**.
