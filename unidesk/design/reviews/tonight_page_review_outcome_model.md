# Tonight Page Review — Outcome Model & Setup Feed Notes
## Momentum OS
**Status:** UX / Product Review Addendum  
**Scope:** Current Tonight page screenshots, with specific focus on Setup Feed readability, cleanliness/stop-room indicators, and the outcome basis for Prior Calls.

---

# 1. Current Page Direction

The new Tonight page is materially clearer than the earlier version.

The current flow is:

```text
MARKET STATE
    ↓
SETUP FEED
    ↓
PRIOR CALLS
    ↓
TRIGGER PROXIMITY
```

This is a sensible nightly workflow:

```text
What kind of market is this?
        ↓
What setups exist?
        ↓
What happened to prior ideas?
        ↓
What is becoming actionable now?
```

The current information hierarchy is broadly correct.

---

# 2. Setup Feed — Cleanliness and Stop-Room Bars

The new setup rows include compact bar-style indicators representing:

```text
CLEANLINESS
STOP ROOM
```

This is a good direction because it adds useful structure without reverting to large candidate cards.

Example conceptual row:

```text
DEEPINDS   [mini chart]   Top 15% · high volume   +0.6%   4.6%   ▮▮▮□ Fair   ▮▮□□ Tight   REJECT
```

## Recommended naming

The labels should remain explicit enough that a new user does not mistake the bars for generic scores.

Preferred:

```text
Structure
Stop room
```

or:

```text
Cleanliness
Stop room
```

Avoid unlabeled bar widgets.

## Cleanliness

Cleanliness should represent only defined structural evidence.

Possible inputs may include:

```text
overlap
range contraction
pivot cleanliness
failed-breakout noise
base compactness
bar-to-bar volatility
```

Do not allow the frontend to infer a cleanliness score independently.

If the backend currently produces:

```text
Fair
Choppy
Very choppy
```

the bars should simply visualize that backend state.

## Stop Room

Stop room should answer:

> Is the structural stop sensible relative to the stock's normal movement?

This is different from simply showing stop distance.

The current warning:

```text
25 of 45 candidates have stops inside 0.75 thrust-days
```

is useful because it compares structural risk with normal stock movement.

Preferred labels:

```text
ROOMY
FAIR
TIGHT
TOO TIGHT
```

Do not imply that a wider stop is automatically better.

---

# 3. Prior Calls — Main Unresolved Issue

The current Prior Calls panel cannot be fully meaningful until the system explicitly defines:

```text
What counts as a win?
What counts as a loss?
When is the setup judged?
```

A single next-day rule is too crude because the page contains multiple setup families.

For example:

```text
EP / Momentum Burst
```

may reasonably be judged faster than:

```text
Base Breakout / IPO Base
```

A next-day-only outcome model would compress very different setup horizons into one rule.

---

# 4. Recommended Solution — Two Outcome Layers

Use:

```text
1. STANDARDIZED OUTCOME
2. SETUP-NATIVE OUTCOME
```

These serve different purposes.

---

# 5. Standardized Outcome

Use this for:

```text
Tonight → Prior Calls
```

because the Tonight page needs one comparable scorecard.

Conceptual model:

```text
Entry = defined trigger
Stop = defined invalidation / structural stop
Review horizon = setup-family default

Then evaluate which event occurred first.
```

Recommended standardized states:

```text
NO TRIGGER
WORKED
WIN
STOPPED
FLAT
OPEN
NO DATA
PATH AMBIGUOUS
```

Definitions:

```text
NO TRIGGER
Setup never crossed its trigger before expiry / invalidation.

WORKED
Reached +1R before -1R.

WIN
Reached +2R before -1R.

STOPPED
Reached -1R first.

FLAT
Triggered, but neither threshold was reached before review horizon expired.

OPEN
Applicable review horizon has not yet elapsed.

NO DATA
Insufficient or invalid market data.

PATH AMBIGUOUS
Daily bar touched both favorable and adverse thresholds and intraday order is unknown.
```

This creates a common language across setup types.

---

# 6. Why Keep WORKED Separate from WIN

A binary:

```text
WIN / STOPPED
```

loses too much information.

Example:

```text
Entry        ₹100
Stop         ₹95
1R           ₹105
2R           ₹110

Price reaches ₹107
then stalls
```

This setup:

```text
WORKED
```

but did not become a full:

```text
WIN
```

That distinction is useful for evaluating:

- setup quality,
- stop quality,
- follow-through quality,
- whether exits are too ambitious.

---

# 7. Setup-Family Review Horizons

Do not use one next-day horizon for every setup.

Suggested initial research defaults:

| Setup family | Initial review horizon |
|---|---:|
| Episodic Pivot | 3–5 bars |
| Momentum Burst | 3–5 bars |
| Inside Bar | 5–10 bars |
| Base Breakout | ~10 bars |
| IPO Base | 10–15 bars |
| Pullback | 5–10 bars |
| Reversal / Reclaim | 5–10 bars |
| Power Play | 5–10 bars |

These are **starting research defaults**, not production truth.

They should be:

```text
configurable
versioned
historically validated
```

Do not silently tune them after observing performance.

---

# 8. Setup-Native Outcome

Use the deeper layer in:

```text
History
Stock Detail
Research
Replay
```

The native outcome can reflect the actual behavior expected from each setup family.

## Episodic Pivot

Relevant native evaluation may include:

```text
Day-0 trigger
Day-0 risk-free
Day-1 follow-through
Day-3 follow-through
gap retention
AVWAP hold
reset / pullback formation
```

## Momentum Burst

Relevant native evaluation:

```text
immediate expansion
3–5 bar continuation
MFE
MAE
failure speed
```

## Base Breakout

Relevant native evaluation:

```text
breakout hold
follow-through
retest behavior
10-bar outcome
MFE / MAE
```

## IPO Base

Relevant native evaluation:

```text
breakout hold
10–15 bar continuation
listing AVWAP behavior
structural stop survival
```

## Reversal / Reclaim

Relevant native evaluation:

```text
reclaimed level held
follow-through
failure back below reclaim
```

The Tonight page should not expose all this detail by default.

---

# 9. Tonight Page — Recommended Prior Calls Header

Recommended:

```text
PRIOR CALLS

Newest completed review cohort

[ Standard ] [ Setup-native ]
```

Default:

```text
Standard
```

For Beginner mode, the setup-native option may live inside:

```text
Details
```

rather than as a primary toggle.

---

# 10. Standard Scorecard Example

Recommended compact summary:

```text
PRIOR CALLS

0 WIN
3 WORKED
10 STOPPED
4 FLAT
19 OPEN
1 NO TRIGGER
1 NO DATA

Avg outcome     +0.2R
Avg MFE         +1.4R
Avg MAE         -0.6R

Basis:
+1R = worked
+2R = win
-1R = stopped
Review horizon = setup-family default
```

