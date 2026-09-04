# GUIDED SYSTEM — Critical inspection of the built rail, headers, legend, status vocab

**Status:** inspection report on the **already-built** guided system (handoff #10).
**Branch:** `emergent`. **Date:** 2026-07-12. **Do not git commit.** "Rs", never the rupee glyph.

> **What changed since the handoff was written.** The handoff (`HANDOFF_GLM_guided_system_DESIGN.md`)
> asked for a from-scratch DESIGN spec. By the time it was actioned, **the guided system is already
> built and wired**: `GuidedFlowRail`, `CollapsedFlowStrip`, `TabPurposeHeader`, `StatusBadge` ship
> in `desk/src/components/v5/`, are imported in `App.jsx:14`, fed by a live `/api/flow/today` poll
> (`App.jsx:365–403`), and rendered in both densities (`App.jsx:547–564`). So a from-scratch design
> would be redundant. This file is instead a **critical, claim-by-claim inspection** of that built
> code against the handoff's intent — routing correctness, contrast/a11y, copy fidelity, and the
> genuine remaining gaps. Every finding is grounded in a file:line and (for contrast) a computed
> ratio. This is the "inspect every small thing critically" pass.

---

## 0. What exists (verified, not assumed)

| Handoff deliverable | Built as | File | Wired? |
|---|---|---|---|
| 1. Flow rail | `GuidedFlowRail` (beginner, left 220px) + `CollapsedFlowStrip` (expert, one-line) | `components/v5/GuidedFlowRail.jsx`, `CollapsedFlowStrip.jsx` | ✅ `App.jsx:547–561` |
| 2. Per-tab purpose header | `TabPurposeHeader` (WHAT/HOW/NEXT; beginner expanded, expert collapsible) | `components/v5/TabPurposeHeader.jsx` | ✅ `App.jsx:564` (7 tabs; **not** TRADE PLAN route) |
| 3. List-relationship legend | **Not built.** ALPHA/DEBATE/SHORTLIST have no shared legend or cross-badges. | — | ❌ |
| 4. Status vocabulary | `StatusBadge` (LIVE/SHADOW/WARMING/EXPERIMENTAL/NEEDS-DATA) | `components/v5/StatusBadge.jsx` | ✅ exists; ⚠️ **not wired** into ALPHA/DEBATE organs |
| 5. End-to-end walkthrough | n/a (this doc) | — | — |

The flow payload is real and polled: `GET /api/flow/today` returns 200 with 6 steps
(`done/action/blocked`), `current_step=positions` (curl-verified 2026-07-12, payload in §1.1 of
the prior draft, preserved at `/tmp` if needed). `App.jsx:396–403` re-fetches every 30s.

---

## 1. Defects found by critical inspection (grounded, severity-ranked)

### P0 — a11y contrast failures in the rail (computed, not eyeballed)

Three rendered pairs in `primitives.v5.css` fail WCAG 2.2 AA. Ratios computed by the WCAG
relative-luminance formula (second route: direct math, not a tool claim):

| # | Element | Pair | Ratio | Threshold | Verdict |
|---|---|---|---|---|---|
| 1.1 | `.gfr-step-count` (the pending-count chip, e.g. "4") | `--v5-panel` #fffdf9 text on `--v5-amber-bright` #b8801a bg | **3.37:1** | 4.5:1 (it's a number = text) | **FAIL** |
| 1.2 | `.gfr-step--active` left border ("you are here") | `--v5-amber-bright` on amber-glow-over-panel #f6eede | **2.96:1** | 3:1 (non-text UI) | **FAIL** (by 0.04) |
| 1.3 | `.gfr-step--done` whole step at `opacity:0.55` | `--v5-ink-mute` #6b6f78 faded to effective #aeafb2 on `--v5-panel` | **2.16:1** | 4.5:1 (label is text) | **FAIL** (severe) |

**Source:** `primitives.v5.css` — `.gfr-step-count { background: var(--v5-amber-bright); color: var(--v5-panel) }`,
`.gfr-step--active { border-left-color: var(--v5-amber-bright); background: var(--v5-amber-glow) }`,
`.gfr-step--done { opacity: 0.55 }`. The token layer itself flags `--v5-amber-bright` as
"graphics/borders only, NOT body text (~2.9:1, fails AA)" (`tokens.v5.css:33`) — so using it as a
*text-background* (1.1) directly violates the token's documented intent.

**Fix (one pass, token-faithful):**
- 1.1 → swap count chip to `background: var(--v5-amber-ink); color: var(--v5-panel)` (8.04:1, the
  same pairing the action button already uses — verbatim reuse, no new token).
- 1.2 → active border to `--v5-amber-ink` #6e470d on the glow-over-panel bg #f6eede = **7.08:1**
  (passes 3:1 comfortably; verified by a second compute route), OR keep amber-bright but note the
  3:1 non-text rule is about contrast, not border weight — so the color swap is the real fix.
- 1.3 → do **not** dim done steps with opacity. Convey "done" by the green ✓ icon + muted label
  color alone (the icon already carries status per WCAG 1.4.1). If dimming is desired, dim only
  to `opacity:0.75` (lifts to ~3.3:1 — still short; better to drop opacity entirely and rely on the
  ✓ + `--v5-ink-mute` label, which is 4.8:1 on panel).

### P1 — routing: `tabForStep` for `order_ticket` lands on DEBATE, not the ticket

`GuidedFlowRail.jsx:36–42`: `tabForStep("order_ticket") → "DEBATE"` with comment "opens trade plan
from debate". The step's own `detail` says *"Review setups first and log TAKEN to unlock a copyable
order ticket."* So the step's target **is** the order ticket (TRADE PLAN route), not the debate list.

- Today `order_ticket` is `blocked`, so no button renders (correct — blocked steps show no action).
- But once a setup is logged TAKEN, the step flips to `action` and `actionLabel` returns
  `"Open trade plan: <symbol> →"` — which then calls `onNavigate("DEBATE")`, landing the user on
  the **debate list**, where they must re-find the card and click TRADE PLAN again. The button's
  label promises the ticket; the navigation delivers the list. Mismatch.
- **Root cause:** `navigateTab(tab)` (`App.jsx:249`) carries **no symbol**, and the TRADE PLAN route
  is opened by `openTradePlan(symbol)` (`App.jsx:234`), symbol-scoped. The rail's `onNavigate`
  prop is tab-only — it has no path to `openTradePlan`.
- **Fix (build, small):** pass an `onOpenTradePlan(symbol)` handler into `GuidedFlowRail` (App.jsx
  already has it), and in `actionLabel`/the click handler, when `step.id==="order_ticket"` and
  `step.ticket?.symbol` exists, call `onOpenTradePlan(symbol)` instead of `onNavigate("DEBATE")`.
  The API already returns `ticket` (null today; populated once unblocked) — `step.ticket.symbol`
  is the right source.

### P1 — `setups` step routes to DEBATE (correct), but the detail points at SHORTLIST

Re-verified, not assumed: `tabForStep("setups") → "DEBATE"` (`GuidedFlowRail.jsx:40`) is
**correct** — the chair TAKE/SKIP verdict lives in DEBATE (`DebateTab` renders the council vote,
chair ruling, and the TRADE PLAN affordance; `DebateTab.jsx:569–575`). SHORTLIST rows *also* have a
"trade plan" button (`ShortlistTab.jsx:227`) but the decision is the debate. **No defect here** —
flagging because my earlier draft wrongly routed setups→SHORTLIST; the built code is right.

The only wrinkle: the step `detail` says *"4 of 4 setup(s) still need TAKEN / SKIPPED"* and the
VERDICT is in DEBATE, but the *list of 4 pending* may render in SHORTLIST too. If the user lands on
DEBATE and doesn't see "4 pending" highlighted, they'll be confused. **Minor:** consider whether the
rail's action should deep-link to DEBATE *filtered to pending* (needs symbol/set filter to travel —
same P1 root cause as order_ticket).

