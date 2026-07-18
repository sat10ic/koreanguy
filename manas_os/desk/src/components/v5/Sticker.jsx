import React, { useEffect, useRef, useState } from "react";
import { STICKERS, STICKER_PRIORITY, pickVisibleStickers } from "../../stickers.js";

// v5 shared primitive: one sticker chip. Mono 2-3 char glyph, v5 tokens
// only, title/aria = plainRead (hover teaches the linkage), clickable ->
// caller-provided onClick for drill-in. Never decorative — a sticker with
// no onClick still exposes its full read via title/aria for screen readers
// and hover, per spec ("every sticker clickable -> the evidence that
// earned it").
export default function Sticker({ code, detail, onClick, tabIndex }) {
  const meta = STICKERS[code];
  if (!meta) return null;
  const title = detail ? `${meta.label} — ${meta.plainRead} (${detail})` : `${meta.label} — ${meta.plainRead}`;
  return (
    <button
      type="button"
      className={`v5-sticker v5-sticker-${meta.tone}`}
      title={title}
      aria-label={title}
      onClick={onClick}
      tabIndex={tabIndex}
    >
      {meta.glyph}
    </button>
  );
}

// StickerRow: renders up to MAX_VISIBLE stickers for one card/row + a "+N"
// overflow popover for the rest, per the priority order in stickers.js.
// Props:
//   codes    — array of sticker codes present on this row (already
//              filtered by the caller to codes whose source field is
//              actually present — StickerRow never invents evidence).
//   details  — optional {code: "extra detail string"} shown in the title.
//   onSelect — (code) => void, called when a sticker (visible or from the
//              overflow popover) is clicked. Typically opens drill-in.
export function StickerRow({ codes, details, onSelect, className }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const { visible, overflow } = pickVisibleStickers(codes);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  if (!visible.length) return null;

  return (
    <span className={"v5-sticker-row" + (className ? " " + className : "")} ref={wrapRef}>
      {visible.map((code) => (
        <Sticker key={code} code={code} detail={details?.[code]} onClick={onSelect ? () => onSelect(code) : undefined} />
      ))}
      {overflow.length > 0 && (
        <span className="v5-sticker-overflow-wrap">
          <button
            type="button"
            className="v5-sticker v5-sticker-overflow"
            title={`${overflow.length} more sticker${overflow.length > 1 ? "s" : ""}`}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            +{overflow.length}
          </button>
          {open && (
            <span className="v5-sticker-popover" role="menu">
              {overflow.map((code) => {
                const meta = STICKERS[code];
                return (
                  <button
                    type="button"
                    key={code}
                    role="menuitem"
                    className="v5-sticker-popover-item"
                    onClick={() => {
                      setOpen(false);
                      onSelect?.(code);
                    }}
                  >
                    <span className={`v5-sticker v5-sticker-${meta.tone}`} aria-hidden="true">{meta.glyph}</span>
                    <span className="v5-sticker-popover-text">
                      <span className="v5-sticker-popover-label">{meta.label}</span>
                      <span className="v5-sticker-popover-read">{meta.plainRead}</span>
                    </span>
                  </button>
                );
              })}
            </span>
          )}
        </span>
      )}
    </span>
  );
}

// StickerLegend: the glossary panel required by the spec ("a STICKER
// LEGEND panel reachable from any tab header"). A single header button
// that toggles a panel listing every registered sticker — glyph, label,
// plain read and the exact live field it traces to. Self-contained so
// any tab header can drop in <StickerLegend /> without extra wiring.
export function StickerLegend({ className }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const orderedCodes = STICKER_PRIORITY.filter((c) => STICKERS[c]);

  return (
    <span className={"v5-sticker-legend-wrap" + (className ? " " + className : "")} ref={wrapRef}>
      <button
        type="button"
        className="v5-sticker-legend-btn"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        title="Sticker legend — what every sticker means and where it comes from"
      >
        <span aria-hidden="true">&#9673;</span> sticker legend
      </button>
      {open && (
        <div className="v5-sticker-legend-panel" role="dialog" aria-label="Sticker legend">
          <div className="v5-sticker-legend-hd">
            Sticker legend — hover any sticker in the app for this same read.
          </div>
          <div className="v5-sticker-legend-list">
            {orderedCodes.map((code) => {
              const meta = STICKERS[code];
              return (
                <div className="v5-sticker-legend-row" key={code}>
                  <span className={`v5-sticker v5-sticker-${meta.tone}`} aria-hidden="true">{meta.glyph}</span>
                  <span className="v5-sticker-legend-text">
                    <span className="v5-sticker-legend-label">{meta.label}</span>
                    <span className="v5-sticker-legend-read">{meta.plainRead}</span>
                    <span className="v5-sticker-legend-source mono-num">{meta.sourceField}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </span>
  );
}
