# HANDOFF — Scouting × Wire build wave (2026-08-24)

**Binding specs (read in this order):**
1. `traderlog/design/REDESIGN_SCOUTING_WIRE.md` — the owner-approved fourth visual
   direction. **This is the spec.** On build it supersedes `VISUAL_LANGUAGE.md`
   §1, §1a, §3 in full. The renderer ladder (§2), the component contract (§6),
   the truth/evidence rules and the empty-state contract carry over unchanged.
2. `traderlog/design/VISUAL_LANGUAGE.md` — §2 (renderer ladder), §6 (component
   contract — public props are FROZEN), §7 (implementation notes) remain
   binding. §1/§1a/§3 are superseded by the redesign doc.
3. `traderlog/design/WIREFRAMES.md` — element lists carry over where the
   redesign doc does not contradict them; the reconciling rewrite is the
   orchestrator's, published as part of this wave.
4. `traderlog/design/AUDIT_LEDGER.md` — C6 retraction + C8 (XP fix) apply to S1.
5. `traderlog/design/CONTRACTS.md` — §8 API table; **S9 updates it in the same
   change** whenever a payload shape changes.

**Owner decisions made for this wave (2026-08-24, recorded):**
- **Fix XP first (C8), then reskin Market.** The Market screen is built in the
  new language and renders **without** the §8 caution block (`--caution` block
  is removed when XP is fixed; the fix lands in this wave). If the recompute
  evidence fails (early-series transient not eliminated), the orchestrator
  re-adds the block — a stale disclaimer is its own kind of dishonesty.
- **Keep the centered 1680px desktop grid** at 1920×1080 (W3c structure).

**Group-wide rules (from traderlog/AGENTS.md + STANDING_INSTRUCTIONS.md):**
- Do NOT commit anything. Leave the working tree; the maintainer commits.
- Do NOT touch `manas_os/` or `legacy/`. No `import manas_os` anywhere.
- Never run `seed_mock.py` against `data/traderlog.db`. Production DB is
  real-data-only. No subagent touches the production DB file at all — the
  orchestrator performs the single XP recompute with a pre-change backup.
- Every percentage shows its `n`; unstated renders `—` / "not stated", never
  0; adaptive precision (2dp under ₹100, 0dp above) is a correctness rule.
- `tokens.css` is the ONLY file that may contain a colour literal. No raw hex
  in a component, chart spec, screen, or per-screen CSS — resolve everything
  through `var(--token)`.
- Charts never animate on load; every chart has `role="img"` + an
  `aria-label` stating the finding in words; every chart renders the labelled
  `.chart-empty` one-line empty state when it has no data (never null, never a
  zero-height SVG).
- Microcopy: the strings flagged in §7 of the redesign doc as "must survive
  verbatim" are protected. See the copy appendix below.
- Model-work attribution: after finishing, each subagent reports in its final
  message: its own `model` id if its environment documents one (else
  `unknown`), `host_tool`, and a one-line `scope` summary. The orchestrator
  appends `MODEL_WORK_LOG.jsonl` records.

---

## File ownership matrix (binding, no overlap — parallel agents)

