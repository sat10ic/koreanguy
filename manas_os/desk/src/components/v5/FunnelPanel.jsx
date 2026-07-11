import React from "react";

// v5 primitive: universe -> debated gate funnel. Plain SVG trapezoid stack
// (no chart lib) sized from real counts in `stages`; stat rows + drop chips
// mirror the SVG. `stages`: [{ label, n }] in descending order; `drops`:
// [{ label, n }] optional cause-of-drop chips.
export default function FunnelPanel({ stages, drops, width = 200, height = 150 }) {
  if (!stages || stages.length === 0) {
    return <div className="v5-fs-row"><span className="v5-lbl">{"— no funnel data"}</span></div>;
  }
  const numericCounts = stages.map((stage) => Number(stage.n)).filter((n) => Number.isFinite(n) && n >= 0);
  const max = numericCounts.length ? Math.max(...numericCounts, 1) : null;
  const bandH = height / stages.length;
  const bands = stages.map((s, i) => {
    const wTop = Math.max(((stages[i].n || 0) / (max || 1)) * width, 4);
    const wBot = Math.max(((stages[i + 1] ? stages[i + 1].n : stages[i].n) || 0) / (max || 1) * width, 4);
    const y = i * bandH;
    const x1t = (width - wTop) / 2;
    const x2t = x1t + wTop;
    const x1b = (width - wBot) / 2;
    const x2b = x1b + wBot;
    const isLast = i === stages.length - 1;
    return (
      <polygon
        key={s.label}
        className={"v5-funnel-band" + (isLast ? " v5-funnel-band-last" : "")}
        points={`${x1t},${y} ${x2t},${y} ${x2b},${y + bandH - 2} ${x1b},${y + bandH - 2}`}
      />
    );
  });
  return (
    <div className="v5-funnel-wrap">
      <svg className="v5-funnel-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="gate funnel">
        {bands}
      </svg>
      <div className="v5-funnel-stats">
        {stages.map((s) => (
          <div className="v5-fs-row" key={s.label}>
            <span className="v5-n mono-num">{s.n ?? "—"}</span>
            <span className="v5-lbl">{s.label}</span>
            <span className="v5-pct mono-num">
              {max && s.n !== null && s.n !== undefined ? `${((Number(s.n) / max) * 100).toFixed(1)}%` : "—"}
            </span>
          </div>
        ))}
        {drops && drops.length > 0 && (
          <div className="v5-fs-drop">
            {drops.map((d) => (
              <span key={d.label}>
                {d.label} <b>-{d.n}</b>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