### P1 — TRADE PLAN route has no purpose header

`App.jsx:562–571`: the `tradePlan ?` branch renders `<TradePlanTab/>` with **no** header
(`TabPurposeHeader` is gated behind `!tradePlan`). So the one screen where money moves — the
explicit ask of TRADE PLAN — has no WHAT/HOW/NEXT. `TabPurposeHeader.jsx` `TAB_COPY` has **no
TRADE_PLAN key** either. This is the audit §6 screen (best in the app) getting less legibility
context than every other tab.

- **Fix (build, small):** add a `TRADE_PLAN` entry to `TAB_COPY` (copy below, §3.⑥), and render
  `<TabPurposeHeader tab="TRADE_PLAN"/>` inside the `tradePlan` branch (or pass the symbol through
  and render a purpose header specific to that route).

### P1 — `StatusBadge` exists but is not wired into the organs that need it

`StatusBadge.jsx` implements the full 5-status vocab (LIVE/SHADOW/WARMING/EXPERIMENTAL/NEEDS-DATA)
with correct AA colors (`primitives.v5.css:1083–1087`: green/red/amber-ink on dim washes, all ≥5:1 —
verified). But the audit's experimental/warming organs still render as bare text or raw JSON:

- DEBATE context "HMM: warming up (2/20)" — bare text, no `<StatusBadge status="WARMING"/>` (audit §11.3).
- ALPHA research bench raw `{ "models": [], "experiments": [] }` `<pre>` — no `<StatusBadge status="NEEDS-DATA"/>` (audit §11).
- ChartDrawer "STOCK HMM · EXPERIMENTAL" — the word is there but not as the shared chip.
- **This is a wiring gap, not a design gap.** The component is built; the organs don't import it.

