# UX panel audit — user's-eye view (2026-09-02)

Attribution-ID: attr-unidesk-audit-foolproof-a02-glm53flash-20260902-001

This audit also delivered: the foolproofing layer (desk self-checks panel,
register guardrails, truthful stale marking, jargon glosses) and the A-02
L1.5 exploration prototype (`research/analogue.py` + 11 constraint tests,
research-only per design/AI_INTEGRATION_EXPLORATION_A02.md).

**Scope:** every screen, panel by panel, card by card — what the user sees,
whether the data is accurate / current / present, how much jargon it carries,
and whether the panel is foolproof without LLM help. Fixes applied in this
pass are marked ✅; items that need backend data are marked ⛔ with the
named field (never faked in the UI, per spec §0.1).

Reference: preservation of Claude's thrust wave is documented separately in
`PRESERVATION_MANIFEST_CLAUDE_THRUST_2026-09-02.md`.

---

## Shell (all screens)

| Item | Finding | Action |
|---|---|---|
| Theme | Was dark-only; owner asked for a **light terminal** | ✅ Light is now the default; dark is a one-click toggle in the top bar, persisted. No dark flash on load. |
| Sidebar | Icon-only rail did not match the spec (§4.2 text-primary) | ✅ 208px expanded / 64px collapsed, text labels, persisted collapse, Stock removed from nav (contextual), Market added. |
| Session date | "stale" flag showed on the newest completed session at night (compared against *today*, not the newest session) | ✅ Stale now means "older than the newest bundled session"; at 2am yesterday's report reads current, correctly. |
| Data status | No self-verification visible anywhere | ✅ Data Quality drawer now ends with **Desk self-checks — n/n passing** (7 published invariants: prices match bhavcopy to the paisa, funnel nests, every candidate traded today, no hard-coded market numbers, no fabricated rows, outcome labels current, scores vary). One flagged item (setup-quality DEGENERATE) is shown honestly, not hidden. |
| Beginner/Pro | Toggle existed; several screens ignored it | ✅ Every screen now has at least one mode-differentiated element. |

## Tonight

| Panel | Finding | Action |
|---|---|---|
| Market State hero | Regime verbatim; engineering token `breadth_only` visible in Beginner | ✅ Beginner now reads "CHOP (breadth 50.0% above EMA50)"; Pro keeps the verbatim note incl. classifier-source. |
| 20-session strip | Stored classifications exist only from Aug 28 | ✅ Honest: stored label where the classifier was live, labelled R0 replay elsewhere, tooltip discloses which. |
| Market participation | 1D/5D were "—"; denominator invisible | ✅ Real 1D AND 5D deltas from the 43-session archive (e.g. EMA50 ↓4.9pp 1D, ↓6.1pp 5D); tooltips now give numerator/denominator in plain words ("560 of 1,163 scanned stocks above their long-term trend average"). |
| Opportunity funnel | Was absent | ✅ Real counts, each step's definition in its tooltip. ⛔ Per-symbol gate reasons are not logged backend-side (aggregate counts only). |
| Breadth analytics | BO/BD jargon | ✅ Plain labels ("New highs vs lows", "Volume vs normal", "Breakouts vs breakdowns") with definitions on hover. |
| Setup feed rows | No chart context before | ✅ Real 40-session mini-candles with trigger line; Beginner shows "Top 9% of market / high volume" instead of raw RS/RVOL; ADR column glossed. |
| Prior calls | Three states only; the newest sessions showed nothing (outcomes lag 10 bars) | ✅ Now five states (won / stopped / active / flat / no data) matching the exporter's finer labels; a plain caption explains outcomes need 10 future sessions. |
| Trigger proximity | Same amber dot for every state; no drift | ✅ Four groups (at trigger / approaching / getting late / far), prior→now distance with approaching/extending tag, sub-1R flagged, quality as a letter grade. |

## Market

| Panel | Finding | Action |
|---|---|---|
| Breadth history | Absent | ✅ Real line over 43 archived sessions + regime dots. |
| Market character | Absent | ✅ Rule-derived descriptor (documented thresholds, labelled heuristic). |
| Sector table | Sector data was "not in export" | ✅ Candidates-by-sector from the Chartsmaze vendor mapping (provenance disclosed). ⛔ Market-wide per-sector breadth needs a universe-level sector join (backend). |

## Candidates

