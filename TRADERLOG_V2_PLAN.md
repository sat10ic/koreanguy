# TraderLog v2 — a market-intelligence engine, designed from the data up

## Context

The v1 build is being retired. The owner's verdict — *"it was supposed to be a
brain and an engine, but it's a useless, untidy mess"* — is correct, and the
audit explains why in one sentence: **v1 was architected as an archive and the
product needed an engine.**

Every symptom traces to that mismatch:

- The production pipeline processes **oldest-first** (`run_recon.py:193,203`),
  so today's posts sit behind a 2024 backlog. The team found this bug on the
  last day of work, fixed it in a side tool (`tools/classify_backlog.py:47`),
  and never propagated it to the orchestrator.
- A trade needs **three sequential LLM passes** before anything renders, at
  2.5s pacing on free models with 90s–15min rate-limit cooldowns.
- Nothing is scheduled. There is no production invocation of any stage.
- Every UI element is `&&`-guarded on data that never arrives, so missing data
  renders as *nothing* rather than as an alarm.
- The one screen written once and never re-skinned (Radar) is the only one the
  owner finds useful. The UI was reskinned four times; the derivations behind it
  stayed empty.

And trust in the artifact is gone: the Ledger's scale lenses and R-multiple
analytics are recorded as shipped and "browser-verified" in six documents, with
owner approval cited — while `Ledger.jsx` was never modified and its stylesheet
is imported by nothing.

**Decision (owner, this session): salvage the corpus only.** The captured data is
kept as an asset. All pipeline and UI code is discarded, and the product is
redesigned from the data up.

Two decisions are explicitly **parked** for later and are not assumed here: how
posts get captured going forward, and what the LLM budget is. This plan is
written so that neither blocks the design.

---

## ⚠ Urgent, before any other work

**`derive/reconcile_all.py` must be deleted or quarantined now.** It is
committed at HEAD with **zero callers**, is mentioned in no document, and is not
chained by `run_recon.py` — so nothing warns anyone off running it.

It opens by wiping the sole writer's output:

```python
# derive/reconcile_all.py:376-377
conn.execute("DELETE FROM position_events WHERE is_mock = 0")
conn.execute("DELETE FROM positions WHERE is_mock = 0")
```

That destroys every LLM-reconciled position and all **71 hand-audited** rows.
The damage is **permanent**: `llm/link.py:268` excludes any post that has a
`review_queue` row in any status, so accepted links survive the wipe as queue
rows whose `position_events` are gone and can never be re-proposed. Position IDs
are content-hashed, so surviving `review_queue.position_id` values dangle.

What it would write instead is worse than nothing. Its exit detection matches
bare, unanchored substrings `out` and `some` (`:105,:117`) — verified by
executing it against the real corpus:

```
_is_exit_post("Breakout above 1240 on volume")    → full exit, 100%
_is_exit_post("outperformer of the day")          → full exit, 100%
_is_exit_post("Standout strength in PSU")         → full exit, 100%
_is_exit_post("3200 Added some more #DATAPATTNS") → partial exit, 50%   (it is an ADD)
```

**53% of its "full exits" fire on the token `out`; 61% of its "partials" on
`some`.** 169 of 397 trade events (42.6%) get flagged as exits. Its price
regexes are equally unsound — `"Bought #AVANTEL at 174 SL 2% at 171"` yields no
entry and a **₹2.00 stop**, and any `@mention` followed by a number is read as an
entry price, so a follower's *"sir what about 1240 levels"* becomes a full exit
at ₹1,240.

Fabricated closes are precisely what `CANONICAL.md` and the reconciler contract
exist to prevent.

---

## 1. The only asset: what the corpus actually contains

| Asset | Volume | Why it matters |
|---|---|---|
| Posts + replies, threaded | 3,395 across 17 handles (4 active) | The raw claims |
| **Vision-transcribed chart images** | **1,274 media, 600+ annotated price levels** | **The crown jewel — prices traders literally drew on charts. Nobody else has this.** |
| Classified trade events | 302, with symbols / play type / conviction words | The commitments |
| Reconstructed positions | 305 | Entry/stop/add/exit skeletons |
| Teaching posts | 549 | The "preach" half of practice-vs-preach |
| Market-opinion posts | 284 | Gradeable market reads |
| **Daily OHLCV (bhavcopy)** | **1.3M rows** | **The grader. Massively underused in v1.** |
| Breadth + XP/MBI regime | 431 sessions | Context at the time of every claim |

