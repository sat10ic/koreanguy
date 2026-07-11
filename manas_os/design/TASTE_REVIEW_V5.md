# TASTE REVIEW — current Manas OS desk (taste-skill/redesign audit, 2026-07-11)

Applied the `redesign-existing-projects` audit + the `interface-design` "Avoid" list to the
current desk (HEAD `bd24e29f`, verified via the UI-0 rendered baseline in
`UI_OVERHAUL_HANDOFF.md` §9). Marketing-only audit items (John-Doe copy, pricing towers,
testimonial carousels, hero photos, footer link farms) are DROPPED — this is a data workbench.
This is the review the user ordered before the UI-1 rebuild; it feeds the rebuild's fix list.

## The AI-tells this UI actually exhibits (ranked by how much they cheapen it)

| # | Generic/AI pattern present | Evidence in our build | Targeted fix |
|---|---|---|---|
| 1 | **Uniform generic card = border + shadow + same bg everywhere** | ~103 `.panel`, one base rule gives every section identical bg/border/radius/shadow/padding (§9). DEBATE renders 15 of them. | A card exists ONLY when elevation communicates hierarchy or it's the real interactive object (candidate/position/saved-scan). Replace the rest with cardless rails/bands/tables + tonal shift. |
| 2 | **Only 400/700 weights; size-only hierarchy** | flat hierarchy, MARKET has 1 heading; "everything one size/weight" | Three levers together (size+weight+color): 600/primary value · 500/secondary label · 400/muted meta. Add 500 + 600. |
| 3 | **Mono used for prose/status/nav** | ~239 mono refs; mono is the texture of the whole UI | JetBrains Mono ONLY for numbers/time/R/qty/tabular evidence. Inter for prose/controls. |
| 4 | **All-caps small-caps labels + literal `[B]`/`[E]` everywhere** | 35 `[B]` markers, pervasive ALL-CAPS section labels | Replace `[B]`/`[E]` with plain "Why this matters" / "Evidence & method". Vary label treatment (sentence case, tracked small-caps sparingly), not all-caps-everything. |
| 5 | **Browser-default type; headlines lack presence** | Helvetica/Segoe + mono, MANAS is 15px, no display face | Bundle **Barlow Condensed** (verdicts/masthead/mechanism names) — heavy, tight tracking, intentional. Inter body. Numbers mono. |
| 6 | **Faint text below the readability bar** | `#666` on `#141414` ≈ 3.21:1, used at 10-11px for essential copy | No essential copy below WCAG-AA. Raise muted-text lightness; 14px min prose. (vercel `web-design-guidelines` gate catches this per-line.) |
| 7 | **Uniform border-radius on everything** | one radius across panels/inputs/chips | Radius scale: tight inputs/buttons, medium cards, large modals. Concentric nesting (`outer = inner + padding`). |
| 8 | **Missing whitespace / monotone density** | "compact terminal", same gap/density everywhere (§9) | Spatial rhythm: group tightly-related, real air between groups. One focal point per view ringed in space. 60/30/10 color distribution. |
| 9 | **`window.prompt()` / native dialogs for edits** | position SL/qty edits + shortlist-remove reason use `window.prompt` | Inline editing or slide-over sheet with real validation + error states; never native prompt/alert. |
| 10 | **Full-surface `Loading…` erases confirmed data** | multiple tabs replace the whole surface | Skeletons that match layout shape; keep last confirmed data visible while refetching. |
| 11 | **Flat, zero-texture surfaces** | pure flat `#141414`, sterile | Our art direction WANTS newsprint — add a very subtle grain/tint to the canvas (restrained), tinted shadows to the bg hue, not pure-black low-opacity. |
| 12 | **Icon-left-big-number-small-label metric boxes** (the generic metric grammar) | metric tiles in this exact shape | Infinite-expression: verdict-on-annotated-sparkline (our signature), inline stat, delta badge, gauge — not the same box each time. |
| 13 | **No always-on active-nav / weak state feedback; div-soup semantics** | 9 real headings, panel-div heavy | Semantic `<nav>/<main>/<section>`, real headings, clear active-nav, hover/active/focus on every control. |

## What is NOT a tell here (don't "fix" these — they're correct)
- No purple/blue AI-gradient — the palette is already neutral-charcoal (good; keep it).
- Multiple accents (cyan/amber/green/red) are SEMANTIC (live-state / caution / market-outcome), not decoration — defensible; keep, but hold cyan to live-state only (scarce).
- Honest "0 actionable" zero state + honest empty equity curve — KEEP; do not decorate into fake opportunity.
- Deterministic risk = display-only server values — KEEP; never invent stop/target/qty in the UI.

## Dial read (taste-skill VARIANCE / MOTION / DENSITY, retargeted for a data workbench)
- **VARIANCE: low-medium.** This is an evidence tool — restraint over expressiveness; one signature (annotated-price verdict), not decorative variety.
- **MOTION: low.** Motion marks a real change once, then holds. Never animate P&L/stop/target/verdict. Pipeline fill + status-change pulses only.
- **DENSITY: medium-high but RHYTHMIC.** It's a trading desk — dense is right, but grouped with real air between groups, not monotone. Not a brochure; not a parking lot.

## Feeds into
`DESIGN_SYSTEM_V5.md` (domain exploration + tokens) and the UI-1 build. The fixes above are the
concrete anti-default checklist the rebuild is verified against (swap/squint/signature/token
tests + the `web-design-guidelines` a11y gate). Items 1, 2, 3, 5, 8, 12 are the highest-leverage
— they're what make it read "designed" vs "generated".
