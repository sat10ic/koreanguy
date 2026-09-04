import { useState } from "react";
import { useDensity } from "../DensityContext.jsx";

/**
 * InfoDot (ⓘ) — the beginner glossary affordance from the design system
 * (§3, §7). Click any term's ⓘ to get a one-line plain-English definition.
 * Small, self-contained glossary scoped to what's actually on screen today;
 * grows as new terms appear on other pages — not a wholesale import of the
 * old (larger) legacy glossary, per the adopt-don't-import rule.
 *
 * Axis F (BEGINNER_EXPERT_SPEC): full affordance in Beginner; dimmer in Expert
 * (a dense view doesn't need every ⓘ shouting) but identical on hover/click.
 */
export const GLOSSARY = {
  posture: "How aggressive you're allowed to be today, based on market breadth and trend health.",
  xp: "A single dial summarizing the energy/strength of the current up-move — how much of the market is participating in up-moves right now. Higher = stronger thrust, broader participation.",
  mbi: "Market Breadth Indicator — colors the day Green/White/Red from a handful of breadth ratios (see below).",
  burst: "The ratio of stocks making big (4%+) up-moves vs. big down-moves today. Above ~200 = broad-based strength; below ~50 = broad-based weakness.",
  r10: "10R — the ratio of stocks above their 10-day average vs. below it. 75+ green (strong), 50-75 white (neutral), below 50 red (weak).",
  r20: "20R — the ratio of stocks above their 20-day average vs. below it. 75+ green (strong), 50-75 white (neutral), below 50 red (weak).",
  r50: "50R — the ratio of stocks above their 50-day average vs. below it. 85+ green (strong), 60-85 white (neutral), below 60 red (weak).",
  "xp-band": "Where today's XP dial sits: below 15 = low energy, 15-40 = building, 40-100 = strong, above 100 = extreme.",
  breadth: "The share of stocks trading above their 20-day average — rising = broadening participation, falling = narrowing.",
  risk: "The % of your account you're allowed to risk on one new trade today, based on the current posture.",
  warning: "3 or more of the underlying breadth checks turned red — a caution flag even if the overall day isn't red yet.",
  momentum: "Is short-term price thrust expanding or fading, based on today's move and the burst ratio.",
  swing: "Can short-term (days-to-weeks) trades work right now — based on how many stocks are above their short moving averages.",
  trend: "Is the intermediate (weeks) trend healthy — based on medium moving-average breadth.",
  bias: "Is the longer-term backdrop supportive — based on longer moving-average breadth.",
  rvol: "Relative volume — today's volume divided by its recent average. Above 1.5x means unusually heavy trading.",
  gap: "The % difference between today's open and yesterday's close.",
  adr: "Average Daily Range — how much a stock typically moves in a day, as a %. Higher = more volatile.",
  delivery: "Delivery % (bhavcopy) — the share of traded volume that actually changed hands (not intraday squaring-off). Higher tends to mean more genuine, less speculative buying.",
  readiness: "A 0-100 score for how well a candidate matches its setup's named filters right now. Not a black box — every point traces to a named filter that fired.",
  expectancy: "Average R gained or lost per trade, based on your logged trade history. Positive means the system has an edge over time.",
  "dist-pivot": "% distance from the entry pivot (breakout/pullback trigger level). Near zero means the setup is close to actionable.",
};

export default function InfoDot({ term }) {
  const [open, setOpen] = useState(false);
  const { density } = useDensity();
  const text = GLOSSARY[term];
  if (!text) return null;
  return (
    <span className="relative inline-block">
      <button
        type="button"
        data-testid={`infodot-${term}`}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setOpen(false)}
        title={text}
        aria-label={`What does ${term} mean?`}
        className={
          "ml-0.5 inline-flex h-3 w-3 items-center justify-center rounded-full text-[8px] leading-none text-inkDisabled hover:text-info " +
          (density === "expert" ? "opacity-40 hover:opacity-100" : "")
        }
      >
        ⓘ
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-0 top-4 z-10 w-48 border border-hairline bg-card p-2 font-sans text-[11px] leading-snug text-ink2 shadow-none"
        >
          {text}
        </span>
      )}
    </span>
  );
}
