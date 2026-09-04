"""Source-aware fingerprinting for the ingested-store snapshot (B2-3 / 4b-hardening).

WHY THIS EXISTS
``run_archive_attach_resume.py`` pickles the ingested ``InMemoryMarketStore`` so a
restart costs seconds instead of a ten-minute re-ingest (task 4b). Reuse is guarded by a
corpus fingerprint: CSV count, total size, newest mtime, and the confirmed-actions hash.

That guard covers the *data* and misses the *code*. The snapshot is a pickle of live
Python objects, so it is only valid while the classes it was written from still have the
same shape. The existing guard carries a hand-written ``__version_note__`` string that
someone must remember to bump.

Task 4c rewrites ``InMemoryMarketStore``'s internals from per-bar Python objects to
contiguous arrays. If that lands and the note is not bumped, a stale pickle deserialises
into new class code and the run proceeds on silently wrong bars behind a valid-looking
``ca_table_hash``. A forgotten string edit is not an acceptable guard for that.

``store_source_hash()`` removes the human step: it hashes the source of the modules whose
classes the snapshot actually contains, so any edit to them invalidates the snapshot
automatically.

USAGE (one line in the resume driver's ``_corpus_fingerprint``)::

    from unidesk.momentum.data.store_fingerprint import store_source_hash
    return (len(files), total_size, round(newest_mtime, 0),
            confirmed_actions_content_hash(), store_source_hash())

FAILURE POLICY
If a module's source cannot be read, this raises rather than returning a placeholder. A
fingerprint that silently degrades to a constant is worse than no fingerprint: it would
match everything. Callers that want a slow-but-safe start should catch and re-ingest.
"""
from __future__ import annotations

import hashlib
import inspect
from typing import Iterable

from unidesk.contracts.base import ContractError

# Modules whose class definitions the pickled store actually embeds. Add to this list
# if the snapshot ever starts carrying another type.
_SNAPSHOT_MODULES = (
    "unidesk.momentum.data.market_store",
    "unidesk.contracts.market",
)


def _module_source(dotted: str) -> str:
    try:
        module = __import__(dotted, fromlist=["__name__"])
        return inspect.getsource(module)
    except Exception as exc:  # noqa: BLE001 - re-raised as a contract error below
        raise ContractError(
            f"store_source_hash cannot read source for {dotted!r}: {exc}. "
            "Refusing to emit a placeholder fingerprint -- a constant would match "
            "every snapshot and defeat the guard."
        ) from exc


def store_source_hash(modules: Iterable[str] = _SNAPSHOT_MODULES) -> str:
    """Stable 16-hex digest of the source of every module the snapshot embeds.

    Deterministic across runs for identical source. Changes the moment any of those
    modules changes -- which is exactly when a pickled store stops being trustworthy.
    """
    names = sorted(set(modules))
    if not names:
        raise ContractError("store_source_hash requires at least one module")
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_module_source(name).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def snapshot_modules() -> tuple[str, ...]:
    """The modules covered, so a caller can report what the guard actually watches."""
    return _SNAPSHOT_MODULES
