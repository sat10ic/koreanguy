"""Nexus themetracker industry taxonomy -> canonical sector key crosswalk.

Source: manas_os/data/nexus_industry_map.json — "nexus themetracker Domain
Vector, Copy TV Watchlist" (215 industries, 2,676 NSE tickers), captured
2026-07-26.

This is a HYPOTHESIS, not ground truth. It is a hand-classified mapping from
Nexus's raw industry labels onto the 24 canonical sector keys used by
manas_os.regime.sectors (SECTORS / INDUSTRY_TO_SECTOR), built by reading each
industry name plus a sample of its constituent tickers. Some calls (which
canonical key a mixed-bag "Other X" or "Diversified X" bucket belongs to,
whether two similarly-named industries are the same concept or genuinely
distinct) are judgment calls that could be wrong and need verification
against actual company business descriptions before being trusted for
position sizing, sector exposure limits, or any other risk decision. Treat
every entry here as "someone's best read of a label", not audited fact.

Layout:
    NEXUS_INDUSTRY_TO_SECTOR  -- canonical Nexus industry name -> sector key
    NEXUS_INDUSTRY_ALIASES    -- duplicate/near-duplicate Nexus name -> the
                                 canonical Nexus name it was merged into
                                 (look that canonical name up in
                                 NEXUS_INDUSTRY_TO_SECTOR for the sector)
    UNMAPPED                  -- Nexus industry name -> reason no canonical
                                 sector key honestly fits
    sector_for_nexus_industry -- single lookup helper resolving aliases

POWER VALUE CHAIN -> ENERGY (decided 2026-07-26, overriding the first draft).

The first draft of this file mapped the six power industries (Power
Generation, Power Generation & Distribution, Power Distribution, Power -
Transmission, Power Trading, Integrated Power Utilities -- ~34 tickers) to
UTILITIES, on the taxonomic argument that Nexus splits the power value chain
finely enough to make the UTILITIES-vs-ENERGY distinction meaningful again,
where ChartsMaze's coarser "Power"/"Energy" labels could not.

That argument is reasonable and it was rejected anyway, for an operational
reason: in sectors.py, ENERGY carries index "NIFTY ENERGY" while UTILITIES
carries index None. Sending the power complex to UTILITIES would strip those
~34 tickers of any benchmark index, so MARS and every other index-relative
signal would silently lose its comparison for the whole group. A cleaner
taxonomy that breaks the sector-vs-index comparison is a bad trade.

So the power chain maps to ENERGY here, matching
sectors.INDUSTRY_TO_SECTOR["Power Generation & Distribution"] = "ENERGY" and
the ENERGY entry's own chartsmaze aliases ["Power", "Energy"]. One concept,
one sector key, across both tables -- the project's one-writer rule.

Revisit only if UTILITIES is given a real benchmark index; at that point the
finer split becomes free and is probably right.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 5 spelling/pluralisation duplicate pairs (rule a) + additional semantic
# duplicates found by inspecting ticker overlap/composition (rule b).
# Each entry: smaller-count raw Nexus name -> larger-count canonical Nexus
# name that absorbed it. Look the canonical name up in
# NEXUS_INDUSTRY_TO_SECTOR for the sector.
# ---------------------------------------------------------------------------
NEXUS_INDUSTRY_ALIASES: dict[str, str] = {
    # --- rule (a): the 5 required spelling/pluralisation pairs ---
    "Specialty Chemicals Companies": "Speciality Chemical Companies",          # 29 -> 36
    "Aerospace & Defence Companies": "Aerospace & Defense Companies",          # 1  -> 25
    "Commodity Chemical Companies": "Commodity Chemicals Companies",          # 4  -> 19
    "Housing Finance Companies": "Housing Finance Company Companies",         # 4  -> 15
    "Petrochemical Companies": "Petrochemicals Companies",                    # 3  -> 11

    # --- rule (b): confirmed semantic duplicates from the task brief ---
    "Stock Broking Companies": "Stockbroking & Allied Companies",             # 12 -> 24
    "Paper Companies": "Paper & Paper Products Companies",                    # 4  -> 22
    "Paints/Varnish Companies": "Paints Companies",                           # 2  -> 10
    "Telecomm Equipment Companies": "Telecom -  Equipment & Accessories Companies",  # 1 -> 10
    "Cigarettes/Tobacco Companies": "Cigarettes & Tobacco Products Companies",  # 1 -> 4

    # --- rule (b): additional semantic duplicates found on inspection ---
    # "Advertising Companies" (1: ODIGMA) is a same-concept subset of the
    # broader ad-agency bucket; no reason to keep a 1-ticker splinter.
    "Advertising Companies": "Advertising & Media Agencies Companies",        # 1  -> 10
    # "Computer Hardware Companies" (1: PANACHE) vs "Computers Hardware &
    # Equipments Companies" (18) — same industry, Nexus just forked the label.
    "Computer Hardware Companies": "Computers Hardware & Equipments Companies",  # 1 -> 18
}

# ---------------------------------------------------------------------------
# Canonical Nexus industry name -> one of the 24 sector keys.
# Grouped by sector for readability; comments flag the less obvious calls.
# ---------------------------------------------------------------------------
NEXUS_INDUSTRY_TO_SECTOR: dict[str, str] = {
    # ---------------------------------------------------------------- AUTO
    "2/3 Wheelers Companies": "AUTO",
    "Auto Components & Equipments Companies": "AUTO",
    "Auto Dealer Companies": "AUTO",
    "Auto Tyres & Rubber Products Companies": "AUTO",
    "Commercial Vehicles Companies": "AUTO",
    "Cycles Companies": "AUTO",
    "Dealers-Commercial Vehicles, Tractors, Construction Vehicles Companies": "AUTO",
    "Passenger Cars & Utility Vehicles Companies": "AUTO",
    "Tractors Companies": "AUTO",
    "Trading - Auto components Companies": "AUTO",
    "Tyres & Rubber Products Companies": "AUTO",

    # ---------------------------------------------------------------- BANK
    # "Other Bank" = small finance banks (rule c: -> BANK, not PSU/PRIVATE).
    "Other Bank Companies": "BANK",

    # -------------------------------------------------- FINANCIAL_SERVICES
    "Asset Management Company Companies": "FINANCIAL_SERVICES",
    "Depositories, Clearing Houses and Other Intermediaries Companies": "FINANCIAL_SERVICES",
    "Exchange and Data Platform Companies": "FINANCIAL_SERVICES",
    "Financial Institution Companies": "FINANCIAL_SERVICES",
    "Financial Products Distributor Companies": "FINANCIAL_SERVICES",
    "Financial Technology (Fintech) Companies": "FINANCIAL_SERVICES",
    "General Insurance Companies": "FINANCIAL_SERVICES",
    "Holding Company Companies": "FINANCIAL_SERVICES",
    "Housing Finance Company Companies": "FINANCIAL_SERVICES",
    "Insurance Distributors Companies": "FINANCIAL_SERVICES",
    "Investment Company Companies": "FINANCIAL_SERVICES",
    "Life Insurance Companies": "FINANCIAL_SERVICES",
    "Microfinance Institutions Companies": "FINANCIAL_SERVICES",
    "Non Banking Financial Company (NBFC) Companies": "FINANCIAL_SERVICES",
    "Other Capital Market related Services Companies": "FINANCIAL_SERVICES",
    "Other Financial Services Companies": "FINANCIAL_SERVICES",
    "Ratings Companies": "FINANCIAL_SERVICES",
    "Stockbroking & Allied Companies": "FINANCIAL_SERVICES",

    # ---------------------------------------------------------------- FMCG
    "Animal Feed Companies": "FMCG",
    "Breweries & Distilleries Companies": "FMCG",
    "Cigarettes & Tobacco Products Companies": "FMCG",
    "Dairy Products Companies": "FMCG",
    "Diversified FMCG Companies": "FMCG",
    "Edible Oil Companies": "FMCG",
    "Food Processing Companies": "FMCG",
    "Household Products Companies": "FMCG",  # batteries/agarbatti/soaps: fast-moving household consumables, not durables
    "Meat Products including Poultry Companies": "FMCG",
    "Other Agricultural Products Companies": "FMCG",
    "Other Beverages Companies": "FMCG",
    "Other Food Products Companies": "FMCG",
    "Packaged Foods Companies": "FMCG",
    "Personal Care Companies": "FMCG",
    "Seafood Companies": "FMCG",
    "Sugar Companies": "FMCG",
    "Tea & Coffee Companies": "FMCG",

    # ------------------------------------------------------------------ IT
    "Business Process Outsourcing (BPO)/ Knowledge Process Outsourcing (KPO) Companies": "IT",
    "Computers - Software & Consulting Companies": "IT",
    "Computers Hardware & Equipments Companies": "IT",
    "Data Processing Services Companies": "IT",
    "IT Consulting & Software Companies": "IT",
    "IT Enabled Services Companies": "IT",
    "IT Software Products Companies": "IT",
    "Software Products Companies": "IT",

    # --------------------------------------------------------------- MEDIA
    "Advertising & Media Agencies Companies": "MEDIA",
    "Digital Entertainment Companies": "MEDIA",
    "Electronic Media Companies": "MEDIA",
    "Entertainment Companies": "MEDIA",
    "Film Production, Distribution & Exhibition Companies": "MEDIA",
    "Media & Entertainment Companies": "MEDIA",
    "Print Media Companies": "MEDIA",
    "Printing & Publication Companies": "MEDIA",  # book/newspaper publishers, not education-service providers
    "TV Broadcasting & Software Production Companies": "MEDIA",

    # -------------------------------------------------------------- METAL
    "Aluminium Companies": "METAL",
    "Aluminium, Copper & Zinc Products Companies": "METAL",
    "Castings & Forgings Companies": "METAL",
    "Copper Companies": "METAL",
    "Diversified Metals Companies": "METAL",
    # Graphite-electrode / refractory makers sell almost exclusively into
    # steel/foundry furnaces -> grouped with the metal value chain.
    "Electrodes & Refractories Companies": "METAL",
    "Ferro & Silica Manganese Companies": "METAL",
    "Industrial Minerals Companies": "METAL",  # mining/minerals, matches sectors.py "Mining/Minerals"
    "Iron & Steel Companies": "METAL",
    "Iron & Steel Products Companies": "METAL",
    "Pig Iron Companies": "METAL",
    "Sponge Iron Companies": "METAL",
    "Trading - Metals Companies": "METAL",
    "Trading - Minerals Companies": "METAL",  # taxonomy label says minerals trading even though ADANIENT is far more diversified in reality
    "Zinc Companies": "METAL",

    # -------------------------------------------------------------- PHARMA
    "Biotechnology Companies": "PHARMA",
    "Healthcare Research, Analytics & Technology Companies": "PHARMA",
    "Healthcare Service Provider Companies": "PHARMA",
    "Hospital Companies": "PHARMA",
    "Medical Equipment & Supplies Companies": "PHARMA",
    "Pharmaceuticals Companies": "PHARMA",

    # ------------------------------------------------------------- REALTY
    "Real Estate Companies": "REALTY",
    "Real Estate Investment Trusts (REITs) Companies": "REALTY",
    "Real Estate related services Companies": "REALTY",
    "Residential, Commercial Projects Companies": "REALTY",

    # ------------------------------------------------------------- ENERGY
    # Reserved for the broader renewable/alternative-energy value chain
    # (EPC, equipment, project development) -- NOT power generation itself,
    # which now goes to UTILITIES (see module docstring + rule d).
    "Renewable Energy Companies": "ENERGY",

    # ----------------------------------------------------- INFRASTRUCTURE
    "Airport & Airport services Companies": "INFRASTRUCTURE",
    "Cement & Cement Products Companies": "INFRASTRUCTURE",
    "Civil Construction Companies": "INFRASTRUCTURE",
    "Dredging Companies": "INFRASTRUCTURE",
    "Granites & Marbles Companies": "INFRASTRUCTURE",  # natural stone as a B2B construction material
    "Other Construction Materials Companies": "INFRASTRUCTURE",
    "Port & Port services Companies": "INFRASTRUCTURE",
    "Road AssetsToll, Annuity, Hybrid-Annuity Companies": "INFRASTRUCTURE",
    "Solar EPC": "INFRASTRUCTURE",  # engineering/construction of solar plants, not a manufacturer or a utility

    # -------------------------------------------------------- PSU_BANK / PRIVATE_BANK
    "Public Sector Bank Companies": "PSU_BANK",
    "Private Sector Bank Companies": "PRIVATE_BANK",

    # ---------------------------------------------------- CONSUMER_DURABLES
    "Ceramics Companies": "CONSUMER_DURABLES",  # tiles: home-building consumer durable, mirrors sectors.py "Glass"
    "Consumer Electronics Companies": "CONSUMER_DURABLES",
    "Diamond, Gems and Jewellery Companies": "CONSUMER_DURABLES",
    "Diversified consumer products Companies": "CONSUMER_DURABLES",
    "Footwear Companies": "CONSUMER_DURABLES",
    "Furniture, Home Furnishing Companies": "CONSUMER_DURABLES",
    "Gems, Jewellery And Watches Companies": "CONSUMER_DURABLES",
    "Glass - Consumer Companies": "CONSUMER_DURABLES",
    "Glass - Industrial Companies": "CONSUMER_DURABLES",
    "Household Appliances Companies": "CONSUMER_DURABLES",
    "Houseware Companies": "CONSUMER_DURABLES",
    "Leisure Products Companies": "CONSUMER_DURABLES",
    "Paints Companies": "CONSUMER_DURABLES",
    "Plastic Products - Consumer Companies": "CONSUMER_DURABLES",
    "Sanitary Ware Companies": "CONSUMER_DURABLES",
    "Stationary Companies": "CONSUMER_DURABLES",

    # -------------------------------------------------------------- OIL_GAS
    "Coal Companies": "OIL_GAS",  # fossil-fuel commodity, mirrors sectors.py "Coal Products"
    "Crude Oil & Natural Gas Companies": "OIL_GAS",
    "Gas Transmission/Marketing Companies": "OIL_GAS",
    "LPG/CNG/PNG/LNG Supplier Companies": "OIL_GAS",
    "Lubricants Companies": "OIL_GAS",
    "Offshore Support Solution Drilling Companies": "OIL_GAS",
    "Oil Equipment & Services Companies": "OIL_GAS",
    "Oil Exploration & Production Companies": "OIL_GAS",
    "Oil Storage & Transportation Companies": "OIL_GAS",
    "Petrochemicals Companies": "OIL_GAS",  # mirrors sectors.py "Petrochemicals" -> OIL_GAS, not CHEMICALS
    "Refineries & Marketing Companies": "OIL_GAS",
    "Trading - Coal Companies": "OIL_GAS",
    "Trading - Gas Companies": "OIL_GAS",

    # --------------------------------------------------------- CAPITAL_GOODS
    "Abrasives & Bearings Companies": "CAPITAL_GOODS",
    "Aerospace & Defense Companies": "CAPITAL_GOODS",
    "Cables - Electricals Companies": "CAPITAL_GOODS",
    "Compressors, Pumps & Diesel Engines Companies": "CAPITAL_GOODS",
    "Construction Vehicles Companies": "CAPITAL_GOODS",  # earthmoving/heavy-equipment mfg, not road-going AUTO
    "Electronic Manufacturing Services": "CAPITAL_GOODS",
    "Heavy Electrical Equipment Companies": "CAPITAL_GOODS",
    "Industrial Machinery Companies": "CAPITAL_GOODS",
    "Industrial Products Companies": "CAPITAL_GOODS",
    "Other Electrical Equipment Companies": "CAPITAL_GOODS",
    "Other Industrial Products Companies": "CAPITAL_GOODS",
    "Plastic Products - Industrial Companies": "CAPITAL_GOODS",
    "Plastic Products Companies": "CAPITAL_GOODS",
    "Railway Wagons Companies": "CAPITAL_GOODS",
    "Ship Building & Allied Services Companies": "CAPITAL_GOODS",

    # ------------------------------------------------------------ UTILITIES
    # Whole power value chain (generation/distribution/transmission/trading)
    # per rule (d): a power generator is UTILITIES, not ENERGY. See module
    # docstring for how this departs from the legacy ChartsMaze mapping.
    # Power chain -> ENERGY, not UTILITIES: UTILITIES has index None in
    # sectors.py, so routing these here keeps NIFTY ENERGY as their benchmark
    # and matches the existing INDUSTRY_TO_SECTOR entry. See module docstring.
    "Integrated Power Utilities Companies": "ENERGY",
    "Power - Transmission Companies": "ENERGY",
    "Power Distribution Companies": "ENERGY",
    "Power Generation & Distribution Companies": "ENERGY",
    "Power Generation Companies": "ENERGY",
    "Power Trading Companies": "ENERGY",
    "Water Supply & Management Companies": "UTILITIES",

    # -------------------------------------------------------------- SERVICES
    "Airline Companies": "SERVICES",
    "Consulting Services Companies": "SERVICES",
    "Diversified Commercial Services Companies": "SERVICES",
    "Engineering Services Companies": "SERVICES",
    "Logistics Companies": "SERVICES",
    "Logistics Solution Provider Companies": "SERVICES",
    "Shipping Companies": "SERVICES",
    "Transport Related Services Companies": "SERVICES",
    "Waste Management Companies": "SERVICES",

    # ------------------------------------------------------------ CHEMICALS
    "Carbon Black Companies": "CHEMICALS",
    "Commodity Chemicals Companies": "CHEMICALS",
    "Dyes And Pigments Companies": "CHEMICALS",
    "Explosives Companies": "CHEMICALS",
    "Fertilizers Companies": "CHEMICALS",
    "Industrial Gases Companies": "CHEMICALS",
    "Pesticides & Agrochemicals Companies": "CHEMICALS",
    "Printing Inks Companies": "CHEMICALS",
    # Synthetic rubber/latex/rubber-thread processing (chemical manufacture),
    # not auto-specific parts -- Nexus already splits auto rubber out into
    # its own "Auto Tyres & Rubber Products" / "Tyres & Rubber Products".
    "Rubber Companies": "CHEMICALS",
    "Speciality Chemical Companies": "CHEMICALS",
    "Trading - Chemicals Companies": "CHEMICALS",

    # ------------------------------------------------------------ TEXTILES
    "Garments & Apparels Companies": "TEXTILES",
    "Jute & Jute Products Companies": "TEXTILES",
    "Leather And Leather Products Companies": "TEXTILES",  # no dedicated leather key; closest specific fit
    "Other Textile Products Companies": "TEXTILES",
    "Readymade Garments/ Apparels Companies": "TEXTILES",
    "Textiles Companies": "TEXTILES",
    "Trading - Textile Products Companies": "TEXTILES",

    # ----------------------------------------------------- CONSUMER_SERVICES
    "Amusement Parks/ Other Recreation Companies": "CONSUMER_SERVICES",
    "Diversified Retail Companies": "CONSUMER_SERVICES",
    "E-Learning Companies": "CONSUMER_SERVICES",
    "E-Retail/ E-Commerce Companies": "CONSUMER_SERVICES",
    "Education Companies": "CONSUMER_SERVICES",
    "Hotels & Resorts Companies": "CONSUMER_SERVICES",
    "Internet & Catalogue Retail Companies": "CONSUMER_SERVICES",  # consumer-facing marketplaces/classifieds, not software product cos
    "Other Consumer Services Companies": "CONSUMER_SERVICES",
    "Pharmacy Retail Companies": "CONSUMER_SERVICES",  # retail chain format, not drug manufacturing
    "Restaurants Companies": "CONSUMER_SERVICES",
    "Road Transport Companies": "CONSUMER_SERVICES",  # cab/personal-mobility services, not freight logistics
    "Speciality Retail Companies": "CONSUMER_SERVICES",
    "Tour, Travel Related Services Companies": "CONSUMER_SERVICES",
    "Wellness Companies": "CONSUMER_SERVICES",

    # -------------------------------------------------------------- TELECOM
    "Other Telecom Services Companies": "TELECOM",
    "Telecom -  Equipment & Accessories Companies": "TELECOM",  # note: double space is the literal Nexus key
    "Telecom - Cellular & Fixed line services Companies": "TELECOM",
    "Telecom - Infrastructure Companies": "TELECOM",

    # ---------------------------------------------------------- DIVERSIFIED
    "Diversified Companies": "DIVERSIFIED",

    # ------------------------------------------------------ FOREST_MATERIALS
    "Packaging Companies": "FOREST_MATERIALS",  # mirrors sectors.py "Packaging" -> FOREST_MATERIALS (house precedent), despite many constituents being plastic-based
    "Paper & Paper Products Companies": "FOREST_MATERIALS",
    "Plywood Boards/ Laminates Companies": "FOREST_MATERIALS",  # mirrors sectors.py "Wood Products"
}

# ---------------------------------------------------------------------------
# Nexus industries with no honest home among the 24 canonical keys.
# ---------------------------------------------------------------------------
UNMAPPED: dict[str, str] = {
    "Trading & Distributors Companies": (
        "Heterogeneous general trading/distribution bucket (govt bulk "
        "traders MMTC/STCINDIA, IT-hardware distributor REDINGTON, agro "
        "and chemical trading firms) with no coherent single-sector "
        "identity -- the category is diverse, not any one constituent "
        "company; forcing it into DIVERSIFIED or SERVICES would misstate "
        "what DIVERSIFIED means elsewhere in this crosswalk (a company "
        "whose OWN operations span sectors, not a grab-bag category)."
    ),
    "Web based media and service Companies": (
        "Only 2 tickers and they point two different ways: ONMOBILE is "
        "telecom content/media distribution (mobile VAS, ringback tones), "
        "PELATRO is B2B loyalty/engagement software -- no single sector "
        "honestly covers both, and the sample is too small to pick a "
        "majority shape."
    ),
}


def sector_for_nexus_industry(name: str) -> str | None:
    """Canonical sector key for a raw Nexus industry name, or None.

    Resolves aliases first, then looks up the canonical name. Returns None
    for anything in UNMAPPED or not present in the source map at all --
    callers should treat None as "needs a decision", not "safe to drop
    silently".
    """
    if not name:
        return None
    canonical = NEXUS_INDUSTRY_ALIASES.get(name, name)
    return NEXUS_INDUSTRY_TO_SECTOR.get(canonical)
