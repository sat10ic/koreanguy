# DECISIONS — locked calls, dated

Manas OS scattered its locked decisions across a dozen single-topic files with no
index, so nobody can answer "what has already been decided?" without reading all
of them. This file is that index. One dated entry per irreversible or
expensive-to-reverse call.

Append, never rewrite. If a decision is reversed, add a new dated entry that says
so and leave the original in place — the reasoning that was wrong is worth as much
as the reasoning that was right.

### 2026-08-27 · INS-2 tape-after-mention — IST anchor boundary locked at 09:00
The INS-2 implementation locks the IST session boundary and the symbol-level
anchor as one spec'd call (INSIGHT_SURFACES_PLAN.md §INS-2 required the
implementation to lock it before shipping): a post strictly before 09:00 IST
whose IST calendar date has a session in the symbol's `daily_prices` anchors to
THAT session's open; everything else (09:00:00 IST or later, or a session-less
date) anchors to the next available session strictly after the post's IST date.
Sessions are the symbol's actual `daily_prices` rows — never calendar-guessed —
so holidays and weekends fall out naturally. Returns are forward CLOSE returns
`close[i+k]/open[anchor] - 1` at +1/+5/+10/+20 trading sessions; a missing
horizon is null, never zero; the anchor session's own close is never used, so
the computation cannot be read as close-to-close. The per-symbol anchor is the
symbol's FIRST mention inside the Radar window (its "entry into the corpus" for
that view), not the strongest-cluster start date. No win/loss or direction
label is produced anywhere. Implementation: `derive/tape.py`, locked by
`tests/test_derive_tape.py`; surfaced on the /api/radar `co_attention` rows and
the Radar "Close return after anchor open" column.

### 2026-08-25 · Ledger scale lenses — the shared axis renders a scoped slice
With 23 reconstructed positions (and 384 reconcile candidates), the one-lane-
per-position shared axis is visually saturated. Owner approved scoping lenses:
a **status lens** (`OPEN · CLOSED · ALL`, default OPEN = open + last-90-day
closes) and a **window lens** (`30D · 90D · 1Y · ALL`) narrowing the time
domain. The signature element is preserved — one lane per position *within the
visible slice*; clustering in time stays visible inside any scope. Lenses
re-scope the outcome strip, overlap sentence, and table defaults; full history
remains queryable, never deleted. Spec: WIREFRAMES.md §3 "Scale lenses".

### 2026-08-25 - Live X capture retired - backend data feed is the source
The owner confirmed Chrome/X capture (run_xfetch.py) is NOT needed: the backend
price/corpus feed covers the tools needs. Capture code stays in the repo but is
not a standing dependency; ingest freshness WARNs are expected and acceptable.
Owner decision, 2026-08-25.

### 2026-08-24 · Scouting × Wire is the binding visual direction; Market waits on the XP fix
The owner approved the fourth visual direction, `design/REDESIGN_SCOUTING_WIRE.md`
— dark ground, citrus accent meaning exactly one thing (money was risked), wire
triage on TODAY, a shared time axis on LEDGER. On build it supersedes
`VISUAL_LANGUAGE.md` §1, §1a, §3 in full; the renderer ladder (§2), component
contract (§6), truth/evidence rules, and empty-state contract carry over
unchanged. Per the same wave decision (owner, 2026-08-24): fix the XP seed
transient (C8) FIRST, then reskin MARKET — and Market renders without the
caution block once XP is fixed (a stale disclaimer is its own kind of dishonesty).
The 1680px centered desktop grid stays.

### 2026-08-23 · Model-work attribution is append-only and machine-checked
Every model-role contribution is recorded in `design/MODEL_WORK_LOG.jsonl` and
every completed handoff cites its exact attribution ID. Executor, orchestrator,
reviewer, and vision roles stay separate; undocumented model identity remains
unknown. `checks` enforces the record/report round trip. Chosen because a
multi-model tool needs auditable ownership without fabricated provenance.

---

