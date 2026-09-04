# irfc-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | IRFC 1.png |
| symbol_on_chart | INDIAN RAILWAY FIN CORP L · 1D · NSE |
| timeframe | Daily |
| panel_layout | single |
| series_role | IRFC series stage 1 |
| setup_family_primary | `long_dry_base_break` |
| status | **gold** |
| chrome_traps | Header ~125 is live-era chrome; train on plotted May–Aug 2023 structure only |

Machine twin: `entries/json/irfc-1.json`

---

## 1. pre_breakout_crop

| field | value |
|-------|--------|
| crop_x_range | **[0.00, 0.70]** — cut off the vertical Aug rocket and volatile top |
| decision_moment | First cluster of closes **accepting through the long horizontal shelf** built from the May impulse high, with volume lifting from desert (teacher arrow sits here; model must find geometry without it) |
| what_is_visible_at_decision_time | Left May thrust; summer-long chop under a flat high; dead mid volume; MAs flat then starting to re-tip up at the right of the crop; **no** large green tower yet |

**Training rule:** selection loss is computed on this crop only. Expansion is used only in outcome_link.

---

## 2. regions (normalized, price pane unless noted)

| name | box (x0,x1,y0,y1) | conf | description |
|------|------------------|------|-------------|
| impulse | 0.12, 0.28, 0.25, 0.55 | high | May blue-box thrust, fat green bodies |
| shelf | 0.26, 0.68, 0.48, 0.52 | high | Thin horizontal band = multi-month resistance from impulse high |
| rest | 0.28, 0.68, 0.28, 0.52 | high | Chop between shelf and rising green 50 |
| dry_up_volume | 0.32, 0.62, 0.05, 0.25 | high | volume pane: near-floor bars mid-base |
| entry_zone | 0.66, 0.74, 0.45, 0.58 | high | Leave of shelf / first acceptance |
| expansion | 0.74, 0.98, 0.50, 0.95 | high | Post-trigger rocket (mask in phase B) |
| impulse_volume | 0.12, 0.28, 0.30, 0.95 | high | volume pane: green/blue mountains under May thrust |

---

## 3. event_timeline

| id | phase | when | price_behaviour | duration | volume_vs_local_median | ma_state | for_selection? |
|----|-------|------|-----------------|----------|------------------------|----------|----------------|
| E1 | impulse | x~0.12–0.28, May | ~8 large green bodies, near-vertical | 8 bars / 11d labeled | **≈10×+** (HVQ 343M/702%, HVY cluster) | 10/20/50 turn up under thrust | YES — proves demand |
| E2 | rest_start | just after May high | Sharp red rejection off high | few bars | still elevated then falling | stack flattens | YES |
| E3 | rest | x~0.30–0.65, Jun–Jul | Overlapping small candles; **sinks toward green 50**; cannot hold shelf | 51 bars / 72d labeled | **≈0.1–0.2×** impulse (“desert”) | purple≈orange, often braided; green slow rise | YES — core dry base |
| E4 | coil | x~0.62–0.70 | Ranges shrink just under shelf | ~1–2 weeks visual | still quiet then lifting | MAs re-bunch, tip up | YES |
| E5 | trigger | x~0.68–0.74 | Closes through shelf | few bars | blue expansion off floor (HVE/HVY labels) | price >10>20>50 emerging | YES — decision |
| E6 | expansion | x>0.74 | Steppy large greens to ~49–60 zone | days–weeks | loud again | purple goes near-vertical | NO (outcome only) |

---

## 4. volume_signature

```
pattern: loud_impulse → desert_rest → expansion_at_break
relative_heights (visual): impulse_peak : mid_rest : break_cluster ≈ 10 : 1 : 6–8
dry_up_definition: majority of bars from ~x0.35–0.60 have height ≤ ~15–20% of May peak bars
anomaly: none major — pure desert until break (contrast Gallant, where vol returns early)
```

---

## 5. unlabeled_detection_spec  ★ executable on any chart

**Family:** `long_dry_base_break`

### Must-see (ALL)
1. **Prior thrust:** a short window of large-range up candles whose slope/body size dominate the left half of the recent history (here: ~8 bars, labeled +33.76% / 11d).  
2. **Hard high:** that thrust leaves a **horizontal resistance** that price fails to hold for a long time afterward.  
3. **Long pause under that high:** pause duration **visually >> thrust duration** (here: ~72d vs 11d).  
4. **Volume desert mid-pause:** mid-pause volume bars **much shorter** than thrust volume peaks (order-of-magnitude).  
5. **Rising or flat-up longer MA under the pause:** green 50 not in freefall; base is a platform, not a waterfall.

