"""Unified desk — governance, contracts and integration layer.

Adopted 2026-08-28 per plan/UNIFIED_DESK_BUILD_MANUAL.md. The manual's
``desk/`` layout maps to ``unidesk/`` (DECISIONS.md D2). Boundary rules:

* ``unidesk`` may import ``orderflow`` (one-way, D4). ``orderflow`` imports
  nothing cross-project, and neither ever imports ``traderlog`` or
  ``manas_os`` — adopt by copying with a provenance header instead.
* No order routing, no credential handling, anywhere (unified R3).
* Contracts here are schema-only until Phases 1-3 produce real data; nulls
  stay null, unknown enums fail closed (unified R12).
"""
