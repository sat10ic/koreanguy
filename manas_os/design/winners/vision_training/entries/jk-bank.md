# jk-bank — GOLD v2

| field | value |
|-------|--------|
| source_file | J&K Bank.png |
| symbol | J & K BANK LTD · 1D |
| family | `short_tight_flag_break` |
| status | **gold** |
| nuance | Rest only 16d/12b; impulse +35.93%/24d; MA text 10<20>50 messy; LF 300%/12d |

JSON: `entries/json/jk-bank.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.55]
- **decision_moment:** Leave of 16d short rest high
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +35.93% / 16b / 24d, Vol 229.14M
- Rest: 12b / 16d, Vol 74.16M
- BF: 33 · MA text 10<20>50 · LF: 300% in 12 Days

## volume_signature
```
impulse elevated → quieter rest → expansion
```

## unlabeled_detection_spec
**Family:** `short_tight_flag_break`
**Must-see:** fresh thrust; short 2-3 week rest near highs; quieter vol; leave rest high
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Twin IRFC-2/4 short-flag family.
- Imperfect 10>20>50 text OK if price structure rises.

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
