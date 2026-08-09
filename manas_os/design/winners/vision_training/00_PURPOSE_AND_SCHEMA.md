# Winner Chart Vision Training — Gold Protocol (v2)

## Purpose

Train a **vision LLM** to **select winners on unlabeled charts** by recognizing the same price/volume geometry that appears in `manas_os/design/winners/`.

**Inference target (what the model must do on a new chart):**  
Score whether the *right edge* of the chart is a **setup ready zone** (or just broke one), using only candles, volume bars, and MAs — **ignoring** any teaching stickers if present.

**What failed in v1 notes:** prose stories after the move. v2 forces **pre-breakout detection specs**, **spatial regions**, **relative volume sequences**, **transfer rules**, and **lookalike rejects**.

---

## How a vision model is trained on each entry

| Phase | Input | Target output |
|-------|--------|----------------|
| A. Locate | Full chart image | Normalized boxes: impulse, rest/pause, dry-up volume band, pivot/shelf, entry zone |
| B. Pre-breakout quiz | Crop with **post-entry expansion masked/hidden** (described in entry if crop not separate file) | Setup family + pass/fail checklist + “ready / not ready” |
| C. Unlabeled brief | Same crop, no teacher text | `unlabeled_detection_spec` only |
| D. Outcome link | Full chart | Confirm expansion matched the setup (supervision only; not used at selection time) |
| E. Transfer | New chart | Apply `transfer_rules` + reject `lookalike_rejects` |

Teacher purple/green labels are **supervision answers**, never required features at inference.

---

## Coordinate system (mandatory)

All regions use **normalized chart plot coordinates** (price pane only, not volume pane unless said):

- `x`: 0.0 = left of candles, 1.0 = right of candles  
- `y`: 0.0 = **bottom** of price pane, 1.0 = **top** of price pane  

Volume regions use the volume pane with the same x, y local to that pane.

If uncertain, write `approx:` and a confidence (`high|med|low`). Never invent false precision.

---

## Gold entry schema (every image, v2)

Markdown file + matching JSON under `entries/json/<slug>.json`.

### 1. Meta
```yaml
id, source_file, symbol_on_chart, timeframe, panel_layout, series_role
chrome_traps: []   # e.g. header OHLC is live price, not panel era
status: gold | draft
```

### 2. setup_family_primary
One of: `long_dry_base_break` | `short_tight_flag_break` | `lv_pullback_continuation` | `titan_multi_tf_coil` | `other`

### 3. pre_breakout_crop (CRITICAL)
Describe what the model is allowed to use **as if the rocket did not exist yet**.

```yaml
crop_x_range: [0.0, 0.72]   # hide right expansion when training selection
what_is_visible_at_decision_time: |
  ...only structure left of entry...
decision_moment: "first close accepting above shelf" | "3rd red day of LV pullback holding MA" | ...
```

### 4. regions[] (spatial ground truth)
```yaml
- name: impulse | rest | shelf | dry_up_volume | entry_zone | expansion | ma_stack_zone
  pane: price | volume
  box: {x0, x1, y0, y1}   # normalized
  confidence: high|med|low
  description: one line
```

### 5. event_timeline[] (ordered, relative — not generic prose)
Each event:
```yaml
- id: E1
  phase: impulse | rest | coil | trigger | expansion | exit
  when_on_chart: "x~0.15–0.28, May cluster"
  price_behaviour: concrete (staircase / 8 fat green / 4 red bodies / tabletop)
  duration: "8 bars / 11d" or "approx 3 weeks visual"
  volume_vs_local_median: "≈10×" | "≈0.2×" | "dead dust" | labeled HVY if on chart
  ma_state: "price>10>20>50 rising" | "braided flat" | "dip into 20, 50 still rising"
  counts_as_feature: true|false   # true = usable at selection time
```

