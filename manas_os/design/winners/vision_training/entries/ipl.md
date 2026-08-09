# ipl — GOLD v2

| field | value |
|-------|--------|
| source_file | IPL.png |
| symbol | INDIA PESTICIDES LTD · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Violent short impulse +44.30% in 5b/7d; rest ~3 months 55b/80d; MAs All 3 Coinciding; LF 300% in 4 Days |

JSON: `entries/json/ipl.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.65]
- **decision_moment:** Leave of multi-month shelf when MAs coincide under price
- **visible:** Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked

## key_metrics_on_chart (teacher)
- Impulse: +44.30% / 5b / 7d, Vol 27.35M
- Rest: 55b / 80d (~3 months), Vol 95.78M
- BF: 36 · MAs All 3 Coinciding · LF: 300% in 4 Days

## volume_signature
```
impulse green spikes → dry mid rest → expansion greens after leave
```

## unlabeled_detection_spec
**Family:** `long_dry_base_break`
**Must-see:** prior thrust (even if ~1 week); multi-month rest under hard high; dry vol; MAs bunched then stack up on leave
**Trigger:** acceptance through shelf/flag high or LV pullback high with vol uptick
**Hard reject:** no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint
**Invalidation:** fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard

## transfer_rules
- Fast impulse + long rest (IRFC-1 style duration).
- All 3 coinciding = MA squeeze support feature.

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
