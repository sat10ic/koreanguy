# SwingIntel Build — Handoff Document

**Session:** 2026-07-02 → 2026-07-03
**Branch:** `emergent`
**Commits:** 7 (T1.2–T1.6, T2.0, QC fixes), starting after `447ffc70`

---

## 1. What this session set out to do

Execute the SwingIntel unified build plan (per the Compass artifact + FilingsEdge Handoff Spec) in three tracks:
- **Track 1** — Fix the signal-starved technical screen (the gate; catalyst cross-ref is useless if the technical side emits 0 candidates).
- **Track 2** — Build the FilingsEdge catalyst layer (M1–M8: bhavcopy + announcements + LLM classification + veto + outcomes).
- **Track 3** — Unify outcomes + extend the React dashboard.

Decisions locked at planning time: new `disclosures.db` (4th DB, not crammed into portfolio), `prices` table kept separate from `ohlcv.db`, reuse `scripts/analyst.py` for the LLM, extend `scripts/notify.py`, no Streamlit (extend React instead).

---

## 2. What's DONE — verified

### Track 1: Technical screen fixed (THE GATE — PASSED)

The headline failure (per `AUDIT_FINDINGS.md`): `candidates.csv` was **permanently empty**, `setup_pass` 0–1/416/day. **Now produces 4 verified candidates** on the latest data (2026-06-17):

| Symbol | Tier | Grade |
|---|---|---|
| DATAPATTNS | primary | A+ |
| TITAGARH | secondary | A+ |
| NUVAMA | secondary | A |
| MGL | secondary | A |

| Commit | Task | What changed | Measured impact |
|---|---|---|---|
| `4348c7f6` | T1.2 | `scripts/_symbol_map.py` — evidence-backed rename map (14 renames) + delisted set (2). Wired into both fetchers. | 29 missing symbols categorized: 14 renamed, 2 delisted (removed), 13 transient. Fixed AVENUE→DMART in universe.csv. |
| `2b783a8b` | T1.3 | `indicators.py` Weinstein stage: `slope > 0.005` → `slope > adr14_pct/100` (volatility-aware). | S2: 98→57 (was mislabelling noise as trend; 42 ex-S2 + 52 ex-S3 → correctly S1B). |
| `89207d90` | T1.4 | `_grade_helper.py` hybrid grading: absolute rs_score floor caps percentile grades. | 23/63 inflated top-tier stocks suppressed (e.g. RELIANCE rs 0.022 was percentile A-, now B+). |
| `df6929e0` | T1.5 | `screen.py` dual-path setup: added Path B (fresh breakout). | setup_pass: 13 → 19 (+46%). Captures 6 fresh breakouts (PARAS, DATAPATTNS, etc.). |
| `1f36ba99` | T1.6 | `verify.py` made config-authoritative; Layer A relaxed from unachievable to disciplined. | 0 candidates → 4. |

**T1.1 (holiday calendar) was SKIPPED** — verified `ohlcv.db` is already trading-days-only (zero weekend rows), so a holiday mask would be dead complexity. Deferred to FilingsEdge M7 orchestrator.

### Track 2 T2.0: FilingsEdge scaffold — DONE

| File | Purpose | Lines |
|---|---|---|
| `scripts/filings/_db.py` | `disclosures.db` schema (9 spec tables + `pipeline_runs`), `init_schema()`, `log_run()` | 237 |
| `scripts/filings/_sources.py` | Source-abstraction: curl_cffi browser impersonation, inbox pattern, lazy lib imports | 143 |
| `scripts/filings/__init__.py` | Package docstring | 26 |
| `prompts/classifier_v1.md` | Versioned classifier prompt (taxonomy, JSON schema, examples) | 73 |
| `evals/golden_events.csv` | Eval harness stub (header + instructions) | 19 |

`disclosures.db` initialized with 11 tables. Config `filingsedge:` section added. Requirements updated (curl_cffi, jugaad-data, pdfplumber).

### QC fixes (commit `1bc4d4d2`)

