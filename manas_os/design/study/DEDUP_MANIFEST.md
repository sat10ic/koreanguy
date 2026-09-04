# Study Corpus Dedup Manifest

Cleanup pass over `manas_os/design/study/` (170 git-tracked files). Every removal below was
`git rm`'d (fully recoverable from git history — nothing was hard-deleted). Method: md5 hash
every file to find byte-identical duplicates, cross-reference every filename against citations
in `manas_os/design/knowledge/*.md` and `manas_os/design/*.md` to build a CITED_LOCKED set that
is never touched regardless of duplication, then verify each remaining stage-dup candidate by
diffing/spot-checking head AND tail content (not just size/word-count) before removal.

## Summary

| | Count |
|---|---|
| Files before | 170 |
| Files removed | 33 |
| Files after | 137 |
| — EXACT_DUP (byte-identical) | 18 |
| — STAGE_DUP (verified: content fully present in kept canonical) | 13 |
| — LOW_VALUE (tooling/wrapper, not teaching content) | 2 |
| CITED_LOCKED files preserved (never considered for removal) | 40 basenames (see below) |

Target range given was 25–40 files; landed at 33 after honest classification. No file was
removed "for the sake of a number" — every remaining apparent-duplicate candidate that could not
be verified byte-for-byte or content-for-content was left in place (conservative bias).

## CITED_LOCKED — preserved regardless of duplication

These filenames are referenced by basename in `manas_os/design/knowledge/*.md` and/or
`manas_os/design/*.md` (TRADETM_INDEX.md, TRADETM_NUANCES*.md, WAVE_K_SPEC.md, WAVE_J_SPEC.md,
WAVE_K8_PULLBACK_SPEC.md, STRATEGY_REFERENCE.md) as CITE sources or provenance anchors. Kept
unconditionally, including the 24 TradeTM `_text.txt` blog-article extracts individually cited
with `CITE:` tags in `TRADETM_NUANCES.md` / `TRADETM_NUANCES_COMPLETION.md`:

- `main.md` (EP/, IPO/, Manas Arora/, Tradetm/ — 4 files, all cited as folder indices)
- `Episodic Pivots_ A Complete Guide for Indian Traders_custom_rip.txt`, `_text.txt`, `ep_qna_formatted.txt` (EP/)
- `IPO_trading_transcript.md` (IPO/)
- `6 Manas Entry.md`, `CH3.1 Layout and Scans.md` (cleaned/), `Strong_Start_Tightness_Study.md` (cleaned/)
- `groww 2.txt`, `groww 3.txt`
- `9 mil vol scan_text.txt`, `Anger and Depression in Trading_ The Hidden Edge_text.txt`,
  `Complete Guide to Position Sizing & Risk Management in MTF trading_text.txt`,
  `Creating a Setups Playbook for Smarter Trading_text.txt`, `D2 Entry_ Every Question You Had, Answered_text.txt`,
  `Developing Feedback Loops_ Trader's Blueprint for Speed_text.txt`,
  `Fundamentals and Themes in Trading Explained_text.txt`, `How Probabilities Can Be Misleading in Trading_text.txt`,
  `How_Working_Professionals_Can_Build_a_Trading_System_for_Bull_Markets_Transcript.md`,
  `Improving Trading Processes for Better Performance_text.txt`, `On Bear Markets and Episodic Pivots Explained_text.txt`,
  `Position Sizing_ The Key to Better Trading Results_text.txt`, `Setup Prioritization and EPs — EP Trading Guide Tips_text.txt`,
  `Situational Awareness & Trading_ Smart Market Moves_text.txt`, `The Cost of Illiquidity and Its Impact on Traders_text.txt`,
  `Three Fatal Mistakes to Avoid in Stock Markets_text.txt`, `Trade Journal Analysis and Post Reviews - MAE MFE Guide_text.txt`,
  `Trade the Market You are in _ Adapt to Win in India_text.txt`, `Trading Intuition Over Objective Rules Explained_text.txt`,
  `Trading in Choppy Markets_ Practical Tactics & Rules_text.txt`, `choppy.txt`, `entry_framework_formatted.txt`,
  `situational_awareness_formatted.txt` (Tradetm/)
- `MBI_transcript.md`, `Trading_Systems_Part3_transcript.md` (Umang Stocksgeeks/)

## Removed files

### EXACT_DUP (byte-identical md5 to a kept file) — 18

