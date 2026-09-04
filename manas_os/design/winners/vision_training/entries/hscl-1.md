# hscl-1 — GOLD v2

| field | value |
|-------|--------|
| source_file | HSCL 1.png |
| symbol | HIMADRI SPECIALITY CHEM L · 1D |
| family | `long_dry_base_break` |
| status | **gold** |
| nuance | Strong impulse **+109.47%/34d**; rest **85d** (55b/83d measure); **two** entry arrows spaced in time (early leave + later continuation add) |

JSON: `entries/json/hscl-1.json`

## pre_breakout_crop
- **crop_x:** [0.00, 0.68] — first entry zone only; or [0.00, 0.78] if training second arrow as add — default **0.68** for first leave  
- **decision_moment:** First arrow — break of long blue shelf after dry base (~Dec)  
- **visible:** Aug–Sep +109% thrust; Oct–Nov dry chop under high; coil into shelf  

## regions
| name | box | notes |
|------|-----|-------|
| impulse | 0.12–0.32, 0.25–0.65 | +109.47% / 23b / 34d, Vol 214.88M; HVY 33.32M (556%) |
| rest | 0.32–0.65, 0.45–0.62 | 55b/83d, Vol 131.35M under blue high |
| dry_up_vol | 0.35–0.58, floor | Oct–Nov dust (Q/Y marks) |
| entry_1 | 0.62–0.70, 0.55–0.68 | first Potential Entry (shelf leave) |
| entry_2 | 0.78–0.85, 0.60–0.75 | second arrow later (continuation) |
| expansion | 0.70–0.99 | mask; LF 400%/38d & 50%/15d |

## volume_signature
```
impulse HVY 33M class → desert rest → lift at first break → more vol into 2024 continuation
```

## unlabeled_detection_spec
**Must-see:** large prior thrust (>~50% visual OK); long rest under hard high (~2–3 months); desert; first acceptance above shelf with stack.  
**Supporting:** second higher entry later if first worked — train **primary** as first shelf leave.  
**Hard reject:** buying only the second arrow without seeing first break structure; no desert.

## transfer_rules
- Strong-impulse cousin of GMDC (GMDC weaker impulse, same rest idea).  
- Dual arrows ≠ IRFC-3 dual (here spaced in **time along trend**, not probe+break same week).

## lookalike_rejects
- Calling second arrow the only setup while ignoring first leave.  
- Short flag 19d.

## teacher
BF 35&38 · Rest 85d · 10>20>50 · LF 400%/38d & 50%/15d · Vol dry-up · dual Potential Entry · +109.47%/34d · 55b/83d

## outcome_link
Post-break advance into ~360–380 zone. Mask.

## vision_tasks
1. Impulse %? → +109.47%.  
2. Rest ~days? → 85 (teacher) / 83 measure.  
3. How many entry arrows? → 2.  
4. Primary trigger? → first shelf leave.