Four properties of this data must drive the design rather than be fought. All
four are measured, not assumed.

**(a) Traders announce entries loudly and exits quietly — and usually without
naming the ticker.** Measured on the corpus: **33 of 64 exit posts (51.6%) carry
no symbol at all**; @iManasArora owns 22 of them — *"Closed"*, *"Fully closed at
955"*, *"Out at BE"*. Five separate filters in v1 dropped these
(`classify.py:108`, `run_recon.py:201`, `link.py:129,286`,
`reconcile_all.py:370`), one of them **silently, without even queueing a
review**. This is the single strongest argument for the design in §5:
**v2 must never depend on a trader announcing an outcome.**

**(b) The corpus has no thread structure, and it is unrecoverable.**
**3,348 of 3,360 posts lack `conversation_id` and `in_reply_to` entirely** —
absent, not null (`design/DECISIONS.md:299-305`). Every one of v1's 305
positions was reconciled from a "thread" of exactly one post, which is why
nothing ever closes: one post cannot contain both an entry and an exit.
Re-scraping a year of history to recover ancestry was considered and rejected.
**Consequence for v2: claims must be extracted from isolated posts, and linked
by `(trader, symbol, time-proximity)` — never by thread.**

**(c) A large minority of claims are images, not text.** **353 posts have empty
text**, and 1,274 media rows carry vision transcriptions with structure notes
and 600+ annotated levels. v1's classifier sent **text only**
(`llm/classify.py:239`) and never saw them, so a chart-only entry or close was
classified from an empty string, landed as `noise`, and was filtered out before
anything downstream could see it. **v2's claim extractor must take text and
vision together as one input.**

**(d) The corpus is mostly noise, and partly misattributed.** Audit finding I8:
the visible feed is "almost entirely cricket… correctly classified `noise` at
0.99." Worse, the DOM scrapers stamped the profile handle onto every tweet on a
`/with_replies` page, so **≥50 posts by other people are filed under
`iManasArora`** — follower questions counted as his claims. Signal density is
low and authorship needs verifying: rank hard, and prove the author.

---

## 2. Product thesis

> **X is already the feed. Do not build another one.**
>
> What a human scrolling X cannot do is **remember, aggregate, and grade.**
> That is the entire product.

Three things this tool does that no amount of scrolling can:

| | A human can't | The engine can |
|---|---|---|
| **Remember** | recall that this trader posted MAZDOCK 3 weeks ago at ₹2,100 with a stop at ₹1,980 | replay every claim against what the tape did next |
| **Aggregate** | notice 6 independent traders entered defence names within 3 days | cluster first-mentions in time and flag the convergence while it is still early |
| **Grade** | know whose entries actually work | score every trader on forward tape returns, with `n` shown |

So v2 is a **memory and a scoreboard**, not a reader.

---

## 3. The unit of the product is the CLAIM, not the post

v1's unit was the post, which is why its screens are lists. v2's unit is the
claim — and a claim is defined by being **resolvable**.

```
CLAIM  =  author + timestamp + subject + commitment + resolution
                                  │          │             │
        symbol / market / principle          │             │
                        entry+stop, add, watch+trigger,    │
                        opinion, teaching                  │
                                    what the tape did next
```

Every claim carries its source post (evidence) and its price series
(measurement). That is what "evidence-backed" means operationally: **nothing on
screen exists without a post to click and a chart to check it against.**

This is the v1 idea worth keeping — *"results are what the trader said, never
computed"* — extended with the half v1 never built: **the tape says what
happened, independently of what the trader claimed.**

---

## 4. The engine: attention that doesn't buy crowded tops

The best idea in the v1 documents was specified and never built
(`design/ATTENTION_ENGINE.md`, status: *"specified, not built"*). It is the core
of v2, because it encodes the one insight that makes this product non-obvious:

> **Attention is a lagging indicator.** By the time eight traders post about a
> name, it is frequently day 6 of the move. A score that rises with attention is
> a machine for buying crowded tops.

So the engine does **not** rank by how many people are talking. It ranks by
**conviction, discounted for lateness and for echo.**

**Conviction weight — talk and money are never summed:**

| Event | Weight | Why |
|---|---|---|
| Entry **with stated stop** | 6.0 | the only event where the author showed their risk |
| Add to existing position | 4.5 | doubling down is a real commitment |
| Entry, no stop | 4.0 | |
| Watchlist **with trigger price** | 2.0 | falsifiable |
| Vague positive | 1.0 | |
| Bare mention | 0.5 | |
| Exit | 0.0 | and feeds the caution flags below |

