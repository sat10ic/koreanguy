import React, { useState } from "react";
import { Panel, Empty, GradePill, Tag, Button } from "../ui";
import { fmtNum, fmtInt, classNames } from "../utils";
import { endpoints } from "../api";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { InfoDot } from "./Tooltip";

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
  const [adding, setAdding] = useState(false);
  const [flash, setFlash] = useState(null);
  const rows = data?.rows || [];

  // After adding a new symbol, the backend kicks off a background backfill
  // (sector/industry from yfinance.info + 380 days OHLCV + indicators).
  // Re-poll the watchlist a few times so the UI catches up live without
  // requiring a full pipeline run.
  const scheduleRefreshes = () => {
    [3000, 10000, 30000, 90000].forEach((ms) =>
      setTimeout(() => onChange?.(), ms)
    );
  };

  const handleAdd = async (e) => {
    e?.preventDefault?.();
    const sym = add.trim().toUpperCase();
    if (!sym || adding) return;
    setAdding(true);
    try {
      await endpoints.watchlistAdd(sym, "manual");
      setAdd("");
      setFlash({ type: "ok", msg: `Added ${sym} — pulling history & metadata…` });
      onChange?.();
      scheduleRefreshes();
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message;
      setFlash({ type: "err", msg: detail });
    } finally {
      setAdding(false);
      setTimeout(() => setFlash(null), 6000);
    }
  };

  const handleRemove = async (sym) => {
    try {
      await endpoints.watchlistRemove(sym);
      onChange?.();
    } catch (err) {
      setFlash({ type: "err", msg: "Failed to remove: " + err.message });
      setTimeout(() => setFlash(null), 4000);
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
            disabled={adding}
            className="w-32 border border-borderDefault bg-page px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-textPrimary placeholder-textMuted focus:border-bull focus:outline-none disabled:opacity-50"
          />
          <Button
            testId="watchlist-add-btn"
            variant="primary"
            onClick={handleAdd}
            disabled={adding}
          >
            {adding ? (
              <Loader2 size={11} className="animate-spin" />
            ) : (
              <Plus size={11} />
            )}
            {adding ? "Adding" : "Add"}
          </Button>
        </form>
      }
    >
      {flash && (
        <div
          data-testid="watchlist-flash"
          className={classNames(
            "mb-3 border px-3 py-2 text-[11px]",
            flash.type === "ok"
              ? "border-bull/40 bg-bull/5 text-bull"
              : "border-bear/40 bg-bear/5 text-bear"
          )}
        >
          {flash.msg}
        </div>
      )}

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
                <Th>
                  <span className="inline-flex items-center gap-1">
                    Grade <InfoDot k="Grade" />
                  </span>
                </Th>
                <Th>
                  <span className="inline-flex items-center gap-1">
                    5-day
                    <InfoDot
                      k="GradeHistory"
                      title="5-day grade trend"
                      text="Last 5 sessions of this stock's grade — a quick read on whether quality is improving or deteriorating."
                    />
                  </span>
                </Th>
                <Th align="right">
                  <span className="inline-flex items-center gap-1">
                    RS <InfoDot k="RS" />
                  </span>
                </Th>
                <Th align="right">Close</Th>
                <Th align="right">
                  <span className="inline-flex items-center gap-1">
                    PD/30 <InfoDot k="PD/30" />
                  </span>
                </Th>
                <Th>
                  <span className="inline-flex items-center gap-1">
                    Bucket <InfoDot k="Bucket" />
                  </span>
                </Th>
                <Th>Added</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const enriching =
                  r.close == null && r.rs_score == null && r.grade == null;
                return (
                  <tr
                    key={r.symbol}
                    className="cursor-pointer transition-colors hover:bg-surfaceHover"
                    data-testid={`watchlist-row-${r.symbol}`}
                  >
                    <Td onClick={() => onSymbol?.(r.symbol)}>
                      <span className="font-mono font-semibold">{r.symbol}</span>
                      <div className="text-[10px] text-textMuted">
                        {r.name || ""}
                      </div>
                    </Td>
                    <Td onClick={() => onSymbol?.(r.symbol)}>
                      <span className="text-textSecondary">
                        {r.sector || "—"}
                      </span>
                      {r.industry && (
                        <div className="text-[10px] text-textMuted">
                          {r.industry}
                        </div>
                      )}
                    </Td>
                    <Td onClick={() => onSymbol?.(r.symbol)}>
                      {enriching ? (
                        <span className="inline-flex items-center gap-1 font-mono text-[10px] text-textMuted">
                          <Loader2 size={10} className="animate-spin" />
                          syncing
                        </span>
                      ) : (
                        <GradePill grade={r.grade} />
                      )}
                    </Td>
                    <Td onClick={() => onSymbol?.(r.symbol)}>
                      <MiniGradeStrip history={r.grade_history_5d} />
                    </Td>
                    <Td align="right" mono>
                      {r.rs_score != null ? fmtNum(r.rs_score, 4) : "—"}
                    </Td>
                    <Td align="right" mono>
                      {fmtNum(r.close)}
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
                      <span className="font-mono text-textMuted">
                        {r.date_added}
                      </span>
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
                );
              })}
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