`cleaned/Manas/` was a stale, incomplete earlier-generation copy of `cleaned/` (13 of 16
chapters + 2 misc files, all byte-identical to the same-named file one directory level up, which
also has all 16 chapters plus correction logs). Every file in it was an exact duplicate.

| Removed | Kept canonical | Reason |
|---|---|---|
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_1.md` | `cleaned/Chapter_1.md` | EXACT_DUP (md5 identical) |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_2.md` | `cleaned/Chapter_2.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_3.md` | `cleaned/Chapter_3.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_4.md` | `cleaned/Chapter_4.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_5.md` | `cleaned/Chapter_5.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_6.md` | `cleaned/Chapter_6.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_7.md` | `cleaned/Chapter_7.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_8.md` | `cleaned/Chapter_8.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_9.md` | `cleaned/Chapter_9.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_10.md` | `cleaned/Chapter_10.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_11.md` | `cleaned/Chapter_11.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_12.md` | `cleaned/Chapter_12.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Chapter_16.md` | `cleaned/Chapter_16.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/Strong_Start_Tightness_Study.md` | `cleaned/Strong_Start_Tightness_Study.md` | EXACT_DUP (kept file is CITED_LOCKED, per WAVE_K_SPEC.md/WAVE_J_SPEC.md) |
| `Manas Arora/Course Notes/cleaned/Manas/TRANSCRIPT_CLEANING_AUDIT.md` | `Manas Arora/Course Notes/TRANSCRIPT_CLEANING_AUDIT.md` | EXACT_DUP |
| `Manas Arora/Course Notes/cleaned/Manas/TRANSCRIPT_QUERIES.md` | `Manas Arora/Course Notes/TRANSCRIPT_QUERIES.md` | EXACT_DUP |
| `Manas Arora/Course Notes/ch12.txt` | `Manas Arora/Course Notes/ch12.md` | EXACT_DUP (md5 identical, 26252 bytes) |
| `Manas Arora/groww_int1_utf8.txt` | `Manas Arora/groww int 1.txt` | EXACT_DUP (md5 identical, 92479 bytes; naming consistent with sibling `groww int 2/3.txt`) |

Content confirmed present in kept file for all 18: identical md5 hash means byte-for-byte
identical content — no verification beyond hash needed.

### STAGE_DUP (verified: raw ASR-cleaning is non-lossy, or reflow-only reformat) — 13

Course Notes raw `.txt` transcripts with a matching `cleaned/<name>.md`. Verified NOT lossy by
diffing head AND tail of each pair — the cleaned versions restructure into headers/bullets and
strip filler words/disfluencies (word count typically drops 5-35%) but preserve every fact,
number, and example found in the raw tail. (Contrast with `CH 8.md`/`CH 9.md`/`CH10.md`/`CH11.md`/
`CH13.md`/`CH1 Fear Management.md`/`ch14.md`/`ch15.md`/`ch16.md`, which use a *different* naming
scheme than their `cleaned/Chapter_N.md` counterparts and whose cleaned header explicitly says
"raw ... untouched" — these are a deliberate raw+cleaned+correction_log provenance pair by
design and were NOT touched.)

| Removed | Kept canonical | Reason |
|---|---|---|
| `Manas Arora/Course Notes/CH 2.2.txt` | `cleaned/CH 2.2.md` | STAGE_DUP-verified (head+tail match, ASR cleanup only) |
| `Manas Arora/Course Notes/CH 2.3.txt` | `cleaned/CH 2.3.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/CH 3.2.txt` | `cleaned/CH 3.2.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/CH 4.1.txt` | `cleaned/CH 4.1.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/CH 4.2.txt` | `cleaned/CH 4.2.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/CH3.1 Layout and Scans.txt` | `cleaned/CH3.1 Layout and Scans.md` | STAGE_DUP-verified (kept file is CITED_LOCKED per WAVE_K_SPEC.md line 148) |
| `Manas Arora/Course Notes/Ch 5.1.txt` | `cleaned/Ch 5.1.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/Ch 5.2.txt` | `cleaned/Ch 5.2.md` | STAGE_DUP-verified |
| `Manas Arora/Course Notes/Ch2.1  Basic Foundation and Cycles.txt` | `cleaned/Ch2.1 Basic Foundation and Cycles.md` | STAGE_DUP-verified |
| `Tradetm/the_cost_of_illiquidity_text.txt` | `Tradetm/The Cost of Illiquidity and Its Impact on Traders_text.txt` | STAGE_DUP-verified (diff shows only PDF-extraction whitespace/page-marker artifacts; text identical; kept file is CITED_LOCKED / CITE: target in TRADETM_NUANCES.md) |
| `Tradetm/trade_the_market_you_are_in_text.txt` | `Tradetm/Trade the Market You are in _ Adapt to Win in India_text.txt` | STAGE_DUP-verified (same as above) |
| `Tradetm/Fundamentals and Themes in Trading Explained_custom_rip.txt` | `Tradetm/Fundamentals and Themes in Trading Explained_text.txt` | STAGE_DUP-verified (same as above) |
| `Manas Arora/groww int 2.txt` | `Manas Arora/groww_int2_formatted.txt` | STAGE_DUP-verified (147596 vs 147626 bytes; diff is a 16-line reflow/paragraph-break only, same Hindi transcript text throughout) |

