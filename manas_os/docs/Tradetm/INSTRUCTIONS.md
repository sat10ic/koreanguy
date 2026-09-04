# Working Instructions — Tradetm Study-Digest (agent-agnostic)

**Purpose.** This file lets ANY coding agent (Claude Code, Cursor, Aider, Hermes, etc.)
continue the Tradetm study-digest work without losing the principles we've established.
It is intentionally vendor-neutral. If you are an AI agent reading this: follow it as
standing instructions for this task. The markdown vault is the source of truth — you are
disposable; do not rely on your own memory over these files.

---

## 1. What we are building
A **private study digest** (NOT a published book) of Indian-market momentum-trading
material, sourced from the Tradetm transcripts (`Tradetm/*.txt`) and PDFs
(`reference/Tradetm/*.pdf`). Goal: understand **Indian market nuances** and **institutional
footprints** on their own terms. Output digest notes live in `study-digest/tradetm/`,
one `.md` per source file, later synthesized into topic frameworks.

Because it is a private digest for personal learning, extraction can be liberal. The
concern is **accuracy and fidelity**, not IP. (A *published* book would require a different,
synthesis-only treatment — see §6.)

---

## 2. Ground principles (do not violate)
1. **Markdown is the source of truth. The AI is disposable.** Never treat any model's memory
   as authoritative. Trust the files. Use **git** as version control (this repo is a git repo).
2. **Minimize token/compute spend — but never at the cost of quality.** Token thrift is the
   default; quality/fidelity is the hard constraint. If a cheaper path risks weaker capture or
   a missed nuance, take the costlier path.
3. **Fidelity over judgment.** This is about INDIAN markets. Do NOT filter, discount, or
   "correct" claims using US-market assumptions or general priors. Capture the source's
   claims, nuances, parameters, reasoning, metaphors, and mental models faithfully and in
   DETAIL. Prefer capturing too much to too little.
4. **Flag, never remove.** If a claim seems extraordinary, unlikely, or unverified, keep it
   intact and mark it `⚠️` with a short neutral note ("flagged for later verification,
   retained as stated"). Never delete or water down a claim.
5. **Separate assertion from evidence.** A transcript is the educator *asserting* something —
   that is not evidence. Record "what the source claims" separately from "how it could be
   verified on real Indian data (NSE/BSE: delivery %, shareholding pattern, FII/DII flows,
   F&O OI, OHLCV)". Frame verification neutrally as a future check, not grounds to doubt now.
6. **Capture concrete parameters/thresholds** explicitly (numbers, %, day-counts, RVOL, stop
   sizes, gap %). The specificity is much of the value.
7. **Note contradictions** with the existing book chapters or between sources, factually and
   without picking a winner.

---

## 3. The digest template (one file per source)
Each note in `study-digest/tradetm/<slug>.md` uses this structure. The canonical worked
example is `study-digest/tradetm/volume-pocket-pivots.md` — read it before writing a new one.

```markdown
---
source_file: Tradetm/<filename>          # or reference/Tradetm/<filename>.pdf
topic: <one-line topic>
chapter_map: [<existing book chapter(s), e.g. Ch3 Signal Stack, or "new">]
conviction: high | medium | low          # how strongly the source argues it
type: fact | opinion | mixed             # falsifiable claim vs discretionary view
transcription_quality: clean | rough     # transcripts are rough auto-transcriptions
flag_legend: "⚠️ = extraordinary/unverified claim, retained as stated; NOT removed"
---

## Core claims (restated in my words, with the source's own reasoning)
## Mental models / metaphors the source uses
## When it applies (conditions: regime / cap tier / timeframe / liquidity)
## Parameters & thresholds (concrete numbers)
## Worked chart reads / examples described
## How it could be confirmed on Indian data (future check — does not lower the claim)
## When the source says it fails / caveats
## Contradictions & open questions
## Related frameworks  ([[other-note-slug]] links)
```

Restate in your own words — do NOT quote verbatim (transcripts are rough auto-transcriptions;
decode obvious garbles, e.g. "Wipe Off" → Wyckoff, "pocket pet/word" → pocket pivot).

**Existing book chapters for `chapter_map`:** Ch1 Core Truth · Ch2 Microstructure ·
Ch3 Signal Stack · Ch4 Setup Architecture · Ch5 Execution · Ch6 Sizing/Risk · Ch7 Trade
Journal · Ch8 Process · Ch9 Market-Cap Playbooks · Ch10 IPO · Ch11 Episodic Pivots ·
Ch12 Position Building · Ch13 Capital Growth · Ch14 Alpha Decay · Ch15 Psychology.

---

## 4. Workflow
1. **Large single-line transcripts** (some files are one ~50–165k-char line) overflow
   line-based file readers. Pre-split them with `tools/_chunk_transcripts.py`, which writes
   Read-friendly chunks to `study-digest/_src/<slug>/part_NN.txt`. (`study-digest/_src/` is
   scaffolding — git-ignored.) Read all parts in order; they form one continuous transcript.
2. **One digest per source file**, using §3's template and §2's discipline.
3. **Synthesis pass (do last, on your most capable model):** roll the per-file notes into
   topic frameworks (entries, EPs, volume/accumulation, sizing, psychology, Indian
   microstructure, institutional footprints) plus a single **contradiction log** that lists
   where sources disagree with each other or with the existing book.

---

## 5. Model orchestration (token-smart, quality-first)
- Use your **most capable model as orchestrator** for synthesis, structure, and judgment.
- Delegate to a **cheaper/faster model** ONLY for work that is *mechanical AND bulky*
  (reading/extracting across many large files), so only conclusions return to the main
  thread. Do NOT delegate small tasks — cold-start re-derivation costs more than it saves.
- (In Claude Code: Opus 4.8 orchestrates, Sonnet sub-agents do bulk extraction.)

---

## 6. If this ever becomes a PUBLISHED artifact (not the current plan)
Switch from "single-source repackaging" to **genuine synthesis**: Tradetm becomes one input
among many, ideas restated in your own words, generic attribution ("a school of Indian
momentum educators"), no mirrored chapter flow, never quote transcript text. See
`reference/SOURCE_NOTES_momentum_school.md` for the established source-discipline rules.

---

## 7. File map
- `Tradetm/*.txt` — raw transcripts (source)
- `reference/Tradetm/*.pdf` — source PDFs (git-ignored binaries)
- `study-digest/tradetm/*.md` — the digest notes (output)
- `study-digest/_src/<slug>/part_NN.txt` — chunked large transcripts (git-ignored scaffolding)
- `tools/_chunk_transcripts.py` — the chunker
- `CLAUDE.md` — Claude-Code-specific version of these principles
- `anchor/` — the existing book's control plane (OUTLINE, STYLE_GUIDE, DEFINITIONS, PROGRESS)
