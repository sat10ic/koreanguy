# WAVE K8 — Pullback-specificity fix (shrink the `pullback_to_rising_ma` crowd)

**Problem (from K7 recall):** discovery-bucket recall vs the practitioner label set is 5/12
(7/23 full). Binding constraint is the **specificity** of `pullback_to_rising_ma`: ~200
names/day qualify, and the hard `CAP_PER_ARCHETYPE=20` (ranked by proximity-to-trigger)
evicts real picks — PARAGMILK (2026-06-16), TATAINVEST (2026-06-05) — before they clear the
cap. Loosening thresholds is BANNED. The fix is **corpus-cited quality discriminators that
shrink the daily pullback crowd** so real picks rank inside the top 20, plus a corpus-justified
ranking-key change.

Current `_pullback_to_rising_ma` (discovery.py L275-309) requires only: depth ≤ band, ≥3-of-5
down closes, and close within 3% of a *rising* 10/20 SMA. That admits every stock **drifting
up hugging a rising MA** — the corpus says a *buyable* pullback is a much narrower object.
The spec's own archetype-b definition already names one missing filter ("**no heavy-red-day in
pullback**", WAVE_K_SPEC PART C archetype b) that the code never implemented.

---

## Discriminators (ranked by crowd-shrink power × cite strength)

Each is a **quality gate added inside `_pullback_to_rising_ma`** (AND-ed after the existing
rising+near+3-of-5 checks), except D4 which is the ranking key. All shrink the crowd; none
loosen any threshold.

### D1 — No heavy red-dot day + up-volume dominance in the pullback (volume dry-up) — **NEW metric**
- **Formula:** over the pullback window (leg-high index → now, capped at last 10 sessions):
  `has_heavy_red_day` = any down-close bar with `volume > 500_000` **and** day-move ≤ −5%
  (the down-variant of the purple dot); `up_down_vol_ratio` = Σvol(up-close bars) /
  Σvol(down-close bars). **Gate: `not has_heavy_red_day` AND `up_down_vol_ratio ≥ 1.0`.**
- **Cite:** groww 2 / groww 4 (WAVE_K_SPEC PART A): *"no big red-dot (heavy-volume down) day
  in the pullback; up-volume >> down-volume."* Already in archetype-b's spec definition —
  **implements existing intent, not a new threshold.**
- **Crowd-shrink:** the biggest single cut. A real pullback is supply drying up; any name that
  had an institutional distribution day (heavy-volume red) or that fell on net-higher down-volume
  is out. Removes the "sloppy decline that happens to sit near a rising MA" majority.

