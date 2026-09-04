# genus-power — GOLD v2

| field | value |
|-------|--------|
| source_file | Genus Power.png |
| symbol_on_chart | GENUS POWER INFRASTRU LTD · 1D · NSE |
| timeframe | Daily · ~Apr 2022 → Aug 2023 |
| setup_family_primary | `long_dry_base_break` (subtype: **extreme_duration**) |
| status | **gold** |

Machine twin: `entries/json/genus-power.json`

---

## 1. pre_breakout_crop

| field | value |
|-------|--------|
| crop_x_range | **[0.00, 0.78]** — cut the near-vertical Jun–Aug melt-up to ~221 |
| decision_moment | First multi-day **acceptance above the blue high drawn from the Apr/May 2022 spike**, after months of living underneath |
| what_is_visible | 2022 thrust + failed high; **year of range**; desert volume; late coil under same high; MAs finally re-stacking — **not** the 350%/9d tower |

---

## 2. regions

| name | box | conf | description |
|------|-----|------|-------------|
| impulse | 0.08, 0.18, 0.35, 0.58 | high | +72.27%/24d Apr–May 2022 |
| deep_base | 0.18, 0.55, 0.15, 0.50 | high | Wide vertical noise mid-2022 |
| late_coil | 0.55, 0.78, 0.35, 0.52 | high | 2023 tighten under shelf |
| shelf | 0.15, 0.78, 0.50, 0.54 | high | Single horizontal from 2022 high across entire panel |
| dry_up_volume | 0.20, 0.70, 0.02, 0.12 | high | Desert most of 2022–early 2023 |
| entry_zone | 0.75, 0.82, 0.48, 0.60 | high | Leave of year-long high |
| expansion | 0.82, 0.99, 0.55, 0.98 | high | Vertical to ~221 (mask) |

---

## 3. event_timeline

| id | phase | price_behaviour | duration | volume | select? |
|----|-------|-----------------|----------|--------|---------|
| E1 | impulse | Sharp +72% then volatile fail | 16 bars / 24d | HVQ~14M / HVY~10.7M | YES |
| E2 | deep_rest | **Gives back large fraction** of thrust; wide range | months | desert + tiny blips | YES |
| E3 | time_base | Sideways under same high; stamp Mon 26 Sep '22 mid | **267 bars / 392d** total rest measure | dust | YES |
| E4 | late_coil | Compress under shelf; MAs re-align | spring 2023 | still quiet | YES |
| E5 | trigger | Break year-high | ~Jun 2023 | vol lifts | YES |
| E6 | expansion | Vertical; LF 350%/9d | days–weeks | **HVY 30.93M** climax | NO |

---

## 4. volume_signature

```
pattern: loud_2022_impulse → year_desert → break_climax_loudest_on_chart
relative: mid_desert : 2022_impulse : break_peak ≈ 1 : 8 : 15+
note: loudest volume is at BREAK (30.93M), not only at first impulse — opposite of Force Motors left-climax story
```

---

## 5. unlabeled_detection_spec

### Must-see (ALL)
1. Clear historical thrust that creates a **reusable high**.  
2. Price spends a **very long time** (many months) mostly **below that high**.  
3. Early base may be **deep/wide** (not tight) — still valid if later compresses.  
4. Long stretches of **tiny volume bars** vs thrust peaks.  
5. At right of pause: **compression under the same high** + MAs no longer in chaos.

### Supporting
- Break volume becomes the **largest cluster on the visible chart**.  
- Modest “quality scores” if any text exists — geometry overrides (BF 24 here).

### Trigger
- Closes **through the long-term horizontal high** with volume expanding from desert, MAs stacked or stacking up.

### Hard reject
- Long base that is really a **downtrend channel** under declining 50 with no late coil.  
- Break attempt with **no** volume expansion after a year of quiet (weak).  
- Calling “Genus setup” on a 3-week flag (wrong duration class — use short_tight_flag).

### Invalidation
- Failed break: back under the long high quickly on heavy volume; or 50 rolls over hard.

---

## 6. transfer_rules

1. **Duration is a continuous variable:** 72d (IRFC-1), 57d (Gallant), 392d (Genus) are the **same family**. Do not require 392d.  
2. **Early base depth is allowed** — do not require VCP tightness for the whole year; require **late** tightness under the high.  
3. **BF can be low** — never gate on BF text.  
4. When a chart shows a high from **>6 months ago** still capping price with dead volume, run this checklist before dismissing as “too old.”

---

## 7. lookalike_rejects

| Lookalike | Reject |
|-----------|--------|
| Multi-month bear flag under falling MAs | Not rising-platform rest |
| Quiet base but **no** prior thrust high | Missing ceiling memory |
| Already vertical for weeks | Late chase |

---

## 8. teacher_labels (supervision)

BF 24 · Rest 392d · 10>20>50 · LF 350% in 9 Days · Volume Dry Up · Potential Entry · +72.27%/24d · 267 bars/392d

---

## 9. outcome_link

Post-break HVY 30.93M and ~221 high; LF 350%/9d. Selection crop must exclude this.

---

## 10. vision_tasks

1. How long is the shelf in bars/days? → 267 / 392.  
2. Is the base tight all year? → **No** — deep early, tight late.  
3. Where is loudest volume? → **Break cluster ~30.93M**.  
4. Family? → long_dry_base_break extreme_duration.  
5. Would BF 24 fail unlabeled_detection_spec? → **No**.

---

## 11. self_check — complete
