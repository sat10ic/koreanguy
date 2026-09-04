# -*- coding: utf-8 -*-
"""Bulk gold v2 entry generator for winner chart vision training."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
EDIR = os.path.join(BASE, "entries")
JDIR = os.path.join(EDIR, "json")
os.makedirs(JDIR, exist_ok=True)


def write_gold(r: dict) -> None:
    slug = r["id"]
    fam = r["family"]
    md = f"""# {slug} — GOLD v2

| field | value |
|-------|--------|
| source_file | {r['source_file']} |
| symbol | {r.get('symbol', '(see chart)')} |
| family | `{fam}` |
| status | **gold** |
| nuance | {r.get('nuance', '')} |

JSON: `entries/json/{slug}.json`

## pre_breakout_crop
- **crop_x:** {r.get('crop', '[0.00, 0.68]')}
- **decision_moment:** {r.get('decision', 'Leave of rest high after dry pause')}
- **visible:** {r.get('visible', 'Prior thrust; rest under hard high; dry volume; MA structure into leave — expansion masked')}

## key_metrics_on_chart (teacher)
{r.get('metrics_block', '(see JSON)')}

## volume_signature
```
{r.get('volume', 'thrust elevated → rest dry → expansion on leave')}
```

## unlabeled_detection_spec
**Family:** `{fam}`
**Must-see:** {r.get('must', 'prior thrust; multi-bar rest under hard high or short tight coil; volume dries vs thrust; leave with rising MA structure')}
**Trigger:** {r.get('trigger', 'acceptance through shelf/flag high or LV pullback high with vol uptick')}
**Hard reject:** {r.get('reject', 'no prior thrust; expanding supply into every high; already parabolic extended; climactic red dump as sole footprint')}
**Invalidation:** {r.get('invalid', 'fail back through shelf/pullback low on heavy volume; lose rising intermediate MA hard')}

## transfer_rules
{r.get('transfer', '- Same primary family as corpus peers with similar rest tempo.\\n- Geometry over BF text.')}

## lookalike_rejects
{r.get('lookalike', '- Wrong family tempo (3d pullback vs multi-month base).\\n- Late chase after large labeled LF already complete on panel.')}

## outcome_link
{r.get('outcome', 'Post-entry expansion per teacher LF/up-move labels. Mask for selection.')}

