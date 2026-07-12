# SESSION HANDOFF — UPDATE 3 (2026-07-12, Fable orchestration session, stopped by user)

Read after `SESSION_HANDOFF_2026-07-12.md` + `SESSION_HANDOFF_UPDATE_2.md`. Queue truth:
`manas_os/design/handoffs/HANDOFF_INDEX.md`.

## Workflow state (CHANGED this session)
- User LIFTED the no-subagent rule: normal delegation again — Sonnet subagents code,
  orchestrator (Fable) QCs against the live app and commits. Gemini/GLM paste-back flow no
  longer required unless user reinstates it.
- User ordered caveman-mode replies (memory: feedback-caveman-mode.md) — terse fragments;
  code/commits/security normal.
- Orchestration doctrine adopted from github.com/plugin87/ux-ui-agent-skills:
  mechanical gates + "gates don't prove pixels" rendered pass. See `scripts/desk_gate.py`.

## Landed this session (all committed + pushed, branch emergent)
1. `0c0df56d` — **#13 guided-system punch-list A-D**: 409 in-flight guard fixed for real
   (Sonnet's route-order fix + orchestrator-caught bug: async stream path checked but never
   REGISTERED the key — registration added in route, release in run_pushed_debate_job finally,
   spawn-failure rollback); StatusBadge wired (DEBATE HMM WARMING, ChartDrawer EXPERIMENTAL;
   AlphaLab NEEDS-DATA pre-existed); TRADE_PLAN TabPurposeHeader; order_ticket rail button →
   TRADE PLAN. Verified: idempotency 3/3, 79 debate/desk tests, suite 784+1-known-fail, live
   DOM (sbadge--warming with real "warming up (2/20)").
2. `fce0b176` — **#13b legend + cross-badges + ALPHA row actions** (orchestrator-built):
   new v5 primitive `ListRelationshipLegend.jsx` (+CrossBadges +useListMembership) — live
   funnel from /api/desk/debate (never hardcoded), role lines, cross-tab nav; replaced
   AlphaLab's old static collapsed legend (dedup). Badges: ⚖ debated / ★ on watch / ◈ shadow #N
   (icon+text). ALPHA leaders rows: push-to-debate + add-to-watch actions (closes audit §11 P0).
   DEBATE deliberately gets badges only — funnel already on its ContextRow.
3. `b003d492` — **`scripts/desk_gate.py`** standing mechanical wave-gate: raw-hex lint vs v5
   tokens (comments stripped — "#13b" false-positive fixed in fce0b176), WCAG contrast on 8
   locked token pairs, money-math zero-diff. Baseline now **53 findings** (all #14 debt:
   ChartDrawer 47, MarketTab 3, viz.js 3 — see below). Rule: a wave may not ADD findings.

**Guided-system (#10/#13/#13b) is now COMPLETE** per GLM GUIDED_SYSTEM_DESIGN §6.

## UNFINISHED — do this first
- **UX/UI craft audit FAILED** — the Sonnet subagent (interface-design + web-design-guidelines
  skills) hit the account session limit mid-run (reset 10:10pm IST 2026-07-12) and wrote NO
  file. `manas_os/design/UI_CRAFT_AUDIT_2026-07-12.md` does NOT exist. RE-RUN it next session.
  Context: user says "the tool still looks bad" — this ranked audit is the answer that unblocks
  a targeted craft wave. Prompt pattern that was in flight: rendered-first (screenshot every
  tab via mcp__Claude_Browser__* against desk :5174 / API :8000), apply the interface-design +
  web-design-guidelines skill checklists (not vibes), AESTHETIC_BAR 2026-07-11 §"Shell and
  comprehension defects" blockers are LAW, output = verdict line + ranked P0/P1/P2 defect table
  (each traceable to [rendered]tab or [code]file:line) + a <=10 cheap-wins list. The audit is
  the input to the next real UI wave; without it, UI work is guesswork.

## Queue after that (HANDOFF_INDEX order)
1. **#14 ChartDrawer v5 restyle + single-theme cleanup** — desk_gate found 47 raw dark-theme
   hex in desk/src/ChartDrawer.jsx (THE "legacy black island" locked release blocker,
   AESTHETIC_BAR 2026-07-11 §1) and it mounts on 5 tabs; also retire legacy desk/src/tokens.css
   (second theme source, still imported in main.jsx) + MarketTab(3) + viz.js(3) hex.
   Done-test: `python scripts/desk_gate.py` → 3/3 PASS.
2. **#11 UX defects batch** (shortlist verdict-contradiction, journal delete UI, positions
   debug-string leak + freshness, scanners offscreen/scroll-to, date dead-ends, URL routing,
   trade-plan chart/persist/log-to-journal).
3. **#12 live-QC remainder** — verify HMM persists regime_hmm_states or honestly WARMING on
   the running app; #7 streamed-debate end-to-end QC.
4. **#8** live-default UI finish, **#9** guru trade-plan panel.

## Verification state at stop
- Suite: 784 pass + 1 known-allowed fail (sector_downside baseline). Desk build clean,
  vitest 37/37. desk_gate 53 (baseline; #14 closes to 0). Zero console errors on
  MARKET/SCANNERS/SHORTLIST/DEBATE/ALPHA at 2026-07-10 data.
- Servers at stop: API :8000 + desk :5174 running under this session's preview tool —
  they DIE with the session. Next session: `python run_manas_api.py` (reload=False — RESTART
  after every backend edit, stale-server bit us again this session) + `cd manas_os/desk &&
  npm run dev`.

## Footguns hit this session (add to the pile)
- API runs reload=False → EVERY app.py edit needs a server restart before live QC; a stale
  server made the fixed 409 look broken.
- A dead vite can keep 5174 in LISTEN as a zombie (curl 000, process alive) — taskkill + restart.
- pytest on this box can die on `%TEMP%\pytest-of-satta\pytest-current` PermissionError —
  pass `--basetemp` to a fresh dir.
- Live 409 QC nuance: a symbol already user_pushed for the scan_date returns 200
  `already_debated` (idempotent-by-result) — NOT a guard failure; use a fresh symbol or the
  deterministic tests.
