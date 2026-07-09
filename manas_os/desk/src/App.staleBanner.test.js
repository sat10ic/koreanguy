import { describe, expect, it } from "vitest";
import { computeStaleBanner } from "./App.jsx";

describe("computeStaleBanner", () => {
  it("returns null when there is no card", () => {
    expect(computeStaleBanner(null)).toBe(null);
  });

  it("returns null when the card is not available", () => {
    expect(computeStaleBanner({ available: false })).toBe(null);
  });

  it("shows the STALE banner for a no_op card, keyed on scan_date", () => {
    const card = {
      available: true,
      no_op: true,
      run_date: "2026-07-10",
      scan_date: "2026-07-09",
      pipeline: [],
    };
    expect(computeStaleBanner(card)).toBe(
      "STALE — showing last completed night 2026-07-09"
    );
  });

  it("falls back to run_date for the no_op banner when scan_date is missing", () => {
    const card = { available: true, no_op: true, run_date: "2026-07-10", scan_date: null };
    expect(computeStaleBanner(card)).toBe("STALE — showing last completed night 2026-07-10");
  });

  it("returns null for a completed, non-no_op night with no failed stages", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "agents_debate", status: "ok" }],
    };
    expect(computeStaleBanner(card)).toBe(null);
  });

  it("reports an incomplete night when a pipeline stage failed and no_op is false", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "agents_debate", status: "fail" }],
    };
    expect(computeStaleBanner(card)).toBe(
      "Data fresh only through 2026-07-09 — last night's run did not complete."
    );
  });

  it("treats a 'skip' stage as normal and does not flag it as incomplete", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "mars", status: "skip" }],
    };
    expect(computeStaleBanner(card)).toBe(null);
  });
});