| Agent | Owns exactly these files | Must NOT touch |
|---|---|---|
| S1 | `adopted/xp.py`, `adopted/regime_daily.py`, `db/schema.sql` (stale C6 comments only), `adopted/universe_breadth.py` (comments only), `config.example.yaml` (seed comments), `tests/test_adopted_xp_mbi.py`, `tests/test_adopted_regime_daily.py`, `tests/test_run_w4.py` | anything else; production DB |
| S2 | `ui/src/styles/tokens.css`, `ui/src/styles/app.css`, `ui/index.html`, `ui/src/App.jsx`, `ui/src/main.jsx`, `ui/src/components/ui.jsx`, `ui/src/components/CommandBar.jsx` (new), `ui/src/screens/Style.jsx` | screens/* except Style.jsx, charts.jsx, api.js, api/ |
| S4 | `ui/src/components/charts.jsx` | everything else |
| S3 | `ui/src/screens/Today.jsx` (renames/deletes `Feed.jsx`), `ui/src/styles/today.css` (replaces/deletes `thread.css`) | everything else |
| S5 | `ui/src/screens/Ledger.jsx`, `ui/src/styles/ledger.css` | everything else |
| S6 | `ui/src/screens/Traders.jsx`, `ui/src/styles/traders.css` | everything else |
| S7 | `ui/src/screens/Ideas.jsx`, `ui/src/screens/Library.jsx`, `ui/src/styles/ideas.css`, `ui/src/styles/library.css` | everything else |
| S8 | `ui/src/screens/Market.jsx` (renames/deletes `Breadth.jsx`), `ui/src/styles/market.css` | everything else |
| S9 | `api/app.py`, `ui/src/api.js`, `ui/src/screens/Symbol.jsx` (new), `ui/src/styles/symbol.css` (new), `ui/package.json` + `package-lock.json` (add `lightweight-charts`), `design/CONTRACTS.md` (§8 only) | screens owned by S3–S8 |
| S10 | `tests/test_pc_layout.py`, `tests/test_browser_review.py`, `tests/test_scouting_wire.py` (new) | everything else |

**App.jsx screen imports (fixed contract — final names):**
`Today, Ledger, Traders, Ideas, Library, Market, Style, Symbol` — default
exports, files `screens/{Today,Ledger,Traders,Ideas,Library,Market,Style,Symbol}.jsx`.
`NAV_TABS = ["TODAY","LEDGER","TRADERS","IDEAS","LIBRARY","MARKET"]`, all
uppercase labels. `ALL_TABS` adds `"STYLE"` and `"SYMBOL"` (route-only, never
in visible nav). `NAV_PARAM_KEYS` stays `["handle","symbol","position"]`.
`?tab=SYMBOL&symbol=X` opens the symbol landing page. The FEED review-count
badge moves to the TODAY tab. Cross-screen navigation keeps working:
handle → TRADERS, symbol → SYMBOL landing page (and LEDGER filter where it
already existed), thread/post link → x.com.

**Per-screen stylesheets** live in `ui/src/styles/*.css` and are imported by
their own screen module (precedent: `thread.css`), so agents never edit
`app.css` in parallel. `app.css` = shell, layout grid, shared primitives.
`tokens.css` = tokens + base element reset only.

**ui.jsx public API is FROZEN for this wave** (screens compile against it while
S2 restyles): keep every existing export and signature — `Panel, Chip, Conf,
Num, Pct, Bar, Segmented, SortableTh, Disclosure, Empty, Loading, MockBanner,
ErrorBox, useApi, fmtDate, fmtTime` — restyling internals to the new tokens is
allowed and required. ADD one export: `Stat({ value, meaning, n })` — the
explained-stat component. `CommandBar` lives in its own new
`components/CommandBar.jsx` (S2). Do not remove or rename existing exports;
screens may stop using some of them.

---

## Token layer (§3 of the redesign doc — exact values, S2 implements)

```css
/* ground + structure */
--ground:      #0f1115;   /* canvas */
--raised:      #141821;   /* explained-stat blocks, callouts */
--sunken:      #181b21;   /* timeline lanes, track backgrounds */
--edge:        #23262d;   /* region border, 1px */
--hair:        #1c1f25;   /* row separator, 1px */

/* ink ladder */
--ink:         #e9eaed;   /* primary */
--ink-2:       #8b929d;   /* the plain-English gloss — Rule 1 lives here */
--ink-3:       #6f7681;   /* labels, handles, metadata */
--ink-4:       #5d626b;   /* timestamps, struck text */

/* meaning */
--risk:        #c6f24e;   /* MONEY WAS RISKED. Nothing else. */
--up:          #2f9e63;   /* a stated positive result */
--down:        #8a4a3f;   /* a stated negative result, or a removed post */
--caution:     #c9a227;   /* we do not trust this number */
--caution-bg:  #2a1f14;

