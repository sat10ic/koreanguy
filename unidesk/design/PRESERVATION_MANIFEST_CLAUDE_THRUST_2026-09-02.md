# Preservation manifest — Claude thrust wave (2026-09-02, ~02:13–02:35 IST)

**Purpose:** Claude's session ran out of quota mid-wave and could not record
its progress. This manifest inventories every artifact of that wave so no
later agent overwrites it. Inventoried from file mtimes and content, BEFORE
any follow-up edits.

**Attribution note:** these artifacts belong to Claude (host per owner's
rotation). No attribution record was appended by that session; per the
never-invent rule, no record has been authored on its behalf either. The
owner should have that session append its own `attr-unidesk-…` record
citing this manifest, or approve a record with `identity_basis: unknown`.

## Inventory (all verified on disk)

| # | Artifact | Status at handover |
|---|---|---|
| 1 | `unidesk/momentum/features/thrust.py` (NEW, 8.8KB) | Complete. Clean-room ADRMAX + ChopScore + stop-in-thrust-days from the authors' public descriptions; provenance documented in-module. |
| 2 | `unidesk/momentum/scan.py` | Claude added `adr_max_pct` / `chop_score` fields to `SymbolScan` (lines ~125-127) and computes them per symbol (`chop_score(...)` at ~line 374, `adr_max(...)` near ~line 394). |
| 3 | `unidesk/momentum/report_json.py` | Claude added the four fields to `_CANDIDATE_FIELDS`-adjacent emission (`adr_max_pct`, `chop_score`, `chop_band`, `stop_thrust_days`; `stop_thrust_days` derived via `stop_in_thrust_days` at ~line 84). |
| 4 | `unidesk/tests/test_thrust.py` (NEW) | Complete and passing: 15/15. |
| 5 | `unidesk/checks/published_invariants.py` | Claude's published-invariants suite (7 invariants incl. funnel-nesting, prices-match-source, scores-have-variance, ranked-symbols-traded, no-fabricated-rows). Passing; results recorded in STATE.json `checks.inv:*`. |
| 6 | `unidesk/STATE.json` | Claude appended the `inv:*` results (preserved verbatim). NOTE: its rewrite also reverted `showing_synthetic_data` to `true`; corrected back to `false` (the UI carries no synthetic data) with the `inv:*` block untouched. |
| 7 | `tonight_2026-09-01.json` (source + bundled copy) | Claude re-ran the nightly at ~02:14 IST with the thrust features; both copies regenerated (identical; 1,163 scanned / 88 candidates; four thrust fields present on every candidate row). |
| 8 | `unidesk_terminal/src/lib/candidates.ts` | Claude's mapper additions: `adrMaxPct` / `chopScore` / `chopBand` / `stopThrustDays` from the report fields. INCOMPLETE at handover: the types on `RawCandidate` / `Candidate` were never declared, so `npm run build` failed with 5 TS errors. |
| 9 | `unidesk_terminal/src/screens/History.tsx` (00:46) | Claude's OWN upgrade for its finer outcome states: WIN / STOPPED / STOPPED_GAP / OPEN ("Still open") / FLAT ("no target") / NO_DATA — fixing the win-inflation it documented in the exporter docstring. Complete; do not regress. |

## Completion work done by the follow-up session (GLM-5.3-Flash, same day)

Declared the four fields on `RawCandidate` (tonight.ts) and `Candidate`
(fixtures.ts) and surfaced them in the Stock page Pro panel under
"Thrust / price action" with a provenance footnote (charter: no dormant
code). Nothing else in Claude's wave was altered.

## Loose ends observed in Claude's wave (kept as-is, listed for the owner)

- No `MODEL_WORK_LOG.jsonl` record and no handoff doc for the wave
  (quota ran out) — the attribution gap is real and acknowledged above.
- The thrust mapper was UI-dormant at handover (now surfaced — see above).
- `published_invariants.py` is not yet invoked by `run_checks.py`; it is
  run standalone and its results live in STATE.json. Surfaced to the user
  via the Data Quality drawer's new "Desk self-checks" block
  (src/data/desk_checks.json, generator `unidesk/run_export_desk_checks.py`).
- `showing_synthetic_data` regression (above) was corrected to `false`.
