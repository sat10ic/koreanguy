import { describe, expect, it } from "vitest";
import {
  formatDisplayFloat,
  humanizeShortlistReason,
  newHighsLowsCopy,
} from "./presentation.js";

describe("formatDisplayFloat", () => {
  it("rounds visible floats to one or two decimals and keeps the unit", () => {
    expect(formatDisplayFloat(0.8052299365389679, { digits: 2, unit: "x" })).toBe("0.81x");
    expect(formatDisplayFloat(0, { digits: 1, unit: "%" })).toBe("0.0%");
    expect(formatDisplayFloat(101.236, { digits: 2, prefix: "₹" })).toBe("₹101.24");
  });

  it("uses an em dash for missing and invalid values", () => {
    expect(formatDisplayFloat(null, { unit: "%" })).toBe("—");
    expect(formatDisplayFloat("not-a-number", { unit: "%" })).toBe("—");
  });
});

describe("humanizeShortlistReason", () => {
  it("replaces truncated allowed-family dumps with a plain sentence", () => {
    expect(humanizeShortlistReason("held for current regime (allowed: ['base/pattern', 'momentum'"))
      .toBe("Held for the current market posture.");
  });
});

describe("newHighsLowsCopy", () => {
  it("uses beginner copy for the four-percent-moves proxy", () => {
    expect(newHighsLowsCopy(-4, "up_4pct-down_4pct (NH/NL not ingested; proxy)"))
      .toBe("New highs vs lows: -4 (proxy from 4% moves)");
  });
});