### Supporting (≥2)
- Price works **down toward the 50** during the pause then coiling up (depth OK if 50 holds).  
- Late pause: candle ranges shrink under the shelf.  
- At leave: volume **expands** vs desert median.

### Trigger (fire `ready=true` only when)
- **≥1–3 daily closes accepting above the multi-week/month shelf**, with volume **above** desert median, and price back above the short MA.

### Hard reject (any)
- No prior thrust (pause from nowhere).  
- Pause volume **stays loud** or **grows into every test of the high**.  
- “Rest” prints **lower lows under a declining 50** with expanding red volume.  
- Right edge already **many large green bars extended** far above shelf with no new pause (late chase).

### Invalidation after trigger
- Fast return **below the shelf** on expanding volume, or loss of the rising 50 shortly after a failed break.

---

## 6. transfer_rules (spot *similar* winners)

1. **Same family, longer clock:** Genus Power — year under one high, desert, then break (BF can be modest).  
2. **Same family, medium clock:** Gallant 1 — ~57d rest; allow **late volume footprints inside base** before break.  
3. **Same skeleton, faster clock:** IRFC 2/4 — if rest is only ~3 weeks but **tight under the high** with dry-ish vol, reclassify primary as `short_tight_flag_break` but keep thrust→quiet→leave logic.  
4. **Ignore absolute price:** IRFC at ~3 vs Force at thousands — geometry is scale-free.  
5. **Ignore teacher BF:** this panel BF=17 still worked; do **not** require high BF text — require thrust+desert+shelf geometry.

---

## 7. lookalike_rejects

| Lookalike | Why reject |
|-----------|------------|
| Tight 4-day red dip in uptrend | That is `lv_pullback_continuation` (PullBack Setup 1), not a 72d base |
| Sideways chop with **no** prior vertical thrust | Missing must-see #1 |
| High-volume multi-month range that expands every rally into the high | Supply active; not desert |
| Breakout already 50%+ extended on climax bars | Late; not entry_zone |

---

## 8. teacher_labels (supervision only — do not require at inference)

| text | maps_to_feature |
|------|-----------------|
| Buying Force: 17 | Weak/modest thrust score (counterexample: still works) |
| Rest: 72 days | Long pause length |
| MA's 10>20>50 | Stack at trigger |
| LF: 600% in 14d and 100% in 8d | Outcome magnitude |
| Volume Dry Up in Base | desert_rest |
| Potential Entry Point | entry_zone box |
| +33.76% / 8 bars / 11d | impulse metrics |
| 51 bars / 72d | rest metrics |

---

## 9. outcome_link (supervision only)

After E5, price rockets; dual LF labels 600%/14d and 100%/8d; volatile top later.  
**Do not use LF to select.** Use only to reinforce that E1–E5 geometry preceded a large move on this sample.

---

## 10. vision_tasks

1. **Mask x>0.70.** Is a long dry base present? → Yes: May high shelf + summer desert.  
2. Point to entry_zone without reading “Potential Entry Point”. → First acceptance through blue shelf ~x0.70.  
3. Ratio of rest duration to impulse duration (labels). → ~72/11 ≈ 6.5×.  
4. Is mid-base volume closer to 1× or 0.1× of May peaks? → ~0.1× desert.  
5. BF is 17 — reject setup? → **No** under unlabeled_detection_spec (geometry passes).  
6. Classify family. → `long_dry_base_break`.

---

## 11. self_check

- [x] Pre-breakout crop  
- [x] ≥4 regions  
- [x] volume sequence  
- [x] must/support/reject/trigger  
- [x] transfer + lookalikes  
- [x] no outcome inside unlabeled_detection_spec  

---

## 12. compact chart_walkthrough (landmarks)

May: +33.76%/11d on billion-scale vol → hard high. Jun–Jul: 72d chop sinks toward rising 50, volume dies (Fri 02 Jun '23 mid). Early Aug: leave shelf = entry. Then vertical expansion to high-40s/60s left scale. BF 17 / LF 600% are teacher-only.
