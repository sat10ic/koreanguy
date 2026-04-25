import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { endpoints } from "../api";
import { GradePill, Spinner, Empty, Tag } from "../ui";
import { fmtNum, fmtPct, classNames } from "../utils";

/**
 * Fetches /api/screen with the given filter and shows the resulting stock list.
 * Filter shapes supported (any one):
 *   { purple_dot_only: true }
 *   { setup_only: true }
 *   { sector: "Financials" }
 *   { industry: "Banks" }
 *   { basic_industry: "..." }
 *   { bucket: "Bullish", grade: "A+" }
 */
export default function StockListModal({ open, title, subtitle, filter, onClose, onSymbol }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setAvailable(true);
    endpoints
      .screen({ ...(filter || {}), sort_by: "rs_score", sort_desc: true, limit: 300 })
      .then((d) => {
        if (cancelled) return;
        setRows(d?.rows || []);
        setAvailable(d?.available !== false);
      })
      .catch(() => !cancelled && setRows([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [open, JSON.stringify(filter || {})]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-center bg-page/80 backdrop-blur-sm"
      onClick={onClose}
      data-testid="stock-list-modal"
    >
      <div
        className="mt-16 w-full max-w-3xl border border-borderDefault bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-borderDefault px-4 py-3">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-overline text-saffron">
              {title}
            </div>
            {subtitle && (
              <div className="mt-0.5 text-[11px] text-textSecondary">{subtitle}</div>
            )}
          </div>
          <button
            data-testid="stock-list-modal-close"
            onClick={onClose}
            className="text-textMuted transition-colors hover:text-textPrimary"
            aria-label="close"
          >
            <X size={16} />
          </button>
        </header>

        <div className="max-h-[70vh] overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-10">
              <Spinner label="loading list" />
            </div>
          ) : !available ? (
            <Empty>
              The market screen hasn't been computed yet — run the daily pipeline
              from the header to populate this list.
            </Empty>
          ) : rows.length === 0 ? (
            <Empty>No stocks match this filter today.</Empty>
          ) : (
            <table className="w-full text-[12px]">
              <thead className="sticky top-0 bg-surface">
                <tr>
                  <Th>Symbol</Th>
                  <Th>Sector</Th>
                  <Th>Grade</Th>
                  <Th align="right">RS</Th>
                  <Th align="right">Close</Th>
                  <Th align="right">5d</Th>
                  <Th align="right">21d</Th>
                  <Th>Bucket</Th>
                  <Th>Flags</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.symbol}
                    onClick={() => {
                      onSymbol?.(r.symbol);
                      onClose?.();
                    }}
                    className="cursor-pointer transition-colors hover:bg-surfaceHover"
                    data-testid={`stock-list-row-${r.symbol}`}
                  >
                    <Td>
                      <div className="font-mono font-semibold text-textPrimary">
                        {r.symbol}
                      </div>
                      <div className="text-[10px] text-textMuted">{r.name || ""}</div>
                    </Td>
                    <Td>
                      <span className="text-textSecondary">{r.sector || "—"}</span>
                      {r.industry && (
                        <div className="text-[10px] text-textMuted">{r.industry}</div>
                      )}
                    </Td>
                    <Td>
                      <GradePill grade={r.grade} />
                    </Td>
                    <Td align="right" mono>
                      {r.rs_score != null ? fmtNum(r.rs_score, 4) : "—"}
                    </Td>
                    <Td align="right" mono>
                      {fmtNum(r.close)}
                    </Td>
                    <Td align="right" mono className={pnlCls(r.ret_5d)}>
                      {r.ret_5d != null ? fmtPct(r.ret_5d, 1) : "—"}
                    </Td>
                    <Td align="right" mono className={pnlCls(r.ret_21d)}>
                      {r.ret_21d != null ? fmtPct(r.ret_21d, 1) : "—"}
                    </Td>
                    <Td>
                      {r.bucket && (
                        <Tag color={r.bucket === "Bullish" ? "bull" : "bear"}>
                          {r.bucket}
                        </Tag>
                      )}
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {r.purple_dot ? <Tag color="purple">PD</Tag> : null}
                        {r.setup_pass ? <Tag color="bull">SETUP</Tag> : null}
                        {r.extended_yellow ? <Tag color="warn">EXT-Y</Tag> : null}
                        {r.extended_red ? <Tag color="bear">EXT-R</Tag> : null}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <footer className="flex items-center justify-between border-t border-borderDefault px-4 py-2 text-[10px] uppercase tracking-overline text-textMuted">
          <span>Click any row to open chart & details</span>
          <span className="font-mono">{rows.length} matches</span>
        </footer>
      </div>
    </div>
  );
}

function pnlCls(v) {
  if (v == null) return "text-textMuted";
  if (v > 0) return "text-bull";
  if (v < 0) return "text-bear";
  return "text-textSecondary";
}

function Th({ children, align = "left" }) {
  return (
    <th
      className={classNames(
        "border-b border-borderDefault bg-surface px-2 py-2 text-[10px] uppercase tracking-overline text-textMuted",
        align === "right" ? "text-right" : "text-left"
      )}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left", mono = false, className }) {
  return (
    <td
      className={classNames(
        "border-b border-borderSubtle px-2 py-2 align-top",
        align === "right" ? "text-right" : "text-left",
        mono ? "font-mono tnum" : "",
        className
      )}
    >
      {children}
    </td>
  );
}
