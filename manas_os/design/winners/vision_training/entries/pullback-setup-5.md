# pullback-setup-5 — GOLD v2

| field | value |
|-------|--------|
| source_file | PullBack Setup 5.png |
| symbol | HOME FIRST FIN CO IND LTD · 1D |
| family | `lv_pullback_continuation` |
| status | **gold** |
| nuance | Prior +48.46%/17d; Down 4 Days -7.67%; Low Volume; 20% Up Move |

JSON: `entries/json/pullback-setup-5.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.70]
- **decision_moment:** After 4 quiet red days into 20MA, leave
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Prior: +48.46% / 10b / 17d
- Down 4 Days: -7.67%
- 20% Up Move · Low Volume

## volume_signature
```
prior thrust → quiet 4 reds → continuation
```

## unlabeled_detection_spec
**Family:** `lv_pullback_continuation`
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
1. Family? → `lv_pullback_continuation`
2. Rest/impulse labels? → see metrics
3. Entry geometry without stickers? → shelf/flag leave or tight-on-20 leave
4. Crop before what? → expansion rocket
