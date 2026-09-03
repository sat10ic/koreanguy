// E-4/F-3: loading skeleton for the now-async desk data load. A pulsing
// placeholder beats a blank screen; it names what is loading so a hang is
// diagnosable rather than mysterious.
export function Skeleton({ label }: { label?: string }) {
  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center gap-3 bg-surface-0" role="status">
      <div className="h-8 w-56 animate-pulse rounded-btn bg-surface-2" />
      <div className="h-4 w-80 animate-pulse rounded-btn bg-surface-1" />
      <div className="h-4 w-72 animate-pulse rounded-btn bg-surface-1" />
      {label && <p className="mt-2 text-caption text-ink-tertiary">{label}</p>}
    </div>
  );
}