## vision_tasks
1. Family? → `{fam}`
2. Rest/impulse labels? → see metrics
3. Entry geometry without stickers? → {r.get('entry_q', 'shelf/flag leave or tight-on-20 leave')}
4. Crop before what? → expansion rocket
"""
    with open(os.path.join(EDIR, f"{slug}.md"), "w", encoding="utf-8") as f:
        f.write(md.replace("\\n", "\n"))
    skip = {
        "metrics_block",
        "must",
        "trigger",
        "reject",
        "invalid",
        "transfer",
        "lookalike",
        "outcome",
        "entry_q",
        "visible",
        "decision",
        "volume",
        "family",
    }
    jr = {k: v for k, v in r.items() if k not in skip}
    jr["status"] = "gold"
    jr["setup_family_primary"] = fam
    with open(os.path.join(JDIR, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump(jr, f, indent=2)
    print("wrote", slug)


# --- BATCH DATA (append as vision pass completes) ---
RECORDS = [
    dict(
        id="iob-2",
        source_file="IOB 2.png",
        symbol="INDIAN OVERSEAS BANK · 1D",
        family="long_dry_base_break",
        nuance="BF24; rest 113d/78b; impulse +91.04%/54d; LF 400%/40d; cleaner high-level rest than IOB-1 203d deep rebuild",
        crop="[0.00, 0.70]",
        decision="Leave of long blue shelf after 113d dry rest",
        metrics_block="- Impulse: +91.04% / 35b / 54d, Vol 3.22B\n- Rest: 78b / 113d, Vol 2.8B\n- BF: 24 · MA 10>20>50 · LF: 400% in 40 Days",
        volume="impulse HVQ/HVE loud → desert → break expansion",
        transfer="- Pair with IOB-1 (203d deep) — this is cleaner 113d high-level rest.\n- Tempo near IRFC-1 72d / slightly longer.",
        teacher_metrics={
            "buying_force": 24,
            "rest_days": 113,
            "impulse_pct": 91.04,
            "lf": ["400% in 40 Days"],
        },
    ),
    dict(
        id="ipl",
        source_file="IPL.png",
        symbol="INDIA PESTICIDES LTD · 1D",
        family="long_dry_base_break",
        nuance="Violent short impulse +44.30% in 5b/7d; rest ~3 months 55b/80d; MAs All 3 Coinciding; LF 300% in 4 Days",
        crop="[0.00, 0.65]",
        decision="Leave of multi-month shelf when MAs coincide under price",
        metrics_block="- Impulse: +44.30% / 5b / 7d, Vol 27.35M\n- Rest: 55b / 80d (~3 months), Vol 95.78M\n- BF: 36 · MAs All 3 Coinciding · LF: 300% in 4 Days",
        volume="impulse green spikes → dry mid rest → expansion greens after leave",
        must="prior thrust (even if ~1 week); multi-month rest under hard high; dry vol; MAs bunched then stack up on leave",
        transfer="- Fast impulse + long rest (IRFC-1 style duration).\n- All 3 coinciding = MA squeeze support feature.",
        teacher_metrics={
            "buying_force": 36,
            "rest_days": 80,
            "impulse_pct": 44.3,
            "lf": ["300% in 4 Days"],
            "ma_note": "all_3_coinciding",
        },
    ),
    dict(
        id="jk-bank",
        source_file="J&K Bank.png",
        symbol="J & K BANK LTD · 1D",
        family="short_tight_flag_break",
        nuance="Rest only 16d/12b; impulse +35.93%/24d; MA text 10<20>50 messy; LF 300%/12d",
        crop="[0.00, 0.55]",
        decision="Leave of 16d short rest high",
        metrics_block="- Impulse: +35.93% / 16b / 24d, Vol 229.14M\n- Rest: 12b / 16d, Vol 74.16M\n- BF: 33 · MA text 10<20>50 · LF: 300% in 12 Days",
        volume="impulse elevated → quieter rest → expansion",
        must="fresh thrust; short 2-3 week rest near highs; quieter vol; leave rest high",
        transfer="- Twin IRFC-2/4 short-flag family.\n- Imperfect 10>20>50 text OK if price structure rises.",
        teacher_metrics={
            "buying_force": 33,
            "rest_days": 16,
            "impulse_pct": 35.93,
            "lf": ["300% in 12 Days"],
        },
    ),
    dict(
        id="jai-corp",
        source_file="Jai Corp.png",
        symbol="JAI CORP LTD · 1D",
        family="long_dry_base_break",
        nuance="+41.84%/18d; rest 37d with deeper mid dip toward 50; BF42; LF 100%/15d & 50%/8d",
        crop="[0.00, 0.58]",
        decision="Leave of rest as MAs re-stack after dip",
        metrics_block="- Impulse: +41.84% / 12b / 18d, Vol 82.91M\n- Rest: 25b / 37d, Vol 59.31M\n- BF: 42 · LF: 100% in 15 Days and 50% in 8 Days",
        volume="impulse HVQ cluster → dry mid → HVY expansion 20-23M class",
        transfer="- Force Motors-like 37d rest tempo.\n- Deeper mid-rest dip OK if 50 holds.",
        teacher_metrics={
            "buying_force": 42,
            "rest_days": 37,
            "impulse_pct": 41.84,
            "lf": ["100% in 15 Days", "50% in 8 Days"],
        },
    ),
    dict(
        id="jbma",
        source_file="JBMA.png",
        symbol="JBM AUTO LTD · 1D",
        family="long_dry_base_break",
        nuance="+62.50%/66d; rest 43d/30b; BF45; LF 300% in 2 months",
        crop="[0.00, 0.62]",
        decision="Leave of 43d rest high near stack",
        metrics_block="- Impulse: +62.50% / 41b / 66d, Vol 75.06M\n- Rest: 30b / 43d, Vol 25.99M\n- BF: 45 · LF: 300% in 2 months",
        volume="trend elevated → rest dry-up → expansion tall greens",
        transfer="- Standard medium rest. Pair with jbma-new (Hudco-style labels, same metrics).",
        teacher_metrics={
            "buying_force": 45,
            "rest_days": 43,
            "impulse_pct": 62.5,
            "lf": ["300% in 2 months"],
        },
    ),
    dict(
        id="jbma-new",
        source_file="Jbma new.png",
        symbol="JBM AUTO LTD · 1D",
        family="long_dry_base_break",
        nuance="Same campaign as JBMA with Hudco stickers: Rest 1.5 months; Gone Tight Near 20 MA; Volume Contraction; 84% Up Move",
        crop="[0.00, 0.62]",
        decision="Tight coil near 20MA at right of 1.5-month rest",
        metrics_block="- Impulse: +62.50% / 41b / 66d, Vol 75.06M\n- Rest: 30b / 43d, Vol 25.99M\n- 84% Up Move · Gone Tight Near 20 MA · Volume Contraction",
        volume="thrust greens → contraction in rest → expansion on leave",
        transfer="- Same geometry as JBMA.png; Hudco-language late coil on 20.",
        teacher_metrics={
            "impulse_pct": 62.5,
            "rest_days": 43,
            "continuation_pct": 84,
            "sticker_style": "hudco",
        },
    ),
    dict(
        id="jio",
        source_file="Jio.png",
        symbol="JIO FIN SERVICES LTD · 1D",
        family="short_tight_flag_break",
        nuance="Rest only 2 weeks/11b/15d; impulse +33.75%/32d; Gone Tight Near 20 MA; 42% Up Move",
        crop="[0.00, 0.58]",
        decision="Leave of 2-week tight rest on 20MA",
        metrics_block="- Impulse: +33.75% / 21b / 32d, Vol 797.12M\n- Rest: 11b / 15d (~2 weeks), Vol 609.23M\n- 42% Up Move · Volume Contraction · Gone Tight Near 20 MA",
        volume="impulse elevated → contraction in short rest → expansion",
        must="fresh thrust; short ~2 week rest; tighten near rising 20; vol contracts; leave",
        transfer="- Short-flag family with IRFC-4 / J&K Bank.\n- 2-week rest valid when tight on 20.",
        teacher_metrics={
            "impulse_pct": 33.75,
            "rest_days": 15,
            "continuation_pct": 42,
        },
    ),
    dict(
        id="jk-tyre-1",
        source_file="Jk Tyre 1.png",
        symbol="JK TYRE & INDUSTRIES LTD · 1D",
        family="long_dry_base_break",
        nuance="+42.95%/47d; rest 44d/32b with mid dip; BF36; LF 400%/44d",
        crop="[0.00, 0.62]",
        decision="Leave of 44d shelf after dry mid and MA re-stack",
        metrics_block="- Impulse: +42.95% / 28b / 47d, Vol 85.16M\n- Rest: 32b / 44d, Vol 60.82M\n- BF: 36 · LF: 400% in 44 Days",
        volume="impulse HVQ → dry mid → expansion HVQ into trend",
        transfer="- Medium rest ~6 weeks. Pair with jk-tyre-2.",
        teacher_metrics={
            "buying_force": 36,
            "rest_days": 44,
            "impulse_pct": 42.95,
            "lf": ["400% in 44 Days"],
        },
    ),
]


if __name__ == "__main__":
    for rec in RECORDS:
        write_gold(rec)
    print("total", len(RECORDS))
