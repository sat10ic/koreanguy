# railtel — GOLD v2

| field | value |
|-------|--------|
| source_file | Railtel.png |
| symbol | RAILTEL CORP OF IND LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Hudco-style stickers: +115.05%/118d; Rest 3.5 months/106d; Gone Tight Near 20 MA; Volume Contraction; 40% Up Move |

JSON: `entries/json/railtel.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68]
- **decision_moment:** Tight near 20MA at right of 3.5-month rest
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Good BF: +115.05% / 81b / 118d
- Rest: 71b / 106d (3.5 months)
- 40% Up Move · Gone Tight Near 20 MA · Volume Contraction

## volume_signature
```
thrust → contraction in rest → expansion
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Same campaign as railtel-1 with Hudco language.

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
