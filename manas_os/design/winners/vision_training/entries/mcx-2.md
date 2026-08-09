# mcx-2 — GOLD v2

| field | value |
|-------|--------|
| source_file | MCX 2.png |
| symbol | MULTI COMMODITY EXCHANGE · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | +29.01%/37d mild impulse; rest 86d/59b; BF26; LF 70%/19d & 300%/23d |

JSON: `entries/json/mcx-2.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.65]
- **decision_moment:** Leave of 86d shelf
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +29.01% / 27b / 37d, Vol 13.62M
- Rest: 59b / 86d, Vol 33.18M
- BF: 26 · LF: 70% in 19 Days and 300% in 23 Days

## volume_signature
```
mild thrust → dry → expansion
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Same primary family as corpus peers with similar rest tempo.
- Geometry over BF text.

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
