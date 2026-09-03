import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Square } from "lucide-react";
import { useToast } from "../ui/Toast";
import { refreshDeskData } from "../../data/deskData";

/*
  E-4.1: the real Run-pipeline button. idle → click → optimistic "Starting…"
  → live SSE progress (per-stage ticks, elapsed time, determinate bar) →
  success toast naming the new session, or a failure naming the failed stage
  and exit code. On success the data layer re-hydrates and the screens
  update WITHOUT a reload and WITHOUT npm run build (PART E-0 reversed the
  static-only architecture — see UI_BACKEND_INTEGRATION_PLAN.md E-5 note).
  The nightly chain itself is fail-fast (B2-4): a failure here is a real
  failure, never a stale-but-confident desk.
*/

type StepState = { name: string; label: string; status: "running" | "finished" | "skipped" | "failed"; exitCode?: number | null };

type RunState =
  | { phase: "idle" }
  | { phase: "starting" }
  | { phase: "running"; steps: StepState[]; total: number; startedAt: number }
  | { phase: "failed"; stage: string | null; exitCode: number | null; error: string };

export function RunPipeline() {
  const { push } = useToast();
  const [state, setState] = useState<RunState>({ phase: "idle" });
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  function listen(jobId: string) {
    const es = new EventSource(`/api/jobs/${jobId}/events`);
    const startedAt = Date.now();
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 1000);
    es.onmessage = (m) => {
      let ev: Record<string, unknown>;
      try { ev = JSON.parse(m.data); } catch { return; }
      const kind = ev.event as string;
      setState((cur) => {
        if (cur.phase !== "running") {
          if (kind === "job_started") return { phase: "running", steps: [], total: Number(ev.total ?? 0), startedAt };
          return cur;
        }
        const steps = [...cur.steps];
        switch (kind) {
          case "stage_started":
            steps.push({ name: String(ev.name), label: String(ev.label), status: "running" });
            return { ...cur, steps, total: Number(ev.total ?? cur.total) };
          case "stage_finished":
          case "stage_skipped": {
            const s = steps.find((x) => x.name === ev.name && x.status === "running");
            if (s) s.status = kind === "stage_finished" ? "finished" : "skipped";
            return { ...cur, steps };
          }
          case "stage_failed": {
            const s = steps.find((x) => x.name === ev.name && x.status === "running");
            if (s) { s.status = "failed"; s.exitCode = ev.exit_code as number | null; }
            return { ...cur, steps };
          }
          default:
            return cur;
        }
      });
      if (kind === "job_finished") {
        es.close();
        if (timer.current) clearInterval(timer.current);
        setState({ phase: "idle" });
        const session = (ev.session as string | null) ?? "";
        push({ tone: "success", title: "Refresh complete", detail: session ? `Desk is now on session ${session}.` : "Data reloaded." });
        void refreshDeskData(); // re-hydrate → screens update, no reload
      }
      if (kind === "job_failed") {
        es.close();
        if (timer.current) clearInterval(timer.current);
        const stage = (ev.failed_stage as string | null) ?? null;
        const exitCode = (ev.exit_code as number | null) ?? null;
        setState({ phase: "failed", stage, exitCode, error: String(ev.error ?? "refresh failed") });
        push({ tone: "error", title: "Refresh failed", detail: `stage "${stage ?? "?"}" exited ${exitCode ?? "—"} — the desk kept its last verified data.` });
      }
    };
    es.onerror = () => {
      es.close();
      if (timer.current) clearInterval(timer.current);
      setState({ phase: "failed", stage: null, exitCode: null, error: "connection to the desk server was lost" });
      push({ tone: "error", title: "Refresh interrupted", detail: "connection to the desk server was lost" });
    };
  }

  function start() {
    setState({ phase: "starting" });
    fetch("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }).then(async (res) => {
      if (res.status === 409) {
        const body = await res.json().catch(() => null);
        const other = body?.detail?.job_id ?? "";
        setState({ phase: "idle" });
        push({ tone: "info", title: "A refresh is already running", detail: other ? `job ${other}` : undefined });
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { job_id } = await res.json() as { job_id: string };
      listen(job_id);
    }).catch((err: Error) => {
      setState({ phase: "failed", stage: null, exitCode: null, error: `desk server unreachable (${err.message})` });
      push({ tone: "error", title: "Cannot start refresh", detail: "desk server unreachable — start it with: python -m uvicorn unidesk.server.app:app --port 8181" });
    });
  }

  const running = state.phase === "running" || state.phase === "starting";
  const done = state.phase === "running" ? state.steps.filter((s) => s.status !== "running").length : 0;
  const total = state.phase === "running" ? state.total : 0;
  const pct = state.phase === "running" && total > 0 ? Math.round((done / total) * 100) : state.phase === "starting" ? 4 : 0;

  return (
    <div className="flex min-w-0 flex-col">
      <button
        onClick={start}
        disabled={running}
        title={running ? "A refresh is running" : "Run the full desk refresh (download → nightly → exports → checks → no rebuild needed)"}
        className={"flex h-9 items-center gap-1.5 rounded-btn border px-3 text-caption font-medium transition-colors " +
          (state.phase === "failed"
            ? "border-danger-border bg-danger-bg text-danger"
            : running
              ? "border-accent-border bg-accent-bg text-accent-strong"
              : "border-subtle text-ink-secondary hover:bg-surface-2")}
      >
        {running ? <Loader2 size={13} className="animate-spin" aria-hidden />
          : state.phase === "failed" ? <Square size={13} aria-hidden />
            : <Play size={13} aria-hidden />}
        {state.phase === "starting" ? "Starting…"
          : state.phase === "running" ? `Refreshing… ${elapsed}s`
            : state.phase === "failed" ? "Refresh failed"
              : "Run refresh"}
      </button>
      {running && (
        <div className="mt-0.5 h-1 w-full overflow-hidden rounded-sm bg-surface-2" aria-hidden>
          <div className="h-full rounded-sm bg-accent/60 transition-all duration-500" style={{ width: `${Math.max(3, pct)}%` }} />
        </div>
      )}
    </div>
  );
}