**Modifiers:** freshness decay (1.00 at 0–2 sessions since first mention → 0.10
at 16+) · independence discount (×0.6 for echoes inside 24h) · regime damping
(from XP/MBI, already computed for 431 sessions).

**The headline is the PHASE, not the number.** This is what makes it
actionable:

| Phase | Condition | What it means |
|---|---|---|
| **EARLY** | ≤3 sessions since first mention · ≥2 independent traders · ≥1 stated stop | the only genuinely actionable state |
| **BUILDING** | 4–8 sessions, attention still rising | confirmed but no longer cheap |
| **CROWDED** | ≥6 traders or >8 sessions since first mention | **a caution, not a buy** |
| **FADING** | cluster exits appearing, or attention declining | |

**Caution flags are never netted into the score** — they surface separately:
cluster exits (2+ traders out within 3 days) · deleted entry posts · **stop
violations** (price broke a stated stop and no exit was ever posted — the single
most revealing thing in the corpus).

Every score expands to its component multipliers. No black box.

---

## 5. Three surfaces, and one push

v1 had seven screens and no point of view. v2 has three, each answering one
question, plus a daily brief.

### SIGNAL — *"what deserves attention right now, and is it early?"*

The landing screen. A ranked board of symbols by conviction-weighted attention,
each row leading with its **phase chip** (EARLY / BUILDING / CROWDED / FADING),
the independent-trader count, sessions since first mention, and any caution
flags.

The signature graphic is a **conviction × freshness scatter** — early and
high-conviction is the top-left quadrant, and it is the only quadrant that
matters. Crowded names are visibly stranded to the right. One glance answers
"is there anything worth my time today?"

### SYMBOL — *"everything known about this name"*

Reachable for **any** symbol by search. (v1's fatal limitation: its dossier was
reachable only by clicking one of the ~2 symbols that cleared a co-attention
threshold, leaving ~83 multi-trader symbols invisible.)

- Price chart with **every trader action marked on the date it was said** —
  entries, adds, stop moves, exits
- **The Level Book** — every price any trader publicly marked, who marked it,
  when, and from which chart image. Conflicting levels coexist; they are
  evidence, not a merged target. *This is the feature no competitor can copy,
  because the 600+ levels came out of chart screenshots.*
- Who is in, out, and watching — at what stated prices
- What the tape did after each mention, against the NIFTYMIDSML400 median
- Regime context (XP/MBI) at the time of each entry

### TRADER — *"is this person any good, and at what?"*

The scoreboard, designed around the closes problem by **grading on the tape
instead of on their claims**:

- **Tape score** — median excess forward return at 5/10/20 sessions after their
  entries, vs the NIFTYMIDSML400 median. **Computable today for all 302 trade
  events. Requires no closes at all.**
- Hit rate on the tape — % of entries positive at 10 sessions
- **Stop discipline** — % of entries carrying a stated stop, and % where price
  broke the stated stop with no exit ever posted
- **Timing fingerprint** — median sessions between the move starting and their
  post. Are they early, or are they the crowd?
- **Specialisation** — which sectors, setups, and regimes their tape score
  actually holds up in
- Practice vs preach — teaching posts next to whether their own logged trades
  followed the rule

Every rate shows its `n`, and is withheld below a minimum rather than shown thin.

### THE BRIEF — the daily push

Not a screen. A short, ranked, opinionated digest — new EARLY names, phase
transitions, cluster exits, stop violations, notable closes — pushed to Telegram.
This is the "brain" the owner is missing: the tool saying something, unprompted,
once a day.

### What is cut

**Feed** (X does it better), **Library** and **Style** as standalone screens
(fold into TRADER), **Breadth** as a screen (becomes a context ribbon on
SIGNAL and SYMBOL, where it actually changes a decision).

---

## 6. Architecture principles

These exist to prevent the specific failures that killed v1.

1. **Newest-first, everywhere.** Currency beats completeness. Backlog is
   processed only with spare capacity, never ahead of today.
2. **Two-speed pipeline.** A deterministic fast path (ticker + verb + price
   regex) produces a **provisional** claim in seconds; LLM passes upgrade and
   correct it in the background. v1 showed nothing until it was certain — v2
   shows something immediately and marks it provisional.
3. **The tape is the grader.** No product metric may depend on a trader
   announcing an outcome.
