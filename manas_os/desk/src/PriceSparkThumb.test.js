import { describe, expect, it } from "vitest";

import { pointsFor } from "./PriceSparkThumb.jsx";

describe("PriceSparkThumb", () => {
  it("builds a real close-price polyline from chart-data bars", () => {
    const points = pointsFor([{ close: 100 }, { close: 103 }, { close: 101 }]);
    expect(points.split(" ")).toHaveLength(3);
    expect(points).toContain("0.0,");
    expect(points).toContain("120.0,");
  });

  it("does not invent a chart for insufficient data", () => {
    expect(pointsFor([{ close: 100 }])).toBe("");
  });
});
