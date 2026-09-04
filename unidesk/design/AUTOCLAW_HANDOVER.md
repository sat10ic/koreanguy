# Autoclaw handover — N1 (live measurement session) and N2 (recorder)

Persisted 2026-08-28 (supersedes the chat-drafted version). Read before
starting: `DESK.md`, `plan/UNIFIED_DESK_BUILD_MANUAL.md` (Phase 0 + Phase 3
preamble), `plan/ORDERFLOW_BUILD_MANUAL.md`, `AGENTS.md`,
`orderflow/design/WORKFLOW_MAP.md`,
`orderflow/design/handoffs/P0.1_CAPABILITY_AUDIT_COMPLETED.md`, and
`orderflow/design/handoffs/N1_LIVE_SESSION_PREP_STOP.md` (what preparation
already happened and why).

Your model signature must be real in every ledger record (see
`unidesk/design/MODEL_ATTRIBUTION.md` for the 14-key schema and round-trip
rule; N1/N2 records go in `orderflow/design/MODEL_WORK_LOG.jsonl`).

## Task N1 — live measurement session (= unified U-P0.4 live half)

Goal: regenerate `orderflow/capability.json` from a REAL session
(`--source live`) and present the R1 gate decision to the owner. No feature
work proceeds before that gate.

Build (you):
1. `orderflow/checks/run_live_session.py` — CLI launcher: subscribe >=8 NSE
   cash symbols across four liquidity buckets (highly liquid midcap /
   moderate midcap / liquid smallcap / thin smallcap — final ticker list
   fixed WITH the owner), log every raw message with `ts_exchange` +
   `ts_received` for one full session, run the capability auditor, write
   `capability.json`.
2. Emit the **window-eligibility gate table** from the measured capability
   (unified P0.4 acceptance): median depth interval per liquidity bucket →
   which of 5s/15s/1m/5m windows are valid, research-only, or invalid.
3. Owner-side transport shim — OUTSIDE `orderflow/` (repo-root `scripts/`;
   the boundary test bans `import fyers_apiv3` and env/credential access in
   production code). It duck-types `orderflow.market_data.websocket_manager.MessageTransport`.
   Locked design (DECISIONS D7, from the N1 prep session):
   - construct `FyersDataSocket` with **`reconnect=False`** — the client is a
     singleton with its own internal auto-reconnect that would race the
     manager's;
   - `connect()` blocks ~2 s internally; `close_connection()` is the clean
     shutdown;
   - point the client's `log_path` away from `orderflow/`;
   - subscribe failures arrive via the client's `on_error` callback, NOT the
     message stream — surface them to the manager as control events;
   - subscribe: `subscribe(symbols, data_type="SymbolUpdate"|"DepthUpdate",
     channel=...)`; 5000-symbol batch cap enforced client-side.
4. TBT probe (owner present): attempt a 50-level TBT-socket subscribe for one
   NSE cash symbol; answer "provisioned / not provisioned" with evidence.

Owner does: token refresh out-of-band (existing
`.claude/worktrees/*/scripts/refresh_token.py` flow), exports the token,
starts the session during NSE market hours. **You never read, write, log, or
handle any credential value. If the work requires one, STOP and say so.**

First-live-session checks (from the N1 prep session — confirm, don't assume):
- `exch_feed_time` epoch semantics (UTC epoch assumed; ~1 s granularity).
- Depth sizes (`bid_size1..5`) sit in the un-scaled tail of the client's
  field list — verify scaling against one real sample before trusting
  size-derived numbers.
- Confirm per-field population (`order_count`, `tot_buy_qty`, `tot_sell_qty`,
  `last_traded_qty`) matches expectation.

Acceptance (N1):
- [ ] real `capability.json`, `data_source=live`, real per-bucket histogram +
      medians + p95
- [ ] R1 gate table filled from measurement
- [ ] TBT verdict with evidence either way
- [ ] optional-field presence from observation
- [ ] live forced-disconnect test: kill the socket once; gap visible in
      output, never interpolated
- [ ] ledger record + completed handoff in `orderflow/design/`; unidesk
      TASKS.md U-P0.4 updated at wave close

## Task N2 — continuous recorder (= unified U-P0.5)

Files: `orderflow/storage/parquet_writer.py`, `orderflow/storage/duckdb_repo.py`,
`orderflow/checks/feed_health.py`, tests. Partition
`date=YYYY-MM-DD/symbol=SYM/`. Feed-health state machine
`HEALTHY/DEGRADED/STALE/DISCONNECTED` (last-quote age, last-depth age,
reconnect count, duplicates, clock skew, out-of-order timestamps,
nonsensical quantities). Reconnect with subscription recovery.

Acceptance:
- [ ] forced disconnect reconnects + resubscribes; gap visible in data
- [ ] replaying one session's Parquet reproduces the canonical book state
- [ ] stale depth ⇒ `flow_state=UNKNOWN`, proven by a clock-advancing test
- [ ] no credential in any written file or log

## Standing constraints (unchanged)

No order routing anywhere. No `import traderlog`/`import manas_os`. Don't
modify `traderlog/`, `manas_os/`, `backend/`, `legacy/`. No git commit.
Missing fields are null, never invented. FYERS names stay in the adapter.
`python -m pytest orderflow/tests -q` stays green (62 baseline).
Module runs use the Python 3.12 interpreter (`py -3.12` or
`.venv-orderflow/Scripts/python.exe` — prepared by the N1 prep session); the
default `python` (3.14 hybrid) ignores cwd/PYTHONPATH for `-m`.

## When N1 is green

Present the R1 gate decision to the OWNER before building anything on it. If
the feed is slow and TBT absent, the short-window features die at birth and
what remains is the liquidity/exit-safety layer — that is a legitimate
outcome, decided on the measurement (unified manual §6).
