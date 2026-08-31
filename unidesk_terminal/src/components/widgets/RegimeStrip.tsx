import { VintageBadge } from "../ui/VintageBadge";
import type { REGIME } from "../../data/fixtures";
import { TONIGHT_REPORT } from "../../data/tonight";

/* A — Regime Strip (manual V2 §3.A). BULL/BEAR/CHOP + breadth mini-bars.
   AIRTIGHT RULE 1: single session authority — the real regime note from the
   pipeline JSON overrides the stale fixture label. */
const REGIME_TONE: Record<string, string> = {
  BULL: "var(--positive)",
  BEAR: "var(--danger)",
  CHOP: "var(--score-mid)",
};

interface RegimeStripProps {
  regime: typeof REGIME;
  regimeBuilt?: boolean;
  regimeNote?: string;
}

export function RegimeStrip({ regime, regimeBuilt = true, regimeNote }: RegimeStripProps) {
  let regimeLabel: string = regime.label;
  let regimeSource = regime.source;
  let regimeSessions = regime.sessions;

  if (regimeBuilt && regimeNote) {
    const firstWord = regimeNote.split(/[ (—]/)[0];
    if (["BULL", "BEAR", "CHOP"].includes(firstWord)) {
      regimeLabel = firstWord;
    }
    regimeSource = regimeNote;
    regimeSessions = 0;
  }

  const color = REGIME_TONE[regimeLabel] ?? "var(--neutral)";
  const bars = [
    { label: "Above EMA50", pct: regime.aboveEma50Pct },
    { label: "Above EMA21", pct: regime.aboveEma21Pct },
    { label: "Near 52w highs", pct: regime.nearHighsPct },
    { label: "Near 52w lows", pct: regime.nearLowsPct },
  ];

  return (
    <div className="rounded-card border border-border bg-surface-1 p-3.5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          <span className="text-h3 font-semibold" style={{ color }}>
            {regimeLabel}
          </span>
          {regimeSessions > 0 && (
            <span className="text-caption text-ink-tertiary">{regimeSessions} sessions</span>
          )}
        </div>
        <VintageBadge
          label="Regime"
          sessionDate={TONIGHT_REPORT.session_date}
          appDate={TONIGHT_REPORT.session_date}
        />
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
        Market mood — {regimeSource}
      </p>
    </div>
  );
}