Do not show an average such as:

```text
avg -1.00R n=10
```

without making clear:

- which calls entered the denominator,
- whether only stopped trades were included,
- whether open/no-trigger calls were excluded.

---

# 11. Prior Calls Strip

The visual strip is useful.

Recommended states:

```text
W   = Win
+   = Worked
S   = Stopped
F   = Flat
O   = Open
—   = No Data
NT  = No Trigger
```

Do not rely on color alone.

Hover should show:

```text
Symbol
Setup
Entry date
Review horizon
Current outcome
MFE
MAE
```

Example:

```text
DIFFNKG
Base Breakout

Horizon        10 bars
Outcome        Worked
MFE            +1.6R
MAE            -0.3R
```

---

# 12. Outcome State Machine

Recommended:

```text
CANDIDATE
    ↓
WAITING FOR TRIGGER
    │
    ├─ horizon expires / invalidates before trigger
    │      ↓
    │   NO TRIGGER
    │
    └─ trigger occurs
           ↓
        ACTIVE
           │
           ├─ -1R first
           │     ↓
           │   STOPPED
           │
           ├─ +1R first
           │     ↓
           │   WORKED
           │       │
           │       ├─ +2R later
           │       │      ↓
           │       │     WIN
           │       │
           │       └─ horizon expires
           │              ↓
           │            WORKED
           │
           └─ neither threshold reached by horizon
                  ↓
                FLAT
```

`OPEN` is used while the applicable horizon is still active.

---

# 13. First-Touch Ordering Must Be Preserved

For every triggered setup, calculate:

```text
time_to_stop
time_to_1R
time_to_2R
```

Outcome depends on ordering.

Example:

```text
+1R reached first
then -1R
```

is not the same as:

```text
-1R reached first
then +1R
```

Daily bars may not reveal intraday ordering if both levels are touched in the same session.

In this case:

```text
PATH_AMBIGUOUS
```

is preferable to guessing.

---

# 14. Daily-Data Ambiguity Rule

If one daily candle touches:

```text
stop
AND
+1R
```

and intraday bars are unavailable, possible policies are:

### Conservative
Assume adverse threshold occurred first.

### Preferred for research truth
Mark:

```text
PATH_AMBIGUOUS
```

until intraday data resolves it.

Do not silently make the favorable assumption.

---

# 15. MFE / MAE

Prior Calls should eventually calculate:

```text
MFE = Maximum Favorable Excursion
MAE = Maximum Adverse Excursion
```

expressed preferably in:

```text
R
```

Example:

```text
Avg MFE    +1.4R
Avg MAE    -0.6R
```

These are often more informative than win rate.

They help answer:

```text
Did the setup fail?
or
Was the stop too tight?
```

---

# 16. Suggested Tonight-Level Complexity

The Tonight page should remain simple.

Recommended visible level:

```text
0 wins
3 worked
10 stopped
4 flat
19 open

Avg +0.2R
```

Then one small line:

```text
Standard basis · setup-family horizon
```

Hover / Details:

```text
Worked = +1R before -1R
Win = +2R before -1R
```

Do not put the full family-specific outcome specification directly into Tonight.

---

# 17. History Page

History should contain the deeper analysis.

Recommended columns:

```text
STOCK
SETUP
TRIGGER DATE
HORIZON
RESULT
R
MFE
MAE
NATIVE OUTCOME
FAILURE REASON
REPLAY
```

Example:

```text
DIFFNKG
IPO Base
10-bar horizon
Worked
+1.3R final
+1.8R MFE
-0.4R MAE
Breakout held, follow-through weak
```

---

# 18. Setup-Native Detail Example

```text
DIFFNKG
IPO BASE

STANDARD OUTCOME
Worked

Horizon       10 bars
MFE           +1.6R
MAE           -0.3R

SETUP-NATIVE
Breakout held          ✓
Listing AVWAP held     ✓
Follow-through         Weak
Base invalidated       No
```

This is where complexity belongs.

---

# 19. Research Separation

The standardized scorecard and setup-native research answer different questions.

## Standardized

```text
Which setup families produced favorable excursion relative to risk?
```

Useful for:
- cross-setup comparison,
- broad nightly scorecard,
- common performance reporting.

## Setup-native

```text
Did the setup behave the way this setup is supposed to behave?
```

Useful for:
- detector validation,
- strategy design,
- execution improvement,
- historical research.

Both should exist.

---

# 20. Avoid These Outcome Definitions

Do not use:

```text
next-day green = win
next-day red = loss
```

Do not use:

```text
current price above entry = win
```

Do not use:

```text
candidate no longer in scanner = stopped
```

Do not use:

```text
10 bars elapsed = automatically flat
```

without first checking:
- trigger,
- stop,
- favorable excursion,
- event order.

---

# 21. Recommended Backend Fields

```yaml
call_outcome:
  symbol:
  setup_type:
  candidate_date:

  trigger_price:
  trigger_date:
  trigger_time:

  stop_price:
  stop_type:

  risk_per_share:

  review_horizon_bars:

  first_touch_1r:
  first_touch_2r:
  first_touch_stop:

  time_to_1r:
  time_to_2r:
  time_to_stop:

  mfe_r:
  mae_r:
  final_r:

  standardized_state:
    NO_TRIGGER |
    ACTIVE |
    WORKED |
    WIN |
    STOPPED |
    FLAT |
    NO_DATA |
    PATH_AMBIGUOUS

  setup_native_state:
  review_complete:
```

---

# 22. UI Recommendation for the Current Screen

Current concept:

```text
2026-08-20 · 10 sessions ago
0 won
10 stopped
19 still open
1 no data
avg -1.00R
```

Recommended concept:

```text
2026-08-20 · completed review cohort

WIN
WORKED
STOPPED
FLAT
OPEN
NO TRIGGER
NO DATA

Avg outcome
Avg MFE
Avg MAE

Standard basis · family-specific review horizon
```

Use backend-generated values only.

---

# 23. Final Recommendation

Use:

```text
TONIGHT
→ standardized R-based outcome
→ setup-family review horizon

HISTORY / STOCK DETAIL / RESEARCH
→ setup-native evaluation
```

This gives the system:

```text
comparability
+
setup-specific accuracy
+
low Tonight-page clutter
+
better research fidelity
```

---

# 24. Overall Review Verdict

The new Tonight page is moving in the right direction.

Strong improvements already visible:

```text
Market state hierarchy
Compact setup rows
Real chart thumbnails
Cleanliness indicator
Stop-room indicator
Trigger-proximity grouping
Clearer Beginner / Pro / Lab separation
```

The primary unresolved product issue is now:

```text
OUTCOME SEMANTICS
```

Once the standardized-vs-native outcome model is implemented, the Tonight page will have a much more coherent loop:

```text
MARKET
→ SETUPS
→ OUTCOMES
→ ACTIONABLE WATCH
```

