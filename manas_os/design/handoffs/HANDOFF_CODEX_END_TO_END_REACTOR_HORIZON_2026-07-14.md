# Handoff — Codex end-to-end repair, Reactor analogue and Horizon

Status: **implementation and QC complete; maintainer review required before
commit.** Canonical evidence is in
`../CODEX_END_TO_END_QC_REACTOR_HORIZON_2026-07-14.md`.

## What is now working

- Alpha Lab loads instead of spinning on parallel SQLite schema locks.
- Reactor-equivalent research is present as an honestly labelled EOD
  abnormal-activity analogue, wired to Alpha and Debate.
- Horizon experiment/failure/factor-health governance is persisted and shown.
- Scanner cards populate through one bounded batch request; the page no longer
  launches 18 full-universe jobs.
- The beginner daily flow is compatible and clickable.
- Debate observer, debate agents, chair and post-chair visual QC have distinct
  contracts again.
- Candidate research can populate before profile setup; actual sizing still
  refuses an incomplete profile.
- Live FSM SQLite-row crashes are fixed.

## Verification

- `pytest -q --tb=short`: **794 passed, 9 skipped**.
- `npm test`: **37 passed**.
- `npm run build`: pass; one ~605 kB bundle-size warning.
- `npx playwright test --reporter=line`: **2 passed**.
- Live `/api/scanners/presets?date=2026-07-13&include_hits=true`:
  **20 presets, 18 populated, 422 ms** on the final check.
- `ruff check --select F` on repaired Python surfaces: pass.
- `scripts/desk_gate.py`: hard-code and contrast pass; locked-files fails by
  design because four protected decision files changed and need review.

## Do not undo

- Do not rename the activity analogue to “Reactor Scale” or claim smart-money
  identity/direction from EOD bhavcopy.
- Do not make Alpha/Horizon output override eligibility, stops, quantity or
  portfolio heat.
- Do not restore request-time discovery fallback in preset card counts.
- Do not force the sector-downside model to display; it currently loses to its
  baseline.
- Do not combine the pre-debate observer with post-chair visual QC.
- Do not restore the three-phase PREP/LIVE/REVIEW payload in place of the
  compatible six-step flow.

## Maintainer review targets

1. Review locked diffs in `risk/plan.py`, `regime/governor.py`,
   `scanner/candidates.py` and `scanner/gates.py`.
2. Confirm that the large pre-existing study-folder deletions are intentional.
3. Keep the sector-downside model shadowed until a genuinely out-of-sample
   revision beats baseline.
4. Supply Fyers authentication for the remaining intraday backfill.
5. Add exact DSR only from a traceable formula source.

## Runtime state

The local API was restarted on `127.0.0.1:8000`; health and the repaired scanner
endpoint were verified. The existing Vite desk on `127.0.0.1:5173` was used for
the final Playwright journey.
