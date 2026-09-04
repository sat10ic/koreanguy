# HANDOFF W-E primitives + first real setup scan — COMPLETED (first slice)

Date: 2026-08-29.

Attribution-ID: attr-unidesk-we-primitives-scan-glm53flash-20260829-001

## Outcome

- `unidesk/momentum/primitives/pivots.py` — k-bar fractal pivots with the
  manual's known_at confirmation lag (a pivot is observable only k bars
  after it occurs; ties reject deterministically) + `pivots_known_at`
  point-in-time filter.
- `unidesk/momentum/primitives/contraction.py` — base_depth_pct,
  range_contraction_ratio, volume_dryup_ratio (exclusive windows, warm-up
  None on unfull or zero-baseline windows).
- `unidesk/momentum/detectors/momentum_burst.py` — the first setup detector:
  pure rule composition over caller-computed features (ADR%, RS rank, RVOL,
  contraction ratio, optional AVWAP extension). Returns
  VALID/INVALID/INSUFFICIENT_DATA with named rule failures; all thresholds
  are parameters (R14). No math, no I/O, no scores.
- **FIRST REAL SETUP SCAN** (2026-06-30, point-in-time filtered): 2,760
  symbols, 20-day RS ranks across the live universe, scanned in 8.3 s →
  8 VALID Momentum Burst candidates (BANKA, VLEGOV, NEOGEN, HBESD, IGPL,
  PARKHOSPS, KIMS, OMNI) with per-rule values recorded. This is the first
  end-to-end run: real files → store → features → detector → named output.

## Files changed

- `unidesk/momentum/primitives/__init__.py`, `pivots.py`, `contraction.py` (new)
- `unidesk/momentum/detectors/__init__.py`, `momentum_burst.py` (new)
- `unidesk/tests/test_setup_primitives.py` (9 tests, new)
- `unidesk/GOAL.md` (status)

## Verification

```text
.venv-orderflow/Scripts/python.exe -m pytest orderflow/tests unidesk/tests -q -> 182 passed
Full-universe scan: 646k bars, 2760 symbols, scan 8.3 s
```

## Honest partials

- One detector of eight; remaining detectors (episodic pivot, IPO base,
  inside bar, base breakout, pullback, reversal/reclaim, power play) follow
  the same rule-composition pattern.
- Geometry (trigger/invalidation/room/RR/entry quality, P2.5–P2.8) not
  started; gold fixtures (P2.3 acceptance) not yet authored.
- Scan candidates are rule outputs, NOT trade recommendations (R3/R7) — and
  the scan used a provisional benchmark-less RS rank (universe percentile);
  benchmark-relative RS arrives with the index series decision.
