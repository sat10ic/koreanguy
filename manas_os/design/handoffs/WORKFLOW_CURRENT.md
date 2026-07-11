# Current workflow constraint (user-set, 2026-07-11, TEMPORARY — this session)

- NO subagents (Sonnet/Codex/any) may be spawned in this session, temporarily.
- All coding work ships as handoff MDs in this folder, addressed to Gemini or GLM;
  the user feeds them and pastes results back.
- The orchestrator (Fable main thread) does direction, handoff authoring, reconciliation,
  wiring of single-writer files (app.py/schema.sql/cli), and QC — inline, itself.
- Agents already in flight when this was set may finish; nothing new starts.
