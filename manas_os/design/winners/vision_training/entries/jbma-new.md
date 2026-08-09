# jbma-new — GOLD v2

| field | value |
|-------|--------|
| source_file | Jbma new.png |
| symbol | JBM AUTO LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Same campaign as JBMA with Hudco stickers: Rest 1.5 months; Gone Tight Near 20 MA; Volume Contraction; 84% Up Move |

JSON: `entries/json/jbma-new.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.62]
- **decision_moment:** Tight coil near 20MA at right of 1.5-month rest
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +62.50% / 41b / 66d, Vol 75.06M
- Rest: 30b / 43d, Vol 25.99M
- 84% Up Move · Gone Tight Near 20 MA · Volume Contraction

## volume_signature
```
thrust greens → contraction in rest → expansion on leave
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Same geometry as JBMA.png; Hudco-language late coil on 20.

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
