"""K1: build manas_os/data/labels/practitioner_picks.csv (scratch, run once)."""
import csv, sqlite3

DB = "manas_os/data/manas.db"

rows = [
    # symbol, entry_date, archetype, source_cite, note
    ("GESHIP", "", "reversal_pullback", "CHARTGYM Week12 GESHIP (Dec22-Jan23)", "no specific day in source; only month range"),
    ("NAVINFLUOR", "", "reversal_pullback", "CHARTGYM Week11 NAVINFLOUR (Jul13-Aug14)", "no specific day; also predates daily_prices coverage entirely"),
    ("POCL", "", "reversal_pullback", "CHARTGYM Week10 POCL (Dec23-Nov24)", "no specific day in source"),
    ("BSOFT", "", "reversal_pullback", "CHARTGYM BSOFT (Mar20-Nov20 pandemic chart)", "no specific day; predates daily_prices coverage entirely"),
    ("JAYNEECOIND", "", "momentum_hold", "CHARTGYM JAYNEECOIND (up 29% in few days)", "symbol not found in daily_prices/screener_hits under any spelling tried"),

    ("BSOFT", "2025-06-12", "strong_start", "Tightness Study: Birlasoft 12-Jun", ""),
    ("CHENNPETRO", "2025-10-17", "strong_start", "Tightness Study: Chennai Petroleum 17-Oct", "ticker flagged [FLAG] in source, ASR-garbled"),
    ("COALINDIA", "2025-10-10", "strong_start", "Tightness Study: Coal India 10-Oct", "ticker flagged [FLAG] in source, ASR-garbled"),
    ("EMSLIMITED", "2025-11-06", "strong_start", "Tightness Study: EMS 6-Nov", ""),
    ("INTELLECT", "2025-08-21", "strong_start", "Tightness Study: Intellect 21-Aug", ""),

    ("PARAGMILK", "2026-06-16", "strong_start", "6 Manas Entry: Parag Milk bought 16-Jun", ""),
    ("TATAINVEST", "2026-06-05", "strong_start", "6 Manas Entry: Tata Invest bought 5-Jun", ""),
    ("BSOFT", "2026-06-12", "reversal", "6 Manas Entry: BSOFT bought 12-Jun (reversal setup, 5 red days)", ""),
    ("NCC", "2026-03-10", "busted_reversal", "6 Manas Entry: NCC added 10-Mar (smaller-frame busted entry)", "initial position started 6-Mar per text; 10-Mar is the described execution day"),
    ("ZENTEC", "2026-02-24", "busted_reversal", "6 Manas Entry: Zentec pullback add 24-Feb", ""),
    ("ZENTEC", "2026-03-13", "busted_reversal", "6 Manas Entry: Zentec pullback add 13-Mar", ""),
    ("ZENTEC", "2026-03-16", "busted_reversal", "6 Manas Entry: Zentec pullback add 16-Mar", ""),

    ("GROWW", "2026-07-09", "ipo_velocity", "live refusal case (GROWW autopsy, Part B)", "recently-listed fast mover; ran the next day"),
]

conn = sqlite3.connect(DB)

out = []
for symbol, entry_date, archetype, source_cite, note in rows:
    mappable = False
    reason = note
    if not entry_date:
        reason = reason or "no specific day identifiable from source"
    else:
        hit = conn.execute(
            "select 1 from daily_prices where symbol=? and trade_date=?", (symbol, entry_date)
        ).fetchone()
        if hit:
            mappable = True
        else:
            has_symbol = conn.execute(
                "select 1 from daily_prices where symbol=? limit 1", (symbol,)
            ).fetchone()
            if not has_symbol:
                reason = (reason + "; " if reason else "") + "symbol not present in daily_prices at all"
            else:
                minmax = conn.execute(
                    "select min(trade_date), max(trade_date) from daily_prices where symbol=?", (symbol,)
                ).fetchone()
                reason = (reason + "; " if reason else "") + f"date not in daily_prices for this symbol (coverage {minmax[0]}..{minmax[1]})"
    out.append({
        "symbol": symbol,
        "entry_date": entry_date,
        "archetype": archetype,
        "source_cite": source_cite,
        "mappable": mappable,
        "unmapped_reason": "" if mappable else reason,
    })

with open("manas_os/data/labels/practitioner_picks.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["symbol", "entry_date", "archetype", "source_cite", "mappable", "unmapped_reason"])
    w.writeheader()
    w.writerows(out)

total = len(out)
mappable_n = sum(1 for r in out if r["mappable"])
print(f"total={total} mappable={mappable_n} unmapped={total-mappable_n}")
for r in out:
    if not r["mappable"]:
        print(" UNMAPPED:", r["symbol"], r["entry_date"], "->", r["unmapped_reason"])
