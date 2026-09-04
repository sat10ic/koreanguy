const REGIME_TONE: Record<string, string> = {
  BULL: "var(--positive)",
  BEAR: "var(--danger)",
  CHOP: "var(--score-mid)",
};

interface RegimeStripProps {
  regimeBuilt: boolean;
  regimeNote: string;
}

// H1-01: the regime headline is the page anchor — largest element on Home 1,
// text matches honesty_footer.regime_note exactly (no paraphrase).
export function RegimeStrip({ regimeBuilt, regimeNote }: RegimeStripProps) {
  let regimeLabel = "unknown";
  if (regimeBuilt && regimeNote) {
    const firstWord = regimeNote.split(/[ (—]/)[0];
    if (["BULL", "BEAR", "CHOP"].includes(firstWord)) regimeLabel = firstWord;
  }
  const color = REGIME_TONE[regimeLabel] ?? "var(--neutral)";

  return (
    <div className="rounded-card border border-border bg-surface-1 px-4 py-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <span className="text-display font-bold leading-none tracking-tight" style={{ color }}>
            {regimeLabel}
          </span>
          <span className="text-caption text-ink-tertiary">market regime</span>
        </div>
      </div>
      <p className="mt-2 max-w-3xl text-body text-ink-secondary">{regimeNote}</p>
    </div>
  );
}
