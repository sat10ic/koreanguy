# Transcript Cleaning Loop

A self-improving, decision-making playbook for turning raw ASR (speech-to-text) course transcripts into clean, faithful Markdown — without inventing, losing, or distorting anything Manas said. Sister document to `MiMo Manas/CHAPTER_BUILD_LOOP.md` (that one drafts the *book*; this one cleans the *source*).

The core problems this loop solves:
1. ASR picks a wrong-but-plausible word (acoustic error) that only context catches ("small **town**" → "small **account**", "**tangle**" → "**triangle**").
2. A term garbled at first mention is **clarified later** in the same transcript — so you must read ahead and *retrofit* the fix backward.
3. Words are **dropped** ("went from 200 350" → "from 200 to 350").
4. The same ASR garble recurs across files and should resolve the **same way every time** (consistency).
5. Every user correction should make the next transcript cleaner — the loop **learns.**

---

## Part 1 — What cleaning is (the bar)

Cleaning is **copyedit + disambiguation.** It is not rewriting, summarizing, or improving.

**DO:**
- Fix ASR spelling/homophone/acoustic errors where context makes the intent unambiguous.
- Add punctuation, sentence and paragraph breaks, light Markdown structure (`#` title, `##` topic shifts, bullet lists where he enumerates).
- Repair garbled run-ons and de-duplicate ASR stutters — without changing meaning.
- Insert an obviously-dropped connective word ("to", "the", "and") where grammar and flow demand it.
- Keep Manas's first-person voice, idioms, and his real vocabulary.

**NEVER:**
- Change any number, %, price, date, or count.
- Change which ticker/example he's discussing (only fix its *spelling*).
- Change his reasoning, claims, conclusions, or teaching order.
- Add analysis or content he didn't say.
- "Correct" his real trading terms into generic ones (see the Vocabulary Whitelist, Part 5).

**The hard constraint:** fidelity to what he actually said. When in doubt, flag — don't guess.

---

## Part 2 — The per-file loop

**Model policy.** Sonnet does the reading and mechanical cleaning (bulky). Opus decides the genuinely ambiguous semantic calls, adjudicates conflicting reads, and updates this loop + the Correction Ledger. Default Sonnet; escalate to Opus only when a fix could change meaning.

### Step 1 — Full read-through FIRST (Sonnet)
Read the entire transcript before editing a single word. Build a mental model of the argument: what is Manas teaching, in what order, with which examples? You cannot resolve an acoustic error without knowing what the sentence is *for.* **No edits during this pass.**

### Step 2 — Mechanical pass (Sonnet)
Strip ASR artifacts: stray escapes (`208\.` → `208.`), spacing, casing. Add punctuation and paragraph breaks. De-duplicate stutters ("...it worked out. Not saying — not saying we cannot go down..." → single clean version). Apply the Correction Ledger (Part 5) — every already-confirmed mapping is applied automatically, no re-deciding.

### Step 3 — Semantic pass (Sonnet, Opus on close calls)
Hunt acoustic mis-transcriptions: wrong-but-plausible words that break meaning. Homophones and near-homophones ("bar"/"bus", "triangle"/"tangle", "account"/"town", "force"/"fourth", "low"/"SSA"). Mangled trading terms. Half-parsed idioms. For each, run the **Decision Matrix** (Part 3).

### Step 4 — Retrofit pass (Sonnet, Opus on close calls) ← the key one
This is the pass most cleaners skip. Spoken transcripts explain themselves out of order. Run the **Retrofit Engine** (Part 4): resolve early garbles from later context, hold ambiguities open until the transcript clarifies them, and insert dropped words. This pass often *upgrades* a Step-3 flag into a confident fix, because the answer was three paragraphs downstream all along.

### Step 5 — Emit + self-audit (Sonnet)
Write the cleaned `.md`. Then produce two artifacts:
- **Correction log** for this file: every fix made (raw → fixed, confidence) and every flag left.
- **Query rows** for anything still uncertain → appended to `TRANSCRIPT_QUERIES.md`.

### Step 6 — Ledger update (Opus, when user answers)
When the user confirms/corrects a query, update the **Correction Ledger** (Part 5) so the mapping is permanent and auto-applies to every future file. This is the self-improvement hinge.

---

## Part 3 — The Decision Matrix (fix / flag / query)

For every suspected error, classify by confidence, then act:

