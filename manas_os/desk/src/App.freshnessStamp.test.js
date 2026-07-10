import { describe, expect, it } from "vitest";
import { computeFreshnessStamp, relativeDayLabel } from "./App.jsx";

describe("relativeDayLabel", () => {
  it("returns 'today' when data_as_of equals today", () => {
    expect(relativeDayLabel("2026-07-10", "2026-07-10")).toBe("today");
  });

  it("returns 'yesterday' when data_as_of is one day behind", () => {
    expect(relativeDayLabel("2026-07-09", "2026-07-10")).toBe("yesterday");
  });

  it("returns 'N days ago' for older data", () => {
    expect(relativeDayLabel("2026-07-06", "2026-07-10")).toBe("4 days ago");
  });

  it("returns 'unknown' when data_as_of is missing", () => {
    expect(relativeDayLabel(null, "2026-07-10")).toBe("unknown");
  });
});

describe("computeFreshnessStamp", () => {
  it("returns null when there is no latest payload yet", () => {
    expect(computeFreshnessStamp(null, "2026-07-10")).toBe(null);
  });

  it("renders the full stamp text and flags amber when data is not from today", () => {
    const latest = {
      data_as_of: "2026-07-09",
      next_update_hint: "today's update pending — press UPDATE or run run_daily_update.bat",
      build_sha: "abc1234",
    };
    const result = computeFreshnessStamp(latest, "2026-07-10");
    expect(result.text).toBe(
      "DATA AS OF 2026-07-09 (yesterday) · today's update pending — press UPDATE or run run_daily_update.bat · build abc1234"
    );
    expect(result.isAmber).toBe(true);
  });

  it("is not amber when data_as_of is today", () => {
    const latest = {
      data_as_of: "2026-07-10",
      next_update_hint: "live market hours — today's data already in; next full update ~19:00 IST",
      build_sha: "def5678",
    };
    const result = computeFreshnessStamp(latest, "2026-07-10");
    expect(result.isAmber).toBe(false);
  });

  it("falls back to 'unknown' for missing build_sha and data_as_of", () => {
    const result = computeFreshnessStamp({ next_update_hint: "market closed — data through 2026-07-10" }, "2026-07-11");
    expect(result.text).toBe(
      "DATA AS OF unknown (unknown) · market closed — data through 2026-07-10 · build unknown"
    );
  });
});
