# psb — GOLD v2

| field | value |
|-------|--------|
| source_file | PSB.png |
| symbol | PUNJAB & SIND BANK · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | +65.01%/40d; rest 125d; multi-arrow; BF27&32; LF 400%/41d & 100%/13d |

JSON: `entries/json/psb.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.70]
- **decision_moment:** Multi-arrow leave of 125d shelf
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +65.01% / 26b / 40d, Vol 271.54M
- Rest: 85b / 125d, Vol 345.02M
- BF: 27 and 32 · LF: 400% in 41 Days and 100% in 13 Days

## volume_signature
```
impulse HVE → long dry → expansion
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
