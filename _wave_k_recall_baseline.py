"""K2+K6: BASELINE recall harness (scratch, read-only vs production tables)
extended with WAVE K K4 Stage-1 SENSITIVE BUCKET membership.

Copies manas_os/data/manas.db to a scratch file first (scan_candidates_deterministic
writes to `refusals` + commits, discovery.run writes to discovery_bucket) so
production is never touched, then for each MAPPABLE labeled pick rebuilds:
  - the point-in-time OLD pool (confluence_pool UNION detector_shortlist) for
    entry_date and entry_date-1, and scan_candidates() gate-survivor membership
    (the K2 baseline, preserved verbatim);
  - the NEW Stage-1 discovery_bucket (build_bucket) for entry_date and
    entry_date-1, with archetype attribution (K6).
"""
import csv
import shutil
import sqlite3
from datetime import date, timedelta

import sys
sys.path.insert(0, ".")

from manas_os.scanner.candidates import confluence_pool, detector_shortlist, scan_candidates, latest_price_date
from manas_os.scanner.discovery import build_bucket

SRC_DB = "manas_os/data/manas.db"
SCRATCH_DB = r"C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db"
import os
if not os.path.exists(SCRATCH_DB):
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


bucket_cache: dict[str, list[dict]] = {}

# resumable: computed buckets persist into the SCRATCH db's discovery_bucket
# table so an interrupted run continues where it left off.
from manas_os.scanner.discovery import ensure_schema as _ensure_bucket_schema, persist_bucket
import json as _json
_ensure_bucket_schema(conn)


def bucket_for(on_or_before: str) -> list[dict]:
    price_date = latest_price_date(conn, on_or_before)
    if price_date is None:
        return []
    if price_date not in bucket_cache:
        stored = conn.execute(
            "SELECT symbol, archetypes_json, metrics_json FROM discovery_bucket WHERE scan_date = ?",
            (price_date,),
        ).fetchall()
        marker = conn.execute(
            "SELECT 1 FROM discovery_bucket WHERE scan_date = ? AND symbol = '__DONE__'",
            (price_date,),
        ).fetchone()
        if marker:
            bucket_cache[price_date] = [
                {"symbol": r["symbol"], "archetypes": _json.loads(r["archetypes_json"]),
                 "metrics": _json.loads(r["metrics_json"])}
                for r in stored if r["symbol"] != "__DONE__"
            ]
        else:
            b = build_bucket(conn, price_date)
            persist_bucket(conn, price_date, b)
            conn.execute(
                "INSERT OR REPLACE INTO discovery_bucket (scan_date, symbol, archetypes_json, metrics_json) "
                "VALUES (?, '__DONE__', '[]', '{}')", (price_date,))
            conn.commit()
            bucket_cache[price_date] = b
    return bucket_cache[price_date]


def bucket_lookup(on_or_before: str) -> dict[str, list[str]]:
    return {e["symbol"]: e["archetypes"] for e in bucket_for(on_or_before)}


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

    bucket_ed = bucket_lookup(ed)
    bucket_edm1 = bucket_lookup(edm1)
    in_bucket_entry_day = sym in bucket_ed
    in_bucket_day_before = sym in bucket_edm1
    in_bucket_either = in_bucket_entry_day or in_bucket_day_before
    archetypes_hit = sorted(set(bucket_ed.get(sym, []) + bucket_edm1.get(sym, [])))

    results.append({
        "symbol": sym,
        "entry_date": ed,
        "archetype": r["archetype"],
        "source_cite": r["source_cite"],
        "in_pool_entry_day": in_pool_entry_day,
        "in_pool_day_before": in_pool_day_before,
        "in_pool_either": in_pool_either,
        "is_gate_survivor": is_survivor,
        "in_bucket_entry_day": in_bucket_entry_day,
        "in_bucket_day_before": in_bucket_day_before,
        "in_bucket_either": in_bucket_either,
        "archetypes_hit": archetypes_hit,
        "pool_size_entry_day": len(pool_ed),
        "pool_size_day_before": len(pool_edm1),
        "survivor_count_entry_day": len(surv_ed),
        "bucket_size_entry_day": len(bucket_ed),
        "bucket_size_day_before": len(bucket_edm1),
    })