| Confidence | Meaning | Action |
|---|---|---|
| **HIGH** | Context makes the intended word/number unambiguous. A competent reader would agree instantly. | **Fix inline.** No marker in prose. Log it in the file's correction log. |
| **MEDIUM** | You have a strong guess but a reasonable person could disagree, OR it changes meaning. | **Flag inline** with `**<u>suspect</u>**[⚠ likely "X"?]` + a **query row**. Do not change the word. |
| **LOW** | You can tell something's wrong but can't confidently reconstruct it. | **Leave as-is**, wrap in `[⚠ ASR garble: raw was "..."]`, + a **query row.** |

**Hard rule regardless of confidence:** numbers, prices, %, dates, and ticker *identities* never get a silent fix. A garbled *number* is at most MEDIUM (flag + query), never HIGH — because you can't hear the audio. The one exception: a dropped connective inside a number phrase ("200 350" → "200 **to** 350") is HIGH because you're inserting grammar, not changing a value.

**Meaning-inversion check:** if a candidate fix could flip the trading logic (buy/sell, add/exit, more/less, stop-above/stop-below, above/below a MA), demote to MEDIUM at best and flag. A wrong homophone in position-sizing or stop-loss logic is the most expensive error class.

---

## Part 4 — The Retrofit Engine

Three mechanisms for using the *whole* transcript to clean any one part of it.

### 4a — Forward-hold (don't guess at first contact)
When you hit a garble, do not resolve it immediately. **Scan ahead.** Spoken teaching almost always circles back: the ticker gets named later, the number gets restated, the concept gets defined. Hold the ambiguity open as a candidate until you've read past it. Only decide once you've seen whether the transcript resolves itself.

*Example pattern:* Manas says "I bought [garble]" then two paragraphs later "...and that's why [Company] worked" — the later name retro-resolves the earlier garble to HIGH confidence.

### 4b — Backward-retrofit (fix the earlier line from the later one)
Once a later passage disambiguates an earlier garble, **go back and fix the earlier instance** — and every other instance of the same garble in the file. Then log the mapping so it propagates (Part 5). A term is cleaned consistently across the whole file, not just where it was finally understood.

*Example pattern:* an early "focal volume" is opaque; later "...the purple dot, which is high relative volume" reveals the concept, letting you resolve or confidently flag the earlier line.

