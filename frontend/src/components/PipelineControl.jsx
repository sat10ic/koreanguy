import React, { useEffect, useState } from "react";
import { Button } from "../ui";
import { Play, Square } from "lucide-react";
import { endpoints } from "../api";

export default function PipelineControl({ running, onStarted }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let timer;
    const tick = async () => {
      try {
        const s = await endpoints.pipelineStatus();
        setStatus(s);
      } catch (e) {}
      timer = setTimeout(tick, running ? 1500 : 5000);
    };
    tick();
    return () => clearTimeout(timer);
  }, [running]);

  const trigger = async () => {
    try {
      await endpoints.pipelineRun();
      onStarted?.();
    } catch (e) {
      alert("Failed to start pipeline: " + e.message);
    }
  };

  const progress = status?.progress;
  const stage = status?.current_stage;
  const pct =
    progress?.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div className="flex items-center gap-3">
      {running && (
        <div className="hidden items-center gap-2 border border-borderDefault bg-surface px-3 py-1.5 md:flex">
          <span className="block h-2 w-2 animate-pulse bg-bull" />
          <div className="font-mono text-[10px] uppercase tracking-overline text-textPrimary">
            <span className="text-bull">[ {stage?.toUpperCase() || "RUN"} ]</span>{" "}
            <span className="text-textSecondary">
              {progress?.done || 0}/{progress?.total || 0}
            </span>{" "}
            <span className="text-textMuted">
              {progress?.symbol ? `· ${progress.symbol}` : ""}
            </span>
          </div>
          <div className="w-24 border border-borderDefault">
            <div
              className="h-1 bg-bull transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="font-mono text-[10px] tnum text-textPrimary">
            {pct}%
          </span>
        </div>
      )}
      <Button
        testId="run-pipeline-btn"
        variant={running ? "default" : "primary"}
        onClick={trigger}
        disabled={running}
      >
        {running ? <Square size={11} /> : <Play size={11} />}
        {running ? "Running…" : "Run Pipeline"}
      </Button>
    </div>
  );
}
