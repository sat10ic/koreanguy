"""derive/insight_tables.py -- materialises the three classifier-shaped insight
tables from the classified corpus: ``themes``, ``breadth_notes``, ``edu_items``.

## Design premise (why this module exists)
INS-3 (Theme rotation) and INS-9 (Market chorus) both depend on tables that the
classifier cascade never materialised: as of the first production run of this
module, ``themes``, ``breadth_notes``, ``edu_items`` (and ``edu_links``) hold
zero rows while ``post_class`` already carries 290 ``theme``, 284 ``breadth``
and 553 ``education`` rows (read-only probe, 2026-08-25). CONTRACTS.md keeps
naming ``llm/classify.py`` as the writer of these three tables, but classify.py
only ever wrote ``post_class`` -- this module is the repair, in the same
spirit as the earlier watchlists/radar materialisation (per CANONICAL.md SS6
ownership, the maintainer should repoint that row at this module).

This module is PURE SQL + Python over existing tables. No LLM calls, $0 cost.
Every written row is derived only from text and values literally present in the
corpus -- nothing is invented, guessed, or fuzzy-matched. Per the house rule
"NULL over guess, always", an unstated stance is NULL and an unstated theme is
left unwritten.

## Tables and sources (one writer function each, idempotent upserts)
  1. breadth_notes -- ONE row per post classified ``kind == 'breadth'``.
     Verified column set (db/schema.sql): post_id (PK), handle, trade_date
     (NOT NULL), stance (nullable), claims_json, symbols, confidence,
     is_mock, ingested_at. There is NO text/excerpt column, so the verbatim
     comment is stored as the elements of ``claims_json`` (the schema's
     "JSON array of discrete claims made"): the post's text is split on
     sentence punctuation into verbatim spans (decimal points do not split --
     the split requires punctuation followed by whitespace). The full text
     stays available via ``posts.text``; the feed endpoint already joins it.
     ``stance`` is risk_on | risk_off | neutral -- the schema's vocabulary
     (the API maps risk_on->GREEN, risk_off->RED, neutral->WHITE) -- and is
     set ONLY from a fixed, auditable keyword list of explicit stance words
     (see STANCE_RISK_ON_WORDS / STANCE_RISK_OFF_WORDS / STANCE_NEUTRAL_WORDS,
     all of which appear verbatim in the corpus, e.g. "bullish", "staying
     light", "sideways"). When the text states both a risk-on and a risk-off
     word, or states none at all, stance is NULL -- never guessed, never
     resolved in favour of one side. ``symbols`` is the JSON array of
     NSE-validated symbols literally named in the post (post_class.symbols
     UNION #hashtags, validated against ``SELECT DISTINCT symbol FROM
     daily_prices``, dropped-not-invented exactly like watchlists.py).
     ``confidence`` inherits the classifier's post_class.confidence (it
     certifies the row IS a breadth note; the keyword stance makes no
     separate confidence claim).

  2. edu_items -- ONE row per post classified ``kind == 'education'``.
     Column set: id, post_id, handle, title, principle_text (NOT NULL),
     topic_tags, stated_at (NOT NULL), confidence, is_mock, ingested_at.
     ``principle_text`` is the post's own text, verbatim (the schema comment
     says to quote where possible: paraphrase drift would corrupt the
     practice-vs-preach scoring). ``title`` is derived from the first
     sentence of the text -- a verbatim substring, truncated at
     TITLE_MAX_CHARS, never a paraphrase (the schema does not require a
     title; the first-sentence rule keeps it honest and cheap). ``topic_tags``
     is a JSON array drawn from a small fixed vocabulary (stops, sizing,
     entries, risk, discipline, process) where a tag is emitted ONLY when at
     least one of its LITERAL trigger strings appears in the text (see
     TOPIC_TAG_TRIGGERS; every trigger is a real corpus phrase, e.g. "stop
     loss", "position size", "busted entry"). No tag is ever inferred from
     tone.

  3. themes -- distinct market themes/sectors discussed by the traders.
     Verified column set: id, name (NOT NULL UNIQUE), symbols_json,
     first_seen, last_seen, mention_count, is_mock, ingested_at. There is no
     post_id column and no trader-count column, so:
       * name        -- the canonical display label (THEME_LABELS keys).
       * mention_count -- the number of DISTINCT TRADERS citing the theme.
                        The product requirement (INS-3) is "count distinct
                        traders per theme"; the schema has exactly one count
                        column, and the INS-3 acceptance ("a single prolific
                        trader cannot masquerade as breadth") requires the
                        anti-masquerade metric. The raw citing-POST count is
                        reported per theme in the run stats.
       * first_seen / last_seen -- min/max calendar date (ts_ist prefix)
                        across citing posts.
       * symbols_json -- NSE-validated symbols named in citing posts.
       * is_mock -- 1 if ANY citing post is mock, else 0 (conservative).
     Source: posts classified ``kind == 'theme'`` PLUS posts classified
     ``kind == 'breadth'`` whose text literally names a theme phrase -- a
     breadth post never invents a theme, it only adds a mention to a phrase
     that already exists in THEME_LABELS.

## Theme label extraction -- the no-invention rule
A theme exists ONLY if the post text literally contains one of the audited
literal phrases in THEME_LABELS below. Every phrase was copied verbatim from
the real corpus (or given verbatim in the wave brief) and is listed with its
canonical display label -- the same auditable-hand-written-map discipline
watchlists.py uses for SYMBOL_ALIASES. This is NOT a fuzzy matcher: a post
whose text matches no phrase produces NO theme row and is counted as
skipped/no_extractable_theme (coverage debt, reported honestly).

Normalisation rule (documented, conservative):
  * Matching is case-insensitive on the raw post text.
  * Multi-word phrases match as plain substrings; single-word phrases require
    word boundaries (so "gold" never matches "golden" and "silver" never
    matches "#SilverETF").
  * A post contributes at most ONE theme. The longest matched phrase wins
    (so "Gold and Silver" beats bare "Silver" in a post discussing both);
    ties resolve to the phrase listed first in THEME_LABELS.
  * Keeping the brief's own instruction: posts discussing the SAME theme under
    different wording produce CONSERVATIVELY SEPARATE labels unless the
    different wordings are explicitly listed as the same theme in THEME_LABELS
    (e.g. "wire & cable" and "wire and cable" are deliberate aliases of
    "Wire and Cable"; "&" is a stylised "and", which is why those aliases
    exist -- they are auditable table entries, NOT automatic normalisation).
  * A theme row's ``name`` is the canonical label from THEME_LABELS (all
    matches for the same theme share the key), and the label is stable across
    runs.

## Idempotency
breadth_notes and themes upsert ON CONFLICT on their natural keys
(post_id / name) and then delete rows outside the current source set, so a
re-run against an unchanged corpus produces identical rows and a reclassified
post's stale row disappears -- all inside one transaction (a failure rolls
back to the prior state). edu_items has NO unique constraint on post_id in the
schema (ON CONFLICT post_id is impossible), so its rows are refreshed in place
by an UPDATE-if-exists else INSERT loop in the same transaction. edu_items rows
are never deleted: ``edu_links`` (written by derive/preach.py) references
``edu_items.id``, so deleting would break the FK; a re-run updates the same
row, keeping edu_links valid.

Public contract (matches adopted/bhavcopy.py's ingestor shape):
    run(conn, run_date) -> int   # rows written across the three tables;
                                  # always logs pipeline_runs; never partially
                                  # commits
"""
from __future__ import annotations

