# ATTENTION ENGINE — spec

What symbols is the trader pool converging on, is that convergence *early*, does
it agree with breadth and sector strength, and is it the kind of play this desk
actually trades?

Output: a ranked prioritisation signal for the watchlist. **Not a buy signal.**
TraderLog does not size, route, or advise (`DECISIONS.md`, 2026-08-23). This
surfaces what to look at; the user's own gates decide what to take.

Status: **specified, not built.** Depends on W2 (classification) and W4 (breadth
+ daily prices). Nothing here can be computed today. See "Build order".

---

## 1. The two failure modes this design exists to avoid

**A. Counting talk as if it were money.**
A mention costs nothing. An entry with a stated stop is somebody showing you
their risk. Summing them into one "mentions" number throws away the only part
that carries information. Events are therefore weighted by *cost to the author*.

**B. Attention is a lagging indicator.**
This is the one that kills naive versions of this feature. By the time eight
traders are posting about a name, it is frequently day 6 of the move — the exact
opposite of the early-entry edge this methodology is built on (TradeTM/Arora
spine). A score that rises with attention is a machine for buying crowded tops.

So the score **decays with age since first mention**, and rewards *tightness in
time*, not volume. Three traders entering within two sessions of each other beats
eight traders mentioning something over three weeks — and the design must make
the second case score LOWER, not higher.

**B-adjacent: these traders read each other.** Six mentions can be one idea and
five echoes. Independence is discounted, not assumed.

---

## 2. Event weights

Every contributing event comes from `position_events`, `watch_ideas`, or
`post_class`. Weight reflects what the author risked by posting it:

| Event | w_action | why |
|---|---|---|
| entry **with stated stop** | 6.0 | risk shown, position taken — the strongest thing available |
| add to an existing position | 4.5 | pressing a winner; higher conviction than the initial entry |
| entry, no stop stated | 4.0 | took it, but told you less |
| watch idea **with a trigger level** | 2.0 | specific enough to be falsifiable |
| watch idea, vague | 1.0 | "on my list" |
| bare mention in a theme/breadth post | 0.5 | context, not a call |
| exit | 0.0 | contributes nothing to *entering* attention (tracked separately, see §6) |

---

## 3. Attention score

```
attention(sym, d) = Σ  w_action · w_trader · w_recency · w_independence
                  events in [d-20, d]
```

- **`w_trader`** — from `trader_style`. Blend of stop discipline, stated win
  rate, and `preach_score`. **Cold start = 1.0 for everyone**; do not weight by
  track record until a trader has ≥30 closed positions logged, or the score is
  just noise amplified by a small sample.
- **`w_recency`** — `0.5 ** (sessions_ago / 3)`. Three-session half-life.
- **`w_independence`** — `1.0` for the first post on a symbol in a 24h window,
  `0.6` for each subsequent trader inside that window whose post contains no new
  information (no level, no entry). Echoes count less than ideas.

---

## 4. The prioritisation signal

```
priority(sym, d) = attention
                 × freshness
                 × regime_mult
                 × theme_mult
                 × activity_mult
                 × play_fit
```

**`freshness` — the anti-crowding term. The most important multiplier here.**

| sessions since first mention | multiplier |
|---|---|
| 0–2 | 1.00 |
| 3–5 | 0.80 |
| 6–9 | 0.50 |
| 10–15 | 0.25 |
| 16+ | 0.10 |

**`regime_mult` — breadth gates conviction, it does not add to it.**
From `regime_daily` (adopted XP + MBI). Breakout and momentum plays fail
disproportionately in poor breadth, so a bad tape *dampens*:

| MBI day colour | XP band | multiplier |
|---|---|---|
| GREEN | STRONG / EXTREME | 1.20 |
| GREEN | BUILDING | 1.10 |
| WHITE | any | 0.85 |
| RED | any | 0.55 |
| RED + warning day | any | 0.35 |

