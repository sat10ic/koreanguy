"""K6 diagnosis (K-iteration refresh, mirrors scanner/discovery.py's CURRENT
per-archetype eligibility as of K4.1): for each label pick, report exactly
which condition failed, with measured values. Read-only vs the resumable
scratch DB. Unlike the pre-K4.1 version, buying-force ("bf") is NOT a hard
early-return -- the LEG-FORCE family (reversal / pullback-to-rising-MA) does
not require current force, matching build_bucket's actual branching.
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
    ("PARAGMILK", "2026-06-05"),
    ("NBIFIN", "2026-01-01"),  # control: expect stays out on ALL dates
]


def day_before(d):
    y, m, dd = map(int, d.split("-"))
    return (date(y, m, dd) - timedelta(days=1)).isoformat()


def _pctile_pop(scan_date):
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
        at = dsc._avg_turnover_cr_30d(bars)
        vol_ok = (av is not None and av >= dsc.MIN_AVG_VOL_30D) or \
                 (at is not None and at >= dsc.MIN_AVG_TURNOVER_CR_30D_ALT)
        if not vol_ok:
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
    at = dsc._avg_turnover_cr_30d(bars)
    vol_ok = (av is not None and av >= dsc.MIN_AVG_VOL_30D) or \
             (at is not None and at >= dsc.MIN_AVG_TURNOVER_CR_30D_ALT)
    if not vol_ok:
        print(f"  FAIL base: 30d avg_vol {av} < 2L AND 30d avg_turnover_cr {at} < 3cr")
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
    print(f"  current buying force: {'PASS' if bf else 'FAIL'} "
          f"(pct_up_65d_low={None if pct65 is None else round(pct65,1)}% [need >=30], "
          f"mom63={mom if mom is None else round(mom,1)}%, "
          f"mom_pctile={momp if momp is None else round(momp,1)} [need >=60])")

    dots = dm.purple_dot_count_60d(bars)
    adr = dm.adr20(bars)
    adrp = dsc._pctile_rank(adr, adr_pop)
    vel = dots >= dsc.PURPLE_DOT_MIN or (adrp is not None and adrp >= 100.0 - dsc.TOP_PCTILE_CUTOFF)
    print(f"  velocity (HARD gate): {'PASS' if vel else 'FAIL'} "
          f"(purple_dots_60d={dots} [need >=1], adr20={None if adr is None else round(adr,2)}%, "
          f"adr_pctile={None if adrp is None else round(adrp,1)} [need >=60])")
    if not vel:
        print("  => OUT: velocity hard-gate failed (kills every archetype)")
        return

    leg_force = dm.leg_force_from_65d_low(bars)
    depth = dm.correction_depth_from_leg_high(bars)
    leg_force_ok = leg_force is not None and leg_force >= dsc.BUYING_FORCE_PCT_UP_65D_LOW
    correction_ok = depth is not None and depth <= dsc.CORRECTION_DEPTH_MAX
    listing = eod_detectors.listing_status(conn, sym, scan_date)
    days_listed = listing.get("days_since_listing")
    recent_listing = days_listed is not None and days_listed <= dsc.RECENT_LISTING_MAX_DAYS
    force_waived = recent_listing

    tight = dm.prev_day_tightness_pctile(bars)
    rc = dm.range_contraction_flag(bars)
    pers = dm.persistency_counts(bars)
    # K7: uptrend accepts a longer-frame EMA200 persistency run too
    up = (mom is not None and mom > 0) or ((pers.get("ema200") or 0) > 0)
    pm = dm.is_persistent_momentum(pers)

    # momentum value at today's top-40pctile cutoff (reversal alt branch)
    mom_top40 = None
    if mom_pop:
        s = sorted(mom_pop)
        idx = min(len(s) - 1, int(round((100.0 - dsc.TOP_PCTILE_CUTOFF) / 100.0 * (len(s) - 1))))
        mom_top40 = s[idx]

    ssr = d2 = ipo = False
    if bf or force_waived:
        ssr = tight is not None and tight <= dsc.TIGHTNESS_BOTTOM_PCTILE and up
        d2 = dsc._d2_episodic(bars)
        ipo = bool(eod_detectors.ipo_base(bars, listing))

    rev_prior = dsc._reversal_prior_strength(bars, mom_top40)
    depth180 = dm.correction_depth_from_180d_high(bars)
    band180_ok = depth180 is not None and depth180 <= dsc.REVERSAL_CORRECTION_MAX
    pb2 = False
    if leg_force_ok and correction_ok:
        pb2 = dsc._pullback_to_rising_ma(bars, depth)
    elif rev_prior and band180_ok:
        pb2 = dsc._pullback_to_rising_ma(bars, depth180, max_depth=dsc.REVERSAL_CORRECTION_MAX)
    rev = dsc._reversal_archetype(bars, mom_top40)

    print(f"  prior-strength family gates: leg_force_ok={leg_force_ok} (leg_force_from_65d_low="
          f"{None if leg_force is None else round(leg_force,1)}% [need >=30]), correction_ok={correction_ok} "
          f"(correction_depth_from_leg_high={None if depth is None else round(depth,1)}% [need <=30]); "
          f"rev_prior_180d={rev_prior}, depth_180d={None if depth180 is None else round(depth180,1)}% "
          f"(band<=40 ok={band180_ok}); trigger={dsc._reversal_trigger(bars)}")
    print(f"  archetypes: strong_start_ready={ssr} (tightness_pctile="
          f"{None if tight is None else round(tight,1)} [need <=25], uptrend={up}, gated_by_bf_or_waiver={bf or force_waived}); "
          f"pullback_to_rising_ma={pb2}; vcp_coil={rc if (bf or force_waived) else 'N/A(no current-force)'}; "
          f"reversal={rev}; d2_episodic={d2}; ep_ipo={ipo} (is_ipo={listing.get('is_ipo')}); "
          f"persistent_momentum={pm if (bf or force_waived) else 'N/A(no current-force)'} (counts={pers})")
    if not any([ssr, pb2, (rc if (bf or force_waived) else False), rev, d2, ipo,
                (pm if (bf or force_waived) else False)]):
        print("  FAIL: passed base+velocity but NO archetype fired")
    else:
        print("  => WOULD BE IN BUCKET on this date")


for sym, ed in PICKS:
    diagnose(sym, ed)
    diagnose(sym, day_before(ed))

conn.close()