### P2 — active-step highlight conflates "current" with "action" status

`.gfr-step--active` paints the **amber** border + amber-glow bg regardless of the step's status. So
a current step that is `blocked` (e.g. if `current_step` were `order_ticket`) would show an amber
"action" edge + a "blocked" icon — a mixed signal (amber = action in the rest of the rail).

- **Fix (design, tiny):** make the active-edge color status-aware: amber for `action`, red for
  `blocked`, teal for a `done` current step (rare). Or keep one neutral "current" indicator
  (teal `--v5-teal`) orthogonal to status, so current-ness never collides with status color.

### P2 — rail `data` step shows "Run EOD update →" even when `done`

`actionLabel("data")` always returns `"Run EOD update →"` (`GuidedFlowRail.jsx:17`). Today `data` is
`done` with `detail: "Latest session 2026-07-10 (0 trading day(s) behind)"`. The button only renders
when `isActive && btnLabel` — and `data` is not the current step today — so it's not visible now.
But if `data` ever becomes the current step while already `done` (e.g. stale-but-present), the
button would say "Run EOD update" against a `done` status. **Minor:** gate the data button on
`step.status !== "done"`.

### P2 — no weekend / no-run empty state in the rail

`/api/flow/today` returns `as_of` and a `detail` that says "Latest session 2026-07-10". When the
requested date is a weekend/holiday, the rail has no "no run for this date — jump to latest" affordance —
the audit's date dead-end (§1 P1) is not addressed by the rail. The rail always renders whatever the
API returns for the freshest run, so this only bites if a future change makes the rail date-scoped.
**Flag, not urgent** unless date-scoping is added.

---

## 2. Contrast ledger — all built guided-system pairs (computed)

Recomputed every text/UI pair the built CSS actually renders, so the verdicts above are auditable:

| Pair (element) | fg | bg | ratio | threshold | pass? |
|---|---|---|---|---|---|
| `.gfr-step-action` button text | `--v5-panel` #fffdf9 | `--v5-amber-ink` #6e470d | 8.04:1 | 4.5 | ✅ |
| `.gfr-step-icon` (action) | `--v5-amber-ink` | `--v5-panel` | 8.04:1 | 3 (icon) | ✅ |
| `.gfr-step-detail` (active step) | `--v5-ink-dim` #43464e | amber-glow-over-panel #f6eede | 8.18:1 | 4.5 | ✅ |
| `.gfr-step-label` | `--v5-ink` #17181b | `--v5-panel` | 16.7:1 | 4.5 | ✅ |
| `.sbadge--live` | `--v5-green` | `--v5-green-dim` | 5.05:1 | 4.5 | ✅ |
| `.sbadge--warming` | `--v5-amber-ink` | `--v5-amber-glow` (composite) | 5.64:1 | 4.5 | ✅ |
| `.sbadge--needs-data` | `--v5-red` | `--v5-red-dim` | 5.19:1 | 4.5 | ✅ |
| `.gfr-step-count` | `--v5-panel` | `--v5-amber-bright` | **3.37:1** | 4.5 | ❌ P0 |
| `.gfr-step--active` border | `--v5-amber-bright` | glow-over-panel | **2.96:1** | 3 | ❌ P0 |
| `.gfr-step--done` @0.55 | ink-mute→#aeafb2 | `--v5-panel` | **2.16:1** | 4.5 | ❌ P0 |

Method: WCAG 2.x relative luminance + (L1+0.05)/(L2+0.05). Opacity pairs composite the fg over the
bg before computing (the done-step fade is the real rendered color, not the raw token). `amber-glow`
`rgba(184,127,26,0.12)` composited over `#fffdf9` = `#f6eede`.

---

