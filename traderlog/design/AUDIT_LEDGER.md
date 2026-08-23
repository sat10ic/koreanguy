# AUDIT LEDGER

**Append dated addenda. Never re-run a whole audit.**

The convention, inherited from `manas_os/design/AUDIT_LEDGER_2026-07-17.md`:

- Findings are coded and keep their code forever: `C<n>` critical, `I<n>`
  important, `G<n>` verified-good (recorded so nobody re-checks it).
- Each finding: one-line repro, then `Fix:`.
- A later pass **appends** an `## ADDENDA (<date>, <source>)` section rather than
  regenerating the file. Re-auditing what a prior pass already certified is waste;
  re-audit only the delta.
- Findings that need work graduate into `TASKS.md` by title. The ledger records
  what was found; TASKS.md tracks what is being done about it.

Sections in order: `## CRITICAL` · `## IMPORTANT` · `## GOOD (verified, keep)` ·
`## Unverified this pass` · then dated `## ADDENDA` blocks.

---

## W0 pass — 2026-08-23 (Claude Opus 5, self-audit at wave close)

### CRITICAL
_None._

### IMPORTANT
- **I1** `checks` reports `not_built_yet` for ingest/parse/derive/telegram rather
  than failing. Correct for W0, but it means a green `checks` run does **not**
  yet mean the tool works end to end. Each wave must flip its own check from
  `not_built_yet` to a real assertion as part of that wave's done-test, or the
  harness quietly becomes decorative.
  Fix: W1–W7 each own their check. Tracked in TASKS.md per wave.

### GOOD (verified, keep)
- **G1** DB path guard works: `traderlog.db.connect()` refuses to open the
  production DB under `PYTEST_CURRENT_TEST` without an explicit path. Adopted
  from Manas OS, where the absence of this guard once polluted the live 717 MB
  database with synthetic fixture rows.
- **G2** No `import manas_os` anywhere in `traderlog/`. The one-way door holds.
- **G3** No model id appears at any call site; all routing goes through
  `llm/provider.py` tiers.

### ADDENDA (2026-08-23, handoff-readiness audit)
- **I2** CONTRACTS.md drifted from the schema within the same session: the
  classifier gained `play_type` / `conviction_words` and two attention tables
  were added, but §1 still showed the old JSON. A model reading CONTRACTS.md as
  the authority would have written a classifier missing two fields.
  **Fixed same pass.** Root cause is that the schema and its contract doc are two
  files with no mechanical link. Cheap guard for a later wave: a test asserting
  every column in `post_class` appears somewhere in CONTRACTS.md.
- **I3** `STATE.json.last_verified_commit` read `28ce22ed` — a commit that
  predates the entire project — because nothing had been committed. The field is
  honest about what git says but misleading about what was verified. It resolves
  itself on the first commit of this work; noted so nobody trusts that value
  before then.

### ADDENDA (2026-08-23, W1 review + design wave)
- **G4** W1's completion claim verified independently rather than accepted.
  `fetch_timeline(handle, since) -> list[RawPost]` matches CONTRACTS.md §7 exactly,
  and self-reply ancestry is real in SQLite: 8 of 12 captured posts are replies
  with correct `conversation_id` grouping across four threads. The VCPSwing
  `#FCL` chain is a genuine reconstructable position. The report was honest about
  its own unverified edges, which is the behaviour we want.
- **I4** `/api/feed` dropped `conversation_id` and `in_reply_to`, so self-reply
  threads could not render — defeating the reason ingest polls `/with_replies`
  at all. W1 flagged it as a cross-wave gap rather than hiding it.
  **Fixed this pass**: fields are additive, `posts` stays a flat list, the UI
  groups. Two follow-on bugs found and fixed while verifying: LIMIT cut threads
  mid-chain leaving replies whose root was absent (an exit with no visible
  entry), and the first sort reversed within-thread so the exit rendered above
  the entry. Threads now order newest-activity-first with posts oldest-first
  inside each.
- **I5** The W0 UI was tables with bars beside them — correctly judged bland.
  Root cause: no binding appearance spec existed, only a one-line "editorial
  poster" aesthetic note, so each screen was built to whatever the builder
  imagined. `design/VISUAL_LANGUAGE.md` now sits above `WIREFRAMES.md` with an
  explicit banned list, a chart vocabulary, and a component contract.

