# pullback-setup-3 — GOLD v2

| field | value |
|-------|--------|
| source_file | PullBack Setup 3.png |
| symbol | KPIT TECHNOLOGIES LTD · 1D |
| family | `lv_pullback_continuation` |
| status | **gold** |
| nuance | Prior +34.43%/60d; Down 5 Days -6.67%; Low Volume; 30% Up Move |

JSON: `entries/json/pullback-setup-3.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.70]
- **decision_moment:** After 5 quiet red days into rising 20MA, leave pullback high
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Prior: +34.43% / 42b / 60d
- Down 5 Days: -6.67%
- 30% Up Move · Low Volume

## volume_signature
```
trend → quiet under 5 reds → loud continuation
```

## unlabeled_detection_spec
**Family:** `lv_pullback_continuation`
**Must-see:** uptrend; 3-5 down days; quiet vol; holds rising MA; leave pullback high
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
