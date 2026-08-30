import { Sparkline } from "../ui/Sparkline";
import type { REGIME } from "../../data/fixtures";

/* A — Regime Strip (manual V2 §3.A). BULL/BEAR/CHOP + breadth mini-bars
   (above 50/200 DMA, near highs/lows). Folds V1's separate Market tab into
   one strip, per V2 §10. */
const REGIME_TONE: Record<string, string> = {
  BULL: "var(--positive)",
  BEAR: "var(--danger)",
  CHOP: "var(--score-mid)",
};

interface RegimeStripProps {
  regime: typeof REGIME;
}

export function RegimeStrip({ regime }: RegimeStripProps) {
  const color = REGIME_TONE[regime.label] ?? "var(--neutral)";
  const bars = [
    { label: "Above EMA50", pct: regime.aboveEma50Pct },
    { label: "Above EMA21", pct: regime.aboveEma21Pct },
    { label: "Near 52w highs", pct: regime.nearHighsPct },
    { label: "Near 52w lows", pct: regime.nearLowsPct },
  ];

  return (
    <div className="rounded-card border border-border bg-surface-1 p-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          <span className="text-h3 font-semibold" style={{ color }}>
            {regime.label}
          </span>
          <span className="text-caption text-ink-tertiary">{regime.sessions} sessions</span>
        </div>
        <Sparkline values={regime.breadthSpark} width={80} height={24} color={color} fill />
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2">
        {bars.map((b) => (
          <div key={b.label} className="rounded-chip border border-border-subtle bg-surface-2 px-2 py-1.5">
            <div className="text-caption text-ink-muted">{b.label}</div>
            <div className="font-mono-num text-body font-semibold text-ink-primary">{b.pct.toFixed(1)}%</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-caption text-ink-muted" title={regime.source}>
        Market mood — {regime.source}
      </p>
    </div>
  );
}