Never zero. A genuine leader emerging in a bad tape is information, and a hard
gate would hide exactly the setup worth knowing about.

**`theme_mult`** — 1.25 when ≥2 other symbols in the same theme (`themes`) or NSE
sector are also scoring in the top quartile. Sector confirmation is real; an
isolated name in a dead sector is weaker than the raw count suggests.

**`activity_mult`** — from `alpha_activity_signals` (adopted Reactor Scale:
`q_ratio` × `d_ratio` from bhavcopy trade-quantity and delivery). 1.0 baseline,
up to 1.35 when activity is in the top decile. **This is the highest-value term
in the whole formula**: it is the only input that is not derived from what people
*said*. Talk plus independent evidence of delivery-based accumulation is a very
different claim from talk alone.

**`play_fit`** — see §5.

---

## 5. Play-type classification

Classified per trade-event post by the LLM (W2 classifier, extended field), from
the post text plus vision output:

`ep` (episodic pivot — gap on a fresh catalyst) · `momentum_burst` ·
`breakout` (base/range breakout) · `pullback` (to a rising MA) ·
`vcp` (volatility contraction) · `ipo_base` · `swing_range` · `unclear`

`play_fit` weights toward what this desk actually trades. Default 1.0 for all
until the user sets preferences — **do not invent a preference ordering.** Ships
as a config block the user fills in, and `unclear` is always 1.0 so an
unclassifiable post is never penalised for the classifier's failure.

---

## 6. Negative signal — the part most versions of this omit

Attention is not only bullish. Three things must subtract:

- **Cluster exits.** Two or more tracked traders exiting the same symbol inside
  three sessions is a strong negative, and it is *more* reliable than a cluster
  of entries — traders under-report exits, so when several do it publicly, it is
  real.
- **Deleted posts.** A deleted entry post on a symbol (`posts.deleted_at`)
  reduces the score. It is usually a quiet loss.
- **Stop violations.** A trader who stated a stop, blew through it, and kept
  posting about the name is not conviction — it is a bag being held.

These are surfaced as an explicit `caution` flag on the row, not silently netted
into one number. A reader must be able to see *why* something was demoted.

---

## 7. Honesty requirements

**The score is unvalidated until it is backtested, and the UI must say so.**
Once W4 supplies daily prices, `derive/attention_validate.py` computes, for every
historical cluster: forward return at +5 / +10 / +20 sessions versus the
NIFTYMIDSML400 median over the same window, bucketed by score decile.

Ship criterion: **the top decile must beat the universe median at +10 sessions
across at least 60 clusters.** If it does not, the screen displays the failure
rather than the ranking. A prioritisation number with no evidence behind it is
worse than no number, because it will be trusted.

Every score on screen expands to its component multipliers. No black box — same
rule the rest of this project runs on.

---

## 8. Data model

```sql
CREATE TABLE IF NOT EXISTS symbol_attention (
  symbol TEXT NOT NULL, trade_date TEXT NOT NULL,
  attention REAL, priority REAL,
  n_traders INTEGER, n_entries INTEGER, n_mentions INTEGER,
  first_seen TEXT, sessions_since_first INTEGER,
  freshness REAL, regime_mult REAL, theme_mult REAL,
  activity_mult REAL, play_fit REAL,
  dominant_play TEXT, theme TEXT,
  caution_json TEXT,           -- cluster exits, deletions, stop violations
  components_json TEXT,        -- per-event contributions, for the drill-down
  is_mock INTEGER NOT NULL DEFAULT 0, ingested_at TEXT NOT NULL,
  PRIMARY KEY (symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS attention_validation (
  as_of TEXT NOT NULL, decile INTEGER NOT NULL,
  n_clusters INTEGER, fwd_5d REAL, fwd_10d REAL, fwd_20d REAL,
  universe_10d REAL, beats_universe INTEGER,
  ingested_at TEXT NOT NULL,
  PRIMARY KEY (as_of, decile)
);
```

