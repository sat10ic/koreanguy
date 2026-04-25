import React, { useMemo, useState } from "react";
import { Panel, Tag, Empty, GradePill, Button } from "../ui";
import { fmtNum, fmtPct, fmtInt, pnlClass, classNames } from "../utils";
import { InfoDot } from "./Tooltip";
import PositionFormModal from "./PositionFormModal";
import { Plus, Edit2, LogOut, Trash2 } from "lucide-react";
import { endpoints } from "../api";

const STATE_TAG = {
  PENDING_CONFIRM: "pending",
  ACTIVE: "active",
  EXITED_STOP: "bear",
  EXITED_EXTENDED: "bull",
  EXITED_DECAY: "bear",
  EXITED_MANUAL: "default",
  DISCARDED: "discarded",
};

const STATE_GROUPS = [
  { id: "open", label: "Open", states: ["PENDING_CONFIRM", "ACTIVE"] },
  { id: "exited", label: "Exited", states: ["EXITED_STOP", "EXITED_EXTENDED", "EXITED_DECAY", "EXITED_MANUAL"] },
  { id: "all", label: "All", states: null },
];

export default function PositionsPanel({ data, onSymbol, onChange }) {
  const [tab, setTab] = useState("open");
  const [modal, setModal] = useState(null); // { mode, initial }
  const summary = data?.summary || {};
  const stats = data?.stats || {};
  const rows = data?.rows || [];

  const filtered = useMemo(() => {
    const grp = STATE_GROUPS.find((g) => g.id === tab);
    if (!grp || !grp.states) return rows;
    return rows.filter((r) => grp.states.includes(r.state));
  }, [rows, tab]);

  const handleDelete = async (p) => {
    if (!window.confirm(`Delete position #${p.id} (${p.symbol})? This is permanent.`)) return;
    try {
      await endpoints.positionDelete(p.id);
      onChange?.();
    } catch (e) {
      alert("Delete failed: " + (e?.response?.data?.detail || e.message));
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
      <div className="xl:col-span-3">
        <Panel title="Tracker State" testId="tracker-summary">
          <div className="grid grid-cols-2 gap-px bg-borderDefault">
            {[
              ["PENDING_CONFIRM", "Pending"],
              ["ACTIVE", "Active"],
              ["EXITED_STOP", "Stopped"],
              ["EXITED_EXTENDED", "Exit-Ext"],
              ["EXITED_DECAY", "Exit-Decay"],
              ["DISCARDED", "Discarded"],
            ].map(([k, label]) => (
              <div key={k} className="bg-surface px-3 py-2.5">
                <div className="text-[9px] uppercase tracking-overline text-textMuted">
                  {label}
                </div>
                <div className="mt-1 font-mono text-xl tnum text-textPrimary">
                  {summary[k] || 0}
                </div>
              </div>
            ))}
          </div>

          {stats.total_exited > 0 && (
            <div className="mt-4 border border-borderDefault">
              <div className="border-b border-borderDefault px-3 py-2 text-[10px] uppercase tracking-overline text-textMuted">
                Walk-forward Stats
              </div>
              <div className="grid grid-cols-2 divide-x divide-borderSubtle">
                <div className="px-3 py-2">
                  <div className="flex items-center gap-1 text-[9px] uppercase tracking-overline text-textMuted">
                    <span>Hit Rate</span>
                    <InfoDot
                      k="HitRate"
                      title="Hit Rate"
                      text="% of closed trades that ended profitable. The bread-and-butter setup targets 35–55% — pair with avg P&L to judge edge."
                    />
                  </div>
                  <div className={classNames(
                    "mt-0.5 font-mono text-lg tnum",
                    stats.hit_rate >= 0.35 && stats.hit_rate <= 0.55 ? "text-bull" :
                    stats.hit_rate < 0.35 ? "text-bear" : "text-warn"
                  )}>{fmtPct(stats.hit_rate)}</div>
                  <div className="text-[10px] text-textMuted">target 35–55%</div>
                </div>
                <div className="px-3 py-2">
                  <div className="text-[9px] uppercase tracking-overline text-textMuted">Avg P&L</div>
                  <div className={classNames("mt-0.5 font-mono text-lg tnum", pnlClass(stats.avg_pnl_pct))}>
                    {fmtPct(stats.avg_pnl_pct)}
                  </div>
                  <div className="text-[10px] text-textMuted">
                    best {fmtPct(stats.best_pnl_pct)} · worst {fmtPct(stats.worst_pnl_pct)}
                  </div>
                </div>
              </div>
              <div className="border-t border-borderDefault px-3 py-2 text-[10px] text-textMuted">
                Total Exited: <span className="font-mono text-textPrimary">{stats.total_exited}</span>{" · "}
                W/L: <span className="font-mono text-bull">{stats.wins}</span>/
                <span className="font-mono text-bear">{stats.losses}</span>
              </div>
            </div>
          )}
        </Panel>
      </div>

      <div className="xl:col-span-9">
        <Panel
          testId="positions-table-panel"
          title="Positions · State Machine"
          right={
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                {STATE_GROUPS.map((g) => (
                  <button
                    key={g.id}
                    data-testid={`pos-tab-${g.id}`}
                    onClick={() => setTab(g.id)}
                    className={classNames(
                      "border px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline transition-colors",
                      tab === g.id
                        ? "border-bull text-bull"
                        : "border-borderDefault text-textSecondary hover:text-textPrimary"
                    )}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
              <Button
                variant="primary"
                onClick={() => setModal({ mode: "add", initial: null })}
                testId="pos-add-btn"
              >
                <Plus size={11} />
                Add Position
              </Button>
            </div>
          }
        >
          {filtered.length === 0 ? (
            <Empty>
              <div>No positions in this view yet.</div>
              <div className="mt-2">
                Primary signals seed PENDING_CONFIRM rows automatically — or click
                <span className="mx-1 inline-block border border-bull/60 bg-bull/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-overline text-bull">
                  + Add Position
                </span>
                to log a discretionary trade.
              </div>
            </Empty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr>
                    <Th>Symbol</Th>
                    <Th>State</Th>
                    <Th>
                      <span className="inline-flex items-center gap-1">Grade <InfoDot k="Grade" /></span>
                    </Th>
                    <Th align="right">Entry</Th>
                    <Th align="right">
                      <span className="inline-flex items-center gap-1">Stop <InfoDot k="Stop" /></span>
                    </Th>
                    <Th align="right">Current</Th>
                    <Th align="right">
                      <span className="inline-flex items-center gap-1">P&L <InfoDot k="PnL" /></span>
                    </Th>
                    <Th align="right">Size</Th>
                    <Th align="right">
                      <span className="inline-flex items-center gap-1">
                        Δ Stop
                        <InfoDot
                          k="DeltaStop"
                          title="Distance to Stop"
                          text="How far the current price is above the stop, as a % of the current price. Bigger cushion = lower risk of getting stopped out today."
                        />
                      </span>
                    </Th>
                    <Th>Signal Date</Th>
                    <Th>
                      <span className="inline-flex items-center gap-1">Regime <InfoDot k="Regime" /></span>
                    </Th>
                    <Th align="right">Actions</Th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((p) => {
                    const tagColor = STATE_TAG[p.state] || "default";
                    const livePnl = p.live_pnl_pct ?? p.pnl_pct;
                    const isOpen =
                      p.state === "ACTIVE" || p.state === "PENDING_CONFIRM";
                    return (
                      <tr
                        key={p.id}
                        className="transition-colors hover:bg-surfaceHover"
                        data-testid={`position-row-${p.symbol}`}
                      >
                        <Td onClick={() => onSymbol?.(p.symbol)} className="cursor-pointer">
                          <span className="font-mono font-semibold">{p.symbol}</span>
                        </Td>
                        <Td>
                          <Tag color={tagColor} testId={`position-state-${p.symbol}`}>
                            {p.state.replace("EXITED_", "EXIT·")}
                          </Tag>
                        </Td>
                        <Td><GradePill grade={p.entry_grade} /></Td>
                        <Td align="right" mono>{fmtNum(p.entry_price)}</Td>
                        <Td align="right" mono className="text-bear">{fmtNum(p.stop_price)}</Td>
                        <Td align="right" mono>{fmtNum(p.current_price ?? p.exit_price)}</Td>
                        <Td align="right" mono>
                          <span className={pnlClass(livePnl)}>{fmtPct(livePnl)}</span>
                        </Td>
                        <Td align="right" mono>{fmtInt(p.size_shares)}</Td>
                        <Td align="right" mono>
                          {p.distance_to_stop_pct != null ? (
                            <span className={p.distance_to_stop_pct > 0.05 ? "text-bull" : "text-warn"}>
                              {fmtPct(p.distance_to_stop_pct)}
                            </span>
                          ) : "—"}
                        </Td>
                        <Td><span className="font-mono text-textSecondary">{p.signal_date}</span></Td>
                        <Td>
                          <span className="font-mono text-[10px] text-textMuted">{p.regime_at_entry || "—"}</span>
                        </Td>
                        <Td align="right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              data-testid={`pos-edit-${p.symbol}`}
                              onClick={() => setModal({ mode: "edit", initial: p })}
                              title="Edit / trail stop"
                              className="text-textMuted transition-colors hover:text-textPrimary"
                            >
                              <Edit2 size={11} />
                            </button>
                            {isOpen && (
                              <button
                                type="button"
                                data-testid={`pos-exit-${p.symbol}`}
                                onClick={() => setModal({ mode: "exit", initial: p })}
                                title="Close position"
                                className="text-warn transition-colors hover:text-bear"
                              >
                                <LogOut size={11} />
                              </button>
                            )}
                            <button
                              type="button"
                              data-testid={`pos-delete-${p.symbol}`}
                              onClick={() => handleDelete(p)}
                              title="Delete row"
                              className="text-textMuted transition-colors hover:text-bear"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>

      <PositionFormModal
        open={!!modal}
        mode={modal?.mode}
        initial={modal?.initial}
        onClose={() => setModal(null)}
        onSaved={() => onChange?.()}
      />
    </div>
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

function Td({ children, align = "left", mono = false, className }) {
  return (
    <td
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
