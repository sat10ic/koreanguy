# WAVE 1 FIX SPEC (Codex task, 2026-07-17)

Fix items C1-C4, I1, I2, I3, I5 from manas_os/design/AUDIT_LEDGER_2026-07-17.md (read it first).
Repo: FastAPI backend manas_os/api/app.py, Vite/React desk manas_os/desk/src (v5 light tokens).
HARD RULES: no money-math changes (risk/plan.py semantics), no gate-logic changes, no git commit.

1. C1 one-voice: TODAY guided-flow step 4 + verdict panel + DEBATE must agree. When agents_debate
   produced 0 verdicts, flow step 4 copy: "Council didn't run last night (model errors) — 4
   gate-passed setups are ungraded. Review them manually on DECIDE or retry the council."
   Verdict panel keeps SIT OUT + same clause. Derive both from ONE payload field.
2. C2 merge the two shell banners into one state machine {fresh | awaiting_tonight (~19:00 IST)
   | run_failed(reason)} — never two contradictory lines.
3. C3 DEBATE pipeline-note: humanized copy (models errored/rate-limited, N ungraded, retry button
   wired to existing debate rerun endpoint); raw JSON only in expert drill-in.
4. C4 WATCH empty-state: shortlist empty but scan_candidates has rows for the date → render
   "tonight's gate-passed candidates" (symbol, setup_type, grade, entry/stop) with existing
   TAKEN/SKIPPED buttons.
5. I1 one float formatter for user-visible numbers (1-2 decimals + unit): ShortlistTab RVOL20
   16-decimal leak, heat "0.0000 % used", grep other raw renders.
6. I2 dev-speak: "NH/NL -4 (up_4pct-down_4pct (NH/NL not ingested; proxy))" → "New highs vs
   lows: -4 (proxy from 4% moves)" + info-dot; shortlist history "(allowed: [" truncated dumps →
   plain sentence.
7. I3 debated-strip "65dL" chip: same static value for all symbols — replace with real per-symbol
   % off 65d low from payload, or drop chip.
8. I5 ALPHA: "20d residual" → "vs market (20d)" + info-dot; "Leadership" info-dot; header →
   "RESEARCH RANKING — evidence only, never sizes a trade"; blank sectors → "—".

Verify: python -m pytest manas_os/tests -q green (PYTHONPATH=repo root needed for -m invocations);
cd manas_os/desk; npm run build clean. Report per-item done/skipped + files + results.
