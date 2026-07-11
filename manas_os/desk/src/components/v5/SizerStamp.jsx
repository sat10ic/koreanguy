import React from "react";

// v5 primitive: refusal stamp -- "SIZER REFUSED - DETERMINISTIC RISK IS FINAL
// AUTHORITY" + qty/rupee-risk/multiplier metrics. Values come ONLY from the
// payload (sizer object); this component performs zero risk arithmetic.
export default function SizerStamp({ reason, qty = 0, rupeeRisk = 0, multiplier = 0 }) {
  return (
    <div className="v5-sizer-stamp">
      <div className="v5-icon" aria-hidden="true">
        {"✕"}
      </div>
      <div className="v5-txt">
        <div className="v5-h">SIZER REFUSED &mdash; DETERMINISTIC RISK IS FINAL AUTHORITY</div>
        <div className="v5-d">{reason || "no reason recorded"}</div>
      </div>
      <div className="v5-metrics">
        <div className="v5-m">
          <div className="v5-mn mono-num">{multiplier}&times;</div>
          <div className="v5-ml">multiplier</div>
        </div>
        <div className="v5-m">
          <div className="v5-mn mono-num">{qty}</div>
          <div className="v5-ml">qty</div>
        </div>
        <div className="v5-m">
          <div className="v5-mn mono-num">{rupeeRisk}</div>
          <div className="v5-ml">risk</div>
        </div>
      </div>
    </div>
  );
}
