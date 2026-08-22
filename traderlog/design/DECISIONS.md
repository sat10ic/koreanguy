# DECISIONS — locked calls, dated

Manas OS scattered its locked decisions across a dozen single-topic files with no
index, so nobody can answer "what has already been decided?" without reading all
of them. This file is that index. One dated entry per irreversible or
expensive-to-reverse call.

Append, never rewrite. If a decision is reversed, add a new dated entry that says
so and leave the original in place — the reasoning that was wrong is worth as much
as the reasoning that was right.

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

### 2026-08-23 · TraderLog never sizes, routes, or advises
It records what other people publicly said they did. It does not tell the user
what to trade. Inherited from the Manas OS manual-execution-only lock, and it is
also what keeps the tool outside SEBI's algo framework. Any wave that blurs this
line is out of scope.