import json
import re
import time
from datetime import date

from traderlog.db import now_iso

STAGE = "derive.insight_tables"

# ---------------------------------------------------------------------------
# Tunables -- named + commented so every threshold is auditable, not magic.
# ---------------------------------------------------------------------------

# Title derivation for edu_items: title = first sentence, truncated to this
# many characters with "..." appended when truncated. A verbatim substring of
# the post text, never a paraphrase.
TITLE_MAX_CHARS = 100

# The three breadth_notes stance vocabularies. Every word/phrase below appears
# verbatim in the production corpus (checked by direct inspection on
# 2026-08-25). Exact-match only, and the row is written with NULL stance when
# NONE of the buckets matches or when MORE THAN ONE bucket matches (a text
# stating both "bullish" and "staying light" is contradictory evidence: NULL
# over guess, always). Note the schema vocabulary is risk_on/risk_off/neutral
# (the API maps risk_on->GREEN, risk_off->RED, neutral->WHITE in /api/breadth);
# "bullish"/"bearish" from the brief map onto risk_on/risk_off.
STANCE_RISK_ON_WORDS = frozenset({
    "bullish", "bulls", "risk on", "risk-on", "long bias", "stay long",
    "staying long", "strong tape", "adding on strength", "add on strength",
    "buy the dip", "buying dips",
})
STANCE_RISK_OFF_WORDS = frozenset({
    "bearish", "bears", "risk off", "risk-off", "staying light", "stay light",
    "keep it light", "reduce exposure", "reducing exposure", "reduced exposure",
    "trimming", "cut exposure", "protect capital", "protecting capital",
    "capital protection", "defensive", "downtrend", "very strong selloff",
    "weak market", "market tone is weak", "bloodbath", "crash", "crashed",
    "selloff",
})
STANCE_NEUTRAL_WORDS = frozenset({
    "neutral", "neutralize", "neutralized", "sideways", "choppy",
    "choppiness", "rangebound", "ranging", "mixed tape", "doing nothing",
    "not clear", "no clear", "stabilize", "stabilizing", "stabilise",
    "consolidation", "consolidating", "pullback", "base formation",
})

# A single fixed stance value can belong to at most one bucket (checked in a
# unit test); the buckets above are disjoint by construction.
STANCE_RISK_ON = "risk_on"
STANCE_RISK_OFF = "risk_off"
STANCE_NEUTRAL = "neutral"
STANCE_NULL = None

# edu_items topic vocabulary. A tag is emitted ONLY when at least one of its
# literal trigger strings appears in the lowercased post text. Triggers are
# real corpus phrases (verified 2026-08-25), e.g. "stop loss" ("Your trade
# hits stop"), "position size", "busted entry", "protect capital", "patience
# matters", "building a process". Single-word triggers are matched with word
# boundaries; multi-word triggers as plain substrings. Tags are never inferred
# from tone and no tag outside this vocabulary is ever produced.
TOPIC_TAG_TRIGGERS: dict[str, tuple[str, ...]] = {
    "stops": ("stop loss", "stop-loss", "stop losses", "stops", "stop out",
              "stop hit", "tapped out", "at stop", "sl "),
    "sizing": ("position size", "position sizing", "sizing", "quarter size",
               "half size", "full size", "keep them small", "size"),
    "entries": ("entry point", "entry points", "entry method", "busted entry",
                "reentry", "entries", "entry"),
    "risk": ("risk", "risky", "protect capital", "protect your capital",
             "stay light", "capital preservation", "risk management"),
    "discipline": ("discipline", "patience", "sit-out", "sit out",
                   "never blame the market", "wrong expectations"),
    "process": ("process", "checklist", "pre-trade checklist", "routine",
                "system"),
}

