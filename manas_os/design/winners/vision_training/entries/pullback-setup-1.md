# pullback-setup-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | PullBack Setup 1.png |
| symbol_on_chart | FORCE MOTORS LTD · 1D · NSE |
| setup_family_primary | `lv_pullback_continuation` |
| status | **gold** |
| note | Same ticker as Force Motors.png base study — **different family** |

Machine twin: `entries/json/pullback-setup-1.json`

---

## 1. pre_breakout_crop

| field | value |
|-------|--------|
| crop_x_range | **[0.00, 0.72]** — hide the measured +40% expansion tower |
| decision_moment | After **4 red days** into rising mid-MAs on **quiet volume**, on the **first strong leave** of that 4-day swing high |
| what_is_visible | Long blue-shaded prior uptrend; four red bodies mid-right; small volume oval under them; MAs still rising — **not** the 40% measure arrows |

---

## 2. regions

| name | box | conf | description |
|------|-----|------|-------------|
| prior_uptrend | 0.15, 0.62, 0.15, 0.70 | high | Blue shade +80.81%/54d |
| pullback_bars | 0.62, 0.70, 0.55, 0.72 | high | Exactly **four red** bodies |
| lv_volume | 0.62, 0.70, 0.08, 0.22 | high | Circled short red vol hump |
| ma_support | 0.55, 0.72, 0.40, 0.58 | high | Purple/orange rising under dip |
| entry_zone | 0.68, 0.75, 0.58, 0.75 | high | Reclaim of 4-day high / first expansion |
| expansion | 0.75, 0.98, 0.60, 0.95 | high | +40.33% leg (mask) |

---

## 3. event_timeline

| id | phase | price_behaviour | duration | volume | select? |
|----|-------|-----------------|----------|--------|---------|
| E1 | prior_trend | Higher highs, above rising 3-MA fan | 38 bars / 54d, +80.81% | mixed; some tall greens | YES |
| E2 | pullback | **4 consecutive red** bodies; −12.35% | 4 days | **low** (circled) | YES |
| E3 | trigger | Leave pullback high | 1–3 bars | vol starts up | YES |
| E4 | expansion | Measured +40.33% | days–weeks | tall green vol | NO |

---

## 4. volume_signature

```
pattern: normal/elevated_trend → QUIET_RED_PULLBACK → loud_green_continuation
rule: pullback red volume height < nearby prior green expansion bars
relative: quiet_red_hump : post_break_green_peaks ≈ 1 : 3–5+
```

---

## 5. unlabeled_detection_spec

**Family:** `lv_pullback_continuation`

### Must-see (ALL)
1. **Established uptrend** immediately left of the dip: rising price + rising MAs (not a bounce in a bear market).  
2. **Short counter-swing:** about **3–5** down/red days (this sample: **4**).  
3. **Shallow vs prior leg:** dip % much smaller than recent advance % (here −12% after +81%).  
4. **Quiet volume on the down days** relative to prior up days.  
5. Dip **holds the rising 10 or 20** (50 still rising below) — no crash through the whole stack on heavy vol.

### Supporting
- Prior leg duration multi-week (here 54d).  
- Clear visual separation: long blue trend region then tiny red patch.

### Trigger
- First solid expansion **through the high of the 3–5 day pullback** with volume ≥ pullback volume.

### Hard reject
- Down days on **climactic volume** (largest bars on chart).  
- Pullback that **breaks the rising 50** and keeps making lower lows.  
- “Pullback” that is actually **10–20+ red days** (becomes a base problem — switch checklist).  
- No prior uptrend (buying a falling knife).

### Invalidation
- Immediate failure back through pullback low on expanding volume; or 20-MA rolls over hard.

---

## 6. transfer_rules

1. **Sonata PullBack Setup 2:** same family with **3 days / −4.68%** after only **+20%** prior — shallower template; still valid.  
2. Depth can vary (~5–12% in corpus) — gate on **time short + volume quiet + MA hold**, not exact %.  
3. **Never confuse with Force Motors.png base study** (37d rest after +95%) — same name, different geometry.  
4. If you see a **horizontal multi-month shelf**, switch to `long_dry_base_break` checklist.

---

## 7. lookalike_rejects

| Lookalike | Reject |
|-----------|--------|
| 4 red days after a long downtrend | No prior uptrend |
| 4 red days with huge volume | Distribution |
| 4 red days that undercut declining 50 | Trend break |
| 40-day rectangle under a high | Wrong family (base) |

---

## 8. teacher_labels (supervision)

Prior Uptrend +80.81%/54d · Down 4 Days · −12.35% · Low Volume · 40% Up Move / +40.33%

---

## 9. outcome_link

+40.33% continuation after trigger. Mask for selection training.

---

## 10. vision_tasks

1. Count red days in the taught dip. → **4**.  
2. Is volume on those days high or low vs neighbors? → **Low** (circled).  
3. Prior trend %? → **+80.81%**.  
4. Family vs IRFC-1? → pullback vs long dry base.  
5. Same symbol as Force base slide — same setup? → **No**.

---

## 11. self_check — complete
