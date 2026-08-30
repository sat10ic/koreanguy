import { useMode } from "../../lib/ModeContext";
import { scoreColor } from "../../lib/status";

/*
  W1 — the "Ignition Stack" (signature widget, carried from V1 §17/§9.3 into
  V2 — manual V2 §0 explicitly keeps this one).

  Intent:     A desk reader deciding, tonight, whether a candidate is worth
              opening. Must answer "stock vs setup vs entry" in one glance.
  Hierarchy:  The three bands share one frame so they read as ONE instrument;
              the composite needle is the highest-contrast element — what the
              eye lands on first, per-band numbers second.
  Palette:    Fill color is the score-tone scale (positive/score-mid/danger —
              deliberately NOT warning-amber for the middle band, so a 60
              doesn't read as "caution"; amber stays reserved for the warning
              semantic elsewhere). Frame/ticks stay neutral.
  Depth:      Borders-only capsule, no shadow.
  Typography: mono tabular numerals for scores; V2 §8 vocabulary — beginner
              labels by default ("Stock Strength" not "Stock Quality"), a
              title attr carries the one-line glossary hint (I4).
  Spacing:    4px grid; bands separated by a 1px hairline, so the capsule
              reads as fused rather than three stacked cards.
*/

interface Band {
  key: string;
  labelBeginner: string;
  labelPro: string;
  hint: string;
  value: number; // 0-100
}

interface QualityStackProps {
  stock: number;
  setup: number;
  entry: number;
  size?: "compact" | "full";
  mode?: "beginner" | "pro";
}

const TICKS = [25, 50, 75];

export function QualityStack({ stock, setup, entry, size = "compact", mode }: QualityStackProps) {
  const { mode: contextMode } = useMode();
  const effectiveMode = mode ?? contextMode;
  const bands: Band[] = [
    { key: "stock", labelBeginner: "Stock Strength", labelPro: "Stock Quality", hint: "Overall leadership and trend quality", value: stock },
    { key: "setup", labelBeginner: "Setup", labelPro: "Setup Quality", hint: "How clean the pattern/setup is", value: setup },
    { key: "entry", labelBeginner: "Entry Timing", labelPro: "Entry Quality", hint: "Whether the current price is attractive", value: entry },
  ];
  const composite = (stock + setup + entry) / 3;
  const rowH = size === "compact" ? 20 : 26;

  return (
    <div className="relative w-full">
      <div className="relative overflow-hidden rounded-chip border border-border bg-surface-2">
        {/* shared tick guides */}
        <div className="pointer-events-none absolute inset-0 z-10">
          {TICKS.map((t) => (
            <div key={t} className="absolute top-0 bottom-0 w-px bg-border" style={{ left: `${t}%` }} />
          ))}
        </div>
        {/* composite needle */}
        <div
          className="pointer-events-none absolute top-0 bottom-0 z-20 w-0.5 bg-ink-primary"
          style={{ left: `${composite}%`, opacity: 0.85 }}
        />

        {bands.map((band, i) => (
          <div
            key={band.key}
            title={band.hint}
            className="relative flex items-center justify-between px-2"
            style={{
              height: rowH,
              borderTop: i === 0 ? undefined : "1px solid var(--border-subtle)",
            }}
          >
            <div
              className="absolute inset-y-0 left-0 transition-[width] duration-300 ease-out"
              style={{ width: `${band.value}%`, background: scoreColor(band.value), opacity: 0.28 }}
            />
            <div
              className="absolute inset-y-0 w-px transition-[left] duration-300 ease-out"
              style={{ left: `${band.value}%`, background: scoreColor(band.value), opacity: 0.7 }}
            />
            <span className="relative z-10 truncate pr-2 text-caption font-medium uppercase tracking-normal text-ink-secondary">
              {effectiveMode === "beginner" ? band.labelBeginner : band.labelPro}
            </span>
            <span
              className="relative z-10 shrink-0 font-mono-num text-caption font-semibold"
              style={{ color: scoreColor(band.value) }}
            >
              {Math.round(band.value)}
            </span>
          </div>
        ))}
      </div>
      {size === "full" && (
        <div className="mt-1.5 flex items-center justify-between px-0.5">
          <span className="text-caption text-ink-muted">Composite</span>
          <span className="font-mono-num text-caption font-semibold text-ink-secondary">
            {composite.toFixed(0)}
          </span>
        </div>
      )}
    </div>
  );
}
