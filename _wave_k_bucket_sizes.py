"""K4 size distribution: bucket size over a sample of the last 60 sessions
(every 3rd session), resumable via the scratch DB's discovery_bucket table."""
import json
import sqlite3
import sys

sys.path.insert(0, ".")
from manas_os.scanner.discovery import build_bucket, ensure_schema, persist_bucket

SCRATCH_DB = r"C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db"
conn = sqlite3.connect(SCRATCH_DB)
conn.row_factory = sqlite3.Row
ensure_schema(conn)

sessions = [r["d"] for r in conn.execute(
    "SELECT DISTINCT trade_date AS d FROM daily_prices WHERE series='EQ' "
    "ORDER BY trade_date DESC LIMIT 60").fetchall()]
sample = sorted(sessions[::3])  # every 3rd session of the last 60

sizes = []
for d in sample:
    done = conn.execute(
        "SELECT 1 FROM discovery_bucket WHERE scan_date=? AND symbol='__DONE__'", (d,)).fetchone()
    if done:
        n = conn.execute(
            "SELECT COUNT(*) FROM discovery_bucket WHERE scan_date=? AND symbol<>'__DONE__'",
            (d,)).fetchone()[0]
    else:
        b = build_bucket(conn, d)
        persist_bucket(conn, d, b)
        conn.execute("INSERT OR REPLACE INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
                     "VALUES (?, '__DONE__', '[]', '{}')", (d,))
        conn.commit()
        n = len(b)
    sizes.append((d, n))
    print(f"{d}  {n}", flush=True)

vals = [n for _, n in sizes]
vals_sorted = sorted(vals)
print(f"\nSAMPLE n={len(vals)} (every 3rd of last 60 sessions)")
print(f"min={min(vals)} p25={vals_sorted[len(vals)//4]} median={vals_sorted[len(vals)//2]} "
      f"p75={vals_sorted[3*len(vals)//4]} max={max(vals)} mean={sum(vals)/len(vals):.0f}")
print(f"in 30-80 target band: {sum(1 for v in vals if 30<=v<=80)}/{len(vals)}")

# archetype frequency across the sample
from collections import Counter
c = Counter()
for d, _ in sizes:
    for r in conn.execute("SELECT archetypes_json FROM discovery_bucket WHERE scan_date=? AND symbol<>'__DONE__'", (d,)):
        for a in json.loads(r["archetypes_json"]):
            c[a] += 1
print("\narchetype tag frequency across sample:", dict(c.most_common()))
conn.close()
