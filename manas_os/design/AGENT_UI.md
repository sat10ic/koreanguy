# AGENT_UI — the front-end for the agentic scanner ("a desk you watch, not panels you read")

Why the old UI failed (user verdict 0/10): static dashboard panels re-arranged nightly
numbers. Nothing HAPPENED on screen. The agentic system fixes this structurally — the tool
now has actors, arguments, decisions, and memory. The UI's job is to show the desk WORKING.

## Information architecture (replaces the 5-tab shell)
```
DESK        — the living home: activity stream + morning brief   (default tab)
DEBATE      — per-candidate debate theater
POSITIONS   — coach signals + open-position lifecycle
LEDGER      — agent track records + lessons diary + trade journal
(ChartDrawer stays as an overlay from any symbol click)
```

## 1. DESK — the living home
Two zones:
**Morning brief (top)** — one generated narrative block, the daily entry point:
"Last night the desk reviewed 14 names. The models agreed on 2 (SYRMA, KPIL), split 2-1 on
GABRIEL. Vision demoted SYRMA — 'base too loose, third-stage'. Sizer took KPIL at 0.75x
(SELECTIVE, heat 0.5/2.0%). One coach alert: HUDCO stop unchanged, wobble normal."
Data: composed from agent_verdicts + scan_agent_logs + coach output by one cheap LLM call
at the end of the nightly run; stored, not regenerated per view.
**Activity stream (below)** — reverse-chronological feed of desk events, each a one-liner
with timestamp + agent identity chip:
```
18:41  SIZER      2 picks sized · KPIL 0.75x (why: split debate, fresh regime)
18:39  VISION     demoted SYRMA — "base too loose" · promoted KPIL +1
18:36  GEMINI     disagrees on GABRIEL (2/5 vs DeepSeek 4/5) — disagreement flagged
18:33  DEEPSEEK   ranked 14 names · top: KPIL, SYRMA, GABRIEL
18:31  GATES      1,029 → 259 → 34 → 14 shortlist (regime SELECTIVE, day 6)
18:30  PIPELINE   data fresh through 2026-07-08 · all 16 stages ok
```
Every row expands to the underlying artifact (transcript, chart, plan). Events persist —
scrubbing back a week replays any past night. Data: scan_agent_logs + pipeline_runs +
agent_verdicts, one `/api/desk/feed?date=` endpoint.
**Live mode:** while the nightly run executes, the stream updates via polling (2s) or SSE —
rows appear as stages/agent calls complete, with a subtle "DeepSeek is reading 14 charts…"
typing indicator on in-flight calls (scan_agent_logs row exists but latency null). If the
user isn't watching, nothing is lost — the same feed renders from persistence.

## 2. DEBATE — the theater
Per candidate (top-ranked first):
- **Header**: symbol + lens tag (STRONG START / EP / IPO / HTF / PEAD) + chair verdict +
  conviction meter (the 2-3 models' convictions as stacked dots, disagreement gap
  highlighted — a 5v2 split renders as tension, because it IS signal).
- **Two columns**: BULL (each model's bull_case, attributed) | BEAR (bear cases). The
  disagreeing model's argument gets visual weight, not buried.
- **Vision strip**: the actual daily+weekly chart PNGs the vision agent saw, its verdict
  stamped on them ("pivot clean, volume dry-up ✓ — promote").
- **Plan block**: entry/stop/target/qty from the deterministic engine (labeled "math:
  engine" to keep authorship honest) + sizer multiplier with its reasoning.
- **Footer**: this lens×regime base rate (from setup_expectancy) + each model's own track
  record chip on this lens ("DeepSeek on EP: 5/9 hits").

## 3. POSITIONS — the coach on duty
- Open positions as lifecycle cards: entry→now R-path sparkline with phase bands
  (INITIATION/TREND/EXTENSION), trail stop line, coach's latest instruction as the
  headline ("HOLD — wobble normal until 892 breaks").
- The coach QUOTES THE ORIGINAL THESIS on every update: "Entry thesis (DeepSeek, Jul 8):
  'quiet base + delivery surge'. Still intact — delivery holding, base low untouched."
  The position remembers why it exists. That continuity is what static tools never had.
- Telegram mirror: every signal sent renders here too, with sent-status.

## 4. LEDGER — memory made visible
- **Agent track records**: per agent × lens × regime — hit rate, avg R, n, trend arrow.
  Agents visibly earn/lose credibility; the chair's merge weights can cite these numbers.
  ("Gemini's disagreements were right 7 of 9 times — its dissent now reads louder.")
- **Lessons diary**: the lessons/*.md stream rendered as a journal the desk keeps —
  newest first, tagged right-process-loss / wrong-process-win / clean-hit / clean-miss.
  The user watches the system learn; the digest injected into tomorrow's prompts is
  shown verbatim ("what the desk carries forward").
- Trade journal + equity curve + expectancy matrix live here too (existing data).

## Living-ness mechanics (the difference from the static tool)
1. **Time is a first-class axis** — every surface has a date scrubber; the desk replays.
2. **Agents are characters** — stable identity chips (model, role, record). Their language
   appears verbatim, attributed. No anonymous "the system thinks".
3. **Disagreement is rendered, not averaged away** — splits, dissents, vision vetoes are
   the most prominent UI moments.
4. **The tool narrates itself** — morning brief + activity stream mean the user never
   reconstructs what happened from panel-diffs.
5. **Memory on screen** — theses quoted back on positions, lessons feeding forward,
   track records moving. Yesterday visibly shapes today.
6. **Progressive liveness** — polling first (cheap, works), SSE upgrade later; no
   websocket complexity before the loop's DONE-TEST passes.

## Build order (folds into AGENT_LOOP as wave F, after C/D land)
F1 `/api/desk/feed` + DESK stream & morning brief (needs A/B/C data — first visible win)
F2 DEBATE theater (agent_verdicts + vision PNGs)
F3 POSITIONS lifecycle cards with thesis quotes (coach D1)
F4 LEDGER (track records from outcome joins + lessons diary from D2)
F5 Live-mode polish (in-flight indicators, scrubber everywhere)
Fidelity rule unchanged: this file is the contract; screenshot-vs-contract per screen;
two-direction (nothing extra); light theme; the ASCII-style blocks above are layout law.
