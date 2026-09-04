# SaaS-grade quality bar — unidesk (2026-09-03)

**Assessor:** Claude Opus 5, audit role. Companion to
`AUDIT_2026-09-02_RENDERED_ELEMENT_SWEEP.md` (correctness) and
`handoffs/HANDOFF_2026-09-02_CORRECTIONS_AND_THRUST_UI.md` (corrections).

**Scope, set by the owner:** this is a personal tool and stays one. The question
is **not** "can it be sold" — it is **"why isn't it as good as a product that
was?"** Everything below is a reliability and craft bar, not a launch checklist.

The correctness audit asked *"are the numbers right?"* — mostly yes. This asks
*"why does it need babysitting?"*

**Verdict: the engine is product-grade; everything around it is not.** The gap
is not the bug list. The tool cannot explain itself, cannot run itself, and
cannot catch its own regressions.

---

## 1 · The real test: how much of *you* does the tool require?

The owner's own words, earlier in this project: *"the pipeline is not smooth on
its own… I always need an LLM like you to patch things up."* That is the whole
problem, and it is measurable.

Take the MILKYMIST question — *"why is it in no setup?"*:

| Step | What happened |
|---|---|
| You ask | "Why isn't MILKYMIST in tonight's list?" |
| The tool answers | Cites the **price and turnover floors** — the two gates it clears by a mile (₹232 vs ₹30; ₹543 cr vs ₹2 cr) |
| The truth | 11 of 61 sessions of history; also circuit-locked at +10.00% that session |
| Could the tool tell you? | **No.** The per-symbol reason is computed at `scan.py:281` and thrown away |
| What it took | Grepping 400 raw bhavcopy files, reading `scan.py` to establish gate-vs-history order — ~15 minutes of forensics |

**A product-grade tool answers that in one click. This one required an engineer
and an afternoon.** That is the difference you are feeling, and it is not
cosmetic.

The same shape recurs everywhere: the desk knows things it does not say, says
things it has not checked, and cannot explain itself. **B2-8 (record why each
symbol was refused) and A-7 (answer honestly) are therefore not minor UI
items — they are the highest-leverage work in the handoff**, because every one
of them removes a future session of you asking an LLM to go find out.

---

## 2 · What is genuinely product-grade already

Stated plainly, because it is the asset and because a gap list alone misleads:

- **Point-in-time discipline.** Windows exclusive of the current bar; warm-up
  returns `None`, never 0.
- **Corporate-action handling** with a content-hashed table, an unconfirmed-CA
  quarantine, and a detector that correctly reports basis drift.
- **Honest nulls.** `entry: null` rather than a guessed price; `bo_bd_ratio`
  rendering `—` rather than 0. **Every breadth, funnel and participation figure
  recomputed in the audit matched to the decimal.**
- **Machine-checked invariants** (`checks/published_invariants.py`) — seven
  checks proven to fire on planted defects.
- **Named gaps** instead of silent fabrication, throughout the honesty footer.

Most shipped retail tools do not have this and cannot acquire it cheaply. The
failures are in what surrounds it — which is the good news, because surroundings
are the replaceable part.

---

## 3 · Where the bar is actually missed

Re-graded from the correctness audit's severities against "what would a well-run
product never ship?"

| Finding | Audit grade | Against the bar |
|---|---|---|
| Wrong answer to "why isn't X here" (S1-9) | S1 | **Worst item here.** A confident wrong answer is worse than "I don't know" — it sends you down a false path |
| `Hit rate 0% · Avg -1.00R` from right-censoring (S1-3) | S1 | You could act on this. It reads as "the system loses every trade" when the window structurally cannot contain a winner |
| Cumulative-R over a mixed-CA archive (S1-6) | S1 | A number you would size positions against, computed across three different adjustment bases |
| PRIME on a 0.3R setup; opposite verdict next screen (S1-4) | S1 | The tool disagreeing with itself about the same stock, same session |
| Prior calls frozen 103 days (S1-2) | S1 | Silently showing May data on a September desk |
| Momentum Burst silently dropped (S1-1) | S1 | Header says 88, feed shows 86, no error |
| Nightly never scheduled (B2-7) | S1 | The tool does not run unless you remember |
| Scheduled job failing silently | S2 | The one job that is scheduled fails nightly with `LastTaskResult 1` and nothing tells you |
| Handler-less search box / alerts bell (S3-2) | S3 | Controls that look live and do nothing — teaches you to distrust the UI |

---

## 4 · Engineering gaps behind those symptoms

Measured on `unidesk_terminal/src`, 53 TypeScript files:

| Gap | Measured | Why it matters *to you* |
|---|---|---|
| **CI** | **none — no `.github` directory** | Nothing runs pytest or `run_checks.py` on change. This is the single biggest cause of repeat findings |
| **Error boundaries** | **0 of 53 files** | One null blanks a screen. History already did this, on `.toFixed(null)` |
| **Frontend tests** | **0 test files, 0 Playwright specs** — despite `playwright` in devDependencies | Every UI regression is found by you, visually, later |
| **try/catch** | **1 of 53 files** | A single malformed field takes down a panel instead of degrading it |
| **Monitoring** | none | The failing nightly job is invisible. You find out by noticing stale data |
| **Data durability** | positions register + account size in **`localStorage` only** (5 files) | **Clear your browser cache and your trade register is gone.** No export, no backup |
| **Accessibility** | `aria-` in 14 of 53 files | Partial, never audited |
| **Bundle** | 7.3 MB single chunk (1.2 MB gzip), no code splitting | Slow cold load; will worsen with `framer-motion` |
| **Repo hygiene** | `node_modules` **committed** (`manas_os/terminal/node_modules/…`); 299 MiB pack; loose garbage objects in `.git` | Slow clones, noisy diffs, risk of losing work in a large uncommitted tree |
| **Secrets** | ✅ clean — none tracked; `.gitignore` covers `.env`, `.env.*`, `*.env` | No action needed |

Deliberately **not** listed as gaps, because they do not apply to a personal
tool: authentication, multi-tenancy, rate limiting, uptime targets, audit logs.

---

## 5 · Why audit #11 still finds new S1s

Full analysis in §S2-8 of the correctness audit. Short form, because it governs
the sequence below:

**Audits emit prose; only code prevents regression.** The guard that should have
caught the thrust wave's missing point-in-time coverage
(`test_truncation_invariance`) worked exactly as designed and was **wired to
nothing** — it fired three days late, when a human happened to run pytest.
Findings land as instances, never as classes: the `SESSION` fixture was deleted
months ago and the identical defect reappeared as prose at `Settings.tsx:65`.

**This is why CI comes before the bug list.** Fixing 20 findings without CI
produces finding #21.

---

## 6 · Sequence (deliberately not "fix the findings")

**Phase 1 — stop the regeneration.** CI running `pytest` + `run_checks.py` on
every change. React error boundaries so one null cannot blank a screen. One
smoke test per route. None of this is a feature; all of it stops findings from
recurring. *Cheapest phase, highest leverage — do it first.*

**Phase 2 — make the tool explain itself.** B2-8 (per-symbol refusal reasons)
and A-7 (honest veto answer). Every question the tool can answer itself is a
session you do not spend asking an LLM to go dig. Directly targets §1.

**Phase 3 — stop it contradicting itself.** Audit PART A: S1-1 through S1-6.
Screens disagreeing about the same symbol destroy your trust in the tool faster
than any missing feature.

**Phase 4 — fix the statistics you would act on.** S1-3 (censored hit rate) and
S1-6 (mixed-CA archive). These are numbers you would size against; wrong is
worse than absent.

**Phase 5 — make it run itself.** B2-7 (scheduling with *visible* failure),
plus durable storage for the positions register so a cache clear cannot erase
your record.

**Phase 6 — the dynamic workflow** (handoff PART E) and features.

Features last. **The reason this is on audit #11 is that this order has been
inverted every time.**

---

## 7 · What this assessment did NOT cover

- No security review. §4 comes from reading the repo, not from pentesting or a
  dependency-vulnerability scan.
- No load, latency or cost modelling.
- No accessibility audit beyond counting `aria-` occurrences.
- No assessment of the Desk broker-import panels against their source CSV, of
  Pro mode panel-by-panel, or of whether the 393 mixed-basis partitions actually
  change any published statistic.
- No effort sizing. Phases 1-2 are small; Phase 5 builds things that do not
  exist. Anyone quoting a date from this document is guessing.

---

## 8 · The honest summary

The expensive half is built. A correct, point-in-time, corporate-action-aware
research engine with machine-checked invariants is the part most people never
get right.

What is missing is the cheap-but-unskippable half: CI, error handling, the
ability to explain a refusal, scheduling that reports its own failure, and
durable storage for your own records. None of it is intellectually hard. All of
it has been deferred in favour of features — which is exactly why the same class
of defect keeps resurfacing wearing a new instance, and why the tool still needs
you (or an LLM) standing next to it to work.

**"As good as a SaaS" here means one thing: it runs, it explains itself, and it
catches its own regressions — without you in the loop.** Phases 1 and 2 are most
of that.