# claims_json sentence split: punctuation followed by whitespace. Trailing
# decimal points ("94.82") do not split because there the '.' is followed by a
# digit, not whitespace.
_CLAIM_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# list-marker segments like "1." or "1)" produced by splitting numbered lists
# are not claims; drop them verbatim-safely.
_LIST_MARKER_RE = re.compile(r"^\d+[.)]?$")

# Same conservative ticker shape llm/classify.py and watchlists.py validate
# symbols against (duplicated here to keep the module self-contained).
_HASHTAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9]{0,29})")


def _boundary_re(word: str) -> re.Pattern:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])"
    )


# ---------------------------------------------------------------------------
# THEME_LABELS -- the audited canonical theme table.
#
# canonical display name -> literal phrases that map to it. Every phrase below
# was copied verbatim from the production corpus (or given verbatim in the
# wave brief) and checked present in the 2026-08-25 read-only dump of the 290
# kind='theme' posts (and, where noted, kind='breadth' posts). This is the
# same hand-verified exception-list discipline as watchlists.SYMBOL_ALIASES:
# NOT a fuzzy matcher -- a phrase absent here is never matched, and a post
# matching no phrase produces no theme row (counted as coverage debt).
#
# Deliberate aliases (same canonical theme, different literal wording) are
# listed as separate phrases under one key -- e.g. "wire & cable" and "wire
# and cable" both map to "Wire and Cable". Anything else is conservatively a
# separate label, never merged automatically. Longest matched phrase wins per
# post; ties go to the first-listed key.
# ---------------------------------------------------------------------------
THEME_LABELS: dict[str, tuple[str, ...]] = {
    # Brief example "Everywhere Gold and Silver" (post 2017199440973660372);
    # also 2013919899102392704, 2018245122966835365, 2025768621184856327,
    # 2027003147626172444. "Gold and Silver" is the preserved canonical;
    # "gold & silver" (2016904583680077839, 2034644749869785144) is a
    # deliberate alias.
    "Gold and Silver": ("gold and silver", "gold & silver"),
    # Commodities, each a literal single-word phrase with word boundaries, so
    # "gold" never fires on "golden" and "silver" never fires on "#SilverETF".
    "Gold": ("gold",),
    "Silver": ("silver",),
    "Copper": ("copper",),
    # "crude", "crude oil", "brent crude", "oil market"... dominate the
    # multibaggerwala/Trading4Bucks energy-crisis posts (2027643535357583473
    # "Crude Gold Silver Equity Sensex", 2029501515921252531 "STRAIT of
    # HORMUZ", 2031661817890767075 "Brent Crude above $91").
    "Crude and Oil": ("crude", "crude oil", "brent crude", "oil market",
                      "oil production", "oil crisis", "oil prices",
                      "oil supply", "crude prices", "oil at"),
    "Fuel Prices": ("petrol", "diesel", "petrol and diesel", "fuel price",
                    "fuel prices", "pump prices"),
    # Brief example "wire and cable firms" (2087432700781269374); also
    # 2018995481955967271 "Wire and cable firms", 2075235687608271329 "Wire &
    # Cable stocks", 2059155031224733860 "Cables and Wires: Leaders".
    "Wire and Cable": ("wire and cable", "wire & cable", "wire and cable firms",
                       "cables and wires", "w & c"),
    # "Manas bhai any outlook on defence" (2001900817008463965), "Defence
    # Acquisition Council", "India?s defence super-cycle", "Defense/ Chemicals"
    # (2067154690207584510), "Data Patterns was one of the Defence names".
    "Defence": ("defence", "defense"),
    # "Power theme is super strong, along with metals" (2048734145648767032),
    # "Power transmission upgrades" (2022904846781943850), "Power is back on
    # charts" (2059633524941234391), "Power and Proxies" (2043684809281843582).
    "Power": ("power",),
    # "DATA CENTRES a big theme" (2006987634061750368), "Ai-Data Centre"
    # (2069077524437668185), "AI data center theme struggling" (2075235687608271329),
    # "data center setups increase" (2077761198662271102).
    "Data Centres": ("data centre", "data center", "data centres",
                     "data centers", "data centre proxy", "ai data center",
                     "ai data centre", "data demand"),
    # "renewables are on Added a record 51 GW" (2043361560937267360),
    # "renewable integration" (2022904846781943850), "solar manufacturers"
    # (2058861470683918603).
    "Renewables and Solar": ("renewable", "renewables", "solar"),
    # "railway stocks" (2002043257875042672), "#railways" (2053702613640859709),
    # "Railway Minister" (2070721911437615460), "New Wagon Design Policy".
    "Railways": ("railway", "railways", "wagon"),
    # "Water: Today the Pumps" (2069316477170454844), "Water theme stocks"
    # (2075943755862196255), "My thesis on the water names" (2082497577895989621).
    "Water": ("water",),
    "Pumps": ("pumps",),
    # "Biodiesel is arguably better" (2027006849682182614), "Biofuels is a
    # miracle" (2007768930799194183), "20% ethanol bleeding"
    # (2027006849682182614), "producing so much ethanol" (2079597122643792126).
    "Biodiesel": ("biodiesel",),
    "Biofuels": ("biofuel", "biofuels"),
    "Ethanol": ("ethanol",),
    # "Telecom + optical fibre + data demand cycle" (2019270111287529795),
    # "whole Telecom and Network industry" (2045887522996441363),
    # "conventional and optical fibres players" (2077761198662271102).
    "Telecom and Optical Fibre": ("telecom", "optical fibre", "optical fiber"),
    # "Metal and mining sector strong" (2044709609353683253),
    # "Metals and their proxies" (2048734145648767032), "Metal & Mining"
    # (2048609050708037656), "rotating into the Metals sector"
    # (2052224963986510162), "similar to Metals" (2021628784395551141).
    "Metals and Mining": ("metal and mining", "metal & mining",
                          "metals sector", "metals and proxies",
                          "mining sector"),
    "Metals": ("metals", "metal"),
    # "PSU banks" (2011853194696233345), "Money flow is now shifting toward
    # the banking and defence sectors" (2016938144579641746), "Small finance
    # banks ... turning around" (2080625303513391258), "ESAF small bank"
    # (2087039813279199502).
    "Banking": ("banking", "banks", "bank"),
    "Small Finance Banks": ("small finance bank", "small finance banks",
                            "small bank", "small banks"),
    # "SME related data" (2006640231496450197), "46 SMEs" (2007094040169496807).
    "SMEs": ("sme", "smes"),
    # "Microcap stocks are where fortunes are made" (2028337711267172766).
    "Microcaps": ("microcap", "microcaps", "micro-cap"),
    # "Slowdown in Real estate" (2075830212840042572), "Real estate in my
    # tier 3 city" (2029088196194103701).
    "Real Estate": ("real estate",),
    # "Theme of shipping is strong" (2051442073765847178).
    "Shipping": ("shipping",),
    # "identify next ipo stock" (2005822975388369297), "IPO sector as a whole"
    # (2086391496450920611), "hunting for IPO names" (2034106029139689551).
    "IPOs": ("ipo", "ipos"),
    # "chemical firms in EV battery value chain" (2078460929549963639),
    # "Himadri Speciality Chemical" (2077363368894357922), "Defense/ Chemicals"
    # (2067154690207584510).
    "Chemicals": ("chemical", "chemicals"),
    # "pharma as a sector has been performing quite well" (2031377214143607008),
    # "biggest compounding stories may still be pharma" (2064269438346805263).
    "Pharma and Healthcare": ("pharma", "healthcare", "hospital", "hospitals",
                              "medical", "pharmaceutical"),
    # "EVs use ~80 kg of #copper" (2034313216164311160), "Indian battery
    # sector poised for robust expansion" (2073619333495037975).
    "EV and Batteries": ("electric vehicle", "electric vehicles", "evs",
                         "battery", "batteries", "lithium", "ev battery"),
    # "INDIAN AVIATION IS UNDER EXTREME STRESS" (2049019115004981505).
    "Aviation": ("aviation", "airlines"),
    # "Textile will be biggest beneficiary" (2075426073756713146), "greige
    # fabric" (2075559322009161760).
    "Textiles": ("textile", "textiles", "greige fabric", "fabric"),
    # "Gems, Pharma, Textile" (2075426073756713146), "jewellery stocks may
    # suffer" (2054450115897913434), "gold and rough diamonds" (2029130006593716523).
    "Gems and Jewellery": ("jewellery", "jewelry", "gems", "diamond",
                           "diamonds"),
    # "Media sector will do well" (1809566913506459775).
    "Media": ("media",),
    # "Intense competition in Paint Industry" (1804534687324410140).
    "Paint": ("paint",),
    # "Logistics isn?t a sector, it?s an economic multiplier" (2013838870824014277).
    "Logistics": ("logistics",),
    # "Sugar stocks yesterday and today" (2084490667280253123).
    "Sugar": ("sugar",),
    # "Told you about the #NUCLEAR Theme" (2067467761543200957), "nuclear fast
    # breeder technology" (2042160201906979244).
    "Nuclear Energy": ("nuclear",),
    # "Focus on Natural Gas" (2029226033841619282), "QATARS GAS PRODUCTION
    # CAPACITY" (2034858366141702229), "LNG in transport" (2046873977445089548).
    "Natural Gas and LNG": ("natural gas", "lng", "gas production"),
    # "For sectoral/theme nifty energy looking too good" (2018959637287206992),
    # "biggest energy crisis in last 5 decades" (2034465980932620451).
    "Energy": ("energy",),
    # "palm oil prices to fall drastically" (2006241559831089439),
    # "edible oil dynamic" (same post).
    "Palm Oil": ("palm oil",),
    "Edible Oil": ("edible oil",),
}
# Transparency: any theme absent from this table is reported as
# skipped/no_extractable_theme at run time and must be added here by the
# maintainer with quoted corpus evidence, never guessed.
assert len(THEME_LABELS) == len({k for k in THEME_LABELS}), "no duplicate keys"

