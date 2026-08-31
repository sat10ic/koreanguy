import { useMemo } from "react";
import { TONIGHT_REPORT } from "../data/tonight";

/**
 * AIRTIGHT RULE 1 — Single session authority.
 *
 * Returns the ONE authoritative session date for the entire app.
 * Every screen, every component, every data point MUST derive from this.
 * If a screen shows data from a different date, that's a defect.
 *
 * The session comes from the report JSON's `session_date` field,
 * emitted by the pipeline at scan time. Never from fixtures, never
 * from a hardcoded string, never from a stale import.
 */
export function useSessionDate(): string {
  return useMemo(() => TONIGHT_REPORT.session_date, []);
}

/**
 * AIRTIGHT RULE 2 — Vintage check.
 *
 * Given a data origin (screen name + source description), verify
 * that its session date matches the app's authoritative session date.
 * Returns null if coherent, or a description of the mismatch if not.
 *
 * Example: if a component displays "Regime: BULL" but its data was
 * computed from a July 3 fixture while the report is Aug 31, this
 * returns a descriptive warning.
 */
export function checkVintage(
  label: string,
  dataSessionDate: string | null | undefined,
): string | null {
  const appDate = TONIGHT_REPORT.session_date;
  if (!dataSessionDate) {
    return `${label}: no vintage stamp — cannot verify freshness`;
  }
  if (dataSessionDate !== appDate) {
    return `${label}: data is from ${dataSessionDate} but the current report is ${appDate} — STALE`;
  }
  return null;
}

/**
 * AIRTIGHT RULE 3 — Grain disclosure.
 *
 * Every count displayed in the UI must state what it's counting.
 * "40 candidates" is ambiguous. "40 candidates (40 distinct symbols)"
 * or "40 candidates (symbol×detector)" is honest.
 */
export function grainLabel(
  count: number,
  unit: string,
  distinct?: number,
): string {
  if (distinct !== undefined && distinct !== count) {
    return `${count} ${unit} (${distinct} distinct)`;
  }
  return `${count} ${unit}`;
}