without becoming overly complex.

---

# Candidates Screen Review — Progressive Disclosure, Research Lens & Table Simplification

## 26. Current Candidates Screen — Diagnosis

The Candidates screen has a strong analytical foundation, but the current default presentation is too close to a **research workbench / Lab view** for a beginner-facing product.

The problem is not the number of capabilities.

The problem is that too many capabilities are exposed simultaneously without clearly explaining:

```text
what each control does
why it matters
what question it answers
what action it should lead to
```

The current screen appears to expose, at once:

```text
8 setup filters
+
multiple lifecycle-state filters
+
preset selector
+
5 opportunity-landscape modes
+
research-lens chips
+
many table column toggles
+
row checkboxes
```

This creates excessive cognitive load before the user has understood the page's main job.

The key principle should be:

> **Do not remove analytical depth. Reduce how much of that depth is exposed by default.**

---

# 27. Candidates Screen — Primary User Question

The page should first help the user answer:

```text
What kind of candidate am I trying to find?
```

Instead of starting with technical filters, begin with understandable research intents.

Recommended preset-style entry points:

```text
WHAT DO YOU WANT TO FIND?

[ Best opportunities ]
Strong setup + sensible entry

[ Early leaders ]
Strong stocks before they become obvious

[ Tight setups ]
Compressed stocks close to expansion

[ Momentum bursts ]
Stocks showing fresh urgency

[ Safer entries ]
Good setups with enough stop room
```

These presets should configure the underlying filters and landscape automatically.

The user should still be able to inspect the exact filters that were applied.

---

# 28. Replace the Filter Wall with a Compact Research Bar

Current persistent filter buttons are too numerous.

Recommended default:

```text
VIEW
[ Best opportunities ▼ ]

FILTERS
Setup: Any
State: Actionable
Sector: Any
[ More filters ]

SORT
Actionability

[ Reset ]
```

The full filter set should move into:

```text
More filters
```

drawer / popover.

Suggested grouping:

```text
SETUP
□ Momentum Burst
□ Episodic Pivot
□ IPO Base
□ Inside Bar
□ Base Breakout
□ Pullback
□ Reversal / Reclaim
□ Power Play

READINESS
□ Prime
□ Ready
□ Near Pivot
□ Watch
□ Extended

RISK / TRADEABILITY
□ Good stop room
□ Exclude low liquidity
□ Exclude extended
□ Exclude loose structure

STRUCTURE
□ Tight
□ Clean
□ VCP-like
```

The filter drawer should use the user's existing Beginner / Pro / Lab modes.

---

# 29. Presets Must Explain the Trading Objective

Every preset should explain **what it helps find**, not merely the metrics it activates.

## Best Opportunities

```text
Find stocks combining:
• strong setup quality
• strong relative strength
• reasonable current entry
• acceptable stop room
```

## Tight Setups

```text
Find stocks whose recent price ranges are compressing near a trigger.

Useful for:
breakouts
VCP-style setups
low-risk expansion entries
```

## Early Leaders

```text
Find stocks whose relative strength is improving
before entry quality becomes obvious.

Useful for:
watchlist building
early theme leadership
future breakout candidates
```

## Momentum Bursts

```text
Find stocks showing fresh urgency.

Useful for:
EPs
rapid expansion
strong short-term momentum
```

## Safer Entries

```text
Find valid setups where the structural stop
is not sitting inside normal daily price noise.
```

---

# 30. Opportunity Landscape — Keep the Capability, Simplify the Language

The Opportunity Landscape is one of the best concepts on the page.

The issue is naming and explanation.

Current technical modes such as:

```text
Cleanliness × Entry
Setup × Entry
RS × Accumulation
Tightness × Entry
Risk × Reward
```

are understandable to an advanced user but not intuitive to a beginner.

Recommended Beginner labels:

```text
[ Best setups ]
[ Best entries ]
[ Emerging leaders ]
[ Tight breakouts ]
[ Risk / Reward ]
```

Pro mode can show the technical subtitle underneath:

```text
TIGHT BREAKOUTS
Tightness × Entry
```

Example explanation:

```text
Find stocks with clean/tight structure
and sensible current entry positioning.

↑ cleaner structure
→ better entry

Top-right = preferred combination
```

---

# 31. Opportunity Landscape — Quadrant Labels

Quadrants should answer a trading question.

Recommended:

```text
                     CLEAN / STRONG STRUCTURE
                              HIGH
                               ↑

           WATCH               │        BEST AREA
                               │
                               │
───────────────────────────────┼──────────────────→ ENTRY QUALITY
                               │
           AVOID               │        LATE / RISKY
                               │
```

The current terms such as:

```text
WATCH
PRIME ZONE
IGNORE
SPECULATIVE
```

are usable, but the page should still explain what the axes mean.

A short explanation should always be visible:

```text
How to read this:
↑ better structure
→ better current entry
Top-right is preferred
```

---

# 32. Research Lens — Current Issue

The current Research Lens is underused.

At present it behaves mostly like:

```text
CHOP

RS
RVOL
Tightness
Entry precision
Setup quality
```

with a short explanatory sentence.

That does not yet justify the panel's screen space.

It should become:

```text
CONTEXT
+
INTERPRETATION
+
FILTER ACTION
```

rather than only a regime label.

---

# 33. Research Lens — Recommended Beginner Version

Example for the current CHOP environment:

```text
RESEARCH LENS                             CHOP

WHAT MATTERS MOST NOW

1. Relative leadership
   Prefer stocks outperforming the market.

2. Entry precision
   Avoid chasing too far beyond trigger.

3. Tight structure
   Cleaner bases matter more in chop.

4. Stop room
   Reject stops sitting inside normal noise.

5. Sector confirmation
   Prefer narrow pockets of real leadership.

────────────────────────────────

CURRENT CANDIDATE SET

62 candidates
18 fit the CHOP lens
7 strong fits
3 near entry

[ Show strongest CHOP fits ]
```

This gives the panel a practical purpose.

---

# 34. Research Lens Must Be Operational

The Research Lens should control the page.

Clicking:

```text
Show strongest CHOP fits
```

should visibly apply filters such as:

```text
strong RS
acceptable tightness / cleanliness
acceptable entry quality
not extended
not low liquidity
```

Important:

This must **not** be an opaque AI action.

The UI should show exactly what changed.

Example:

```text
APPLIED CHOP LENS

RS                 strong
Tightness          acceptable+
Entry quality      acceptable+
Low liquidity      excluded
Extended           excluded

[ Clear lens ]
```

If exact thresholds exist, Pro/Lab may expose them.

---

# 35. Research Lens — Why the Regime Changes Priorities

The page should explain why the active regime changes what matters.

Example:

```text
WHY THESE METRICS?

In CHOP:
generic breakouts fail more often.

The current lens therefore pays more attention to:
• isolated RS leaders
• tight structure
• precise entries
• good stop room
```