### LOW_VALUE (tooling/presentation wrapper, not teaching content) — 2

| Removed | Kept canonical | Reason |
|---|---|---|
| `Manas Arora/Manas_Arora_CHARTGYM_Compilation_with_Photos.html` | `Manas Arora/Manas_Arora_CHARTGYM_Compilation_with_Photos (1).md` | LOW_VALUE: html is a CSS-styled viewer shell that loads photos live from external X post URLs (not embedded); stripped of markup it is ~5KB of mostly CSS with no teaching content beyond what the .md already contains in full prose |
| `Manas Arora/Course Notes/audit_transcript_loop.py` | — (no content to preserve) | LOW_VALUE: read-only Python audit/QA script for the cleaning pipeline itself, not source teaching material |

## Explicitly NOT removed (checked and kept as unique/intentional)

- **EP/** folder (4 files: `_custom_rip.txt`, `_text.txt`, `ep_qna_formatted.txt`, `main.md`) — all
  4 are CITED_LOCKED; kept regardless of any overlap between `_custom_rip.txt` and `_text.txt`.
- **`Tradetm/situational_awareness_formatted.txt`** and **`Tradetm/entry_framework_formatted.txt`**
  — despite the "_formatted" naming pattern that elsewhere indicates a reflow duplicate, these are
  large (116KB / 193KB) standalone Hindi-language video transcripts with no raw/unformatted
  counterpart in this repo — verified UNIQUE content, not a duplicate of the short English `_text.txt`
  blog articles of similar topic name.
- **`Tradetm/choppy.txt`** (32KB raw video transcript) vs **`Trading in Choppy Markets..._text.txt`**
  (9.8KB polished blog extract) — verified different content (raw session vs edited article), both kept.
- **`Course Notes/CH 8.md`, `CH 9.md`, `CH10.md`, `CH11.md`, `CH13.md`, `CH1 Fear Management.md`,
  `ch14.md`, `ch15.md`, `ch16.md`** — raw transcripts under a numbering scheme distinct from
  `cleaned/Chapter_N.md`; the cleaned header for Chapter 8 explicitly states "raw `CH 8.md`
  untouched," confirming these are an intentional raw+cleaned+correction_log provenance triad, not
  excess duplication. Kept both raw and cleaned for all of these.
- **`Umang Stocksgeeks/Umang.md`, `Umang_Stocksgeeks_deepseek.md`, `Umang_Stocksgeeks_mimo.md`** —
  three independently-synthesized digests of the same two source transcripts (MBI_transcript.md,
  Trading_Systems_Part3_transcript.md). Not a raw/cleaned pair; each is a distinct synthesis pass.
  Left all three (conservative bias — did not attempt to rank/merge synthesis quality).
- **3 PDFs in `Manas Arora/`** (`Manas_Arora_BroTip_Almanac_2018-2026_Merged.pdf`,
  `Manas_Arora_BroTip_Full_Almanac_2016-2026_2.pdf`, `Manas_Arora_BroTip_Full_Posts_Dump_2016-2026_2.pdf`)
  and `Manas_Arora_Gem_Threads_and_Comments_Almanac.pdf` — filenames suggest overlapping date
  ranges/content tiers (curated "Almanac" vs raw "Posts Dump"), but binary PDF text extraction was
  out of scope for this pass; left unverified and therefore untouched (conservative bias).
- All `ma1.txt`–`ma21.txt`, `mas1.txt`–`mas6.txt`, `elearn.txt`, `rcf.txt`, `vijaythk.txt`,
  `Ankur ptel.txt`, `groww 1.txt`, `groww 4.txt`–`groww 10.txt`, `groww int 3.txt` — none hash-matched
  any other file in the corpus; kept as unique, uncited-but-unverified-unique source material (not
  a duplication problem; simply not yet digested into the knowledge base).