### 2026-08-22 · TraderLog is a separate tool, not a Manas OS subsystem
The repo owner judged the Manas OS trading desk, ML engine, and positions modules
failures. TraderLog takes only breadth, the volume reverse-engineering work, and
infrastructure patterns, by **copying** them into `adopted/`. No `import manas_os`
anywhere. Neither project can break the other.

### 2026-08-22 · Ingest by polling timelines-with-replies, not by notifications
A trader's replies to their own posts do not fire bell notifications, and adds,
stop moves and exits are almost always self-replies. The notification and email
routes structurally cannot see the most important events. **This killed the
original design.**

### 2026-08-22 · Browser automation with the user's own logged-in profile
Chosen by the repo owner over the paid X API, with the risk flagged: it violates
X's ToS and risks account suspension. Mitigations: read-only, human-cadence
jitter, and a recommendation to point it at a secondary handle. The password is
never stored, never passed to a script, and never handled by an agent — Playwright
reuses a profile directory the user authenticates by hand.
The fetcher sits behind one interface so switching to the official API is a
one-file change. **Deferred, not rejected.**

### 2026-08-22 · Full thread re-derivation, never incremental state updates
The reconciler re-reads the entire thread and re-emits the complete position state
on every change. Incremental LLM state-diffing drifts within days and cannot be
tested against fixtures. Threads are short, so full re-derivation is cheap, and
caching on `thread_hash` means unchanged threads cost nothing.

### 2026-08-22 · Every extracted field cites its source post; nothing is inferred
`evidence_json` maps each populated field to the `post_id` that justifies it. A
field with no citation is dropped rather than stored. Anything a trader did not
state goes in `unresolved[]`. A wrong price is worse than a missing one, because
the value of this log is that it is a factual record.

### 2026-08-22 · Cross-thread links are proposed, never auto-applied below 0.8
The symbol linker is the accuracy ceiling of the tool and the one place ambiguity
is unavoidable. Low-confidence links go to `review_queue` for a human.

### 2026-08-22 · Deleted posts are kept, and the deletion is itself logged
Traders delete losers. Silently dropping deleted posts would bias every derived
style metric toward flattery and make the whole dataset dishonest.

### 2026-08-23 · Call sites request a tier, never a model
`llm/provider.py` exposes `cheap`, `smart`, `vision`. Model ids live only in
config. This is what makes the eventual migration to a local model a config edit
rather than a rewrite, and it is what lets any model be swapped mid-project
without touching parsing code.

### 2026-08-23 · Each tier is a fallback chain, not a single model
Prompted by the request to use **Ox Alpha**, a stealth model. Stealth endpoints
are renamed or withdrawn without notice, and a pipeline that names one model dies
the day that happens. Each tier is therefore an ordered list; the provider walks
it on failure and records which model actually served each call in `llm_runs.model`.

**`Unverified:` the OpenRouter slug for Ox Alpha.** It postdates this session's
model knowledge and was not guessed. Find it with
`curl -s https://openrouter.ai/api/v1/models` and put it first in the `smart` and
`vision` chains in `config.yaml`. No code change is needed.

**Note when using stealth models:** they are typically free because the provider
logs prompts and completions for evaluation. TraderLog sends public posts, so the
exposure is low — but this is a deliberate acceptance, not an oversight. Do not
route anything private through a stealth tier.

### 2026-08-23 · lightweight-charts for price candles; symbol validation first
Owner-approved amendment to the §2 renderer ladder, which previously named
Plotly for "financial charts". lightweight-charts is purpose-built for OHLC,
~45kb against Plotly's ~3MB, and is already proven at `manas_os/desk`
(v4.2.3) so there is adoptable code rather than a cold start. It is scoped to
**one row of the ladder** — an instrument's price pane — and is not a general
renderer. ECharts, Vega-Lite and Flint keep their rows unchanged.

Two preconditions, both binding, because a candle chart is the most
authoritative-looking surface this tool can render:

- **Price data must exist.** `daily_prices` was empty when this was decided;
  W4 fills it. A chart with no bars renders the labelled empty frame.