This should be template-driven from deterministic regime state, not generic runtime LLM prose.

---

# 36. Research Lens — Mode-Specific Behavior

## Beginner

```text
CHOP

Focus on:
Strong leaders
Tight setups
Precise entries
Good stop room

18 candidates fit
```

## Pro

```text
CHOP LENS

RS rank           High emphasis
RS acceleration   High
Tightness          High
Entry quality      High
RVOL               Medium
Setup quality      Medium
Extension penalty  High
```

## Lab

```text
CHOP LENS v0.x

UI / research heuristic
not production scoring unless validated

rs_percentile           ...
tightness_percentile    ...
entry_percentile        ...
extension threshold     ...
```

---

# 37. Ranked Research Table — Current Issue

The current Ranked Research Table appears to expose advanced fields such as:

```text
Stock
Setup
Sector
Quality
Entry
RS
RS Δ1D
RVOL
Tightness
RS10D / trend
R:R
CHOP
Stop / Thrust
State
```

This is useful for advanced research.

It is too dense for Beginner mode.

The current view is better classified as:

```text
PRO / LAB
```

than:

```text
BEGINNER
```

---

# 38. Ranked Research Table — Beginner Preset

Recommended Beginner columns:

```text
STOCK
SETUP
WHY INTERESTING
ENTRY
STOP ROOM
STATE
```

Example:

```text
INDOTECH    Inside Bar    Strong RS · clean setup    Fair    Good    PRIME
BOSCHLTD    Inside Bar    Strong setup               Good    Good    PRIME
INGERGRAND  Inside Bar    Clean setup                Fair    Tight   PRIME
```

Expand / hover can show:

```text
RS           97
Tightness    0.66
R:R          1.6R
```

---

# 39. Ranked Research Table — Pro Preset

Recommended Pro columns:

```text
STOCK
SETUP
SECTOR
QUALITY
ENTRY
RS
RS Δ
RVOL
TIGHTNESS
R:R
STOP ROOM
STATE
```

This is close to the current table density.

---

# 40. Ranked Research Table — Lab Preset

Lab can expose:

```text
DRS
thrust
chop
raw ranks
trend deltas
experimental scores
metric coverage
debug provenance
alternative formulas
```

The current screen's broad metric exposure belongs primarily here.

---

# 41. Incomplete Columns Must Not Be Default

The screenshot contains many:

```text
—
```

values.

A default table should not expose a metric if it is missing for most rows.

Recommended coverage rule:

```text
if metric coverage < 70%:
    hide from Beginner default
```

Pro may show the metric with coverage information.

Lab may show all raw fields.

Important missing-value distinctions:

```text
—
```

must not ambiguously mean all of:

```text
not applicable
missing
not computed
insufficient history
```

Internally preserve separate states:

```text
NOT_APPLICABLE
MISSING_DATA
NOT_COMPUTED
INSUFFICIENT_HISTORY
```

Tooltips can expose them.

---

# 42. Data Coverage Indicator

Add a compact coverage signal.

Example:

```text
TABLE DATA

Core metrics       96% complete
Advanced metrics   61% complete
```

Or in the Columns menu:

```text
RS Δ1D          41 / 62
RVOL            62 / 62
Tightness       58 / 62
DRS             12 / 62
```

This helps distinguish true missing data from bugs.

---

# 43. Checkbox Affordance — Fix or Remove

The current row checkboxes imply:

```text
I can select multiple stocks and do something useful.
```

If they do nothing, they should be removed.

Two acceptable solutions:

## Option A — Remove

Use until bulk actions exist.

## Option B — Implement Compare / Watchlist Workflow

This is preferred because it fits the Candidates Research Lab.

Example:

```text
☑ INDOTECH
☑ INGERGRAND
☑ BOSCHLTD
```

Sticky bulk-action bar:

```text
3 selected

[ Compare ] [ Add to Focus ] [ Add to Backup ] [ Clear ]
```

---

# 44. Compare Workflow

Compare should support approximately:

```text
2–5 candidates
```

Example:

```text
COMPARE CANDIDATES

                 INDOTECH   BOSCHLTD   INGERGRAND
Setup Quality       63         65          74
Entry               38         49          34
RS                  97         85          80
Tightness          0.66       1.24        1.48
R:R                1.6R       1.9R        1.0R
Stop room           Good       Good        Tight
Sector              Cap Gds    Auto        Cap Gds
```

This justifies the checkboxes and supports the page's intended research role.

---

# 45. Candidate Selection Workflow

The intended flow should become:

```text
Select
   ↓
Compare
   ↓
Promote
   ↓
Focus / Backup
```

This creates a direct connection between:

```text
Candidates
→ Watchlist
→ Trigger Proximity
```

---

# 46. State Should Be More Prominent in Beginner Mode

Lifecycle state is one of the easiest things for a beginner to understand.

Example:

```text
INDOTECH                              PRIME
Inside Bar · Capital Goods

Strong RS · clean structure
Entry still early

[ View ]
```

Then Pro mode exposes the full table row.

---

# 47. Add "Why Ranked Here?"

Every candidate should support:

```text
Why #3?
```

Example expansion:

```text
WHY INDOTECH RANKS #3

POSITIVE
+ RS 97
+ Clean structure
+ Good R:R
+ PRIME lifecycle state

CAUTION
− Entry quality only 38
− RVOL below normal
```

This has two benefits:

1. teaches the user how ranking works,
2. makes ranking errors easier to audit.

The explanation should come from deterministic rank components, not generic LLM interpretation.

---

# 48. Ranking Logic Should Be More Visible

The current header note:

```text
ranked by state, then trigger distance, then RS
```

is useful but visually too quiet.

Replace with:

```text
SORT
[ Actionability ▼ ]
```

Tooltip:

```text
Actionability sorts by:
1. Lifecycle state
2. Distance to trigger
3. Relative strength
```

Recommended sort presets:

```text
Actionability
Best quality
Best entry
Strongest RS
Tightest setups
Best R:R
```

Again, user-facing names should describe the research objective.

---

# 49. Column Toggles — Move into a Columns Menu

Current inline toggles such as:

```text
sector
quality
entry
rs
drs
rvol
tight
trend
rr
chop
thrust
```

create visual noise.

Replace with:

```text
Columns ▾
```

Example menu:

```text
ESSENTIAL
✓ Sector
✓ Quality
✓ Entry
✓ RS

STRUCTURE
□ Tightness
□ Trend
□ Chop

FLOW
□ RVOL
□ DRS

RISK
□ R:R
□ Stop / Thrust

[ Reset to mode default ]
```

---

# 50. Add Research Question Shortcuts

A very beginner-friendly approach is to expose the purpose of the tools directly.

Example:

```text
RESEARCH QUESTIONS

Where are the strongest setups?
Which leaders are still early?
Which stocks are tightening?
Which have the best entry geometry?
Which are strongest in this regime?
```

