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
  // Real honesty_footer facts (report_json.py). When regimeBuilt is false —
  // true today, 2026-08-28 report: honesty_footer.regime_built === false —
  // the real classifier hasn't run, so the strip leads with that fact
  // instead of a colored BULL/BEAR/CHOP badge, and demotes the fixture
  // regime numbers below into a clearly-labelled illustrative preview.
  regimeBuilt?: boolean;
  regimeNote?: string;
}

export function RegimeStrip({ regime, regimeBuilt = true, regimeNote }: RegimeStripProps) {
  const color = REGIME_TONE[regime.label] ?? "var(--neutral)";
  const bars = [
    { label: "Above EMA50", pct: regime.aboveEma50Pct },
    { label: "Above EMA21", pct: regime.aboveEma21Pct },
    { label: "Near 52w highs", pct: regime.nearHighsPct },
    { label: "Near 52w lows", pct: regime.nearLowsPct },
  ];

  if (!regimeBuilt) {
    return (
      <div className="rounded-card border border-border bg-surface-1 p-3.5">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full bg-ink-muted" />
          <span className="text-h3 font-semibold text-ink-secondary">Regime not built yet</span>
        </div>
        {regimeNote && <p className="mt-1.5 text-caption text-ink-tertiary">{regimeNote}</p>}

        <div className="mt-3 rounded-chip border border-dashed border-border-subtle bg-surface-2 p-2.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wide text-ink-muted">
              Illustrative preview — not the real classifier
            </span>
            <span className="text-h4 font-semibold" style={{ color, opacity: 0.6 }}>
              {regime.label}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2 opacity-60">
            {bars.map((b) => (
              <div key={b.label} className="rounded-chip border border-border-subtle bg-surface-1 px-2 py-1.5">
                <div className="text-caption text-ink-muted">{b.label}</div>
                <div className="font-mono-num text-body font-semibold text-ink-primary">{b.pct.toFixed(1)}%</div>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-caption text-ink-muted" title={regime.source}>
            {regime.source}
          </p>
        </div>
      </div>
    );
  }

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
