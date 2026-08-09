# zentec-png — GOLD v2

| field | value |
|-------|--------|
| source_file | Zentec.png |
| symbol | ZEN TECHNOLOGIES LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Hudco-style: +108.30%/81d; Rest 3 months/99d; Gone Tight Near 20 MA; 38% Up Move; later breakdown visible right |

JSON: `entries/json/zentec-png.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68]
- **decision_moment:** Tight near 20MA leave of 3-month rest
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Good BF: +108.30% / 54b / 81d, Vol 35.54M
- Rest: 68b / 99d
- 38% Up Move · Volume Contraction · Gone Tight Near 20 MA

## volume_signature
```
thrust → contraction → expansion then later fail
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Daily base-break framing of Zen vs TITAN multi-TF slides.

## lookalike_rejects
- Wrong family tempo (3d pullback vs multi-month base).
- Late chase after large labeled LF already complete on panel.

## outcome_link
Post-entry expansion per teacher LF/up-move labels. Mask for selection.

## vision_tasks
1. Family? → `long_dry_base_break`
2. Rest/impulse labels? → see metrics
3. Entry geometry without stickers? → shelf/flag leave or tight-on-20 leave
4. Crop before what? → expansion rocket