Clicking a question configures:

```text
preset
filters
landscape mode
sort
table columns
```

This can teach users how the research tools fit together.

---

# 51. Progressive Teaching

The first time a user opens a landscape mode, show a concise explanation.

Example:

```text
TIGHTNESS × ENTRY

Find stocks that are:
• structurally compressed
• close to a sensible entry

Best area = upper right
```

After repeated use, this may collapse automatically or be manually dismissed.

Do not create lengthy onboarding modals.

---

# 52. Recommended Beginner Candidates Page

```text
CANDIDATES                                    62
Find the strongest trade ideas from tonight's scan.

VIEW
[ Best opportunities ▼ ]

Showing:
Strong setup · good entry · reasonable stop room

Filters: Actionable · Any setup · Any sector
                                     [ More filters ]


┌──────────────────────────────────────┬────────────────────────────┐
│ OPPORTUNITY LANDSCAPE                │ RESEARCH LENS · CHOP       │
│                                      │                            │
│ How to read:                         │ Prioritize                 │
│ ↑ cleaner setup                      │ ✓ Strong RS                │
│ → better entry                       │ ✓ Tight structure          │
│                                      │ ✓ Precise entry            │
│             PRIME                    │ ✓ Good stop room           │
│               ●                      │                            │
│                                      │ 18 fit current lens        │
│                                      │ [ Show best 18 ]           │
└──────────────────────────────────────┴────────────────────────────┘


TOP CANDIDATES

STOCK        SETUP        WHY INTERESTING        ENTRY    STOP    STATE
INDOTECH     Inside Bar   RS leader · clean      Fair     Good    PRIME
BOSCHLTD     Inside Bar   strong setup           Good     Good    PRIME
INGERGRAND   Inside Bar   clean setup            Fair     Tight   PRIME
```

This preserves the research capability while making the page much easier to understand.

---

# 53. Recommended Pro Candidates Page

Pro can remain close to the current implementation.

Visible metrics may include:

```text
Quality
Entry
RS
RS Δ1D
RVOL
Tightness
R:R
CHOP fit
Stop / Thrust
```

Advanced filters and landscape modes remain accessible.

---

# 54. Recommended Lab Candidates Page

Lab should expose:

```text
raw formulas
metric coverage
experimental metrics
research-lens weights
score components
distribution percentiles
alternative landscape axes
debug provenance
unvalidated ranking features
```

The current page is conceptually closest to this mode.

---

# 55. Immediate Priority Fixes

Recommended implementation order:

```text
1. Move setup/state filter wall behind More filters.
2. Add human-readable research presets.
3. Make Research Lens operational.
4. Reduce Beginner table to ~6 columns.
5. Move advanced metrics into Pro/Lab.
6. Hide poorly populated columns by default.
7. Implement checkbox Compare / Watchlist actions or remove checkboxes.
8. Explain every Opportunity Landscape mode in plain language.
9. Add Why ranked here? per candidate.
10. Move column toggles into a Columns menu.
```

---

# 56. Final Candidates-Screen Principle

The correct design philosophy is:

```text
DO NOT simplify the research capability.
SIMPLIFY the default exposure to that capability.
```

The Candidates page should remain the deepest comparative research surface in the tool.

But the Beginner experience should guide the user through:

```text
RESEARCH QUESTION
       ↓
PRESET
       ↓
LANDSCAPE
       ↓
RANKED SHORTLIST
       ↓
COMPARE
       ↓
FOCUS / BACKUP
```

rather than presenting every research control simultaneously.

---

# Desk / History / Research Review — Trader Usefulness, Jargon Reduction & Beginner/Pro Separation

## 57. Core Problem

The current Desk, History, and Research sections contain a lot of **good underlying evidence**, but several screens expose that evidence at the wrong abstraction level.

The main issue is not that the data is useless.

The issue is:

```text
GOOD RESEARCH DATA
        ↓
shown directly as
        ↓
RAW RESEARCH / ENGINEERING LANGUAGE
```

A beginner sees terms such as:

```text
MFE
MAE
right-censoring
label version
ablation
leakage
event-store partitions
detector trust
N5 experiments
gross of costs
```

without knowing:

```text
what this means
why it matters
what action it should change
```

The better product architecture is:

```text
RAW RESEARCH EVIDENCE
        ↓
MODE-SPECIFIC TRANSLATION
        ↓
TRADER-FACING IMPLICATION
```

The Beginner / Pro / Lab toggle has the most value on exactly these screens.

---

# 58. Role of the Three Modes

These sections should use the three modes more aggressively than the rest of the product.

## Beginner

Primary question:

```text
What does this mean for me as a trader?
```

Show:

- plain-language conclusions,
- small number of metrics,
- clear warnings,
- direct interpretation,
- simple comparisons,
- no engineering vocabulary unless expanded.

## Pro

Primary question:

```text
What exactly does the data say?
```

Show:

- raw trading metrics,
- sample sizes,
- expectancy,
- MFE / MAE,
- regime splits,
- R-multiples,
- confidence / coverage,
- detector status,
- cost assumptions where relevant.

## Lab

Primary question:

```text
Can I trust the research process itself?
```

Show:

- leakage tests,
- label versions,
- archive partitions,
- ablation studies,
- frozen configs,
- detector audits,
- experimental status,
- provenance,
- negative findings.

This gives the modes a meaningful product role:

```text
BEGINNER
Interpretation

PRO
Trading evidence

LAB
Scientific / engineering evidence
```

---

# 59. Navigation Role Clarification

The left navigation can remain:

```text
Tonight
Market
Candidates
Desk
History
Research
Settings
```

But each page should answer one clean question:

```text
TONIGHT
What matters now?

MARKET
Where is leadership?

CANDIDATES
What should I research?

DESK
What am I holding / risking?

HISTORY
What has worked?

RESEARCH
Why should I trust the system?
```

This distinction should guide which information is allowed on each page.

---

# 60. Desk — Recommended Purpose

The Desk should become:

> **Portfolio & Execution**

Its trader-facing job is:

```text
What am I holding?
What am I risking?
Is this new trade sensible?
Am I making execution mistakes?
```

The current screen already contains useful foundations:

```text
Pre-trade check
Positions register
Gross exposure
Loss if all stops hit
Import / export
Paper-call marker
Position-size outcomes
```

The main opportunity is to make these more actionable.

---

# 61. Desk — Pre-Trade Check

Current concept:

```text
Is this name in tonight's universe at all?
```

This is too weak.

The pre-trade check should become a deterministic trade-readiness summary.

Example:

```text
PRE-TRADE CHECK — DIFFNKG

SETUP
Base Breakout

CURRENT STATE
Ready

MARKET
Choppy

SECTOR
Strong

ENTRY
1.6% below breakout

STOP
Enough room for normal price movement

LIQUIDITY
Good

PORTFOLIO IMPACT
Open risk now           1.4%
After this trade        1.9%
Sector exposure        18% → 27%

RESULT
Tradeable, but wait for trigger
```

