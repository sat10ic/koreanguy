# pullback-setup-2 — GOLD v2

| field | value |
|-------|--------|
| source_file | PullBack Setup 2.png |
| symbol | SONATA SOFTWARE LTD · 1D |
| family | `lv_pullback_continuation` |
| status | **gold** |

JSON: `entries/json/pullback-setup-2.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.70] — cut +34% expansion  
- **decision_moment:** After **3 red days (−4.68%)** on low vol, leave of 3-day high  
- **visible:** blue-box prior +20.04%/37d; 3 reds; quiet vol; **ignore earlier left washout under green**  

## regions
| name | box | notes |
|------|-----|-------|
| prior_uptrend | 0.35–0.62, 0.25–0.55 | +20.04% / 26b / 37d, Vol 8.89M |
| pullback | 0.62–0.70, 0.48–0.58 | **3 red** days, −4.68% |
| lv_vol | 0.62–0.70, vol low | Low Volume arrow |
| entry | 0.68–0.75, 0.50–0.62 | reclaim |
| expansion | 0.75–0.99 | +34% mask |

## volume_signature
```
trend_mixed → quiet under 3 reds → tall green vol on +34% leg
```

## unlabeled_detection_spec
**Must-see:** uptrend left of dip; **3–5** quiet red/down days; shallow vs prior leg; holds rising 10/20; first leave of pullback high.  
**Hard reject:** climactic red volume; break falling 50; multi-week rectangle (switch to base family); using **left early washout** as the setup.  
**vs PB1:** shallower (−4.7% vs −12%) and shorter prior (+20% vs +81%).

## transfer_rules
- Same family as PullBack Setup 1 (Force); depth/time vary.  
- Gate on quiet short dip + MA hold, not exact %.

## lookalike_rejects
- Early left green-undercut on this chart.  
- 4-week base under flat high.

## teacher
Prior Uptrend +20.04%/37d · Down 3 Days · −4.68% · Low Volume · 34% Up Move

## outcome_link
+34% labeled continuation. Mask for selection.

## vision_tasks
1. Down days? → 3.  
2. Depth? → −4.68%.  
3. Prior %? → +20.04%.  
4. Family? → lv_pullback_continuation.