4. **Text and image are one input.** A claim extractor that reads only text is
   blind to 353 posts and to 1,274 transcribed charts. Vision goes in at
   extraction, not as a later enrichment.
5. **A dropped record is a logged record.** v1 silently discarded symbol-less
   closes — the schema already defines an `ambiguous_symbol` review kind that
   nothing ever wrote. Anything the pipeline cannot resolve must land somewhere
   visible and countable, never on the floor.
6. **Degrade loudly, never hide.** Every empty state names the cause and the
   staleness ("no NSE price history for this symbol", "ingest last ran 6 days
   ago"). A silent `&&` guard is a bug.
7. **No score without visible components.**
8. **Error boundaries around every chart and panel.** One dead panel must never
   take down a page — v1 had zero error boundaries.
9. **Pin chart library versions and test the render.** v1's chart was written
   against v4 and shipped on v5.
10. **A feature is done when a test drives the rendered UI.** v1's browser tests
   `pytest.skip` when `ui/dist` is absent — which it always is — so four
   contract mismatches shipped green.
11. **One writer per metric**, and docs updated in the same commit as the code.
   The `[x]`-with-no-code failure is what destroyed confidence in v1.

---

## 7. Build order

Each phase ends with something the owner can look at and judge.

**Phase 0 — Corpus rescue.** Export posts, media + vision JSON, classifications,
positions, edu items, breadth notes and OHLCV from the v1 database into a clean,
documented schema keyed on the CLAIM. Nothing else is carried over. *Ends with:
a row count and a schema the owner can read.*

Phase 0 has three prerequisites, in order:

1. **Quarantine `derive/reconcile_all.py` before anything else** — see the
   Urgent block below. It must not run against the production database.
2. **Establish which reconciler produced the current 305 positions**, because
   it decides whether they are salvageable:
   ```sql
   SELECT reconcile_model, status, COUNT(*) FROM positions GROUP BY 1,2;
   SELECT MAX(ts_ist), MAX(fetched_at) FROM posts WHERE is_mock=0;
   SELECT handle, COUNT(*), MAX(ts_ist) FROM posts GROUP BY handle ORDER BY 3 DESC;
   ```
   If `reconcile_model` names an LLM, the positions are genuine and closes are
   simply absent. If it reads `deterministic-lifeline-reconciler (2026-08-26)`,
   the landmine already fired: the hand-audited rows are gone and roughly half
   the `closed` rows are regex artifacts that must not be trusted.
3. **Verify authorship** on import, dropping the ≥50 posts misattributed to
   `iManasArora` by the scraper.

**Phase 1 — The grader.** Join every one of the 302 trade events to the 1.3M-row
price history and compute forward excess returns at 5/10/20 sessions. *Ends
with: the first real trader scoreboard — who is actually any good — from data
already in hand, with no new capture and no LLM calls.*

**Phase 2 — SYMBOL.** Search, chart with action markers, and the Level Book.
*Ends with: the stock-level analytics and working charts that were asked for.*

**Phase 3 — The attention engine + SIGNAL.** Conviction weights, freshness decay,
independence discount, regime damping, phase classification, caution flags.
*Ends with: a ranked board with a point of view.*

**Phase 4 — TRADER, complete.** Stop discipline, timing fingerprint,
specialisation, practice-vs-preach.

**Phase 5 — THE BRIEF.** Daily digest to Telegram.

**Phase 6 — Live intake.** Deliberately last, and gated on the parked decision
below. Everything above is buildable and judgeable on the existing corpus.

---

## 8. Verification

- **Phase 1 is the honesty test.** If the tape scores say the roster's entries
  have no edge, the tool must say so. A scoreboard that flatters is worthless.
- **The engine's ship criterion** (inherited from `ATTENTION_ENGINE.md`, and
  correct): backtest the score against forward returns by decile. **If the top
  decile does not beat the median, the score does not ship.** A ranked list that
  isn't predictive is worse than no list.
- Every rendered screen is covered by a browser test that **fails, not skips,**
  when the UI is not built.
- Every number on screen traces to a post and a price series in one click.

---

## 9. Parked decisions (do not assume)

- **Intake** — hand-launched Chrome vs official X API vs hybrid. Determines
  whether "current" means minutes or days. Phases 0–5 do not depend on it.
- **LLM budget** — free tier vs small paid vs local. Determines fast-path
  latency and the classification null rate. The deterministic fast path in
  principle #2 keeps the product usable at any budget.
