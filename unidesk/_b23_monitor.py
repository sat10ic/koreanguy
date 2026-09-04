"""B2-3 progress from persisted disk state ONLY (never process absence)."""
import json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
EVENTS = Path("data/market/research/events")
tally = Counter()
parts = 0
for d in EVENTS.glob("date=*"):
    pj = d / "events.parquet"
    if not pj.exists():
        continue
    parts += 1
    try:
        import pyarrow.parquet as pq
        md = pq.read_metadata(pj)
        # snapshot_json holds ca_table_hash per row; read just that column
        t = pq.read_table(pj, columns=["snapshot_json"])
        for i in range(t.num_rows):
            snap = json.loads(t.column("snapshot_json")[i].as_py() or "{}")
            tally[snap.get("ca_table_hash", "MISSING")] += 1
    except Exception as e:
        tally[f"ERROR:{type(e).__name__}"] += 1
print("partitions:", parts)
for h, n in tally.most_common():
    print(f"  {h}: {n}")
