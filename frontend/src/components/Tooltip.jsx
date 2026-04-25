import React, { useState, useRef, useEffect } from "react";
import { HelpCircle } from "lucide-react";
import { classNames } from "../utils";

/**
 * GLOSSARY — short forms used across the app, with plain-English meaning.
 * Add an entry here and reference it via <Term k="..."> or <InfoDot k="...">.
 */
export const GLOSSARY = {
  RS: {
    title: "Relative Strength (RS)",
    text: "A blended momentum score: 0.2×(1-day return) + 0.3×(5-day return) + 0.5×(21-day return). Stored as a decimal — multiply by 100 to read as %. e.g. RS = 0.0234 → ~2.34% weighted-average daily push. Higher = trending stronger than peers; the Grade column ranks this percentile within bucket.",
  },
  Grade: {
    title: "Grade (A+ → G)",
    text: "Letter rank of the stock's RS percentile within its bucket (Bullish above 50DMA / Bearish below). A+ = top 5%; F/G = bottom of the pack.",
  },
  PD: {
    title: "Purple Dot (PD)",
    text: "A one-day power signal: the stock closed up ≥ 5% on at least 2× its 20-day average volume — a sign of institutional buying.",
  },
  "PD/30": {
    title: "Purple Dots in last 30 days",
    text: "Number of times this stock printed a Purple Dot (≥5% jump on heavy volume) in the past 30 trading sessions. More = persistent demand.",
  },
  Bucket: {
    title: "Bucket (Bullish / Bearish)",
    text: "Bullish = price is above the 50-day moving average. Bearish = price below it. Trends and setups are graded within their bucket.",
  },
  ATR: {
    title: "ATR (Average True Range)",
    text: "A volatility yardstick — the typical daily move of the stock over the last 14 sessions. Used to size stops and judge how 'extended' a move is.",
  },
  SMA: {
    title: "SMA (Simple Moving Average)",
    text: "Average closing price over a window. SMA50 = last 50 days, SMA200 = last 200 days. Trend filters: above = uptrend, below = downtrend.",
  },
  SMA50: {
    title: "50-day Moving Average",
    text: "The medium-term trend line. Stock above SMA50 → bullish bucket. The 'bread-and-butter' setup wants pullbacks toward this line in strong stocks.",
  },
  SMA200: {
    title: "200-day Moving Average",
    text: "The long-term trend line — a stock trading above its 200DMA is in a long-term uptrend.",
  },
  EMA: {
    title: "EMA (Exponential Moving Average)",
    text: "Like SMA but weights recent days more heavily, so it reacts faster to new prices.",
  },
  RSI: {
    title: "RSI (Relative Strength Index)",
    text: "Momentum oscillator (0–100). Above 70 = overbought / extended; below 30 = oversold. Used as a filter, never alone.",
  },
  Setup: {
    title: "Bread-and-Butter Setup",
    text: "Manas Arora's core swing entry: a strong-RS stock pulling back to its 50DMA (or 21EMA) on lighter volume, then printing a green confirmation candle.",
  },
  "Setup Pass": {
    title: "Setup Pass",
    text: "How many stocks in the universe today triggered the bread-and-butter setup conditions (trend, pullback depth, volume contraction, confirmation).",
  },
  Extended: {
    title: "Extended (Yellow / Red)",
    text: "Stocks trading too far above their 50DMA — Yellow = ≥5× ATR away, Red = ≥7× ATR. High risk of mean-reversion; avoid fresh longs.",
  },
  Regime: {
    title: "Market Regime",
    text: "An overall traffic-light read on the market: RISK_ON (green light to take swing trades), CAUTION (be selective), RISK_OFF (stand aside / cash).",
  },
  Pillar: {
    title: "Regime Pillars",
    text: "Four checks the system runs to set the regime: index trend, market breadth, leadership quality, and volatility. All four green = RISK_ON.",
  },
  Tier: {
    title: "Tier (Primary / Secondary)",
    text: "Primary candidates pass the strictest filters and live on your watchlist — these are tradeable. Secondary candidates are watch-only ideas to graduate later.",
  },
  Layer: {
    title: "Layers A & B",
    text: "Two verification gates before a candidate becomes tradeable. Layer A = trend & RS quality. Layer B = setup confirmation (volume contraction, candle).",
  },
  "R-multiple": {
    title: "R-multiple",
    text: "How many units of risk (R = entry − stop) the trade returned. +2R means you made twice your initial risk. Hit-rate × avg-R drives expectancy.",
  },
  Stop: {
    title: "Stop Price",
    text: "The pre-decided exit level if the trade goes against you, usually placed below the recent swing low or 1×ATR under entry.",
  },
  PnL: {
    title: "P&L (Profit & Loss)",
    text: "Live or realised gain/loss on the position, shown in % of entry price.",
  },
  Breadth: {
    title: "Market Breadth",
    text: "How many stocks in the universe are participating — % above SMA50, advance-decline counts. Healthy breadth → trends sustain.",
  },
  ADR: {
    title: "ADR % (Average Daily Range)",
    text: "Average of (High − Low) / Close over the last 14 sessions, expressed as a percent. A read of how much room a stock typically gives you in a day. Above 4% = high-momentum / good for swings; below 2% = sluggish.",
  },
  SectorRS: {
    title: "Sectoral RS (percentile in sector)",
    text: "The stock's RS percentile rank inside its own sector. 0.95 = top 5% of its sector — a true sector leader. Pair this with overall Grade: A-grade AND high SectorRS = best-in-class.",
  },
  BF: {
    title: "Buying Force",
    text: "An 'explosive demand' score — positive % move × (volume / 20-day average volume). The 30-day MAX captures the strongest accumulation event recently. Pairs with the Pine setup: |ROC%| ≥ 5 AND volume ≥ threshold (the same condition that prints a Purple Dot).",
  },
  VolRatio: {
    title: "Volume × (vs 20-day avg)",
    text: "Today's volume divided by the 20-day average volume. 2× = double the usual; 3×+ = institutional accumulation/distribution.",
  },
};