### ADDENDA (2026-08-23, W2 review)
- **C2 — CRITICAL, fixed this pass.** `check_golden` never verified prompt
  versions. Fixtures were compared only against their own stored expectations,
  so a model could edit any prompt and every fixture would still pass **while
  testing against a prompt that no longer existed**. The anti-drift mechanism —
  described in the project's own docs as the single most important test, and the
  thing standing between this tool and silent extraction decay — did not detect
  drift. Fixtures record the prompt hashes they were verified against; the check
  now compares them to `prompts.all_versions()` and reports `stale_prompts_<n>`,
  a status distinct from both pass and fail because a stale fixture is a
  human-re-verification task, not a code failure. Regression test added.
- **I6** `vision.md` rule 5 discards broker order confirmations, holdings tables
  and watchlists as `unreadable` — 3 of 9 real archived images, including a fill
  price of 39.05. Filed as W2b rather than fixed mid-wave: the prompt edit and
  the fixture re-verification must land together. The W2 agent found this,
  refused to invent a broader reading to rescue the number, and recorded the loss
  in the fixture's `unresolved`. That is the correct behaviour.
- **G5** W2 delivered 3 reconcile fixtures from 4 real threads and said so
  plainly rather than padding toward the aspirational 30, and lowered
  `_GOLDEN_FIXTURE_TARGET` with a comment forbidding raising it without more
  real posts behind it. Verified independently: every `evidence` value in all
  three fixtures resolves to a post present in that fixture's own thread, and the
  `unresolved` lists correctly refuse to infer an entry price, convert "2% risk"
  into an absolute stop, or treat "10% up from Entry" on an open position as a
  final result.
- **G6** W2 made **zero** LLM calls and hand-verified every fixture from the
  archived post text and images, honouring the budget constraint.

### ADDENDA (2026-08-23, UI audit + brutalist overhaul)
- **C3 — CRITICAL, fixed.** LEDGER printed "mock rows have no file on disk"
  unconditionally over **real** archived images that served fine (verified: both
  return 200 image/jpeg). It told the user their own captured evidence did not
  exist, on rows whose `is_mock` was 0. The backend endpoint was already correct
  and honest; the frontend simply never called it and rendered a hardcoded
  placeholder. Now a real `<img>`; the "no file" line is an `onError` fallback
  only. Verified live: 2 images load, 1709×80 and 675×680.
- **C4 — CRITICAL, fixed.** `{p.holding_days}d` had no null guard, rendering a
  bare `"d"` for a position with no stated hold time — reads as a broken render
  where every other null in the app correctly shows an em dash.
- **C5 — CRITICAL, fixed.** `Num` defaulted to 0 decimals, rendering the
  VCPSwing broker fill price `39.05` as `39`. Silently destroying a stated price
  is the same class of error as fabricating one. Precision is now adaptive and
  the rule is recorded in `VISUAL_LANGUAGE.md` §1 as correctness, not styling.
- **I7 — fixed.** Screen files still referenced tokens deleted in the overhaul
  (`--line`, `--teal`, `--panel-3`, `--state-green`, …). Those resolve to
  nothing, so the BREADTH chart marks would have rendered invisible. Remapped.
  Root cause worth remembering: a token-layer rewrite must grep **screen** files
  too, not just stylesheets — inline SVG `fill="var(--x)"` is easy to miss.
- **I8** Audit found 12 further spec/UX defects still open: missing confidence
  filters (FEED, LEDGER), category chips coloured with state tokens, TRADERS
  missing its small-multiples frame and sortable headers, TRADERS collapsing four
  charts into one `<p>` instead of four labelled empty frames, BREADTH
  reinventing `BandLine`/`Ribbon` locally instead of importing the house
  components, mobile horizontal overflow from the 7-tab nav, and `Bar` carrying
  no `role`/`aria-label`. Filed, not yet fixed.
- **G7** The prompt-drift detector (C2, added earlier the same day) fired
  correctly on its first real test: W2b's `vision.md` rewrite immediately flagged
  all three reconcile fixtures as `stale_prompts_3`. The mechanism works on a
  genuine prompt edit, not just on a synthetic one.
- **G8** Near-miss caught pre-commit: `git add traderlog` staged
  `data/browser_profile_competing/.../Network/Cookies` — live X session cookies —
  because the ignore pattern named an exact directory and a later session created
  a suffixed variant. Never committed, absent from history. Same bug class hid
  three database backups. Both patterns are now globs.

### Unverified this pass
- Extraction yield on real posts. Unknown until W2's golden fixtures exist, and
  it is the project's largest open risk — if Indian traders' posts are too vague
  to yield stops and targets, this becomes a commentary archive rather than a
  trade log. Measure it before building anything on top of the reconciler.
- Whether Playwright can reliably parse X's current markup, and whether
  timeline-with-replies is reachable from a logged-in profile without triggering
  rate limiting. W1 proves or kills this. Nothing before W1 depends on it.
