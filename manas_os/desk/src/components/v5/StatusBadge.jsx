import React from "react";

// Status vocabulary for gated/experimental/data-starved organs.
// Rules:
//   LIVE         — actively computing, real data, influences display
//   SHADOW       — computing in background, never influences gates/sizing
//   WARMING      — not enough history yet; will activate automatically
//   EXPERIMENTAL — not validated; display-only, no gate/risk influence
//   NEEDS-DATA   — missing required input; shows what's needed

const BADGE_META = {
  LIVE:         { cls: "sbadge--live",         icon: "●", title: "Live — using real data." },
  SHADOW:       { cls: "sbadge--shadow",        icon: "◈", title: "Shadow — observing only, does not affect gates or sizing." },
  WARMING:      { cls: "sbadge--warming",       icon: "◷", title: "Warming — accumulating history, will activate automatically." },
  EXPERIMENTAL: { cls: "sbadge--experimental", icon: "◧", title: "Experimental — not validated. Display-only, no live influence." },
  "NEEDS-DATA": { cls: "sbadge--needs-data",   icon: "◌", title: "Needs data — required input is missing or not yet ingested." },
};

// StatusBadge: inline chip + optional one-line why.
// Props:
//   status  — one of LIVE | SHADOW | WARMING | EXPERIMENTAL | NEEDS-DATA (drives color/icon)
//   why     — (optional) plain-English explanation shown below the badge
//   label   — (optional) override for the visible text; falls back to `status`.
//             Lets callers (e.g. a stage tracker) reuse the existing color vocabulary
//             with their own wording instead of introducing new badge colors.
export default function StatusBadge({ status, why, label }) {
  const meta = BADGE_META[status] || BADGE_META["NEEDS-DATA"];
  return (
    <span className="sbadge-wrap">
      <span className={["sbadge", meta.cls].join(" ")} title={meta.title} aria-label={`${status}: ${meta.title}`}>
        <span className="sbadge-icon" aria-hidden="true">{meta.icon}</span>
        <span className="sbadge-label">{label || status}</span>
      </span>
      {why && <span className="sbadge-why">{why}</span>}
    </span>
  );
}