export function InfoDot({ k, title, text, size = 11, className }) {
  const entry = GLOSSARY[k];
  const t = title || entry?.title || k;
  const d = text || entry?.text || "";
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <span
      ref={ref}
      className={classNames("relative inline-flex items-center", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span
        role="button"
        tabIndex={0}
        data-testid={`info-dot-${k}`}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            setOpen((v) => !v);
          }
        }}
        aria-label={`What is ${t}?`}
        className="inline-flex h-3.5 w-3.5 cursor-help items-center justify-center text-textMuted transition-colors hover:text-textPrimary focus:outline-none focus:text-textPrimary"
      >
        <HelpCircle size={size} strokeWidth={1.6} />
      </span>
      {open && (
        <span
          role="tooltip"
          className="absolute left-1/2 top-full z-50 mt-1.5 w-64 -translate-x-1/2 border border-borderDefault bg-surface px-3 py-2 text-left shadow-xl"
          style={{ pointerEvents: "auto" }}
        >
          <span className="block font-mono text-[10px] uppercase tracking-overline text-saffron">
            {t}
          </span>
          {d && (
            <span className="mt-1 block text-[11px] leading-relaxed text-zinc-300 normal-case">
              {d}
            </span>
          )}
        </span>
      )}
    </span>
  );
}

/**
 * <Term k="RS">RS</Term>  — renders text + adjacent help dot.
 * Pass `as="span"` to inline inside other text.
 */
export function Term({ k, children, className, dotSize = 10 }) {
  return (
    <span className={classNames("inline-flex items-center gap-1", className)}>
      {children ?? k}
      <InfoDot k={k} size={dotSize} />
    </span>
  );
}

export default Term;
