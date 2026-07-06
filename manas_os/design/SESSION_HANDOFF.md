# SESSION HANDOFF — read this first, then the files it points to

Repo: `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Manas AI Trading OS — beginner
NSE swing-trading cockpit. FastAPI :8000 + React/Vite :5173, SQLite `manas_os/data/manas.db`.

## Binding rules (do not relitigate)
- Rules-first, no black-box scores. Manual execution only — never order routing.
- Anti-mashup: one writer per metric, one ranked number per screen, no dormant code.
- `manas_os/design/Feedback_woolly_peacock plan` (aka the canonical plan, path in
  `~/.claude/plans/c-users-satta-downloads-manas-os-v2-md-woolly-peacock.md`) has every LOCKED
  threshold (stop caps, R:R floor, regime caps, risk profiles). Never re-derive these ad hoc.
- **Delegate ALL coding to Codex** (`codex:codex-rescue` subagent, background). Main thread
  orchestrates + writes specs only. **One Codex batch at a time** — do not fan out multiple
  concurrent jobs (burns credits fast, caused merge collisions).
- Codex sandbox often lacks `python`/`py` on PATH — tell it to fall back to
  `C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe`.

## The 3 files to read next (in order)
1. `manas_os/design/CODEX_HANDOFF.md` — the execution queue. BATCH 1/2 done. BATCH 3
   (Position Coach), 4 (Telegram digest), 5 (mentor checklists), 6 (regime history strip) were
   launched — check the `[x]`/`[ ]` boxes at the bottom of this file for what actually landed;
   Codex reports may say done before boxes are ticked, verify against the file itself, not
   just the chat.
2. `manas_os/TASKS.md` — current task board (T-numbers mirror the plan). Sync after each batch.
3. `manas_os/design/LEARNINGS.md` — append-only threshold/finding log, dated entries at the
   bottom. Read the last 3-4 entries for the most recent ground truth (e.g. the 2026-07-06
   entry on a DB-lock false alarm and the rr=2.0 stale-data false alarm — don't re-diagnose
   these, they're resolved).

## The rest of `manas_os/design/*.md` — read on demand, not upfront (skip unless the task touches them)
- `OWNERS_GUIDE.md` — plain-language explainer for the USER (not the agent) of every
  deterministic mechanism + what's tweakable. Read only if the user asks a "how does X work"
  question you should answer in their terms.
- `WIREFRAMES.md` — ASCII panel-by-panel layout spec for Phase 3 screens. Read before touching
  any frontend panel's layout/structure so you don't invent a different one.
- `BEGINNER_EXPERT_SPEC.md` — the density-toggle mechanics (densityLabels.js, ShowDetails,
  per-surface conditional renders). Read before touching beginner/expert axis work (e.g. #29).
- `STATE_OF_TOOL.md` / `CRITICAL_REVIEW_FABLE.md` — pre-Manas-2.0 ground truth + the review that
  triggered the whole rebuild. Historical context only, largely superseded by LEARNINGS.md now.
- `DESIGN_GUIDANCE.md`, `REDESIGN_SPEC.md`, `LIVE_LOOP_FABLE.md`, `STRATEGY_REFERENCE.md`,
  `RESEARCH_PROMPT.md`, `NEXT_STEPS.md` — earlier-phase design/strategy notes (some pre-date
  the canonical plan). If something in here conflicts with the canonical plan or LEARNINGS.md,
  the canonical plan + LEARNINGS win — these are inputs that were already synthesized in, not a
  parallel source of truth. Only open one if you need history on a specific past decision.
- `Feedback/` subfolder — the 8 raw research docs the canonical plan was synthesized from.
  Don't re-read these; the plan already distilled them.

## To continue
1. Run `python -m pytest manas_os/tests -q` from repo root yourself first — get the REAL
   passing count before trusting anything a subagent claimed. Baseline is now **170** (was 163
   at session start, 167 when Fable last checked — BATCH 3-6 added tests in between).
2. Check which of BATCH 3/4/5/6 actually finished + passed, by reading CODEX_HANDOFF.md's
   checkboxes and running the suite — not by trusting agent self-reports.
3. Next unclaimed queue slot: pick the next `[ ]` task in CODEX_HANDOFF.md, or if all batches
   there are done, write the next one following the same zero-judgment spec style (exact file
   paths, exact function contracts, exact test assertions) so Codex needs no judgment calls.
4. Remaining known-open work (see TASKS.md for full list): T3.9 Position Coach (batch 3, was
   relaunched fresh after the first launch got stuck "queued" 18+ min without ever starting —
   check its actual status, don't assume it ran just because it was launched twice),
   T4.1 Telegram (batch 4 = slice 1 only, live push is NOT built), #17 mentor checklists
   (batch 5), #1 regime history strip (batch 6), #21 live intraday loop (NOT started, needs
   Fyers WS creds — biggest remaining chunk), #29 Axis D beginner/expert column enforcement
   (deferred, noted in LEARNINGS).
5. ~~Verification debt~~ **CLEARED 2026-07-07 (Fable browser-QC pass).** `npm run build` clean;
   all 8 C7-C16 endpoints 200; clicked through Regime/Setups/Watchlist/Journal live. Found+fixed
   during the pass (all committed): (a) stray C12 guard block pasted into `journal_add`
   (`NameError: trade_id` — POST /api/journal was fully broken); (b) Rules-of-Hooks violation in
   RegimeSummary.jsx (`useDensity()` below early returns — regime screen render bug); (c) the C8
   contradiction chip was NOT actually fixed by Codex — chip read breadth fields the summary
   payload never had; `/api/regime/summary` now exposes `breadth_20dma_pct` (one writer) and the
   chip agrees with the posture line; (d) bogus double-close assertion in the C13 banner test
   (re-closing a closed trade now asserted 404). Suite: 174 green. Remaining un-QC'd: ChartDrawer
   visual detail (C6) — renders but not pixel-inspected; do a quick eyeball when convenient.
6. Also rerun the full-history replay (`manas replay`) with the current code — the last known
   result had the REFUSED cohort outperforming the PASSED cohort at T+10, which means the gate's
   edge is still unproven, not confirmed. Don't report "the gate adds value" until this is
   resolved on full history, not the one narrow window checked so far.
7. After each batch: `git add -A manas_os && git commit` (do NOT commit `manas_os/data/`,
   `manas_os/config.yaml` — already gitignored) then `git push origin emergent`.

## 2026-07-06 — Fable progress consult (independent re-score)
Consulted Fable for an honest re-score against the original 3/10 `CRITICAL_REVIEW_FABLE.md`
(the review that triggered this whole rebuild). **Verdict: 6.5/10 — real machinery now, not
theatre, but the edge itself is still statistically unproven and the journal moat has zero
real data yet (expected — needs live months).** Full detail in `LEARNINGS.md`'s
"2026-07-06 — Fable consult + integrity bug in structural_target()" entry; short version:
- Original 3/10 sins (gate doesn't refuse, garbage stops/EPS/R:R, cross-panel contradictions)
  are genuinely fixed and verified in code — not just claimed. Journal plumbing is real but
  empty (needs live use to fill).
- **Caught and fixed a real integrity bug**: `risk/plan.structural_target()` was picking the
  FARTHEST qualifying swing high instead of the nearest (inflating R:R for every candidate with
  >1 swing high in its window), compounded by a non-strict `>=` comparison letting flat/tied
  bars falsely qualify as swing highs (same degenerate-tie class already fixed once this build
  in the AVWAP anchor). Both fixed same-day; 170 tests green after. Existing tests didn't catch
  either bug because every fixture used only a single swing high — a follow-up test with two
  swing highs at different distances would lock in the "nearest wins" contract.
- Flagged the C7-C16 verification debt and the unresolved replay caveat above (both now items
  4-6 in "To continue"). Also flagged: audit whether `market_cap_cr` coverage is thin enough
  that the MAX/lottery/pump gates are silently passing on `None` mcap (`scanner/gates.py`
  ~L136,143) — if so the small-cap trap exclusions the PEAD study validated aren't firing for
  those names.

## Open design thread: "organic/smart" vs fixed rules (user-raised, 2026-07-07)
The user is uneasy that a fully deterministic gate misses good calls (and the last replay window
supports the worry — refused near-misses outperformed passed names). The agreed direction is in
`VIZ_BRAINSTORM.md` Parts 2-3: adaptivity in the PARAMETERS (percentile-fitted thresholds,
quarterly calibration, override ledger, learned rank among survivors), determinism in the
DECISION (gate stays reproducible, LLM proposes but never generates a gating/sizing number).
First concrete steps if picked up: the near-miss verdict chart (viz #1), then the override
ledger (A5), then the LLM devil's-advocate with acceptance ledger (L2). Do not re-litigate
LLM-as-gate — it recreates the original 3/10 black-box problem.

## Known footguns hit this session
- `codex-companion.mjs cancel <task-id>` is broken on Windows (taskkill arg-parse error) —
  zombie "queued" jobs can't be cancelled. They historically never start (two sat >4h without
  running), so leave them; just don't count them as live work, and launch retries with a fresh
  task rather than fighting cancel.
- Stale python.exe child processes can hold a SQLite write lock long after the job that
  spawned them "finished" — `tasklist` + kill orphans before assuming a background replay is
  still the cause of a 500.
- Persisted DB rows can predate a code fix — if live data looks wrong, re-run the pipeline
  stage on current code before concluding it's a live bug.
- `git bash` here sometimes fails `python -c "..."` imports that work fine from a script file
  — write a temp `.py` file and run it, don't rely on `-c`.
