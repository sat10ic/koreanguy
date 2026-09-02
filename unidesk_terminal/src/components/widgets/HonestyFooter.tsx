import { ChevronDown, ChevronRight, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { HonestyFooterFacts } from "../../data/tonight";
import deskChecksJson from "../../data/desk_checks.json";

interface DeskCheck { key: string; name: string; detail: string; pass: boolean }
const DESK_CHECKS = (deskChecksJson as { checks: DeskCheck[] }).checks ?? [];

/*
  G-07: ONE diagnostics drawer per screen. All engineering / provenance
  strings live here (adjustment_note, detection_inputs_policy, gate-skip
  breakdown, liveness detail, history depth, grain) — never in Beginner's
  primary view. Collapsed, it is the H4-08 one-liner: quiet, factual.
*/
export function HonestyFooter({ hf }: { hf: HonestyFooterFacts }) {
  const [open, setOpen] = useState(false);
  const scanned = hf.universe_scanned?.toLocaleString?.() ?? "—";
  const skipped = hf.universe_skipped_insufficient_history ?? 0;
  const gated = hf.universe_gate_skips_total ?? 0;
  const stale = hf.stale_excluded ?? 0;

  return (
    <div className="rounded-card border border-border-subtle bg-surface-1 px-3.5 py-2.5">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 text-left"
        aria-expanded={open}
      >
        <ShieldCheck size={13} className="shrink-0 text-ink-tertiary" aria-hidden />
        <span className="text-caption font-medium text-ink-secondary">Data quality</span>
        <span className="text-caption text-ink-tertiary font-mono-num">
          ✓ {scanned} scanned · {skipped.toLocaleString()} skipped · {gated.toLocaleString()} gated out
          {stale > 0 ? ` · ${stale} stale excluded` : ""}
        </span>
        <span className="ml-auto flex items-center gap-1 text-caption text-ink-muted">
          details
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>

      {open && (
        <div className="mt-2.5 space-y-1.5 rounded-chip bg-surface-2 p-2.5">
          <Line k="Adjustment">{hf.adjustment_note}</Line>
          <Line k="CA applied">{hf.actions_applied} actions · {hf.adjusted_symbols} symbols adjusted ({hf.adjustment_status})</Line>
          <Line k="Detection inputs">{hf.detection_inputs_policy}</Line>
          {hf.history_sessions_max != null && (
            <Line k="History depth">
              deepest scanned symbol carries {hf.history_sessions_max.toLocaleString()} sessions (nightly ingest window, not the full archive)
            </Line>
          )}
          {hf.history_depth && <Line k="History policy">{hf.history_depth}</Line>}
          {hf.liveness_gate && <Line k="Liveness gate">{hf.liveness_gate}</Line>}
          {hf.liveness_excluded && Object.keys(hf.liveness_excluded).length > 0 && (
            <Line k="Stale excluded (symbol → last print)">
              {Object.entries(hf.liveness_excluded).map(([s, d]) => `${s} → ${d}`).join(" · ")}
            </Line>
          )}
          {hf.universe_gate_skips && Object.keys(hf.universe_gate_skips).length > 0 && (
            <Line k="Gate skips">
              {Object.entries(hf.universe_gate_skips).map(([k, v]) => `${k.replace("universe_gate_", "")}=${v}`).join(", ")}
            </Line>
          )}
          <Line k="Candidate grain">{hf.candidate_grain ?? "symbol"} · {hf.candidate_distinct_symbols?.toLocaleString() ?? "—"} distinct symbols</Line>
          {hf.prior_session_date && (
            <Line k="Prior session">{hf.prior_session_date} — {hf.prior_regime_note ?? "no regime note"}</Line>
          )}
          {DESK_CHECKS.length > 0 && (
            <div className="border-t border-border-subtle pt-2">
              <div className="mb-1 text-caption font-medium text-ink-secondary">
                Desk self-checks · {DESK_CHECKS.filter((c) => c.pass).length}/{DESK_CHECKS.length} passing
              </div>
              {DESK_CHECKS.map((c) => (
                <div key={c.key} className="grid grid-cols-[14px_1fr] gap-1.5 py-0.5">
                  <span className={c.pass ? "text-positive" : "text-warning"}>{c.pass ? "✓" : "⚠"}</span>
                  <span className="text-caption text-ink-tertiary" title={c.detail}>
                    {c.name}
                    {!c.pass && <span className="ml-1 font-medium text-warning">— {c.detail}</span>}
                  </span>
                </div>
              ))}
            </div>
          )}
          <Line k="Disclaimer">{hf.disclaimer}</Line>
        </div>
      )}
    </div>
  );
}

function Line({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[130px_1fr] gap-2 text-caption text-ink-tertiary">
      <span className="text-ink-muted">{k}</span>
      <span>{children}</span>
    </div>
  );
}
