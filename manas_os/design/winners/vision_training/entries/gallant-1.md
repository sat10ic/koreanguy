# gallant-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | Gallant 1.png |
| symbol_on_chart | GALLANTT ISPAT LTD · 1D · NSE |
| timeframe | Daily |
| setup_family_primary | `long_dry_base_break` (subtype: **late_base_volume_footprints**) |
| status | **gold** |
| chrome_traps | Header ~775 is late-panel era; date stamp Fri 11 Jul '25 marks entry region |

Machine twin: `entries/json/gallant-1.json`

---

## 1. pre_breakout_crop

| field | value |
|-------|--------|
| crop_x_range | **[0.00, 0.72]** — hide Jul–Aug vertical run to ~775 |
| decision_moment | Dual structure: (1) bounce/reclaim of **rising 50** after late-rest dip, and (2) leave of rest highs with **volume already re-ignited** |
| what_is_visible | Mar–Apr +52% staircase; May–Jun dry mid-base; late Jun **volume spikes while price still near base**; early Jul MA reclaim — **not** yet the full multi-bagger tower |

---

## 2. regions

| name | box (x0,x1,y0,y1) | conf | description |
|------|------------------|------|-------------|
| impulse | 0.15, 0.32, 0.22, 0.55 | high | Apr blue-box +52.66%/34d staircase |
| rest | 0.32, 0.70, 0.35, 0.58 | high | 57d drift/weave; late dip to green |
| shelf | 0.32, 0.62, 0.52, 0.56 | med | Blue line from early rest high |
| dry_up_volume | 0.35, 0.55, 0.02, 0.15 | high | May–mid Jun near-zero volume |
| late_footprints_vol | 0.55, 0.68, 0.25, 0.70 | high | HVQ 1.66M/953% & 1.75M/476% **before** full expansion |
| entry_zone | 0.65, 0.74, 0.48, 0.62 | high | Dual arrows / 50 reclaim + lift |
| expansion | 0.74, 0.98, 0.55, 0.95 | high | Run toward 690–775 (mask for selection) |

---

## 3. event_timeline

| id | phase | price_behaviour | duration | volume | ma_state | select? |
|----|-------|-----------------|----------|--------|----------|---------|
| E1 | impulse | Staircase greens +52.66% | 20 bars / 34d | elevated (HVQ ~511k class) | stack fans up | YES |
| E2 | rest | High → weave on 10/20 | ~May–mid Jun | **desert** | 10/20 flat-up | YES |
| E3 | rest_depth | Dip **tags green 50** | late rest | still moderate | 50 rising support | YES |
| E4 | prebreak_vol | Price still near base highs | late Jun–early Jul | **HVQ 953% & 476%** return | under/near 10/20 | YES — Gallant signature |
| E5 | trigger | Reclaim 50 + leave structure | ~11 Jul stamp | expanding into HVY 816% later | 10>20>50 | YES |
| E6 | expansion | Vertical to ~775 | Jul–Aug | HVY 3.54M (816%), U/D 3.2 | steep purple | NO |

---

## 4. volume_signature

```
pattern: elevated_impulse → desert_mid_base → LOUD_FOOTPRINTS_WHILE_STILL_IN_BASE → expansion
relative: mid_desert : late_footprint : expansion_peak ≈ 1 : 8–10 : 15+
critical_anomaly: volume returns BEFORE price is extended — demand re-enters at base prices
dry_up_definition: May–mid Jun bars ≈ dust vs Apr and vs late Jun spikes
```

---

## 5. unlabeled_detection_spec

**Family:** `long_dry_base_break` + **late footprint clause**

### Must-see (ALL)
1. Prior multi-week thrust with clear expansion candles (here +52%/34d).  
2. Multi-week pause (here ~57d) that does **not** destroy the rising 50.  
3. Mid-pause volume **collapses** vs thrust.  
4. **Either** (a) classic leave of shelf from desert, **or** (b) **Gallant path:** volume **spikes again while price is still inside/near the base** then price lifts with 10>20>50.

### Supporting
- Late rest dip that **holds the 50**.  
- Dual geometric tells at trigger: MA reclaim + structure break.  
- U/D volume bias rising into expansion (footer 3.2 on this sample).

### Trigger
- Price reclaims short/mid MAs after the late dip **and** breaks the rest high zone **with volume already above desert** (footprints acceptable *before* the first expansion gap).

### Hard reject
- Volume spikes in base that are **red, expanding, and produce lower lows under a falling 50** (distribution, not footprint).  
- No prior thrust.  
- Mid-base never dries (always loud).  

### Invalidation
- Post-trigger loss of the rising 50 on heavy red volume.

---

## 6. transfer_rules

1. When scanning new charts: if desert appears “broken” by late spikes, **check price location** — if spikes occur **near the base high with rising 50**, score as Gallant-type **footprint ignition**, not automatic reject.  
2. Contrast IRFC-1: pure desert until break is OK too — footprints are optional accelerator, not required.  
3. Same family as Genus on duration logic, but Genus is much longer and quieter mid-base.  
4. Do not require LF 9000% text — use geometry only.

---

## 7. lookalike_rejects

| Lookalike | Reject reason |
|-----------|---------------|
| Volume spike + crash through 50 | Distribution |
| Tight 3-day LV pullback only | Wrong family (pullback) |
| Year-long base with no late coil | Wait for compression/leave (Genus needs the leave) |

---

## 8. teacher_labels (supervision only)

BF 53 · Rest 57d · MA 10>20>50 · LF 9000%/28d & 500%/14d · Volume Dry Up · Potential Entry Point · +52.66%/34d · 40 bars/57d

---

## 9. outcome_link

Jul–Aug advance into ~775; extreme LF labels. Selection must work from crop without seeing 775.

---

## 10. vision_tasks

1. Mask expansion. Where is volume desert vs footprint return? → mid-base dust vs late HVQ 953%/476%.  
2. Does rest hold only 10/20 or also tag 50? → **tags 50** late.  
3. Entry is single shelf tip or dual MA+structure? → **dual**.  
4. Family + subtype? → long_dry_base_break + late footprints.  
5. Transfer: IRFC-1 has no late footprints — still same primary family? → **Yes**.

---

## 11. self_check

All gold boxes complete.
