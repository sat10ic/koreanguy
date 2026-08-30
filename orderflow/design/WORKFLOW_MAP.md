# The momentum desk — plain-English status

Updated 2026-08-29. For the technical version, see `unidesk/GOAL.md` and
`plan/UNIFIED_DESK_INTEGRATION_PLAN.md`.

---

## The big picture

We are building a helper that checks stock trades BEFORE you take them.

It doesn't pick stocks. It doesn't place trades. It answers one question at
the moment you'd press buy:

> "Is this trade healthy — or is something quietly wrong?"

It looks at three things, like three advisors in a room:

1. **The Scout** — which stocks are strong and setting up (daily charts).
2. **The Bodyguard** — can we actually get in and out of this stock without
   getting hurt (liquidity, exit risk).
3. **The Lie Detector** — right at the trigger moment, is the order book
   confirming the move, or faking it (live market data).

You always make the final call. The tool can only say: GO / WAIT / DON'T.

---

## The build, in plain words

```
STEP 1 — Test the thermometer      ████████░░  almost done
STEP 2 — Install the CCTV          █████░░░░░  half done
STEP 3 — Build the Scout           ████████░░  almost done
STEP 4 — Build the Lie Detector    █░░░░░░░░░  parts ready
STEP 5 — The final referee         ░░░░░░░░░░  waiting on steps 1–4
STEP 6 — The screen you look at    ░░░░░░░░░░  last, on purpose
```

**Step 1 — Test the thermometer (measure the data feed).**
Before trusting any gauge, you test it. We built the gauge and tested it on
fake data. Remaining: point it at the REAL market for one day — that's the
login you do on Monday morning. One day of data tells us which fancy
features are real and which are fantasy.

**Step 2 — Install the CCTV (record everything).**
The order book can't be rewind-ed later — if it wasn't recorded live, it's
gone. So we built a recorder first. It's built and tested; it just needs
real days to record.

**Step 3 — Build the Scout (find good setups).** ✅ nearly complete
This part reads official NSE end-of-day records (we found ~15 months of
them already in your folders — 646,000 rows covering 2,760 stocks) and
answers: is this stock strong? is the pattern good? is there room to move?
is the entry worth it? All built and tested with hand-checked numbers.

**Step 4 — Build the Lie Detector (live order book).** Parts ready.
The plumbing to talk to the broker's live data is built. The "smell test"
rules for live breakouts are designed. They get finished while we wait for
real recorded data.

**Step 5 — The referee.**
Combines everything and says GO / WAIT / DON'T. Hard rules (like "exit door
too narrow = DON'T") can't be overruled by anything else.

**Step 6 — The screen.**
The nice visual dashboard. Built last on purpose — a beautiful screen with
no data behind it is decoration.

---

## What happened so far (simple log)

| When | What |
|---|---|
| Aug 28 | Wrote the rulebook and the blueprint into the repo |
| Aug 28 | Built the measuring tools (Step 1) — tested on fake data, 62 checks pass |
| Aug 28 | Another robot (Autoclaw) verified the broker's tech details, then stopped safely |
| Aug 29 | A third robot (Codex) finished the CCTV recorder (Step 2 core) |
| Aug 29 | Built the Scout's math: trend, strength, participation, room-to-move (Step 3) |
| Aug 29 | Plugged in your 15 months of NSE records: 646,000 rows, 2,760 stocks |
| Aug 29 | Ran the FIRST REAL SCAN: 2,760 stocks checked in 8 seconds, 8 setups passed |
| Aug 29 | Built the referee's scoring rulebook (Step 5 math) and trade report cards |
| Every hour | A robot wakes up and builds the next unfinished piece automatically |

Every piece above has its own signed receipt in the project's ledgers — who
built it, what proves it works, and what is still unproven.

---

## What's left, and who does it

### You (small but important)
| What | When |
|---|---|
| Log in and let it watch the market for one day | **Monday ~09:00** |
| Glance at the results and say "keep" or "kill" | after that day |
| Two small choices (which index to compare against; where files live) | anytime |

### The robots (everything else)
- Finish the Lie Detector's rules and the referee (Steps 4–5)
- Add the remaining pattern checkers to the Scout
- The screen (Step 6) — last

---

## The honest warning

Monday might shrink this project. If the real data turns out slow and
shallow, the fancy stuff dies and what survives is the part that stops you
entering trades you can't exit safely. That's still worth having — but it's
your call, made on Monday's measurement, not on anyone's wishful thinking.
