/**
 * SetupStickers — "What's working / What's not" (design §1.4). Its own
 * bordered card with two labelled rows: PREFER (bull-band chips, ▸ glyph)
 * and AVOID (bear-band chips, ✕ glyph). Left 64px eyebrow column + wrapped
 * chips on the right, so it reads as two tidy rows instead of a jumble.
 */
export default function SetupStickers({ preferred = [], avoid = [] }) {
  const empty = preferred.length === 0 && avoid.length === 0;

  return (
    <section
      data-testid="setup-stickers"
      className="mb-4 border border-hairline bg-card p-3"
    >
      <div className="mb-2 font-mono text-[10px] uppercase tracking-overline text-ink3">
        What's working / what's not
      </div>
      {empty ? (
        <p className="font-sans text-[12px] text-ink3">
          No setup guidance for this regime — sit tight.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <StickerRow eyebrow="Prefer" items={preferred} band="bull" glyph="▸" />
          <StickerRow eyebrow="Avoid" items={avoid} band="bear" glyph="✕" />
        </div>
      )}
    </section>
  );
}

function StickerRow({ eyebrow, items, band, glyph }) {
  if (items.length === 0) return null;
  const cls =
    band === "bull"
      ? "border-bull-border bg-bull-bg text-bull"
      : "border-bear-border bg-bear-bg text-bear";
  return (
    <div className="grid grid-cols-[64px_1fr] items-start gap-2">
      <span className="pt-0.5 font-mono text-[9px] font-bold uppercase tracking-overline text-ink3">
        {eyebrow}
      </span>
      <div className="flex flex-wrap gap-1">
        {items.map((s) => (
          <span
            key={s}
            className={"rounded-chip border px-2 py-0.5 font-mono text-[10px] " + cls}
          >
            {glyph} {s}
          </span>
        ))}
      </div>
    </div>
  );
}
