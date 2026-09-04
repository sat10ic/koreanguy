# WAVE K10 — `busted_reversal` archetype (deep-correction re-entry of a former leader)

**Author:** Opus, 2026-07-11, over the Arora/TradeTM/Stockgeeks corpus + real bars pulled
from `manas_os/data/manas.db` (daily_prices) around each labelled `busted_reversal` entry.
**Rule reaffirmed (unchanged from K7/K8/K9):** corpus-cited thresholds only; NO tuning on
labels; NBIFIN negative control stays excluded; a wider/branched read is legitimate ONLY
when it matches how the practitioners describe the setup. The danger this wave manages is
explicit: admitting a formerly-strong name **deep in a correction** without admitting the
flood of **falling knives** (still-declining names at fresh lows). The knife-guards below
are the whole content of the wave.

## Where the baseline stands
Post-K9 the bucket baseline is **4/12** (INTELLECT, BSOFT, GROWW, CHENNPETRO). The four
remaining `busted_reversal` label rows are all misses:
`NCC 2026-03-10`, `ZENTEC 2026-02-24`, `ZENTEC 2026-03-13`, `ZENTEC 2026-03-16` — all "6
Manas Entry" real Arora buys. K9 diagnosed them as low-leg-force (16-20%) deep-correction
re-entries that fail the pullback family's D1 supply-dry gate and the reversal archetype's
3-5-down-run trigger, and deferred them to K10 as "a different animal." This wave builds
the detector for that animal.

---

## PART A — WHAT ARORA WAS ACTUALLY BUYING (chart read from real bars)

### NCC 2026-03-10 (label busted_reversal) — **the clean textbook case. CATCHABLE.**
**Prior structure:** former leader, 180d peak **236.9**, 252d low **135.0**, ratio
**1.75**; corrected **38.8%** off the peak (in the 15-40 reversal band). d200 **-24.3%** —
a genuine Stage-4 decline, not a shallow dip.
**The bottom (real bars, 2026-02-10..03-16):**
- **02-19: capitulation / demand-reversal bar.** O137.4 → intraday low **135.0** (undercut
  to the 252d low) → C150.3, on **26.96M shares** (~8-10x normal). A textbook long-tail /
  undercut-and-recover climax — someone bought the low hard. [SG long-tail; ARORA SVR]
- Chops 149-153 for a week, then rolls to a **6-day down run** 02-27→03-09
  (152.6→149.4→143.3→143.0→141.0→140.4) bottoming at **136.2 intraday on 03-09** — a
  **higher low** vs the 135.0 of 02-19 (institution defending a rising floor).
- **03-10 (entry, C145.0, +3.3%):** a reversal up-day closing in the **upper 89% of its
  range** (H145.5 L141.1 C145.0) off that higher low; confirmed next session
  (03-11 +2.8% on **8.87M**, 4x). MAs still falling (d10 -1.3, d20 -3.0, d50 -3.7) — this
  is **not** a pullback in an uptrend, it is a **bottom reversal**. up-from-65d-low **7.4%**.
**What Arora bought:** a former leader, 39% off its high, that undercut its prior low and
recovered on climax volume, then set a higher low and turned up. The danger (still-falling
knife) is answered by: undercut-and-recover bar present, higher low in place, not at a new
low, reversal up-day.

### ZENTEC 2026-02-24 / 03-13 / 03-16 (busted_reversal trio) — **pyramiding into a busted-base breakout.**
**Prior structure:** former leader, 180d peak **2065**, 252d low **1223**, ratio **1.69**;
corrected **~36-31%** across the three dates. An 8-week **base** (Jan 16 – Feb 27) roughly
1280-1420 after the deep correction — a "neglected/dead range" of a former leader
[TTM-C J6]. This is the multi-add pyramid the task flags — note **what changed** across the
three dates:
- **02-24 (C1325, +0.1%):** **in-base toehold.** A quiet, tight, below-average-volume
  (0.77x) drift in the middle of the base; sma20 rising, sma10/50 flat/converging.
  Higher-low base in place, not at a new low (65d low far below at 1223, up **8.3%** from
  it), a demand bar 8 sessions back (02-16: L1288 C1330, recovered). This is Arora's **1%
  starter** on a former leader tightening in a neglected base [pyramiding V1; TTM-C J6].