Single writer: `derive/attention.py` for the first, `derive/attention_validate.py`
for the second.

---

## 9. Screen — HEATMAP

```
┌── PRIORITY · 22 Aug ────────────────── XP 11.4 LOW · MBI RED ⚠ ─────────────┐
│  regime multiplier 0.35 applied to everything below — bad tape             │
│                                                                            │
│  ┌────────────┬────────────┬────────────┬────────────┐                     │
│  │ KPITTECH   │ BEL        │ CUMMINSIND │ ZAGGLE     │   ■ 8+  ■ 5-8       │
│  │ ███████    │ █████      │ ███        │ █          │   ■ 3-5 □ <3        │
│  │ 3 in · 2d  │ 2 in · 4d  │ 1 in · 9d  │ 0 in · 14d │                     │
│  │ EP         │ BREAKOUT   │ PULLBACK   │ IPO BASE   │   size = priority   │
│  └────────────┴────────────┴────────────┴────────────┘   colour = freshness│
└────────────────────────────────────────────────────────────────────────────┘

┌── RANKED ──────────────────────────────────────────────────────────────────┐
│ sym        pri   att  trd  ent  age  play      theme      regime act  why  │
│ KPITTECH   7.4  21.1   3    3    2d  EP        —          0.35  1.31   ›   │
│ BEL        4.1  16.8   2    2    4d  BREAKOUT  DEFENCE    0.35  1.00   ›   │
│ CUMMINSIND 1.2  11.0   4    1    9d  PULLBACK  POWER ANC  0.35  1.00   ›   │
│   ⚠ 2 traders exited within 3 sessions — caution                           │
│                                                                            │
│ ▼ KPITTECH · why 7.4                                                       │
│   attention 21.1 = 3 entries w/ stop (6.0) × recency × independence 0.6    │
│   × freshness 1.00 (2 sessions since first mention)                        │
│   × regime 0.35 (MBI RED, warning day)  ← biggest drag today               │
│   × theme 1.00 (no sector confirmation)                                    │
│   × activity 1.31 (delivery ratio top decile — accumulation, not just talk)│
│   3 entries: @a 20 Aug ₹1,610 SL 1,570 · @b 21 Aug ₹1,624 · @c 21 Aug ...  │
└────────────────────────────────────────────────────────────────────────────┘

┌── IS THIS SIGNAL REAL? ────────────────────────────────────────────────────┐
│  top decile +10d:  +4.1%   universe median +1.2%   n=74   ✓ beats          │
│  bottom decile:    -0.8%                                                   │
│  Last validated 21 Aug. Score is NOT shown as a ranking until this passes. │
└────────────────────────────────────────────────────────────────────────────┘
```

Treemap is plain SVG (`squarifyTreemap` idiom exists in `manas_os/desk/src/viz.js`
and can be adopted). No chart library.

---

## 10. Build order

Nothing here is computable before its inputs exist.

| Needs | Why |
|---|---|
| W2 classify | symbols, play type, event kinds |
| W2 reconcile | entries vs mentions — the whole talk-vs-money distinction |
| W4 breadth | `regime_mult` |
| W4 prices | validation, and `activity_mult` via W5 |
| W5 Reactor Scale | `activity_mult` |
| W6 trader_style | `w_trader` (and even then, only past 30 closed positions) |

Proposed waves:
- **W9** — `derive/attention.py`, `symbol_attention`, HEATMAP screen with the
  score visible but explicitly labelled unvalidated.
- **W10** — `derive/attention_validate.py` + the "is this signal real?" panel.
  **Until W10 passes its ship criterion, the screen ranks by raw attention and
  says the priority score is unproven.**

**Acted on now (W0):** the W2 classifier prompt captures `play_type` and
conviction language from day one. Retrofitting it later would mean re-running
every historical post through the LLM.
