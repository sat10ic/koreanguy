/* Entry-quality contributors, decomposed (manual V2 §5.3: "each bar
   decomposable"). Backend source: unidesk/momentum/scoring/entry_quality.py
   band normalizers — room / RR / extension / trigger-proximity. */
interface Contributor {
  label: string;
  value: number; // 0-100
  detail: string;
}

export function ContributorBars({ contributors }: { contributors: Contributor[] }) {
  return (
    <div className="flex flex-col gap-2">
      {contributors.map((c) => (
        <div key={c.label} className="flex items-center gap-3">
          <span className="w-28 shrink-0 text-caption text-ink-tertiary">{c.label}</span>
          <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-accent transition-[width] duration-300 ease-out"
              style={{ width: `${Math.max(2, Math.min(100, c.value))}%`, opacity: 0.65 }}
            />
          </div>
          <span className="w-20 shrink-0 text-right font-mono-num text-caption text-ink-secondary">{c.detail}</span>
        </div>
      ))}
    </div>
  );
}
