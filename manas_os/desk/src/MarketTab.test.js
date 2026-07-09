import { describe, expect, it } from "vitest";
import { sectorsUpTitle, rankDealsByMcap, isPropDeskCounterparty } from "./MarketTab.jsx";

describe("sectorsUpTitle (SHIP-1 #11)", () => {
  it("labels 'Sectors up' when at least one sector is positive", () => {
    const rows = [{ move_pct: 1.2 }, { move_pct: -0.4 }];
    expect(sectorsUpTitle(rows)).toBe("Sectors up");
  });

  it("relabels 'Least down' when every sector is negative (all-red day)", () => {
    const rows = [{ move_pct: -0.4 }, { move_pct: -1.1 }, { move_pct: -0.05 }];
    expect(sectorsUpTitle(rows)).toBe("Least down");
  });

  it("labels 'no sectors up today' when the list is empty", () => {
    expect(sectorsUpTitle([])).toBe("no sectors up today");
    expect(sectorsUpTitle(null)).toBe("no sectors up today");
  });

  it("treats a zero move as not-negative (still 'Sectors up')", () => {
    const rows = [{ move_pct: 0 }, { move_pct: -0.4 }];
    expect(sectorsUpTitle(rows)).toBe("Sectors up");
  });
});

describe("rankDealsByMcap (SHIP-1 #14)", () => {
  it("ranks deals with pct_of_mcap desc, ahead of any null-pct deals", () => {
    const deals = [
      { symbol: "A", pct_of_mcap: 0.5, trade_date: "2026-07-01" },
      { symbol: "B", pct_of_mcap: null, trade_date: "2026-07-05" },
      { symbol: "C", pct_of_mcap: 2.1, trade_date: "2026-07-02" },
      { symbol: "D", pct_of_mcap: null, trade_date: "2026-07-03" },
    ];
    const ranked = rankDealsByMcap(deals);
    expect(ranked.map((d) => d.symbol)).toEqual(["C", "A", "B", "D"]);
  });

  it("handles an empty/undefined list", () => {
    expect(rankDealsByMcap([])).toEqual([]);
    expect(rankDealsByMcap(undefined)).toEqual([]);
  });
});

describe("isPropDeskCounterparty (SHIP-1 #14)", () => {
  it("matches known prop-desk/HFT names case-insensitively as substrings", () => {
    expect(isPropDeskCounterparty("Graviton Research Capital LLP")).toBe(true);
    expect(isPropDeskCounterparty("alphagrep securities")).toBe(true);
    expect(isPropDeskCounterparty("TOWER RESEARCH CAPITAL")).toBe(true);
  });

  it("does not match unrelated names", () => {
    expect(isPropDeskCounterparty("Foo Fund")).toBe(false);
    expect(isPropDeskCounterparty(null)).toBe(false);
    expect(isPropDeskCounterparty("")).toBe(false);
  });
});
