# Detection Playbook — Spot Winners Like This Corpus

**Use at inference on an unlabeled daily/weekly chart.**  
Do not require purple boxes, BF, LF, or TITAN stickers.

## Step 0 — Ignore chrome traps
- Header OHLCV may be **live** price; trust **candles on the plot**.
- Ignore emoji, text stickers, measure boxes if present (treat as absent).

## Step 1 — Read the right edge first
Ask: is the **latest 10–30% of the x-axis** (a) still inside a pause, (b) just leaving a pause, or (c) mid-parabolic with no structure left to buy?

| Right-edge state | Action |
|------------------|--------|
| Inside pause / coil under a clear high | Run family checklists (setup scan) |
| First 1–5 bars leaving a clear high/coil on rising vol | Setup **trigger** — highest priority |
| Already vertical for many bars, extended far above 10/20 | Late; do not treat as fresh setup unless a **new** tight pause formed |

## Step 2 — Find a prior thrust (required for this corpus)
Scan left of the pause for a **visibly dominant advance**:
- Large green bodies and/or steep slope vs earlier chop  
- Volume peak **during or just before** that thrust ≫ median of the later pause  

**Hard reject:** pause after a long downtrend with no thrust (bottom-fishing) — not this curriculum.

## Step 3 — Classify pause type (pick one primary)

### A. Long dry base (`long_dry_base_break`)
- Pause lasts **visually many weeks to months** under a **re-usable horizontal high** from the thrust (or early rest high).
- Mid-pause volume bars often **near floor** vs thrust peak (desert).
- Price may sink toward rising 50 or stay mid-range; late coil under the same high is bullish.
- **Trigger:** multi-bar **acceptance above the shelf**, preferably with volume lifting off the desert floor.

### B. Short tight flag (`short_tight_flag_break`)
- Pause **~2–5 weeks**, price **glued to 10/20** near highs; 50 well below.
- Volume quieter than thrust, not necessarily zero.
- **Trigger:** leave of the tight high / flag nose.

### C. LV pullback (`lv_pullback_continuation`)
- No long horizontal shelf required.
- **3–5 consecutive down/red days** (or equivalent short counter-swing).
- Depth typically **shallow vs prior leg** (corpus examples ~5–12% labeled).
- Those down days show **volume ≤ prior up-day volume** (quiet reds).
- Holds **rising 10 or 20**; 50 still rising below.
- **Trigger:** first strong reclaim / expansion off the pullback low through the pullback high.

### D. TITAN-style multi-TF coil (`titan_multi_tf_coil`)
Needs weekly (or higher) + daily when both visible:
- Weekly: price **anchored on rising ~10-week MA** (closes defend it).
- Daily: prior trend, **mid-structure volume spikes**, then **range shrink + volume shrink** into a narrow high.
- **Trigger:** daily leave of narrow pivot while weekly still on/above 10w MA.

## Step 4 — Volume sequence score (0–3)
Award one point each:
1. Thrust peak ≥ ~3× typical mid-pause bar height  
2. Clear dry stretch in the pause (many short bars)  
3. Volume rising again into/through the trigger (or footprints returning late in base — Gallant pattern)

**Selection bias in this corpus:** setups that score **2–3** dominate big outcomes. Score 0–1 → reject or downgrade.

## Step 5 — MA stack filter
At trigger time, prefer:
- Price above 10, 10 above 20, 20 above 50, all flat-to-up  
**Reject:** trigger while 50 is rolling over hard and price is under all three on expanding red volume.

## Step 6 — Output format (model should emit)
```json
{
  "family": "long_dry_base_break|short_tight_flag_break|lv_pullback_continuation|titan_multi_tf_coil|none",
  "ready": true,
  "trigger_seen": true,
  "confidence": 0.0,
  "evidence": ["...", "..."],
  "rejects_fired": [],
  "entry_zone_box": {"x0":0,"x1":0,"y0":0,"y1":0},
  "invalidation": "lose shelf / lose 20 on vol / close below 50..."
}
```

## Step 7 — Common false positives (always reject)
1. **Churny base:** volume **expands on every test of the high** and price fails — supply active.  
2. **High-volume dump pullback:** 3 red days on **largest volume of the chart** into falling MAs.  
3. **No prior thrust:** long sideways from nowhere.  
4. **Late chase:** entry zone is already many ATR above the shelf with climactic volume and upper wicks.  
5. **Broken 50 on the “rest”:** rest that is actually a **trend reversal** (lower lows under declining 50).  

## Calibration anchors from this folder (mental templates)

| Template chart | Family | Pre-breakout tell |
|----------------|--------|-------------------|
| IRFC 1 | long dry base | May spike high → summer desert under blue shelf → Aug leave |
| IRFC 2 / 4 | short tight flag | 19–22d high coil on 10/20 after loud thrust |
| Genus Power | long dry base (extreme clock) | Year under same high; deep early range; desert; break on huge vol |
| Gallant 1 | long dry base + late footprints | 57d rest; dry mid; **vol returns before break**; dip tags 50 |
| PullBack Setup 1–2 | LV pullback | 3–4 quiet reds into rising MAs after labeled prior uptrend |
| Titan Setup 1 / Setup Selection 1 | titan multi-TF | 10w anchor + daily tight+dry pivot |

When scoring a new name, ask: **which template does the geometry match?** not “is BF high?”.