## 3. Per-tab purpose header copy — TRADE PLAN missing, others reviewed

`TabPurposeHeader.jsx` `TAB_COPY` has 7 entries (MARKET/SCANNERS/SHORTLIST/DEBATE/ALPHA/POSITIONS/JOURNAL).
Read critically against each tab's real content, the copy is accurate and advice-free — with notes:

- **MARKET** how-read correctly leads with regime mode → breadth. ✅
- **SCANNERS** "Hits are raw scan results — not vetted by the council." ✅ honest. But it does **not**
  mention the live presets hang (§4 below) — when scans fail to load, the header gives no context.
  Minor: add a NEEDS-DATA conditional line when the presets fetch fails.
- **SHORTLIST** "A TAKE chip means the council endorsed it; always check the current regime before
  acting." — ✅ advice-free (describes how to read, not what to do). Note: does not flag the audit's
  §4 P0 stale-contradiction (TAKE chip vs stale "waiting on" line). Could add: *"if the verdict chip
  and the 'waiting on' line disagree, the line is stale."*
- **DEBATE** how-read is accurate (chair verdict, conviction, seats). ✅
- **ALPHA** "SHADOW/RESEARCH rank, not a tradeable call — it informs the debate council, not your
  sizing." ✅ matches ALPHA_LEARNING_CONSTRAINTS exactly. Still no cross-badges (P1 §1).
- **POSITIONS** how-read names P&L vs stop/target + flagged exits + freshness. ✅
- **JOURNAL** ✅.

**Missing entry — TRADE PLAN (⑥), for the route overlay** (P1 §1):

```jsx
TRADE_PLAN: {
  what: "The exact broker ticket for one decision — entry, stop, target, size, and the do-not-trade gates.",
  how:  "The do-not-trade gates are hard stops on execution. The checklist is what to confirm at the broker; it saves per symbol and date.",
  next: "Work the checklist, then log the decision (TAKE / SKIP) in JOURNAL to close the loop →",
},
```

Copy is advice-free (describes the tool's function), grounded in audit §6 (ticket + gates +
checklist + management contract + PAPER banner). Note it describes **desired** behavior
(checklist persists, log-to-journal) that audit §6 P1 flags as not-yet-built — so wiring this header
should land *with* those fixes, not before.

---

## 4. The SCANNERS hang — separate backend bug, design only designs around it

You reported SCANNERS shows no scans. Verified live 2026-07-12: `/api/flow/today` returns 200 in
<1s, but `/api/scanners/presets?date=2026-07-10` **times out at 8s, empty body (HTTP 000)**.
Root cause is in the handler: `preset_hit_count(conn, key, as_of)` runs **synchronously per preset,
per registry entry** in a loop (`api/app.py:6874–6885`), aggravating audit §3's "per-preset counts
are the slow part."

- **This is a backend/pipeline bug, out of scope for the guided-system design.** Flagged as a
  separate work item.
- **Design implication (P2 §3):** the SCANNERS `TabPurposeHeader` should render a NEEDS-DATA
  conditional line when the presets fetch fails: *"Scans aren't loading right now — the last good
  scan was 2026-07-10 (243 cleared the gate). [Retry] "* — using the `data` step's `detail` from
  `/api/flow/today` as the fallback source of truth, and the existing `StatusBadge status="NEEDS-DATA"`.

---

## 5. Deliverable 3 — list-relationship legend: still genuinely unbuilt (the real design work)

Unlike the rail/headers/status-vocab (built), the **Alpha ↔ Debate ↔ Shortlist legend + cross-badges
do not exist** in code. This is the one deliverable that is still real design + build work. Keeping
the substance from the prior draft, now reconciled to the live counts (not the mockup's date):

- **ALPHA** = shadow cross-sectional rank over the whole universe, market movement removed.
  Research/leadership, not tradable. (audit §0.1, §11; ALPHA_LEARNING_CONSTRAINTS.)
- **DEBATE** = council verdict on **gate-passed** candidates only — tonight's decisions.
- **SHORTLIST** = user-curated watch.

The funnel that makes "different stocks" intentional (universe → gate-passed → debated → your
watch) already renders on DEBATE's `FunnelPanel` (`components/v5/index.js:18`, data from
`/api/desk/debate` `funnel` field, `App.jsx:427`). **Reuse those live numbers** — do not hardcode
the round-4 mockup's 2,370/13 (those are a different date; the audit saw 29 debated, `/api/flow/today`
sees 243 cleared the gate — three different snapshots; live-at-render is the only honest source).