# ---- report ----
n = len(results)
pool_hits = sum(1 for r in results if r["in_pool_either"])
surv_hits = sum(1 for r in results if r["is_gate_survivor"])
bucket_hits = sum(1 for r in results if r["in_bucket_either"])

print(f"MAPPABLE label rows: {n} (of {len(rows)} total)")
print(f"OLD POOL recall (entry_date OR entry_date-1): {pool_hits}/{n} = {pool_hits/n*100:.1f}%")
print(f"OLD SURVIVOR recall (scan_candidates on entry_date): {surv_hits}/{n} = {surv_hits/n*100:.1f}%")
print(f"NEW BUCKET recall (entry_date OR entry_date-1): {bucket_hits}/{n} = {bucket_hits/n*100:.1f}%")
print()

print("Per-archetype (label archetype -> NEW bucket recall):")
archs = sorted(set(r["archetype"] for r in results))
for a in archs:
    sub = [r for r in results if r["archetype"] == a]
    ph = sum(1 for r in sub if r["in_pool_either"])
    bh = sum(1 for r in sub if r["in_bucket_either"])
    print(f"  {a}: OLD pool {ph}/{len(sub)} ({ph/len(sub)*100:.0f}%) | NEW bucket {bh}/{len(sub)} ({bh/len(sub)*100:.0f}%)")
print()

print("Row-by-row (OLD pool vs NEW bucket + which discovery archetype(s) caught it):")
for r in results:
    print(f"  {r['symbol']:12s} {r['entry_date']}  label_archetype={r['archetype']:18s} "
          f"OLD_pool={r['in_pool_either']!s:5s} OLD_survivor={r['is_gate_survivor']!s:5s}  "
          f"NEW_bucket={r['in_bucket_either']!s:5s} caught_by={r['archetypes_hit'] or '-'}")
print()

print("Bucket-size distribution across these dates (entry_day bucket sizes):")
for r in results:
    print(f"  {r['symbol']:12s} {r['entry_date']}  bucket_ed={r['bucket_size_entry_day']:4d}  "
          f"bucket_ed-1={r['bucket_size_day_before']:4d}")
print()

missed = [r for r in results if not r["in_bucket_either"]]
if missed:
    print(f"MISSED by new bucket ({len(missed)}/{n}):")
    for r in missed:
        print(f"  {r['symbol']:12s} {r['entry_date']}  [{r['source_cite']}]")
else:
    print("MISSED by new bucket: none")
print()

groww = [r for r in results if r["symbol"] == "GROWW"]
print("GROWW row:", groww)
print()

# ---- RAIN: not in the mappable label set (no dated practitioner pick), but
# LEARNINGS 2026-07-10 WAVE K2 flags it as a separate autopsy ("found daily
# by screeners, regime-family-killed 5x"). Report its bucket status explicitly
# on the latest EQ price date it has a screener_hits row, per K6 instructions.
rain_date = conn.execute(
    "SELECT MAX(trade_date) AS d FROM screener_hits WHERE symbol = 'RAIN' AND trade_date <= "
    "(SELECT MAX(trade_date) FROM daily_prices WHERE series='EQ')"
).fetchone()["d"]
print(f"RAIN row (not in mappable label set; separate LEARNINGS autopsy date {rain_date}):")
if rain_date:
    rain_bucket = bucket_lookup(rain_date)
    print(f"  RAIN in NEW bucket on {rain_date}: {'RAIN' in rain_bucket}  archetypes={rain_bucket.get('RAIN')}")
    rain_pool = pool_for(rain_date)
    print(f"  RAIN in OLD pool on {rain_date}: {'RAIN' in rain_pool}")
else:
    print("  no screener_hits row found for RAIN")

conn.close()
