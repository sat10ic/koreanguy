# TraderLog — backlog

Status: `[x]` done · `[~]` partial/in progress · `[ ]` pending

Keep this current **at every wave close**, not at session end. Manas OS's own
TASKS.md went 12 days stale while work tracked only in a session tool, which is
why that project now has an explicit standing order about it. Same rule here.

Rules for entries:
- Titles are stable; numbers are not. Cross-reference by title.
- `[~]` requires an explicit **DONE** / **STILL OPEN** split. Never mark `[x]`
  on anything with an open remainder.
- Every closed item carries evidence: a measured number, a file:line, or a
  command whose output proves it.
- Nothing disappears silently. Killed items move to DROPPED with a reason.

Controlling plan: `C:\Users\satta\.claude\plans\how-can-you-start-happy-sunrise.md`

---

# OUTSTANDING

## W1 — ingest (any model)

- [ ] **Playwright X fetcher** — `ingest/xfetch.py`. Persistent browser profile
      the user logs into by hand; no password touched by any script. Poll each
      active trader's timeline **including replies** (self-replies are where adds
      and exits live, and they do not fire bell notifications — this is why the
      email-notification route was rejected outright). Group by `conversation_id`.
      Interface is fixed by `CONTRACTS.md`: `fetch_timeline(handle, since) -> list[RawPost]`.
      Done-test: 3 traders, 7 days, `checks` ingest check green.

- [ ] **Immutable archive** — `ingest/archive.py`. Post JSON + every image written
      to `data/raw/` and `data/media/` **before** anything parses them, keyed by
      `post_id`, with a sha256 per media file. Nothing downstream may re-fetch:
      threads run for weeks and X's search window does not.

- [ ] **Deletion detection** — `ingest/deletions.py`. A post seen before and now
      gone gets `deleted_at` stamped; the row and its archive are **kept**.
      Traders delete losers, so dropping them silently would bias every derived
      style metric toward flattery.

## W2 — parse (needs a strong model)

- [ ] **Golden fixtures first** — build ~30 real posts with hand-verified expected
      JSON in `tests/golden/` BEFORE trusting any parser output. These also
      measure the real extraction yield, which is the project's biggest unknown.
- [ ] **Classifier** (`cheap` tier) — post → `trade_event | breadth | watch_idea | theme | education | noise`.
- [ ] **Vision pass** (`vision` tier) — annotated chart → levels + structure + any
      text in the image. Exits are frequently a chart plus the word "booked".
- [ ] **Thread reconciler** (`smart` tier) — the core. Whole thread → full position
      state, re-derived in full on every change, cached on `thread_hash`.
      Never incremental: LLM state-diffing drifts within days.

## W3 — cross-thread linking

- [ ] **Symbol linker** — standalone posts referencing a symbol with an open
      position ("booked XYZ +18%", no reply link to a 3-week-old entry). This is
      the accuracy ceiling of the whole tool. **Proposes** links only; anything
      under `reconcile.link_confidence_floor` (0.8) goes to `review_queue`.
- [ ] **Review queue wired to the UI** so a human can resolve in one click.

## W4 — breadth + XP/MBI

- [ ] Adopt `bhavcopy.py` + `breadth_counts.py` + `breadth_analytics.py` +
      `universe_breadth.py` into `adopted/`, with provenance headers.
      `universe_breadth.py` and `niftymidsml400_constituents.csv` are **required**,
      not optional: XP's weights were calibrated on the NIFTYMIDSML400 universe
      and feeding it a different advancer count silently produces wrong numbers.

- [ ] **Adopt the XP dial reverse-engineering** — `manas_os/regime/xp.py`, whole
      file (115 lines, imports `math` + config only). Reproduces the finallynitin
      XP recursion. Writes `regime_daily.xp_value` / `xp_z_state`.
      **It is a recursion on the prior day**, so: seed from config on first run,
      backfill strictly in date order, and treat a gap in `breadth_daily` as a
      chain break rather than something to interpolate over.
      Done-test: recompute a known date twice, get the identical value; a
      deliberately introduced date gap raises rather than silently seeding.

- [ ] **Adopt the MBI score reverse-engineering** — `manas_os/regime/snapshot.py`
      lines 53-162 ONLY: `ratio_from_pct_above`, `burst_ratio`, `band_ratio`,
      `band_r50`, `xp_band`, `band_r4p5`, `compute_mbi`. All pure, stdlib only.
      Stocksgeeks MBI: r10/r20/r50/r4p5 → bands → day color → warning day.
      Source notes: `manas_os/design/knowledge/SG_MBI_DIGEST.md`.
      **Do NOT take the rest of that file** — `compute_pillars`, `market_mode`,
      `compute_quadrant`, `four_phase`, `choppy_brake`, `run()` are the governor
      layer that gates the user's own trades. Out of scope by decision.

- [ ] Wire the BREADTH screen: computed metrics + XP + MBI day color beside
      trader commentary, with agreement scored over time (trader says "risk-on"
      on a day XP read LOW and MBI read RED → that is a scoreable miss).

## W5 — volume reverse-engineering

