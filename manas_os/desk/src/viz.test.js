import { describe, expect, it } from "vitest";
import { colorScale, squarifyTreemap } from "./viz.js";

describe("colorScale", () => {
  it("returns the neutral light chart background for zero", () => {
    const style = colorScale(0);
    expect(style.background).toBe("var(--v5-chart-bg)");
    expect(style.color).toBe("var(--ink-dim)");
  });

  it("returns the neutral background for null/undefined/NaN", () => {
    for (const v of [null, undefined, NaN]) {
      const style = colorScale(v);
      expect(style.background).toBe("var(--v5-chart-bg)");
      expect(style.color).toBe("var(--ink-dim)");
    }
  });

  it("maps positive values to the v5 green rgb + ink token", () => {
    const style = colorScale(2.5);
    expect(style.background).toMatch(/^rgba\(20, 113, 63,/);
    expect(style.color).toBe("var(--positive)");
  });

  it("maps negative values to the v5 red rgb + ink token", () => {
    const style = colorScale(-2.5);
    expect(style.background).toMatch(/^rgba\(173, 44, 52,/);
    expect(style.color).toBe("var(--danger)");
  });

  it("clamps magnitude at capAt so an outlier doesn't exceed max alpha", () => {
    const atCap = colorScale(5, 5);
    const wayOver = colorScale(500, 5);
    expect(wayOver.background).toBe(atCap.background);
  });
});

describe("squarifyTreemap", () => {
  const fixture = [
    { name: "a", size: 40 },
    { name: "b", size: 25 },
    { name: "c", size: 15 },
    { name: "d", size: 12 },
    { name: "e", size: 8 },
  ];

  it("returns rects whose total area sums to ~the container area", () => {
    const rects = squarifyTreemap(fixture, 200, 100);
    expect(rects).toHaveLength(5);
    const totalArea = rects.reduce((sum, r) => sum + r.w * r.h, 0);
    expect(totalArea).toBeCloseTo(200 * 100, 0);
  });

  it("produces non-overlapping rects on the 5-item fixture", () => {
    const rects = squarifyTreemap(fixture, 200, 100);
    for (let i = 0; i < rects.length; i += 1) {
      for (let j = i + 1; j < rects.length; j += 1) {
        const a = rects[i];
        const b = rects[j];
        const overlapX = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
        const overlapY = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
        const overlapArea = overlapX * overlapY;
        expect(overlapArea).toBeLessThan(1e-6);
      }
    }
  });

  it("drops zero/negative-size items and returns [] for empty/invalid input", () => {
    expect(squarifyTreemap([], 200, 100)).toEqual([]);
    expect(squarifyTreemap(fixture, 0, 100)).toEqual([]);
    expect(squarifyTreemap(fixture, 200, 0)).toEqual([]);
    const withZero = squarifyTreemap([...fixture, { name: "z", size: 0 }], 200, 100);
    expect(withZero).toHaveLength(5);
  });
});
