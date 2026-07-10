"""K2: BASELINE recall harness (scratch, read-only vs production tables).

Copies manas_os/data/manas.db to a scratch file first (scan_candidates_deterministic
writes to `refusals` + commits) so production is never touched, then for each
MAPPABLE labeled pick rebuilds the point-in-time candidate pool
(confluence_pool UNION detector_shortlist) for entry_date and entry_date-1,
and checks scan_candidates() gate-survivor membership on entry_date.
"""
import csv
import shutil
import sqlite3
from datetime import date, timedelta

import sys
sys.path.insert(0, ".")

from manas_os.scanner.candidates import confluence_pool, detector_shortlist, scan_candidates, latest_price_date

SRC_DB = "manas_os/data/manas.db"
SCRATCH_DB = r"C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro.db"
shutil.copyfile(SRC_DB, SCRATCH_DB)

conn = sqlite3.connect(SCRATCH_DB)
conn.row_factory = sqlite3.Row


def day_before(d: str) -> str:
    y, m, dd = map(int, d.split("-"))
    return (date(y, m, dd) - timedelta(days=1)).isoformat()


def pool_for(on_or_before: str) -> set[str]:
    price_date = latest_price_date(conn, on_or_before)
    if price_date is None:
        return set()
    _, cpool = confluence_pool(conn, on_or_before)
    shortlist = detector_shortlist(conn, price_date)
    return set(cpool.keys()) | set(shortlist)


def survivors_for(on_or_before: str) -> set[str]:
    result = scan_candidates(conn, on_or_before)
    return {c["symbol"] for c in result.get("candidates", [])}


rows = []
with open("manas_os/data/labels/practitioner_picks.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

mappable_rows = [r for r in rows if r["mappable"] == "True"]

results = []
pool_size_cache = {}
survivor_cache = {}

for r in mappable_rows:
    sym = r["symbol"]
    ed = r["entry_date"]
    edm1 = day_before(ed)

    if ed not in pool_size_cache:
        pool_size_cache[ed] = pool_for(ed)
    if edm1 not in pool_size_cache:
        pool_size_cache[edm1] = pool_for(edm1)
    if ed not in survivor_cache:
        survivor_cache[ed] = survivors_for(ed)

    pool_ed = pool_size_cache[ed]
    pool_edm1 = pool_size_cache[edm1]
    surv_ed = survivor_cache[ed]

    in_pool_entry_day = sym in pool_ed
    in_pool_day_before = sym in pool_edm1
    in_pool_either = in_pool_entry_day or in_pool_day_before
    is_survivor = sym in surv_ed

    results.append({
        "symbol": sym,
        "entry_date": ed,
        "archetype": r["archetype"],
        "source_cite": r["source_cite"],
        "in_pool_entry_day": in_pool_entry_day,
        "in_pool_day_before": in_pool_day_before,
        "in_pool_either": in_pool_either,
        "is_gate_survivor": is_survivor,
        "pool_size_entry_day": len(pool_ed),
        "pool_size_day_before": len(pool_edm1),
        "survivor_count_entry_day": len(surv_ed),
    })

# ---- report ----
n = len(results)
pool_hits = sum(1 for r in results if r["in_pool_either"])
surv_hits = sum(1 for r in results if r["is_gate_survivor"])

print(f"MAPPABLE label rows: {n} (of {len(rows)} total)")
print(f"POOL-level recall (entry_date OR entry_date-1): {pool_hits}/{n} = {pool_hits/n*100:.1f}%")
print(f"SURVIVOR-level recall (scan_candidates on entry_date): {surv_hits}/{n} = {surv_hits/n*100:.1f}%")
print()

print("Per-archetype:")
archs = sorted(set(r["archetype"] for r in results))
for a in archs:
    sub = [r for r in results if r["archetype"] == a]
    ph = sum(1 for r in sub if r["in_pool_either"])
    sh = sum(1 for r in sub if r["is_gate_survivor"])
    print(f"  {a}: pool {ph}/{len(sub)} ({ph/len(sub)*100:.0f}%) | survivor {sh}/{len(sub)} ({sh/len(sub)*100:.0f}%)")
print()

print("Per-source:")
srcs = sorted(set(r["source_cite"] for r in results))
for s in srcs:
    sub = [r for r in results if r["source_cite"] == s]
    ph = sum(1 for r in sub if r["in_pool_either"])
    sh = sum(1 for r in sub if r["is_gate_survivor"])
    print(f"  {s}: pool {ph}/{len(sub)} | survivor {sh}/{len(sub)}")
print()

print("Pool-size distribution across these dates (entry_day pool sizes):")
sizes = sorted(set(r["pool_size_entry_day"] for r in results))
for r in results:
    print(f"  {r['symbol']:12s} {r['entry_date']}  pool_ed={r['pool_size_entry_day']:4d}  pool_ed-1={r['pool_size_day_before']:4d}  survivors={r['survivor_count_entry_day']:4d}")
print()

print("Row-by-row:")
for r in results:
    print(f"  {r['symbol']:12s} {r['entry_date']}  archetype={r['archetype']:18s} "
          f"in_pool_entry={r['in_pool_entry_day']!s:5s} in_pool_d-1={r['in_pool_day_before']!s:5s} "
          f"survivor={r['is_gate_survivor']!s:5s}  [{r['source_cite']}]")
print()

groww = [r for r in results if r["symbol"] == "GROWW"]
print("GROWW row:", groww)
