# jio — GOLD v2

| field | value |
|-------|--------|
| source_file | Jio.png |
| symbol | JIO FIN SERVICES LTD · 1D |
| family | `short_tight_flag_break` |
| status | **gold** |
| nuance | Rest only 2 weeks/11b/15d; impulse +33.75%/32d; Gone Tight Near 20 MA; 42% Up Move |

JSON: `entries/json/jio.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.58]
- **decision_moment:** Leave of 2-week tight rest on 20MA
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +33.75% / 21b / 32d, Vol 797.12M
- Rest: 11b / 15d (~2 weeks), Vol 609.23M
- 42% Up Move · Volume Contraction · Gone Tight Near 20 MA

## volume_signature
```
impulse elevated → contraction in short rest → expansion
```

## unlabeled_detection_spec
**Family:** `short_tight_flag_break`
**Must-see:** fresh thrust; short ~2 week rest; tighten near rising 20; vol contracts; leave
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Short-flag family with IRFC-4 / J&K Bank.
- 2-week rest valid when tight on 20.

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
