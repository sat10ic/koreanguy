# N1 live measurement session — handoff at stop point

Date: 2026-08-28 ~23:25 IST. Model: GLM-5.3-Flash (`builtin:zai/zai_glm-5.3-flash` via
OpenClaw/AutoClaw), role executor. Owner asked to STOP mid-preparation. Nothing in
`orderflow/` production code was modified; no live FYERS connection was made; no
credentials were read, handled, or logged.

Attribution-ID: attr-orderflow-n1-prep-glm53flash-20260828-001

## Status of Task N1 (manual P0.1 steps 1-4, live session)

State at stop: **preparation and verification only.** The live session itself has NOT
been run — by task rule it requires the owner to start it, and the owner has not
started it.

## What was done (all read-only except the venv)

1. Read, in the required order: `DESK.md`, `plan/ORDERFLOW_BUILD_MANUAL.md`,
   `AGENTS.md`, `orderflow/design/WORKFLOW_MAP.md`,
   `orderflow/design/handoffs/P0.1_CAPABILITY_AUDIT_COMPLETED.md`.
2. Read the existing P0.1 apparatus end-to-end (schemas, adapter, manager, auditor,
   boundary tests) to fix the integration contract for the live transport.
3. Installed `fyers-apiv3==3.1.16` into a NEW isolated virtual environment
   `.venv-orderflow/` (Python 3.12) at the repo root. Reason: the installed global
   fyers_apiv3 (on Python 3.14) is v3.1.12 and contains NO websocket module at all;
   the owner's global site-packages were NOT touched. Added `.venv-orderflow/` to `.gitignore`
   pre-existing untracked `orderflow/`.
4. Read the v3.1.16 wheel source as protocol reference and verified, against the
   installed package (not memory):
   - `data_ws.py` `FyersDataSocket`: URL `wss://socket.fyers.in/hsm/v1-5/prod`,
     auth + mode messages sent automatically in `__on_open`, decoded dicts handed to
     the `on_message` callback — exactly the adapter's input contract.
   - `map.json` field lists (`data_val`, `depthvalue`) match `fyers_adapter.py`'s
     mapping exactly: quote = `sf` with `ltp`, `vol_traded_today`, `last_traded_qty`,
     `exch_feed_time`, `tot_buy_qty/tot_sell_qty`, top-of-book
     `bid_price/bid_size/ask_price/ask_size`; depth = `dp` with flat
     `bid_price1..5 / ask_price1..5 / bid_size1..5 / ask_size1..5 /
     bid_order1..5 / ask_order1..5`. 5 levels by protocol on this socket.
   - Subscribe success ack: `{"type": "sub", "code": 200, "s": "ok"}` (matches
     `is_subscribe_ack` + `ack_indicates_success`); failures surface via the
     `on_error` callback, not the message stream.
   - `subscribe(symbols, data_type="SymbolUpdate"|"DepthUpdate", channel=11)`;
     5000-symbol cap enforced client-side in `subscribe`.
   - IMPORTANT lifecycle facts for the live transport design: `FyersDataSocket` is a
     SINGLETON with its own background threads and its own internal auto-reconnect
     (`__on_close` reconnect loop, enabled by default via `reconnect=True`). The
     manager's own reconnect would race the client's internal one. Design decision
     reached: construct the owner-side transport with `reconnect=False` and let the
     orderflow `WebSocketManager` own all reconnect/resubscribe logic;
     `close_connection()` is the clean shutdown path; `connect()` blocks ~2 s
     internally (`time.sleep(2)`).
   - `tbt_ws.py` exists in v3.1.16 (protobuf, `msg_pb2.py`, separate socket) — the
     50-level TBT probe remains answerable only with a live owner-run session.
   - The client writes `fyersDataSocket.log` files (its own logging); the live
     transport must set `log_path` to keep client logs out of `orderflow/`.
5. Confirmed the owner auth pattern: `.claude/worktrees/*/scripts/refresh_token.py`
   (interactive; app id/secret from env or SwingEdge settings; prints the access
   token for the owner to export). Credentials never enter `orderflow/` — unchanged.

## What was NOT done

- No live session run (owner has not started one; also the NSE cash session window
  is required).
- No new production files written. `orderflow/checks/run_live_session.py`, the live
  transport module, and the TBT probe do NOT exist yet.
- No `capability.json` regeneration (still `data_source: synthetic`).
- No R1 gate table fill-in, no TBT verdict, no live optional-field presence, no
  forced-disconnect live test.
- No tests were run this session and no existing file was modified.
- No git commit (per standing constraint).

## Where the next session should pick up

1. Write `orderflow/checks/run_live_session.py` (CLI launcher) plus an owner-side
   transport shim OUTSIDE the package (the boundary test bans `import fyers_apiv3`
   and any env/credential access in production code — the shim must live outside
   `orderflow/`, e.g. a repo-root scripts directory, duck-typing `MessageTransport`
   constructed with `reconnect=False`).
2. Owner performs token refresh out-of-band, starts the session during NSE market
   hours with the token already in the environment.
3. Symbols plan: >=8 NSE cash symbols across the four liquidity buckets
   (highly liquid midcap / moderate midcap / liquid smallcap / thin smallcap),
   concrete ticker list still to be fixed with the owner.
4. Separate TBT-socket probe for one NSE cash symbol, owner present.
5. Acceptance checklist remains exactly as in the N1 task block (live capability.json,
   R1 gate table, TBT evidence, optional-field presence, live forced-disconnect test).

## Honest unknowns at this stop point

- Whether the account is provisioned for 50-level TBT (Unverified — external claim).
- Real depth cadence, optional-field population, real subscription limits, live
  reconnect behaviour: all Unverified until the owner-run live session.
- `exch_feed_time` epoch semantics (UTC epoch assumed; 1-second granularity
  suspected): must be confirmed against live traffic before trusting
  `feed_latency_ms`.
- v3.1.16's `__response_output` divides price fields by `precision`/`multiplier`;
  the adapter assumes rupee-scaled inputs. The scaling boundary for depth sizes
  (`bid_size1..5` sit in the un-scaled tail of `depthvalue`) needs one live sample
  to confirm — listed as a first-session check, not an assumption to build on.
