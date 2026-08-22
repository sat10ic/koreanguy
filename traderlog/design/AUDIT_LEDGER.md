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

### Unverified this pass
- Extraction yield on real posts. Unknown until W2's golden fixtures exist, and
  it is the project's largest open risk — if Indian traders' posts are too vague
  to yield stops and targets, this becomes a commentary archive rather than a
  trade log. Measure it before building anything on top of the reconciler.
- Whether Playwright can reliably parse X's current markup, and whether
  timeline-with-replies is reachable from a logged-in profile without triggering
  rate limiting. W1 proves or kills this. Nothing before W1 depends on it.
