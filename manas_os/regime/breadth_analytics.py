"""regime/breadth_analytics.py — pure Python breadth analytics over breadth_counts.

Implements all ratios, percentages, spreads, and Norman Fosback's High-Low Logic Index
matching the formulas in Market Breadth V2.0.xlsm.
"""
from __future__ import annotations

import sqlite3

def _fetch_rows(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Helper to query the DB safely, returning a list of Row objects.
    Catches sqlite3.OperationalError gracefully and returns [] (honest-empty rule).
    Sets the row_factory to sqlite3.Row cursor-locally to guarantee column-name access.
    """
    try:
        cur = conn.cursor()
        cur.row_factory = sqlite3.Row
        return cur.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        return []

def net_nh_nl(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Net (new-52wk-high% - new-52wk-low%) * 100, per REVERSE_ENGINEERING.md Market Map col I.
    
    Formula: NET NH-NL (pp) = (new_52wk_high/universe - new_52wk_low/universe) * 100
    
    One dict per trading day in the window: {"trade_date": str, "value": float}.
    Returns [] if breadth_counts is empty, missing, or has no rows with total_universe > 0.
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, new_52wk_high, new_52wk_low, total_universe
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        nh = r["new_52wk_high"]
        nl = r["new_52wk_low"]
        if nh is None or nl is None:
            continue
        val = (nh / univ - nl / univ) * 100.0
        res.append({"trade_date": r["trade_date"], "value": val})
    return res

def fosback_hl_logic_index(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Fosback Hi-Low Logic Index: 10-day SMA of daily min(new_52wk_high/total_universe, new_52wk_low/total_universe) * 100,
    per REVERSE_ENGINEERING.md Market Map col W (daily) and col X (SMA).
    
    Fosback's insight: when both new highs and new lows are elevated, the market is conflicted (panic/transition).
    Returns [] if fewer than 10 raw history rows are available at/before the date.
    """
    if days <= 0:
        return []
    limit = days + 9
    rows = _fetch_rows(conn, """
        SELECT trade_date, new_52wk_high, new_52wk_low, total_universe
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, limit))
    
    rows.reverse()
    valid_rows = []
    for r in rows:
        univ = r["total_universe"]
        if univ is not None and univ > 0:
            valid_rows.append(r)
            
    n = len(valid_rows)
    if n < 10:
        return []
        
    daily_vals = []
    for r in valid_rows:
        nh = r["new_52wk_high"] or 0
        nl = r["new_52wk_low"] or 0
        univ = r["total_universe"]
        val = min(nh / univ, nl / univ) * 100.0
        daily_vals.append(val)
        
    res = []
    for i in range(9, n):
        sma = sum(daily_vals[j] for j in range(i - 9, i + 1)) / 10.0
        res.append({"trade_date": valid_rows[i]["trade_date"], "value": sma})
    return res

def volatility_ratio(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """volatility_ratio = range_expansion / range_contraction,
    per REVERSE_ENGINEERING.md Breadth criteria dictionary and §2 formula map.
    
    Formula: VOLATILITY RATIO = range_expansion / range_contraction (universe cancels out)
    Skips days where range_contraction is 0 or NULL to avoid division by zero.
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, range_expansion, range_contraction, total_universe
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        exp = r["range_expansion"]
        cont = r["range_contraction"]
        if exp is None or cont is None or cont == 0:
            continue
        val = exp / cont
        res.append({"trade_date": r["trade_date"], "value": val})
    return res

def volume_ratio(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """volume_ratio = high_vol / low_vol,
    per REVERSE_ENGINEERING.md Breadth criteria dictionary and §2 formula map.
    
    Formula: VOLUME RATIO = high_vol / low_vol (universe cancels out)
    Skips days where low_vol is 0 or NULL.
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, high_vol, low_vol, total_universe
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        high = r["high_vol"]
        low = r["low_vol"]
        if high is None or low is None or low == 0:
            continue
        val = high / low
        res.append({"trade_date": r["trade_date"], "value": val})
    return res

def bo_bd_ratios(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Calculates breakouts/breakdowns ratios and sustainability spreads,
    per REVERSE_ENGINEERING.md Breadth criteria dictionary and §2 formula map.
    
    Individual sub-ratios are set to None if their denominator is 0.
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, total_universe, breakouts, breakdowns,
               breakout_sustained, breakout_failed,
               breakdown_sustained, breakdown_failed
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        bo = r["breakouts"]
        bd = r["breakdowns"]
        bo_s = r["breakout_sustained"]
        bo_f = r["breakout_failed"]
        bd_s = r["breakdown_sustained"]
        bd_f = r["breakdown_failed"]
        
        bo_val = bo or 0
        bd_val = bd or 0
        bo_s_val = bo_s or 0
        bo_f_val = bo_f or 0
        bd_s_val = bd_s or 0
        bd_f_val = bd_f or 0
        
        bo_bd = bo_val / bd_val if bd_val != 0 else None
        bo_sust = bo_s_val / bo_val if bo_val != 0 else None
        bo_failed = bo_f_val / bo_val if bo_val != 0 else None
        bo_sf = bo_s_val / bo_f_val if bo_f_val != 0 else None
        bd_sust = bd_s_val / bd_val if bd_val != 0 else None
        bd_failed = bd_f_val / bd_val if bd_val != 0 else None
        bd_sf = bd_s_val / bd_f_val if bd_f_val != 0 else None
        
        res.append({
            "trade_date": r["trade_date"],
            "bo_bd_ratio": bo_bd,
            "bo_sustained_ratio": bo_sust,
            "bo_failed_ratio": bo_failed,
            "bo_sf_ratio": bo_sf,
            "bd_sustained_ratio": bd_sust,
            "bd_failed_ratio": bd_failed,
            "bd_sf_ratio": bd_sf
        })
    return res

def close_pct_ratios(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Calculates close percentage ratios,
    per REVERSE_ENGINEERING.md Breadth criteria dictionary, §2 formula map, and §2b quirk 1.
    
    Exposes both up_close_pct (breakout-denominated) and up_close_pct_range_denom (expansion-denominated).
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, total_universe, up_4pct, down_4pct, breakouts, breakdowns,
               close_upper_half, close_lower_half, range_expansion
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        up_4 = r["up_4pct"]
        dn_4 = r["down_4pct"]
        bo = r["breakouts"]
        bd = r["breakdowns"]
        c_up = r["close_upper_half"]
        c_dn = r["close_lower_half"]
        r_exp = r["range_expansion"]
        
        up_4_val = up_4 or 0
        dn_4_val = dn_4 or 0
        bo_val = bo or 0
        bd_val = bd or 0
        c_up_val = c_up or 0
        c_dn_val = c_dn or 0
        r_exp_val = r_exp or 0
        
        up_close = up_4_val / bo_val if bo_val != 0 else None
        dn_close = dn_4_val / bd_val if bd_val != 0 else None
        up_close_range = c_up_val / r_exp_val if r_exp_val != 0 else None
        dn_close_range = c_dn_val / r_exp_val if r_exp_val != 0 else None
        
        res.append({
            "trade_date": r["trade_date"],
            "up_close_pct": up_close,
            "down_close_pct": dn_close,
            "up_close_pct_range_denom": up_close_range,
            "down_close_pct_range_denom": dn_close_range
        })
    return res

def distance_band_pct(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Calculates 52-week distance band percentages,
    per REVERSE_ENGINEERING.md Market Map col I-V and §2b quirk 5.
    
    Divide each band's count by total_universe directly (non-exclusive buckets).
    """
    if days <= 0:
        return []
    cols = [
        "from_52wh_15pct", "from_52wh_30pct", "from_52wh_50pct", "from_52wh_70pct", "from_52wh_70pct_plus",
        "from_52wl_15pct", "from_52wl_30pct", "from_52wl_50pct", "from_52wl_90pct", "from_52wl_150pct", "from_52wl_150pct_plus"
    ]
    query_cols = ", ".join(cols)
    rows = _fetch_rows(conn, f"""
        SELECT trade_date, total_universe, {query_cols}
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        day_dict = {"trade_date": r["trade_date"]}
        for col in cols:
            val = r[col]
            day_dict[col] = (val / univ * 100.0) if val is not None else None
        res.append(day_dict)
    return res

def net_hl_spreads(conn: sqlite3.Connection, on_or_before: str, days: int) -> list[dict]:
    """Calculates net 15% and 30% high-low spreads in percentage points,
    per REVERSE_ENGINEERING.md Market Map col J and col K and §2b quirk 2.
    """
    if days <= 0:
        return []
    rows = _fetch_rows(conn, """
        SELECT trade_date, total_universe,
               from_52wh_15pct, from_52wh_30pct,
               from_52wl_15pct, from_52wl_30pct
        FROM breadth_counts
        WHERE trade_date <= ?
        ORDER BY trade_date DESC
        LIMIT ?
    """, (on_or_before, days))
    
    rows.reverse()
    res = []
    for r in rows:
        univ = r["total_universe"]
        if univ is None or univ <= 0:
            continue
        wh15 = r["from_52wh_15pct"]
        wh30 = r["from_52wh_30pct"]
        wl15 = r["from_52wl_15pct"]
        wl30 = r["from_52wl_30pct"]
        
        if wh15 is None or wl15 is None:
            net_15 = None
        else:
            net_15 = (wh15 - wl15) / univ * 100.0
            
        if wh15 is None or wh30 is None or wl15 is None or wl30 is None:
            net_30 = None
        else:
            net_30 = ((wh15 + wh30) - (wl15 + wl30)) / univ * 100.0
            
        res.append({
            "trade_date": r["trade_date"],
            "net_15pct_hl": net_15,
            "net_30pct_hl": net_30
        })
    return res

def summary(conn: sqlite3.Connection, date: str) -> dict:
    """Returns a flattened summary of the latest indicators as of the closest trade_date <= date.
    
    Returns {} if no usable row exists at or before the given date.
    """
    rows = _fetch_rows(conn, """
        SELECT max(trade_date) as max_date
        FROM breadth_counts
        WHERE trade_date <= ?
          AND total_universe IS NOT NULL
          AND total_universe > 0
    """, (date,))
    
    if not rows or not rows[0]["max_date"]:
        return {}
        
    as_of = rows[0]["max_date"]
    summary_dict = {"as_of": as_of}
    
    # Net NH-NL
    fn1 = net_nh_nl(conn, as_of, 1)
    if fn1:
        summary_dict["net_nh_nl"] = fn1[0]["value"]
        
    # Fosback Index (requires 10 sessions of history)
    fn2 = fosback_hl_logic_index(conn, as_of, 1)
    if fn2:
        summary_dict["fosback_hl_logic_index"] = fn2[0]["value"]
        
    # Volatility Ratio
    fn3 = volatility_ratio(conn, as_of, 1)
    if fn3:
        summary_dict["volatility_ratio"] = fn3[0]["value"]
        
    # Volume Ratio
    fn4 = volume_ratio(conn, as_of, 1)
    if fn4:
        summary_dict["volume_ratio"] = fn4[0]["value"]
        
    # Close Pct Ratios
    fn6 = close_pct_ratios(conn, as_of, 1)
    if fn6:
        for k in ("up_close_pct", "down_close_pct", "up_close_pct_range_denom", "down_close_pct_range_denom"):
            summary_dict[k] = fn6[0][k]
            
    # Distance Band Percentages
    fn7 = distance_band_pct(conn, as_of, 1)
    if fn7:
        cols = [
            "from_52wh_15pct", "from_52wh_30pct", "from_52wh_50pct", "from_52wh_70pct", "from_52wh_70pct_plus",
            "from_52wl_15pct", "from_52wl_30pct", "from_52wl_50pct", "from_52wl_90pct", "from_52wl_150pct", "from_52wl_150pct_plus"
        ]
        for col in cols:
            summary_dict[col] = fn7[0][col]
            
    # Net HL Spreads
    fn8 = net_hl_spreads(conn, as_of, 1)
    if fn8:
        summary_dict["net_15pct_hl"] = fn8[0]["net_15pct_hl"]
        summary_dict["net_30pct_hl"] = fn8[0]["net_30pct_hl"]
        
    return summary_dict
