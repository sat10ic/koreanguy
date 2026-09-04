import React, { useId, useState } from "react";
import { GLOSSARY, GLOSSARY_KEYS, hasGlossaryTerm } from "./glossary.js";

export { GLOSSARY, GLOSSARY_KEYS, hasGlossaryTerm };

export function Term({ k, children, as = "button" }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const term = GLOSSARY[k];

  if (!term) {
    return <>{children}</>;
  }

  // Some usages sit inside another interactive control (e.g. a tab <button>
  // label) where a nested <button> is invalid HTML and triggers a React
  // warning. as="span" renders a keyboard/screen-reader-accessible span
  // instead (role="button" + tabIndex + Enter/Space activation).
  const isSpan = as === "span";
  const TriggerTag = isSpan ? "span" : "button";
  const triggerProps = isSpan
    ? {
        role: "button",
        tabIndex: 0,
        onKeyDown: (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            setOpen((value) => !value);
          }
        },
      }
    : { type: "button" };

  return (
    <span
      className="term-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <TriggerTag
        {...triggerProps}
        className="term-trigger"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={(event) => {
          event.stopPropagation();
          setOpen((value) => !value);
        }}
      >
        {children}
      </TriggerTag>
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