# All multi-word + single-word phrases, precompiled for matching. Keeps the
# no-invention rule cheap: one scan of the lowercased text per post.
_THEME_PHRASES: list[tuple[str, str, str, re.Pattern | None]] = []
for _name, _phrases in THEME_LABELS.items():
    for _phrase in _phrases:
        _rex = None if " " in _phrase or "&" in _phrase else _boundary_re(_phrase)
        _THEME_PHRASES.append((_name, _phrase, _phrase, _rex))


def _match_themes(text: str) -> tuple[str | None, str | None]:
    """(theme name, matched literal phrase) for ``text``, or (None, None).

    Implements the documented normalisation rule: case-insensitive literal
    phrase matching; single-word phrases need word boundaries; the LONGEST
    matched phrase wins per post; ties go to the first phrase listed in
    THEME_LABELS. A text matching nothing yields (None, None) -- the caller
    skips the post (no-invention guard).
    """
    lower = (text or "").lower()
    best_name: str | None = None
    best_phrase: str | None = None
    best_len = -1
    # _THEME_PHRASES order is THEME_LABELS insertion order; iterating in that
    # order and only replacing on STRICTLY longer matches implements ties ->
    # first listed.
    for name, phrase, _, rex in _THEME_PHRASES:
        hit = bool(rex.search(lower)) if rex is not None else phrase in lower
        if hit and len(phrase) > best_len:
            best_len = len(phrase)
            best_name = name
            best_phrase = phrase
    return best_name, best_phrase


