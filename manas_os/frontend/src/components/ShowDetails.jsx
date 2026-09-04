import { useState } from "react";

/**
 * ShowDetails — the reusable "show the numbers" expander (BEGINNER_EXPERT_SPEC §2 Axis C).
 * Beginner collapses diagnostic numbers behind this; Expert renders them inline.
 * A curious beginner can peek; the numbers are never forced on them.
 */
export default function ShowDetails({ label = "Show the numbers", testid = "show-details", children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2" data-testid={testid}>
      <button
        onClick={() => setOpen((v) => !v)}
        data-testid={`${testid}-toggle`}
        className="font-mono text-[9px] uppercase tracking-overline text-ink3 hover:text-ink2"
      >
        {open ? "▾ hide the numbers" : `▸ ${label}`}
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  );
}