1. **`backend/server.py` `SWINGEDGE_ROOT` bug**: defaulted to `/app` (container path), silently serving empty data locally. Now defaults to repo root.
2. **`fetch_fyers.py` `fetch_one()` hardening**: guards against `None` symbol (delisted).
3. **`fetch_fyers.py` rename logging**: `run_fetch()` logs all active remaps up front.

---

## 3. QC issues — found and resolved

During QC (prompted by "are you done qc testing?") I discovered my initial "gate passed" claim was made **before force-rebuilding indicators** — screen/verify were reading stale `stage` data that coincidentally gave the same answer. The fixes were then properly verified:

| Issue found in QC | Resolution | Status |
|---|---|---|
| T1.3 not persisted to `features.db` (screen/verify read stale stage) | `run_indicators(force_rebuild=True)` — S2=57 now in DB | ✅ Fixed |
| `SWINGEDGE_ROOT=/app` breaks local backend (serves empty data) | Default to repo root | ✅ Fixed |
| `fetch_one` crashes on `None` symbol (delisted via `--only`) | Guard added | ✅ Fixed |
| Wrong symbol rename silent on fetch (data gap invisible) | `run_fetch` logs remaps up front | ✅ Fixed |
| Frontend untested | React production build + 10-endpoint smoke test | ✅ Verified |

### Final QC verification (all passed)
- Full pipeline: regime (RISK_ON 5/5) → screen (19 setups) → verify (4 candidates).
- 10 frontend-called endpoints return 200 with correct structure.
- `/api/candidates` serves the 4 candidates; `/api/screen` includes `fresh_breakout_pass`.
- React build compiles clean (1 pre-existing lint warning, unrelated).
- Downstream detectors unbroken: ep 19, breakout 47, pullback 53, top_picks 10.

### ⚠️ One item NOT verifiable from this environment
**Live Fyers symbol resolution**: the rename map (GMRINFRA→GMRAIRPORT, PVR→PVRINOX, etc.) is verified against NSE's `symbolchange.csv` and live quote pages, but NOT against the actual Fyers API (no token in this env). **On the next fetch, check the new remap log line** — if any mapped symbol logs "invalid symbol", the mapping is wrong and needs correction in `scripts/_symbol_map.py`. The log makes this immediately visible.

---

## 4. Process notes / known debts

1. **Attribution drift in two commits** — T1.3 (`2b783a8b`, indicators.py) and the QC commit (`1bc4d4d2`, server.py) swept in pre-existing uncommitted work from the working tree (your REPLAN endpoint renames in server.py; `_lin_slope`/`_bars_since_high` in indicators.py). The code is correct and tested, but the commits attribute ~580 lines of your prior work under my messages. Flagged in commit messages rather than rewriting history.

2. **Audit/FIX_PLAN docs were partially wrong** — three of their claims were refuted by measuring actual data:
   - "holidays distort indicators" → False (ohlcv already trading-days-only).
   - "HPCL→HINDPETRO rename" → False (different companies; HPCL is valid).
   - FIX_PLAN grade bands (A+≥0.30) → miscalibrated (would give A to <1% of stocks; used data-derived floors instead).
   These docs (`AUDIT_FINDINGS.md`, `FIX_PLAN.md`, `TODO.md`) should not be trusted blindly going forward.

---

## 5. What's LEFT to build

### Track 2 — FilingsEdge M1–M8 (scaffold done, modules not started)

