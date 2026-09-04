# HANDOFF — Update feedback + Fyers re-auth UI + honest freshness (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Fixes three real bugs found live 2026-07-14 (user: "tool stuck at 07-10, update does nothing, no
way to update Fyers auth"). NONE is a Fyers-blocks-EOD problem — diagnosis below.

## Diagnosis (verified, do not re-investigate)
- `daily_prices` advanced fine to 07-14 (bhavcopy ingests OK). But `regime_snapshots` +
  `scan_candidates` stayed at 07-10, so the desk's "data as of" froze at 07-10.
- Cause A: NSE EOD bhavcopy for a day publishes ~evening. Clicking "update" DURING the day finds no
  file → `ingest_bhavcopy` logs `skip: file not found` SILENTLY → nothing advances → looks broken.
- Cause B: when today's inputs aren't all ready, `scan_candidates` / debate / alerts **silently
  fall back to the last complete date** (07-10 / 07-07) and the UI shows that as if current — no
  "couldn't advance, here's why" message.
- Fyers: only skips `ingest_mars` (sector RS) + live/intraday. It does NOT block the EOD chain.
  BUT there is genuinely no UI to re-enter/refresh the Fyers token (it expires ~6am IST daily).

## Scope
### 1. Honest "update" feedback (the #1 fix)
The refresh/update button (`_run_pipeline_thread` / the pipeline-run endpoint, app.py ~L3350-3441)
must report a clear result, surfaced in the UI (reuse the UI-2 Live Work job events — this is
exactly what "watch it work" is for):
- If the target date's bhavcopy is not yet published: return/show
  `"NSE bhavcopy for <date> not out yet (usually ~7 PM IST). Latest complete session: <date>."`
  — NOT a silent skip. Detect: file-not-found on `ingest_bhavcopy` for a date that is today/after
  the latest file.
- Stream per-stage progress + the final "advanced to <date>" or "could not advance past <date>
  because <stage> <reason>". Never leave the button looking like it did nothing.
- If a source fetch is what's missing (e.g. the download step didn't run), say so and, if a
  download entrypoint exists, offer to run it; otherwise state the manual step.

### 2. No silent stale-fallback (honest freshness)
When the pipeline cannot advance the regime/scan chain to the requested/latest trading date, the
MARKET/guided-flow "Data" step must say so explicitly: `"Prices are at <priceDate> but the regime/
setups couldn't rebuild for it yet (<reason>) — showing last complete: <completeDate>."` The
current guided-flow "0 trading days behind" is WRONG when price date > regime date. Compute
"behind" from the REGIME/scan date vs latest trading day, and show the split (prices vs analysis)
when they differ. This is the one-opinion/honest-state rule — never render old analysis as current.

### 3. Fyers re-auth UI (the missing option the user asked for)
Backend has `fyers_auth` (used by `sources/fyers_provider.py` / mars / live). Add:
- `GET /api/fyers/status` → `{connected, token_valid, expires_hint, needs_reauth}` (read the
  existing auth module; do NOT print/log the token/secret).
- A re-auth flow that fits Fyers' OAuth: an endpoint that returns the Fyers login URL, and one that
  accepts the returned auth code and exchanges it for the token via the existing auth module
  (mirror how the CLI/`fyers_auth` already does it — reuse, don't reinvent). The USER pastes the
  auth code; the tool never asks for the raw password/secret in a field it stores.
- A desk card (shell status area or a small Settings/Connection panel): shows connected/expired +
  a "Re-authenticate Fyers" button that opens the login URL and a field to paste the redirect code.
  Prominent "auth needed" chip when the token is dead (the plan's architected failure state).
- SECURITY: credentials live only in gitignored `config.yaml`; never commit/echo them; the token
  file stays where `fyers_auth` puts it. This is display + a guided OAuth paste, not credential
  storage in the UI.

## Guardrails
No money-math touch. Real states only (no faking freshness). Additive endpoints. Secrets never
logged/committed/rendered. `.v5` tokens, a11y AA. pytest green + build + desk_gate.

## Output
`HANDOFF_GEMINI_update_fyers_freshness_COMPLETED.md`: the update-feedback contract + a real example
(update during-day = "not published yet"; update after-close = "advanced to <date>"), the
freshness split (prices vs analysis date) shown honestly, the Fyers status + re-auth flow (with a
real status read, token never exposed), tests.
