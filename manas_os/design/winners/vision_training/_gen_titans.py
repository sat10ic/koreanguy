# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Users\satta\Downloads\koreanguy\manas_os\design\winners\vision_training")
from _gen_gold import write_gold


def titan(n, symbol, outcome, extra=""):
    return dict(
        id=f"titan-setup-{n}",
        source_file=f"Titan Setup {n}.jpeg",
        symbol=symbol,
        family="titan_multi_tf_coil",
        nuance=f"TITAN curriculum #{n}. {extra}",
        crop="[0.00, 0.55]",
        decision="Daily tight/narrow pivot + volume dry-up while HTF ~10w anchor holds",
        metrics_block=(
            f"- TITAN checklist full\n- Symbol: {symbol}\n- Outcome: {outcome}"
        ),
        volume="mid footprints → dry at pivot → expansion",
        must="trend; footprint; tight narrow pivot; vol dry-up; weekly ~10w anchor",
        trigger="leave of daily narrow pivot while weekly anchored",
        teacher_metrics={"symbol": symbol, "outcome": outcome, "curriculum_index": n},
    )


batch = [
    titan(8, "COCHIN SHIPYARD LTD", "200% UP IN A 4 MONTHS", "EXIT BELOW 20 MA CLOSE"),
    titan(9, "DATA PATTERNS INDIA LTD", "51% UP IN 3 MONTHS", "EXIT BELOW 20 MA CLOSE"),
    titan(10, "DATAMATICS GLOBAL / FACT LTD context", "58% UP IN 1 MONTH", "EXIT BELOW 20 MA CLOSE; top strip DATAMATICS-style, daily FACT LTD label"),
    titan(11, "HPL ELECTRIC & POWER LTD", "43% UP IN 5 DAYS", "EXIT BELOW 20 MA CLOSE OR SELL INTO STRENGTH ON 5TH DAY"),
    titan(12, "HSG & URBAN DEV CORPN LTD", "45% UP IN 1 MONTH", "EXIT BELOW 20 MA CLOSE; Hudco TITAN framing"),
    titan(13, "INDRAPRASTHA MEDICAL CORP", "26% UP IN JUST OVER A MONTH", "EXIT BELOW 20 MA CLOSE"),
    titan(14, "JBM AUTO LTD", "85% UP IN LESS THAN A MONTH", "EXIT BELOW 20 MA CLOSE"),
    titan(15, "JINDAL DRILLING IND. LTD", "88% UP IN 3 MONTHS", "EXIT BELOW 20 MA CLOSE"),
]

for r in batch:
    write_gold(r)
print("wrote", len(batch))
