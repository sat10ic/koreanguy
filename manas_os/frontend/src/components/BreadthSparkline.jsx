import { useEffect, useState } from "react";
import { getBreadthHistory } from "../api.js";
import MiniSpark from "./MiniSpark.jsx";

const DAYS = 20;

/**
 * BreadthSparkline — keeps its own fetch + caption logic (design §1.6:
 * "REWORK — extract <MiniSpark>; keep the breadth caption logic"); the
 * sparkline math itself now lives in the shared <MiniSpark>.
 */
export default function BreadthSparkline() {
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    getBreadthHistory(DAYS)
      .then((d) => !cancelled && setState({ loading: false, error: null, data: d }))
      .catch((e) => !cancelled && setState({ loading: false, error: e.message, data: null }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) return <BreadthSkeleton />;
  if (state.error || !state.data?.available || state.data.rows.length === 0) {
    return <span className="font-mono text-[14px] text-ink3">&mdash;</span>;
  }

  const rows = state.data.rows;
  const values = rows.map((r) => r.pct_above_20dma);
  const caption = breadthCaption(rows.map((r, i) => ({ i, v: r.pct_above_20dma })).filter((p) => p.v != null));

  return (
    <div className="min-w-0">
      <div className="h-7 w-full">
        <MiniSpark values={values} />
      </div>
      <div className="truncate font-mono text-[9px] leading-none text-ink3">{caption}</div>
    </div>
  );
}

function breadthCaption(values) {
  if (values.length < 2) return "breadth flat";

  const last = values[values.length - 1].v;
  const prev = values[values.length - 2].v;
  if (last === prev) return "breadth flat";

  const direction = last > prev ? "up" : "down";
  let streak = 1;
  for (let i = values.length - 2; i > 0; i -= 1) {
    const delta = values[i].v - values[i - 1].v;
    if ((direction === "up" && delta > 0) || (direction === "down" && delta < 0)) {
      streak += 1;
    } else {
      break;
    }
  }

  return direction === "up" ? `breadth improving ${streak}d` : `breadth fading ${streak}d`;
}

function BreadthSkeleton() {
  return (
    <div className="min-w-0">
      <div className="h-7 w-full animate-pulse rounded bg-hairline2" />
      <div className="mt-1 h-2 w-20 animate-pulse rounded bg-hairline" />
    </div>
  );
}
