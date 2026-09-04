import React from "react";

// v5 primitive: "Tonight's Call" banner -- stance cell + headline + arrow
// bullets + mono cite tags. Renders `tonights_call` payload verbatim.
// `bullets`: [{ text, cite }]
export default function CallBanner({ stance = "CAUTION", icon = "⚠", headline, bullets }) {
  return (
    <div className="v5-call-banner">
      <div className="v5-stance">
        <span className="v5-ic" aria-hidden="true">{icon}</span>
        <span className="v5-t">{stance}</span>
      </div>
      <div className="v5-content">
        {headline && <div className="v5-headline">{headline}</div>}
        {bullets && bullets.length > 0 && (
          <ul>
            {bullets.map((b, i) => (
              <li key={i}>
                {b.text} {b.cite && <span className="v5-cite">[{b.cite}]</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
