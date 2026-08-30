# UniDesk terminal — design system

Direction: **pit-lane cockpit at night.** Dark premium, one accent,
borders-only depth. Governed by
`plan/UNIFIED_DESK_UI_UX_MANUAL_V2.md` (repo root `plan/`) — V2 supersedes
the V1 manual in `Downloads/`. This file records the concrete values chosen
to satisfy that manual, not a restatement of it.

**Product shape (V2, 2026-08-29 pivot):** an evening desk, not a live
terminal — see `HANDOFF.md` for the full V1→V2 rationale. The direction
below (palette, tokens, signature widget) survived the pivot unchanged;
what changed is the screen set and the removal of live/pulse widgets.

## Domain grounding

- **Concepts:** NSE bhavcopy, AVWAP anchors, RS rank, RVOL/delivery ratio,
  contraction, lifecycle stages (BananaPatterns vocabulary), R-multiples,
  MFE/MAE, the honesty footer.
- **Color world:** graphite tarmac, oxidized copper/instrument-dial gold,
  brushed steel — not fintech teal/blue. Calm and reportorial, not a live
  trading-floor palette (V2 §1: "a quiet research desk at night").
- **Signature:** the "Ignition Stack" (`components/widgets/QualityStack.tsx`)
  — Stock/Setup/Entry fused into ONE bordered instrument with shared tick
  guides, a per-band fill-edge tick, and a single composite needle, not
  three separate progress bars. Reuse it, don't reinvent a metric display.
  Second-signature: the candidate scatter (`CandidateScatter.tsx`, entry ×
  stock, bubble = setup quality, color = lifecycle stage) — V2 §4 calls this
  "the product's signature visual after the Quality Stack."

## Tokens (`src/index.css`)

- **Surfaces (whisper-quiet elevation):** `surface-0` #0a0c10 canvas →
  `surface-1` #101318 card → `surface-2` #161a21 raised/hover →
  `surface-3` #1c212a popover. `surface-input` #0c0f13 (darker than
  surroundings — inset). Left rail = `surface-rail` = `surface-0`.
- **Borders:** `border-subtle` rgba(255,255,255,.06) · `border`
  rgba(255,255,255,.10) · `border-strong` .16 · `border-focus` amber .55.
  No shadows — borders do the elevation work.
- **Text (4 levels):** `ink-primary` #eef0f3 · `ink-secondary` #9aa2ad ·
  `ink-tertiary` #6b7280 · `ink-muted` #454b54.
- **Accent (one, used with intention):** `accent` #d89b4a copper/amber,
  `accent-strong` #f0b05f.
- **Semantic:** `positive` #3ecf8e · `warning` #e0a53d (amber — same family
  as accent, used ONLY for the warning semantic, e.g. the "played out"
  lifecycle chip) · `danger` #ef5350 · `neutral` #6b7280 · **`score-mid`**
  #7fa3c9 (cool blue) — the mid-tier score color AND the Chip `info` tone
  (e.g. "fresh breakout"). `score-mid`/`info` exists specifically so amber
  never has to carry two meanings at once (brand accent + warning semantic
  + "average score" all landing on the same hue was a real bug caught by
  review — see HANDOFF.md). Each semantic has a `-bg` (12% tint) and
  `-border` (30% tint) pair.
- **Setup-category tags** (`tag-burst/pivot/base/pullback/reversal`) — small
  dot + label in card headers only, never for status.
- **Type scale** (1.25 ratio off 14 base): `caption` 11 · `body` 14 ·
  `h4` 16 · `h3` 18 · `h2` 22 · `h1` 28 · `display` 44+. Numerics get
  `.font-mono-num` (tabular-nums) — never the sans face.
- **Spacing:** 4px base, multiples only. **Radius (concentric):** `chip` 6px
  · `card` 10px · `modal` 16px.

## Component patterns (reuse, don't reinvent)

- **QualityStack** — reads `useMode()` from `lib/ModeContext.tsx` itself by
  default (an explicit `mode` prop overrides). Do NOT reintroduce a
  caller-supplied-only mode prop — that was a real bug (Pro mode silently
  didn't reach the Decision panel because `DecisionCard` forgot to thread
  it through). `size="compact"` on cards, `size="full"` on the Decision
  Card.
- **CandidateCard** (`widgets/CandidateCard.tsx`) — the manual V2 §3 card
  shape: symbol/close/setup, QualityStack, lifecycle chip, one-line "why",
  trigger/invalidation pair. `dataSource: "illustrative"` candidates render
  with a dashed border + a visible "Illustrative" label — never silently
  blend fixture demo data with real scan output (see fixtures.ts header).
- **Chip** — `tone` prop drives color (`positive/warning/danger/neutral/
  accent/info`). `dot`/`pulse` for live-state badges only.
- **ScrollRail** (`ui/ScrollRail.tsx`) — wraps horizontal card rails; only
  applies the edge fade when the rail actually overflows (checks
  `scrollWidth - clientWidth - scrollLeft`). A fade on a fully-visible row
  falsely implies more content — don't apply `.scroll-fade-x` unconditionally.
- **DecisionCard / SetupEvidencePanel / ContributorBars** — the V2 §5.3–5.4
  Decision-panel decomposition. Every score must trace to a contributor bar
  or a named-number row; don't add an opaque composite without one.

## Status labels (single source of truth)

`src/lib/status.ts` — `LIFECYCLE_META` (forming/fresh_breakout/climbing/
played_out → label+tone) and `scoreColor`/`scoreTone` (score bands, mid-tier
is `score-mid` blue, NOT warning-amber). `toneColor(tone)` is the one
tone→CSS-var lookup; don't duplicate it locally in a component (duplication
across `TriggerRing`/`Home.tsx` was a real finding in the V1 pass — V2 killed
those files, but keep using the shared helper for anything new).

## What's still a default / open

- Chart library: `lightweight-charts` v5, used in `StockChart.tsx` — candles
  + EMA21/EMA50 + one AVWAP + trigger/invalidation price lines. Base-box
  (VCP geometry) overlay from manual §5.2 is NOT implemented — honest gap.
- No light theme — dark-only, matches the manual's "quiet research desk at
  night."
- Bundle is ~800KB unminified-adjacent (lightweight-charts + recharts) —
  fine for a prototype, would want route-level code-splitting before this
  became a real deploy target.
