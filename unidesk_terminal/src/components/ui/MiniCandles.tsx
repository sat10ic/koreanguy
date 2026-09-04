/*
  CandidateMiniChart (spec §7.5): real miniature candlestick chart from the
  per-session OHLCV snapshot. ~40 sessions, 104×36, no axes, optional
  trigger line. Real price history only — the caller renders "—" when
  getRealHistory returns undefined; no synthetic shapes (§7.5/§28.2).
*/
interface MiniCandlesProps {
  bars: { open: number; high: number; low: number; close: number }[];
  trigger?: number | null;
  width?: number;
  height?: number;
}

export function MiniCandles({ bars, trigger, width = 104, height = 36 }: MiniCandlesProps) {
  if (!bars || bars.length < 5) return null;
  const shown = bars.slice(-40);
  let lo = Math.min(...shown.map((b) => b.low));
  let hi = Math.max(...shown.map((b) => b.high));
  if (trigger != null) {
    lo = Math.min(lo, trigger);
    hi = Math.max(hi, trigger);
  }
  const range = hi - lo || 1;
  const pad = 2;
  const y = (v: number) => pad + (1 - (v - lo) / range) * (height - pad * 2);
  const step = width / shown.length;
  const bodyW = Math.max(1.5, step * 0.55);

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      {trigger != null && (
        <line x1={0} x2={width} y1={y(trigger)} y2={y(trigger)}
          stroke="var(--accent)" strokeWidth={0.75} strokeDasharray="3 3" opacity={0.7} />
      )}
      {shown.map((b, i) => {
        const x = i * step + step / 2;
        const up = b.close >= b.open;
        const color = up ? "var(--positive)" : "var(--danger)";
        const top = y(Math.max(b.open, b.close));
        const bottom = y(Math.min(b.open, b.close));
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={y(b.high)} y2={y(b.low)} stroke={color} strokeWidth={0.75} opacity={0.7} />
            <rect x={x - bodyW / 2} y={top} width={bodyW} height={Math.max(1, bottom - top)} fill={color} opacity={0.85} />
          </g>
        );
      })}
    </svg>
  );
}
