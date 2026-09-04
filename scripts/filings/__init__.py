"""FilingsEdge — filings-intelligence catalyst layer for SwingIntel.

Implements the M1-M8 pipeline from FilingsEdge_Handoff_Spec.md, adapted to
REUSE the existing SwingEdge infrastructure (scripts.analyst for the LLM,
scripts.notify for Telegram, scripts._db conventions for SQLite).

Modules (each independently runnable with --date YYYY-MM-DD for backfills):
  m1_ingest_bhavcopy      — UDiFF bhavcopy + delivery -> prices
  m1_ingest_announcements — NSE/BSE announcements -> announcements_raw
  m1_ingest_deals         — bulk/block deals -> bulk_block_deals
  m1_ingest_surveillance  — ASM/GSM lists -> surveillance
  m2_extract              — LLM classification of announcements -> events
  m3_features             — deterministic feature battery -> features
  m4_crossref             — material events ⋈ technical watchlist -> candidates
  m5_veto                 — pledge/ASM/delivery/pump checks + risk memo
  m6_alert                — Telegram digest + health message
  m7_orchestrator         — plain driver calling M1->M6 with retries
  m8_outcomes             — 5/10/20-day forward returns backfill

Design principles (handoff spec §2):
  - raw files are immutable (inbox pattern: data/inbox/YYYY-MM-DD/)
  - LLM touches text only, never arithmetic
  - every stage independently runnable
  - human executes all trades (analysis-side only — stays outside SEBI algo
    framework)
"""