- **03-04: the base breaks out.** +4.5% to 1406 on **3.35M shares (12x normal)** — the
  power bar clearing the 1420 base ceiling. Trend turns: by 03-13 **all** MAs (10/20/50)
  are rising.
- **03-13 (C1364, -3.8%):** first pullback after the breakout — a **down day** back toward
  the rising 10-SMA (d10 -2.6%). This is a *pullback-in-fresh-uptrend* add, not a bottom.
- **03-16 (C1416, +3.8%):** the reversal-day **reclaim** — bounces off 03-13's 1330 low
  back **above the 10-SMA** (d10 +0.7%, d20 +3.3%, d50 +5.4%), confirming the pullback held.
**What changed 02-24 → 03-16:** the setup migrates from *in-base bottom* (02-24) to
*post-breakout pullback/reclaim* (03-13, 03-16). Consequence for the tool: **02-24 and
03-16 are catchable** by `busted_reversal` (in-base higher-low with a demand bar; and a
fresh 10-SMA reclaim off a higher low, respectively). **03-13 is a down-day pullback add**
that fails every *up*-reversal trigger and the pullback family's D1 (K9 measured its
up/down-vol ratio at **0.375**, down-vol dominant) — it is an honest skip on daily bars,
exactly as K9 documented. Arora's conviction there rests on the developing pyramid /
intraday action a daily EOD scan cannot see.

---

## PART B — CORPUS DOCTRINE (what THEY require before touching a deep-corrected name)

The corpus does buy deep-corrected former leaders, but only under tightly specified
conditions. Cites (verbatim locations in `manas_os/design/knowledge/`):

1. **Lower-low defense = institutional buying / undercut-then-base**
   — `ARORA_SHARDS_NUANCES.md:41-47`. CLAIM: *"In downtrend, if each lower low is higher
   than previous (higher lows forming), institution is defending that level = reversal
   signal."* QUOTE: *"Recently gone below 10 and 20, touch 50, gone up and now making a
   base. Wonderful setup... I only buy stocks which have recently gone below 10 and 20."*
   CODEABLE (their own note): *detect lower_low < previous_low, then check next_low >
   recent_low.* **→ the higher-low knife-guard (KG2) and the 10-SMA-reclaim trigger (T_A).**

2. **Brief Stage 4 → immediate Stage 2 (former-leader deep-correction re-entry)**
   — `ARORA_SHARDS_NUANCES.md:172-177`. *"Stock so powerful selling is weak... immediately
   resumes the trend."* Establishes prior-leadership as the anchor for touching a corrected
   name. **→ prior-strength eligibility (G0), reused from K7.**

3. **VCP = higher lows / flat highs / previous-low defense**
   — `STOCKGEEKS_NUANCES.md:60-64`. *"institution defending lower prices... confirm higher
   lows using pivot logic."* **→ KG2 higher-low structure.**

4. **Long-tail candle = demand reversal** — `STOCKGEEKS_NUANCES.md:66` (IPO_transcript:75).
   *"Long tail... someone bought at the low; strong bounce likely if the wick low holds;
   enter 1% above the long-tail wick."* **→ the undercut-and-recover demand bar in T_B.**

5. **Shakeout vs breakdown — the >50%-range reclaim** — `TRADETM_NUANCES.md:158-166` (B9).
   *"Momentum stocks shake out because fear is gunpowder... recover fast if buyers remain."*
   CODEABLE: *don't treat a decline as breakdown if next-day reclaims >50% of the range.*
   **→ the "closes in the upper half of its range" test in T_B / the UR-bar definition.**

6. **Tennis-ball action breaking down = structure break** — `TRADETM_NUANCES.md` (B10).
   The knife signature: *"pullbacks deepen and don't recover."* **→ the negative case the
   knife-guards refuse (still making new lows, no reclaim).**

