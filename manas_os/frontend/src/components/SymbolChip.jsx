/**
 * SymbolChip — the fused-source atom (design §0.2A). Fuses ChartsMaze RS +
 * bhavcopy delivery% (DLV) + a Fyers live quote into one inline chip that
 * appears anywhere a ticker is named. No per-symbol endpoint exists yet
 * (Open Q3/Q4 in the spec — /api/symbol/{sym} is backend-blocked), so this
 * component takes its fused fields as props from whatever list endpoint
 * already carries them (e.g. sector/industry stock drilldowns give `rs`);
 * fields it doesn't have simply degrade to a muted placeholder — NEVER a
 * fake number.
 *
 * Props:
 *   symbol        - ticker, required
 *   rs            - ChartsMaze relative strength (0-100) or null
 *   rsAsOf        - date string for RS, for the title tooltip
 *   deliveryPct   - bhavcopy delivery % (0-100) or null
 *   deliveryAsOf  - date string for delivery, for the title tooltip
 *   changePct     - signed live quote change % or null
 *   fyersConnected- whether the live quote is real (else changePct is ignored)
 *   onSelect      - click handler (payload) => void; opens ChartDrawer later.
 *                   Chip renders as a plain span (not a button) when omitted.
 */
export default function SymbolChip({
  symbol,
  rs = null,
  rsAsOf = null,
  deliveryPct = null,
  deliveryAsOf = null,
  changePct = null,
  fyersConnected = false,
  onSelect,
}) {
  const rsBand = rs == null ? null : rs >= 50 ? "bull" : rs >= 40 ? "muted" : "bear";
  // DLV% banding: >=60 bull / 40-59 muted / <40 bear (design §0.2A placeholder,
  // confirmed as final threshold per Open Q1 — no override given, ship as spec'd).
  const dlvBand =
    deliveryPct == null ? null : deliveryPct >= 60 ? "bull" : deliveryPct >= 40 ? "muted" : "bear";
  const quoteLive = fyersConnected && changePct != null;
  const quoteBand = quoteLive ? (changePct >= 0 ? "bull" : "bear") : null;

  const bandCls = {
    bull: "bg-bull-bg text-bull border-bull-border",
    muted: "bg-muted-bg text-muted border-muted-border",
    bear: "bg-bear-bg text-bear border-bear-border",
  };

  const title = [
    rs != null ? `RS ${rs.toFixed(0)}${rsAsOf ? ` (ChartsMaze ${rsAsOf})` : ""}` : null,
    deliveryPct != null
      ? `Delivery ${deliveryPct.toFixed(0)}%${deliveryAsOf ? ` (bhavcopy ${deliveryAsOf})` : ""}`
      : null,
    quoteLive ? "Quote live (Fyers)" : "Quote needs Fyers",
  ]
    .filter(Boolean)
    .join(" · ");

  const Tag = onSelect ? "button" : "span";

  return (
    <Tag
      type={onSelect ? "button" : undefined}
      onClick={
        onSelect
          ? () => onSelect({ symbol, rs, rsAsOf, deliveryPct, deliveryAsOf, changePct, fyersConnected })
          : undefined
      }
      data-testid={`symbol-chip-${symbol}`}
      title={title}
      className={
        "inline-flex items-center gap-1.5 rounded-chip border border-hairline bg-card px-1.5 py-0.5 font-mono text-[11px] " +
        (onSelect ? "cursor-pointer hover:border-ink" : "")
      }
    >
      <span className="font-bold text-ink">{symbol}</span>
      {rs != null ? (
        <span
          className={"rounded-chip border px-1 py-px text-[10px] tabular-nums " + (bandCls[rsBand] || bandCls.muted)}
        >
          RS {rs.toFixed(0)}
        </span>
      ) : (
        <span className="text-[10px] text-inkDisabled">RS ·</span>
      )}
      {deliveryPct != null ? (
        <span
          className={"rounded-chip border px-1 py-px text-[10px] tabular-nums " + (bandCls[dlvBand] || bandCls.muted)}
        >
          DLV {deliveryPct.toFixed(0)}%
        </span>
      ) : (
        <span className="text-[10px] text-inkDisabled">DLV ·</span>
      )}
      {quoteLive ? (
        <span className={"flex items-center gap-0.5 text-[10px] tabular-nums " + (quoteBand === "bull" ? "text-bull" : "text-bear")}>
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-bull-dot" title="live" />
          {changePct >= 0 ? "▲+" : "▼"}
          {Math.abs(changePct).toFixed(1)}%
        </span>
      ) : (
        <span className="text-[10px] text-inkDisabled" title="needs Fyers">
          ·
        </span>
      )}
    </Tag>
  );
}
