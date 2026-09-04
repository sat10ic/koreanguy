import React from "react";
import StatusChip from "./StatusChip.jsx";

// v5 primitive: app shell header. Brand mark + name/sub, middle StatusChips
// (Day/Regime/HMM/VIX), right mono stats (XP/Universe/Debated). All values
// are display-only passthrough from the run-card/market payloads -- this
// component never computes or infers a value it wasn't given.
export default function CommandStrip({
  date,
  dayColor,
  regimeMode,
  hmmCaption,
  vix,
  vixTitle,
  xp,
  universe,
  debated,
}) {
  const dayTone = dayColor === "GREEN" ? "green" : dayColor === "RED" ? "red" : dayColor ? "amber" : "neutral";

  return (
    <div className="v5-cmd-topbar">
      <div className="v5-cmd-brand">
        <div className="v5-cmd-brand-mark" aria-hidden="true">S</div>
        <div>
          <div className="v5-cmd-brand-name">
            sat10ic os <span style={{ color: "var(--v5-ink-mute)", fontWeight: 500 }}>/ DESK</span>
          </div>
          <div className="v5-cmd-brand-sub">NSE SWING · MULTI-MODEL COUNCIL{date ? ` · ${date}` : ""}</div>
        </div>
      </div>

      <div className="v5-cmd-mid">
        <StatusChip label="Day" value={dayColor || "—"} tone={dayTone} />
        <StatusChip label="Regime" value={regimeMode || "—"} tone={regimeMode ? "amber" : "neutral"} />
        <StatusChip label="HMM" value={hmmCaption || "—"} dot={false} />
        <StatusChip
          label="VIX"
          value={vix !== null && vix !== undefined ? vix : "—"}
          qual={vix === null || vix === undefined}
          title={vixTitle}
          dot={false}
        />
      </div>

      <div className="v5-cmd-right">
        <span>
          XP <b className="mono-num">{xp !== null && xp !== undefined ? xp : "—"}</b>
        </span>
        <span>·</span>
        <span>
          Universe <b className="mono-num">{universe ?? "—"}</b>
        </span>
        <span>·</span>
        <span>
          Debated <b className="mono-num" style={{ color: "var(--v5-amber-ink)" }}>{debated ?? "—"}</b>
        </span>
      </div>
    </div>
  );
}
