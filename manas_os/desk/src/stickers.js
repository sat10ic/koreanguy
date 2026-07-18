// ============================================================
// STICKER REGISTRY — the ONE canonical sticker set, app-wide.
// Spec: manas_os/design/FOOTPRINT_DRIVER_SPEC_2026-07-18.md
//   section "UI — FLOW BOARD + STICKER REGISTRY"
//
// Anti-mashup rule: this is the ONLY file that defines sticker codes,
// glyphs, plain-English reads and colors. Every other component imports
// from here — never redeclare a sticker inline.
//
// No-fabrication rule: every code below maps to a field that already
// exists in a real API payload (sourceField documents exactly which
// one). A sticker is only ever rendered where its caller actually has
// that field on the row it is holding — deriveLaneSticker/deriveTier
// below return null rather than guessing when the field is absent.
// LDR (edge-stack leader) is spec'd but not built on the backend yet —
// skipped per the build note.
// ============================================================

// Tier constants — vendor-verbatim, from footprint spec "BUILD NUMERICS"
// (manas_os/alpha/activity.py is the one writer of `score`; these bands
// are display-only classification of that score, computed client-side
// because the board payload carries raw `score`, not a precomputed tier).
export const FOOTPRINT_TIERS = {
  ABNORMAL: 3.5,
  STRICT: 4.0,
  EXTREME: 8.0,
};

// v5 tone -> token color is resolved in Sticker.jsx / primitives.v5.css.
// tone is one of: "green" | "amber" | "red" | "teal" | "neutral".
export const STICKERS = {
  SA: {
    code: "SA",
    glyph: "SA",
    label: "Silent Accumulation",
    plainRead: "Footprint score is unusual, volume is NOT elevated, price is flat inside a base — institutions absorbing quietly. Volume screens miss this by design.",
    sourceField: "footprint.lane === 'silent_accumulation' (GET /api/footprint/board, GET /api/footprint/{symbol})",
    tone: "green",
  },
  SO: {
    code: "SO",
    glyph: "SO",
    label: "Silent Offloading",
    plainRead: "Big prints selling into strength near highs while price holds up — exit-side evidence on a holding.",
    sourceField: "footprint.lane === 'silent_offloading' (GET /api/footprint/board, GET /api/footprint/{symbol})",
    tone: "red",
  },
  AB: {
    code: "AB",
    glyph: "AB",
    label: "Absorption",
    plainRead: "A Wyckoff-style flush on high volume met by size (narrow range) — bullish if it happens in or near a base.",
    sourceField: "footprint.lane === 'absorption' (GET /api/footprint/board, GET /api/footprint/{symbol})",
    tone: "teal",
  },
  FP: {
    code: "FP",
    glyph: "FP",
    label: "Footprint Unusual",
    plainRead: "Institutional footprint score is unusual today (score > 3.5) or extreme (score >= 8) — persistence and delivery decide if it is worth following.",
    sourceField: "footprint.score, thresholded client-side (ABNORMAL 3.5 / EXTREME 8.0, GET /api/footprint/board, GET /api/footprint/{symbol})",
    tone: "amber",
  },
  SS: {
    code: "SS",
    glyph: "SS",
    label: "Strong Start Ready",
    plainRead: "Gap-up-and-hold plus Arora fast-mover checks currently qualify this name.",
    sourceField: "row.ss_flag (GET /api/desk/focus-list rows, Strong Start section of SHORTLIST)",
    tone: "green",
  },
  D2: {
    code: "D2",
    glyph: "D2",
    label: "Day-2 Setup",
    plainRead: "Setup family is a day-2 follow-through pattern off yesterday's move.",
    sourceField: "row.family_label / row.family text match \"day 2\" (DEBATE / SHORTLIST rows)",
    tone: "teal",
  },
  EP: {
    code: "EP",
    glyph: "EP",
    label: "Catalyst / Earnings",
    plainRead: "Setup is catalyst-conditioned — an earnings or news trigger sits behind this entry.",
    sourceField: "row.family_label / row.family text match \"earnings\"/\"catalyst\" (DEBATE / SHORTLIST rows)",
    tone: "amber",
  },
  IPO: {
    code: "IPO",
    glyph: "IPO",
    label: "Fresh Listing",
    plainRead: "Fresh-listing base-coil family — a recently listed stock building its first base.",
    sourceField: "row.family_label / row.family text match \"ipo\" (DEBATE / SHORTLIST rows)",
    tone: "teal",
  },
  W: {
    code: "W",
    glyph: "W",
    label: "Anticipation (WATCH)",
    plainRead: "Trigger is armed — the setup is waiting on price to confirm, not fired yet.",
    sourceField: "row.classification === 'WATCH' (SCANNERS result rows)",
    tone: "amber",
  },
  NT: {
    code: "NT",
    glyph: "NT",
    label: "New Tonight",
    plainRead: "Added to the shortlist by tonight's curator run.",
    sourceField: "row.status === 'ADDED' (GET /api/desk/watchlist rows, SHORTLIST)",
    tone: "teal",
  },
  EXT: {
    code: "EXT",
    glyph: "EXT",
    label: "Extended / Churn Risk",
    plainRead: "Price is extended or sitting near highs and today reads as churn-against-holding — exit-side caution.",
    sourceField: "footprint.context === 'churn_against_holding' (GET /api/footprint/{symbol})",
    tone: "red",
  },
  ASM: {
    code: "ASM",
    glyph: "ASM",
    label: "Surveillance Caution",
    plainRead: "Under exchange short-term/long-term ASM surveillance — sizing or entry may be constrained.",
    sourceField: "reserved — no desk payload currently surfaces a per-symbol ASM tier field; the ASM gate exists server-side (gates.py) but is not yet exposed to any UI row, so this sticker does not render anywhere yet.",
    tone: "red",
  },
};