### 6. volume_signature (sequence, not a single word)
```yaml
pattern: [loud_impulse, desert_rest, optional_prebreak_footprint, expansion]
relative_heights: "impulse peak : rest median : break peak ≈ 10 : 1 : 8"
dry_up_definition: "≥N bars with height ≤ ~20% of nearest prior impulse peak"
anomalies: "e.g. volume returns inside late base before price breaks"
```

### 7. unlabeled_detection_spec (THE TRAINABLE CORE)
Write as **IF / THEN / ELSE reject** rules a vision model can execute on any chart of this family.

Must include:
- **Must-see** (all required)
- **Supporting** (2 of 3, etc.)
- **Hard reject** (any one fails the setup)
- **Trigger definition** (exact geometric event)
- **Invalidation** (what kills it after trigger)

**Forbidden words inside this block:** Buying Force, LF%, TITAN (unless defining pure geometry), “constructive”, “strong demand”.

### 8. transfer_rules
How to recognize *similar* winners that are not this ticker:
```yaml
- "If rest length is 3 weeks instead of 10 but shelf is tight, volume desert, and 10>20>50 — still long_dry_base_break family (IRFC-2/4 tempo)."
```

### 9. lookalike_rejects
Charts that *look* related but should score low:
```yaml
- "Deep red expansion volume into new lows under falling 50 — not LV pullback."
- "Base with rising volume into the high every test — not dry-up."
```

### 10. teacher_labels (supervision only)
Separate table; never inside `unlabeled_detection_spec`.

### 11. outcome_link (supervision only)
What happened after trigger on **this** image; LF only if labeled.

### 12. vision_tasks (exam questions for the model)
At least 5, answerable from the **image** (or pre-breakout crop), with short answers.

### 13. self_check
- [ ] Pre-breakout crop defined  
- [ ] ≥4 regions with boxes  
- [ ] volume_signature is a sequence  
- [ ] unlabeled_detection_spec has must/support/reject/trigger  
- [ ] transfer_rules + lookalike_rejects non-empty  
- [ ] No outcome leakage inside unlabeled_detection_spec  

---

## Family detection cheat-sheet (cross-entry)

| Family | Pre-breakout look | Trigger | Typical volume seq |
|--------|-------------------|---------|-------------------|
| `long_dry_base_break` | Prior thrust then multi-week/month action under a **hard horizontal high**; vol dies mid-base | Acceptance **through the shelf** with vol expansion | loud → desert → loud |
| `short_tight_flag_break` | After thrust, **2–4 week** high tight coil on 10/20; 50 below | Leave of coil high | loud → quieter → loud |
| `lv_pullback_continuation` | Established uptrend; **3–5 red days** into rising 10/20; **no** multi-month shelf | Reclaim of pullback high / first green expansion | trend vol → **quiet reds** → loud greens |
| `titan_multi_tf_coil` | HTF price hugging ~10w MA; LTF trend + mid vol spikes + **tight high + dry vol** | LTF leave of narrow pivot while HTF still anchored | footprints mid → dry at pivot → expansion |

---

## Specificity bar (still mandatory)

Chronological walkthrough + instance facts remain required. v2 **adds** detection machinery on top; it does not replace landmarks.

**Test A (human):** strip filename — still unique chart?  
**Test B (vision train):** can you run `unlabeled_detection_spec` on a masked pre-breakout crop and get pass/fail without seeing the rocket?  
**Test C (transfer):** do `transfer_rules` mention at least one other corpus chart by family tempo?

If any test fails → not gold.

---

## File layout

```
vision_training/
  00_PURPOSE_AND_SCHEMA.md      # this protocol
  01_INDEX.md
  02_PATTERN_TAXONOMY.md
  03_DETECTION_PLAYBOOK.md      # cross-chart inference procedure
  entries/
    <slug>.md                   # gold markdown
    json/<slug>.json            # machine target
```

## Status of corpus

- **v2 gold:** only entries explicitly marked `status: gold`  
- Older draft narrative entries are **insufficient for vision training** until upgraded to this schema.
