# WAVE K9 — Recall iteration on ground-truth-correct prices (true baseline 3/12)

**Author:** Opus, 2026-07-10, over the Arora/TradeTM corpus + real bars pulled from
`manas_os/data/manas.db` (daily_prices) around each labelled entry date.
**Rule reaffirmed (unchanged from K7/K8):** corpus-cited thresholds only; NO tuning on
labels; NBIFIN negative control stays excluded; no loosening for its own sake. A
corpus-cited **wider/branched** read that matches how the practitioners actually describe
the setup IS legitimate — that is the whole content of this wave.

## Where the true baseline stands (post-backfill correction, LEARNINGS tail)
K7's 5/12 was a stale-data artifact. On ground-truth-correct prices the true bucket
baseline is **3/12** (INTELLECT via reversal, BSOFT via reversal, GROWW via
ep_ipo+pm+recent_listing). K8's D1-D3 crowd-shrink was recall-neutral (3/12 -> 3/12) but
real (pullback pre-cap ~200 -> 41-57/day). The 9 misses, re-read on correct bars below,
split into **one genuine corpus-cited capability gap** (CHENNPETRO — a 50-day-MA pullback
we never test for) and **eight honest skips** (velocity-floor, legitimate D1 failure,
size-rank tension, out-of-band triggers, knife-edges). This wave adds the one branch the
corpus supports and documents the rest as principled skips — it does not manufacture recall.

---

## PER-MISS DIAGNOSIS (chart read from real bars + corpus nugget + verdict)

### 1. CHENNPETRO 2025-10-17 (label strong_start) — **CATCHABLE. New branch: pullback_to_50ma.**
**Chart read (real bars):** ran 757 -> 807 into early Oct in a strong uptrend
(180d-high/252d-low ratio **1.63**), then a clean **5-of-5 down** slide (807 -> 723) that
parked price **+0.9% above a RISING 50-day SMA** (d10 -7.1%, d20 -5.8%, **d50 +0.9%**,
rising50=True). corr-from-60d-leg 15.7%, leg_force 38.3%. No heavy-red-dot day.
**Why it misses today:** the pullback archetype only tests the **10/20** SMA (discovery.py
`_pullback_to_rising_ma`), and at -6 to -7% from the 10/20 it fails the 3% "near" test. It
is not near the 10/20 because it pulled back to the **50** — the deeper support.
**Corpus nugget:** TradeTM buys **pullbacks to the 20/50 EMA** on persistent names, not
breakouts. Explicit and repeated:
- **TTM-H-III4** (TRADETM_NUANCES_HINDI L112-116): *"buy pullbacks to the 20 or 50 EMA...
  define pullback zones as 20/50 EMA ±X%."*
- **INDIA_PLAYBOOK L249-251**: *"buy pullbacks to the 20/50 EMA... [TTM-H-III4] [CODEABLE —
  alert within 1-2% of 20/50 EMA]."*
- **TTM-C10** (TRADETM_NUANCES L253): strong-uptrend pullbacks pausing near support and
  resuming are the base-rate expectation.
- **TTM-COMPLETION L105-106**: persistent momentum = *"accept giving back 20-30% on
  pullbacks... just trail the 50 DMA"* — the 50-MA pullback is a distinct, DEEPER, slower
  flavour than the shallow 10/21 pullback.
**Key nuance — why D1/D3 must NOT apply to the 50-branch:** CHENNPETRO's measured D1
up/down-vol ratio is **0.049** and prev-day tightness pctile **100** (widest) — it FAILS
K8's D1 (up-vol dominance) and D3 (tight contraction). Those gates encode the *shallow
absolute-momentum 10/21 pullback* signature ("supply dries up, tight coil into the MA").
The corpus's 50-MA pullback is explicitly the opposite temperament — a persistent name
"giving back 20-30%" on an orderly multi-day slide. Re-using D1b/D2/D3 on the 50-branch
would re-kill exactly the setup the branch exists to admit. Keep only the ONE universal
supply-shock guard (no heavy-red-dot distribution day — groww2/4).

### 2. COALINDIA 2025-10-10 (label strong_start) — **HONEST SKIP (velocity floor).**
**Chart read:** mega-cap coiling flat *on* its MAs (d10 -0.3%, d20 -1.4%, d50 -0.2%, all
**flat/falling**), pct-up-from-65d-low only 4.3%, leg_force 9.2%, prior-strength ratio 1.16
(weak), **0 purple dots**, adr20 **1.28** (bottom of universe). Only 2 down closes in 5.
**Verdict:** killed by the corpus's own hardest rule — *"ZERO dots (Reliance, Maruti) =
skip regardless of setup"* (groww2 / CH3.1; WAVE_K_SPEC PART A). It is not a rising-MA
pullback (MAs flat/falling), not a prior-strength reversal (ratio 1.16), and has no
velocity. The large-cap-nature-relativity tension (a Tightness-Study example that our
velocity floor rejects) is real and already logged (K7); resolving it would mean weakening
the one velocity floor the corpus states most absolutely. **Do not.** Principled skip.