This should remain deterministic.

The LLM should not decide whether the trade is taken.

---

# 62. Pre-Trade Check — Beginner Mode

Avoid:

```text
Invalidation
Thrust-days
ADR normalized stop
Portfolio heat
Correlated exposure
```

Show:

```text
ENTRY
Still below breakout

STOP
Not too close to normal daily noise

LIQUIDITY
Easy enough to trade

PORTFOLIO
This would increase Defence exposure

BOTTOM LINE
Wait for trigger
```

Optional:

```text
Why?
```

opens more detail.

---

# 63. Pre-Trade Check — Pro Mode

Show:

```text
Trigger                   ₹493.20
Current                   ₹485.50
Distance to trigger       -1.6%
Stop                      ₹472.40
Stop distance              2.7%
ADR                         4.2%
Stop / thrust              0.82
R:R                         2.1R
Liquidity                  Pass
ASM/GSM                    Clear
Open portfolio risk         1.4%
Post-trade portfolio risk   1.9%
Sector exposure            18% → 27%
```

This is where technical labels belong.

---

# 64. Desk — Positions Register

The Positions Register is trader-useful and should remain.

Its primary job should be:

```text
POSITION
ENTRY
CURRENT
STOP
RISK
P&L
STATE
```

Beginner labels:

```text
Entry
Current
Setup fails below
Money at risk
Gain / loss
```

Pro labels:

```text
Entry
Current
Invalidation
Initial R
Open R
MFE
MAE
Trailing rule
```

---

# 65. Desk — Portfolio Summary

Recommended top summary:

## Beginner

```text
PORTFOLIO

5 positions
42% of account invested
1.6% of account currently at risk
If every stop is hit: -1.6%

Largest concentration:
Defence 31%
```

## Pro

```text
Open positions             5
Gross exposure             42%
Open risk                  1.6%
Loss at all stops          1.6%
Largest sector exposure    31%
Largest theme exposure     27%
Average initial R          ...
Average open R             ...
```

Do not require the beginner to interpret portfolio-risk jargon.

---

# 66. Position-Size Outcomes — Current Value

The current section is potentially useful because it appears to contain real personal-trading evidence.

Current examples include:

```text
₹0–5k
₹5–10k
₹10–25k
...
```

with historical counts and audit notes.

This can answer a valuable question:

> **Does my position sizing behavior help or hurt me?**

But the current presentation mostly shows bucket counts, which is incomplete.

---

# 67. Position-Size Outcomes — Recommended Beginner View

Example:

```text
HOW POSITION SIZE AFFECTED YOUR RESULTS

₹0–5k
Many trades, but fees hurt results

₹5–10k
Mixed results

₹10–25k
Best historical results
Sample is smaller

BIGGEST LESSON
One unmanaged large loss erased months of gains
```

Then show:

```text
Most-used size
₹0–5k

Historically best size
₹10–25k

Warning
Only 47 trades in this bucket
```

This is much easier to understand.

---

# 68. Position-Size Outcomes — Recommended Pro View

```text
SIZE          TRADES   NET P&L   AVG R   WIN%   FEES / P&L
₹0–5k           308       ...    -0.08R   38%       31%
₹5–10k          117       ...    +0.11R   43%       14%
₹10–25k          47       ...    +0.42R   51%        6%
₹25–50k           0        —        —      —         —
₹50k+              0        —        —      —         —
```

This turns the section into an actual personal execution study.

---

# 69. Calls vs Trades — Recommended Use

This section has potentially very high trader value.

It should answer:

```text
Do I trade the scanner well?
```

Possible comparisons:

```text
Scanner calls
vs
Trades actually taken

Missed winners
Avoided losers
Late entries
Oversized trades
Trades taken outside scanner
```

---

# 70. Calls vs Trades — Beginner View

Example:

```text
YOUR EXECUTION VS THE SCANNER

Scanner calls taken        42%
Good calls you skipped     18
Bad calls you avoided      31
Trades outside scanner      7

MAIN ISSUE
You often entered after price had already moved too far.
```

Use plain-language conclusions.

---

# 71. Calls vs Trades — Pro View

Show:

```text
call_capture_rate
winner_capture_rate
loser_avoidance_rate
late_entry_rate
off-system_trade_count
avg_entry_slippage
avg_R_taken_vs_available
```

This becomes an execution-discipline audit.

---

# 72. History — Recommended Purpose

History should answer:

> **What has actually worked, under what conditions, and what has failed?**

The current page already contains useful building blocks:

```text
Performance summary
Setup scorecard
Winner / stopped / flat / open
MFE / MAE
Calls archive
Cumulative R
```

The main improvement is translation and hierarchy.

---

# 73. History — Beginner View

Lead with:

```text
WHAT HAS BEEN WORKING?

Last 3 months · CHOP market

1. Pullback
   Best average outcome

2. IPO Base
   Good average outcome

3. Inside Bar
   Most evidence / largest sample

Weakest:
Momentum Burst
```

Then:

```text
HOW RELIABLE IS THIS?

High evidence
Inside Bar
Pullback

Medium evidence
IPO Base
EP

Too little evidence
Power Play
```

Avoid forcing the beginner to interpret:

```text
n=3586
+0.45R
right-censoring
```

unless they expand details.

---

# 74. History — Pro View

Show the actual scorecard:

```text
SETUP             N      HIT%     AVG R     MEDIAN MFE     MEDIAN MAE
Pullback         2036     45%     +0.64R      ...            ...
IPO Base          365     40%     +0.56R      ...            ...
Inside Bar       3586     39%     +0.45R      ...            ...
EP                146     34%     +0.42R      ...            ...
```

Important:

```text
Power Play
n=1
```

must never visually compete with a setup having thousands of observations.

Add:

```text
INSUFFICIENT SAMPLE
```

rather than emphasizing 100% hit rate.

---

# 75. History — Sample Confidence

Every setup row should communicate evidence strength.

Example:

```text
Inside Bar
n=3586
Evidence: HIGH
```

```text
Momentum Burst
n=156
Evidence: MODERATE
```

```text
Power Play
n=1
Evidence: INSUFFICIENT
```

The exact sample thresholds should be configured and validated.

---

# 76. History — Regime-Aware Performance

This should become one of the most useful features in History.

Instead of only:

```text
Pullback +0.64R
```

show:

```text
PULLBACK

BULL        +0.91R
CHOP        +0.37R
RISK-OFF    -0.08R
```

Then the current regime can be linked:

```text
CURRENT MARKET
CHOP

Historically strongest here:
EP
Tight Pullback
Reversal / Reclaim
```

This is what should eventually give the Candidates Research Lens empirical support.

---

# 77. Regime Performance — Beginner View

Example:

```text
IN CHOPPY MARKETS

Historically better:
✓ EP
✓ Tight Pullback
✓ Reversal / Reclaim

Historically weaker:
✕ Generic breakout
✕ Loose Inside Bar
```

No need to expose confidence intervals by default.

---

# 78. Regime Performance — Pro View

Show:

```text
SETUP       REGIME      N      AVG R      HIT%      MFE      MAE
EP          CHOP       103     +0.72R     ...
EP          BULL        87     +0.91R     ...
...
```

Optional:

```text
bootstrap interval
year stability
coverage
```

belongs in Pro or Lab.

---

# 79. History — Calls Table

The Calls table is useful and should remain.

Recommended filters:

```text
Setup
Regime
Sector
Theme
Outcome
Score band
Entry-quality band
Stop-room band
```

This allows practical trader questions such as:

```text
Show failed Base Breakouts in CHOP.
```

```text
Show EP winners with RS > 90.
```

```text
Show IPO Base trades with tight stops.
```

---

# 80. Calls Table — Beginner Mode

Columns:

```text
DATE
STOCK
SETUP
RESULT
BEST MOVE
WORST MOVE
WHY IT FAILED / WORKED
```

Translate:

```text
MFE → Best move after trigger
MAE → Worst move against entry
```

---

# 81. Calls Table — Pro Mode

Columns:

```text
DATE
STOCK
SETUP
RESULT
R
MFE
MAE
REGIME
SECTOR
ENTRY QUALITY
STOP ROOM
REASON
```

Replay action should be available where data supports it.

---

# 82. Cumulative R Curve — Current Risk

The current cumulative R curve may be misread as:

```text
account equity
```

when it is actually:

```text
archived call-label sum
```

especially if:
- calls overlap,
- position sizing is ignored,
- costs are incomplete,
- multiple signals occur simultaneously.

This is scientifically useful but potentially misleading to a trader.

---

# 83. Cumulative R — Beginner View

Rename:

```text
SCANNER RESULTS OVER TIME
```

and show:

```text
This is NOT account profit.

It adds the measured R outcome of historical scanner calls
to show whether the scanner's edge was persistent.
```

Better beginner charts:

```text
Rolling average R
Rolling win / worked rate
Drawdown in signal expectancy
```

rather than only a giant cumulative line.

---

# 84. Cumulative R — Pro View

Title:

```text
SCANNER EXPECTANCY CURVE
```

Display:

```text
gross / net status
number of calls
overlap warning
max drawdown in R
rolling expectancy
year-by-year expectancy
```

Keep:

```text
NOT ACCOUNT PERFORMANCE
```

prominent.

---

# 85. Research — Recommended Purpose

Research should answer:

> **Why should I trust the system?**

This is different from:

```text
What should I trade tonight?
```

The current Research page mixes:
- trader research,
- experiment design,
- detector QA,
- data integrity,
- reproducibility.

These should be separated.

---

# 86. Recommended Research Navigation

Use four subsections:

```text
RESEARCH

1. Performance
2. Experiments
3. Detector Trust
4. Data Integrity
```

---

# 87. Research → Performance

Purpose:

```text
What evidence supports the setups?
```

Trader / Pro relevant:

```text
setup expectancy
regime expectancy
score calibration
feature bands
historical analogues
```

Beginner:

```text
What has worked?
What works in this market?
How much evidence do we have?
```

Pro:

```text
N
avg R
MFE
MAE
hit rate
regime split
coverage
```

---

# 88. Research → Experiments

Purpose:

```text
Which layer actually adds value?
```

Contains:

```text
ablation ladder
N5 experiments
L1.5 analogue tests
L2 challenger tests
champion vs challenger
```

This is primarily:

```text
PRO / LAB
```

Beginner should see only a simple summary:

```text
RESEARCH STATUS

Setup detection       Adds value
Entry geometry        Adds value
Liquidity gate        Under test
AI model              Not promoted
```

if the evidence is actually available.

---

# 89. Ablation Ladder

Current concept:

```text
Baseline
+ Setup detection
+ Geometry / entry quality
+ Liquidity gate
...
```

This is scientifically useful.

Its actual question is:

> **Which component adds edge?**

Recommended Pro/Lab view:

```text
LAYER                    AVG R     COVERAGE     N
Baseline                 +0.18R      100%       ...
+ Setup detection        +0.31R       ...
+ Geometry               +0.44R       ...
+ Liquidity              +0.48R       ...
+ Regime                 +0.55R       ...
```

Do not show expectancy improvements before the required N5 experiment standard is met.

---

# 90. Research → Detector Trust

This is relevant to the trader, but only in compact form.

Recommended trader-facing status:

```text
DETECTOR TRUST

Episodic Pivot        ✓ Rankable
Inside Bar            ✓ Rankable
IPO Base              ✕ Blocked
Momentum Burst        ⚠ Under review
Base Breakout         ⚠ Under review
Pullback              ⚠ Under review
```

This directly answers:

```text
Can I trust the ranking for this setup?
```

---

# 91. Detector Trust — Beginner Mode

Avoid:

```text
rankable
audit passed
hazardous cohort
historical reclaim used current EMA
```

Translate:

```text
EP
Ready to use

Inside Bar
Ready to use

IPO Base
Do not rely on ranking yet
Reason:
The system cannot yet verify how old the IPO really was.

Momentum Burst
Use with caution
A recent rule bug was fixed and still needs rechecking.
```

This is far easier to understand.

---

# 92. Detector Trust — Pro Mode

Show:

```text
Episodic Pivot
Status: RANKABLE
Audit: 2026-08-30
Reason: audit passed

IPO Base
Status: BLOCKED
Issue: listing_age_unverified

Momentum Burst
Status: REVIEW
Issue: avwap_extension_guard_inert
Fixed: 2026-08-30
Reaudit: pending
```

---

# 93. Negative Findings Board

This is one of the best research-governance features.

Keep it.

Its purpose:

```text
What do we already know is broken, weak, or unproven?
```

The trader does not need the engineering language by default.

---

# 94. Negative Findings — Beginner View

Example:

```text
KNOWN LIMITATIONS

IPO Base
Do not trust ranking yet.
Listing age is not verified.

Momentum Burst
Use cautiously.
A recent entry rule was not working correctly and is being rechecked.

Base Breakout
Use cautiously.
Stop-room logic was recently corrected.
```

This is genuinely useful.

---

# 95. Negative Findings — Pro / Lab View

Show exact findings:

```text
avwap extension guard inert
listing age not verified
room rule inverted
anchor proximity had no direction
historical reclaim used current EMA
universe eligibility hazardous cohort
```

with:

```text
detected_date
fixed_date
reaudit_status
affected_versions
```

---

# 96. Research → Data Integrity

Move these sections here:

```text
Archive coverage
Leakage suite
Label version
Detector hit distribution
Frozen config
Build provenance
```

These are essential to trust the research but not day-to-day trading decisions.

