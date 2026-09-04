# UX AUDIT — FULL RENDERED PASS (2026-07-12)

Method: live drive of the desk (Vite :5174 + API :8000, real data date 2026-07-10) via
in-app browser — DOM text extraction, JS DOM/state probes, network log, console log —
plus code tracing in `manas_os/desk/src/` where the browser could not confirm (each
finding labels its method: **[rendered]**, **[code]**, or **needs live check**).
Excludes the two already-known P0s (search doesn't analyze; no live debate stream) except
where they intersect new findings. Lens: "what can the user NOT do here", one-question /
one-primary-action per screen, state coverage, beginner comprehension.

---

## 0. THE HEADLINE STRUCTURAL PROBLEM — the tool is not legible AS A SYSTEM

**P0 · whole app · effort L (design M + build M)**

The desk is a set of individually honest, individually well-explained CARDS with no
connective tissue. Every panel has a "PLAIN-ENGLISH READ" for its own metric, but nothing
anywhere explains:

- (a) the end-to-end process (Market → regime → scan → debate → plan → size → manage →
  exit → learn) as a thing the user walks through;
- (b) what each SECTION is *for* in that process (why does ALPHA exist next to DEBATE?);
- (c) how to *read/infer* from a card as a decision input rather than a fact;
- (d) where the user currently IS in the daily workflow and what the next action is;
- (e) how the three stock lists relate (see §0.1).

**Hard evidence that this was speced and abandoned:** `/api/flow/today` EXISTS and
returns exactly the guided flow — six steps with per-step status/detail/actions
(`{"current_step":"positions","steps":[{"id":"data",...},{"id":"regime",...},
{"id":"positions","status":"action","detail":"1 position(s) flagged EXIT TODAY: HUDCO"},
{"id":"setups","status":"action","detail":"4 of 4 setup(s) still need TAKEN / SKIPPED"},
{"id":"order_ticket","status":"blocked",...}...]}` — verified live with
`curl /api/flow/today?date=2026-07-10`). **Zero references to `flow/today` exist in
`manas_os/desk/src/`** (grep, [code]). The stepper backend (plan T3.8, EXECUTOR_PLAYBOOK
Wave 3) is built, tested per the playbook, and never rendered. The guided flow is
currently vaporware in the UI while being real on the server.

### Proposed design (concrete)

1. **Persistent flow rail** (left edge or under the header, both modes, collapsible in
   expert): the six `/api/flow/today` steps as a vertical stepper — Data ✓ · Regime ✓ ·
   Positions ⚠1 · Setups ⚠4 · Order ticket 🔒 · Done. Each node: status dot, one-line
   detail (verbatim from the endpoint), and **click = navigate to the owning tab**
   (Positions⚠ → POSITIONS, Setups⚠ → SHORTLIST/DEBATE, Order ticket → TRADE PLAN).
   `current_step` gets the highlight; `blocked` steps show *why* ("Review setups first").
   This single component answers (a), (d) and gives every tab a "you are here".
2. **Per-tab purpose header** (one standard component, all 7 tabs): three fixed lines —
   *WHAT THIS IS* (one sentence), *HOW TO READ IT* (one sentence naming the decision it
   feeds), *NEXT →* (link to the flow step it feeds). E.g. ALPHA: "Research ranking of
   the whole 1,184-stock universe with market movement removed — shadow only, never a
   buy list / Use it to see which names *may* enter future scans / Next → tonight's
   SCANNERS." The existing PLAIN-ENGLISH READ pattern proves the voice already exists;
   it's just aimed at metrics instead of the system.
3. **"How these lists relate" legend** on ALPHA, DEBATE and SHORTLIST (§0.1).
4. **First-run overlay** (beginner mode only, dismissable, re-openable from header "?"):
   the pipeline funnel drawn once — universe 2370 → screeners 1820 → hard gates 961 →
   pool 243 → debated 29 → sized 1 — with each stage linked to its tab. The numbers
   already render on DEBATE's GATE FUNNEL; reuse them.
5. **Beginner mode should change the spine, not just labels**: today the beginner/expert
   toggle renders the same 7 tabs ([rendered] — tab list identical in both modes) and
   only swaps copy/density. In beginner mode the flow rail should be open by default and
   the landing view should be the stepper, not the MARKET wall of 12 panels.

### 0.1 ALPHA vs DEBATE vs SHORTLIST show different stocks and nothing says why — P0

**[rendered]** ALPHA top-12: SIGMAADV, SETL, TIRUPATIFL, BETA, INDSWFTLAB… ("1184
eligible stocks"). DEBATE: 29 debated names (UNIPARTS, LENSKART…). SHORTLIST: 37 curated
names. Only SETL overlaps the visible alpha list. A beginner sees three competing
"stock lists" with three different winners and no sentence anywhere explaining the
relationship (Alpha = shadow cross-sectional research rank over the WHOLE universe,
alpha/features.py, not tradable; Debate = council verdicts on gate-passed candidates
only; Shortlist = the user-curated watch layer). ALPHA's subtitle says "research rank,
not a buy list" but never says how it relates to the other two tabs.
**Fix (S/M):** the shared "how these lists relate" legend (three-row diagram: UNIVERSE
RANK → tonight's SCAN pool → DEBATED → YOUR SHORTLIST) + on each ALPHA row a badge when
the symbol IS in tonight's pool/debate ("in debate", "shortlisted") so the lists visibly
connect. Effort S for the legend, M for the row badges.

---

## 1. SHELL / NAV / HEADER / SEARCH

One question it should answer: "where am I, what date am I looking at, and how do I get
anywhere?" It half-answers: tabs are clear, but there is no location-in-workflow signal
(see §0) and the date control is hostile.

- **P0 — No URL routing at all.** [rendered] URL stayed `http://localhost:5174` through
  every tab switch, trade-plan open, chart open, date change. Browser back exits the app
  and loses everything; a reload rewinds to MARKET/latest (observed after pane reload:
  landed back on MARKET, beginner mode). Nothing is shareable/bookmarkable — you cannot
  send someone "the UNIPARTS plan". Fix: hash-router encoding tab/symbol/date
  (`#/debate/2026-07-10/UNIPARTS`). Effort M.
- **P1 — Date scrubber is arrows-only over CALENDAR days.** [rendered + code
  App.jsx:25-28,376-382] `shiftDate(d,±1)` walks weekends/holidays; clicking ▶ from
  07-10 lands on Saturday 07-11 → "No run for 2026-07-11 yet. The desk runs after market
  close." — honest but a DEAD END: no "back to latest" button, no explanation it's a
  weekend, no date picker, no jump-to-latest anywhere in the header (jumpToLatest runs
  only on load, App.jsx:273). Fix: `<input type=date>` + "latest" chip + skip to previous
  trading day. Effort S.
- **P1 — Search has no affordance for what it accepts.** [rendered] Plain text input
  `placeholder="symbol search"`, no autocomplete/suggestions, no validation — a typo'd
  or non-pool symbol navigates to DEBATE and (per known P0) lands nowhere useful. Even
  post-fix, add a typeahead over the symbols universe. Effort M.
- **P2 — No "/" (or any) keyboard shortcut to focus search; no keyboard shortcuts at
  all.** [code] No keydown listener in App.jsx. Effort S.
- **P2 — UPDATE button gives no pre-flight context** ("what will this do, how long") —
  it's the nightly pipeline trigger sitting one click away with no confirm. needs live
  check on its confirm behavior (not clicked to avoid a 160-minute run during audit).
- Checked and OK: stale/offline banners exist (App.jsx:434-459, incl. "API offline —
  showing cached snapshot" fallback); mode toggle persists visually; header is compact.

## 2. MARKET

One question: "can I take risk today, and where?" — **it answers this well in <20s**
([rendered]: verdict banner CAUTION + "The one question" + TODAY'S LAW + OPPORTUNITY
NOW + primary action button). Best screen in the app.

- **P1 — Twelve stacked evidence panels dilute the one answer.** [rendered] After the
  verdict, the beginner scrolls XP, MBI, Breadth V2, %DMA, NET BREADTH, AD ratio,
  monthly-move, DMA-cross, NH-NL/Fosback, volatility ratio, BO/BD, sectors. All have
  plain-reads, none say which ones *changed today* or which drove tonight's verdict.
  Fix: "what moved tonight" delta chips at top; collapse evidence panels behind an
  accordion in beginner mode. Effort M.
- **P1 — No drill-down anywhere on MARKET.** [rendered] Breadth numbers, sector leaders
  ("Leading: Realty, PSU Bank"), funnel stages — none are clickable (only the single
  primary-action button and "view activity →" navigate; MarketHomeTab.jsx:734 is the
  sole onNavigate button in the opportunity section). User can't click "Realty" to see
  realty names, can't click "37 shortlisted" to open SHORTLIST. Effort M.
- **P2 — Unexplained numerology for beginners:** "r4.5 2400", "R10 161", Fosback 1.1
  (is 1.1 high?), VOL RATIO 0.31 with no good/bad band. Plain-reads explain the concept
  but not the threshold. Add "supportive/neutral/hostile" tinting per stat. Effort S.
- **P2 — `[B]` leftover renders literally**: "[B] SELECTIVE law - up to 4 cards…"
  [rendered]. Strip the mode-tag from user copy. Effort S.
- Checked and OK: honest-zero panels ("Monthly winner/loser counts are not populated
  yet… no zero is being inferred") are exemplary; LIVE WORK strip shows PARTIAL honestly.

## 3. SCANNERS

One question: "which mechanism found what tonight?" — answers it, but the interaction
model fights the user.

- **P0 — Clicking a preset gives ZERO visible feedback.** [rendered] Clicked
  "Persistent Momentum"; result rows rendered at `top: 7103px` while `scrollY` stayed 0 —
  results mount at the very bottom of the page, below all three lanes AND the ChartsMaze
  section. The user clicks, nothing happens on screen, and unless they scroll ~7000px
  they never learn the click worked. Fix: scroll-into-view on open, or render results
  inline under the clicked card / in a drawer. Effort S.
- **P1 — ~10s loading with a text-only placeholder.** [rendered] "LOADING PRACTITIONER
  SCANNERS…" persisted ~10s after the API had already returned 200 (network log shows
  presets 200 at request start; the slow part is per-preset counts). No skeleton, no
  per-lane progressive fill. Also **5 duplicate `GET /api/scanners/presets` requests**
  on one mount ([rendered network log]) — wasted latency. Effort M.
- **P1 — Result rows: cryptic icon strip.** [rendered] Each row ends in `★ ⚡SS+ → ▤`.
  aria-labels exist ("shortlist ADFFOODS", "push to debate", "open chart" — good), but
  visually a beginner sees four glyphs; titles only on hover. Fix: labels in beginner
  mode / a row overflow menu. Effort S.
- **P1 — No filter/sort/search within 66-292 result rows**, no column sort, no "only
  not-yet-shortlisted". Arora Baseline = 292 rows behind "show all". Effort M.
- **P2 — No way to run a preset against a custom date or export the hits.** needs live
  check on CUSTOM BUILDER coverage (builder exists as a second top-level mode;
  not driven in this pass).
- Checked and OK: BUILD vs LIVE badges, source citations per preset, honest "Not
  available yet. This lane is planned, not a zero-result scan", counts-by-date note.

## 4. SHORTLIST

One question: "what am I watching and what would make each name actionable?" — the
trigger data is there but the freshness story actively misleads.

- **P0 — "WAITING ON" lines show STALE (previous-day) gate reasons that contradict the
  same row's current verdict.** [rendered] LENSKART row: verdict chip **TAKE** while the
  line reads "WAITING ON: **2026-07-09** hard gate failure: regime — SELECTIVE does not
  allow momentum setups"; KTKBANK: verdict chip **SKIP** while the line reads
  "2026-07-10 … chair verdict **TAKE** (conviction 4)". A beginner cannot tell which
  statement to trust. The row is mixing (i) last state-history event, (ii) tonight's
  chair verdict, (iii) an old hard-gate failure, without dating them relative to "now".
  Fix: always render the reason FOR THE SELECTED DATE, label older events "yesterday:",
  and never pair a TAKE chip with an unexplained failure line. Effort M.
- **P1 — Chart thumbnails fail silently for symbols without a nightly PNG.**
  [rendered + code] `/api/desk/chart?symbol=ATGL` → 404 JSON (curl-verified) →
  ERR_BLOCKED_BY_ORB in the page; ChartThumb falls back to "no chart"
  (ShortlistTab.jsx:95-112) with NO way to generate one on demand. Chart-from-anywhere
  fails exactly for the less-mainstream names a watchlist exists for. Fix: on-demand
  chart render endpoint + "generate chart" affordance on the fallback. Effort M.
- **P1 — No sort/group controls over 34 pool rows** (no "gate-passed first", "nearest
  trigger first", "newest first"), and trigger distance isn't computed against last
  price ("trigger >= 410.7" — how far away is it?). Effort M.
- **P2 — Glyph noise:** "—", "–", "miss 1/2", "▲/▼" unlabelled; "conviction 2" scale
  never defined (of what? 1-5?). Effort S.
- **P2 — Strong Start section: "RS -"** renders a bare dash with no tooltip why.
  [rendered]. Effort S.
- Checked and OK: curator delta explainer, ADD A SYMBOL manual add, reversible remove
  with reason + undo (RemoveControl, ShortlistTab.jsx:120), per-row trade plan/debate
  links, state history accordions.

## 5. DEBATE

One question: "what did the council decide and why?" — answered, but on an enormous
single scroll with buried authority conflicts.

- **P1 — One ~15,000px page, no internal navigation.** [rendered] Market context +
  funnel + governor + heat + 29-row table + 18 deep-dive cards, sequential. No sticky
  section nav, no "jump to symbol", no collapse. Finding one card means scrolling past
  ~10 others. Fix: sticky mini-TOC (Context / Table / Cards A-Z) + collapsed cards with
  expand. Effort M.
- **P1 — Vote-count inconsistency confuses the verdict.** [rendered] Header: "4 models ·
  97 verdicts"; table column "MODEL VOTES" shows mixed denominators (3T/0S, 0T/4S,
  0T/3S); cards say "3-MODEL VOTE — 3 TAKE / 0 SKIP" listing 3 LLMs while VISION
  (chart-reader) sits separately saying HOLD. Nowhere states: vision is the 4th voter /
  when a model abstains. A beginner cannot audit "who voted". Fix: one voters legend +
  consistent denominator with abstentions shown. Effort S.
- **P1 — "Sizer refused: validation failed"** is the FINAL authority overriding chair
  TAKE, and its reason is an opaque string ([rendered], LENSKART/SHRINGARMS cards). The
  single most decision-critical message in the app has the least explanation. Fix:
  surface the actual failed validation (which check, which number). Effort S (backend
  passes reason through).
- **P1 — "1 pipeline note(s) logged" is not clickable** [rendered probe: no
  button/details ancestor]. A logged anomaly the user cannot read. Effort S.
- **P2 — PUSH TO DEBATE control sits at page top with no state feedback while the
  known-P0 sync blocking happens** (intersects known P0 #2; not re-reported).
- **P2 — HMM everywhere in half-born state, unexplained** (see §11 item 3): context
  strip "HMM: warming up (2/20)" [rendered]; table column STOCK HMM shows BULLISH /
  CHOP / n/a with no legend that this is an experimental, data-starved model.
- Checked and OK: near-miss reasons are specific and educational (best copy in the
  app); gate chips per card; delivery z-scores; SCAN vs PUSHED provenance chips; heat
  bar with cap.

## 6. TRADE PLAN

One question: "exactly what do I do at the broker tomorrow?" — **answered excellently**
(ticket + do-not-trade gates + 7-step broker checklist with per-step sources + management
contract + wobble-day rule + honest PAPER banner). Remaining gaps:

- **P1 — No chart on the execution screen.** [rendered] The user is told "buy above the
  opening-range high with the low holding" for UNIPARTS without the daily chart shown
  anywhere on the plan. Every other surface has charts; the one screen where money moves
  has none. Fix: embed the same ChartDrawer PNG. Effort S.
- **P1 — Checklist checkboxes don't persist.** [rendered: 7 real checkboxes; code: local
  state only, no storage] Tab away and back → progress gone. Also nothing happens when
  all 7 are checked (no "armed / done" state), and there is no "I took it / I skipped
  it" capture into the journal from here — the learn-loop's entry point is missing at
  the exact moment of decision. Fix: persist per symbol+date; completion CTA "log
  decision → journal". Effort M.
- **P2 — No copy/export.** A manual-execution checklist you cannot print/copy to your
  phone at the broker terminal. "Copy ticket as text" was in the T3.8 spec
  ("order ticket with copyable text" — EXECUTOR_PLAYBOOK.md:91). Effort S.
- **P2 — Reachability: TRADE PLAN has no tab; it's only reachable via a DEBATE card or
  SHORTLIST row** ([code] App.jsx:206-218 route pattern; [rendered] 7-tab nav). With 4
  setups pending decision, there is no "all pending tickets" list — the flow-rail
  Order-Ticket step (§0) should list them. Effort tied to §0.
- Checked and OK: back-navigation both top ("← DEBATE") and bottom; DO-NOT-TRADE gates
  with live numbers; "Evidence & alternative scenarios" details element.

## 7. POSITIONS

One question: "what must I do with my open money right now?" — answered loudly (EXIT
banner + fired rules + R math). Gaps:

- **P0 — Raw internal alert payload rendered verbatim.** [rendered] The card prints:
  `dry-run: shown, not sent "URGENT: deterministic exit_now fired (stop-breached, …)
  "Two kinds of letting go — …" [TTM-E8, TTM-E9] … signal — manual execution only; not
  advice"` — a Telegram dry-run debug string with nested quotes and internal doctrine
  tags, shown to the user as UI copy. Fix: render a formatted alert preview or nothing.
  Effort S.
- **P1 — No chart and no link back to the origin thesis.** [rendered] HUDCO card says
  "Entry steps were on the original DEBATE card" but provides NO link to that card/date
  (and the debate for the entry date may not even be loadable — needs live check), no
  price chart with entry/stop/now marked beyond the 3-point strip. Fix: chart thumb +
  "open origin debate (2026-07-03)" link. Effort M.
- **P1 — "NOW 207.0" has no as-of/source marker.** [code: current price derived from
  `entry + openR*risk`, PositionsTab.jsx:122; no timestamp rendered] Under the
  LIVE-first doctrine the user can't tell if 207.0 is live, EOD-stale, or feed-down
  (fyers_connected:false right now). Fix: freshness chip ("EOD 07-10" / "live 10:42" /
  "feed down"). Effort S.
- **P2 — No closed-positions section here** (history lives in JOURNAL, unlinked). "ORIGINAL
  THESIS: no agent thesis" — dead-end copy: say why (manually added position) and offer
  "run debate now". Effort S.
- Checked and OK: Add position (manual), Edit SL / Edit qty / Close all present with
  inline editors; exit reasons named; R math shown; "no new LLM call from this screen"
  honesty.

## 8. JOURNAL

One question: "am I improving — does my edge exist?" — honest zero-states, but it's
read-only where it must be read-write.

- **P1 — No delete for a journal row although `DELETE /api/journal/{trade_id}` exists**
  ([code] api/app.py:3352; desk `api.js` has no journal delete; [rendered] no delete
  control on the history row). The HUDCO test/mistake entry is permanent in the UI.
  Quick win. Effort S.
- **P1 — User cannot write anything.** [rendered] No add-trade, no edit (wrong entry
  price stays wrong), no manual lesson — "LESSONS DIARY from ~/.manas/lessons" is
  file-system-only. A journal you can't write in. Effort M.
- **P1 — History rows don't drill down.** [rendered] The HUDCO row links to nothing —
  not the debate card, not the plan, not a chart of the trade. Effort M.
- **P2 — SYSTEM EDGE table jargon:** "DIRECTIONAL n=24 hit 0% · avg -1.26R" vs
  "OPERATIONAL n=19065 win 48% (no stop set)" — the taken-vs-counterfactual distinction
  is the tab's whole insight and is never explained in plain-read voice; "n=19065" next
  to "n=24" begs the beginner question the UI doesn't answer. Effort S.
- Checked and OK: equity-curve honest zero ("appears from your second closed trade"),
  screener-predictiveness table with n<30 flag, expectancy tiles dashed not zeroed.

## 9. CHARTDRAWER

- **P1 — No symbol mobility inside the drawer.** [rendered] Drawer shows one symbol
  (GROWW): D/W toggle + layer chips (50/200 EMA, Markers, HMM, RMV) but no prev/next
  through the list you opened it from, no symbol search inside, no compare. Reviewing 29
  debated charts = 29 open/close cycles. Fix: ←/→ through the source list, keeping
  context. Effort M.
- **P1 — Static PNG: no zoom/pan/crosshair, no OHLC readout.** [rendered/code] It's an
  <img>. Acceptable for v5, but at least click-to-open full-size / new tab. Effort S-M.
- **P2 — Badge jargon:** "BP 3.00 (3)", "Mswing 0.04 vs 0.35 positive, trails index",
  "RMV 49.9" — unexplained even in beginner mode [rendered]. Effort S.
- **P2 — Experimental HMM strip inside the drawer is good honesty** ("insufficient
  history (141 clean bars, need >= 150)") — but see §11 item 3: it renders as noise
  because no element says what HMM would give you when alive.
- Checked and OK: role=dialog aria-modal, Escape handler in code
  (ChartDrawer.jsx:359-362; synthetic-event test inconclusive — needs live check),
  backdrop click, layer toggles work per class state. **No focus trap / initial focus
  management found in code** — keyboard users tab behind the modal. P2, effort S.

## 10. LIVE WORK INSPECTOR

- **P1 — Header contradiction: "LIVE WORK · COMPLETE" + badge "PARTIAL" + 31/33 with two
  failed stages** in one panel [rendered]. Pick one truth: PARTIAL. Effort S.
- **P1 — Failed stages say "why it failed" + "retry" (good) but nothing states the USER
  IMPACT** — which tabs are degraded because bhavcopy/chartsmaze failed (e.g. missing
  charts on SHORTLIST are plausibly THIS failure, and nothing connects them). Fix: map
  failed stage → affected surfaces ("charts may be missing on SHORTLIST/DEBATE").
  Effort M.
- **P1 — Inspector only knows the nightly update.** Intersects known P0 #2 (jobs/SSE
  built, on-demand work invisible) — extend the same panel to ALL jobs, including
  user-triggered debates and retries. Effort tied to that fix.
- **P2 — Elapsed "160m 22s" for a finished run reads like it's still counting** — label
  "took 160m" vs "elapsed". Effort S.
- Checked and OK: per-stage durations, event feed with timestamps, "full detail" toggle,
  footer reassurance, retry buttons.

## 11. ALPHA LAB

One question: "is the quant layer finding anything, and can I trust it?" — currently
answers neither for a beginner.

- **P0 — Zero interactive elements on the entire tab.** [rendered probe: buttons/links
  in main = 0] The opportunity ranking is a dead end: can't open SIGMAADV's chart, can't
  push it to debate, can't even copy it via an affordance. Every other list in the app
  has row actions; this one has none. Fix: same row-action strip as SCANNERS (chart /
  debate / shortlist). Effort M.
- **P1 — Raw JSON dump rendered in the RESEARCH BENCH panel:**
  `{ "models": [], "experiments": [] }` as a <pre> [rendered]. Replace with the honest-
  zero pattern used everywhere else. Effort S.
- **P1 — "What did the quant layer actually deliver" is illegible.** The tab mixes
  real-and-running (leadership ranking, shrunk setup evidence over 58 resolved paths),
  data-starved (HMM), and not-built (0 registered models) with equal visual weight and
  no per-panel status. Fix: a REAL / SHADOW / WARMING / NOT-BUILT status chip system on
  every Alpha panel, with one line each on what it would do when alive. Effort M.
- **P1 — LEADERSHIP column: six ties at 100%, no definition of the score** [rendered],
  no sector/why per row (the WHY panel is generic prose). Effort S-M.
- **P2 — "posterior hit 3% / -1.21R" family evidence is strong content with no
  so-what**: nothing says "this is why tonight's verdict said paper-trade". Cross-link
  to the MARKET verdict which cites the same base rate. Effort S.

### 11.3 The HMM pattern (coordinator item 3) — "experimental organs shown dead,
unexplained" — P1, app-wide

[rendered evidence] DEBATE context: "HMM: warming up (2/20)"; DEBATE table STOCK HMM:
BULLISH/CHOP/n/a mix; ChartDrawer: "STOCK HMM · EXPERIMENTAL — insufficient history
(141 clean bars, need >= 150)". Root cause is data+pipeline (trains on
regime_snapshots, only 286 sessions since 2025-03-19; output table regime_hmm_states
absent — fix by replaying backfill-snapshots over the new 5y daily_prices panel), but
the UX defect is generalizable: **the app shows experimental/warming organs without
telling the beginner (i) what this organ will do when alive, (ii) what "2/20" counts,
(iii) whether to ignore it today.** Same pattern: "ALPHA READ · WARMING" cards on
DEBATE, "ML P(UP 10D) —" blanks, "BUILDING SAMPLE n=5" in JOURNAL, "coming" presets on
SCANNERS (this one is done well — "planned, not a zero-result scan" is the model to
copy). Fix: one standard WarmingChip component: status + fill-condition + ignore/heed
advice. Effort M.

---

## 12. CROSS-CUTTING

- **Navigation continuity — FAIL.** No URL state (§1); tab switches do preserve
  in-memory state within a session but symbol context does NOT travel: opening ARVIND's
  chart on SCANNERS then switching to DEBATE does not focus ARVIND. debateJump exists
  for explicit pushes only ([code] App.jsx). P1, M.
- **Chart-from-anywhere — PARTIAL.** Scanner rows ▤, shortlist thumbs, debate cards yes;
  ALPHA rows no; POSITIONS no; TRADE PLAN no; header search no. And any symbol without a
  nightly PNG 404s with no on-demand render (§4). P1.
- **Compare two symbols — DOES NOT EXIST.** [code] zero "compare" hits in src/*.jsx
  (only prose matches in MarketHomeTab copy). No side-by-side charts or plans anywhere.
  P2 (worth doing as part of ChartDrawer prev/next work), M.
- **Guided beginner flow — vaporware in UI, real on server.** §0. P0.
- **Provenance/next-trigger — surfaced but freshness-broken** on SHORTLIST (§4 P0);
  provenance chips (SCAN/PUSHED/USER) good on DEBATE/Strong-Start.
- **Live-work visibility — nightly only** (§10).
- **Freshness under LIVE-first — inconsistent.** Stale banners exist at shell level;
  per-number as-of markers absent (POSITIONS "NOW", SHORTLIST triggers vs last price,
  MBI "DAY GREEN" vs live). fyers_connected:false right now and NO surface says the
  live feed is down. P1, M.
- **Honest-zero states — mostly excellent** (MARKET monthly-breadth, JOURNAL, SCANNERS
  "planned" lanes). Exceptions: ALPHA's raw JSON (§11), "no agent thesis" dead end (§7).
- **Keyboard/a11y — spot-checked:** aria-labels on icon buttons and date scrubber are
  present [rendered]; role=search on the form; dialog semantics on ChartDrawer; BUT no
  app-level shortcuts, no focus trap in the drawer, no skip-link, and
  **prefers-reduced-motion exists in only 3 of 10 CSS files while App.css declares 11
  animation/transition rules with zero reduced-motion guard** [code: grep counts]. P2, S.
- **Console — clean** (0 errors during the whole drive) [rendered].
- **Perf — SCANNERS mounts 5 duplicate preset fetches; ~10s to first content** (§3).

---

## TOP-10 PRIORITIZED FIXES

| # | Fix | Screen | Effort |
|---|-----|--------|--------|
| 1 | Render `/api/flow/today` as the persistent guided flow rail + per-tab purpose headers (§0 design) | shell/all | L (rail M + headers M) |
| 2 | SHORTLIST "WAITING ON" freshness: date-scoped reasons, never contradict the verdict chip | SHORTLIST | M |
| 3 | "How these lists relate" legend + cross-badges on ALPHA/DEBATE/SHORTLIST | 3 tabs | S-M |
| 4 | Scanner preset click: scroll-into-view / inline results + kill 5x duplicate fetch | SCANNERS | S |
| 5 | ALPHA row actions (chart/debate/shortlist) + remove raw JSON + status chips (REAL/SHADOW/WARMING/NOT-BUILT) | ALPHA | M |
| 6 | Hash-router: tab/symbol/date in URL; back button and shareable links | shell | M |
| 7 | POSITIONS: remove dry-run debug string; add freshness chip on NOW price; link to origin debate | POSITIONS | S-M |
| 8 | TRADE PLAN: embed chart + persist checklist + "log decision → journal" CTA + copy-ticket | TRADE PLAN | M |
| 9 | JOURNAL delete button (endpoint already exists) + manual lesson/edit entry | JOURNAL | S |
| 10 | Date scrubber → date picker + "latest" chip + trading-day skip; fix empty-date dead end | shell | S |

---

## HIGHEST-CONVICTION STRUCTURAL PROBLEM (one paragraph)

The desk has world-class *component honesty* and zero *system legibility*: every card
explains its own number, no surface explains the machine. The proof is that the six-step
guided daily flow the design speced (T3.8) is fully implemented at `/api/flow/today` —
statuses, blockers, per-step actions — and the frontend never calls it, so a beginner
lands on twelve breadth panels and three mutually contradicting stock lists with no
"you are here, do this next". Ship the flow rail + per-tab purpose headers (Top-10 #1)
and most of the P1 comprehension findings (list confusion, warming organs, jargon)
collapse into slots inside an understood system instead of free-floating mysteries.
