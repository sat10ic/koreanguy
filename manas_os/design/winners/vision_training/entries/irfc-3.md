# irfc-3 — GOLD v2

| field | value |
|-------|--------|
| source_file | IRFC 3.png |
| symbol | INDIAN RAILWAY FIN CORP L · 1D |
| family | `long_dry_base_break` (violent impulse + long flat) |
| status | **gold** |
| label_conflict | Purple **Rest: 28 days** vs white measure **58 bars / 88d** — use **shelf length / white box** for geometry |

JSON: `entries/json/irfc-3.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68] — cut 2024 parabola past ~110  
- **decision_moment:** Dual-arrow zone mid-Dec — probe then leave of Sep spike high  
- **visible:** +85.99%/12d spike; Sep–Dec desert under blue shelf; braided flat MAs  

## regions
| name | box | notes |
|------|-----|-------|
| impulse | 0.10–0.22, 0.35–0.58 | +85.99% / 8 bars / 12d, Vol 2.7B |
| shelf | 0.20–0.68, 0.52–0.56 | from spike high across quarter |
| rest | 0.22–0.68, 0.30–0.55 | 58b/88d measure; deep time base |
| dry_up_vol | 0.25–0.60, vol floor | Oct–Nov dust |
| entry_zone | 0.64–0.72, 0.48–0.60 | dual arrows Dec |
| expansion | 0.72–0.99 | mask; early LF then 2024 melt-up |

## volume_signature
```
spike_impulse loud → quarter desert → break expansion (HVQ 475.98M 719%) → later 492.71M class
```

## unlabeled_detection_spec
**Must-see:** violent short thrust creating hard high; pause **visually months** under that high; desert vol; late re-coil; leave with vol expansion.  
**Trigger:** 1–3 closes through multi-month shelf (two-step probe OK).  
**Hard reject:** treat purple “28d” alone as full rest if shelf spans Sep→Dec — **measure geometry wins**.  
**Invalidation:** fail under shelf on heavy vol.

## transfer_rules
- Longer cousin of IRFC-1 (72d); shorter than Genus 392d.  
- Dual entry arrows = staged leave, not single magic bar.  
- Early LF (70%/60%) may understate full right-edge move — don’t use LF for selection.

## lookalike_rejects
- IRFC-2/4 short flags (19–22d tight).  
- Label-only 28d rest without looking at shelf span.

## teacher
BF 34&27 · Rest 28d (conflict) · 88d measure · 10>20>50 · LF 70%/12d & 60%/4d · Vol dry-up · dual Potential Entry

## outcome_link
Early labeled LF legs then 2024 vertical to ~161. Mask expansion for selection.

## vision_tasks
1. Rest conflict? → 28d vs 88d; trust shelf.  
2. Impulse %? → +85.99%/12d.  
3. Entry style? → dual arrows.  
4. Family? → long_dry_base_break.
