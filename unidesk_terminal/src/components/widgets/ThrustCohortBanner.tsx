import type { Candidate } from "../../data/fixtures";

/*
  ThrustCohortBanner (handoff B-4) — one line, computed from the live report:
  how many candidates have a stop inside 0.75 thrust-days. The flat red
  reading across the cohort is the TRUE finding (stops routinely sit tighter
  than the stock's own ordinary strong-day expansion) — this banner says it
  once, at cohort level, instead of hiding it. Counts are computed from the
  data; nothing here is a literal (B-3: never re-band to spread the colours).
  Hidden entirely when the cohort carries no stop-room data at all.
*/
export function ThrustCohortBanner({ cohort }: { cohort: Candidate[] }) {
  const withData = cohort.filter((c) => c.stopThrustDays != null);
  if (withData.length === 0) return null;
  const inside = withData.filter((c) => (c.stopThrustDays as number) < 0.75);
  if (inside.length === 0) return null;
  return (
    <p className="text-caption text-ink-secondary" title="stop_thrust_days < 0.75 — the entire risk budget fits inside one ordinary strong day's expansion (ADRMAX)">
      <span className="font-semibold text-danger">{inside.length} of {withData.length} candidates</span>
      {" "}have stops inside 0.75 thrust-days — stops are tighter than these stocks' normal daily expansion.
    </p>
  );
}