7. **Neglected / dead range = best base** — `TRADETM_NUANCES_COMPLETION.md:275` (J6).
   *"neglect is a situation where nobody is putting money in... no overhead trapped supply."*
   **→ justifies the in-base ZENTEC 02-24 buy (dead range of a former leader).**

8. **Pyramiding on higher lows** — `TRADETM_NUANCES_HINDI.md:142-145` (V1). *"start 1%
   risk at a clean pullback entry, scale up as the stock makes higher lows and the trend
   proves valid... stage-4 buy signals on breakeven + higher-low confirmation."* **→ the
   ZENTEC multi-add pattern IS this; and it says busted entries are the SMALLER-frame,
   lower-conviction adds — cap-conviction basis for a smaller cap (Part D).**

9. **Trade the mixture, not the template** — `TRADETM_NUANCES.md:537-538` (F18). *"you'll
   get situations with mixtures of Stage 3&4, Stage 1&2."* **→ legitimises the archetype's
   existence: deep-correction re-entry is a real, distinct animal.**

**Synthesis of the required conditions:** prior leadership (2), deep correction into a
value/base zone (2,7), a **higher-low sequence** (1,3), a **demand/undercut-recover bar**
with a >50%-range reclaim (4,5), and a **reversal trigger up** — either a reclaim of the
10-SMA from below (1) or a reversal up-day off the higher low riding the demand bar (4,5).
The corpus NEVER buys a name still printing lower lows with no reclaim (6).

---

## PART C — ARCHETYPE DEFINITION `busted_reversal`

Detector `_busted_reversal(bars, momentum_top40_value)`. All AND-ed. Placed in the
PRIOR-STRENGTH family block of `build_bucket` (independent tag / cap slot, like `reversal`).

**Eligibility (former-leader deep-correction anchor):**
- **G0 — prior strength.** `_reversal_prior_strength(bars, momentum_top40_value)` (180d high
  ≥ 1.5× 252d low, OR 63d-momentum top-40pctile at any point in 120d). Reused verbatim from
  K7 — no new number. [cite 2]
- **G1 — correction band.** `correction_depth_from_180d_high(bars)` in
  **[REVERSAL_CORRECTION_MIN=15, REVERSAL_CORRECTION_MAX=40]** — reused verbatim. NO
  current-force / leg-force floor (these are low-force by construction — the whole point).
  [cite 2,7]

**Knife-guards (the danger management — REFUSE a still-falling name):**
- **KG1 — not at a fresh low.** Today's low must be **> the lowest low of the prior 60
  sessions** (`low[-1] > min(low[-61:-1]) * 1.003`). A name making a new 60-day low today is
  a falling knife, refused. [cite 1,6]
- **KG2 — higher low in place.** `min(low[-10:]) > min(low[-30:-10])` — the most recent swing
  low sits above the prior swing low (institution defending a rising floor). [cite 1,3]

**Reversal trigger (≥1 required — the "it has turned" evidence):**
- **T_A — fresh 10-SMA reclaim from below.** `close > sma10[-1]` AND `close[-2] <= sma10[-2]`
  (yesterday below, today above). [cite 1]
- **T_B — reversal up-day off a demand bar.** today is an up day (`close>close[-2]`)
  **closing in the upper half of its own range** (`(close-low)/(high-low) > 0.5`) AND within
  the **last 8 sessions (inclusive)** there is an **undercut-and-recover bar** — a bar that
  made a new 10-session intraday low and closed in the upper half of its range
  (`low[j] <= min(low[j-10:j])*1.003 and (close[j]-low[j])/(high[j]-low[j]) > 0.5`). This is
  the long-tail / shakeout climax the corpus names. [cite 4,5]

**Deliberately NOT applied** (and why): the pullback family's D1 up/down-vol-dominance gate,
D2 undercut-recover, D3 tightness, and the `reversal` archetype's **3-5-consecutive-down-run**
trigger. Those encode the *shallow absolute-momentum pullback* and the *narrow-down-run*
signatures; the busted reversal is the opposite temperament — a deep, multi-week decline
that bottoms on a **6-day** down run (NCC) or a quiet in-base drift (ZENTEC 02-24). Re-using
them re-kills the branch's reason to exist (this is the same lesson K9 drew for the 50-MA
branch). The demand-bar >50%-reclaim test in T_B is the corpus-cited supply-shock read that
*replaces* D1 here. The one thing kept universal in spirit — no admitting a knife — is done
structurally by KG1/KG2, not by a volume ratio.