- **The symbol must be validated against the NSE universe.** The only symbols
  in the corpus today are `RATEGAIN` and `FCL`, and `FCL` was extracted from a
  bare `#FCL` hashtag with nothing checking it resolves to a real ticker.
  Charting the wrong instrument would look authoritative and be false — worse
  than charting nothing.

Sequencing follows from that: **W4 before charts.** W4 also unblocks the
BREADTH screen, the `derive` check, and `activity_mult` in the attention
engine, so it is the right next wave regardless of this decision.

### 2026-08-23 · Adopt the XP and MBI scores, but not the regime governor
Reverses the original plan, which excluded the whole XP/MBI layer. Requested by
the repo owner, and correct on inspection: both are reverse-engineered
practitioner constructs (XP from the finallynitin dial, MBI from Stocksgeeks) and
both are pure functions over a `breadth_daily` row — ~225 lines, no imports
beyond `math`. They give the BREADTH screen the ability to **grade** a trader's
market read rather than merely quote it.

The rest of `regime/snapshot.py` stays behind: `compute_pillars`, `market_mode`,
`compute_quadrant`, `four_phase.py`, `choppy_brake.py`, `run()`. That is the
governor, whose job is gating the user's own trades — squarely inside what
TraderLog does not do.

Two constraints that will bite whoever builds W4:
- XP is a **recursion** on the prior day's `xp_value`/`xp_z_state`. Backfill in
  strict date order; a gap in `breadth_daily` is a chain break, not something to
  interpolate. Seed from config on first run only.
- XP's weights were calibrated on the **NIFTYMIDSML400** universe. Feeding it
  advancer counts from a different universe produces plausible, wrong numbers
  silently. `universe_breadth.py` + `niftymidsml400_constituents.csv` are
  therefore hard dependencies of XP, not optional breadth extras.

Unrelated, despite the similar name: `manas_os/design/knowledge/MARKET_BREADTH_V2_REVERSE.md`
reverse-engineers Chhirag Kedia's breadth workbook, which contains no XP and no
MBI at all. Potentially useful later as breadth depth (Fosback HL Logic Index,
Stockbee 5/10-day ratios, NH-NL); not part of this adoption.

### 2026-08-23 · Inbound Telegram deferred
Resolving review-queue items by replying to a Telegram message needs a webhook
receiver that exists in neither project. Review resolution happens in the UI; the
Telegram nudge links into it. Revisit at W7 if the queue proves annoying.

### 2026-08-23 · Attention score decays with age; it must not reward crowding
Spec: `design/ATTENTION_ENGINE.md`. The obvious version of a "most discussed
stocks" heatmap ranks by mention count, and in momentum swing trading that ranks
day-6-of-the-move highest — the opposite of the early-entry edge this
methodology is built on. So the prioritisation score multiplies by a freshness
term that decays from 1.00 (0-2 sessions since first mention) to 0.10 (16+), and
discounts echo posts inside a 24h window.

Three further commitments made at the same time:
- **Talk and money are never summed.** An entry with a stated stop weighs ~6x a
  bare mention, because it is the only event where the author showed their risk.
- **Breadth dampens, never gates.** A RED warning day multiplies by 0.35, not 0.
  A leader emerging in a bad tape is exactly the setup worth seeing.
- **The score is unproven until backtested.** Ship criterion is the top decile
  beating the universe median at +10 sessions over ≥60 clusters; until then the
  screen ranks by raw attention and says so. An unvalidated prioritisation number
  is worse than none, because it will be trusted.

Acted on immediately in W0 rather than deferred: the classifier prompt and
`post_class` now capture `play_type` and `conviction_words`. Adding them later
would mean re-running every historical post through an LLM.

### 2026-08-23 (later) · Direction changed to neo-brutalist. Editorial is dead.
The repo owner rejected the editorial/statistical-almanac direction outright.
It was **inherited from Manas OS's locked aesthetic bar rather than chosen for
this tool** — a bad transplant. A trader-intel instrument is not a magazine.

New direction, chosen by the owner from four options: **neo-brutalist /
utilitarian, LIGHT surface, VERY DENSE.** Hard edges, 2px black borders, flat
solid colour, radius 0 everywhere, no shadow except a hard offset press
affordance, no serif anywhere, hover inverts to black.