| Task | Module | Status | Dependencies |
|---|---|---|---|
| T2.1 | `m1_ingest_bhavcopy.py` — UDiFF bhavcopy + delivery → `prices` | Not started | jugaad-data (installed) |
| T2.2 | `m1_ingest_announcements.py` — NSE/BSE announcements → `announcements_raw` | Not started | **pdfplumber (NOT installed — `pip install pdfplumber`)** |
| T2.3 | `m1_ingest_deals.py` + `m1_ingest_surveillance.py` | Not started | curl_cffi (installed) |
| T2.4 | `m2_extract.py` — LLM classifier (reuses `analyst.py` + new JSON validation) | Not started | OPENROUTER_API_KEY in .env |
| T2.5 | `evals/run_eval.py` — eval harness **(GATE)** | Not started | **User must expand `evals/golden_events.csv` from manual reps** |
| T2.6 | `m3_features.py` — deterministic feature battery | Not started | M1 data |
| T2.7 | `m4_crossref.py` — material events ⋈ `screen_today.csv` | Not started | M3 + working screen (✅ done) |
| T2.8 | `m5_veto.py` — pledge/ASM/delivery/pump checks + risk memo | Not started | M3 |
| T2.9 | `m6_alert.py` — Telegram digest (extends `notify.py`) | Not started | TG_TOKEN in .env |
| T2.10 | `m7_orchestrator.py` — plain driver, retries, health rollup | Not started | M1–M6 |
| T2.11 | `m8_outcomes.py` — 5/10/20d forward returns backfill | Not started | M4 candidates + `prices` |
| T2.12 | `import_fundamentals.py` — quarterly screener CSV loader | Not started | **User supplies fundamentals CSV** |

### Track 3 — Unify outcomes + React dashboard (not started)

| Task | Status |
|---|---|
| T3.1 Unified outcomes view (UNION `pick_history` + catalyst `outcomes`) | Not started |
| T3.2 Backend endpoints (`/api/filings/digest`, `/events`, `/smart_money`, `/delivery`, `/outcomes`, `/health`) | Not started |
| T3.3–T3.6 React tabs: Event Explorer, Smart Money, Delivery Radar, Outcomes & Calibration | Not started |
| T3.7 Integrate catalyst candidates into Tonight's Digest | Not started |

### Explicitly deferred to FUTURE.md (both artifacts agree)
- Autonomous self-improvement loop (12+ months of clean data required first).
- Concall transcript analyzer (v2).
- Pump-signature social monitoring (v2 — adversarial data).
- Walk-forward / DSR / PBO gating engine (Tier 2).
- React dashboard rebuild (Tier 3).

---

## 6. What ONLY THE USER can provide

These cannot be fabricated and block specific tasks:

1. **`evals/golden_events.csv` labels** (blocks T2.5 gate) — ≥50 hand-classified announcements from your manual reps (FilingsEdge Playbook §3). I built the harness structure; you expand it. This is what keeps the LLM classifier honest.
2. **`pdfplumber` install** (blocks T2.2) — `pip install pdfplumber`. Needed for announcement PDF text extraction.
3. **Fundamentals CSV** (blocks T2.12) — quarterly screener export (TTM revenue, gross block, pledge %). Materiality ratios need denominators.
4. **Confirm `.env` has `OPENROUTER_API_KEY` and `TG_TOKEN`** (blocks T2.4, T2.9).
5. **Verify live Fyers symbol resolution on next fetch** — check the remap log line; report any "invalid symbol" on a mapped ticker.

---

## 7. How to resume

The state is clean and committed. To continue:

```bash
git log --oneline -7          # see the 7 commits
git show 1bc4d4d2             # review the QC fixes
python scripts/filings/_db.py # re-init/verify disclosures.db schema
```

**Recommended next task:** T2.1 (`m1_ingest_bhavcopy.py`) — the bhavcopy ingest is the data spine everything else reads, and it doesn't depend on the unverified items above. After that, T2.4/T2.5 (classifier + eval) is the next gate.

The FilingsEdge Handoff Spec (`FilingsEdge_Handoff_Spec.md`, in `C:\Users\satta\Downloads\`) is the authoritative reference for M1–M8 module specs, schema, and acceptance criteria.

---

## 8. Compliance posture (unchanged, baked in)

- **No order placement anywhere** — stays outside SEBI's April-2026 algo framework.
- **Risk memos descriptive only** (no buy/sell/target language) — `analyst.strip_forbidden` enforces it; keeps outside RA scope.
- **Telegram digest to you only** — no signal sharing.
- **Public data only** (NSE/BSE disclosures).
