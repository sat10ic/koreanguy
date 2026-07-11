import React from "react";

// v5 primitive: signed % return, green/red, mono tabular. "--" (ink-mute,
// AA-safe -- see primitives.v5.css a11y note; ink-faint fails AA on text,
// with an explanatory title) when null -- e.g. short price history.
export default function ReturnCell({ value, nullTitle = "not enough price history" }) {
  if (value === null || value === undefined) {
    return (
      <span className="v5-return-cell v5-null mono-num" title={nullTitle}>
        {"—"}
      </span>
    );
  }
  const up = value >= 0;
  const sign = up ? "+" : "";
  return (
    <span className={"v5-return-cell mono-num " + (up ? "v5-up" : "v5-down")}>
      {sign}
      {value.toFixed(1)}%
    </span>
  );
}