--radius: 0;
--shadow: none;
```

Type: system grotesk for prose; mono with `tabular-nums` for every numeral,
date, price, confidence and identifier — never prose. Hero numbers 800 weight,
`-0.03em` tracking. Section kickers 9.5px, `0.13em` tracking, uppercase, 800.
Prose sentence case everywhere. Scale: `hero 33 · value 15 · body 12.5 ·
gloss 11.5 · meta 10.5 · kicker 9.5` (`--fs-hero/--fs-value/--fs-body/
--fs-gloss/--fs-meta/--fs-kicker`). Rows ~26px plain, ~30px where a control
lives (28px hit target minimum).

Class vocabulary (shared — S2 defines in app.css, screens use it):
`.shell .topbar .brand .tabs .tab(.active) .tab-count`, `.page` (1680px
centered grid), `.kicker` (uppercase 800 0.13em), `.stat` / `.stat-value` /
`.stat-gloss` (the explained-stat component), `.mono`, `.chart-empty`,
`.panel` (region with one 1px `--edge` rule; no nested boxes), `.row` /
`.row-control`, `.band`, `.footnote`, `.empty`, `.loading`. Keep `.disclosure`
hit-area behavior. No raw colour literals anywhere but tokens.css.

**The explained-stat component** (build order §10.1) lives in `ui.jsx` as
`<Stat value={...} meaning={...} />`: a mono hero/value numeral WITH its
plain-English meaning sentence beneath (`--ink-2`). If a number cannot be
given a truthful meaning, the screen renders the em dash instead. Every
percentage renders with its `n`.

---

## Screens — the binding redefinitions

### Today (was FEED) — S3
Consumes `/api/feed` (+ `/api/review` on top), `POST /api/review/{id}`,
`/api/traders`.

- Bands, in fixed order, each headed by a `.band` with a **kicker label** and
  ONE line explaining *why these are grouped* (not a description of the group).
  Banding is computed, never editorial (Rule 2):
  - **Money moved** — `kind === 'trade_event'` AND a price or stop was stated
    (the feed's `event` join carries a stated price/stop; presence of
    `event.price` is the test).
  - **Names to watch** — `kind === 'watch_idea'`.
  - **Background** — `kind IN ('breadth','theme','education','noise')`,
    plus unclassified, plus any post the rule cannot place (including
    `trade_event` with no stated price).
  - **Removed** — `deleted_at IS NOT NULL`, always its own band, always kept,
    rendered struck + dimmed (`--ink-4`), with the protected note (copy
    appendix). **The band renders only when non-empty** (0 rows today; it
    appears after a real deletion is caught — the wire doc §11).
- Each row: band label · handle · **verbatim post text** (never paraphrased) ·
  gloss (the plain-English meaning — Rule 1) · time (`ts_ist`). The gloss
  cites the trader's own record ONLY when `trader_style` has ≥10 closed
  positions — it does not today, so **omit record glosses entirely rather
  than inventing one** (§11). Glosses derive from payload fields only
  (kind, event kind/price/qty_pct, deleted_at): see the gloss table below.
- Known conversations keep their identity: a post with `thread_pos/thread_size
  > 1` renders its position chip and its self-replies render beneath it in
  the same band (the evidence-desk spine survives as 1px `--edge` rule).
- The **review queue** stays on TODAY above the bands ("work the human owes
  the tool"), one decision at a time, same accept/reject API, restyled to the
  new language. It is not a band. The badge on the TODAY nav tab counts open
  items; a decision refreshes it in-session.
- Filters (trader / kind / confidence / unresolved toggle) survive as a
  compact toolbar above the bands — they exercise the existing `/api/feed`
  query params. Content is paginated ("load more") through
  `pagination.next_offset`; posts land in their band by rule regardless of
  page.
- Deleted-post rows keep the web link out; the "removed by its author" note
  is the protected copy, not new writing.
- Keep `MockBanner` (`is_mock`) behavior unchanged.

### Ledger — S5
Consumes `/api/positions`, `/api/positions/{id}`.

- **The shared time axis is the signature element and is not negotiable** (§4.2):
  one lane per position on ONE time axis; clip spans entry→exit; lanes on
  `--sunken`. Implemented via the `PositionBars` wrapper whose internals S4
  remaps to an **ECharts custom series** (per §5 ladder). Clip colour:
  `--risk` open · `--up` stated positive · `--down` stated negative ·
  `--ink-4` unstated. Markers on the lane for adds and stop moves (the
  existing `events:[{at,kind:"add"|"sl_up"|"sl_down"|"exit"}]` contract
  stays).
- Right column beside the axis: the **outcome in words**, and a `--caution`
  line for anything unstated — e.g. `⚠ no exit price given` (copy appendix).
- **Below the axis: one sentence naming what the overlap shows**, computed
  from the data (e.g. "Manas and Fastzone were both in FCL at the same time.")
  or, when nothing overlaps, an honest sentence saying so. Never a generic
  placeholder.
- The sortable/filterable table stays **beneath** the axis; expanded detail
  keeps the event timeline, the evidence block (not behind a toggle), the
  `unresolved` disclosure with complete strings, and the W3c **media
  containment** rules (images obey their media box; the document never
  overflows 1920px).
- Protected copy: "Results are what the trader *said* — never computed from
  market data" survives verbatim.

### Traders — S6
Consumes `/api/traders` (S9 adds stop-discipline fields to its summary;
see API changes).

- **One question at a time, ranked, with the sample size visible** (§4.3).
  The question is stated in plain English above the ranking (e.g. "How often
  a trader who names an exit price actually uses it."). A `Segmented` control
  switches between the questions where data exists: stated win rate,
  stop-kept rate, average R, median hold, preach score.
- Bars dim to `--ink-4` below the confidence threshold; below threshold the
  cell shows an em dash and the words **"too few"** — never a percentage
  (§6: a trader's rate needs ≥10 closed positions; preach needs ≥10 linked
  trades). The `n` is always visible.
- Below the ranking, one line, verbatim: *"A dim bar means too little history
  to lean on. A dash means we won't guess."*
- `trader_style` is empty today (W6 not built): every row will honestly show
  the dash/"too few" state. Build the mechanism fully; do not fake data.
- Charts (from `charts.jsx`, each with its labelled empty state):
  hold-time `StripPlot` (Vega-Lite), stop-discipline `Dumbbell` (Vega-Lite),
  play-type mix over time (ECharts stacked area — new wrapper), posting
  cadence (ECharts calendar — new wrapper, `CalendarGrid`).
- The roster table stays beneath (or beside) the ranking: handle, tier,
  posts, open, closed, hold, win, preach, with `SortableTh`. Roster rows are
  keyboard-reachable (existing `Disclosure` treatment); selecting a trader
  uses the existing preset-handle navigation.

### Ideas — S7
Consumes `/api/ideas`, `/api/positions`.

- Grouped **by symbol, never by trader** (already the API shape): three people
  on one name is the finding. Order by trader count then recency.
- Per symbol: a **heat strip** showing mention density over time — inline SVG
  (trivial, no library, §5 ladder), labelled; then each mention quoted
  **verbatim** with handle and date (kind chip: WATCH/EP/IPO/THEME styled by
  weight, never hue).
- A follow-through line per symbol: who actually bought it (from `taken_by`)
  or **"nobody has bought it"** when true.
- Footnote (protected copy, Ideas.jsx today):
  "This screen reports what was said and who acted, not who was right.
  Whether the stock moved is deliberately not shown — a different question."
- Keep the themes list (payload-driven) and the ticker leaderboard computed
  client-side from `/api/positions` + `/api/ideas` (kept from WIREFRAMES §5).

### Library — S7
Consumes `/api/library`.

- **The quote is the hero at full size** (§4.5): verbatim principle,
  attributed (`@handle`), dated, with the post link.
- Beneath it, a `--raised` (`--raised` ground) block summarizing the record in
  words: "Followed in N of M trades where he named a stop. Of the K he didn't…"
  built from `practice` (followed/violated/na/n/min_n/enough/score_pct) and
  `violations` (each cites its position — evidence is visible, never behind a
  toggle).
- Below the minimum sample (`n < min_n`, 10): the block renders `--ink-4`
  with *"Not enough to say yet — only N trades link to this. We won't score
  it until 10."* (N real). **No percentage at all below the minimum.**
- Topic tabs from `library.topics`. `edu_items` is empty today — the screen
  renders the compact one-line empty states honestly.

### Market (was BREADTH) — S8
Consumes `/api/breadth` (S9 adds `advances`/`declines` to its history rows).

- **Deliberately quiet. No accent anywhere. No `--risk` on this screen at
  all.** Only `--up`/`--down` for day colours, `--caution` only if a number
  is disclaimed (not in this wave — XP is fixed; orchestrator re-adds only if
  the fix evidence fails).
- A hero XP number (`Stat`) with its plain-English meaning **and its age**
  (the trade_date; the meaning is the band gloss — copy appendix). The
  meaning sentence carries the caveat ("most days are not strong markets" is
  how the dial reads). Band glosses, sharp-colleague voice, no bare numbers:
  - LOW: "Only a few stocks are pushing higher. Breakouts fail more often in a
    market like this." (verbatim from the microcopy table)
  - BUILDING: "More stocks are starting to push higher, but the rope is still
    out — treat breakouts as unproven."
  - STRONG: "Most stocks are pushing higher — a breakout has a real chance of
    working."
  - EXTREME: "The whole tape is extended. Breakouts work until they stop
    working — assume reversion risk."
  Age: "as of 2026-08-14" plus, when the reading is old, the honest stale
  sentence "This reading is N days old — the market has moved since."
- Day-colour ribbon: inline SVG (trivial, §5), one hard block per session
  (existing `Ribbon` contract), legend **in words**: "■ most stocks rose" /
  "■ roughly even" / "■ most fell".
- Cumulative advance–decline: **ECharts line** (via the `BandLine` contract or
  a new exported wrapper owned by S4) from `history[].advances/declines`.
- Trader stances against what the market did (existing stances/agreement
  payload) with `n=` always shown, and the protected footnote:
  "This measures agreement with one particular breadth model — not whether
  the trader was right."

### Symbol landing page (new) — S9 + S2 route
Consumes the new `GET /api/symbol/{symbol}`.

- Candles from `daily_prices` via **lightweight-charts** (§5 ladder; the only
  place it is used). The pane renders bars ONLY for a symbol **validated
  against the NSE universe** — validation is: the symbol has rows in
  `daily_prices` (bhavcopy = NSE EQ) AND matches the corpus. If either is
  missing, render the labelled empty state saying which: "No price history
  for this symbol" vs "This symbol is not in the corpus". Never a chart of an
  invalid instrument.
- Also shows corpus context: positions for the symbol and watch-idea
  mentions, linking to LEDGER/TRADERS.
- Route: `?tab=SYMBOL&symbol=X`; symbol links across the app navigate here.

### New charts.jsx exports (S4 owns the file; S6 consumes; contracts fixed here)

```jsx
// 2.10 — play-type mix over time. One stacked area per session. ECharts.
<StackedArea
  rows={[{ x: "2026-08-01", segments: [{ label: "breakout", value: 3 }, ...] }]}
  n={183}                      // total mentions across rows, shown beside the title
  suffix=""
