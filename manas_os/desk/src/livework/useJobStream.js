import React, { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from "react";
import {
  cancelJob,
  createJob,
  fetchJob,
  fetchJobEvents,
  fetchJobs,
  jobEventsUrl,
  retryJobStep,
} from "../api.js";

export const TERMINAL_JOB_STATUSES = new Set(["succeeded", "partial", "failed", "cancelled", "interrupted"]);
const STREAM_EVENT_TYPES = [
  "job_started", "step_started", "step_finished", "step_failed", "artifact",
  "job_finished", "cancel_requested", "retry_started", "seat_verdict", "seat_failed",
];

export const initialJobState = { job: null, steps: [], artifacts: [], events: [], cursor: 0 };

export function jobReducer(state, action) {
  if (action.type === "reset") return { ...initialJobState, ...(action.payload || {}) };
  if (action.type === "snapshot") {
    const payload = action.payload || {};
    return {
      ...state,
      job: payload.job || state.job,
      steps: payload.steps || state.steps,
      artifacts: payload.artifacts || state.artifacts,
      // A metadata snapshot may race ahead of the stream. Only consumed event
      // rows may advance the cursor, otherwise an event can be skipped forever.
      cursor: state.cursor,
    };
  }
  if (action.type === "events") {
    const incoming = (action.events || []).filter((event) => Number(event.event_id) > state.cursor);
    if (!incoming.length) return action.job ? { ...state, job: action.job } : state;
    const byId = new Map(state.events.map((event) => [Number(event.event_id), event]));
    incoming.forEach((event) => byId.set(Number(event.event_id), event));
    const events = [...byId.values()].sort((a, b) => Number(a.event_id) - Number(b.event_id));
    return {
      ...state,
      job: action.job || state.job,
      events,
      cursor: Number(events[events.length - 1].event_id),
    };
  }
  return state;
}

const LiveWorkContext = createContext(null);

export function useLiveWork() {
  const value = useContext(LiveWorkContext);
  if (!value) throw new Error("useLiveWork must be used inside LiveWorkProvider");
  return value;
}

export function LiveWorkProvider({ children, onJobFinished }) {
  const [state, dispatch] = useReducer(jobReducer, initialJobState);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transport, setTransport] = useState("idle");
  const stateRef = useRef(state);
  const finishedRef = useRef(null);
  const onFinishedRef = useRef(onJobFinished);
  stateRef.current = state;
  onFinishedRef.current = onJobFinished;

  const refreshSnapshot = useCallback(async (jobId) => {
    const snapshot = await fetchJob(jobId);
    dispatch({ type: "snapshot", payload: snapshot });
    return snapshot;
  }, []);

  const chooseJob = useCallback(async (jobId, { reveal = false } = {}) => {
    setError(null);
    setLoading(true);
    if (reveal) setOpen(true);
    try {
      const [snapshot, eventPage] = await Promise.all([fetchJob(jobId), fetchJobEvents(jobId, 0, 1000)]);
      dispatch({ type: "reset", payload: { job: snapshot.job, steps: snapshot.steps, artifacts: snapshot.artifacts } });
      dispatch({ type: "events", events: eventPage.events, job: eventPage.job });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchJobs(1)
      .then((body) => {
        if (active && body.jobs?.[0]) return chooseJob(body.jobs[0].job_id);
        if (active) setLoading(false);
        return null;
      })
      .catch((err) => {
        if (active) {
          setError(String(err));
          setLoading(false);
        }
      });
    return () => { active = false; };
  }, [chooseJob]);

  const jobId = state.job?.job_id;
  const terminal = TERMINAL_JOB_STATUSES.has(state.job?.status);

  useEffect(() => {
    if (!jobId || terminal) {
      setTransport(jobId ? "complete" : "idle");
      if (jobId && finishedRef.current !== jobId) {
        finishedRef.current = jobId;
        onFinishedRef.current?.(state.job);
      }
      return undefined;
    }

    let stopped = false;
    let source = null;
    let pollTimer = null;
    let snapshotTimer = null;

    const applyEvent = (raw) => {
      try {
        const event = JSON.parse(raw.data);
        dispatch({ type: "events", events: [event] });
      } catch (_) {
        // A malformed telemetry row is ignored; the next snapshot remains authoritative.
      }
    };
    const poll = async () => {
      if (stopped) return;
      try {
        const page = await fetchJobEvents(jobId, stateRef.current.cursor, 500);
        dispatch({ type: "events", events: page.events, job: page.job });
        await refreshSnapshot(jobId);
      } catch (err) {
        if (!stopped) setError(String(err));
      }
    };
    const startPolling = () => {
      if (pollTimer || stopped) return;
      setTransport("poll");
      poll();
      pollTimer = setInterval(poll, 2500);
    };

    if (typeof EventSource === "undefined") {
      startPolling();
    } else {
      setTransport("sse");
      source = new EventSource(jobEventsUrl(jobId, stateRef.current.cursor));
      STREAM_EVENT_TYPES.forEach((type) => source.addEventListener(type, applyEvent));
      source.addEventListener("done", () => refreshSnapshot(jobId).catch(() => {}));
      source.onerror = () => {
        source?.close();
        source = null;
        startPolling();
      };
      snapshotTimer = setInterval(() => refreshSnapshot(jobId).catch(() => {}), 2500);
    }

    return () => {
      stopped = true;
      source?.close();
      if (pollTimer) clearInterval(pollTimer);
      if (snapshotTimer) clearInterval(snapshotTimer);
    };
  }, [jobId, terminal, refreshSnapshot]);

  const start = useCallback(async ({ date, fetchSources = true } = {}) => {
    setError(null);
    setOpen(true);
    setLoading(true);
    try {
      const response = await createJob({ date, fetchSources });
      const nextId = response.job_id;
      if (!nextId) throw new Error("The update started without a job ID.");
      finishedRef.current = null;
      await chooseJob(nextId, { reveal: true });
      return response;
    } catch (err) {
      setError(String(err));
      setLoading(false);
      throw err;
    }
  }, [chooseJob]);

  const cancel = useCallback(async () => {
    if (!jobId) return;
    await cancelJob(jobId);
    await refreshSnapshot(jobId);
  }, [jobId, refreshSnapshot]);

  const retry = useCallback(async (stepId) => {
    if (!jobId) return;
    await retryJobStep(jobId, stepId);
    await refreshSnapshot(jobId);
    setOpen(true);
  }, [jobId, refreshSnapshot]);

  const value = useMemo(() => ({
    ...state, open, setOpen, loading, error, transport, start, cancel, retry, chooseJob,
    running: !!state.job && !TERMINAL_JOB_STATUSES.has(state.job.status),
  }), [state, open, loading, error, transport, start, cancel, retry, chooseJob]);

  return React.createElement(LiveWorkContext.Provider, { value }, children);
}

