// ⌘K command bar. A global Ctrl/Cmd+K opens an overlay palette: jump to any
// tab, any trader (from /api/traders), any symbol (from /api/positions +
// /api/ideas, deduped). Type to filter; Arrow keys highlight and Enter
// navigates through the same navigate(toTab, params) the shell uses; Esc or a
// click outside closes. Fully keyboard accessible: role="dialog", the first
// result is active on open, focus lands in the filter input so typing works
// immediately. Restyled to the scouting tokens (--ground canvas, --edge 1px
// rule, radius 0). No new dependencies.
import React from "react";
import { fetchTraders, fetchPositions, fetchIdeas } from "../api.js";

const VISIBLE_TABS = ["TODAY", "LEDGER", "TRADERS", "IDEAS", "LIBRARY", "MARKET"];

// Defensive shape handling: the endpoints return {"<noun>": rows, "is_mock":
// ...}; accept a bare array too so the palette survives both.
function rowsOf(payload, noun) {
  if (Array.isArray(payload)) return payload;
  const v = payload && payload[noun];
  return Array.isArray(v) ? v : [];
}

export default function CommandBar({ onNavigate }) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [active, setActive] = React.useState(0);
  const [traders, setTraders] = React.useState([]);
  const [symbols, setSymbols] = React.useState([]);
  const inputRef = React.useRef(null);
  const itemRefs = React.useRef([]);

  // Load the trader/symbol directory lazily on first open and cache it for
  // the session; the tabs are always available, so the palette never blocks
  // on the network.
  const loadDirectory = React.useCallback(() => {
    Promise.all([fetchTraders(), fetchPositions(), fetchIdeas()])
      .then(([t, p, i]) => {
        setTraders(rowsOf(t, "traders"));
        const symSet = new Set();
        rowsOf(p, "positions").forEach((po) => {
          if (po && po.symbol) symSet.add(po.symbol);
        });
        rowsOf(i, "ideas").forEach((g) => {
          if (g && g.symbol) symSet.add(g.symbol);
        });
        setSymbols(Array.from(symSet).sort());
      })
      .catch(() => {
        /* directory unavailable: the tabs still work */
      });
  }, []);

  const openPalette = React.useCallback(() => {
    setOpen(true);
    setQuery("");
    setActive(0);
    if (traders.length === 0 && symbols.length === 0) loadDirectory();
  }, [traders.length, symbols.length, loadDirectory]);

  // Global Ctrl/Cmd+K (Meta on mac, Ctrl elsewhere).
  React.useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        openPalette();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openPalette]);

  const close = React.useCallback(() => setOpen(false), []);

  // Focus the filter input on open so typing filters immediately; the first
  // result is active, so Arrow/Enter work without a click.
  React.useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
      setActive(0);
    }
  }, [open]);

  const results = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const tabs = VISIBLE_TABS.map((t) => ({
      kind: "tab",
      label: t,
      toTab: t,
      params: {},
    }));
    const traderEntries = traders
      .filter((tr) => tr && tr.handle)
      .map((tr) => ({
        kind: "trader",
        label: tr.handle,
        toTab: "TRADERS",
        params: { handle: tr.handle },
      }));
    const symbolEntries = symbols.map((s) => ({
      kind: "symbol",
      label: s,
      toTab: "SYMBOL",
      params: { symbol: s },
    }));
    const all = [...tabs, ...traderEntries, ...symbolEntries];
    if (!q) return all;
    return all.filter((e) => e.label.toLowerCase().includes(q));
  }, [query, traders, symbols]);

  // Keep the highlighted result in view as the list shrinks.
  React.useEffect(() => {
    if (open && active >= 0 && active < results.length) {
      const el = itemRefs.current[active];
      if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
    }
  }, [active, results.length, open]);

  const go = React.useCallback(
    (r) => {
      onNavigate(r.toTab, r.params);
      setOpen(false);
    },
    [onNavigate]
  );

  const onDialogKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const r = results[active];
      if (r) go(r);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  };

  if (!open) return null;

  return (
    <div className="command-bar-backdrop" onClick={close}>
      <div
        className="command-bar"
        role="dialog"
        aria-label="Command bar"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onDialogKeyDown}
      >
        <input
          ref={inputRef}
          className="command-bar-input"
          type="text"
          placeholder="Jump to a tab, trader or symbol…"
          aria-label="Search tabs, traders and symbols"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
        />
        <div className="command-bar-list" role="listbox" aria-label="Results">
          {results.length === 0 && (
            <div className="command-bar-empty">
              no matches — try a tab, @handle or symbol
            </div>
          )}
          {results.map((r, i) => (
            <button
              key={`${r.kind}:${r.label}`}
              ref={(el) => {
                itemRefs.current[i] = el;
              }}
              type="button"
              role="option"
              aria-selected={i === active}
              className={`command-bar-item${i === active ? " active" : ""}`}
              onMouseEnter={() => setActive(i)}
              onClick={() => go(r)}
            >
              <span className={`cmd-label${r.kind === "tab" ? " cmd-label-tab" : ""}`}>
                {r.kind === "trader" ? `@${r.label}` : r.label}
              </span>
              <span className="cmd-kind">{r.kind}</span>
            </button>
          ))}
        </div>
        <div className="command-bar-hint">↑↓ move · enter jump · esc close</div>
      </div>
    </div>
  );
}