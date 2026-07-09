import React, { useId, useState } from "react";
import { GLOSSARY, GLOSSARY_KEYS, hasGlossaryTerm } from "./glossary.js";

export { GLOSSARY, GLOSSARY_KEYS, hasGlossaryTerm };

export function Term({ k, children }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const term = GLOSSARY[k];

  if (!term) {
    return <>{children}</>;
  }

  return (
    <span
      className="term-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        className="term-trigger"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={(event) => {
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      >
        {children}
      </button>
      {open && (
        <span id={id} role="tooltip" className="term-tooltip">
          <span className="term-tooltip-title">{term.label}</span>
          <span>{term.plain}</span>
          <span className="term-tooltip-care">{term.care}</span>
        </span>
      )}
    </span>
  );
}
