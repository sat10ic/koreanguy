# Image Index — Winner Chart Vision Training

**Folder:** `manas_os/design/winners/`  
**Total images:** 100  
**Protocol:** v2 gold — `00_PURPOSE_AND_SCHEMA.md` + `03_DETECTION_PLAYBOOK.md`  

## Progress — COMPLETE

| tier | count |
|------|------:|
| **gold v2** | **100 / 100** |
| JSON twins | **100 / 100** |
| pending | **0** |

Every source image has:
- `entries/<slug>.md` — pre-breakout crop, metrics, volume signature, unlabeled_detection_spec, transfer/lookalike rules, vision tasks  
- `entries/json/<slug>.json` — machine twin  

## Family coverage

| family | examples |
|--------|----------|
| `long_dry_base_break` | IRFC 1/3, Gallant, Genus, GMDC, HSCL, banks, most named winners, Hudco-style stickers |
| `short_tight_flag_break` | IRFC 2/4, J&K Bank, Jio, KIOCL, Map my India, Union Bank |
| `lv_pullback_continuation` | PullBack Setup 1–5 |
| `titan_multi_tf_coil` | Titan Setup 1–30, Setup Selection 1–8, Sigachi/SJVN/TD Power/Titagarh/Zentec.jpg |

## Slug list (100)

force-motors, gallant-1, gallant-2, genus-power, gmdc-1, gmdc-2, hscl-1, hscl-2, hudco, ifci, inox-wind, iob-1, iob-2, ipl, ircon, irfc-1, irfc-2, irfc-3, irfc-4, jai-corp, jbma, jbma-new, jio, jk-bank, jk-tyre-1, jk-tyre-2, kiocl, ksolves, map-my-india, mazdock-1, mazdock-2, mcx-1, mcx-2, nbcc-1, nbcc-2, pnb-giltz, ppl, psb, pullback-setup-1..5, quickheal, railtel, railtel-1..3, rites, setup-selection-1..8, shalby, sigachi, sjvn, sunflag, td-power, titagarh, titan-setup-1..30, uco-bank-1, uco-bank-2, union-bank, voltamp-1, voltamp-2, zentec-jpg, zentec-png

## Notes

- Some files are near-duplicates across formats/series (e.g. Titan Setup 28 ≈ Sigachi.jpg, Titan Setup 29 ≈ SJVN.jpg, Titan Setup 30 ≈ TD Power.jpg, Titan Setup 2 ≈ TITAGARH.jpg, Zentec.jpg ≈ Titan Setup 1). Entries note `related` / near-duplicate where observed.  
- BF/LF/rest figures are **teacher-labeled on charts**, not independently recomputed from OHLC.  
- Inference without stickers: use `03_DETECTION_PLAYBOOK.md` + each entry’s `unlabeled_detection_spec`.  

**Completed:** 2026-07-12  
