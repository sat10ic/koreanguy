import { VintageBadge } from "../ui/VintageBadge";
import { TONIGHT_REPORT } from "../../data/tonight";

const REGIME_TONE: Record<string, string> = {
  BULL: "var(--positive)",
  BEAR: "var(--danger)",
  CHOP: "var(--score-mid)",
};

interface RegimeStripProps {
  regimeBuilt: boolean;
  regimeNote: string;
  pctAboveEma50?: number | null;
  nearHighsPct?: number | null;
  nearLowsPct?: number | null;
}

export function RegimeStrip({ regimeBuilt, regimeNote, pctAboveEma50, nearHighsPct, nearLowsPct }: RegimeStripProps) {
  let regimeLabel = "unknown";
  if (regimeBuilt && regimeNote) {
    const firstWord = regimeNote.split(/[ (—]/)[0];
    if (["BULL", "BEAR", "CHOP"].includes(firstWord)) {
      regimeLabel = firstWord;
    }
  }
  const color = REGIME_TONE[regimeLabel] ?? "var(--neutral)";
  const bars = [
    { label: "Above EMA50", pct: pctAboveEma50 ?? 0 },
    { label: "Near 52w highs", pct: nearHighsPct ?? 0 },
    { label: "Near 52w lows", pct: nearLowsPct ?? 0 },
  ];

  return (
    <div className="rounded-card border border-border bg-surface-1 p-3.5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          <span className="text-h3 font-semibold" style={{ color }}>{regimeLabel}</span>
        </div>
        <VintageBadge label="Regime" sessionDate={TONIGHT_REPORT.session_date} appDate={TONIGHT_REPORT.session_date} />
      </div>
      <p className="text-caption text-ink-secondary mb-2">{regimeNote}</p>
      <div className="grid grid-cols-3 gap-2">
        {bars.map((b) => (
          <div key={b.label} className="rounded-chip border border-border-subtle bg-surface-2 px-2 py-1.5">
            <div className="text-caption text-ink-muted">{b.label}</div>
            <div className="font-mono-num text-body font-semibold text-ink-primary">{b.pct.toFixed(1)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}