def _stance_of(text: str) -> tuple[str | None, int]:
    """(stance, n_buckets_hit) from the post text's explicit stance words.

    Exactly one of the three vocabularies matching -> that stance. None
    matching -> (None, 0). More than one matching (e.g. both "bullish" and
    "staying light" in one text) -> (None, n) -- contradictory evidence is
    NULL over guess. Returns the bucket count so the caller can report
    ambiguity honestly in the run stats.
    """
    lower = (text or "").lower()
    hits: dict[str, int] = {}
    for bucket, words in (
        (STANCE_RISK_ON, STANCE_RISK_ON_WORDS),
        (STANCE_RISK_OFF, STANCE_RISK_OFF_WORDS),
        (STANCE_NEUTRAL, STANCE_NEUTRAL_WORDS),
    ):
        for word in words:
            if " " in word:
                if word in lower:
                    hits[word] = 1
            elif _boundary_re(word).search(lower):
                hits[word] = 1
    buckets = {
        STANCE_RISK_ON: sum(1 for w in STANCE_RISK_ON_WORDS if w in hits),
        STANCE_RISK_OFF: sum(1 for w in STANCE_RISK_OFF_WORDS if w in hits),
        STANCE_NEUTRAL: sum(1 for w in STANCE_NEUTRAL_WORDS if w in hits),
    }
    n_buckets = sum(1 for n in buckets.values() if n)
    if n_buckets != 1:
        return None, n_buckets
    for stance, n in buckets.items():
        if n:
            return stance, 1
    return None, 0  # pragma: no cover - unreachable, defensive


def _topic_tags_of(text: str) -> list[str]:
    """Topic tags for an education post: exactly the fixed vocabulary tags
    whose literal trigger strings appear in the text (see TOPIC_TAG_TRIGGERS),
    in vocabulary order. Never inferred, never empty-but-guessed."""
    lower = (text or "").lower()
    out: list[str] = []
    for tag in TOPIC_TAG_TRIGGERS:  # dict preserves vocabulary order
        for trigger in TOPIC_TAG_TRIGGERS[tag]:
            if " " in trigger:
                if trigger in lower:
                    out.append(tag)
                    break
            elif _boundary_re(trigger).search(lower):
                out.append(tag)
                break
    return out


def _claims_of(text: str) -> list[str]:
    """Verbatim claim spans for claims_json: the post text split on sentence
    punctuation ('.', '!', '?') followed by whitespace, with empty and
    numbered-list-marker segments dropped. Decimal points do not split ('94.82'
    has a digit after the '.')."""
    segs: list[str] = []
    for seg in _CLAIM_SPLIT_RE.split(text or ""):
        s = seg.strip()
        if s and not _LIST_MARKER_RE.match(s):
            segs.append(s)
    return segs


def _first_sentence(text: str) -> str:
    """Verbatim first sentence of ``text`` (used for edu_items.title)."""
    t = (text or "").strip()
    if not t:
        return ""
    for sep in (". ", "! ", "? "):
        idx = t.find(sep)
        if idx > 0:
            t = t[: idx + 1]
            break
    return t.strip()


def _hashtag_symbols(text: str) -> list[str]:
    """Distinct uppercase #hashtag tokens in ``text``, first-seen order
    (same shape as watchlists._hashtag_symbols)."""
    seen: list[str] = []
    for m in _HASHTAG_RE.finditer(text or ""):
        sym = m.group(1).upper()
        if sym not in seen:
            seen.append(sym)
    return seen


def _is_contaminated(handle: str, text: str) -> bool:
    """Reply-under-tracked-handle capture defect (same rule as watchlists)."""
    return (text or "").startswith("@" + handle)


