# setup-selection-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | Setup Selection 1.jpg |
| symbol | SBI CARDS & PAY SER LTD · 1W + 1D |
| family | `titan_multi_tf_coil` |
| status | **gold** |
| role | TITAN **selection-state** (no LF rocket label) — pair with titan-setup-1 |

JSON: `entries/json/setup-selection-1.json`

## pre_breakout_crop
- **Already mostly pre-breakout** — right edge is tight daily pivot + weekly anchor; little post-break expansion labeled  
- **decision_moment:** daily narrow pivot with dry vol while weekly blue candles defend rising purple MA  
- **visible:** weekly autumn pink selloff then 2025 reclaim/anchor; daily trend + two footprint bars + right tight+dry  

## regions
| name | notes |
|------|-------|
| weekly_correction | pink weeks into low |
| weekly_anchor | right blue weeks on purple MA |
| daily_trend | left-mid advance |
| inst_footprints | two tall mid daily vol bars |
| tight_pivot | right daily compression |
| dry_up | shortest right daily vol |

## volume_signature
```
weekly: loud early → quieter at right highs
daily: mid footprints → right dry-up under coil
```

## unlabeled_detection_spec
Same executable TITAN geometry as titan-setup-1.  
**Difference:** **no outcome %** — train `ready=true` at coil without hindsight multi-bagger.  
**Must-see:** weekly repaired trend + MA anchor; daily trend; footprints; tight+dry pivot.  
**Hard reject:** weekly still in freefall below MA; daily tight under falling MA.

## transfer_rules
- Primary twin of Titan Setup 1 without payoff leakage.  
- Prefer this sample for **selection** loss; Titan Setup 1 for full lifecycle including exit.

## lookalike_rejects
- Weekly lower lows under declining MA with “tight” daily noise.  
- Footprint = largest red dump bar only.

## teacher
TITAN legend · ANCHORED NEAR 10 WEEK · TREND · INSTITUTIONAL FOOT PRINT · TIGHTNESS AND NARROW PIVOT · VOLUME DRY-UP

## outcome_link
No LF label; weekly already elevated on right. Selection geometry only.

## vision_tasks
1. Does this slide show 176% outcome? → **No**.  
2. Weekly unique add? → 10w anchor after correction.  
3. Family? → titan_multi_tf_coil.  
4. Ready without rocket? → **Yes** if checks pass.
