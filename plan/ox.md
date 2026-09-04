# TraderLog Revival Plan — restore the shipped UI, complete the data pipeline, surface the analytics

**Status:** drafted 2026-08-25, owner-triggered after UI rollback was discovered.
**Root causes (measured):** working tree lost the scouting×wire UI build; 317
unreconciled roots (incl. 146 Manas Arora); breadth stale at 2026-08-21;
tape_metrics + activity signals built but never surfaced in any screen.

---

## Phase 0 — Restore the shipped UI (git archaeology + re-verify)
- Locate the scouting×wire UI in git history (`git log --all -- traderlog/ui/src/screens/Today.jsx` etc.); restore Today/Market/Symbol/lenses/tape-column files from the verified commits (cf59be96 lineage).
- Rebuild + rerun the full verification battery (build, pytest, 1920×1080 browser probe).
- **Done-test:** all 8 screens present (Today/Ledger/Traders/Radar/Library/Market/Symbol/Style), Radar tape column live, Ledger lenses live.

## Phase 1 — Complete the Ledger data (agent)
- Run reconcile over ALL 317 remaining roots (agentic in-chat path — proven, rate-free) prioritizing newest-first so Manas Arora's recent trades land first (146 standalone roots with symbols).
- Specifically audit Manas's closes: sample 10 of his recent closed trades end-to-end (post → thread → position row) and fix systemic issues found (e.g., exits posted as separate standalone roots need linking via run_link_pass).
- **Done-test:** 0 unreconciled roots with stated numbers; Manas closed count reflects reality; spot-checks verbatim.

## Phase 2 — Breadth refresh (operational)
- Drop newest bhavcopy CSVs into `data/bhavcopy/` (owner/source action if not auto-available), run `python run_w4.py`, verify regime_daily extends past 2026-08-21.

## Phase 3 — Surface stock-level analytics + TV charts (agent)
- Rebuild/restore Symbol page: lightweight-charts candles + **tape_metrics panel** (ADR, tightness, VCP proxy, IB chains, burst/gap flags, location vs SMAs/52w — from `derive/tape_metrics.py`, 41 tests, already built) + who-said-what timeline + positions overlay.
- Wire **alpha_activity_signals** (W5, 535,991 rows verified intact) into the Symbol payload: activity score/surge flags alongside tape metrics.
- Wire `derive/tape_metrics.py` into the Symbol API payload.
- **Done-test**: RATEGAIN/DIXON render candles + metrics + activity flags; invalid symbol renders honest empty state.

## Phase 4 — Traders + Library value (agent)
- Re-run W6 style derivation after Phase 1 (more closed positions → more traders clear thresholds).
- Materialize `edu_links` (principle ↔ position_events topic matching, cited) → Library practice-vs-preach comes alive; Traders gains preach scores.
- Traders screen additions below-threshold: open positions, last-30d activity, watchlist overlap — real content instead of bare "too few".

## Phase 5 — Close-out
- Docs: WIREFRAMES/VISUAL_LANGUAGE reconciliation, AUDIT_LEDGER addendum, MODEL_WORK_LOG records for every executor, HANDOFF final.
- Full suite + checks green; browser pass all tabs; nothing committed.

## Survived-the-rollback inventory (verified 2026-08-25)
- adopted/activity.py + activity_pipeline.py + run_w5.py ✅
- alpha_activity_signals: 535,991 rows / 1,970 symbols ✅
- derive/tape_metrics.py + 41 tests ✅
- derive/style.py + trader_style 17 rows ✅
- derive/insight_tables.py + themes 39 / breadth_notes 284 / edu_items 549 ✅
- derive/disagreement.py engine ✅ (UI wiring pending)
- run_recon.py orchestrator + tests ✅

## Execution
- Agents: Phase 0 (restoration), Phase 1+2 (data), Phase 3 (analytics surface), Phase 4 (style/library) — spawned in dependency order, verified personally by the orchestrator.
- Nothing committed until owner QC.