def resolve_symbol(raw: str, master: set[str]) -> str | None:
    """Raw candidate token -> NSE ticker, or None. There is intentionally NO
    alias map here: theme/breadth posts are not symbol-resolution targets, and
    a token absent from the master is simply dropped (reported), never
    fuzzy-matched. Mirrors watchlists.resolve_symbol minus the aliases."""
    candidate = raw.strip().upper()
    if candidate.startswith("#"):
        candidate = candidate[1:]
    return candidate if candidate in master else None


def _symbols_of(text: str, class_symbols_json: str | None,
                master: set[str]) -> tuple[list[str], dict[str, int]]:
    """NSE-validated symbol list for a post plus unresolved count per token.
    Candidates = post_class.symbols UNION #hashtags in the raw text; each is
    validated against ``master`` (``SELECT DISTINCT symbol FROM daily_prices``)
    and dropped when absent -- never invented. Same discipline as
    watchlists.derive."""
    candidates: list[str] = list(_hashtag_symbols(text))
    if class_symbols_json:
        try:
            parsed = json.loads(class_symbols_json)
        except (json.JSONDecodeError, TypeError):
            parsed = []
        for s in parsed:
            su = str(s).upper()
            if su not in candidates:
                candidates.append(su)
    resolved: list[str] = []
    unresolved: dict[str, int] = {}
    for raw in candidates:
        sym = resolve_symbol(raw, master)
        if sym is None:
            unresolved[raw] = unresolved.get(raw, 0) + 1
        elif sym not in resolved:
            resolved.append(sym)
    return resolved, unresolved


# ---------------------------------------------------------------------------
# Derivation core -- read-only. Builds every row to write plus a stats dict
# for logging/reporting, without issuing any write (safe to call repeatedly,
# e.g. for a dry-run report against the production DB).
# ---------------------------------------------------------------------------

def _candidate_posts(conn) -> list[dict]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT p.post_id, p.handle, p.text, p.ts_ist, p.ts_utc, p.url, "
            "       p.is_mock, pc.kind AS kind, pc.symbols AS class_symbols, "
            "       pc.confidence AS class_confidence "
            "FROM posts p JOIN post_class pc ON pc.post_id = p.post_id "
            "WHERE pc.kind IN ('theme','breadth','education') "
            "  AND p.text IS NOT NULL"
        ).fetchall()
    ]


