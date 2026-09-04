import { describe, expect, it } from "vitest";
import { coachWhyText, importedAccountLabel, resolveActionSentence } from "./PositionsTab.jsx";

// USABILITY_UX_AUDIT_2026-07-19.md defect #4: the MANAGE card badge said
// "EXIT NOW" while a separate coach line said "near the close" -- two
// conflicting timing instructions. resolveActionSentence/coachWhyText are
// the frontend's single point of truth for that text: they must prefer the
// server-composed action_sentence over any other field, and never let an
// LLM narrative (advisor_note) restate timing for an urgent/EXIT position.

describe("resolveActionSentence", () => {
  it("prefers action_sentence over the legacy action_line", () => {
    const position = { action_sentence: "EXIT today near the close (15:00-15:25) - sell at market.", action_line: "EXIT TODAY - old text." };
    expect(resolveActionSentence(position)).toBe("EXIT today near the close (15:00-15:25) - sell at market.");
  });

  it("falls back to action_line when action_sentence is absent", () => {
    const position = { action_line: "HOLD - do nothing." };
    expect(resolveActionSentence(position)).toBe("HOLD - do nothing.");
  });

  it("returns null when neither field is present", () => {
    expect(resolveActionSentence({})).toBe(null);
  });
});

describe("coachWhyText", () => {
  it("uses the single action sentence for an urgent position and ignores advisor_note", () => {
    const position = {
      urgent: true,
      coach_verdict: "EXIT",
      action_sentence: "EXIT today near the close (15:00-15:25) - sell the full position at market.",
      advisor_note: "Hold, thesis still intact.", // would contradict the exit if it won
    };
    expect(coachWhyText(position)).toBe(
      "EXIT today near the close (15:00-15:25) - sell the full position at market."
    );
  });

  it("uses the single action sentence when coach_verdict is EXIT even if urgent is falsy", () => {
    const position = {
      urgent: false,
      coach_verdict: "EXIT",
      action_sentence: "EXIT today near the close (15:00-15:25) - sell the full position at market.",
      advisor_note: "some other narrative",
    };
    expect(coachWhyText(position)).toBe(
      "EXIT today near the close (15:00-15:25) - sell the full position at market."
    );
  });

  it("prefers the LLM narrative for a non-urgent HOLD position", () => {
    const position = {
      urgent: false,
      coach_verdict: "HOLD",
      action_sentence: "HOLD today - do nothing; stop stays at 95.",
      advisor_note: "Thesis intact, demand still absorbing supply.",
    };
    expect(coachWhyText(position)).toBe("Thesis intact, demand still absorbing supply.");
  });

  it("falls back to the action sentence when there is no advisor note", () => {
    const position = { urgent: false, coach_verdict: "HOLD", action_sentence: "HOLD today - do nothing." };
    expect(coachWhyText(position)).toBe("HOLD today - do nothing.");
  });

  it("reports honestly when nothing is available", () => {
    expect(coachWhyText({})).toBe("Coach read unavailable for this position (no priced sessions yet).");
  });
});

describe("importedAccountLabel", () => {
  it("returns the server-provided account label", () => {
    expect(importedAccountLabel({ account: "Zerodha (FOU446)" })).toBe("Zerodha (FOU446)");
  });

  it("reports account unknown when the field is missing", () => {
    expect(importedAccountLabel({})).toBe("account unknown");
    expect(importedAccountLabel(null)).toBe("account unknown");
  });
});
