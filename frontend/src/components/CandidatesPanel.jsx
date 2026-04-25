import React from "react";
import { Panel, GradePill, Tag, Empty } from "../ui";
import { fmtNum, fmtPct, fmtInt, classNames } from "../utils";

function Th({ children, align = "left", className }) {
  return (
    <th
      className={classNames(
        "border-b border-borderDefault px-2 py-2 text-[10px] uppercase tracking-overline text-textMuted",
        align === "right" ? "text-right" : "text-left",
        className
      )}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left", className, mono = false }) {
  return (
    <td
      className={classNames(
        "border-b border-borderSubtle px-2 py-2 text-[12px]",
        align === "right" ? "text-right" : "text-left",
        mono ? "font-mono tnum" : "",
        className
      )}
    >
      {children}
    </td>
  );
}

function CandidateRow({ c, onSymbol, isPrimary }) {
  return (
    <tr
      onClick={() => onSymbol?.(c.symbol)}
      className="cursor-pointer transition-colors hover:bg-surfaceHover"
      data-testid={`candidate-row-${c.symbol}`}
    >
      <Td>
        <div className="flex items-center gap-2">
          <span className="font-mono font-semibold text-textPrimary">{c.symbol}</span>
          {c.purple_dot_today === 1 && <span className="block h-2 w-2 bg-purpledot" title="Purple dot today" />}
        </div>
        <div className="mt-0.5 truncate text-[10px] text-textMuted">
          {c.name || c.sector || "—"}
        </div>
      </Td>
      <Td><GradePill grade={c.grade} /></Td>
      <Td align="right" mono>{fmtNum(c.rs_score, 4)}</Td>
      <Td align="right" mono>{fmtNum(c.close, 2)}</Td>
      <Td align="right" mono>
        <span className="text-bear">{fmtNum(c.suggested_stop, 2)}</span>
        <div className="text-[10px] text-textMuted">
          −{fmtPct((c.close - c.suggested_stop) / c.close, 2)}
        </div>
      </Td>
      <Td align="right" mono>
        <span className="text-textPrimary">{fmtInt(c.size_shares)}</span>
        <div className="text-[10px] text-textMuted">{fmtPct(c.size_pct, 2)}</div>
      </Td>
      <Td align="right" mono>
        <span className="inline-flex items-center gap-1">
          <span className="block h-1.5 w-1.5 bg-purpledot" />
          {fmtInt(c.purple_dot_count_30d)}
        </span>
      </Td>
      {isPrimary && (
        <Td>
          <div className="max-w-[280px] truncate text-[10px] text-textSecondary" title={c.notes}>
            {c.notes || "—"}
          </div>
        </Td>
      )}
    </tr>
  );
}

function PrimaryCard({ c, onSymbol }) {
  const stopPct = (c.close - c.suggested_stop) / c.close;
  return (
    <button
      onClick={() => onSymbol?.(c.symbol)}
      data-testid={`primary-card-${c.symbol}`}
      className="group flex flex-col border border-borderDefault bg-surface text-left transition-colors hover:border-bull/60 hover:bg-surfaceHover"
    >
      <div className="flex items-center justify-between border-b border-borderDefault px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-base font-semibold tracking-tight">
            {c.symbol}
          </span>
          {c.purple_dot_today === 1 && (
            <Tag color="purple">PD</Tag>
          )}
        </div>
        <GradePill grade={c.grade} />
      </div>
      <div className="grid grid-cols-3 gap-px bg-borderDefault">
        <div className="bg-surface px-3 py-2">
          <div className="text-[9px] uppercase tracking-overline text-textMuted">Close</div>
          <div className="mt-0.5 font-mono text-sm tnum">{fmtNum(c.close)}</div>
        </div>
        <div className="bg-surface px-3 py-2">
          <div className="text-[9px] uppercase tracking-overline text-textMuted">Stop</div>
          <div className="mt-0.5 font-mono text-sm tnum text-bear">{fmtNum(c.suggested_stop)}</div>
          <div className="text-[9px] text-textMuted">−{fmtPct(stopPct)}</div>
        </div>
        <div className="bg-surface px-3 py-2">
          <div className="text-[9px] uppercase tracking-overline text-textMuted">Size</div>
          <div className="mt-0.5 font-mono text-sm tnum">{fmtInt(c.size_shares)}</div>
          <div className="text-[9px] text-textMuted">{fmtPct(c.size_pct)}</div>
        </div>
      </div>
      <div className="border-t border-borderDefault px-3 py-2">
        <div className="text-[9px] uppercase tracking-overline text-textMuted">
          Why · Layer A + B
        </div>
        <div className="mt-1 line-clamp-2 text-[11px] leading-snug text-textSecondary">
          {c.notes || "—"}
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-borderDefault px-3 py-2 text-[10px] text-textMuted">
        <span>
          <span className="text-textMuted">RS</span>{" "}
          <span className="font-mono text-textPrimary tnum">{fmtNum(c.rs_score, 4)}</span>
        </span>
        <span>
          <span className="block h-1.5 w-1.5 bg-purpledot inline-block mr-1" />
          {fmtInt(c.purple_dot_count_30d)} / 30d
        </span>
        <span className="truncate text-textSecondary">{c.sector || ""}</span>
      </div>
    </button>
  );
}

export default function CandidatesPanel({ data, onSymbol }) {
  const primary = data?.primary || [];
  const secondary = data?.secondary || [];
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
      {/* Primary */}
      <div className="xl:col-span-7">
        <Panel
          testId="primary-panel"
          title={
            <span>
              Primary Candidates ·{" "}
              <span className="text-bull">{primary.length}</span> watchlist signals
            </span>
          }
          right={
            <span className="font-mono text-[10px] uppercase tracking-overline text-textMuted">
              Trade Today
            </span>
          }
        >
          {primary.length === 0 ? (
            <Empty testId="primary-empty">
              No watchlist signals fired today. Either regime is RISK_OFF, or no
              setup passed both Layer A (grade stability) and Layer B (chart
              structure).
            </Empty>
          ) : (
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3">
              {primary.map((c) => (
                <PrimaryCard key={c.symbol} c={c} onSymbol={onSymbol} />
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Secondary */}
      <div className="xl:col-span-5">
        <Panel
          testId="secondary-panel"
          title={
            <span>
              Secondary · <span className="text-textPrimary">{secondary.length}</span> for
              Sunday review
            </span>
          }
        >
          {secondary.length === 0 ? (
            <Empty>No secondary signals. The watchlist is doing its job.</Empty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr>
                    <Th>Symbol</Th>
                    <Th>Grade</Th>
                    <Th align="right">RS</Th>
                    <Th align="right">Close</Th>
                    <Th align="right">Stop</Th>
                    <Th align="right">PD/30d</Th>
                  </tr>
                </thead>
                <tbody>
                  {secondary.slice(0, 25).map((c) => (
                    <CandidateRow key={c.symbol} c={c} onSymbol={onSymbol} isPrimary={false} />
                  ))}
                </tbody>
              </table>
              {secondary.length > 25 && (
                <div className="mt-2 text-center text-[11px] text-textMuted">
                  + {secondary.length - 25} more — full list in CSV
                </div>
              )}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
