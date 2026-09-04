# User ask — plain explainers + discovery miss (2026-07-15)

Two standing requirements, restated with fresh evidence (4 practitioner picks screenshotted).

## 1. DISCOVERY MISS (recurring — see memory `feedback-filters-miss-arora-stocks`)
"Again, good stocks are not being picked up by the tool." Standing rule: **discovery
sensitivity BEFORE refusal strictness**; validate against practitioner picks; use dynamic
ADR-relative thresholds, not fixed ones.

Validation cases (add to `data/labels/practitioner_picks.csv`, diagnose why each is missed):
| Ticker | NSE symbol | Setup (per poster) | Note |
|---|---|---|---|
| Fineotex Chemical | FCL | VCP base breakout, ~+6%, showing urgency | con: 10% circuit limit |
| Raymond Realty | RAYMONDREL | base-on-base, held through market weakness, continuation breakout | "supply is now demand" |
| Divi's Laboratories | DIVISLAB | rectangular consolidation breakout | large-cap, weekly |
| JNK India | JNKINDIA | gap-up continuation from a rising base | +2.5% gap day |

Done-test: each ticker either APPEARS in the scan/shortlist, OR the tool names the SPECIFIC
gate that dropped it + why (and whether that drop is defensible vs a false-negative). If dropped
by a fixed threshold a practitioner setup should pass, that threshold is the bug.

## 2. PLAIN ENTER/EXIT EXPLAINERS (new feature)
User wants short, human explainers per setup — the situation in plain words, like the tweets:
- "Initial signs are here. Up ~6% now and starting to show urgency. Only con is the 10% circuit limit. Watching how it builds."
- "Textbook base-on-base. Held up well through broader market weakness. Interested in the continuation breakout again."
- "Rectangular consolidation breakout. Long at CMP, 8% stop, target 9200 in 9m-1y."

Requirement: each setup/position card carries a 2-4 line plain-English read covering the
SITUATION + what to do (enter / wait / exit / stop), in a trader's voice, grounded in the
card's actual computed fields (never generic filler, never invented numbers). Enter AND exit
states both get copy (the exit/coach side is where beginners fail).

UX-copy reference repos (user-supplied): 
- https://github.com/marvinrez/ux-wise-agent
- https://github.com/appariciojunior/website-audit-skill

## Constraint
Copy must be GROUNDED (trace to real card fields), setup-type-specific (VCP vs base-on-base vs
rectangular vs gap-continuation read differently), and honest (circuit-limit / extension / thin-
volume cons stated, like the posters do). No hype. Fits the simplification mandate: the explainer
IS the front-door value — plain words over dials.
