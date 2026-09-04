import React from "react";
import { bandFor } from "./bands.js";

// v5 primitive: small status chip used in the CommandStrip and elsewhere.
// tone: "green" | "amber" | "red" | "neutral" (default neutral -> no dot color override)
// qual: italic "qualitative" value styling for values that are not a hard number
//
// `band` (new): a reference band from ./bands.js. Pass it and the chip grades
// itself -- it colours the dot AND prints a one-word read after the number
// ("48.9 neutral", "20.3 weak"). Without it a beginner sees a bare figure with
// nothing to compare against, which is the "graphs don't teach how to read
// them" complaint. `raw` is the numeric value to grade when `value` is a
// preformatted string; omit it and the chip parses `value`.
export default function StatusChip({
  label, value, tone = "neutral", qual = false, title, dot = true, band = null, raw = undefined,
}) {
  const graded = band
    ? bandFor(raw !== undefined ? raw : parseFloat(String(value).replace(/[^0-9.\-]/g, "")), band)
    : null;
  const effectiveTone = graded && graded.tone !== "neutral" ? graded.tone : tone;
  const toneClass = effectiveTone && effectiveTone !== "neutral" ? ` v5-tone-${effectiveTone}` : "";
  return (
    <div className={"v5-status-chip" + toneClass} title={title}>
      {dot && <span className="v5-dot" aria-hidden="true" />}
      {label && <span className="v5-lbl">{label}</span>}
      <span className={"v5-val" + (qual ? " v5-qual" : "")}>{value ?? "—"}</span>
      {graded?.word && <span className="v5-read">{graded.word}</span>}
    </div>
  );
}