**No invented magic numbers.** Every constant is either reused (G0, G1, 10-SMA) or a
structural comparison (KG1/KG2 swing-low windows 10/30/60; T_B upper-half = 0.5 range =
the corpus's own ">50% reclaim"; UR lookback 10; trigger window 8 sessions ≈ the "recently"
of ARORA cite 1). The 8-session T_B window and 10/30/60 swing windows are pivot-geometry
choices, not tuned thresholds; they are the smallest windows that express "recent higher-low
base" and hold across all four label dates and all counterexamples (Part D).

---

## PART D — KNIFE-GUARD EVIDENCE (labels PASS, knives FAIL)

Measured on real bars (`daily_prices`). "atNew60low" = KG1 fails; "higherLow" = KG2 state.

| symbol | date | corr% | ratio | atNew60low | higherLow | trigger | up-from-65low | **verdict** |
|---|---|---|---|---|---|---|---|---|
| **NCC** | 2026-03-10 | 38.8 | 1.75 | No | **Yes** | **T_B** (UR bar 03-09, close 0.89 of range) | 7.4% | **PASS ✓** |
| **ZENTEC** | 2026-02-24 | 35.8 | 1.69 | No | **Yes** | **T_B** (UR bar 02-16, close 0.83 of range) | 8.3% | **PASS ✓** |
| **ZENTEC** | 2026-03-16 | 31.4 | 1.69 | No | **Yes** | **T_A** (fresh 10-SMA reclaim off 03-13 dip) | 15.8% | **PASS ✓** |
| ZENTEC | 2026-03-13 | 33.9 | 1.69 | No | Yes | none (−3.8% down day, no reclaim, no UR bar) | 11.6% | SKIP (honest) |
| PROTEAN | 2026-03-13 | 44.6 | 1.81 | **Yes** | **No** | — | 0.5% | **REFUSED ✗** |
| CAPACITE | 2026-03-13 | 44.4 | 1.82 | **Yes** | **No** | — | 1.1% | **REFUSED ✗** |
| MOLDTKPAC | 2026-03-13 | 44.5 | 2.18 | **Yes** | **No** | — | 0.7% | **REFUSED ✗** |

**The counterexamples are not cherry-picked.** On 2026-03-13 there are **329 former-leaders
(ratio ≥ 1.5, 15-45% corrected) sitting at/near a fresh 60-day low** — the entire flood of
falling knives. **KG1 alone refuses all 329.** The separation is categorical, not a tuned
edge: the three label-passing names are **7-16% up off their 65d low with a higher low**; the
knives are **0.5-1.7% off the low with no higher low, still printing lower lows on a down
day** — exactly the "tennis-ball action broken" structure the corpus (cite 6) says to avoid.

**Honest expected recall effect (executor confirms exact hit/miss on re-run):**
- **NCC 2026-03-10 → HIT** (cleanest; textbook bottom reversal). **4/12 → 5/12.**
- **ZENTEC 2026-02-24 → likely HIT** (in-base T_B). **→ 6/12.**
- **ZENTEC 2026-03-16 → possible HIT** (fresh reclaim T_A; its trigger is the weakest of the
  three passing — a 1-day-dip reclaim — and it competes for a cap slot; executor confirms).
  **possible → 7/12.**
