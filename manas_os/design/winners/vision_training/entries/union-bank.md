# union-bank — GOLD v2

| field | value |
|-------|--------|
| source_file | Union Bank.png |
| symbol | UNION BANK OF INDIA · 1D |
| family | `short_tight_flag_break` |
| status | **gold** |
| nuance | +33.56%/64d; rest 28d/19b; BF40; LF 250%/60d & 100%/15d |

JSON: `entries/json/union-bank.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.58]
- **decision_moment:** Leave of 28d rest high
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +33.56% / 43b / 64d, Vol 407.21M
- Rest: 19b / 28d, Vol 141.3M
- BF: 40 · LF: 250% in 60 Days and 100% in 15 Days

## volume_signature
```
impulse → short dry → expansion
```

## unlabeled_detection_spec
**Family:** `short_tight_flag_break`
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
1. Family? → `short_tight_flag_break`
2. Rest/impulse labels? → see metrics
3. Entry geometry without stickers? → shelf/flag leave or tight-on-20 leave
4. Crop before what? → expansion rocket