| Panel | Finding | Action |
|---|---|---|
| Landscape | The scatter was degenerate: setup quality is 100 for nearly all candidates tonight, so every dot sat on one line, and auto-zoom magnified it | ✅ Fixed geometry (0–100 domains, quadrant midlines at 50, tinted PRIME zone, top-3 names permanently labelled, bubble = RS, colour = state) AND an explicit warning when an axis carries no variation ("setup quality is 100 for all plotted candidates — differentiation is on Entry quality"). Claude's invariant `scores_have_variance` flags the same degeneracy in the backend. ⛔ The degenerate score itself is a detector-scoring question for the owner (inside_bar passes all rules → 100). |
| Research lens | Absent | ✅ Regime priority chips (RS / volume / tightness / entry precision in CHOP), labelled "UI emphasis only — not validated weighting". |
| Ranked table | No change-over-time, no sector | ✅ RS Δ1D column (real prior-session rank), RS 10-day trend sparkline, sector column (vendor mapping), all hideable. |
| Accumulation | Static single number | ✅ SMF-style temporal table: NOW / PREV / 5D avg / 10D avg / streak / 10-day trend from 10 archived sessions. ⛔ Bulk/block deals absent (no source). |
| Presets | — | ✅ (prior wave) Inclusions plus named exclusion rules per candidate. |

## Stock

| Panel | Finding | Action |
|---|---|---|
| Context ribbon | Regime ambiguity | ✅ MARKET / SECTOR (vendor, provenance in tooltip) / THIS STOCK — never a bare "Regime:". |
| Verdict (Beginner) | Scores led; user had to combine four systems | ✅ Verdict first with WHY (Excellent/Good/Fair/Poor at documented 75/60/45 bands), distance-to-breakout, reward-vs-risk, tightening — then scores. |
| Raw metrics (Pro) | Missing thrust features | ✅ Claude's ADRMAX / Chop score / stop-in-thrust-days surfaced with provenance footnote. |
| Chart | — | ✅ Real bars only; loud banner + levels table when no real history. |
| Base structure | — | ✅ From the clean-room episode; markers show occurred-at AND confirmed-at. |
| D-08 warning | Stale window | ✅ Now uses the per-session snapshot (bars through 09-01). |

## Desk

| Panel | Finding | Action |
|---|---|---|
| Veto | — | ✅ Four outcomes, names the last print for dead symbols. |
| Register | Blind input | ✅ Deterministic guardrails: invalidation ≥ entry, size > stated capital, future-dated entry — each warns inline before recording. |
| Size evidence | — | ✅ Bucket occupancy from the broker import + quoted audited notes; explicitly never suggests a size. |
| Calls vs trades | Mostly "no report for that session" | Honest: the report archive starts 2026-07; most trades predate it. Grows as archives accumulate. |

## History

| Panel | Finding | Action |
|---|---|---|
| Outcome states | Old export could not distinguish open from won | ✅ Claude's exporter fix (OPEN = horizon not elapsed; FLAT = resolved without reaching 1R) is now rendered: five states, five collapsible groups, corrected strip. |
| Scorecard | — | ✅ n shown beside every figure, low-sample flagged. |
| Coverage | Stale coverage snapshot (396 partitions vs 1,570 now) | ✅ research_coverage + settings exports refreshed to the 09-01 session and made auto-discovering. |

## Research / Settings

- Settings: ✅ now reads the 2026-09-01 frozen-config snapshot (auto-discovered).
- Research: ✅ archive coverage now live from the refreshed export; equity curve remains GROSS-labelled (net-of-cost still not on disk).

## Cross-cutting foolproofing (no LLM needed)

1. **Desk self-checks** visible in the Data Quality drawer (7 invariants with measured detail).
2. **Deterministic input guardrails** on the positions register.
3. **Stale marking** is now truthful (newest-session-relative).
4. **Every aggregate carries n**; every missing field reads "—" with the backend requirement named in Pro/diagnostics.
5. Remaining recommendations (not built): scheduled nightly refresh (one command exists: `unidesk/run_desk_refresh.py`); attach-outcomes scheduling so recent sessions resolve automatically; per-symbol gate-reason logging for the veto; universe-level sector joins.

## Still missing (backend fields — named, not faked)

⛔ sector breadth per scanned universe · ⛔ themes · ⛔ earnings dates · ⛔ ASM/GSM flags · ⛔ bulk/block deals · ⛔ market-quality composite (0-100) · ⛔ per-symbol gate refusal reasons · ⛔ net-of-cost per trade · ⛔ historical expectancy / similar-setups (Phase 0 + N5 gated).
