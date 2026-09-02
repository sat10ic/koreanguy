import { useMode } from "../../lib/ModeContext";
import { scoreColor } from "../../lib/status";

/*
  W1 — the "Ignition Stack" (signature widget, carried from V1 §17/§9.3 into
  V2 — manual V2 §0 explicitly keeps this one).

  H2-05 contract (2026-09-01): a band whose score was never computed renders
  "—" with no fill bar — never 0, never a blank label. The composite needle
  appears only when all three scores exist; coverage % and named unknowns
  are shown beside each score in Pro so a 97.9 at 85% coverage reads as
  partial evidence, not a confident verdict.
*/

interface Band {
  key: string;
  labelBeginner: string;
  labelPro: string;
  hint: string;
  value: number | null; // null = not computed; never coerced to 0
  coverage?: number | null;
  unknowns?: string[];
}

interface QualityStackProps {
  stock: number | null | undefined;
  setup: number | null | undefined;
  entry: number | null | undefined;
  size?: "compact" | "full";
  mode?: "beginner" | "pro";
  // H2-05 Pro detail (coverage/unknowns per band)
  coverage?: { stock?: number | null; setup?: number | null; entry?: number | null };
  unknowns?: { stock?: string[]; setup?: string[]; entry?: string[] };
}

const TICKS = [25, 50, 75];

export function QualityStack({ stock, setup, entry, size = "compact", mode, coverage, unknowns }: QualityStackProps) {
  const { mode: contextMode } = useMode();
  const effectiveMode = mode ?? contextMode;
  const isPro = effectiveMode === "pro";
  const bands: Band[] = [
    { key: "stock", labelBeginner: "Stock Strength", labelPro: "Stock Quality", hint: "Overall leadership and trend quality", value: stock ?? null, coverage: coverage?.stock, unknowns: unknowns?.stock },
    { key: "setup", labelBeginner: "Setup", labelPro: "Setup Quality", hint: "How clean the pattern/setup is", value: setup ?? null, coverage: coverage?.setup, unknowns: unknowns?.setup },
    { key: "entry", labelBeginner: "Entry Timing", labelPro: "Entry Quality", hint: "Whether the current price is attractive", value: entry ?? null, coverage: coverage?.entry, unknowns: unknowns?.entry },
  ];
  const allScored = bands.every((b) => b.value != null);
  const composite = allScored
    ? bands.reduce((s, b) => s + (b.value as number), 0) / 3
    : null;
  const rowH = size === "compact" ? 20 : 26;

  return (
    <div className="relative w-full">
      <div className="relative overflow-hidden rounded-chip border border-border bg-surface-2">
        <div className="pointer-events-none absolute inset-0 z-10">
          {TICKS.map((t) => (
            <div key={t} className="absolute top-0 bottom-0 w-px bg-border" style={{ left: `${t}%` }} />
          ))}
        </div>
        {composite != null && (
          <div
            className="pointer-events-none absolute top-0 bottom-0 z-20 w-0.5 bg-ink-primary"
            style={{ left: `${composite}%`, opacity: 0.85 }}
          />
        )}

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
            {band.value != null && (
              <>
                <div
                  className="absolute inset-y-0 left-0 transition-[width] duration-300 ease-out"
                  style={{ width: `${band.value}%`, background: scoreColor(band.value), opacity: 0.28 }}
                />
                <div
                  className="absolute inset-y-0 w-px transition-[left] duration-300 ease-out"
                  style={{ left: `${band.value}%`, background: scoreColor(band.value), opacity: 0.7 }}
                />
              </>
            )}
            <span className="relative z-10 truncate pr-2 text-caption font-medium uppercase tracking-normal text-ink-secondary">
              {isPro ? band.labelPro : band.labelBeginner}
              {isPro && band.coverage != null && (
                <span className="ml-1.5 normal-case text-ink-muted">@{(band.coverage * 100).toFixed(0)}%</span>
              )}
              {isPro && band.unknowns && band.unknowns.length > 0 && (
                <span className="ml-1 text-warning" title={"unknowns: " + band.unknowns.join(", ")}>
                  ?{band.unknowns.length}
                </span>
              )}
            </span>
            <span
              className="relative z-10 shrink-0 font-mono-num text-caption font-semibold"
              style={{ color: band.value != null ? scoreColor(band.value) : "var(--text-muted)" }}
            >
              {band.value != null ? Math.round(band.value) : "—"}
            </span>
          </div>
        ))}
      </div>
      {size === "full" && (
        <div className="mt-1.5 flex items-center justify-between px-0.5">
          <span className="text-caption text-ink-muted">Composite</span>
          <span className="font-mono-num text-caption font-semibold text-ink-secondary">
            {composite != null ? composite.toFixed(0) : "—"}
          </span>
        </div>
      )}
    </div>
  );
}