- [ ] Adopt `alpha/activity.py` (Reactor Scale) + `alpha/schema.py` +
      `engine/universe_filter.py`.
      **`Assumption:` this is what "the volume based reverse engineer" refers to.**
      It is the only manas_os module that is both purely volume/delivery-derived
      and explicitly a reverse-engineering exercise. If wrong, the alternates are
      `up_day_persistence` / `ema10_respect` / `base_symmetry` in
      `manas_os/scanner/discovery_metrics.py:249-473`. Confirm before starting.

## W6 — derived intelligence

- [ ] **Trader style profiles** — hold-time distribution, stated-exit win rate,
      average R, sector tilt, entry-type mix, and stop discipline (stated vs honored).
- [ ] **Practice-vs-preach** — link `edu_items` to `position_events` by topic,
      score adherence.

## W7 — Telegram

- [ ] Adopt the transactional outbox; digests + high-confidence event pushes.
      Starts in `dry_run`, same as Manas OS.

## W8 — local LLM

- [ ] Ollama backend behind `provider.py`. Done-test: golden fixtures still green
      on the local model. `llm_runs` shows the cost delta.

## W9 — attention engine + heatmap

Spec: `design/ATTENTION_ENGINE.md`. Depends on W2, W4, W5, W6 — every input is
missing until those land. Do not start early.

- [ ] **`derive/attention.py`** → `symbol_attention`. Weighted event sum where an
      entry WITH a stated stop counts ~6x a bare mention. Talk and money must
      never be summed into one count.
- [ ] **The freshness decay is the point, not a detail.** Score must fall with
      sessions since first mention (1.00 at 0-2d → 0.10 at 16d+). Eight traders
      over three weeks must rank BELOW three traders inside two sessions. A
      version where attention monotonically increases the score is a machine for
      buying crowded tops — reject it in review.
- [ ] Herding discount: echo posts inside a 24h window carrying no new level and
      no entry count 0.6, not 1.0. Six mentions can be one idea and five echoes.
- [ ] `regime_mult` from `regime_daily` — bad breadth DAMPENS (0.35 on a RED
      warning day), never zeroes. A leader emerging in a bad tape is information.
- [ ] `activity_mult` from `alpha_activity_signals` — the only input not derived
      from what people said, and the highest-value term in the formula.
- [ ] Negative signals surfaced as an explicit `caution` flag, not netted away:
      cluster exits, deleted entry posts, stop violations.
- [ ] HEATMAP screen: treemap + ranked table + per-row "why" drill-down showing
      every multiplier. Plain SVG; adopt the `squarifyTreemap` idiom from
      `manas_os/desk/src/viz.js`.

## W10 — does the signal actually work?

- [ ] **`derive/attention_validate.py`** — forward return at +5/+10/+20 sessions
      vs NIFTYMIDSML400 median, bucketed by score decile, over every historical
      cluster.
- [ ] **Ship criterion: top decile beats universe median at +10d across ≥60
      clusters.** Until it passes, the HEATMAP ranks by raw attention and states
      on screen that priority is unproven. An unvalidated prioritisation number
      is worse than none, because it will be trusted.
- [ ] "Is this signal real?" panel showing the current validation result,
      including when it fails.

---

# COMPLETED

- [x] **W0 — the frame + UI shell** (2026-08-23). Governance docs
      (`CANONICAL.md`, `AGENTS.md`, `HANDOFF.md`, `DECISIONS.md`, `CONTRACTS.md`,
      `WIREFRAMES.md`), `db/schema.sql` + `db/__init__.py` with the prod-DB test
      guard, `llm/provider.py` with tier routing and the `llm_runs` cost ledger,
      the `checks/` harness writing `STATE.json`, mock seed data, and the six-screen
      UI rendering end-to-end against a real SQLite DB.
      Evidence: see `HANDOFF.md` for the verification output.

---

# DROPPED / DEFERRED BY DECISION

Recorded so nothing disappears silently. Reverse any of these by saying so.

- **X email/bell notifications as the ingest trigger** — dropped 2026-08-22.
  A trader's replies to their own posts do not fire bell notifications, and adds,
  stop moves and exits are almost always self-replies. The notification stream
  structurally cannot see the most important events. Replaced by timeline-with-
  replies polling.
- **Incremental LLM state updates** — dropped at design time. Full thread
  re-derivation on every change is idempotent and cheap; incremental diffing
  drifts and cannot be tested against fixtures.
- **Inbound Telegram bot** (resolving review items by replying to a message) —
  deferred. Needs a webhook receiver that exists in neither project. Review
  resolution happens in the UI for now; the Telegram nudge links into it.
- **Official X API** — deferred, not rejected. The fetcher sits behind one
  interface so switching is a one-file change if the browser route breaks or the
  account gets suspended.

---

# USER-SIDE ONLY

- [ ] Log into X by hand, once, in the Playwright profile directory
      (`ingest.browser_profile_dir`). No agent can or should do this.
- [ ] Decide whether the fetcher points at the main handle or a secondary one.
      Recommend secondary — this route risks suspension.
- [ ] Confirm the W5 assumption about which module is "the volume reverse engineer".
- [ ] Provide the initial trader roster (X handles to track).
- [ ] Telegram bot token + chat id, when W7 is reached.
