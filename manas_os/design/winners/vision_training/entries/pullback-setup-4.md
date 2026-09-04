# pullback-setup-4 — GOLD v2

| field | value |
|-------|--------|
| source_file | PullBack Setup 4.png |
| symbol | PNB HOUSING FIN LTD · 1D |
| family | `lv_pullback_continuation` |
| status | **gold** |
| nuance | Prior +33.59%/77d; Down 5 of 8 days -7.90%; Low Volume; 40% Up Move |

JSON: `entries/json/pullback-setup-4.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.72]
- **decision_moment:** After 5-of-8 down days on low vol into 20MA, resume
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Prior: +33.59% / 51b / 77d
- Down 5 of 8: -7.90%
- 40% Up Move · Low Volume

## volume_signature
```
trend → low vol dip → tall green continuation
```

## unlabeled_detection_spec
**Family:** `lv_pullback_continuation`
**Must-see:** uptrend; short multi-day pullback; quiet vol; MA hold; leave
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
