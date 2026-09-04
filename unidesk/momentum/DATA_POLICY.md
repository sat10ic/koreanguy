# Momentum offline data policy

This package is a storage-neutral, offline core.  The owner must explicitly
choose the persistent adapter, storage home, and sole writer before any
persistent implementation is added.

- Symbols are trimmed and uppercased local identifiers matching
  `[A-Z0-9][A-Z0-9._&-]{0,31}`. (Amended 2026-08-29: `&` added —
  M&M and similar real, liquid NSE tickers were rejected by the original
  charset; amendment surfaced by the first real bhavcopy ingestion.) Exchange/provider prefixes and wire vocabulary
  are rejected rather than guessed.
- A classification is a half-open effective interval and has `available_at`.
  Queries see only versions effective and available at their timezone-aware
  `as_of`; later corrections never leak backwards.
- Daily bars are EOD observations. Their `available_at` is the publication
  time, so a same-session pre-close or pre-publication query must not see them.
  Intraday `ts` is completed-bar time and it too must be no later than `as_of`.
- `(symbol, observation time/session, data_version)` duplicates fail. Distinct
  versions may coexist, and the latest `available_at <= as_of` resolves each
  observation deterministically. Equal availability revisions fail as
  ambiguous.
- Missing delivery, circuit, and surveillance information remains `None`.
  `surveillance_state=()` is distinct from `None`: it records an explicit
  no-flags response. No missing value is converted to zero, false, or an
  inferred default.
- **EOD archive home (D15).** Historical bars are ingested from
  `data/bhavcopy/` (the downloader's target). `bhavcopy_extractor/data/bhavcopy/`
  is a stale subset and is not the ingest default.
- **Corporate-action adjustment.** Raw bhavcopy bars are never rewritten.
  Confirmed actions live in `unidesk/config/confirmed_actions.csv` (seed)
  and are applied as a derived OHLC/volume view at scan time. Detection
  never auto-adjusts. Announcements without ratios cannot confirm a factor.
  Official NSE CA feed is still open; the seed is four close-to-close 2:1
  confirmations (ANANDRATHI, BEML, AGIIL, ANUHPHR).
- **Industry map overlay.** Chartsmaze is the primary symbol→industry table.
  `manas_os/data/nexus_industry_map.csv` is a read-only fill for names
  Chartsmaze never mapped. On overlap, Chartsmaze wins — the two taxonomies
  disagree and must not be mixed for the same symbol. `source_tier` records
  which row came from where.
- **Delivery lag (D14 / Phase 0 spec §14.2).** Until a 20-session
  first-seen availability ledger exists, delivery printed for session T is
  usable only for a decision on session T+1 or later. Same-session 15:30
  use is forbidden even when `DELIV_PER` is already on the bhavcopy row.
  See `unidesk/research/delivery_lag.py`.