---

# 97. Archive Coverage

Current examples:

```text
Partitions
Sampled outcomes
Label version
Detector hits
```

Trader-facing usefulness is low.

Beginner should see only:

```text
RESEARCH DATA HEALTH

Historical coverage     Good
Outcome labels          Mixed versions
Missing data            Some
Research status         Use with caution
```

if that summary is truthful.

---

# 98. Archive Coverage — Pro / Lab

Show:

```text
partitions
date range
sampled events
resolved
unresolved
partial
label versions
detector hit counts
coverage gaps
```

This is where the raw numbers belong.

---

# 99. Leakage Suite

The leakage suite is scientifically essential.

Its question is:

```text
Did the research accidentally use future information?
```

Beginner view:

```text
BACKTEST INTEGRITY
Future-data checks       PASS
```

Tooltip:

```text
The research is tested to make sure it does not use information
that would not have been known at the time.
```

That is enough.

---

# 100. Leakage Suite — Pro / Lab

Show:

```text
walk-forward
embargo
next-bar fill
net-cost simulator
fold status
planted-bug tests
```

The current technical implementation should remain available here.

---

# 101. Detector Hit Distribution

This section is mainly QA.

Its question:

```text
Are some detectors firing far too often or too rarely?
```

Move to:

```text
Research → Detector Trust / QA
```

Beginner does not need it.

Pro/Lab can use it to detect:
- imbalance,
- broken detectors,
- setup scarcity,
- unexpected distribution shifts.

---

# 102. Frozen Config

The frozen configuration is important for reproducibility.

Examples:

```text
costs-v1-spec-1.4
outcome-labels-v4-net-cost
universe gates
detector trust audit version
```

This belongs in:

```text
Lab
or
Settings → Research Configuration
```

Beginner should see at most:

```text
Research version
v4
```

---

# 103. Jargon Translation Matrix

The UI should use a centralized translation layer.

| Pro / Lab term | Beginner label |
|---|---|
| MFE | Best move after entry |
| MAE | Worst move against entry |
| R | Risk unit |
| Expectancy | Average result per call |
| Right-censoring | Some calls are still too new to judge |
| Label version | Outcome-rule version |
| Leakage | Future-data cheating check |
| Embargo | Separation between training/test examples |
| Ablation | Test of which component adds value |
| Detector | Setup finder |
| Rankable | Safe enough to include in ranking |
| Blocked | Do not rely on this setup yet |
| Review | Use cautiously; needs rechecking |
| Event-store partition | Historical-data chunk |
| Gross of costs | Before trading costs |
| Net of costs | After trading costs |
| Archive coverage | How complete the historical data is |
| Frozen config | Locked research settings |
| Hit rate | % of calls reaching the defined success condition |
| Sample size / n | How many examples support this result |
| Thrust / thrust-day | Typical daily movement reference |
| Invalidation | Setup fails below this level |
| Correlated exposure | Several positions depend on the same theme/sector |

Beginner tooltips can still show the technical term:

```text
Best move after entry
Technical term: MFE
```

This teaches gradually without forcing jargon first.

---

# 104. Beginner / Pro / Lab Display Matrix

| Section | Beginner | Pro | Lab |
|---|---|---|---|
| Pre-trade check | Plain verdict + key reasons | Raw entry/risk metrics | Rule diagnostics |
| Positions | Money at risk / gain-loss | R, MFE, MAE, stop logic | Audit fields |
| Position-size outcomes | Practical lesson | P&L, avg R, fees | Import methodology |
| Calls vs trades | Execution mistakes | Capture/slippage stats | Matching diagnostics |
| History summary | What works | Expectancy/sample data | Label/version diagnostics |
| Setup scorecard | Ranked setups + confidence | N, R, MFE, MAE | Full statistical analysis |
| Regime performance | What works in CHOP/BULL | Full regime matrix | Model/validation details |
| Calls table | Plain results | Raw metrics | Event/state IDs |
| Cumulative curve | Scanner results over time | Expectancy curve | Construction details |
| Detector trust | Ready / Caution / Blocked | Audit reason | Full finding history |
| Negative findings | Plain limitations | Technical finding | Fix/retest provenance |
| Archive coverage | Simple health summary | Coverage statistics | Partitions / source lineage |
| Leakage suite | PASS / FAIL trust badge | Test summary | Full test suite |
| Ablation | Simple "adds value?" summary | Experiment metrics | Full experimental detail |
| Frozen config | Research version | Cost/label config | Complete reproducibility config |

---

# 105. Visual Hierarchy for Beginner Mode

Beginner screens should prioritize:

```text
CONCLUSION
    ↓
WHY
    ↓
WHAT TO DO / WATCH
    ↓
OPTIONAL DETAILS
```

Example:

```text
IPO BASE
DO NOT RELY ON RANKING YET

Why?
The system cannot verify how old some IPOs were.

What happens now?
IPO candidates can still be shown for observation,
but should not be promoted automatically.

[ Technical details ]
```

This is much better than:

```text
IPO Base
BLOCKED
listing age not verified
```

---

# 106. Visual Hierarchy for Pro Mode

Pro should prioritize:

```text
METRIC
CONTEXT
SAMPLE
STATE
```

Example:

```text
IPO BASE

Status        BLOCKED
Issue         listing_age_unverified
Audit         2026-08-30
Affected N    ...
Version       ...
```

---

# 107. Visual Hierarchy for Lab Mode

Lab can remain engineering-heavy.

It should expose:

```text
raw IDs
versions
hashes
event-store partitions
experiment configurations
test folds
embargo
leakage probes
source provenance
fix/retest history
```

No need to make Lab beginner-friendly.

The purpose of Lab is transparency and scientific control.

---

# 108. Immediate Priority Changes for These Sections

Recommended implementation order:

```text
1. Give Beginner / Pro / Lab genuinely different information density.
2. Translate all trader-facing jargon in Beginner mode.
3. Upgrade Pre-trade Check into a real portfolio-aware readiness check.
4. Reframe Position Size outcomes into practical behavioral lessons.
5. Make History lead with "What has been working?"
6. Add regime-specific setup performance.
7. Add sample-confidence labels to every setup scorecard.
8. Move archive coverage / leakage / frozen config into Data Integrity.
9. Keep compact Detector Trust visible to traders.
10. Translate Negative Findings into plain-language limitations.
11. Reframe cumulative R as scanner expectancy, not account performance.
12. Use a centralized jargon-translation dictionary.
```

---

# 109. Final Product Principle for Desk / History / Research

The raw research machinery should remain.

It is one of the strongest parts of the system.

But the interface should follow:

```text
LAB
How was this proven?

PRO
What does the evidence say?

BEGINNER
What does this mean for my trading?
```

That separation allows the product to be:

```text
scientifically auditable
+
technically deep
+
beginner understandable
```

without deleting any of the research rigor already built into the tool.

