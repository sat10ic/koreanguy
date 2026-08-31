"""Convert the real N1 2026-07-03 scan (markdown) to JSON for the picker."""
import json
from pathlib import Path

CANDIDATES = [
    {"symbol":"BANKA","close":74.18,"adr_pct":4.41,"rs_rank":98.0,"rvol":2.12,"contraction":0.73,"delivery_ratio":1.998,"trend":"STRONG_UPTREND","sessions":282,"adjusted":False,"detector":"momentum_burst","setup_title":"Momentum Burst"},
    {"symbol":"VLEGOV","close":15.84,"adr_pct":5.789,"rs_rank":91.6,"rvol":1.923,"contraction":0.734,"delivery_ratio":1.99,"trend":"TRANSITION","sessions":66,"adjusted":False,"detector":"momentum_burst","setup_title":"Momentum Burst"},
    {"symbol":"FILATEX","close":55.95,"adr_pct":3.683,"rs_rank":84.3,"rvol":3.194,"contraction":0.778,"delivery_ratio":3.445,"trend":"STRONG_UPTREND","sessions":282,"adjusted":False,"detector":"momentum_burst","setup_title":"Momentum Burst"},
]
REPORT = {"schema_version":1,"session_date":"2026-07-03","as_of":"2026-07-03T18:30:00+05:30","honesty_footer":{"regime_note":"not built yet (wave N2)","regime_built":False,"universe_scanned":2563,"universe_skipped_insufficient_history":197,"pct_above_ema50":65.86,"above_ema21":1653,"above_ema21_of":2563,"detection_inputs_policy":"Detection inputs missing for some symbols","adjustment_status":"unadjusted_provisional","actions_applied":0,"adjusted_symbols":0,"adjustment_note":"Unadjusted prices — long-window features are provisional.","disclaimer":"All outputs are rule results for research review. They are not recommendations, and nothing here places orders."},"setups":[{"detector":"momentum_burst","title":"Momentum Burst","candidate_count":3,"candidates":CANDIDATES}],"candidates":CANDIDATES}

R = Path(__file__).resolve().parent.parent
(R/"data"/"market"/"reports"/"tonight_2026-07-03.json").write_text(json.dumps(REPORT,indent=2)+"\n",encoding="utf-8")
(R/"unidesk_terminal"/"src"/"data"/"tonight_2026-07-03.json").write_text(json.dumps(REPORT,indent=2)+"\n",encoding="utf-8")
print(f"[historical] wrote 2026-07-03 JSON (3 candidates)")