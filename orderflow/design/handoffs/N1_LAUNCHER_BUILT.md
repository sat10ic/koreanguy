# N1 launcher + transport shim — BUILT (session still owner-pending)

Date: 2026-08-29. Model: GLM-5.3-Flash (host id `builtin:zai-coding-plan/GLM-5.3-Flash`),
host ZCode, role executor.

Attribution-ID: attr-orderflow-n1-launcher-glm53flash-20260829-001

## Outcome

The live measurement session's tooling is complete and offline-proven; the
session itself awaits the owner (next market day: Mon 2026-08-31, pre-market
login via `scripts/fyers_login.py`).

- `orderflow/checks/run_live_session.py` — launcher: subscribes the (provisional,
  owner-editable) 8-symbol mixed-bucket set, tees every RAW message with
  `ts_received` to `data/orderflow/raw/live_*.jsonl`, runs the capability
  auditor through the `WebSocketManager`, writes `capability.json` with
  `data_source=live`, and prints the R1 window-eligibility gate table computed
  from the MEASURED per-bucket medians (`window_gate_table`: <1 Hz medians
  demote 5s→research_only and 15s→low_confidence; ≥1 Hz boundary counts as
  slow). Smoke mode: `--duration-s 600`. Ctrl+C finalizes the report.
- `scripts/fyers_live_transport.py` — owner-side shim, outside `orderflow/`
  (D7): imports `fyers_apiv3`, composes `CLIENT_ID:TOKEN` in memory, constructs
  `FyersDataSocket(reconnect=False, log_path=<tempdir>)`, maps
  `subscribe/unsubscribe` payloads to the client, surfaces decoded dicts to the
  manager, collects `on_error` failures on a separate error queue the launcher
  drains and prints. Fails fast with a clear RuntimeError when env vars are
  absent; verified.
- `orderflow/market_data/websocket_manager.py` — new benign poll-timeout path:
  `TransportClosed("timeout")` returns `"timeout"` without reconnecting (a
  quiet market second is not a dead socket; heartbeat staleness still forces
  reconnect). Tested.
- `.gitignore` — `data/orderflow/` added so raw captures stay uncommitted (D6).

Boundaries held: `orderflow/` production code remains free of `os.environ`,
credential vocabulary, and `import fyers_apiv3` (boundary tests green); no
credentials handled; no live connection made; `traderlog/`, `manas_os/`,
`backend/`, `legacy/` untouched; no git commit.

## Verification

```text
python -m pytest orderflow/tests unidesk/tests -q   -> 84 passed
  (new: benign-timeout manager test; R1 gate-table tests incl. the
   1 Hz-boundary-counts-as-slow case; launcher env-freeness test)
.venv-orderflow/Scripts/python.exe -m py_compile
  scripts/fyers_live_transport.py
  orderflow/checks/run_live_session.py               -> compile OK
shim without env                                      -> RuntimeError (fail fast)
```

## Honest partials

- The SESSION itself has not run: no live capability.json, no R1 gate from
  real data, no TBT verdict, no live disconnect test, no live scaling check.
- Symbol list is provisional (8 tickers chosen for bucket spread); owner must
  confirm/replace before the session.
- The shim is untested against the real client (it cannot be, offline); its
  behavior rests on the v3.1.16 wheel-source verification recorded in the N1
  prep session. First connection may surface integration mismatches — treat
  the smoke run (`--duration-s 600`) as the shakedown.
- 2026-08-29/30 is a weekend: NSE cash is closed; the earliest meaningful
  session is Mon 2026-08-31 (09:15–15:30 IST).