### 3. PARAGMILK 2026-06-16 (label strong_start) — **HONEST SKIP (legitimate D1 failure).**
**Chart read:** clean pullback to the rising 10/20 SMA, strong leg (leg_force 38.7%, prior
ratio 2.12). Passes rising+near+3-of-5-down and D2/D3.
**The D1 question, answered:** the corpus phrase is *"up-volume **>>** down-volume"*
(groww2/groww4). K8's gate reads that as `up_down_vol_ratio >= 1.0` — already the **loosest
possible** reading of ">>". Measured on correct bars, PARAGMILK's pullback ratio is
**0.896 on the entry day (16-Jun)** and **0.996 on 15-Jun** — down-volume *exceeds* up-volume
on **both** admissible days. Its pullback does NOT show supply drying up; it fails even the
loosest reading of the corpus test. **Per the corpus, PARAGMILK legitimately fails D1** —
this is a correct exclusion, not a false miss. (If anything ">>" argues the floor is too
loose, not too tight; leave it at 1.0 — do not raise it just to make the number look
principled, and do not lower it to admit PARAGMILK.) Principled skip. Arora's own buy
rested on intraday/LTF evidence our daily bars cannot see.

### 4. TATAINVEST 2026-06-05 (label strong_start) — **SKIP today; POSSIBLE via the new 50-branch (§below).**
**Chart read:** clean pullback to the rising 10 SMA (d10 -0.9%, rising10=True), clears
D1 (up/down ratio **3.2**), D2, D3 (tightness 40). leg_force **41.5%**, adr20 2.71.
**Why it misses:** pure **size-control casualty** — ranks **38/57** in the pre-cap pullback
crowd; **37 same-day pullback names carry a STRONGER prior leg** (SBCL 114%, COHANCE 93%,
RESPONIND 85%... 50 names clear the 30% Arora floor). The `CAP_PER_ARCHETYPE=20` slices it.
**Size-control options evaluated (task's own list):**
- *Leg-force floor (>=30%, Arora's #1 signal):* admits **50** pullback names on this date —
  and the bucket is **already 124/day** (>80 target). REJECT: worsens oversizing.
- *leg_force × tightness composite:* TATAINVEST's tightness (40) is middling and the 37
  stronger-force names are not conspicuously looser — a composite does not reliably float it
  into the top 20, and tuning weights until it does is label-fitting. REJECT.
- *Per-sector caps* (would thin the small-cap chem/industrial cluster and surface a lone
  holding-co): **infeasible** — `universe.sector` is 0-populated and `screener_hits.
  basic_industry` exists only for dated dumps. Cannot be relied on. DEFER (revisit if/when
  NSE industry mapping is backfilled — edge-first, this is the right long-run cut).
**Verdict:** on the measurable corpus signals TATAINVEST is a genuinely median pullback;
forcing it in means loosening size or fitting a ranker to its profile — both banned. It gets
a **second, independent cap slot** under the new `pullback_to_50ma` archetype (it also sits
+0.5% above a rising 50 SMA), ranked among the smaller, different 50-MA crowd — that is its
honest shot. Predicted possible-hit; **executor confirms** on re-run, no promise.

### 5. EMSLIMITED 2025-11-06 (label strong_start) — **HONEST SKIP (knife, not a setup).**
**Chart read:** a **-5.5% crash to the 65d low**; all MAs **falling** and 9-13% *above*
price (d10 -9%, d20 -10.5%, d50 -13%); pct-up-from-65d-low 0.8%; leg_force 26.8; prior ratio
1.48. This is a stock breaking down, not a pullback (MAs falling, far away) and not a
prior-strength reversal (ratio 1.48 < 1.5, still declining, no up-trigger). The knife-edge
misses (26.8 vs 30; 1.48 vs 1.50) are **not** tuned. Principled skip.

### 6. NCC 2026-03-10 (label busted_reversal) — **HONEST SKIP (out-of-band trigger).**
**Chart read:** strong prior (ratio 1.75), 38.8% correction off the 180d high (in the 15-40
reversal band), then a **+3.3% up day** — but preceded by **6 consecutive down days**
(corpus states **3-5**), and still **-1.3% below the 10 SMA** (no reclaim). Both reversal
triggers therefore fail (down_run 6 > 5; no 10SMA-reclaim). Also **0 purple dots**.
Loosening "3-5" to "3-6" to admit it is tuning-on-labels. Principled skip.

### 7. ZENTEC 2026-02-24 / 03-13 / 03-16 (busted_reversal trio) — **HONEST SKIP.**
- **02-24:** leg_force 16.5% (well below 30% floor), a flat quiet drift (+0.1%), no clean
  3-5 down run, no trigger. Skip.
- **03-13:** enters the pullback 180d-branch (rev_prior ✓, corr180 33.9% ✓, near rising 10
  SMA, 3-of-5 down) but **fails D1** — up/down-vol ratio **0.375** (choppy pullback,
  down-vol dominant). Correct D1 exclusion. And not a reversal *up*-trigger (it is a -3.8%
  down day). Skip.
- **03-16:** a +3.8% bounce already back *above* the 10 SMA (d10 +0.7%), not a pullback
  *into* support; no 3-5 down run trigger. Skip.
**Common thread:** these are **low-leg-force (16-20%) deep-correction "busted" re-entries** —
6 Manas Entry treats busted_reversal as a distinct, lower-conviction smaller-frame add. Our
archetype set has no busted-reversal detector, and building one that admits 30%+-corrected
falling names without also admitting a flood of knives is a **separate wave (K10)**, not a
K9 threshold change. Principled skip; flagged for K10.

---

## PROPOSED CHANGE (one branch; cite + predicted effect)

### C1 — New archetype `pullback_to_50ma` (persistent-trend pullback to the rising 50-day MA)
**Cite:** TTM-H-III4, INDIA_PLAYBOOK L249-251, TTM-C10, TTM-COMPLETION L105-106 (buy
pullbacks to the **20/50 EMA** on persistent names; accept a 20-30% give-back; trail the 50
DMA). Fills a real capability gap — we test the 10/20 but never the 50, the deeper support
the corpus names in the same breath.

**Admission (all AND-ed), in the PRIOR-STRENGTH family block of `build_bucket`:**
1. **Prior strength** — reuse `_reversal_prior_strength(bars, momentum_top40_value)` (180d
   high >= 1.5x 252d low **OR** 63d momentum top-40pctile at any point in 120d). Establishes
   the *persistent* prior trend the 50-MA pullback presupposes. [TTM-C10]
2. **Near a RISING 50 SMA** — `close` within `PULLBACK_MA_NEAR_PCT` (3%, existing constant,
   NO new number) of `_sma(closes,50)[-1]`, and `sma50[-1] > sma50[-6]` (rising). [TTM-H-III4]
3. **Correction depth** — `correction_depth_from_leg_high(bars) <= CORRECTION_DEPTH_MAX`
   (30%, existing). [groww2]
4. **Actual pullback** — `>=3` down closes in the last 5 sessions (reuse existing logic).
   [6 Manas Entry]
5. **No heavy-red-dot distribution day** — `not dm.pullback_volume_character(bars)
   ["has_heavy_red_day"]` (the ONE universal supply-shock guard). [groww2/4]
6. **DELIBERATELY NOT applied:** the D1 up/down-vol-dominance ratio, the D2 undercut-recover
   test, and the D3 tight-contraction test. These encode the *shallow absolute-momentum*
   10/21 pullback signature; the 50-MA persistent pullback is the "dumb passive, give back
   20-30%" flavour (TTM-COMPLETION L105-106) and measurably fails them (CHENNPETRO D1 0.049,
   tightness 100) *by construction*. Applying them re-kills the branch's own reason to exist.

**Ranking / size:** register `pullback_to_50ma` in `_ARCHETYPE_RANKERS` with the existing
`_pullback_leg_force_rank_key` (leg_force desc, ma_distance tiebreak, liveness) and
`CAP_PER_ARCHETYPE=20` — same discipline as `pullback_to_rising_ma`. It is a distinct tag,
so multi-archetype names (CHENNPETRO, TATAINVEST) get one independent cap slot here.

**Predicted recall effect (executor confirms exact hit/miss on re-run):**
- **CHENNPETRO 2025-10-17 -> HIT.** ratio 1.63 ✓, +0.9% from rising 50 SMA ✓, corr 15.7% ✓,
  5-of-5 down ✓, no heavy-red ✓. The one clean corpus-cited catch. **3/12 -> 4/12.**
- **TATAINVEST 2026-06-05 -> POSSIBLE HIT.** also +0.5% from a rising 50 SMA with a real
  prior leg; gets a second cap slot in the (smaller, different) 50-MA crowd. **Possible
  4/12 -> 5/12** — not promised; confirm on re-run.
- All other misses: unchanged (documented honest skips above).
- **NBIFIN negative control -> STAYS OUT.** C1 only adds an archetype *inside* the
  prior-strength family; it never touches base eligibility, where NBIFIN is rejected on the
  turnover floor (avg vol 941 sh). The `assert not in_bucket` must still pass.

### C2 — (Observation, not a K9 code change) Bucket-size honesty
On correct data the bucket runs **~124/day (2026-06-05), vs the 30-80 target** — 8 sensitive
archetypes x cap-20 + overlap. The 30-80 target and high recall are in genuine tension: to
reach 80 you would cap ~12/archetype and evict *more* real picks. This is why the TATAINVEST
"raise the cap" instinct is wrong (it worsens the real defect). The honest fix is either
(a) accept 80-130 as the true recall-first size and re-state the target, or (b) a Stage-2
rank that trims the union *after* the archetype tags travel (WAVE_K_SPEC PART C Stage-2,
not yet built). **Flag for the orchestrator; no threshold moved in K9.**

---

## IMPLEMENTATION NOTES (Sonnet executor)

**Files:** `manas_os/scanner/discovery.py` only (no new metric — reuses `_sma`,
`correction_depth_from_leg_high`, `pullback_volume_character`, `_reversal_prior_strength`).

**1. New detector `_pullback_to_50ma(bars, correction_depth, momentum_top40_value)`** near
`_pullback_to_rising_ma` (discovery.py ~L285). Same skeleton but: only the 50 SMA line;
require rising50 + near (3%); require prior-strength (call `_reversal_prior_strength`);
require >=3-of-5 down; require `not pullback_volume_character(bars)["has_heavy_red_day"]`.
**Do NOT** add the D1-ratio / D2-undercut / D3-tightness guards. Cite TTM-H-III4 / TTM-C10 /
TTM-COMPLETION in the docstring; note the deliberate D1b/D2/D3 omission and its cite.

**2. Wire into `build_bucket`** inside the existing PRIOR-STRENGTH `if (leg_force_ok and
correction_ok) or (rev_prior and band180_ok):` block (discovery.py ~L547). After the
`pullback_to_rising_ma` append, add:
```
if _pullback_to_50ma(bars, correction_depth if (leg_force_ok and correction_ok) else depth180,
                     momentum_top40_value):
    archetypes.append("pullback_to_50ma")
```
(Guard on `correction_depth is not None` inside the detector; it already checks `<= max`.)

**3. Ranking:** add `"pullback_to_50ma": (_pullback_leg_force_rank_key, False)` to
`_ARCHETYPE_RANKERS` (discovery.py ~L676). No new cap constant.

**4. Re-score procedure:**
- Delete the scratch DB first:
  `C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db`
  (and `wave_k7_postfix.db` if present).
- Run `python _wave_k_recall_baseline.py` (canonical). Confirm: (a) CHENNPETRO
  2025-10-17 flips to HIT via `pullback_to_50ma`; (b) overall bucket recall >= prior 3/12
  with NO regressions to INTELLECT/BSOFT/GROWW; (c) report whether TATAINVEST flips;
  (d) the **NBIFIN** negative-control `assert not in_bucket` still passes; (e) log the
  bucket-size distribution on the label dates (expect a modest rise from the new tag —
  note it against the C2 size observation, do not "fix" size by moving thresholds).
- Add a unit test in `tests/test_discovery_bucket.py`: a synthetic bar series in a strong
  prior trend that pulls back 5-of-5 down to sit +1% above a rising 50 SMA (far from the
  10/20) with no heavy-red day -> tags `pullback_to_50ma`; a variant near the 10/20 (not 50)
  -> does NOT tag it; a variant with a heavy-red distribution day -> excluded.
- One K9 commit per pipeline-hygiene. Add a dated LEARNINGS.md entry: true baseline 3/12,
  C1 branch, CHENNPETRO catch + cite, TATAINVEST result, the 8 honest skips with their
  measured failing condition, and the C2 size-tension note.

**Honest expected outcome:** **4/12** (CHENNPETRO), possibly **5/12** (TATAINVEST via the
second cap slot). The remaining 7 are documented principled skips — do not chase them with
threshold moves. This wave's real deliverable is the corpus-cited 50-MA pullback capability
(good for future persistent-name pullbacks, not just CHENNPETRO) + the size-tension finding.
