# UniDesk data-authority map

Status: canonical U-P0.1 inventory. Observed 2026-08-29. The machine-readable
source is `unidesk/design/DATA_AUTHORITY.json`; `unidesk/run_checks.py` validates
its ownership, classification, lifecycle quarantine, and field-authority rules.

## What the classifications mean

The classification is always relative to the unified desk:

- **accepted** — eligible as evidence or input with its stated provenance;
- **provisional** — visible for research or fixture work, but blocked from a
  production decision until its named gate passes;
- **quarantined** — retained for audit and excluded by default;
- **archive-only** — backup, scratch, experiment, browser state, or retired
  output that is never a unified runtime input.

An accepted post is evidence that the post was captured. It is not an accepted
trade claim. An active database in another product can still be archive-only to
UniDesk because that other product, not UniDesk, owns its writes.

## Canonical field decisions

| Unified field | Current authority | State | Boundary |
|---|---|---|---|
| Daily OHLCV + delivery | TraderLog shared-core projection, sourced from raw NSE bhavcopy | accepted input | data-home/sole-writer relocation is still an owner decision |
| XP/MBI regime | TraderLog `regime_daily` | accepted input | Manas/legacy regime copies do not compete |
| Reactor Scale activity | TraderLog `alpha_activity_signals` | accepted input | participation context only; never identity, direction, or risk |
| Social source evidence | TraderLog posts + media archive | accepted evidence | extracted meaning remains provisional until reviewed |
| Social claims | TraderLog Lite claims/links | provisional | zero rows observed; only accepted review-state rows may project |
| Trader lifecycle | none yet | unresolved | future accepted-claims projection; legacy rows need migration review |
| Intraday quote/depth | OrderFlow raw recorder | provisional | owner live-session and recorder gates still open |
| OrderFlow capability | `orderflow/capability.json` | provisional | synthetic today; cannot promote fast features |
| ChartsMaze context | `chartsmaze_extractor/state/**` | provisional | capture date/freshness/validation required |
| Symbol master | none yet | unresolved | freeze with U-P0.3 data-home decision |
| Point-in-time market store | none yet | unresolved | owner chooses home + sole writer before implementation |

## TraderLog lifecycle quarantine

The production database was opened read-only for this audit.

| Class | Positions | Events | UniDesk rule |
|---|---:|---:|---|
| Current TraderLog accepted predicate | 18 | 12 | migration candidates only; source evidence still required |
| Deterministic reconciler quarantine | 305 | 436 | never project; never bypass `accepted_lifecycle_where()` |
| Claims / claim links | 0 / 0 | — | no canonical Lite lifecycle exists yet |
| DB backups/staging | 45 files, 7,622,328,320 bytes | — | archive-only; never runtime |

This is the load-bearing distinction: the 305 deterministic positions are
retained evidence of a failed derivation, not trades. A future UniDesk lifecycle
must originate from accepted claims and accepted links, not from time proximity,
market-price inference, a database backup, or a model's unreviewed output.

## Package and store ownership summary

| Store family | Sole owner/writer | UniDesk class |
|---|---|---|
| `bhavcopy_extractor/data/**` | bhavcopy downloader | accepted raw source |
| `chartsmaze_extractor/state/**` | ChartsMaze extractor/cron | provisional |
| TraderLog production DB + raw/media | table writers in `traderlog/CANONICAL.md` section 6 | mixed by logical table/subset; exact split in JSON manifest |
| Manas OS live DB | `manas run-eod` + table-specific stages | archive-only to UniDesk; reference/adoption source only |
| Manas research/backtest DBs | Manas import/backtest scripts | archive-only |
| root SwingEdge stores/outputs | root pipeline scripts | archive-only; observed core DBs are zero-byte stubs |
| `SwingEdge/data/chartsmaze/**` | historical SwingEdge jobs | archive-only; superseded extractor path |
| `legacy/**` | no UniDesk writer | archive-only; adopt by copy, never import |
| `orderflow/capability.json` | capability auditor | provisional/synthetic |
| `data/orderflow/**` (raw JSONL tees + partitioned parquet under `data/orderflow/parquet/`, git-ignored) | continuous recorder through Parquet writer | provisional until live acceptance |
| `unidesk/STATE.json` | UniDesk checks runner | accepted governance state |
| package model-work ledgers | completing package sessions, append-only | accepted provenance |

## External inputs and APIs

| Input | Use | Authority rule |
|---|---|---|
| NSE bhavcopy | EOD price, volume, delivery | accepted raw source; missing dates remain missing |
| FYERS REST/WebSocket | intraday quote/depth and capability measurement | provisional until owner-run live evidence; no order routing |
| ChartsMaze | sector/screener/disclosure context | vendor-derived and freshness-gated |
| X capture through TraderLog | public social evidence | archive exact source; inference remains reviewable/provisional |
| Telegram | outbound notification only | never a market-data or decision authority |

Owner credentials are not a persistent data store. They were not read, copied,
validated by value, or included in the manifest.

## Reuse, copy, retire

- **Reuse as inputs:** TraderLog shared-core market projections and evidence
  archive, through explicit point-in-time/provenance boundaries.
- **Copy with provenance when needed:** pure metrics from existing packages;
  never import across TraderLog/Manas/legacy boundaries.
- **Retire from the unified path:** Manas trading-desk/ML/positions outputs,
  root SwingEdge state, SwingEdge snapshot copies, and all legacy runtimes.
- **Build in place:** OrderFlow remains the sole intraday quote/depth owner;
  UniDesk owns contracts, decision integration, research state, and UI—not a
  competing feed recorder.

## Open owner decision

U-P0.3 still needs one explicit choice: the point-in-time market-store home and
its sole writer. Until then, the TraderLog shared core is the accepted read-only
input and no new package may duplicate those fields.

No production data was modified during this audit.
