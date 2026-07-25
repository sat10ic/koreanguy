// v5 primitive: reference bands for stat tiles.
//
// Why this exists. The user, repeatedly: "the graphs are just having 1-2 line
// explainers without helping the user understand what is actually happening and
// how to read". A tile that reads "%>10DMA  20.3" tells a beginner nothing --
// 20.3 is severely weak, but it renders identically to 48.9, which is neutral.
// Every StatusChip on the MARKET tab passed no `tone`, so all 21 were grey.
//
// Fix: state the reference band next to the number, the way earningspulse does
// ("Top 30% of range = pressure into highs; bottom 30% = pressure into lows").
// The number stays; a word and a colour tell you where it sits.
//
// One writer: thresholds live HERE, not scattered at call sites, so the same
// metric cannot be graded two different ways on two panels.

/**
 * @param {number|null|undefined} value
 * @param {{good:number, bad:number, invert?:boolean, words?:[string,string,string]}} band
 *   good/bad are the thresholds. Default reading is "higher is better":
 *   value >= good -> strong, value <= bad -> weak, else neutral.
 *   invert:true flips it (for metrics where lower is better, e.g. RMV).
 * @returns {{tone:"green"|"amber"|"red"|"neutral", word:string|null}}
 */
export function bandFor(value, band) {
  if (value === null || value === undefined || !Number.isFinite(Number(value)) || !band) {
    return { tone: "neutral", word: null };
  }
  const v = Number(value);
  const { good, bad, invert = false } = band;
  const [strongWord, midWord, weakWord] = band.words || ["strong", "neutral", "weak"];
  const isStrong = invert ? v <= good : v >= good;
  const isWeak = invert ? v >= bad : v <= bad;
  if (isStrong) return { tone: "green", word: strongWord };
  if (isWeak) return { tone: "red", word: weakWord };
  return { tone: "amber", word: midWord };
}

// Named bands, so a threshold is defined once and reused.
// Sources: %>DMA 50 is the conventional participation midpoint (already used as
// TrendChart's refLine={50} on this page). A/D ratio and NH/NL pivot at 1.0 and
// 50% respectively by construction. RMV's tight bar of 15 mirrors
// manas_indicators.rmv's own `aplus` threshold via scanner/entry_quality.py.
export const BANDS = {
  pctAboveDma: { good: 60, bad: 40 },                       // participation breadth
  adRatio: { good: 1.2, bad: 0.8 },                          // advancing vs declining
  nhNlPct: { good: 55, bad: 35 },                            // new highs share
  netBreadth: { good: 1, bad: -1 },                          // up4% minus down4%
  sustainRatio: { good: 1.2, bad: 0.8, words: ["sustaining", "mixed", "failing"] },
  rmv: { good: 15, bad: 50, invert: true, words: ["coiled", "normal", "loose"] },
  rs: { good: 80, bad: 50 },
};

/** Compact "what this number means" suffix, e.g. "48.9 neutral". */
export function readWord(value, band) {
  return bandFor(value, band).word;
}
