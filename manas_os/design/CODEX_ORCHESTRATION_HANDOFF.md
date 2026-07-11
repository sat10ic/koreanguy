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

## 2. Current state (commits on `emergent`)
- `0bee8cab` UI_OVERHAUL_HANDOFF reconciled (§4 superseded, §11 sequence).
- `b14f0bb2` UI v5 Wave 2 — DebateTab rebuilt to round-4 on real data + GROWW strike reconciliation.
- `b27037e6` UI v5 Wave 1 — light token layer + 19 primitives + shell CommandStrip (real VIX).
- `07293660` Discovery fix — detector_shortlist sorts by nearness not alphabet (RAIN/SKYGOLD now surface).

**In flight when this was written** (may already be committed by the maintainer — check `git log` + `git status`):
- UI-2a (Live Work schema+emitter) — a Codex build against `UI2_LIVEWORK_DIRECTION.md` §3/§4/§8-2a.
- Two external-model handoff files being drafted (see §4).
- A separate Codex discovery-validation run (verdict retrievable via `/codex:result`).

Servers: API `run_manas_api.py` on :8000 (restart after backend edits; confirm new code with a curl),
desk vite on :5174. `manas_os/data/manas.db` is the live DB (point-in-time; additive migrations only).

## 3. The sequence YOU execute (UI_OVERHAUL §11) — one slice at a time
1. **UI-2 Live Work** (IN PROGRESS): 2a schema+emit → 2b SSE endpoint+replay → 2c v5 Live Work inspector.
   Follow `UI2_LIVEWORK_DIRECTION.md` exactly (event_id AUTOINCREMENT = cursor; one ambient emitter on
   existing seams; append-only; keep `/api/pipeline/status` byte-compatible; never let emit() fail a run).
2. **UI-3 MARKET** — editorial regime canvas + opportunity map + the Live Work inspector (consumes UI-2).
   Design spec = UI_OVERHAUL §5 "MARKET". Compose in v5. Real payloads only.
3. **UI-4 SCANNERS + SHORTLIST** — SCANNERS by TradeTM-stage + parallel mechanism lanes (TradeTM-native/
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
