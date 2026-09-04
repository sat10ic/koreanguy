import React from "react";

// v5 primitive: council vote split bar (muted green/rose segments) + "2T/2S" mono label.
// take/skip are integer vote counts; renders nothing meaningful (empty track) when both are 0/undefined.
export default function VoteBar({ take, skip }) {
  const t = take || 0;
  const s = skip || 0;
  const total = t + s;
  const takePct = total > 0 ? (t / total) * 100 : 0;
  const skipPct = total > 0 ? 100 - takePct : 0;
  return (
    <span className="v5-vote-bar-wrap">
      <span className="v5-vote-bar" title={`${t} take / ${s} skip`}>
        {total > 0 ? (
          <>
            <span className="v5-vote-seg v5-take" style={{ width: `${takePct}%` }} />
            <span className="v5-vote-seg v5-skip" style={{ width: `${skipPct}%` }} />
          </>
        ) : (
          <span className="v5-vote-seg v5-skip" style={{ width: "0%" }} />
        )}
      </span>
      <span className="v5-vote-lbl mono-num">{total > 0 ? `${t}T/${s}S` : "—"}</span>
    </span>
  );
}
