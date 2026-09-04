# HANDOFF 5 — Fyers tiered intraday backfill run + coverage UI (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Wave item 2 of `manas_os/design/handoffs/HANDOFF_CODEX_ALPHA_BEHAVIOUR_WAVE1.md`: the tiered
intraday storage/provider seam is BUILT (5-min full universe, 1-min active set, Fyers adapter,
resumable windows, completeness checks — find it under `manas_os/alpha/` / intraday modules);
the actual backfill has never been RUN.

## Scope
1. **Pre-flight**: locate the intraday backfill entrypoint/CLI; verify Fyers auth status via the
   existing auth module (token expires 6am IST daily — if `auth_needed`, STOP and report; the
   maintainer/user must re-auth, do not attempt credential input yourself). Confirm rate-limit
   handling exists in the adapter (Fyers history API limits); add polite throttling if missing.
2. **Run the tiered backfill** for the resumable windows the seam defines (5-min full universe
   first, then 1-min active set), in bounded chunks (resume on failure — the machinery is
   documented as resumable; prove it by interrupting one chunk and resuming). Record provenance
   + completeness per window.
3. **Coverage surfacing**: expose backfill progress + data-quality coverage in the Alpha Lab UI
   (the wave spec asks for SSE progress — reuse the UI-2 jobs/events pattern so the run shows in
   Live Work; a static coverage table in Alpha Lab is acceptable if the run is already complete
   by the time you wire UI).
4. **QC the data**: per-tier coverage report (symbols × sessions × expected bars vs actual),
   spot-check 3 symbols' 5-min bars against daily OHLC consistency (day high/low must bound the
   intraday bars), gaps documented honestly.

## Do NOT
Store secrets in code/logs. Exceed API limits (back off on 429s). Fabricate bars for gaps.

## Output
`HANDOFF_GEMINI_fyers_intraday_backfill_COMPLETED.md`: windows run, coverage stats, consistency
spot-checks, failures/gaps, UI wiring notes. If auth blocked you, say exactly that + what's ready.
