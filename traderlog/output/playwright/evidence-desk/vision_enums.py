import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from traderlog.llm import vision as v

print("_PAYLOAD_KEYS:", sorted(v._PAYLOAD_KEYS))
print("_IMAGE_KINDS:", sorted(v._IMAGE_KINDS))
print("_TIMEFRAMES:", sorted(v._TIMEFRAMES))
print("_LEVEL_KINDS:", sorted(v._LEVEL_KINDS))
print("_NON_CHART_EVIDENCE_KINDS:", sorted(v._NON_CHART_EVIDENCE_KINDS))