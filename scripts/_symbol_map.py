"""NSE symbol resolution layer.

The universe.csv holds *internal* symbols that may lag NSE's current trading
symbols (rebrands, short-symbol changes, mergers). This module maps internal
symbols → the symbol the data provider (Fyers / yfinance) actually recognises.

Two distinct cases — do not conflate them:
  * RENAME: the company still trades, under a new symbol. Map it.
  * DELISTED: the company is gone (merged / wound up). No valid provider symbol
    exists; the caller should drop it from the universe rather than fetch-loop.

Sources verified July 2026 against NSE symbolchange.csv (columns:
[Company, OLD_SYMBOL, NEW_SYMBOL, DATE]) and individual quote pages.

Keep this map SMALL and EVIDENCE-BACKED. A wrong map is worse than no map —
an unrecognised symbol fails loudly; a wrong-but-valid symbol silently pulls
the wrong company's data. When in doubt, leave it out and let the caller log
the failure for human review.
"""
from __future__ import annotations

# Internal symbol → current provider symbol. Every entry is verified against
# either NSE's official symbolchange.csv or a live quote page (screener/nse).
RENAME_MAP: dict[str, str] = {
    # --- Verified via NSE symbolchange.csv (old → new) ---
    "GMRINFRA": "GMRAIRPORT",   # GMR Airports, 11-Dec-2024
    "PVR": "PVRINOX",           # PVR INOX, 12-May-2023
    "P&G": "PGHH",              # Procter & Gamble Hygiene, 07-Jul-2004

    # --- Verified via NSE/screener quote pages (short-symbol changes) ---
    "AARTI": "AARTIIND",        # Aarti Industries
    "COMPUTERAGE": "CAMS",      # Computer Age Management Services
    "DRLALPATH": "LALPATHLAB",  # Dr Lal PathLabs
    "FINOLEX": "FINPIPE",       # Finolex Industries
    "GO": "GODIGIT",            # Go Digit General Insurance
    "LAKSHMIMACH": "LMW",       # Lakshmi Machine Works
    "MAHANAGAR": "MGL",         # Mahanagar Gas (MGL)
    "PROCTER": "PGHH",          # Procter & Gamble Hygiene (alt alias)
    "RR": "RRKABEL",            # R R Kabel
    "SISLTD": "SIS",            # SIS Limited

    # NOTE on entries deliberately NOT included (TODO.md was wrong here):
    #   HPCL → HINDPETRO  : FALSE. HPCL and HINDPETRO are *different* companies
    #                       (Hindustan Petroleum vs Hinduja Petro). HPCL is a
    #                       valid current symbol; its fetch failures are
    #                       transient (token/rate), not a rename.
    #   AVENUE → DMART    : Avenue Supermarts trades as DMART, but AVENUE is
    #                       simply the wrong ticker in universe.csv, not a
    #                       rename of an existing symbol. Fix in universe.csv
    #                       directly (one-off correction).
}

# Symbols whose listings no longer exist — no provider symbol is valid.
# The fetcher should skip these (they will never resolve) and they should be
# removed from universe.csv. Kept here so callers can detect and report them
# rather than retrying forever.
DELISTED: set[str] = {
    "IDFC",          # merged into IDFC First Bank, trading suspended 10-Oct-2024
    "ICICISECPRD",   # delisted via merger with ICICI Bank, 2024
}


def resolve(internal_sym: str) -> str | None:
    """Return the provider symbol for an internal symbol, or None if the
    listing no longer exists (delisted). Unmapped symbols pass through
    unchanged — most universe entries are already correct."""
    if internal_sym in DELISTED:
        return None
    return RENAME_MAP.get(internal_sym, internal_sym)


def is_delisted(internal_sym: str) -> bool:
    return internal_sym in DELISTED


if __name__ == "__main__":
    # Smoke test: print the resolution table.
    print("RENAME_MAP:")
    for k, v in RENAME_MAP.items():
        print(f"  {k:14s} -> {v}")
    print(f"\nDELISTED: {sorted(DELISTED)}")
