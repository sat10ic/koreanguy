# Design note — incremental split-candidate detection (B2-3 continuation step 5)

**Rule under analysis** (paused handoff, Target 2): *"Before any cache implementation,
write whether appending one bar can alter historical candidate detection; a symbol-only
memo is forbidden."*

## Measured cost being addressed

`detect_split_candidates_bars` cumtime **220s** over the 3-session profile run
(16,243 calls — the CA candidate scan re-runs inside every per-session `scan_universe`
over each symbol's full history), plus `scan_store_for_splits` 44.8s and the same work
again inside `build_future_map` 28s. At the observed rate this is ~70s per session that
scales with corpus length, not with new data.

## Dependency analysis (why appending is safe)

`detect_split_candidates` scans `i` in `1..n-1` and flags a candidate at `i` using ONLY:

- `closes[i-1]` (the gap reference),
- `opens[i]` (the gap print and implied factor),
- `volumes[i]`, `volumes[i-1]` (the `min_post_volume` continuity test).

Every input is local to bars `i-1` and `i`. Therefore, for an APPEND-ONLY series:

```
candidates(prefix L+1) = candidates(prefix L) ∪ candidates(new indices L-1 .. L+1-1)
```

Appending one bar (or k bars) can add candidates only at the appended indices; no
historical flag can appear, disappear, or move, because no historical flag reads any bar
at or after index `i`. **Historical candidate detection is append-stable.** The forbidden
symbol-only memo is unsafe for a different reason: it ignores the prefix boundary. A
memo keyed `(symbol, prefix_length)` holding the candidate list is sound *only* if the
detection restarts at `prefix_length - 1` (the boundary candidate reads `closes[p-1]`,
which existed before, plus the new bars).

## The one genuine invalidation: insertions

The property fails if a bar is INSERTED into the middle of a symbol's history (a
backfilled session): every subsequent index shifts and the shifted bar's `closes[i-1]`
reference now points at the inserted bar. Within one resume run the store is immutable
(one ingest, one corpus fingerprint), so insertions cannot occur mid-run; across runs the
corpus fingerprint (file count/sizes/mtimes) already invalidates all cached state. Rule:
**the memo lives inside a single run only, keyed `(symbol, prefix_length)`, and is never
persisted.**

## Proposed design (Target 2 — NOT implemented; awaits owner go after Target-1 report)

Per run: `{symbol: (processed_len, candidates_tail_list)}`. On each scan of symbol S at
prefix length L ≥ processed_len: run the detector loop over indices
`[processed_len - 1, L)` of the FULL series (the boundary index re-reads the last
pre-existing bar for its `i-1` references), append the new candidates, update the memo.
`detect_split_candidates` gains an optional `start_index` (default 1) — the loop body is
unchanged, so output is byte-identical by construction, provable by asserting
`incremental(L) == full(L)` for random prefixes in the existing split tests.

Expected effect: removes ~70s/session of repeated full-history detection from the
remaining 149-session resume (≈ 3h saved) and from every future archive pass.

## Non-goals / guards

- No ratio inference, no auto-confirmation (owner constraint, unchanged).
- The same memo MUST NOT be shared with `build_future_map` unless its own call pattern is
  verified append-identical — measured first, not assumed.
- If the store ever becomes insert-capable, this memo design is void and must be
  re-derived (the fingerprint gate makes stale reuse impossible).