def derive(conn) -> tuple[dict[str, list[dict]], dict]:
    """Compute the full materialisation for the three insight tables from
    posts/post_class/daily_prices. Pure read -- issues no writes, so it is
    safe to call on its own (e.g. for the production read-only report before
    any write). Returns (rows_by_table, stats)."""
    master = {r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_prices")}

    breadth_rows: list[dict] = []
    edu_rows: list[dict] = []
    # theme aggregation: canonical name -> per-theme accumulators
    theme_acc: dict[str, dict] = {}

    stats: dict = {
        "themes": {
            "considered": 0, "theme_posts": 0, "breadth_contrib_posts": 0,
            "written": 0, "mentions": 0,
            "skipped": {"contaminated": 0, "no_text": 0, "no_ts": 0,
                        "no_extractable_theme": 0},
            "per_theme": {},
        },
        "breadth_notes": {
            "considered": 0, "written": 0,
            "skipped": {"contaminated": 0, "no_text": 0, "no_ts": 0},
            "stances": {"risk_on": 0, "risk_off": 0, "neutral": 0, "null": 0},
            "ambiguous_stance": 0,
        },
        "edu_items": {
            "considered": 0, "written": 0,
            "skipped": {"contaminated": 0, "no_text": 0, "no_ts": 0},
            "tags": {},
        },
    }

    def _theme_mention(post: dict, theme_name: str) -> None:
        acc = theme_acc.setdefault(theme_name, {
            "posts": 0, "traders": set(), "first_seen": None, "last_seen": None,
            "symbols": [], "unresolved": {}, "is_mock": 0,
        })
        acc["posts"] += 1
        acc["traders"].add(post["handle"])
        acc["is_mock"] = acc["is_mock"] or post["is_mock"]
        d = (post["ts_ist"] or "")[:10]
        if d:
            acc["first_seen"] = d if acc["first_seen"] is None else min(acc["first_seen"], d)
            acc["last_seen"] = d if acc["last_seen"] is None else max(acc["last_seen"], d)
        syms, unresolved = _symbols_of(post["text"], post["class_symbols"], master)
        for s in syms:
            if s not in acc["symbols"]:
                acc["symbols"].append(s)
        for tok, n in unresolved.items():
            acc["unresolved"][tok] = acc["unresolved"].get(tok, 0) + n

    for post in _candidate_posts(conn):
        handle = post["handle"]
        text = post["text"] or ""
        kind = post["kind"]

        # Shared eligibility bookkeeping (per-table skipped-with-reason).
        skip_reason = None
        if _is_contaminated(handle, text):
            skip_reason = "contaminated"
        elif not text:
            skip_reason = "no_text"
        elif not post["ts_ist"]:
            skip_reason = "no_ts"

        if kind == "breadth":
            stats["breadth_notes"]["considered"] += 1
            if skip_reason:
                stats["breadth_notes"]["skipped"][skip_reason] += 1
                continue
            # A breadth post names a sector -> it also counts as a theme
            # mention (INS-3's "optionally breadth" source), but ONLY through
            # a literal THEME_LABELS phrase -- it never creates a theme by
            # itself beyond phrase matching.
            theme_name, _ = _match_themes(text)
            if theme_name is not None:
                _theme_mention(post, theme_name)
                stats["themes"]["breadth_contrib_posts"] += 1
            stance, n_buckets = _stance_of(text)
            if n_buckets > 1:
                stats["breadth_notes"]["ambiguous_stance"] += 1
            stats["breadth_notes"]["stances"][stance if stance else "null"] += 1
            symbols, _ = _symbols_of(text, post["class_symbols"], master)
            breadth_rows.append({
                "post_id": post["post_id"],
                "handle": handle,
                "trade_date": (post["ts_ist"] or "")[:10],
                "stance": stance,
                "claims_json": json.dumps(_claims_of(text)),
                "symbols": json.dumps(symbols),
                "confidence": post["class_confidence"],
                "is_mock": post["is_mock"],
                "ingested_at": now_iso(),
            })
            continue

        if kind == "education":
            stats["edu_items"]["considered"] += 1
            if skip_reason:
                stats["edu_items"]["skipped"][skip_reason] += 1
                continue
            tags = _topic_tags_of(text)
            for t in tags:
                stats["edu_items"]["tags"][t] = stats["edu_items"]["tags"].get(t, 0) + 1
            title = _first_sentence(text)
            if len(title) > TITLE_MAX_CHARS:
                title = title[:TITLE_MAX_CHARS] + "..."
            edu_rows.append({
                "post_id": post["post_id"],
                "handle": handle,
                "title": title,
                "principle_text": text,
                "topic_tags": json.dumps(tags),
                "stated_at": post["ts_ist"],
                "confidence": post["class_confidence"],
                "is_mock": post["is_mock"],
                "ingested_at": now_iso(),
            })
            continue

        # kind == 'theme'
        stats["themes"]["considered"] += 1
        stats["themes"]["theme_posts"] += 1
        if skip_reason:
            stats["themes"]["skipped"][skip_reason] += 1
            continue
        theme_name, matched_phrase = _match_themes(text)
        if theme_name is None:
            stats["themes"]["skipped"]["no_extractable_theme"] += 1
            continue
        _theme_mention(post, theme_name)

    theme_rows: list[dict] = []
    for name in sorted(theme_acc):
        acc = theme_acc[name]
        stats["themes"]["mentions"] += acc["posts"]
        theme_rows.append({
            "name": name,
            "symbols_json": json.dumps(acc["symbols"]),
            "first_seen": acc["first_seen"],
            "last_seen": acc["last_seen"],
            # mention_count = DISTINCT TRADERS (see module docstring): INS-3's
            # anti-masquerade metric; the schema has exactly one count column.
            "mention_count": len(acc["traders"]),
            "is_mock": acc["is_mock"],
            "ingested_at": now_iso(),
        })
        stats["themes"]["per_theme"][name] = {
            "posts": acc["posts"],
            "traders": len(acc["traders"]),
            "first_seen": acc["first_seen"],
            "last_seen": acc["last_seen"],
            "unresolved_total": sum(acc["unresolved"].values()),
        }
    stats["themes"]["written"] = len(theme_rows)

    stats["breadth_notes"]["written"] = len(breadth_rows)
    stats["edu_items"]["written"] = len(edu_rows)
    stats["total_written"] = len(theme_rows) + len(breadth_rows) + len(edu_rows)
    return {"themes": theme_rows, "breadth_notes": breadth_rows,
            "edu_items": edu_rows}, stats


# ---------------------------------------------------------------------------
# Orchestration -- matches adopted/bhavcopy.py's run(conn, run_date) -> int
# contract: full materialisation in one transaction, pipeline_runs logging
# either way, never partially commits. Idempotent per the module docstring.
# ---------------------------------------------------------------------------

_INSERT_BREADTH_SQL = (
    "INSERT INTO breadth_notes "
    "(post_id, handle, trade_date, stance, claims_json, symbols, confidence, "
    " is_mock, ingested_at) "
    "VALUES (:post_id, :handle, :trade_date, :stance, :claims_json, :symbols, "
    " :confidence, :is_mock, :ingested_at) "
    "ON CONFLICT(post_id) DO UPDATE SET "
    " handle=excluded.handle, trade_date=excluded.trade_date, "
    " stance=excluded.stance, claims_json=excluded.claims_json, "
    " symbols=excluded.symbols, confidence=excluded.confidence, "
    " is_mock=excluded.is_mock, ingested_at=excluded.ingested_at"
)

_INSERT_THEME_SQL = (
    "INSERT INTO themes "
    "(name, symbols_json, first_seen, last_seen, mention_count, is_mock, "
    " ingested_at) "
    "VALUES (:name, :symbols_json, :first_seen, :last_seen, :mention_count, "
    " :is_mock, :ingested_at) "
    "ON CONFLICT(name) DO UPDATE SET "
    " symbols_json=excluded.symbols_json, first_seen=excluded.first_seen, "
    " last_seen=excluded.last_seen, mention_count=excluded.mention_count, "
    " is_mock=excluded.is_mock, ingested_at=excluded.ingested_at"
)

# edu_items has NO unique constraint on post_id (verified in db/schema.sql), so
# ON CONFLICT(post_id) is impossible; refresh in place by post_id.
_UPDATE_EDU_SQL = (
    "UPDATE edu_items SET handle=?, title=?, principle_text=?, topic_tags=?, "
    " stated_at=?, confidence=?, is_mock=?, ingested_at=? WHERE post_id=?"
)
_INSERT_EDU_SQL = (
    "INSERT INTO edu_items "
    "(post_id, handle, title, principle_text, topic_tags, stated_at, "
    " confidence, is_mock, ingested_at) "
    "VALUES (?,?,?,?,?,?,?,?,?)"
)


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (STAGE, run_date, status, rows, int(dur * 1000), detail, now_iso()),
    )