Cross-badges (also-debated / on-your-shortlist / shadow-rank-N) are **not built** and need a
membership source: either a cheap shared endpoint, or a client-side join of the three existing
payloads. That join is a **build decision**, not a design one — the design only requires the badges
exist, are icon+text (not color-only, WCAG 1.4.1), and link to the sibling tab. ALPHA rows still
have zero actions (audit §11 P0) — the legend work should land with row actions.

---

## 6. What "done" looks like for the build (Gemini's work, from this report)

Ordered by severity, each with a pass/fail check:

1. **Fix the 3 contrast P0s in `primitives.v5.css`** — count chip → amber-ink bg; active border →
   amber-ink or thickened; drop `opacity:0.55` on done steps. *Check: recompute the three ratios;
   all must clear 4.5 (text) / 3 (border).*
2. **Wire `StatusBadge` into the warming/experimental/empty organs** — DEBATE HMM (WARMING),
   ALPHA research bench (NEEDS-DATA, replacing the raw `<pre>`), ChartDrawer HMM (EXPERIMENTAL).
   *Check: grep the rendered DOM for `sbadge--warming`/`sbadge--needs-data` on those surfaces.*
3. **Add TRADE_PLAN header** — `TAB_COPY.TRADE_PLAN` + render in the `tradePlan` branch.
   *Check: open a trade plan route; a WHAT/HOW/NEXT header is present.*
4. **Fix `order_ticket` routing** — pass `onOpenTradePlan` into the rail; call it with
   `step.ticket.symbol` when the step is `action`. *Check: unblock the step (log a setup TAKEN in a
   test fixture), click the rail button → lands in TRADE PLAN for that symbol, not DEBATE.*
5. **Status-aware active edge** (P2) — current step border color follows status, not always amber.
6. **(Larger, separate)** the list-relationship legend + cross-badges + ALPHA row actions (§5).
7. **(Backend, separate)** the `/api/scanners/presets` per-preset synchronous loop (§4).

---

## 7. Verification log (honest)

- **Built components exist:** `components/v5/index.js:25–29` exports them; `App.jsx:14` imports;
  `App.jsx:547–564` renders. **Certain.**
- **`/api/flow/today` live + polled:** curl 200 2026-07-12; `App.jsx:365–403`. **Certain.**
- **Routing (`tabForStep`):** `GuidedFlowRail.jsx:33–42`; cross-checked DEBATE holds the verdict
  (`DebateTab.jsx:569–575`) and TRADE PLAN opens via `openTradePlan(symbol)` (`App.jsx:234–240`).
  **Certain.** (My earlier draft's setups→SHORTLIST was wrong; built code's setups→DEBATE is right.)
- **`navigateTab` carries no symbol:** `App.jsx:249–251` — tab-only. **Certain.**
- **Contrast ratios:** computed by WCAG luminance formula, two routes (direct + composite-for-opacity),
  §2 ledger. **Certain.**
- **SCANNERS hang:** curl `/api/scanners/presets` → HTTP 000 @8s while `/api/flow/today` → 200 @<1s
  same minute; handler `app.py:6874–6885`. **Certain (live).**
- **Funnel counts:** the round-4 mockup (2,370/13), the audit (29 debated), and `/api/flow/today`
  (243 cleared gate) are **three different dates/snapshots** — I do not hardcode any; the build must
  read `funnel` from `/api/desk/debate` at render. **Likely** (the field exists; I did not curl the
  live funnel value this session — flagged).
- **StatusBadge contrast:** `primitives.v5.css:1083–1087` token pairings, computed ≥5:1. **Certain.**

---

## 8. Single strongest recommendation

**The guided system is 80% built; the remaining value is a defect sweep, not a redesign.** Fix the
three contrast P0s (one CSS pass), wire the already-built `StatusBadge` into the three organs that
render as noise, and add the missing TRADE PLAN header + order_ticket route fix. Those four are small,
grounded, and turn the built-but-imperfect rail into the legibility spine the audit asked for. The
one genuinely new build is the list-relationship legend (§5) — and even that reuses the live funnel
data already on DEBATE. Do not rebuild what ships.

*Risks: contrast ratios assume the v5 token values are as read from `tokens.v5.css` (they are today;
a token edit needs a recompute). The order_ticket fix depends on the API populating `step.ticket`
once unblocked — I verified `ticket:null` today but could not exercise the unblocked path live. The
funnel live value is not curl-verified this session (§7). No trading guidance invented; all states
honest.*
