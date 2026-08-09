# mcx-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | MCX 1.png |
| symbol | MULTI COMMODITY EXCHANGE · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Long rest 169d after +90.93%/139d; deep mid-base drawdown; BF46; LF less than 50% (modest outcome label) |

JSON: `entries/json/mcx-1.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.72]
- **decision_moment:** Leave of multi-month shelf after deep rebuild
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +90.93% / 95b / 139d, Vol 51.4M
- Rest: 114b / 169d, Vol 49.85M
- BF: 46 · LF: less than 50%

## volume_signature
```
thrust → deep quiet mid → expansion
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Deep-base cousin of IOB-1.
- Modest LF still structure-valid sample.

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
