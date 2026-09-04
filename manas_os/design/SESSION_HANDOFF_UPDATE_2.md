# SESSION HANDOFF — UPDATE 2 (guided #10 + live-debate #7 + HMM #12 landed w/ open defects)

Read after `SESSION_HANDOFF_2026-07-12.md`. Gemini built handoffs #10/#7/#12; committed to preserve
(frontend `6b670f52`, backend `9971bde7`). Build clean, 783 pytest pass. GLM did a rigorous
inspection: `GUIDED_SYSTEM_DESIGN.md` + `GUIDED_SYSTEM_CONTRAST_PROOF.html`. Maintainer already
fixed the 3 P0 a11y contrast failures in the flow rail.

## STILL OPEN — next session must do these
1. **FAILING TEST**: `test_debate_push_idempotency::test_desk_debate_push_route_returns_409_when_in_flight`
   — the #7 on-demand push path does not 409 a second in-flight push (concurrency guard). Real bug.
2. **GLM punch-list** (grounded file:line in `GUIDED_SYSTEM_DESIGN.md` §6):
   - `StatusBadge` built but NOT wired into HMM / ALPHA / ChartDrawer organs (still bare text / raw
     `{"models":[]}` JSON). Wire LIVE/SHADOW/WARMING/EXPERIMENTAL/NEEDS-DATA.
   - TRADE PLAN route has no `TabPurposeHeader` — add `TAB_COPY.TRADE_PLAN` (copy in the doc §3-6)
     and render it in the `tradePlan` branch of App.jsx.
   - `order_ticket` rail button routes to DEBATE — should open TRADE PLAN for `step.ticket.symbol`
     (pass `onOpenTradePlan` into `GuidedFlowRail`).
   - Alpha to Debate to Shortlist relationship legend + cross-badges = still unbuilt (the one real
     remaining design+build item; reuse live `funnel` numbers from `/api/desk/debate`, no hardcoding).
3. **NOT live-QC'd**: the #7 streamed-debate path end-to-end, the AlphaLab changes, and whether HMM
   (#12) now persists `regime_hmm_states` or honestly reports WARMING — verify on the running app.
4. Still queued in `HANDOFF_INDEX.md`: 8 (live-default UI), 9 (guru TRADE PLAN panel), 11 (defects
   incl. SCANNERS-slow fix8 + journal-delete + shortlist verdict-contradiction + URL routing),
   12-remainder (regime replay).

## Priority for next session
Fix the failing 409 test + the 4 GLM punch-list items first (small, grounded) — that finishes the
guided-system centerpiece. Then live-QC #7/HMM/AlphaLab, then work the #11 defects batch.
