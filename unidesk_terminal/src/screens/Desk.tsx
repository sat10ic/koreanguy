import { useRef, useState } from "react";
import { AlertTriangle, Download, Plus, ShieldAlert, Trash2, Upload } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { Chip } from "../components/ui/Chip";
import { useMode } from "../lib/ModeContext";
import { useReport } from "../lib/useReport";
import {
  addPosition, loadPositions, removePosition, type Position,
} from "../lib/positions";
import { vetoLookup, type VetoVerdict } from "../lib/veto";
import {
  AUDITED_BASELINE, BROKER_SOURCE_LABEL, BROKER_TRADES, deskSaidFor,
} from "../lib/broker";
import { getRealHistory } from "../data/stockHistory";
import { useToast } from "../components/ui/Toast";
import { mirrorRegisterToServer, savePositions } from "../lib/positions";
import { SETUP_LABEL, type SetupType } from "../data/fixtures";

/*
  DESK (X-01 — the ONE new screen; size / manage / exit). Every panel here
  is DESCRIPTIVE: it shows observed facts and the owner's own audited
  record, and never authors a stop, a size, or an instruction (charter:
  LLM proposes never decides; manual execution only; no model-authored
  risk numbers — X-05).

  Grain rule (X-02): this screen shows what the OWNER traded (broker
  import + manual register). Scanner calls live on History. D-09 is the
  only panel where the two meet, and both sides are labelled.
*/

export function Desk() {
  const { mode } = useMode();
  const isPro = mode === "pro";
  const report = useReport();

  return (
    <AppShell breadcrumb={["Desk"]}>
      <div className="flex flex-col gap-4 p-4">
        <div>
          <h1 className="text-h2 font-semibold text-ink-primary">Desk</h1>
          <p className="text-caption text-ink-tertiary">
            Veto, positions, exit alarms, and your own record. Descriptive only — nothing here
            places orders or authors a size (charter: manual execution, LLM never decides).
          </p>
        </div>
        <VetoPanel />
        <PositionsPanel reportSession={report.session_date} isPro={isPro} />
        <SizeEvidencePanel />
        <ReconciliationPanel />
      </div>
    </AppShell>
  );
}

// ---- D-01: pre-trade veto -------------------------------------------------
function VetoPanel() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<{ symbol: string; verdict: VetoVerdict } | null>(null);
  const report = useReport();

  function run() {
    setResult({ symbol: query.trim().toUpperCase(), verdict: vetoLookup(report, query) });
  }

  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="flex items-center gap-1.5 text-h4 font-semibold text-ink-primary">
          <ShieldAlert size={15} className="text-ink-tertiary" aria-hidden />
          Pre-trade check
        </h2>
        <span className="text-caption text-ink-muted">is this name in tonight's universe at all?</span>
      </div>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="SYMBOL"
          aria-label="Symbol to check"
          className="w-44 rounded-chip border border-border bg-surface-input px-2.5 py-1.5 font-mono-num text-caption text-ink-primary outline-none placeholder:text-ink-muted focus:border-border-focus"
        />
        <button onClick={run}
          className="rounded-chip border border-border px-3 py-1.5 text-caption font-medium text-ink-secondary hover:bg-surface-2">
          Check
        </button>
      </div>
      {result && <VetoResult symbol={result.symbol} verdict={result.verdict} />}
    </div>
  );
}

function VetoResult({ symbol, verdict }: { symbol: string; verdict: VetoVerdict }) {
  switch (verdict.kind) {
    case "candidate": {
      const c = verdict.candidate;
      return (
        <div className="mt-2.5 rounded-chip bg-surface-2 p-3 text-caption">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-ink-primary">{symbol}</span>
            <Chip tone="info">CANDIDATE</Chip>
            <span className="text-ink-tertiary">{SETUP_LABEL[c.detector as SetupType] ?? c.detector}</span>
          </div>
          <div className="mt-1 font-mono-num text-ink-secondary">
            Trigger {c.trigger != null ? c.trigger.toFixed(2) : "—"} · Invalidation {c.invalidation != null ? c.invalidation.toFixed(2) : "—"} · R:R {c.rr != null ? c.rr.toFixed(1) : "—"}
          </div>
        </div>
      );
    }
    case "in_universe_no_signal":
      return (
        <VerdictRow tone="neutral" title={`${symbol} — NOT A CANDIDATE`}>
          In tonight's universe, but no detector fired.
        </VerdictRow>
      );
    case "refused_liveness":
      return (
        <VerdictRow tone="danger" title={`${symbol} — NOT IN TONIGHT'S UNIVERSE`}>
          Refused because: no trade on the session date (last print {verdict.lastPrint}).
        </VerdictRow>
      );
    case "refused_universe":
      return (
        <VerdictRow tone="danger" title={`${symbol} — NOT IN TONIGHT'S UNIVERSE`}>
          {verdict.reason}
        </VerdictRow>
      );
    default:
      return (
        <VerdictRow tone="neutral" title={`${symbol || "—"} — UNKNOWN`}>
          Not in this report's candidate list, liveness exclusions, or scanned-universe export.
          {symbol === "" ? " Enter a symbol." : ""}
        </VerdictRow>
      );
  }
}

