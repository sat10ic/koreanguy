# HANDOFF — Fixed-Range Volume Profile levels (POC/VAH/VAL) for the SMF workflow (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md
(no commit; `_COMPLETED.md`; real data; absolute python paths; "Rs" not the rupee glyph).
Run AFTER `HANDOFF_GEMINI_smf_activity_screener.md` (this builds on its drill-in).

## Context — the workflow this completes
Source teaching (frozen extract `design/REACTOR_SMART_MONEY_SOURCE_EXTRACT_2026-07-14.md` + the
dossier `SMF_DATA_COMPLETE_REVERSE_ENGINEERING_2026-07-14.md` §6): the SMF score finds WHERE
abnormal activity is; **direction + levels come from a Fixed-Range Volume Profile** over the
previous swing(s) + the activity range — POC (big move goes in whichever direction crosses it),
VAH/VAL, then structure decides entry/skip. Steps 1-2 (score+persistence) ship in the screener
handoff; steps 4-6 (entry/SL/size/trail) are the existing gates/armed-list machinery. This
handoff adds step 3: the levels.

## HONESTY CONSTRAINT (dossier §6, binding)
Daily bhavcopy CANNOT compute true volume-at-price — we only have OHLCV per day. So this is an
**approximated profile**, and the UI must say so. Two permitted estimation modes:
1. **Daily approximation (default, always available)**: distribute each session's volume across
   its H-L range (uniform, or triangular weighted toward close — pick one, document it, test it)
   into price bins; sum across the selected date range → binned profile → POC = max-volume bin,
   Value Area = smallest set of bins around POC covering 70% of volume → VAH/VAL. Label:
   `"approximated from daily OHLCV — not true volume-at-price"`.
2. **Intraday upgrade (when data exists)**: if the tiered intraday store (alpha wave item 2 /
   `HANDOFF_GEMINI_fyers_intraday_backfill.md` — currently BLOCKED on auth) has 5-min bars for
   the symbol+range, compute the profile from 5-min bars instead (volume at each bar's
   close/HL-midpoint bin) and label `"from 5-min bars"`. Detect availability per symbol+range;
   fall back to mode 1 honestly. Do NOT block this handoff on the backfill.

## Scope
1. **Engine**: new `manas_os/engine/volume_profile.py` — pure functions:
   `fixed_range_profile(bars, bins=..., mode=...) -> {poc, vah, val, bins:[{price_lo, price_hi,
   volume}], volume_total, method, coverage}` + a swing-anchor helper `default_anchor_range(bars)`
   (previous major swing low → today, mirroring the teaching's "connect the previous swing")
   with the anchor always overridable. Deterministic, documented binning; no synthetic volume.
2. **API**: `GET /api/chart/{symbol}/volume-profile?from=&to=&bins=` returning the profile +
   method label + honest `{available:false, reason}` (insufficient bars, no data). Read-only,
   additive; one writer (all math in engine/volume_profile.py).
3. **ChartDrawer overlay**: horizontal profile bars on the right edge of the existing ChartDrawer
   (plain SVG, v5 tokens), POC line (accent, labelled), VAH/VAL lines (dim, labelled), a
   date-range selector for the fixed range (default = the swing-anchor helper; draggable/inputs
   ok, keep minimal), a visible method chip: "approx (daily)" vs "5-min". Toggleable layer, off
   by default in beginner mode until the SMF drill-in opens it.
4. **SMF drill-in integration**: from the activity screener's drill-in, the profile auto-anchors
   over the ACTIVITY WINDOW (the streak's date range + the prior swing) so the user lands on the
   teaching's exact read: activity range + POC/VAH/VAL levels on one chart.
5. **Teaching copy** (one line each, advice-free, per the source): POC = highest-volume price of
   the range — direction of the break matters; VAH/VAL = value-area edges; "profile shows where
   volume traded, not who traded or which side."
6. **Tests**: hand-computed profile on a small fixture (known bins → known POC/VAH/VAL);
   70% value-area math; anchor helper on a fixture swing; honest-unavailable; approximation-mode
   labelling. Vitest for any pure frontend helpers.

## Guardrails
Levels are DISPLAY/context only — they must not feed gates, stops, sizing, or verdicts (the
deterministic risk engine stays the one writer for stops/qty; a user reading levels and placing
a manual trade is the product's manual-execution model working as designed). No new chart libs.
v5 tokens, `.v5`-scoped, a11y AA (lines not color-only — label them), reduced-motion. desk_gate
on the desk wave. pytest green (known sector-downside fail allowed) + vitest + build.

## Output
`HANDOFF_GEMINI_volume_profile_levels_COMPLETED.md`: binning method chosen + why, the API
contract, worked test example, REAL DOM evidence of the overlay on a real symbol (one of the
current SMF leaders), method-chip proof of both modes (or honest note that 5-min mode is
data-blocked), test results.