### D2 — Undercut-and-recover: recently traded BELOW the 10/20 SMA, now reclaimed — **inline, no metric**
- **Formula:** within the last 10 sessions, at least one **close below** the 10SMA *or* 20SMA
  (evaluated bar-by-bar against that bar's own SMA value), **and** today's close is back
  at/above the near MA (already guaranteed by the existing ≤3% "near" test).
- **Cite:** ARORA_SHARDS_NUANCES.md L43 / L186-188 (extract_ma_small.md:65-68,77-79):
  *"I only buy stocks which have recently gone below 10 and 20... Weak hands shaken out → then
  stock forms base → more comfortable entry."*
- **Crowd-shrink:** THE Arora definition of a buyable pullback. Kills every name that merely
  **drifts up along the rising MA without ever undercutting it** — precisely the class the ≤3%
  proximity test cannot distinguish today. Expected to roughly halve the residual crowd.

### D3 — Contraction into the MA (tight, non-expanding pullback bars) — **inline, reuses existing**
- **Formula:** `prev_day_tightness_pctile(bars) ≤ 50` (yesterday's range in the tighter half
  of the stock's own trailing-20d ranges) **OR** the pullback window's last 3 daily ranges are
  non-increasing (`r[-3] ≥ r[-2] ≥ r[-1]`). Reuses `dm.prev_day_tightness_pctile` — no new metric.
- **Cite:** ARORA_SHARDS L34-36 (*"16% wide day → 4% wide day... VCP in the making"*), L55-57
  (*"Tightness is just an entry area... consolidation quality clean"*); TTM_NUANCES_SHARDS #14
  (*"the tightness itself is the signal"*); STOCKGEEKS_NUANCES L60-63 (VCP w/ lower-high touches
  + previous-low defense).
- **Crowd-shrink:** removes wide-range, climactic, still-volatile declines — an *orderly*
  contraction into support is what Arora buys, not a knife.

### D4 — Ranking key: prior-leg force DESC (replaces proximity-to-trigger) — **ranking change**
- **Formula:** rank the surviving pullback members by `leg_force_from_65d_low` **descending**
  (strongest prior advance first); tiebreak `ma_distance_pct` ascending, then `_liveness`
  descending. (Replaces `_pullback_proximity_rank_key`.)
- **Cite:** groww 2 / CH3.1 (WAVE_K_SPEC PART A): buying force = *"stock up ≥30-35% from its
  3-month low. **His #1 momentum signal**"*; ARORA_SHARDS L180 (*"stocks move in ~50-60%
  increments then consolidate... don't buy extended stock"*) — the leg that's pulling back must
  itself have been a real advance.
- **Why change it:** every label pullback pick sits <2.1% from its MA (per the code's own
  comment), so proximity barely separates the crowd — 200 names all rank ~equal and the cap
  slices arbitrarily. Prior-leg force is Arora's stated #1 signal and *does* separate strong
  bases from weak drift. After D1-D3 shrink the crowd, D4 guarantees the strong-prior-leg picks
  (PARAGMILK/TATAINVEST-class) land at the top of whatever remains.

*(Discriminator budget: exactly ONE new cheap metric — `pullback_volume_character` (D1). D2/D3
are inline logic over existing series + `prev_day_tightness_pctile`; D4 reuses
`leg_force_from_65d_low`.)*

---

## Predicted effect on the label misses / negative control

*(Directional prediction with mechanism; the executor confirms exact hit/miss on re-run.)*

- **PARAGMILK (2026-06-16), TATAINVEST (2026-06-05) — HELPED, primarily by D2 + D4.** These
  are clean strong-start/pullback names: a real prior leg that pulled back and reclaimed a
  rising 10/20 MA. Today they clear the archetype but are **evicted by the cap** because ~200
  drift-along-MA names rank indistinguishably by proximity. D1/D2/D3 remove the noise majority
  (no undercut, or a heavy distribution day, or a sloppy wide pullback), shrinking the crowd
  toward/under the cap; D4 then floats these two up because both carry a strong measured prior
  advance (high `leg_force_from_65d_low`). Net: they rank **inside** the top 20.
- **Why the crowd shrinks and picks don't:** D1-D3 each target a property the *noise* names
  lack (dried-up volume, a genuine undercut, orderly contraction) but the *real* Arora pullback
  has by construction — so recall of true picks is preserved while the ~200 collapses.
- **NBIFIN (negative control) — STAYS OUT, untouched.** It is rejected at **base eligibility**
  (avg vol 941 shares / liquidity cap ~12 shares vs `MIN_AVG_VOL_30D`/turnover floor) *before*
  any archetype logic runs (discovery.py L376-381). Every K8 discriminator only **tightens** the
  pullback archetype; none touches base eligibility, so NBIFIN cannot re-enter. The K7 recall
  harness assertion (`assert not in_b`) must still pass.

---

## Implementation notes (Sonnet executor)

**1. New metric — `discovery_metrics.py`:**
Add `pullback_volume_character(bars, leg_lookback=60, max_pullback_sessions=10) -> dict` returning
`{"has_heavy_red_day": bool, "up_down_vol_ratio": float | None}`. Pullback window = from the
`_leg_high` index (reuse existing `_leg_high`) forward, capped to the last `max_pullback_sessions`
bars. Heavy red = down close, `volume > 500_000`, `(close-prev_close)/prev_close*100 ≤ -5`.
Ratio = Σ up-close volume / Σ down-close volume (None if no down bars). Cite groww2/groww4 in the
docstring; do NOT invent thresholds — 500k and -5% are the existing purple-dot numbers reused.

**2. `discovery.py` — `_pullback_to_rising_ma` (L275-309):** after the existing
`rising and near` success, before `return True`, AND-in three guards:
- **D1:** `vc = dm.pullback_volume_character(bars)`; require `not vc["has_heavy_red_day"]` and
  `(vc["up_down_vol_ratio"] is None or vc["up_down_vol_ratio"] >= 1.0)`.
- **D2:** compute over the last 10 bars whether any bar's close was below its 10SMA or 20SMA
  value (use the same `_sma(closes,10/20)` already computed in the function); require ≥1 such bar.
- **D3:** require `dm.prev_day_tightness_pctile(bars) <= 50` OR last-3 pullback ranges
  non-increasing.
Keep the `max_depth` param and 180d-anchor caller path (L505-509) intact — the guards apply to
both the 60d and 180d admission branches.

**3. `discovery.py` — ranking (L601-619):** replace `_pullback_proximity_rank_key` with
`_pullback_leg_force_rank_key(entry)` returning `(-leg_force, ma_distance, -_liveness)` (all
ascending sort, so leg_force high-first, distance low-first, liveness high-first); note the
metric key is `leg_force_from_65d_low` and may be None → coerce to `-1e9` so None sinks.
Update `_ARCHETYPE_RANKERS["pullback_to_rising_ma"]` to `(_pullback_leg_force_rank_key, False)`.
`reversal`/`strong_start_ready` rankers unchanged.

**4. Re-run procedure:**
- Delete scratch DB first: `manas_os/data/manas.db`-copy target
  `C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db`
  (and `wave_k7_postfix.db` if using `_wave_k7_recall.py`).
- Run `python _wave_k_recall_baseline.py` (canonical). Confirm: (a) bucket recall for the two
  pullback picks flips to hit; (b) overall recall ≥ prior 5/12 with no regressions; (c)
  bucket-size distribution on label dates stays in the 30-80 target (K8 should *reduce* sizes);
  (d) NBIFIN negative-control assertion still passes.
- Add unit tests for `pullback_volume_character` (heavy-red-day present/absent; up/down ratio).
- Commit as one K8 wave per pipeline-hygiene.
