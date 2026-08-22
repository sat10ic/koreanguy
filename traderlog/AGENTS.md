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

---

## The rules that matter

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

**Never name a model at a call site.** Ask `llm/provider.py` for a tier —
`cheap`, `smart`, or `vision`. Backends move; call sites do not.

**Do not commit.** Write your `_COMPLETED.md` and stop. The maintainer QCs and
commits, one commit per verified wave.

**Update the docs in the same change.** If you change a table, update
`CONTRACTS.md`. If you change a screen, update `WIREFRAMES.md`. If you make an
irreversible call, add a dated line to `design/DECISIONS.md`. If you learn that
something in `CANONICAL.md` is wrong, fix it — that file is load-bearing.

**Do not touch `manas_os/`.** TraderLog copies from it, never imports it, and
never writes to its database. If you need something from there, copy it into
`traderlog/adopted/` with a provenance header.

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