### 4c — Missing-word reconstruction
When a word is clearly dropped, reconstruct from grammar + trading context:
- **Connectives / articles** ("to", "the", "of", "a") → insert silently, HIGH confidence.
- **A content word that carries meaning** (a verb, a noun, a number) → insert only if context forces exactly one word; otherwise flag with `[⚠ word missing — likely "X"]`.
- **A whole dropped clause** (the thought doesn't complete) → never invent it. Flag: `[⚠ transcript appears to drop a clause here]`.

**Retrofit priority:** always prefer the transcript's *own later words* over your outside knowledge. If Manas later calls it "the low," use "the low" — not a synonym you'd pick. His vocabulary beats yours.

---

## Part 5 — The self-improving core: the Correction Ledger

This is what makes the loop *learn.* Three living tables. Every confirmed correction goes here and **auto-applies to all future transcripts** at Step 2. Update on every user answer.

### 5a — Confirmed ticker/name map (raw ASR → canonical)
Applied automatically. Status: ✅ user-confirmed · 🟡 high-confidence-unconfirmed · ⚠ pending user.

| Raw ASR | Canonical | Status |
|---|---|---|
| Tadani | Adani Enterprises | ✅ |
| Ptm | Paytm | ✅ |
| Zendtech / ZTEK / Zentech | Zen Technologies (ZENTEC) | 🟡 |
| NC (in position lists) | NCC | 🟡 |
| VNL | RVNL | ✅ |
| First Source Solution | Firstsource Solutions | ✅ |
| JK tire | JK Tyre | 🟡 |
| Kanaka Bank | Karur Vysya Bank | ⚠ (query 3-b) |
| Electra / Elektra | Elecon Engineering? | ⚠ (query 2.2-c / 4-b) |
| Kiloska | Kirloskar (which?) | ⚠ |
| Perla soft | Parle Soft? | ⚠ (query 5.1-b) |
| Boros sell | Boro Sales? | ⚠ (query 5.2-a) |
| ITT Cementation | ITD Cementation? | ⚠ (query 3-c) |
| JVMA | *(unresolved)* | ⚠ |
| ETM | *(unresolved)* | ⚠ |
| Argonin | *(unresolved)* | ⚠ |
| BSC (2021 trade) | *(unresolved — BSE Ltd?)* | ⚠ (query 6-b) |

### 5b — Manas vocabulary whitelist (real terms — NEVER "correct" these)
These are his actual words. If ASR renders them cleanly, leave them. They are not errors.

- **Buying force** — % up from the 3-month / 52-week low (his momentum-strength gauge)
- **Purple dot** — a >5% move on >500k volume; his institutional-velocity marker
- **Surfing the 20 DMA** — price riding along the rising 20-day average
- **Strong start** — his entry: next-day gap-up, open = low
- **Busted** / **reversal Busted** — his reversal-entry trigger
- **Linear uptrend** — never closes convincingly below the rising 20 DMA
- **Five-star setup** — his top-grade continuation/reversal label
- **Focus list** — the 5–7 name shortlist
- **Too fast kills the stock** — his over-extension rule
- **Madhyamarg** / desi metaphors — keep verbatim

*(Add to this list whenever a new Manas-ism is confirmed, so no future pass mistakes it for a garble.)*

### 5c — Recurring garble patterns (his accent × ASR)
Once a pattern is seen twice, record it so future passes catch it fast.

| Pattern | Example | Note |
|---|---|---|
| "bar" → "bus" | "big green bus" → "big green bar" | candle terminology |
| "triangle" → "tangle" | "tangle breakout" → "triangle breakout" | chart patterns |
| "names" → "games" | "7-8 games" → "7-8 names" | watchlist |
| "account" → "town" | "small town fast" → "small account fast" | course name |
| "the low" → "SSA" (?) | strong-start rule | ⚠ unconfirmed |
| number-connective dropped | "200 350" → "200 to 350" | insert "to" |
| "write" → "ride" | "should I write it?" → "should I ride it?" | only in holding/selling context; do not alter ordinary "write down" |
| "breaks" → "trades" | "first 30 to 50 breaks" → "first 30 to 50 trades" | learning-phase trade count |
| "stocked out" → "stopped out" | "getting stocked out" → "getting stopped out" | exit/stop-loss context |
| "moving out line" → "moving average line" | "10 week moving out line" → "10-week moving average line" | MA/trend context |
| "dmr" / "dm a" → "DMA" | "20 dmr" → "20-DMA" | only in moving-average/trailing-stop context |
| "games" → "gains" | "one or two games" → "one- or two-day gains" | only in profit-taking context; do not alter watchlist "names" cases |
| "bread" → "breadth" | "bread sheet" → "breadth sheet" | only in market-breadth context |
| "Europe" → "here" | "go high from Europe" → "go high from here" | directional/location phrase in market outlook |
| "setters" → "sectors" | "what the setters are doing" → "what the sectors are doing" | market/index/sector context |
| "basis old" → "bases old" | "three basis, four basis old" → "three bases, four bases old" | base-counting context |
| "rates" → "trades" | "good rates" → "good trades" | trading context only |
| "bit" → "bid" | "high bit" → "high bid / bid above high" | order-placement context; flag if rule-critical |
| "repeat terms" → "rupee terms" | "actual repeat terms" → "actual rupee terms" | account-size scaling context |
| "enjoy yourself" → "injure yourself" | "you will enjoy yourself" → "you will injure yourself" | progressive-overload/bodybuilding analogy |
| "57 names" → "5–7 names" | "pick up some 57 names" → "pick up some 5–7 names" | daily shortlist context |
| "weekends" → "weak hands" | "not a lot of weekends got out" → "not a lot of weak hands got out" | pullback/rest/flushing-sellers context; flag if concept-critical |
| "hour trade" → "R trade" | "100 hour trade" → "100R trade" | risk-multiple context; flag because numbers/units are rule-critical |
| "52 degrees" → "52-week low" | "68% up from 52 degrees" → "68% up from 52-week low" | market-distance context |
| "internet 20" → "10 and 20" | "surfing the internet 20" → "surfing the 10 and 20" | moving-average context |
| "grades" → "trades" | "these are the grades you have taken" → "these are the trades you have taken" | trading sample context |
| "Cool India" → "Coal India" | "Cool India, on 10th October" → "Coal India, on 10th October" | ticker/name context; still confirm if used as formal example |
| compressed percent range | "1020%" → "10–20%" | move-size context |
| sample-count garble | "six member" / "six on six" → "six out of six" | case-counting context |
| "write" → "ride" | "write or sell" → "ride or sell" | sell-side / holding winners context; do not alter literal writing/journal contexts |
| "trading stock" → "trailing stop" | "let the trading stock get hit" → "let the trailing stop get hit" | stop-management context |
| "BQN" → "breakeven" | "move my stop to BQN" → "move my stop to breakeven" | stop moved so trade cannot lose money |
| "pure line" → "period line" | "20 pure line" → "20-period line" | moving-average context |
| "MNC stop" → "emergency stop" | "did not hit my MNC stop" → "did not hit my emergency stop" | trailing/emergency-stop context |
| "TDPOW / trading power systems" → "TD Power Systems" | "trading power systems bought 24th April" → "TD Power Systems bought 24 April" | ticker/name context; confirm before final tables |
| "reading log sheet" → "trading log sheet" | "my reading log sheet" → "my trading log sheet" | journal/log-sheet context |
| "net pi value" → "net P&L value" | spreadsheet return/profit column | profit-and-loss context |
| "best to do ratio" → "reward-to-risk ratio" | "I made four is to one" | reward/risk context; flag if numbers conflict |
| "market bread" → "market breadth" | market sheet / shares above 20-DMA | breadth context only |
| "log gains" → "lock gains" | "looking to log gains" → "looking to lock gains" | profit-booking context |
| "majority" → "maturity" | "that majority has come" → "that maturity has come" | behavioural-edge context |
| "grade trade" → "great trade" | "first grade trade" → "first great trade" | edge/chance-of-good-trades context |
| "apply breaks/bakes" → "apply brakes" | "where to apply breaks" | drawdown slow-down context |
| "droughts" → "drawdowns" | "recover from your droughts" | drawdown/recovery context |
| "emergency stock" → "emergency stop" | "maintain an emergency stock" | stop-management context |

---

## Part 6 — Self-improvement triggers

When the user says any of these, update immediately:

| User signal | What updates |
|---|---|
| Answers a query row (ticker/number) | Move the mapping to Ledger 5a as ✅; retro-apply to every cleaned file that used it; remove the inline ⚠. |
| "You missed a wrong word" | Add the pattern to Ledger 5c; re-run the semantic pass on siblings for the same garble. |
| "That's his actual term, don't change it" | Add to the Vocabulary Whitelist 5b so it's never re-flagged. |
| "You changed a number/meaning" | Tighten Part 3: that error class drops one confidence tier permanently. |
| "You over-flagged / too many marks" | Raise the fix threshold: MEDIUM calls with strong context become HIGH. |
| "You under-flagged / guessed wrong" | Lower the fix threshold: demote borderline HIGH to MEDIUM+flag. |

**The learning invariant:** a garble the user has resolved once should never generate a query again. It lives in Ledger 5a and auto-applies.

---

## Part 7 — Cross-file consistency check (run after every batch)

After cleaning a batch, a quick Sonnet sweep:
- Does every ticker resolve the **same way** across all files? (No "Elecon" in Ch 4 but "Electra" left raw in Ch 2.)
- Do the recurring-garble patterns in 5c appear anywhere still un-fixed?
- Are the Vocabulary Whitelist terms ever accidentally "corrected"?
- Is every ⚠ flag in the files mirrored by a row in `TRANSCRIPT_QUERIES.md` (and vice versa)?

Any drift → fix and log.

---

## File map

| File | Role | Updated by |
|---|---|---|
| `Course Notes/*.txt`, `Course Notes/CH*.md`, `Course Notes/ch*.md`, `6 Manas Entry.md`, `7. Position sizing.md` | Raw ASR sources. **Never edited.** | — (Manas-provided) |
| `Course Notes/cleaned/<part>.md` | Per-part cleaned transcripts. | Cleaning passes. |
| `Course Notes/cleaned/Chapter_N.md` | Combined master per chapter. Canonical source for the book overhaul. | Combine step + retro-applied corrections. |
| `Course Notes/TRANSCRIPT_QUERIES.md` | Open questions for the user. | Every cleaning pass; cleared as answered. |
| `Course Notes/TRANSCRIPT_CLEANING_LOOP.md` | This file. Ledger + rules. | Every user answer / feedback signal. |

---

## The one-line version

Read the whole thing first. Fix what context makes certain, flag what it doesn't, and **let the later half of the transcript clean up the earlier half.** Every answer the user gives becomes a permanent rule, so the next transcript is cleaner than the last.
