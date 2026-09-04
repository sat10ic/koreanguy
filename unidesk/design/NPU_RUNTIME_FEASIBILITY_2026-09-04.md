# UniDesk local NPU feasibility — 2026-09-04

## Decision

Do not add NPU code to the current build. It cannot accelerate deterministic
Python builds, pytest, Parquet/DuckDB work, the nightly scan, or the terminal
UI. It may later accelerate an **optional, advisory** local vision/OCR,
embedding, or small-model classification worker, but only after a measured
device probe and with CPU fallback.

## Observed on this laptop

| Observation | Result |
|---|---|
| NPU device | `Intel(R) AI Boost`, `ComputeAccelerator`, status `OK` |
| CPU | Intel Core Ultra 5 115U |
| Intel NPU driver | `32.0.100.3159`, dated 2024-12-09 |
| OS report | Windows 10 Home Single Language, 25H2, build `26200.9168` |
| Current project runtime | Neither `openvino` nor `onnxruntime` is installed in `.venv-orderflow` |

This proves the device is detected, **not** that a supported inference provider
can use it. Intel's OpenVINO NPU documentation lists Intel Core Ultra and
Windows 11 (22H2+) as supported, and requires a compatible NPU driver. Windows
ML likewise uses Intel OpenVINO for its NPU execution provider. The observed
Windows product report therefore leaves compatibility unverified.

Sources: [OpenVINO NPU device requirements](https://docs.openvino.ai/2026/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html), [OpenVINO system requirements](https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html), [Microsoft Windows ML accelerators](https://learn.microsoft.com/mt-mt/windows/ai/new-windows-ml/accelerate-ai-models).

## Suitable future scope

- **Build / tests / market-data store / ranking:** CPU, memory and SSD bound;
  NPU has no role.
- **Real-time price, risk, ranking, or order flow:** do not use an NPU. These
  paths must stay deterministic and must not depend on an optional local model.
- **Offline chart-image OCR or evidence extraction:** possible as a separate
  worker. Its output must remain cited evidence/provisional data, never author
  a trade, price, stop, score, or ranking.

## Preconditions for an opt-in probe

1. Owner approves an isolated probe environment; do not alter the project
   environment or Windows drivers as part of ordinary UniDesk work.
2. Install a pinned OpenVINO runtime in that probe and verify that its device
   inventory exposes `NPU`; retain CPU fallback.
3. Benchmark the same representative, non-decision model on CPU and NPU after
   warm-up, recording latency, throughput, RAM, failure/retry rate and battery
   draw. Do not generalise from a synthetic model.
4. Adopt only if the NPU run is stable and materially better for that exact
   workload. The owner decides the latency/operating-cost trade-off.

## Non-goals

No model, driver, package, credential, or inference pipeline was installed or
changed. This note does not clear the Phase 0 model gates.

