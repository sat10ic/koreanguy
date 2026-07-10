"""K6 diagnosis: for each label pick missed by the NEW Stage-1 bucket, report
exactly WHICH condition failed (base eligibility / buying force / velocity /
no archetype), with the measured values. Read-only vs the resumable scratch DB.
"""
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from manas_os.scanner.candidates import latest_price_date
from manas_os.scanner import discovery as dsc
from manas_os.scanner import discovery_metrics as dm
from manas_os.engine import eod_detectors
from manas_os.engine.universe_filter import evaluate_symbol

SCRATCH_DB = r"C:\Users\satta\AppData\Local\Temp\claude\C--Users-satta-Downloads-koreanguy\0e2937d8-3968-42ab-b54d-0cec0571174a\scratchpad\wave_k_manas_ro2.db"
conn = sqlite3.connect(SCRATCH_DB)
conn.row_factory = sqlite3.Row

PICKS = [
    ("CHENNPETRO", "2025-10-17"),
    ("COALINDIA", "2025-10-10"),
    ("EMSLIMITED", "2025-11-06"),
    ("INTELLECT", "2025-08-21"),
    ("TATAINVEST", "2026-06-05"),
    ("BSOFT", "2026-06-12"),
    ("NCC", "2026-03-10"),
    ("ZENTEC", "2026-02-24"),
    ("GROWW", "2026-07-09"),
]


def day_before(d):
    y, m, dd = map(int, d.split("-"))
    return (date(y, m, dd) - timedelta(days=1)).isoformat()


def _pctile_pop(scan_date):
    """Recompute eligible-universe populations (momentum + adr) for a date."""
    syms = dsc._universe_symbols(conn, scan_date)
    asm = dsc._asm_symbols(conn, scan_date)
    mom_pop, adr_pop = [], []
    for sym in syms:
        if sym in asm:
            continue
        bars = dsc._load_bars(conn, sym, scan_date)
        if not bars or bars[-1].get("date") != scan_date:
            continue
        if not evaluate_symbol(bars, sym, dsc.BASE_GATE_CFG)["tradeable"]:
            continue
        av = dsc._avg_vol_30d(bars)
        if av is None or av < dsc.MIN_AVG_VOL_30D:
            continue
        m = dsc._momentum_63d(bars)
        if m is not None:
            mom_pop.append(m)
        a = dm.adr20(bars)
        if a is not None:
            adr_pop.append(a)
    return mom_pop, adr_pop


pop_cache = {}


def diagnose(sym, entry_date):
    scan_date = latest_price_date(conn, entry_date)
    print(f"\n== {sym} @ {entry_date} (price date {scan_date}) ==")
    asm = dsc._asm_symbols(conn, scan_date)
    if sym in asm:
        print("  FAIL base: ASM-flagged")
        return
    bars = dsc._load_bars(conn, sym, scan_date)
    if not bars or bars[-1].get("date") != scan_date:
        print(f"  FAIL base: no bar on {scan_date} (last bar {bars[-1].get('date') if bars else None})")
        return
    v = evaluate_symbol(bars, sym, dsc.BASE_GATE_CFG)
    if not v["tradeable"]:
        print(f"  FAIL base eligibility: {v['reasons_failed']}")
        return
    av = dsc._avg_vol_30d(bars)
    if av is None or av < dsc.MIN_AVG_VOL_30D:
        print(f"  FAIL base: 30d avg vol {av:.0f} < 2 lakh")
        return
    print(f"  base eligibility: PASS (price {bars[-1]['close']}, avg_vol_30d {av:,.0f})")

    if scan_date not in pop_cache:
        pop_cache[scan_date] = _pctile_pop(scan_date)
    mom_pop, adr_pop = pop_cache[scan_date]

    pct65 = dm.pct_up_from_65d_low(bars)
    mom = dsc._momentum_63d(bars)
    momp = dsc._pctile_rank(mom, mom_pop)
    bf = (pct65 is not None and pct65 >= dsc.BUYING_FORCE_PCT_UP_65D_LOW) or \
         (momp is not None and momp >= 100.0 - dsc.TOP_PCTILE_CUTOFF)
    print(f"  buying force: {'PASS' if bf else 'FAIL'} "
          f"(pct_up_65d_low={pct65:.1f}% [need >=30], mom63={mom if mom is None else round(mom,1)}%, "
          f"mom_pctile={momp if momp is None else round(momp,1)} [need >=60])")
    if not bf:
        return

    dots = dm.purple_dot_count_60d(bars)
    adr = dm.adr20(bars)
    adrp = dsc._pctile_rank(adr, adr_pop)
    vel = dots >= dsc.PURPLE_DOT_MIN or (adrp is not None and adrp >= 100.0 - dsc.TOP_PCTILE_CUTOFF)
    print(f"  velocity: {'PASS' if vel else 'FAIL'} "
          f"(purple_dots_60d={dots} [need >=1], adr20={adr:.2f}%, adr_pctile={adrp:.1f} [need >=60])")
    if not vel:
        return

    depth = dm.correction_depth_from_leg_high(bars)
    tight = dm.prev_day_tightness_pctile(bars)
    rc = dm.range_contraction_flag(bars)
    pers = dm.persistency_counts(bars)
    up = mom is not None and mom > 0
    ssr = tight is not None and tight <= dsc.TIGHTNESS_BOTTOM_PCTILE and up
    pb = dsc._pullback_to_rising_ma(bars, depth)
    rev = dsc._reversal_archetype(bars)
    d2 = dsc._d2_episodic(bars)
    listing = eod_detectors.listing_status(conn, sym, scan_date)
    ipo = bool(eod_detectors.ipo_base(bars, listing))
    pm = dm.is_persistent_momentum(pers)
    print(f"  archetypes: strong_start_ready={ssr} (tightness_pctile={None if tight is None else round(tight,1)} "
          f"[need <=25], uptrend={up}); pullback_to_rising_ma={pb} (depth={None if depth is None else round(depth,1)}%); "
          f"vcp_coil={rc}; reversal={rev}; d2_episodic={d2}; ep_ipo={ipo} "
          f"(is_ipo={listing.get('is_ipo')}, status={listing.get('listing_status')}); "
          f"persistent_momentum={pm} (counts={pers})")
    if not any([ssr, pb, rc, rev, d2, ipo, pm]):
        print("  FAIL: passed base+force+velocity but NO archetype fired")
    else:
        print("  => WOULD BE IN BUCKET on this date")


for sym, ed in PICKS:
    # entry day AND day-before (bucket recall counts either)
    diagnose(sym, ed)
    diagnose(sym, day_before(ed))

conn.close()
