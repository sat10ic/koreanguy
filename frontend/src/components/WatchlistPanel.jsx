import React, { useState } from "react";
import { Panel, Empty, GradePill, Tag, Button } from "../ui";
import { fmtNum, fmtInt, classNames } from "../utils";
import { endpoints } from "../api";
import { Plus, Trash2 } from "lucide-react";

function MiniGradeStrip({ history }) {
  return (
    <div className="flex items-center gap-0.5">
      {(history || Array(5).fill(null)).map((g, i) => {
        const cls = !g
          ? "bg-borderDefault"
          : g.startsWith("A")
            ? "bg-bull"
            : g.startsWith("B")
              ? "bg-emerald-300"
              : g.startsWith("C")
                ? "bg-warn"
                : g.startsWith("D") || g.startsWith("E")
                  ? "bg-orange-400"
                  : "bg-bear";
        return (
          <span
            key={i}
            className={classNames("block h-3 w-1.5", cls)}
            title={g || "—"}
          />
        );
      })}
    </div>
  );
}

export default function WatchlistPanel({ data, onSymbol, onChange }) {
  const [add, setAdd] = useState("");
  const rows = data?.rows || [];

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!add.trim()) return;
    try {
      await endpoints.watchlistAdd(add.trim().toUpperCase(), "manual");
      setAdd("");
      onChange?.();
    } catch (err) {
      alert("Failed to add: " + err.message);
    }
  };

  const handleRemove = async (sym) => {
    try {
      await endpoints.watchlistRemove(sym);
      onChange?.();
    } catch (err) {
      alert("Failed to remove: " + err.message);
    }
  };

  return (
    <Panel
      testId="watchlist-panel"
      title={`Watchlist · ${rows.length} symbols`}
      right={
        <form onSubmit={handleAdd} className="flex items-center gap-1">
          <input
            data-testid="watchlist-add-input"
            value={add}
            onChange={(e) => setAdd(e.target.value)}
            placeholder="ADD SYMBOL"
            className="w-32 border border-borderDefault bg-page px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-textPrimary placeholder-textMuted focus:border-bull focus:outline-none"
          />
          <Button
            testId="watchlist-add-btn"
            variant="primary"
            onClick={handleAdd}
          >
            <Plus size={11} />
            Add
          </Button>
        </form>
      }
    >
      {rows.length === 0 ? (
        <Empty>
          Watchlist empty. Add high-conviction symbols here; only watchlist
          members produce primary signals.
        </Empty>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr>
                <Th>Symbol</Th>
                <Th>Sector</Th>
                <Th>Grade</Th>
                <Th>5-day</Th>
                <Th align="right">RS</Th>
                <Th align="right">Close</Th>
                <Th align="right">Ret 5d</Th>
                <Th align="right">PD/30</Th>
                <Th>Bucket</Th>
                <Th>Added</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.symbol}
                  className="cursor-pointer transition-colors hover:bg-surfaceHover"
                  data-testid={`watchlist-row-${r.symbol}`}
                >
                  <Td onClick={() => onSymbol?.(r.symbol)}>
                    <span className="font-mono font-semibold">{r.symbol}</span>
                    <div className="text-[10px] text-textMuted">{r.name || ""}</div>
                  </Td>
                  <Td onClick={() => onSymbol?.(r.symbol)}>
                    <span className="text-textSecondary">{r.sector || "—"}</span>
                  </Td>
                  <Td onClick={() => onSymbol?.(r.symbol)}><GradePill grade={r.grade} /></Td>
                  <Td onClick={() => onSymbol?.(r.symbol)}>
                    <MiniGradeStrip history={r.grade_history_5d} />
                  </Td>
                  <Td align="right" mono>{r.rs_score != null ? fmtNum(r.rs_score, 4) : "—"}</Td>
                  <Td align="right" mono>{fmtNum(r.close)}</Td>
                  <Td align="right" mono>
                    {/* ret_5d not directly exposed in watchlist row, fallback */}
                    —
                  </Td>
                  <Td align="right" mono>
                    <span className="inline-flex items-center gap-1">
                      <span className="block h-1.5 w-1.5 bg-purpledot" />
                      {fmtInt(r.purple_dot_count_30d)}
                    </span>
                  </Td>
                  <Td>
                    {r.bucket && (
                      <Tag color={r.bucket === "Bullish" ? "bull" : "bear"}>
                        {r.bucket}
                      </Tag>
                    )}
                  </Td>
                  <Td>
                    <span className="font-mono text-textMuted">{r.date_added}</span>
                  </Td>
                  <Td align="right">
                    <Button
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemove(r.symbol);
                      }}
                      testId={`watchlist-remove-${r.symbol}`}
                    >
                      <Trash2 size={11} />
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function Th({ children, align = "left" }) {
  return (
    <th
      className={classNames(
        "border-b border-borderDefault px-2 py-2 text-[10px] uppercase tracking-overline text-textMuted",
        align === "right" ? "text-right" : "text-left"
      )}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left", mono = false, onClick, className }) {
  return (
    <td
      onClick={onClick}
      className={classNames(
        "border-b border-borderSubtle px-2 py-2",
        align === "right" ? "text-right" : "text-left",
        mono ? "font-mono tnum" : "",
        className
      )}
    >
      {children}
    </td>
  );
}
