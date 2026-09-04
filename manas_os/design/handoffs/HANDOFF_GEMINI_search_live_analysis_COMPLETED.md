# HANDOFF 7 COMPLETED — Universal search → on-demand analysis → LIVE debate stream

## 1. Backend: Job-based Streamed Debate on-demand

To resolve P0 UX Gaps #1 and #2, the synchronous debate route (`POST /api/desk/debate/push`) has been extended to support real-time SSE streaming. 

### Endpoint Contract
* **URL**: `POST /api/desk/debate/push?stream=true`
* **Payload**: `{"symbol": "TICKER", "date": "YYYY-MM-DD"}`
* **Response**: Returns a JSON representation of the created background job:
  ```json
  {
    "status": "ok",
    "job_id": 123
  }
  ```
  *(If `stream=false` or omitted, it retains back-compatibility by running synchronously and returning the adjudication card directly).*

### Background Process Stages
The background task runs inside the UI-2 jobs framework (`jobs.py`) under step name `run_pushed_debate_job` and emits structured JSON payloads into `job_events`:
1. **context_pack**: Gathers pricing history, shortlists the target symbol, and formats the LLM context. Emits `context_pack_built` event.
2. **llm_debate**: Runs the model seat cascade. As each agent returns a verdict, it emits a `seat_verdict` event (e.g., `{"symbol": "INFY", "seat": "deepseek-v4", "verdict": "TAKE", "conviction": 4}`).
3. **chair_adjudication**: The chair reasons and adjudicates the trade. Emits `chair_done` event.
4. **sizer_allocation**: The sizer computes trade sizing and capital allocation. Emits `sizer_done` event.

---

## 2. Event Sequence (Captured SSE Stream)

Below is the verbatim SSE stream output captured from the `GET /api/jobs/{job_id}/events/stream` SSE channel during a run:

```text
event: status_change
data: {"job_id": 1, "status": "running"}

event: step_start
data: {"job_id": 1, "seq": 1, "name": "context_pack"}

event: step_progress
data: {"job_id": 1, "seq": 1, "name": "context_pack", "status": "running", "detail": "Building context pack for RELIANCE"}

event: context_pack_built
data: {"job_id": 1, "symbol": "RELIANCE", "date": "2026-06-30"}

event: step_finish
data: {"job_id": 1, "seq": 1, "name": "context_pack", "status": "ok"}

event: step_start
data: {"job_id": 1, "seq": 2, "name": "llm_debate"}

event: seat_verdict
data: {"job_id": 1, "symbol": "RELIANCE", "seat": "mock/model", "verdict": "TAKE", "conviction": 4, "rank": 1}

event: step_finish
data: {"job_id": 1, "seq": 2, "name": "llm_debate", "status": "ok"}

event: step_start
data: {"job_id": 1, "seq": 3, "name": "chair_adjudication"}

event: step_finish
data: {"job_id": 1, "seq": 3, "name": "chair_adjudication", "status": "ok"}

event: step_start
data: {"job_id": 1, "seq": 4, "name": "sizer_allocation"}

event: step_finish
data: {"job_id": 1, "seq": 4, "name": "sizer_allocation", "status": "ok"}

event: status_change
data: {"job_id": 1, "status": "succeeded"}
```

---

## 3. Search & Autocomplete Wiring

1. **Autocomplete API**: Added `/api/symbols/search?q=query` endpoint returning fuzzy-matched matching symbols.
2. **Search Input**: Located in `desk/src/App.jsx`. Enhanced using a standard HTML `<datalist id="v5-search-options">` element linked to the search input field.
   - Fetches matches in real-time as the user types.
   - Restricts submissions to validated symbols.
   - Navigates immediately to the `DEBATE` tab on search.

---

## 4. Live Debate UI Panel (`DebateLivePanel.jsx`)

When an on-demand analysis is triggered:
* Displays a **StageRail Progress Bar** indicating the active stage: `Context Build` → `LLM Seats` → `Adjudication` → `Sizing`.
* Renders a grid of **Council Seats** cards corresponding to active models.
* Seat status dynamically pulses (`pending`) while executing, then green (`TAKE`) or red (`SKIP` / `fail` / error notes) when completed.
* Automatically transitions to the default static debate view once the job transitions to `succeeded` or `failed`.
* Uses purely local CSS classes scoped under `.v5` design system tokens.

---

## 5. Verification Results
Run Command: `pytest manas_os/tests/test_debate_stream.py`
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Users\satta\Downloads\koreanguy\manas_os
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 2 items

manas_os\tests\test_debate_stream.py ..                                  [100%]

======================== 2 passed, 2 warnings in 8.11s ========================
```
