# Manas AI Trading OS

A beginner-friendly, single-user NSE swing-trading decision cockpit. It does **not** pick
stocks or place orders. It answers four questions each day, with explainable evidence:

1. **Should I be aggressive today?** — the Market Regime page (XP dial + MBI breadth + quadrant).
2. **Which valid setup deserves capital?** — scanner + Trade Readiness scoring.
3. **How much should I risk?** — stop-loss + position sizing + gap simulation.
4. **Am I following my process?** — the journal.

Rules first, AI second. Manual execution only. Every score is explainable (evidence chips,
never a bare %). See the full build plan referenced in `docs/` and `FUTURE.md` for scope gates.

## Layout

```
manas_os/
├── cli/            # `manas` entrypoint — run-eod, init-db, fetch, auth
├── db/             # manas.db schema + connection + init
├── providers/      # market-data providers (Fyers) behind a common ABC
├── sources/        # read adapters: breadth sheet, bhavcopy, chartsmaze
├── engine/         # indicator computation + indicator_registry
├── regime/         # XP dial, MBI layer, 4-pillar → regime snapshot
├── scanner/        # EOD scans + setup detectors + trade readiness
├── risk/           # stop-loss, position sizing, gap simulation
├── api/            # FastAPI app (adopted from legacy ssrvol structure)
├── frontend/       # React + Lightweight Charts dashboard
├── data/           # manas.db + migrated ChartsMaze/bhavcopy history (git-ignored)
├── fixtures/       # golden fixtures for snapshot/parity tests
└── tests/
```

## Anti-mashup rules (binding)

1. **Graft = adopt, never import.** Reusable code from `../legacy/` is *copied* into this
   project, renamed to local conventions, and tested here. **No module may `import` from
   `legacy/`** — enforced by ruff (`pyproject.toml`, `flake8-tidy-imports` banned-api).
2. **One entrypoint, one writer, no dormant code.** `manas run-eod` orchestrates the whole
   daily pipeline. Every displayed metric resolves to exactly one `indicator_registry` key
   computed by exactly one module. A module ships only when both wired into the pipeline and
   surfaced in the UI.

## Quick start

```
pip install -r requirements.txt
cp config.example.yaml config.yaml    # then fill secrets
python -m manas_os.cli init-db
python -m manas_os.cli run-eod --date YYYY-MM-DD
```