// Priority order for the MAX_VISIBLE=3 rule: when a row would carry more
// than 3 stickers, this order decides which 3 stay visible and which fold
// into the "+N" overflow popover. Exit-side risk first (a missed warning
// is worse than a missed opportunity chip), then the footprint evidence
// that argues for/against the name, then timing/context stickers, then
// pure provenance (NT). (Assumption — spec does not fix this order.)
export const STICKER_PRIORITY = ["EXT", "SO", "ASM", "AB", "SA", "FP", "SS", "W", "D2", "EP", "IPO", "NT"];

export const MAX_VISIBLE = 3;

// Split an array of sticker codes into {visible, overflow} per the
// MAX_VISIBLE / priority rule. Unknown codes and duplicates are dropped.
export function pickVisibleStickers(codes, max = MAX_VISIBLE) {
  const unique = Array.from(new Set((codes || []).filter((c) => STICKERS[c])));
  const ordered = unique.sort((a, b) => {
    const pa = STICKER_PRIORITY.indexOf(a);
    const pb = STICKER_PRIORITY.indexOf(b);
    return (pa === -1 ? 999 : pa) - (pb === -1 ? 999 : pb);
  });
  return { visible: ordered.slice(0, max), overflow: ordered.slice(max) };
}

// Lane (Flow Board classification) -> sticker code. Only three of the five
// lanes have a sticker in the initial set (public_markup / retail_churn are
// not spec'd stickers); returns null for those and for unrecognized lanes.
const LANE_STICKER = {
  silent_accumulation: "SA",
  silent_offloading: "SO",
  absorption: "AB",
};

export function deriveLaneSticker(lane) {
  return LANE_STICKER[lane] || null;
}

// footprint.score -> tier band, using the vendor-verbatim thresholds above.
// Returns null below the ABNORMAL floor (no FP sticker for an unremarkable
// score) so callers never render FP without real evidence.
export function deriveTier(score) {
  if (score === null || score === undefined || Number.isNaN(Number(score))) return null;
  const s = Number(score);
  if (s >= FOOTPRINT_TIERS.EXTREME) return "EXTREME";
  if (s >= FOOTPRINT_TIERS.STRICT) return "STRICT";
  if (s > FOOTPRINT_TIERS.ABNORMAL) return "ABNORMAL";
  return null;
}
