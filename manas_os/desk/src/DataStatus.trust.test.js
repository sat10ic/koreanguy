import { describe, expect, it } from "vitest";
import { trustTone } from "./DataStatus.jsx";

// USABILITY_UX_AUDIT_2026-07-19.md defect #9: operational/data/model/build
// statuses competed for attention with no single trust verdict. trustTone
// maps the server-computed word (api/app.py _compute_trust_verdict) to the
// CSS tone the popover's one-line banner renders.

describe("trustTone", () => {
  it("maps each known verdict to its tone", () => {
    expect(trustTone("TRUSTED")).toBe("trusted");
    expect(trustTone("DEGRADED")).toBe("degraded");
    expect(trustTone("STALE")).toBe("stale");
  });

  it("falls back to unknown for anything else", () => {
    expect(trustTone(undefined)).toBe("unknown");
    expect(trustTone(null)).toBe("unknown");
    expect(trustTone("weird")).toBe("unknown");
  });
});
