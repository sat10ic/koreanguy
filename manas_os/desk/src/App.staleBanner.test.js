import { describe, expect, it } from "vitest";
import { computeFreshnessBanner, beginnerRunFailedCopy } from "./App.jsx";

describe("computeFreshnessBanner", () => {
  it("returns null when there is no card", () => {
    expect(computeFreshnessBanner(null, null, "2026-07-10")).toBe(null);
  });

  it("returns null when the card is not available", () => {
    expect(computeFreshnessBanner(null, { available: false }, "2026-07-10")).toBe(null);
  });

  it("shows the STALE banner for a no_op card, keyed on scan_date", () => {
    const card = {
      available: true,
      no_op: true,
      run_date: "2026-07-10",
      scan_date: "2026-07-09",
      pipeline: [],
    };
    expect(computeFreshnessBanner(null, card, "2026-07-10")).toMatchObject({
      state: "awaiting_tonight",
      text: "STALE — showing last completed night 2026-07-09",
    });
  });

  it("falls back to run_date for the no_op banner when scan_date is missing", () => {
    const card = { available: true, no_op: true, run_date: "2026-07-10", scan_date: null };
    expect(computeFreshnessBanner(null, card, "2026-07-10").text).toBe("STALE — showing last completed night 2026-07-10");
  });

  it("returns null for a completed, non-no_op night with no failed stages", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "agents_debate", status: "ok" }],
    };
    expect(computeFreshnessBanner({ data_as_of: "2026-07-09", build_sha: "abc" }, card, "2026-07-09").state).toBe("fresh");
  });

  it("reports an incomplete night when a pipeline stage failed and no_op is false", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "agents_debate", status: "fail" }],
    };
    expect(computeFreshnessBanner(null, card, "2026-07-10")).toMatchObject({
      state: "run_failed",
      reason: "agents debate failed",
    });
  });

  it("treats a 'skip' stage as normal and does not flag it as incomplete", () => {
    const card = {
      available: true,
      no_op: false,
      run_date: "2026-07-09",
      scan_date: "2026-07-09",
      pipeline: [{ stage: "mars", status: "skip" }],
    };
    expect(computeFreshnessBanner({ data_as_of: "2026-07-09" }, card, "2026-07-10").state).toBe("awaiting_tonight");
  });

  it("lets a failed run override the awaiting-tonight hint", () => {
    const latest = { data_as_of: "2026-07-09", next_update_hint: "today's update expected ~19:00 IST" };
    const card = {
      available: true,
      scan_date: "2026-07-09",
      pipeline: [{ stage: "agents_debate", status: "fail", detail: "HTTP 429" }],
      council_status: { state: "run_failed", reason: "model errors" },
    };
    const banner = computeFreshnessBanner(latest, card, "2026-07-10");
    expect(banner.state).toBe("run_failed");
    expect(banner.text).not.toContain("expected ~19:00");
  });
});

// Cold-start audit defect 1: beginner must see the same run_failed banner as
// expert (never hidden), just in plainer language.
describe("beginnerRunFailedCopy", () => {
  it("names the debate stage in plain language", () => {
    expect(beginnerRunFailedCopy("agents debate failed")).toBe(
      "Last night's analysis partly failed (debate stage). Tonight's picks may be incomplete."
    );
  });

  it("falls back to a generic pipeline-stage note for an unrecognized reason", () => {
    expect(beginnerRunFailedCopy("some other stage failed")).toBe(
      "Last night's analysis partly failed (a pipeline stage). Tonight's picks may be incomplete."
    );
  });

  it("handles a missing reason without throwing", () => {
    expect(beginnerRunFailedCopy(null)).toBe(
      "Last night's analysis partly failed (a pipeline stage). Tonight's picks may be incomplete."
    );
  });
});