/>
// labelled .chart-empty when rows is empty. Never a pie. aria-label states
// the mix finding in words.

// 2.11 — posting cadence. One cell per posting day. ECharts calendar.
<CalendarGrid
  from="2026-06-01" to="2026-08-31"
  cells={[{ date: "2026-08-01", count: 4 }]}
  caption="posts per day"
/>
// labelled .chart-empty when cells is empty.
```

These two are the ONLY new public exports. Everything else stays exactly the §6
contract (props frozen; internals remapped per §5: PositionBars → ECharts
custom series for the Ledger shared time axis; Dumbbell + StripPlot →
Vega-Lite; BandLine → ECharts line; Ribbon + SmallMultiples stay inline
SVG/composable; StackedStrip stays).

### ⌘K command bar — S2
Global keydown (`Mod+K` on mac, `Ctrl+K` elsewhere) opens an overlay palette:
jump to any tab, any trader (from `/api/traders`), any symbol (from
positions + ideas). Arrow keys + Enter navigate; Escape closes; fully
keyboard accessible; restyled to the new language. No new dependencies.

### STYLE — S2
Dev reference screen, restyled to the new tokens/scale; still excluded from
visible nav, still reachable via `?tab=STYLE`. Keep every primitive specimen.

---

## Copy appendix (verbatim, binding)

**Protected — must survive word-for-word (copy audit):**
1. Deleted-post note (Today): "⚠ this post was removed by its author. Kept on
   purpose — traders delete losers, and dropping them would bias every derived
   metric."
2. Market footnote: the agreement measure tests one particular breadth model —
   **not** whether the trader was right (existing Breadth.jsx wording).
3. Ledger: "Results are what the trader *said* — never computed from market
   data."

**Gloss patterns (Rule 1 — write sentences, never bare numbers):**
- `trade_event` entry: "Put money on SYMBOL at PRICE." (price only if stated)
- add: "Added at PRICE." · partial exit: "Took profit at PRICE of what he
  risked. Holds the rest." · exit: "Booked SYMBOL at PRICE." (in words, with
  `qty_pct` when stated)
- stop set/moved: "Stated a stop at PRICE." / "Moved the stop to PRICE."
- watch_idea: "A name to watch" (+ trigger text verbatim when present)
- breadth: "His read on the market that day."
- theme: "A theme, not a trade." · education: "A principle, not a trade."
- noise: "Not about the market."
- unclassified: "Not yet classified."
- deleted: "Up HH:MM, gone by HH:MM." (from `ts_ist` and `deleted_at`)
- unstated stop on a money-moved row: "⚠ He never said where he'd get out."
- Removed band: "People delete losers, and forgetting them would flatter
  everyone's record."
- Traders, below threshold: em dash + "too few" (never a percentage);
  under the ranking: "A dim bar means too little history to lean on. A dash
  means we won't guess."
- Library, below minimum: "Not enough to say yet — only N trades link to
  this. We won't score it until 10."
- Ideas follow-through: falls back to "nobody has bought it" when true.

Voice: a sharp colleague who respects your time. Direct, specific, unhedged,
occasionally blunt. Never chirpy, never a tutorial, never talking down.

---

## API changes (S9 — update CONTRACTS.md §8 in the same change)

1. **`GET /api/symbol/{symbol}`** (new) — `{"symbol", "validated": bool,
   "prices": [{trade_date, open, high, low, close, volume}], "source",
   "positions": [...], "mentions": [...], "is_mock"}`. `validated` = symbol
   present in `daily_prices` (bhavcopy NSE EQ source). Shape-stable: removing
   mock data only empties arrays.
2. **`GET /api/breadth`** — history rows additionally carry
   `advances`/`declines` (join `breadth_daily` by `trade_date`) so Market can
   draw the cumulative A/D line. Additive; no existing field changes.
3. **`GET /api/traders`** — summary additionally carries `stop_stated_pct` /
   `stop_honored_pct` (from `trader_style`) for the stop-kept question.
   Additive; null when absent.

---

## XP fix (C8) — S1, per AUDIT_LEDGER.md addenda (2026-08-24)

Facts (from the audit, verified in code):
- C6 is **retracted**: percent-scale `up_4pct`/`down_4pct` inputs are
  correct. `adopted/regime_daily.py` still converts percent→count at the XP
  call site (the retracted C6 fix is live) — **remove that conversion**; feed
  the raw percent columns into `xp_for_date` again.
- C8: the _XP_CAP hits (2024-09-17 → 2024-09-26) and early EXTREME band are a
  **seed transient**: the recursion unwinds from `xp_seed: 15.0` /
  `xp_z_seed: 20.0` (count-scale constants) for ~15–25 sessions.
  **Fix:** at a reseed point, seed the z-state from the session's own
  observed `up_4pct` (percent scale) instead of the constant; keep the
  `xp_seed` config fallback only when no observed value exists. Warm-up or
  discard the transient rather than presenting it as data.
- Also correct the stale comments that claim counts (they caused C6):
  `xp.py` module docstring, `db/schema.sql` breadth_daily block comments,
  `universe_breadth.py` mentions if present, `config.example.yaml` seed notes.
- Update `tests/test_adopted_xp_mbi.py`, `tests/test_adopted_regime_daily.py`,
  `tests/test_run_w4.py` to the percent convention + observed-z seeding.
- Done-test (disposable DBs only — never production): full-series recompute
  over the real 446 breadth_daily dates yields **no cap hits at series
  start**, no four-EXTREME cluster immediately after seed, a distribution
  comparable to the audit's percent row (median ~7.7, most days LOW —
  reference "tops out ~30"), and the environment's `latest-5` breadth/regime
  parity still holds. Report the recompute numbers in the final message.
- Also report: whether `2025-06-20` (the real 46-day gap reseed) also seeds
  from observed data, and what fallback behavior fires when `up_4pct` is
  missing.

---

## Verification (orchestrator, after agents land)

1. `python traderlog/run_checks.py` before (done — exit 0) and after.
2. `python -m pytest traderlog/tests -q` — whole suite green (currently 264).
3. `npm run build` in `traderlog/ui` — clean Vite build.
4. 1920×1080 real-browser pass on a disposable DB: bands in order, accent
   scoping (no `--risk` on Market), no bare percentage without `n`, no
   overflow, clean console; screenshots to `output/playwright/scouting-wire/`.
5. Production XP recompute: backup `data/traderlog.db` first, recompute
   `regime_daily` (stage 4 only, strict ascending order), verify distribution
   + `derive` check, record numbers in `AUDIT_LEDGER.md`.
6. Docs reconciliation by the orchestrator: `VISUAL_LANGUAGE.md` (supersession
   banner), `WIREFRAMES.md` (rewrite the six screens + Symbol + ⌘K),
   `DECISIONS.md` (dated line), `AUDIT_LEDGER.md` (C8 closed with numbers),
   `TASKS.md` (wave entry), `HANDOFF.md` (To-continue), `STATE.json` via
   checks, `MODEL_WORK_LOG.jsonl`, `_COMPLETED.md`.

**Attribution**: every completed handoff carries `Attribution-ID:` lines
resolved from `design/MODEL_WORK_LOG.jsonl`; the orchestrator appends its own
record only after personally running the verification above.

**Done-test (whole wave):** checks exit 0; pytest green incl. updated and new
scouting-wire browser tests; Vite build clean; 1920×1080 browser pass with
zero console errors and zero overflow; XP distribution evidence recorded;
docs reconciled; `_COMPLETED.md` written; nothing committed.