Note the target is narrow: the owner has now ruled out **both** the editorial
aesthetic **and** the generic AI trading terminal (dark/neon/glass/donut/gauge/
six-KPI-cards/purple). `VISUAL_LANGUAGE.md` §1 bans both families explicitly,
because a banned list is what actually stops a model reaching for the default.

The light-only constraint was re-examined rather than assumed — it too was
inherited from Manas OS — and the owner independently chose light again.

Two rules that came out of implementing this and are correctness, not taste:
- **Accessibility beats density.** A 28×28 hit target cannot fit a 22px row.
  Rows carrying a control are ~30px; the control's visual box shrinks and its
  hit area is extended with a pseudo-element. Density never costs the target.
- **Numeric precision is adaptive** (2dp under ₹100, 0dp above). A fixed 0dp
  rendered a real broker fill price of `39.05` as `39`. Rounding away stated
  evidence is the same class of error as inventing a number.

### 2026-08-23 · Visual language is binding and sits above the wireframes
`design/VISUAL_LANGUAGE.md`. The W0 UI was tables with bars beside them and the
repo owner judged it bland — correctly. Root cause was that no binding appearance
spec existed, only a one-line "editorial poster" note, so every screen was built
to whatever its builder imagined.

The direction is a **printed statistical almanac** — FT/Economist data pages,
Tufte small multiples, Swiss data print. Test: could this graphic print in two
colours on newsprint and still carry its meaning?

The explicitly refused direction is the default "AI trading terminal": dark
canvas, neon glow, glassmorphism, gradient-filled charts, a donut with a big
number in the hole, gauges, a row of six rounded KPI cards, purple accents,
force-directed graphs. Every model reaches for that when told to make a trading
UI look good, so it is written down as a banned list rather than left to taste.

Consequences that are decisions, not styling preferences:
- **No chart library, ever.** Plain inline SVG. `lightweight-charts` is not a
  dependency of this project.
- **Colour carries state only** and must always be redundant with position,
  shape, or label. The screen has to survive greyscale.
- **One serif hero number per screen.** More than one is the KPI-card pattern
  wearing a different hat.
- **Every percentage shows its `n`.**
- **Every chart renders a labelled empty frame**, never `null`. The database is
  real-data-only and sparse, so empty is the common case and must look
  deliberate rather than broken.

### 2026-08-23 · TraderLog never sizes, routes, or advises
It records what other people publicly said they did. It does not tell the user
what to trade. Inherited from the Manas OS manual-execution-only lock, and it is
also what keeps the tool outside SEBI's algo framework. Any wave that blurs this
line is out of scope.

### 2026-08-23 · Visual language is binding above the wireframes
`design/VISUAL_LANGUAGE.md` is the source of truth for how every TraderLog
screen may look and how visual work is checked. It is read before
`design/WIREFRAMES.md`: the wireframes specify content and layout, while the
visual language constrains appearance, chart forms, controls, accessibility,
and the screenshot/greyscale completion audit. A screen can satisfy its
wireframe and still be defective under this higher-order contract.

### 2026-08-23 · Approved source universe expanded beyond the six-account starter
The user explicitly supplied `@StocksNerd`, `@ChartistEdge`, `@iArpanK`, and
`@mystocks_in` after the four-account live bootstrap. This supersedes the old
six-account target: TraderLog now has eight approved India/NSE sources. The four
new handles are capture-pending, not rejected. Activate each with its first real
archived post rather than inserting empty active rows, because live freshness is
defined over every active real trader.

### 2026-08-23 · Production TraderLog is real-data-only
After authenticated live capture became available, the user explicitly ordered
the mock corpus removed from production. `data/traderlog.db` must contain only
source-backed real rows. The deterministic mock seed remains useful, but only
against a disposable database selected explicitly for tests or demos; it must
never be used to refill production or to satisfy live/golden acceptance gates.

