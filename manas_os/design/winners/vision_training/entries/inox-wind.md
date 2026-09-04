# inox-wind — GOLD v2

| field | value |
|-------|--------|
| source_file | Inox Wind.png |
| symbol | INOX WIND LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | +90.09%/72d impulse; 85d rest; dual entry arrows; LF 1000%/23d & 220%/8d; late-base red vol spike (HVY 118.96M 1684%) before full expansion |

JSON: `entries/json/inox-wind.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68]  
- **decision_moment:** Dual arrows leave of 85d shelf  
- **visible:** Jun–Aug grind +90%; Sep–Oct dry rest; Nov leave  

## regions
| name | notes |
|------|-------|
| impulse | +90.09% / 51b / 72d, Vol 501.7M |
| rest | 57b / 85d, Vol 392.83M |
| dry_up | mid desert |
| late_vol_event | red HVY 118.96M near leave — footprint/volatility into break |
| entry | dual Potential Entry arrows |
| expansion | mask to ~123 |

## volume_signature
```
impulse elevated → desert → loud event into break (incl. large red bar) → expansion
```

## unlabeled_detection_spec
**Must-see:** multi-week thrust; ~3 month rest under high; desert; leave with stack.  
**Supporting:** volume can **spike into the leave** (not only pure silence then green) — similar Gallant late footprints but may include red. Score price still holding structure.  
**Hard reject:** red spike that **breaks 50 and keeps falling**.

## transfer_rules
- HSCL-1/IRFC-1 tempo.  
- Dual arrows common in this corpus.

## teacher
BF 15&31 · Rest 85d · 10>20>50 · LF 1000%/23d & 220%/8d · Vol dry-up · dual Potential Entry · +90.09%/72d

## outcome_link
Nov–2024 advance ~50→123. Mask.

## vision_tasks
1. Rest? → 85d.  
2. Impulse %? → +90.09%.  
3. Late red HVY meaning? → volatility into break, not auto-reject if structure holds.
