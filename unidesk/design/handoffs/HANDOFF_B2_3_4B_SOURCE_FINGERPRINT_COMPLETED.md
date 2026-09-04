# Completion — B2-3 / 4b automatic snapshot source fingerprint

**Date:** 2026-09-04  
**Scope:** snapshot invalidation guard only; applied while the existing B2-3
worker continued on already-loaded code.

Attribution-ID: attr-unidesk-b23-4b-source-fingerprint-codex-20260904-001

## Change

`run_archive_attach_resume._corpus_fingerprint()` now includes
`store_source_hash()` rather than a manually maintained version-note digest.
The guard covers the source modules embedded in the pickled market store. A
future store-internal change therefore forces safe re-ingestion rather than
silently deserialising a snapshot under incompatible class code.

## Verification

```text
.venv-orderflow\Scripts\python.exe -m pytest unidesk\tests\test_store_equivalence.py -q
2 passed, 2 skipped
```

The temporary, immediately reverted source probe changed the guard from
`083c28ebd0921ec1` to `22bb00d2f8defac0`; after restoration it returned to
`083c28ebd0921ec1`. No B2-3 archive content, worker process, or snapshot was
read or modified by that probe.

## Limitations

- The active worker retains its old already-loaded fingerprint until it exits;
  this change takes effect only on a subsequent restart, which is the intended
  safe boundary.
- The heavy fresh-ingest-versus-snapshot equivalence tests, profiler, columnar
  refactor, and sample diff remain blocked behind the live worker's memory use.
