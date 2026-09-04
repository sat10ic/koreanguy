// Deterministic synthetic OHLC — seeded by symbol so the same symbol always
// renders the same chart. NOT real bhavcopy data; real ingestion lives in
// unidesk/momentum/data/bhavcopy.py (646k real bars, not wired into this UI yet).

export interface Bar {
  time: string; // yyyy-mm-dd
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

function hashSeed(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h || 1;
}

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function generateOhlc(symbol: string, basePrice: number, days = 140): Bar[] {
  const rand = mulberry32(hashSeed(symbol));
  const bars: Bar[] = [];
  let price = basePrice * 0.72;
  let trendBias = 0.15; // gentle uptrend into the setup, matches "prior expansion" framing
  const start = new Date();
  start.setDate(start.getDate() - days);

  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    if (d.getDay() === 0 || d.getDay() === 6) continue; // skip weekends, NSE-style

    if (i > days * 0.7) trendBias = 0.35; // burst phase into the recent breakout
    const drift = trendBias + (rand() - 0.48) * 2.2;
    const open = price;
    const close = Math.max(1, open * (1 + drift / 100));
    const high = Math.max(open, close) * (1 + rand() * 0.008);
    const low = Math.min(open, close) * (1 - rand() * 0.008);
    const volume = Math.round(400000 + rand() * 900000 * (1 + (i > days * 0.85 ? 1.8 : 0)));

    bars.push({
      time: d.toISOString().slice(0, 10),
      open: round2(open),
      high: round2(high),
      low: round2(low),
      close: round2(close),
      volume,
    });
    price = close;
  }

  // The random walk's endpoint drifts from basePrice — rescale every bar so
  // the series' last close lands exactly on the candidate's real close.
  // Without this, trigger/invalidation price lines (computed off the real
  // close) can fall outside the synthetic series' range entirely.
  const last = bars[bars.length - 1];
  if (last && last.close > 0) {
    const scale = basePrice / last.close;
    for (const b of bars) {
      b.open = round2(b.open * scale);
      b.high = round2(b.high * scale);
      b.low = round2(b.low * scale);
      b.close = round2(b.close * scale);
    }
    bars[bars.length - 1].close = basePrice;
  }
  return bars;
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

export function ema(bars: Bar[], period: number): { time: string; value: number }[] {
  const k = 2 / (period + 1);
  let prev: number | null = null;
  return bars.map((b) => {
    const v = prev === null ? b.close : b.close * k + prev * (1 - k);
    prev = v;
    return { time: b.time, value: round2(v) };
  });
}

export function anchoredVwap(bars: Bar[], anchorIndex: number): { time: string; value: number }[] {
  let cumPV = 0;
  let cumV = 0;
  const out: { time: string; value: number }[] = [];
  for (let i = anchorIndex; i < bars.length; i++) {
    const b = bars[i];
    const typical = (b.high + b.low + b.close) / 3;
    cumPV += typical * b.volume;
    cumV += b.volume;
    out.push({ time: b.time, value: round2(cumPV / cumV) });
  }
  return out;
}