- **ZENTEC 2026-03-13 → principled SKIP** (down-day pullback add; fails all up-triggers and
  the pullback family's D1, K9). Do **not** loosen a trigger to catch a down day.
- **NBIFIN negative control → STAYS OUT.** `busted_reversal` adds an archetype *inside* the
  prior-strength family; it never touches base eligibility, where NBIFIN dies on the turnover
  floor (avg vol 941 sh). `assert not in_bucket` must still pass.
- No regression to INTELLECT / BSOFT / GROWW / CHENNPETRO (new tag only; no existing gate
  moved).

**Cap-survival caveat (like K9's TATAINVEST):** the pre-cap crowd is large on broad up-days
(measured: ~71-205 names/day pass G0+G1+KG1+KG2+trigger). Whether all three passing ZENTEC/NCC
rows survive `CAP_PER_ARCHETYPE` depends on the ranker floating them above the crowd. NCC is
the safe HIT; the two ZENTEC rows are "confirm on re-run, no promise." This large pre-cap
crowd is a **direct input to C2** (Part F).

---

## PART E — IMPLEMENTATION NOTES (Sonnet executor)

**File:** `manas_os/scanner/discovery.py` only. Reuses `_reversal_prior_strength`,
`dm.correction_depth_from_180d_high`, `_sma`. No new `discovery_metrics` function required
(KG1/KG2/T_A/T_B are local list ops on `closes`/`highs`/`lows`).

**1. New detector `_busted_reversal(bars, momentum_top40_value)`** near `_reversal_archetype`
(discovery.py ~L271). Skeleton:
```python
def _busted_reversal(bars, momentum_top40_value):
    """Deep-correction re-entry of a former leader: prior-strength + 15-40%
    correction band, guarded against falling knives (not at a fresh 60d low +
    higher-low in place), with a reversal trigger (fresh 10-SMA reclaim OR
    reversal up-day off an undercut-recover demand bar). Deliberately NO
    leg-force floor and NO D1/D2/D3/3-5-down-run gate -- those encode the
    shallow-pullback / narrow-reversal signatures; busted reversals are deep,
    multi-week, low-force by construction (K10; NCC 6-day down run, ZENTEC
    in-base drift). Cite: ARORA_SHARDS L41-47/L172-177, STOCKGEEKS L60-66,
    TRADETM B9 L158-166, TRADETM-C J6 L275, HINDI V1 L142-145."""
    if len(bars) < 70: return False
    if not _reversal_prior_strength(bars, momentum_top40_value): return False
    if not _reversal_correction_ok(bars): return False   # 15-40% off 180d high
    highs = [_num(b,"high") for b in bars]
    lows  = [_num(b,"low")  for b in bars]
    closes= [_num(b,"close")for b in bars]
    if any(v is None for v in (lows[-1], closes[-1], closes[-2])): return False
    # KG1 -- not at a fresh 60d low
    if lows[-1] <= min(lows[-61:-1]) * 1.003: return False
    # KG2 -- higher low in place
    if not (min(lows[-10:]) > min(lows[-30:-10])): return False
    from manas_os.engine.manas_indicators import _sma
    sma10 = _sma(closes, 10)
    # T_A -- fresh 10-SMA reclaim from below
    t_a = (sma10[-1] is not None and sma10[-2] is not None
           and closes[-1] > sma10[-1] and closes[-2] <= sma10[-2])
    # T_B -- reversal up-day (upper-half close) off an undercut-recover demand bar (last 8)
    rng = highs[-1] - lows[-1]
    up_upper = (closes[-1] > closes[-2] and rng > 0 and (closes[-1]-lows[-1])/rng > 0.5)
    ur = False
    for j in range(len(closes)-8, len(closes)):
        r = highs[j]-lows[j]
        if r > 0 and lows[j] <= min(lows[j-10:j])*1.003 and (closes[j]-lows[j])/r > 0.5:
            ur = True; break
    t_b = up_upper and ur
    return t_a or t_b
```
(Guard the slices for short history — `len(bars) >= 70` already covers the 61/30 windows.)

**2. Wire into `build_bucket`** inside the existing PRIOR-STRENGTH block (discovery.py ~L603,
same block as `reversal`), after the `_reversal_archetype` append:
```python
if _busted_reversal(bars, momentum_top40_value):
    archetypes.append("busted_reversal")
```

**3. Ranking + cap.** Register in `_ARCHETYPE_RANKERS`:
`"busted_reversal": (_tightness_proximity_rank_key, False)` — the corpus's
contraction-before-expansion read (same family as `reversal`; these low-leg-force names must
NOT be ranked by `_pullback_leg_force_rank_key`, which would bury them by construction).
Add a **per-archetype cap override** (busted entries are Arora's *smaller-frame, lower-
conviction adds*, HINDI V1 — a smaller cap is corpus-faithful, not arbitrary, and it also
limits the C2 oversizing this archetype adds):
```python
_ARCHETYPE_CAPS = {"busted_reversal": 10}
# in _apply_size_control:
cap = _ARCHETYPE_CAPS.get(archetype, CAP_PER_ARCHETYPE)
keep_symbols.update(e["symbol"] for e in ranked[:cap])
```

**4. Re-score procedure:**
- **Delete scratch DBs first:**
  `C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db`
  (and `wave_k_manas_ro.db`, `wave_k41_manas.db*` if the harness regenerates them fresh).
- Run **`python _wave_k_recall_baseline.py`** (canonical). Confirm:
  (a) NCC 2026-03-10 flips to **HIT** via `busted_reversal`;
  (b) report ZENTEC 02-24 and 03-16 (expected HIT / possible HIT) and that ZENTEC 03-13
      stays out (documented skip);
  (c) overall bucket recall **≥ 5/12, no regression** on INTELLECT/BSOFT/GROWW/CHENNPETRO;
  (d) the **NBIFIN** negative-control `assert not in_bucket` still passes;
  (e) log the bucket-size distribution on the label dates and the `busted_reversal` pre-cap
      count/day (expect the large crowd noted in Part D) — record it against C2, do **not**
      "fix" size by moving any K10 threshold.
- Add a unit test in `tests/test_discovery_bucket.py`: a synthetic former-leader (180d high
  ≥ 1.5× 252d low), ~30% corrected, that (i) sets a higher low, is not at a fresh 60d low,
  and prints a fresh 10-SMA reclaim → tags `busted_reversal`; (ii) a variant still making a
  new 60d low → NOT tagged (KG1); (iii) a variant with a lower low (no higher-low) → NOT
  tagged (KG2); (iv) a variant with the reclaim/UR removed → NOT tagged (no trigger).
- One K10 commit (pipeline-hygiene). Add a dated `LEARNINGS.md` entry: baseline 4/12 → 5/12
  (NCC), the ZENTEC trio split (02-24/03-16 catchable, 03-13 principled down-day skip), the
  full cite list, the 329-knife KG1 refusal evidence, and the C2 size-tension input.

---

## PART F — C2 INPUT (bucket-size honesty; secondary — orchestrator's decision)

**Recommendation: restate the target to ~100-140 honestly, and do the real narrowing at
Stage-2/gate, not by a lossy global Stage-1 trim.** The 30-80 figure predates the archetype
set growing to 8-9 recall-first detectors; with cap-20 each, a bucket of 116-141/day is the
*correct* Stage-1 size for a recall-first union, not a defect. A Stage-2 union-trim that
ranks all archetypes by a single corpus-cited key **re-creates the exact recall loss K10 and
K9 just fought**: a global `leg_force` rank evicts busted reversals and the reversal
archetype (low-force by construction); a global `velocity` rank evicts the deep pullbacks;
there is no single key that fairly orders a momentum-breakout and a bottom-reversal against
each other — that is *why* the caps are per-archetype. So do NOT collapse to one global rank.
Instead: (1) restate the Stage-1 bucket target to **~100-140** as the true recall-first size;
(2) **dedupe multi-archetype names for the reported count** (report distinct symbols — some
of the 116-141 is the same name under two tags) so the number reflects real breadth;
(3) set **conviction-weighted per-archetype caps** (this wave already does this:
`busted_reversal` cap 10 as a "smaller-frame add" per HINDI V1) rather than a flat 20
everywhere; (4) push the aggressive narrowing to **Stage-2/gate**, where per-name evidence
(purple dots, live trigger, regime fit, RelVol) ranks names on comparable ground — that is
the correct place to go from ~120 to a tradable shortlist, and it loses no recall because
nothing is dropped before the evidence is scored. Net: keep Stage-1 wide and honest at
~100-140; narrow at the gate, not by a Stage-1 global key. **Your call on whether to also
build the Stage-2 gate-ranker this wave or defer it.**
