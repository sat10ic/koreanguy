import { useDensity } from "../DensityContext.jsx";

/**
 * <Read> — the verdict layer (design §0.2C / design_guidelines.components.
 * verdict_layer). Fixed slot: mono verdict chip + dashed divider + sans READ
 * line. Every data block gets exactly one; never omit, never decorate.
 * Expert density shrinks the prose to a single line (same sentence, no
 * layout ceremony) per design §0.3.
 */
export default function Read({ verdict, band = "muted", children }) {
  const { density } = useDensity();
  const bandCls =
    {
      bull: "bg-bull-bg text-bull border-bull-border",
      warn: "bg-warn-bg text-warn border-warn-border",
      bear: "bg-bear-bg text-bear border-bear-border",
      muted: "bg-muted-bg text-muted border-muted-border",
      info: "bg-info-bg text-info border-info-border",
    }[band] || "bg-muted-bg text-muted border-muted-border";

  return (
    <div data-testid="read-line" className="mt-2">
      {verdict && (
        <span
          className={
            "mb-1 inline-block rounded-chip border px-1.5 py-px font-mono text-[10px] font-bold uppercase tracking-overline " +
            bandCls
          }
        >
          {verdict}
        </span>
      )}
      <div className="border-t border-dashed border-hairline2 pt-1">
        <span className="mr-1 font-mono text-[9px] uppercase tracking-overline text-inkDisabled">
          read
        </span>
        <span
          className={
            "font-sans text-ink2 " + (density === "expert" ? "text-[11px] leading-tight" : "text-[12px] leading-snug")
          }
          style={{ color: "#3a414c" }}
        >
          {children}
        </span>
      </div>
    </div>
  );
}
