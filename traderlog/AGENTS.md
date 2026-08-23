# TraderLog — read this first

You are working on TraderLog. Read these five files, in this order, before you
plan or edit anything. It takes two minutes and it is the whole reason this
project survives being built by a different model every session.

1. `traderlog/CANONICAL.md` — what is real in this repo, and which similarly-named things are dead
2. `traderlog/STATE.json` — generated health + counts. Tells you if the tool currently works
3. `traderlog/HANDOFF.md` — what the last session did and where you pick up
4. `traderlog/TASKS.md` — the backlog
5. `traderlog/design/CONTRACTS.md` — the data and JSON contracts you must not break

Then, if you were given a wave: `traderlog/design/handoffs/HANDOFF_<WAVE>_*.md`.

Before designing, rebuilding, or reviewing any screen, also read these in order:

1. `traderlog/design/VISUAL_LANGUAGE.md` — binding appearance and chart vocabulary
2. `traderlog/design/WIREFRAMES.md` — binding screen content and layout

`VISUAL_LANGUAGE.md` sits above `WIREFRAMES.md`: satisfying a wireframe while
violating the visual language is a defect.

---

## The rules that matter

**Ask at user-decision gates; never guess them.** Repo facts come from the
read-first chain, but choices that belong to the user must be asked in the wave
where they become necessary. This includes source accounts, authentication or
cookie access, extraction method, trader roster, initial backfill, and market or
coverage boundaries. Record the answer in `HANDOFF.md` before acting on it.
Research or propose options when useful, but never activate a source or trader
until the user approves the exact choice. Approval for one tool's X profile does
not imply approval for another tool to read cookies or credentials.

**Run the checks before and after.**

```bash
python -m traderlog.checks
```

Before, so you know what was already broken and do not get blamed for it. After,
so you know you did not break anything. Non-zero exit means something is wrong.
It rewrites `STATE.json` for the next model.

**Never edit a prompt without running the golden fixtures.** `traderlog/tests/golden/`
holds real posts with hand-verified expected output. A model "improving" a prompt
and silently degrading extraction is the single most likely way this project dies,
and the fixtures are the only thing that catches it.

```bash
pytest traderlog/tests -q
```

**Every extracted field must cite the post it came from.** `evidence_json` maps
field → `post_id`. A field with no citation is dropped, not stored. If a trader
never stated a stop, it goes in `unresolved[]`. **Never infer a number that was
not written down.** A wrong price in this log is worse than a missing one,
because the whole point is that it is a factual record of what someone said.

**The production database is real-data-only.** The user removed production mock
data on 2026-08-23. `seed_mock.py` remains available for isolated temporary test
or demo databases, but never run it against `data/traderlog.db`. UI development
that needs synthetic rows must point at a disposable database explicitly.

**Never name a model at a call site.** Ask `llm/provider.py` for a tier —
`cheap`, `smart`, or `vision`. Backends move; call sites do not.

**Do not commit.** Write your `_COMPLETED.md` and stop. The maintainer QCs and
commits, one commit per verified wave.

**Update the docs in the same change.** If you change a table, update
`CONTRACTS.md`. If you change a screen, reconcile it against both
`VISUAL_LANGUAGE.md` and `WIREFRAMES.md`, and update the relevant spec. If you make an
irreversible call, add a dated line to `design/DECISIONS.md`. If you learn that
something in `CANONICAL.md` is wrong, fix it — that file is load-bearing.

**Do not touch `manas_os/`.** TraderLog copies from it, never imports it, and
never writes to its database. If you need something from there, copy it into
`traderlog/adopted/` with a provenance header.

**Delegation role.** For TraderLog implementation, assign bounded grunt-coding
tasks to a Terra subagent when delegation is useful. The primary agent retains
architecture, task boundaries, supervision, integration review, project checks,
and personal verification of every completion claim before handoff.

---

## Answer quality

The repo owner's standing bar is at `STANDING_INSTRUCTIONS.md` (repo root) and
applies to any user-facing answer you produce. In short: mark claims
`Certain` / `Likely:` / `Assumption:` / `Unverified:`; lead with the outcome; a
`Risks:` section is mandatory; never report unverified work as done; say "I don't
know X, here is how to find out" instead of writing a plausible placeholder.

## What this tool is not

TraderLog records what other traders publicly said they did. It does not size
positions, does not route orders, and does not tell the user what to trade. Any
wave that starts to blur that line is out of scope — flag it, do not build it.
