import { describe, expect, it } from "vitest";
import { initialJobState, jobReducer } from "./useJobStream.js";

describe("jobReducer", () => {
  it("deduplicates replayed cursors and keeps events strictly ordered", () => {
    const first = jobReducer(initialJobState, {
      type: "events",
      events: [{ event_id: 2, event_type: "step_started" }, { event_id: 1, event_type: "job_started" }],
    });
    const replayed = jobReducer(first, {
      type: "events",
      events: [{ event_id: 2, event_type: "step_started" }, { event_id: 3, event_type: "step_finished" }],
    });
    expect(replayed.events.map((event) => event.event_id)).toEqual([1, 2, 3]);
    expect(replayed.cursor).toBe(3);
  });

  it("loads the latest completed job as an honest idle snapshot", () => {
    const state = jobReducer(initialJobState, {
      type: "reset",
      payload: {
        job: { job_id: 9, status: "partial", run_date: "2026-07-10" },
        steps: [{ step_id: 1, seq: 1, status: "fail" }],
        artifacts: [],
      },
    });
    expect(state.job.status).toBe("partial");
    expect(state.steps).toHaveLength(1);
    expect(state.cursor).toBe(0);
  });

  it("does not move the cursor backwards when an older snapshot arrives", () => {
    const streamed = jobReducer(initialJobState, { type: "events", events: [{ event_id: 12 }] });
    const snapped = jobReducer(streamed, { type: "snapshot", payload: { latest_cursor: 8, steps: [] } });
    expect(snapped.cursor).toBe(12);
  });
});
