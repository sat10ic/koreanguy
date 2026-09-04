# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Users\satta\Downloads\koreanguy\manas_os\design\winners\vision_training")
from _gen_gold import write_gold


def titan(n, src, symbol, outcome=None, extra=""):
    return dict(
        id=f"titan-setup-{n}",
        source_file=src,
        symbol=symbol,
        family="titan_multi_tf_coil",
        nuance=f"TITAN curriculum #{n}. {extra}",
        crop="[0.00, 0.55]",
        decision="Daily tight/narrow pivot + volume dry-up while HTF ~10w anchor holds",
        metrics_block=(
            f"- TITAN: Tightness, Institutional Foot Print, Trend, Anchored ~10 Week, Narrow Pivot\n"
            f"- Symbol: {symbol}\n"
            f"- Outcome labels: {outcome or 'see panel / selection-state'}"
        ),
        volume="mid footprints → dry at pivot → expansion if shown",
        must="trend into pause; volume footprint; range shrink narrow pivot; vol dry-up; HTF near rising ~10w MA",
        trigger="leave of daily narrow pivot with vol uptick while weekly still anchored",
        teacher_metrics={
            "symbol": symbol,
            "outcome": outcome,
            "curriculum_index": n,
        },
    )


def sel(n, src, symbol, extra=""):
    return dict(
        id=f"setup-selection-{n}",
        source_file=src,
        symbol=symbol + " · 1W+1D",
        family="titan_multi_tf_coil",
        nuance=f"Setup Selection #{n} TITAN selection-state. {extra}",
        crop="setup-state right edge",
        decision="Right-edge daily tight+dry; weekly near 10w",
        metrics_block=f"- TITAN checklist on {symbol}\n- Selection-state (no LF required)",
        volume="footprints mid → dry at right pivot",
        must="TITAN pure geometry; ignore stickers at inference",
        teacher_metrics={"symbol": symbol, "role": "selection_state", "curriculum_index": n},
    )


batch = [
    sel(5, "Setup Selection 5.jpg", "HSG & URBAN DEV CORPN LTD", "Hudco weekly repair then anchor"),
    sel(6, "Setup Selection 6.jpg", "HIMATSINGKA SEIDE LTD", "weekly re-anchor; daily trend+footprint+tight dry"),
    sel(7, "Setup Selection 7.jpg", "AU SMALL FINANCE BANK LTD", "weekly reclaim 10w"),
    sel(8, "Setup Selection 8.jpg", "CHENNAI PETROLEUM CORP LTD", "weekly reclaim after long decline"),
    titan(3, "Titan Setup 3.jpeg", "ACTION CONST EQUIP LTD", None, "Entry Point + Volume Drying labels; weekly Anchored Near 10 Week"),
    titan(4, "Titan Setup 4.jpeg", "ADANI POWER LTD", "50% UP IN A WEEK", "footprint then dry-up into rocket"),
    titan(6, "Titan Setup 6.jpeg", "BLS INTL SERVS LTD", "45% UP IN 2 MONTHS", "EXIT BELOW 20 MA CLOSE"),
    titan(7, "Titan Setup 7.jpeg", "CENTRAL DEPO SER (I) LTD", "107% UP IN 3 MONTHS", "EXIT BELOW 20 MA CLOSE"),
]

for r in batch:
    write_gold(r)
print("wrote", len(batch))
