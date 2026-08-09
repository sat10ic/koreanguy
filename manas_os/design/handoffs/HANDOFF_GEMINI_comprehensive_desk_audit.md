# HANDOFF — Comprehensive Desk Audit (Visual/UX Craft + Functional Wiring)

**Scope:** All 7 desk tabs + shell + `MarketHomeTab` + 26 v5 primitives + utils/api/livework/glossary.
**Method:** Static, code-traced against live source on disk (not browser-clicked). All 57 source files read; every button/handler/endpoint/cross-nav traced.
**Date:** audit session (branch `emergent`).
**Author:** opencode (principal-engineer discipline, self-attacked).

---

## Verdict

- **P0 (broken / dead / a11y-blocker): NONE.**
- **P1: NONE.**
- **P2a — Fabricated council roster (priority fix).** `DebateLivePanel.jsx:56` hardcodes
  `["deepseek-r1", "gpt-4o", "gemini-1.5-pro"]` as the pre-event "COUNCIL MEMBERS" list.
  - Wrong seats: actual council per `utils.js` `MODEL_SEAT_LABELS` = `deepseek-v4-pro / glm-5 / kimi-k2 / qwen3.5`. During the connecting window the UI claims 3 *different* models are debating.
  - `gpt-4o` / `gemini-1.5-pro` are not in the seat-label map, so real seats get human labels while these render raw via `model.split("/").pop()` — visually inconsistent.
  - Transient (self-heals once `seat_verdict` / `seat_failed` events arrive) but it is the **only** place in the app that *fabricates* content before server data — directly against the standing "real data only / never fabricate" rule.
  - **Fix:** render the existing `v5-debate-empty` "connecting" state (or a neutral "awaiting council seats") when `modelKeys.length === 0`, instead of a hardcoded 3-list.
- **P2b — `SizerStamp` bare currency.** `SizerStamp.jsx:26` shows `{rupeeRisk}` with no unit while DEBATE (`DebateTab.jsx` deep-dive) and TRADE PLAN (`TradePlanTab.jsx`) siblings use `₹` everywhere. The "risk" metric is ambiguous (rupees vs R vs %).
  - **Fix:** label it `₹{rupeeRisk}` to match siblings. (Not a rule break — see `₹` note below.)
- **P2c — `alert()` in 5 spots** vs the app's inline toast/banner pattern:
  `App.jsx:298,377`, `LedgerTab.jsx:795,840`, `TradePlanTab.jsx:454`.
  Jarring/blocking, breaks v5 aesthetic. Low severity; unify to inline error states (`alpha-error` / `panel-note`).

### Note on the `₹` glyph
The `₹` character in JSX is **NOT** a violation. `HANDOFF_GEMINI_positions.md:95-97` explicitly permits `₹` in JSX
("keep doing so with `₹` or `Rs` consistently in your JSX, your choice, but stay consistent within a screen").
The standing "never print the rupee glyph" rule (`HANDOFF_INDEX.md:56`) is **console-only** (Windows cp1252 encoding).
So the 10 `₹` occurrences are sanctioned; the only related defect is P2b (a *missing* unit, not a forbidden glyph).

---

## Verified passes (evidence)

- **No fabricated numbers:** vol forecast hidden when stale (`DeskTab.jsx:61-70`); `Unknown`/`Mixed` modes;
  `offline_fallback:true` tagged in `api.js`; `—`/null handled everywhere.
- **Money math server-owned:** `TradePlanTab` ONE-WRITER-FOR-RISK honored; risk gate immutable → PUSH rejected with `SizerStamp`.
- **Glossary 100% coverage:** all 39 static `k=` + 2 dynamic (`App.jsx:106` `modeTerm` → `mode-*` keys;
  `DeskTab.jsx:56` `stageTermKey` → `stage-*` keys, null-guarded) resolve to `glossary.js`; miss = graceful `children`.
- **No dead ends:** push / shortlist / debate / trade-plan / journal cross-nav all wired to real handlers/endpoints;
  `CrossBadges`→`navigateTab`, `ListRelationshipLegend`→`goToDebate` wired through `App`.
- **a11y:** `aria-expanded`/`describedby` on `Term`; `StatusBadge role="status"`; nested-interactive fixed via `Term as="span"`;
  `ChartDrawer` focus-trap + Esc + inert; `DensityContext` reduced-motion honored in `MarketHomeTab`.
- **Token discipline:** no raw hex in component CSS; `ChartDrawer.tk()` prevents dark islands; `DeskTab` `DAY_COLOR_HEX` uses `var()`.
- **Wiring verified:** `useListMembership`→`fetchAlphaLeaders(date, 50)` matches `api.js` signature (no over-fetch);
  `useJobStream` exports `useLiveWork` / `LiveWorkProvider` / `TERMINAL_JOB_STATUSES` all consumed correctly.
- **`DeskTab` is NOT dead code** — `LawRow` / `ModelsSayPanel` consumed by `MarketHomeTab`.

---

## Self-attack (pre-send)

- **Missed P0?** Re-checked: no `onClick` without handler, no fake payloads rendered as real (except P2a, a *named wrong* placeholder),
  no broken aria. Confident: none.
- **Is P2a a real violation or just a placeholder?** It is a *named, wrong* placeholder = fabrication, not a neutral "loading". Correctly flagged.
- **`₹`?** Re-read `HANDOFF_GEMINI_positions.md:95-97`: explicitly permits `₹` in JSX. Earlier "P1" instinct was wrong; self-corrected.
- **Reduced-motion in raw component CSS not re-read** — claim rests on #31 `tokens.v5.css` universal guard. **Assumption:** covers all 10 files — Likely, not re-verified this pass.

---

## Risks

- **R1:** P2a shows wrong/raw model names for a few seconds on every debate launch — low user impact but a stated-principle violation. Fix ~3 lines.
- **R2:** `alert()` paths untested for exact trigger conditions (no repro run this session). **Assumption:** they fire on error/edge branches; severity stays low.
- **R3:** Reduced-motion CSS coverage asserted by #31, not independently re-verified here. **Likely** pass.
- **R4:** Audit is static (code-traced), not browser-clicked — functional wiring confirmed by source, not live run.

---

## Recommended next step

1. **Fix P2a** (render neutral "awaiting council seats" when no events yet) — patch `DebateLivePanel.jsx`.
2. **P2b** (add `₹` unit in `SizerStamp`) and **P2c** (`alert()` → inline error) safe to batch later.
3. No commit (standing rule: maintainer QCs).