def _delete_stale(conn, table: str, key_col: str, keys: set[str]) -> None:
    """Remove rows this module owns whose natural key no longer appears in the
    current source set (reclassification or edits upstream). Runs inside the
    caller's transaction; breadth_notes and themes have no inbound FK."""
    if not keys:
        conn.execute(f"DELETE FROM {table}")  # noqa: S608 - internal table names
        return
    marks = ",".join("?" * len(keys))
    conn.execute(f"DELETE FROM {table} WHERE {key_col} NOT IN ({marks})", tuple(keys))


def run(conn, run_date: str, _stats_out: dict | None = None) -> int:
    """Full re-derivation of themes + breadth_notes + edu_items. Never raises
    without first logging and rolling back to a clean state.

    Idempotent: re-running against an unchanged corpus writes the same
    content, never duplicates (see module docstring "Idempotency" -- upsert
    on the natural key for breadth_notes/themes plus stale-row deletion;
    update-in-place by post_id for edu_items, whose schema has no unique key).

    ``run_date`` stamps the pipeline_runs row; this stage rebuilds from the
    WHOLE corpus every call and does not filter anything by ``run_date``
    (matching the reconciler/watchlists full-rebuild discipline).

    ``_stats_out``, if given, is populated in place with derive()'s full
    stats dict (skipped-with-reason counts, stance distribution, per-theme
    detail) for callers that want more than the row count -- see __main__.

    Returns the number of rows written across the three tables.
    """
    started = time.monotonic()
    try:
        rows, stats = derive(conn)
        if _stats_out is not None:
            _stats_out.update(stats)

        breadth_keys = {r["post_id"] for r in rows["breadth_notes"]}
        theme_keys = {r["name"] for r in rows["themes"]}

        _delete_stale(conn, "breadth_notes", "post_id", breadth_keys)
        _delete_stale(conn, "themes", "name", theme_keys)

        if rows["breadth_notes"]:
            conn.executemany(_INSERT_BREADTH_SQL, rows["breadth_notes"])
        if rows["themes"]:
            conn.executemany(_INSERT_THEME_SQL, rows["themes"])
        for edu in rows["edu_items"]:
            cur = conn.execute(
                _UPDATE_EDU_SQL,
                (edu["handle"], edu["title"], edu["principle_text"],
                 edu["topic_tags"], edu["stated_at"], edu["confidence"],
                 edu["is_mock"], edu["ingested_at"], edu["post_id"]),
            )
            if cur.rowcount == 0:
                conn.execute(
                    _INSERT_EDU_SQL,
                    (edu["post_id"], edu["handle"], edu["title"],
                     edu["principle_text"], edu["topic_tags"], edu["stated_at"],
                     edu["confidence"], edu["is_mock"], edu["ingested_at"]),
                )

        dur = time.monotonic() - started
        total = len(rows["breadth_notes"]) + len(rows["themes"]) + len(rows["edu_items"])
        detail = (
            f"themes={len(rows['themes'])} mentions={stats['themes']['mentions']} "
            f"breadth_notes={len(rows['breadth_notes'])} "
            f"edu_items={len(rows['edu_items'])} skipped="
            f"{sum(stats['themes']['skipped'].values()) + sum(stats['breadth_notes']['skipped'].values()) + sum(stats['edu_items']['skipped'].values())}"
        )
        _log_run(conn, run_date, "ok", total, dur, detail)
        conn.commit()
        return total
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started,
                 f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise


if __name__ == "__main__":
    from traderlog.db import connect

    _conn = connect()
    _stats: dict = {}
    _n = run(_conn, date.today().isoformat(), _stats_out=_stats)

    _t = _stats["themes"]
    _b = _stats["breadth_notes"]
    _e = _stats["edu_items"]
    print(f"rows written across the three tables: {_n}")
    print(f"themes: {_t['written']} themes from {_t['considered']} posts "
          f"({_t['theme_posts']} theme + {_t['breadth_contrib_posts']} breadth contrib), "
          f"{_t['mentions']} mentions, skipped: {_t['skipped']}")
    print(f"breadth_notes: {_b['written']} rows from {_b['considered']} posts, "
          f"stances {_b['stances']}, ambiguous {_b['ambiguous_stance']}, "
          f"skipped: {_b['skipped']}")
    print(f"edu_items: {_e['written']} rows from {_e['considered']} posts, "
          f"tags {_e['tags']}, skipped: {_e['skipped']}")
    print("themes detail (name: posts/traders, first..last):")
    for name, d in sorted(_t["per_theme"].items(), key=lambda kv: -kv[1]["traders"]):
        print(f"  {name}: {d['posts']} posts / {d['traders']} traders, "
              f"{d['first_seen']}..{d['last_seen']}, unresolved {d['unresolved_total']}")