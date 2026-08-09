# nbcc-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | NBCC 1.png |
| symbol | NBCC (INDIA) LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | +33.64%/17d; rest 34d/23b; BF43; LF 100%/18d |

JSON: `entries/json/nbcc-1.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.60]
- **decision_moment:** Leave of 34d shelf
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +33.64% / 13b / 17d, Vol 802.4M
- Rest: 23b / 34d, Vol 1.21B
- BF: 43 · LF: 100% in 18 Days

## volume_signature
```
impulse elevated → dry → expansion
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
