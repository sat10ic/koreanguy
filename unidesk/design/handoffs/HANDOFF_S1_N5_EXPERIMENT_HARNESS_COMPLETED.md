Attribution-ID: attr-unidesk-s1-n5-harness-codex-20260904-001
Attribution-ID: attr-unidesk-npu-feasibility-codex-20260904-001
# Completed — S-1 N5 fixture experiment harness and NPU feasibility

**Date:** 2026-09-04

## Delivered

`unidesk/run_n5_experiment.py` now has a pure `evaluate_experiment()` path
that consumes immutable `ResearchEvent` fixtures, an explicit trading calendar,
and pre-computed candidate/baseline arm outcomes. It:

- evaluates only expanding walk-forward **test** folds;
- removes same-symbol overlapping events through the existing embargo helper;
- requires both arms to share each reported session;
- refuses missing `net_bps`, arm metadata, exchange-calendar sessions, or a
  single 64-hex `ca_table_hash` instead of substituting zeroes;
- applies `compare_edge`, DSR, and the existing bootstrap CI; and
- writes an auditable artifact with hypothesis, arms, n, coverage, DSR, final
  verdict, date, and CA-basis hash. Exceptions write an error artifact and
  return a non-zero process status.

`unidesk/tests/test_n5_experiment.py` supplies a 160-session fixture. It proves
a successful CLI artifact, the walk-forward/embargo/arm-alignment path, a
missing-outcome refusal, and a null signal that fails the DSR promotion gate.

## Verification

```text
.venv-orderflow\Scripts\python.exe -m pytest \
  unidesk/tests/test_n5_experiment.py \
  unidesk/tests/test_experiments_ep.py \
  unidesk/tests/test_significance.py \
  unidesk/tests/test_phase0_primitives.py -q
39 passed

.venv-orderflow\Scripts\python.exe -m py_compile unidesk/run_n5_experiment.py
exit 0
```

## Event Track boundary

This is the prerequisite harness, not a completed IPO/EP product surface. No
real archive experiment ran, no event archive partition was read or written,
and no Events UI was added. B2-3 must establish a single CA basis; E-1 remains
owned by its in-flight listing-calendar wave; E-2 still needs a timestamped
announcement corpus. The requested E-3 circuit change was not applied because
the actual target (`momentum/universe/gates.py`) is a ranking gate, contrary to
the handoff's isolated-feature assumption; changing it needs an owner decision.

## NPU conclusion

The laptop exposes Intel AI Boost, but the current project has no OpenVINO or
ONNX Runtime and the reported OS is Windows 10. Its NPU is therefore not a
build/runtime dependency. The detailed opt-in, benchmark-first path is in
`unidesk/design/NPU_RUNTIME_FEASIBILITY_2026-09-04.md`.
