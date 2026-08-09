# hudco — GOLD v2

| field | value |
|-------|--------|
| source_file | Hudco.png |
| symbol | HSG & URBAN DEV CORPN LTD · 1D |
| family | `long_dry_base_break` (subtype: **tighten_into_20ma_after_wide_rest**) |
| status | **gold** |
| teaching_style | Different sticker language: “Good Buying Force”, “Rest For 2.5 Months”, “Gone Tight Near 20 MA”, “Volume Contraction”, “47% Up Move” — map to pure geometry |

JSON: `entries/json/hudco.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68] — cut 47% up-move expansion  
- **decision_moment:** Right edge of 2.5-month rest where ranges **go tight near orange 20-MA** (grey box + arrow) after volume contraction  
- **visible:** left +173.94%/64d thrust; Feb–Apr wide rest (54b/80d); vol contracts; coil on 20  

## regions
| name | box | notes |
|------|-----|-------|
| impulse | 0.05–0.35, 0.10–0.70 | +173.94% / 44b / 64d, Vol 2.1B — “Good Buying Force” |
| rest | 0.35–0.68, 0.40–0.70 | “Rest For 2.5 Months”; 54b/80d, Vol 908.23M |
| tight_coil | 0.62–0.70, 0.55–0.65 | “Gone Tight Near 20 MA” |
| vol_contraction | 0.55–0.68, vol low | arrow “Volume Contraction” |
| entry | 0.66–0.72, 0.55–0.68 | leave of rest high / tight zone |
| expansion | 0.72–0.99 | “47% Up Move” mask |

## volume_signature
```
loud left thrust greens → mid rest mixed → clear contraction into right coil → expansion greens after leave
```

## unlabeled_detection_spec
**Must-see:** large prior advance; multi-month pause (here ~80d / “2.5 months”); pause may be **wider** mid-way (not only tight flag); **late range shrink into rising 20-MA**; volume contracts into that coil; leave rest high.  
**Hard reject:** tighten near 20 while 20 is rolling over hard under lower lows; volume expanding on mid-rest dumps without recovery.  
**Note:** Only orange MA heavily drawn (20) — still require rising intermediate MA support.

## transfer_rules
- Same primary family as IRFC/Gallant long bases; language differs (no BF number box).  
- “Gone tight near 20” = late coil feature also seen in TITAN tightness, but this panel is single-TF daily base-break.  
- Outcome 47% is smaller LF-class than IRFC 600% — still valid structure sample.

## lookalike_rejects
- 3-day LV pullback only.  
- Wide rest that never tightens (no coil) and breaks down.

## teacher
Good Buying Force +173.94%/64d · Rest 2.5 months / 54b/80d · Gone Tight Near 20 MA · Volume Contraction · 47% Up Move

## outcome_link
~47% measured advance after May leave. Mask.

## vision_tasks
1. Rest length labels? → 2.5 months / 80d.  
2. Where is entry geometry without stickers? → tight coil on 20 at right of blue rest box.  
3. Impulse %? → +173.94%.  
4. Family? → long_dry_base_break.
