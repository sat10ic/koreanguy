# CODEX ORCHESTRATION HANDOFF — run the UI overhaul loop

Date: 2026-07-11 · Repo `C:\Users\satta\Downloads\koreanguy` · Branch `emergent`

**Purpose.** If Claude (the current orchestrator) is unavailable, YOU (Codex) drive the UI-overhaul
build loop to completion using this file. You are now BOTH executor and orchestrator: pick the next
slice in sequence, build it, self-QC to the bar below, commit per slice, update the ledgers, advance.
Use absolute interpreter paths (bare `python` fails in the sandbox). Never print the rupee glyph to a
Windows console (cp1252) — use "Rs".

---

## 1. Plan of record + controlling docs (read these; they win over memory)
- `manas_os/design/UI_OVERHAUL_HANDOFF.md` **§11** — the reconciled slice sequence + status table. THE roadmap.
- `manas_os/design/UI_BUILD_DIRECTION.md` — the v5 design-system build spec (tokens, primitives, data rules).
- `manas_os/design/UI2_LIVEWORK_DIRECTION.md` — Fable architecture spec for UI-2 (schema/emit/SSE/inspector).
- `manas_os/design/bakeoff/round4/debate_merged_light.html` — the LOCKED v5 LIGHT design language (source of truth for look).
- `CODEX_HANDOFF.md` §0 (product mission), §2 (LOCKED/safety), §3 (env quirks) — still binding.

The design language is LOCKED and LIGHT: canvas `#f7f6f2`, ink ramp, teal `#0d6c6c` / amber `#8a5a12` /
green `#14713f` / red `#ad2c34`, Fraunces (display) + Public Sans (UI) + IBM Plex Mono (numbers-only).
Tokens live in `manas_os/desk/src/styles/tokens.v5.css` (scoped under `.v5`). 19 reusable primitives in
`manas_os/desk/src/components/v5/` (import from `./components/v5/index.js`; do not re-create them).
UI_OVERHAUL §4's OLD dark/Barlow thesis is SUPERSEDED (see its §4 banner) — only its composition +
interaction rules still bind.

## 2. Current state (UPDATED 2026-07-12 — this section supersedes the old commit list)
**The entire UI overhaul (UI-1..UI-7) shipped**; the alpha behaviour wave, breadth enrichment,
live-loop stage 1 (paper), guided system (#10) and on-demand live-debate (#7) are all committed.
HEAD is ~`2a0e9a96`. Do NOT re-derive from the old commit list below — read `git log` +
`manas_os/design/SESSION_HANDOFF_2026-07-12.md` + `SESSION_HANDOFF_UPDATE_2.md` for the true state.

**Authoritative live docs (read these, in order):**
1. `SESSION_HANDOFF_2026-07-12.md` — full cold-start context, guardrails, ground truth.
2. `SESSION_HANDOFF_UPDATE_2.md` — latest delta + the OPEN punch-list.
3. `manas_os/design/handoffs/HANDOFF_INDEX.md` — the live queue + per-handoff status.
4. `manas_os/design/UX_AUDIT_FULL.md` + `GUIDED_SYSTEM_DESIGN.md` §6 — the UX gap ledgers.

**Workflow NOW (may differ from §-below):** the user runs external coders (Gemini/GLM) via the
handoff .md files; the orchestrator authors handoffs, reconciles paste-backs, wires single-writer
files (app.py/schema.sql/cli), QCs against LIVE running data (never trust a completion note's
proof — it has fabricated a "simulated" curl once), commits per-handoff, updates HANDOFF_INDEX.
If the user re-enables Agent-tool subagents, resume normal delegation.

**Immediate next work (highest first):** finish the guided-system centerpiece — fix the failing
`test_debate_push_idempotency` 409-in-flight test, then GLM's §6 punch-list (wire StatusBadge into
HMM/ALPHA/ChartDrawer organs; add TRADE_PLAN TabPurposeHeader; order_ticket→TRADE PLAN routing;
build the Alpha↔Debate↔Shortlist legend). Then HANDOFF_INDEX #11 defects, #8, #9.

Servers: API `run_manas_api.py` on :8000 (restart after backend edits; confirm with a curl),
desk `cd manas_os/desk && npm run dev` on :5174. `manas_os/data/manas.db` is live (point-in-time;
additive migrations only). Baseline test bar: `python -m pytest manas_os/tests -q` → all pass EXCEPT
the known `test_sector_downside` baseline AND (currently) the `test_debate_push_idempotency` 409 —
that second one is a REAL open bug to fix, not an allowed failure.

### Historical commit list (superseded — kept for reference only)
- `0bee8cab` UI_OVERHAUL reconciled · `b14f0bb2` Wave 2 DebateTab · `b27037e6` Wave 1 tokens+primitives
  · `07293660` discovery fix. (Everything after these is in `git log`.)

## 3. The sequence (HISTORICAL — the UI-2..UI-7 slices below are ALL DONE; kept for provenance)
1. **UI-2 Live Work** — DONE (shipped). 2a schema+emit → 2b SSE → 2c inspector all landed.
   `UI2_LIVEWORK_DIRECTION.md` was the spec (event_id cursor; ambient emitter; append-only).
