import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { GLOSSARY, GLOSSARY_KEYS } from "./glossary.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TOUCHED_FILES = [
  "App.jsx", "DeskTab.jsx", "DebateTab.jsx",
  // SHIP-1 #18: glossary density pass extended coverage to POSITIONS/LEDGER/MARKET.
  "PositionsTab.jsx", "LedgerTab.jsx", "MarketTab.jsx",
];

function literalTermKeys(source) {
  return [...source.matchAll(/<Term\s+[^>]*k="([^"]+)"/g)].map((match) => match[1]);
}

describe("glossary", () => {
  it("has complete entries for every literal Term usage in touched files", () => {
    const keys = new Set();
    for (const file of TOUCHED_FILES) {
      const source = readFileSync(join(__dirname, file), "utf8");
      for (const key of literalTermKeys(source)) keys.add(key);
    }
    for (const key of keys) {
      expect(GLOSSARY, `${key} is missing`).toHaveProperty(key);
    }
  });

  it("keeps every glossary entry beginner-facing", () => {
    expect(GLOSSARY_KEYS.length).toBe(Object.keys(GLOSSARY).length);
    for (const key of GLOSSARY_KEYS) {
      expect(GLOSSARY[key].label, `${key} label`).toEqual(expect.any(String));
      expect(GLOSSARY[key].plain, `${key} plain`).toEqual(expect.any(String));
      expect(GLOSSARY[key].care, `${key} care`).toEqual(expect.any(String));
      expect(GLOSSARY[key].plain.trim()).toMatch(/[.!?]$/);
      expect(GLOSSARY[key].care.trim()).toMatch(/[.!?]$/);
    }
  });
});
