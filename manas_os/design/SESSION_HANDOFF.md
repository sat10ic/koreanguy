# SESSION HANDOFF — read this first, then the 3 files it points to

Repo: `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Manas AI Trading OS — beginner
NSE swing-trading cockpit. FastAPI :8000 + React/Vite :5173, SQLite `manas_os/data/manas.db`.

## Binding rules (do not relitigate)
- Rules-first, no black-box scores. Manual execution only — never order routing.
- Anti-mashup: one writer per metric, one ranked number per screen, no dormant code.
- `manas_os/design/Feedback_woolly_peacock plan` (aka the canonical plan, path in
  `~/.claude/plans/c-users-satta-downloads-manas-os-v2-md-woolly-peacock.md`) has every LOCKED
  threshold (stop caps, R:R floor, regime caps, risk profiles). Never re-derive these ad hoc.
- **Delegate ALL coding to Codex** (`codex:codex-rescue` subagent, background). Main thread
  orchestrates + writes specs only. **One Codex batch at a time** — do not fan out multiple
  concurrent jobs (burns credits fast, caused merge collisions).
- Codex sandbox often lacks `python`/`py` on PATH — tell it to fall back to
  `C:\Users\satta\AppData\Local\Programs\Python\Python312\python.exe`.

## The 3 files to read next (in order)
1. `manas_os/design/CODEX_HANDOFF.md` — the execution queue. BATCH 1/2 done. BATCH 3
   (Position Coach), 4 (Telegram digest), 5 (mentor checklists), 6 (regime history strip) were
   launched — check the `[x]`/`[ ]` boxes at the bottom of this file for what actually landed;
   Codex reports may say done before boxes are ticked, verify against the file itself, not
   just the chat.
2. `manas_os/TASKS.md` — current task board (T-numbers mirror the plan). Sync after each batch.
3. `manas_os/design/LEARNINGS.md` — append-only threshold/finding log, dated entries at the
   bottom. Read the last 3-4 entries for the most recent ground truth (e.g. the 2026-07-06
   entry on a DB-lock false alarm and the rr=2.0 stale-data false alarm — don't re-diagnose
   these, they're resolved).

## To continue
1. Run `python -m pytest manas_os/tests -q` from repo root yourself first — get the REAL
   passing count before trusting anything a subagent claimed. Baseline before this session's
   batches was 163.
2. Check which of BATCH 3/4/5/6 actually finished + passed, by reading CODEX_HANDOFF.md's
   checkboxes and running the suite — not by trusting agent self-reports.
3. Next unclaimed queue slot: pick the next `[ ]` task in CODEX_HANDOFF.md, or if all batches
   there are done, write the next one following the same zero-judgment spec style (exact file
   paths, exact function contracts, exact test assertions) so Codex needs no judgment calls.
4. Remaining known-open work (see TASKS.md for full list): T3.9 Position Coach (batch 3),
   T4.1 Telegram (batch 4 = slice 1 only, live push is NOT built), #17 mentor checklists
   (batch 5), #1 regime history strip (batch 6), #21 live intraday loop (NOT started, needs
   Fyers WS creds — biggest remaining chunk), #29 Axis D beginner/expert column enforcement
   (deferred, noted in LEARNINGS).
5. After each batch: `git add -A manas_os && git commit` (do NOT commit `manas_os/data/`,
   `manas_os/config.yaml` — already gitignored) then `git push origin emergent`.

## Known footguns hit this session
- Stale python.exe child processes can hold a SQLite write lock long after the job that
  spawned them "finished" — `tasklist` + kill orphans before assuming a background replay is
  still the cause of a 500.
- Persisted DB rows can predate a code fix — if live data looks wrong, re-run the pipeline
  stage on current code before concluding it's a live bug.
- `git bash` here sometimes fails `python -c "..."` imports that work fine from a script file
  — write a temp `.py` file and run it, don't rely on `-c`.