2. **UI-3 MARKET** — DONE (editorial regime canvas + XP/MBI trends + breadth panels + inspector).
3. **UI-4 SCANNERS + SHORTLIST** — DONE (TradeTM-stage + parallel mechanism lanes) (TradeTM-native/
   Arora/Stocksgeeks); SHORTLIST around confirmation/next-trigger/provenance/timeline. Fixture already
   prepped: `manas_os/design/bakeoff/scanners_data.json`. Design spec = UI_OVERHAUL §5.
4. **UI-5 TRADE PLAN** (DEBATE already shipped) — manual execution ticket + management contract. §5.
5. **UI-6 POSITIONS + JOURNAL** — lifecycle canvas + validated mutation dialogs (kill native prompts);
   personal-edge-first journal with honest thin-sample states. **NOTE: may be delivered externally** (§4).
6. **UI-7 hardening** — delete/archive superseded App.css/components as replacements become canonical;
   full a11y/keyboard/contrast/reduced-motion + mobile/tablet/desktop + failure-state pass; beginner walk.

## 4. Work partition (DO NOT COLLIDE — parallel blind coders)
External models (GLM 5, Gemini) are given self-contained handoff files (`manas_os/design/handoffs/`)
and code screens the maintainer pastes back. To avoid mashups, ownership is by FILE:
- **YOU (Codex) own the in-repo, collision-prone work:** all backend (`api/app.py`, `db/schema.sql`,
  new modules), the shell (`App.jsx`, `main.jsx`), shared tokens/primitives (`styles/tokens.v5.css`,
  `components/v5/*`), and any slice not handed out. **`app.py` and `tokens.v5.css` are SINGLE-WRITER — only you.**
- **External models own ONLY their one screen's two files** (e.g. `JournalTab.jsx`+`JournalTab.v5.css`,
  `PositionsTab.jsx`+`PositionsTab.v5.css`). They are forbidden to touch app.py/tokens/index.js/App.jsx.
- **Reconciling external code:** when the maintainer pastes back a screen, (a) drop the two files in,
  (b) read the file's "BACKEND FIELDS REQUESTED" list and wire those fields into `app.py` yourself
  (single-writer), (c) QC value-by-value + rendered, (d) fix convention drift, (e) commit that screen.
  Never let an external file edit a shared file — move any such edit into your own reconciliation.

## 5. QC bar per slice (UI_OVERHAUL §7 — do NOT skip)
1. Build the slice to its direction-doc spec; no architecture changes beyond it.
2. Self-review the diff: correctness, one-writer-for-risk, state ownership, tests, a11y, no forbidden client math.
3. Verify EVERY value is real + correct (not "does it render"): curl the endpoint, DOM-check the rendered
   rows against the payload. Honest empty/thin states. No synthetic series in production.
4. Run: `python -m pytest manas_os/tests -q` (only the known `test_sector_downside::…beats_baseline`
   failure is allowed); `cd manas_os/desk && npm run build` (clean) + `npx vitest run`; restart API and
   curl-prove changed endpoints. Screenshots time out in the sandbox — do DOM/value checks instead and
   flag the pixel-gestalt as the user's call.
5. On pass: update `UI_OVERHAUL_HANDOFF.md` §11 status + append a slice ledger; `git add <explicit paths>`
   (NEVER `git add -A` — parallel agents + repo junk); commit per slice with a descriptive message ending
   `Co-Authored-By: <your id>`; then advance to the next slice.

## 6. HARD guardrails (binding — violations are defects)
- **Money-math is LOCKED** (5% stop cap, 1.5 R:R floor, risk bands, concurrency, NO_TRADE⇒0). Change ONLY
  via `WAVE_L_RISK_PROPOSAL.md` + explicit user sign-off + replay evidence. UI never invents stop/target/
  qty/exposure — display server values verbatim (one-writer-for-risk). Deterministic risk is final authority.
- **Manual execution only** — no order routing. `agents.telegram_live:false` stays until the user flips it.
- **Secrets:** Telegram/Fyers creds live ONLY in gitignored `manas_os/config.yaml` — never commit or echo them.
  Repo is PUBLIC.
- **DB:** additive/guarded migrations only; point-in-time; never overwrite history; append-only for job events.
- **Don't break** the working `run-eod` pipeline or `/api/pipeline/status`; keep existing routes working
  until their replacement is canonical (UI-7 deletes old code, not before — no two live shells).
- **No new chart libraries; no synthetic data** in production — plain SVG from real fields, or "—".
- Pine ports (© finallynitin/Triyambak) personal-use only. Absolute python paths. No rupee glyph to console.

## 7. If you get stuck / a slice is ambiguous
Prefer the direction docs over guessing. If a genuine architecture fork appears (hard-to-reverse, or a
money-math/safety implication), STOP that slice, write the question + your recommendation into this file
under a "## OPEN QUESTIONS" section, continue with the next independent slice, and surface it for the user
rather than deciding unilaterally.