function VerdictRow({ tone, title, children }: { tone: "danger" | "neutral"; title: string; children: React.ReactNode }) {
  return (
    <div className={"mt-2.5 rounded-chip p-3 text-caption " + (tone === "danger" ? "bg-danger-bg text-danger" : "bg-surface-2 text-ink-secondary")}>
      <div className="font-semibold">{title}</div>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}

// ---- D-03 register + D-02 exit alarm + D-05 risk-cap + D-06 over-trading --
function PositionsPanel({ reportSession, isPro }: { reportSession: string; isPro: boolean }) {
  const [positions, setPositions] = useState<Position[]>(loadPositions);
  const [account, setAccount] = useState<number>(() => {
    // F-4.2: localStorage throws in some contexts — read defensively.
    try {
      const v = localStorage.getItem("unidesk.accountSize");
      return v ? Number(v) : 0;
    } catch { return 0; }
  });
  const [form, setForm] = useState({ symbol: "", entryDate: "", entryPrice: "", sizeInr: "", invalidation: "", paper: false });
  const importFile = useRef<HTMLInputElement | null>(null);
  const { push } = useToast();

  function persist(next: Position[]) {
    setPositions(next);
    // F-4.3: every local save mirrors to the server's durable copy.
    mirrorRegisterToServer(next, account || null);
  }

  // F-4.1: the register lives only in localStorage, which a cache clear
  // erases — Export/Import JSON makes the record survivable without a server.
  function exportRegister() {
    const payload = {
      exported_at: new Date().toISOString(),
      accountSize: account,
      positions,
    };
    const blob = new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `unidesk-register-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    push({ tone: "success", title: "Register exported", detail: `${positions.length} entr${positions.length === 1 ? "y" : "ies"} written to the download.` });
  }

  function importRegister(file: File) {
    file.text().then((text) => {
      try {
        const parsed = JSON.parse(text) as { accountSize?: number; positions?: Position[] };
        if (!Array.isArray(parsed.positions)) throw new Error("no positions array in file");
        savePositions(parsed.positions);
        const next = loadPositions();
        setPositions(next);
        if (typeof parsed.accountSize === "number" && parsed.accountSize > 0) {
          setAccount(parsed.accountSize);
          try { localStorage.setItem("unidesk.accountSize", String(parsed.accountSize)); } catch { /* private mode */ }
        }
        mirrorRegisterToServer(next, account || null);
        push({ tone: "success", title: "Register imported", detail: `${next.length} entries restored.` });
      } catch (exc) {
        push({ tone: "error", title: "Import failed", detail: exc instanceof Error ? exc.message : "unreadable file" });
      }
    });
  }
  // deterministic input guardrails — the form corrects the user itself
  const warns: string[] = [];
  if (form.entryPrice && form.invalidation && Number(form.invalidation) >= Number(form.entryPrice)) {
    warns.push("Invalidation is at or above the entry price — a stop above your buy makes no sense for a long. Check the levels.");
  }
  if (account > 0 && form.sizeInr && Number(form.sizeInr) > account) {
    warns.push("Position size exceeds your stated account size. Re-check before recording.");
  }
  if (form.entryDate && form.entryDate > reportSession) {
    warns.push("Entry date is after the report session — future-dated entries cannot be evaluated against real bars.");
  }

  function submit() {
    if (!form.symbol || !form.entryPrice || !form.sizeInr) return;
    const next = addPosition({
      symbol: form.symbol.trim().toUpperCase(),
      entryDate: form.entryDate || reportSession,
      entryPrice: Number(form.entryPrice),
      sizeInr: Number(form.sizeInr),
      invalidation: form.invalidation ? Number(form.invalidation) : null,
      paper: form.paper,
    });
    persist(next);
    setForm({ symbol: "", entryDate: "", entryPrice: "", sizeInr: "", invalidation: "", paper: false });
  }

  // D-02: structure state from real bars only.
  const alarms = positions.map((p) => ({ p, alarm: exitAlarm(p, reportSession) }));
  const broken = alarms.filter((a) => a.alarm?.broken);

  // D-06: entries in the trailing 7 sessions (register-based count).
  const sevenAgo = daysBefore(reportSession, 7);
  const recentEntries = positions.filter((p) => p.entryDate > sevenAgo && !p.paper).length;

  // D-05: loss to recorded invalidation.
  const grossExposure = positions.reduce((s, p) => s + p.sizeInr, 0);
  const lossIfStopped = positions.reduce(
    (s, p) => s + (p.invalidation ? Math.max(0, (p.entryPrice - p.invalidation) / p.entryPrice) * p.sizeInr : 0), 0);
  const unmanaged = positions.filter((p) => !p.invalidation);

  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Positions register</h2>
        <div className="flex items-center gap-2">
          <span className="text-caption text-ink-muted">manual · local only · no broker connection</span>
          <button onClick={exportRegister} title="Download the register as JSON — a cache clear erases localStorage"
            className="flex items-center gap-1 rounded-chip border border-border px-2 py-0.5 text-caption text-ink-secondary hover:bg-surface-2">
            <Download size={12} aria-hidden /> Export
          </button>
          <button onClick={() => importFile.current?.click()} title="Restore the register from an exported JSON file"
            className="flex items-center gap-1 rounded-chip border border-border px-2 py-0.5 text-caption text-ink-secondary hover:bg-surface-2">
            <Upload size={12} aria-hidden /> Import
          </button>
          <input ref={importFile} type="file" accept="application/json,.json" className="hidden" aria-label="Import register JSON"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) importRegister(f); e.target.value = ""; }} />
        </div>
      </div>

      {/* D-02: exit alarms — observed facts + elapsed sessions (the leak) */}
      {broken.length > 0 && (
        <div className="mb-3 rounded-chip bg-danger-bg p-3">
          <div className="flex items-center gap-1.5 text-caption font-semibold text-danger">
            <AlertTriangle size={13} aria-hidden />
            POSITIONS NEEDING ATTENTION · {broken.length}
          </div>
          {broken.map(({ p, alarm }) => (
            <div key={p.id} className="mt-1 text-caption text-danger">
              {p.symbol} — closed below recorded invalidation {p.invalidation?.toFixed(2)} on {alarm?.breakDate} · {alarm?.sessionsAgo} session{alarm?.sessionsAgo === 1 ? "" : "s"} ago
              {p.paper ? " (paper call)" : ""}
            </div>
          ))}
          <div className="mt-1 text-[10px] text-danger/80">observed facts only — the decision is yours</div>
        </div>
      )}

      {/* D-06 + R-06: activity vs audited baseline + exposure facts */}
      <div className="mb-3 grid grid-cols-2 gap-2 text-caption sm:grid-cols-4">
        <Fact k="Entries, trailing 7 sessions" v={String(recentEntries)} sub={`your audited baseline ≈ ${AUDITED_BASELINE.entriesPerWeek}/week`} />
        <Fact k="Open register entries" v={String(positions.length)} sub={`${positions.filter((p) => p.paper).length} paper`} />
        <Fact k="Gross exposure" v={`₹${grossExposure.toLocaleString()}`} sub={account > 0 ? `${(grossExposure / account * 100).toFixed(0)}% of stated capital` : "state account size below for %"} />
        <Fact k="Loss if all stops hit" v={`₹${lossIfStopped.toLocaleString()}`} sub={account > 0 ? `${(lossIfStopped / account * 100).toFixed(1)}% of capital` : "—"} />
      </div>
      {unmanaged.length > 0 && (
        <div className="mb-3 flex items-center gap-2 rounded-chip bg-warning-bg p-2.5 text-caption text-warning">
          <AlertTriangle size={13} aria-hidden />
          {unmanaged.length} position{unmanaged.length === 1 ? "" : "s"} with NO recorded invalidation ({unmanaged.map((p) => p.symbol).join(", ")}) — unmanaged; that is how a −91% position happens.
        </div>
      )}
      <div className="mb-3 flex items-center gap-2 text-caption text-ink-muted">
        <label htmlFor="account-size">Stated account size (₹):</label>
        <input id="account-size" type="number" value={account || ""} onChange={(e) => {
          const v = Number(e.target.value); setAccount(v);
          try { localStorage.setItem("unidesk.accountSize", String(v)); } catch { /* private mode */ }
          mirrorRegisterToServer(positions, v || null);
        }}
          className="w-36 rounded-chip border border-border bg-surface-input px-2 py-1 font-mono-num text-ink-primary outline-none" />
        <span className="text-[10px]">stored locally, never sent anywhere</span>
      </div>

      {positions.length === 0 ? (
        <p className="text-caption text-ink-tertiary">Register is empty — add an entry below after you trade (or as a paper call).</p>
      ) : (
        <div className="flex flex-col">
          <div className="grid grid-cols-[92px_64px_86px_96px_110px_1fr_32px] gap-2 px-2 py-1 text-caption font-medium text-ink-muted">
            <span>SYMBOL</span><span>DATE</span><span className="text-right">ENTRY</span>
            <span className="text-right">SIZE ₹</span><span className="text-right">INVALIDATION</span><span>STRUCTURE</span><span />
          </div>
          {positions.map((p) => {
            const a = exitAlarm(p, reportSession);
            return (
              <div key={p.id} className="grid grid-cols-[92px_64px_86px_96px_110px_1fr_32px] items-center gap-2 rounded-chip px-2 py-1.5 text-caption hover:bg-surface-2">
                <span className="font-semibold text-ink-primary">{p.symbol}{p.paper ? " 📝" : ""}</span>
                <span className="font-mono-num text-ink-muted">{p.entryDate}</span>
                <span className="text-right font-mono-num text-ink-secondary">{p.entryPrice.toFixed(2)}</span>
                <span className="text-right font-mono-num text-ink-secondary">{p.sizeInr.toLocaleString()}</span>
                <span className={"text-right font-mono-num " + (p.invalidation ? "text-ink-secondary" : "text-danger font-semibold")}>
                  {p.invalidation ? p.invalidation.toFixed(2) : "NONE"}
                </span>
                <span className="truncate text-ink-tertiary">
                  {a?.lastClose != null && p.invalidation
                    ? (a.lastClose < p.invalidation
                      ? `closed ${a.lastClose.toFixed(2)} — below invalidation`
                      : `closed ${a.lastClose.toFixed(2)} — above invalidation`)
                    : "no real bars in the history snapshot for this symbol"}
                </span>
                <button onClick={() => persist(removePosition(p.id))} aria-label={`Remove ${p.symbol}`}
                  className="text-ink-muted hover:text-danger">
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual entry form */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border-subtle pt-3">
        <Plus size={13} className="text-ink-tertiary" aria-hidden />
        <input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
          placeholder="SYMBOL" aria-label="Symbol"
          className="w-24 rounded-chip border border-border bg-surface-input px-2 py-1 font-mono-num text-caption text-ink-primary outline-none" />
        <input value={form.entryDate} onChange={(e) => setForm({ ...form, entryDate: e.target.value })}
          placeholder="YYYY-MM-DD" aria-label="Entry date" type="date"
          className="w-36 rounded-chip border border-border bg-surface-input px-2 py-1 text-caption text-ink-primary outline-none" />
        <input value={form.entryPrice} onChange={(e) => setForm({ ...form, entryPrice: e.target.value })}
          placeholder="Entry ₹" aria-label="Entry price" type="number"
          className="w-24 rounded-chip border border-border bg-surface-input px-2 py-1 font-mono-num text-caption text-ink-primary outline-none" />
        <input value={form.sizeInr} onChange={(e) => setForm({ ...form, sizeInr: e.target.value })}
          placeholder="Size ₹" aria-label="Position size in rupees" type="number"
          className="w-28 rounded-chip border border-border bg-surface-input px-2 py-1 font-mono-num text-caption text-ink-primary outline-none" />
        <input value={form.invalidation} onChange={(e) => setForm({ ...form, invalidation: e.target.value })}
          placeholder="Invalidation ₹" aria-label="Recorded invalidation" type="number"
          className="w-32 rounded-chip border border-border bg-surface-input px-2 py-1 font-mono-num text-caption text-ink-primary outline-none" />
        <label className="flex items-center gap-1 text-caption text-ink-muted">
          <input type="checkbox" checked={form.paper} onChange={(e) => setForm({ ...form, paper: e.target.checked })} />
          paper call
        </label>
        <button onClick={submit}
          className="rounded-chip border border-border px-3 py-1 text-caption font-medium text-ink-secondary hover:bg-surface-2">
          Add
        </button>
      </div>
      {warns.length > 0 && (
        <div className="mt-2 rounded-chip bg-warning-bg p-2.5 text-caption text-warning">
          {warns.map((w) => <div key={w}>⚠ {w}</div>)}
        </div>
      )}
      {isPro && (
        <p className="mt-2 text-[10px] text-ink-muted">
          D-06 baseline constants from {AUDITED_BASELINE.source}: ≈{AUDITED_BASELINE.entriesPerWeek} entries/week,
          {" "}{AUDITED_BASELINE.sameDayRoundTrips} same-day round trips, {AUDITED_BASELINE.revengeReEntries} revenge re-entries (audited).
        </p>
      )}
    </div>
  );
}

function Fact({ k, v, sub }: { k: string; v: string; sub?: string }) {
  return (
    <div className="rounded-chip bg-surface-2 px-2.5 py-2">
      <span className="block text-ink-muted">{k}</span>
      <span className="font-mono-num text-body font-semibold text-ink-primary">{v}</span>
      {sub && <span className="mt-0.5 block text-[10px] text-ink-tertiary">{sub}</span>}
    </div>
  );
}

function daysBefore(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00");
  if (isNaN(d.getTime())) return "0000-01-01";
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

// D-02 resolution: from real bars only. broken = latest close below the
// recorded invalidation; sessionsAgo counts sessions since the break bar.
function exitAlarm(p: Position, sessionDate: string): {
  broken: boolean; breakDate: string; sessionsAgo: number; lastClose: number | null;
} | null {
  const bars = getRealHistory(p.symbol, sessionDate);
  if (!bars || bars.length === 0 || !p.invalidation) return null;
  const usable = bars.filter((b) => b.time <= sessionDate);
  const series = usable.length > 0 ? usable : bars; // snapshot vintage fallback
  const last = series[series.length - 1];
  const broken = last.close < (p.invalidation as number);
  if (!broken) return { broken: false, breakDate: "", sessionsAgo: 0, lastClose: last.close };
  // most recent broken bar scanning back while below
  let i = series.length - 1;
  while (i > 0 && series[i - 1].close < (p.invalidation as number)) i--;
  return {
    broken: true,
    breakDate: series[i].time,
    sessionsAgo: series.length - 1 - i,
    lastClose: last.close,
  };
}

// ---- D-04: size evidence (descriptive of the owner's own record) ----------
const SIZE_BUCKETS: { label: string; lo: number; hi: number }[] = [
  { label: "₹0 – 5k", lo: 0, hi: 5000 },
  { label: "₹5k – 10k", lo: 5000, hi: 10000 },
  { label: "₹10k – 25k", lo: 10000, hi: 25000 },
  { label: "₹25k – 50k", lo: 25000, hi: 50000 },
  { label: "₹50k +", lo: 50000, hi: Infinity },
];

function SizeEvidencePanel() {
  const buys = BROKER_TRADES.filter((t) => t.side === "BUY");
  const buckets = SIZE_BUCKETS.map((b) => {
    const rows = buys.filter((t) => {
      const v = Number(t.gross_value);
      return v >= b.lo && v < b.hi;
    });
    const fees = rows.reduce((s, t) => s + Number(t.fees_allocated || 0), 0);
    return { ...b, n: rows.length, fees };
  });
  const maxN = Math.max(1, ...buckets.map((b) => b.n));
  const mostUsed = buckets.reduce((a, b) => (b.n > a.n ? b : a), buckets[0]);

  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Your outcomes by position size</h2>
        <span className="text-caption text-ink-muted">{buys.length} buy fills · FY25-26 tradebook</span>
      </div>
      <p className="mb-2.5 text-[10px] text-ink-muted">
        Source: {BROKER_SOURCE_LABEL}. Bucket occupancy and fees are computed from the import; the
        audited outcome notes below are quoted from {AUDITED_BASELINE.source}. This panel is
        descriptive — it never suggests a size (charter: no model-authored risk numbers).
      </p>
      <div className="flex flex-col gap-1.5">
        {buckets.map((b) => (
          <div key={b.label} className="grid grid-cols-[86px_46px_1fr_110px] items-center gap-2 text-caption">
            <span className="font-mono-num text-ink-secondary">{b.label}</span>
            <span className={"font-mono-num " + (b === mostUsed ? "text-accent-strong font-semibold" : "text-ink-muted")}>
              n={b.n}
            </span>
            <div className="h-2.5 overflow-hidden rounded-sm bg-surface-2">
              <div className="h-full rounded-sm bg-accent/60" style={{ width: (b.n / maxN * 100) + "%" }} />
            </div>
            <span className="text-[10px] text-ink-tertiary">
              {b === mostUsed ? "← your most-used bucket" : `fees ₹${b.fees.toFixed(0)}`}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 border-t border-border-subtle pt-2 text-caption text-ink-tertiary">
        Audited outcome notes (quoted, not recomputed): your ₹10–25k bucket was your{" "}
        <span className="text-ink-secondary">only profitable bucket</span>; micro-sizing ₹300–5k cost
        ₹10–25k-scale losses; one unmanaged position (RNBDENIMS, −91%) outweighed months of gains.
        Per-bucket realised P&L needs round-trip matching that the fills import does not provide yet.
      </div>
    </div>
  );
}

// ---- D-09: call-vs-trade reconciliation -----------------------------------
function ReconciliationPanel() {
  const buys = BROKER_TRADES.filter((t) => t.side === "BUY");
  // One row per (symbol, date) the owner bought; what the desk said that night.
  const rows = new Map<string, { symbol: string; date: string; verdict: ReturnType<typeof deskSaidFor> }>();
  for (const t of buys) {
    const key = t.symbol + "|" + t.trade_date;
    if (!rows.has(key)) rows.set(key, { symbol: t.symbol, date: t.trade_date, verdict: deskSaidFor(t.trade_date, t.symbol) });
  }
  const list = [...rows.values()].sort((a, b) => (a.date < b.date ? 1 : -1));
  const counts = { candidate: 0, in_universe: 0, not_in_universe: 0, unknown_universe: 0, no_report: 0 } as Record<string, number>;
  for (const r of list) counts[r.verdict.kind] = (counts[r.verdict.kind] ?? 0) + 1;

  return (
    <div className="rounded-card border border-border bg-surface-1 px-3.5 py-3">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="text-h4 font-semibold text-ink-primary">Calls vs trades</h2>
        <span className="text-caption text-ink-muted">{list.length} distinct buy entries · FY25-26</span>
      </div>
      <p className="mb-2.5 text-[10px] text-ink-muted">
        The only place the two grains meet: <span className="text-ink-secondary">"desk said"</span> comes from
        the archived scanner reports; <span className="text-ink-secondary">"you did"</span> comes from the broker
        import. Sessions without an archived report read "no report for that session" — never inferred.
      </p>
      <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-caption">
        <span className="text-info">{counts.candidate} the desk flagged</span>
        <span className="text-ink-tertiary">{counts.in_universe} in universe, no signal</span>
        <span className="text-ink-tertiary">{counts.not_in_universe} not in universe</span>
        <span className="text-ink-muted">{counts.no_report} no archived report</span>
        <span className="text-ink-muted">{counts.unknown_universe} unknown (pre-universe export)</span>
      </div>
      <div className="flex max-h-72 flex-col gap-1 overflow-y-auto pr-1">
        {list.slice(0, 60).map((r, i) => {
          const v = r.verdict;
          const desk = v.kind === "candidate"
            ? `candidate (${SETUP_LABEL[v.detector as SetupType] ?? v.detector})`
            : v.kind === "in_universe" ? "in universe, no signal"
            : v.kind === "not_in_universe" ? "not in universe"
            : v.kind === "no_report" ? "no report for that session"
            : "universe not recorded for that session";
          return (
            <div key={r.symbol + r.date + i} className="grid grid-cols-[64px_92px_1fr] items-center gap-2 rounded-chip px-2 py-1 text-caption hover:bg-surface-2">
              <span className="font-semibold text-ink-primary">{r.symbol}</span>
              <span className="font-mono-num text-ink-muted">{r.date}</span>
              <span className="truncate text-ink-tertiary">
                <span className="text-ink-muted">desk said:</span> {desk}
                <span className="text-ink-muted"> · you did: bought</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