### 2026-08-23 · Visualization renderer ladder supersedes inline-SVG-only
The owner selected a four-tier implementation stack: Apache ECharts for the
core trading terminal, Vega-Lite for custom analytical graphics, Microsoft
Flint Chart for LLM-generated analytical panels, and Plotly.js only for deep
interactive exploration. This explicitly supersedes the earlier same-day
decision "No chart library, ever." Existing inline SVG can remain during
migration, but it is no longer the architecture for new visualization work.
Public React chart wrappers remain renderer-agnostic so the choice does not leak
through screen call sites.

### 2026-08-25 · Thread ancestry is unrecoverable from the existing corpus; positions are built atomically, not from threads
Investigated because `positions` held 3 rows and the reconciler's whole contract
is `reconcile_thread(conn, root_post_id)`. Verified by opening **all 3,360**
archived raw files: exactly **13 contain any ancestry key**. 3,348 are
`capture_method: "chrome_dom_provisional"` records whose only top-level keys are
`provisional_record` and `provenance` — `conversation_id`, `in_reply_to` and
`ordered_status_ids` are absent, not null. **Re-importing gains zero posts.**

There is no importer bug. `ingest/provisional_import.py:_relationship()` and
`chrome_import.py:_validate_record()` both correctly refuse to assert ancestry
they cannot prove, and `xfetch.py:341` is the single writer to `posts` per
CANONICAL.md §6. The loss is at **capture**: the reply-anchor selector
(`a[href*="/status/"][aria-label*="eply"]`) in
`output/playwright/evidence-desk/capture_x_devtools.py` and
`extract_manas_deep.py` matched zero times across every capture run on disk.

**Decided:** do **not** re-scrape a year of history to chase ancestry. The
existing 3,360 posts are extracted through a single-post path plus a symbol
linker, because the corpus's dominant trade-record format is already atomic —
237 posts carry an R-multiple or an entry/stop pair, against 3 positions built.
Thread reconciliation is retained for the 13 posts that have real ancestry and
for future capture, but **it is no longer the spine of the tool**. This is a
deliberate contract change, recorded rather than worked around; the alternative
(synthesising parents from timestamps or symbols) was considered and rejected as
fabrication.

### 2026-08-25 · Future capture moves to the GraphQL interception path, not a fixed DOM selector
`ingest/xfetch.py:135 parse_timeline_payload()` already reads
`legacy.conversation_id_str` and `legacy.in_reply_to_status_id_str` correctly and
**has never been used to populate this database** — all 3,348 bulk rows came from
the DOM scrapers. Fixing the DOM selector would recover ancestry only; the
GraphQL payload also carries the true author, so it fixes ancestry and the
authorship defect below at one stroke. New capture uses that path. The DOM
scrapers are frozen — kept for provenance, not extended.

### 2026-08-25 · `handle` does not prove authorship; a capture-side author check is required
`capture_x_devtools.py:72` writes `"handle": roster_handle` and
`extract_manas_deep.py:85` writes `"handle": handle` — both stamp the profile
being scraped onto every `article[data-testid="tweet"]` on the page. Neither file
contains any `screen_name` or `User-Name` check (grep: zero hits). Because both
crawl `/with_replies`, which interleaves other users' parent and reply tweets,
other people's posts are filed under the tracked trader.

Measured floor: **50 posts** (22 whose text begins with `@iManasArora` — X's
reply convention, which a self-post never produces — plus vocative "bhai/bhaiya"
matches under the same handle). All 50 sit under `iManasArora`. This is a floor,
not a ceiling: a misattributed post with neutral trading content and no vocative
marker is invisible to text search.

**Severity, measured rather than assumed:** of those 50, **47 classify as
`noise`, 2 as `education`, 1 as `trade_event`**; and of the 237 posts bearing
trade numbers, exactly **1** is provably foreign-authored. So the defect is real
and must be fixed at capture, but it is **not** currently corrupting win rates,
stop discipline or style profiles — followers' questions are not trade records.
It therefore does not block the derive layer. Two obligations follow: the
GraphQL capture path must record the true author, and any per-trader metric must
exclude posts whose text begins with the filed handle's own `@mention` until
authorship is provable.
