# CONTRACTS

The interfaces between waves. A later wave is written against these, not against
whatever an earlier wave happened to produce. **If you change a shape here,
change this file in the same edit** — a model three sessions from now is going to
trust it without reading your code.

Two invariants run through everything and are enforced by `checks`:

1. **Every populated field cites the post it came from.** `evidence` maps
   `field_name -> post_id`. A field with no citation is dropped, not stored.
2. **Never infer a number that was not written down.** Anything the trader did
   not state goes in `unresolved[]`. A wrong price is worse than a missing one:
   the value of this log is that it is a factual record of what someone said.

---

## 1. Classifier output — `llm/classify.py`

One call per post. Tier: `cheap`.

```json
{
  "kind": "trade_event",
  "confidence": 0.91,
  "symbols": ["APOLLOTYRE"],
  "play_type": "breakout",
  "conviction_words": ["added 25% more"],
  "reason": "states an add and a trailed stop with prices"
}
```

`kind` is exactly one of:

| kind | means |
|---|---|
| `trade_event` | states an entry, add, stop, target, or exit on a position |
| `breadth` | daily market/situational commentary, no specific position |
| `watch_idea` | a name to watch, with or without a trigger level |
| `theme` | sector/theme discussion, EP or IPO chatter |
| `education` | a teachable principle, not tied to a live trade |
| `noise` | banter, replies to others, promotion, unrelated |

A post may be reclassified when its thread grows. `kind` is a property of the
post, not of the thread.

**`play_type`** — one of `ep | momentum_burst | breakout | pullback | vcp |
ipo_base | swing_range | unclear`. Only meaningful for `trade_event` and
`watch_idea`; `unclear` everywhere else. Read it off the post, never inferred
from the symbol, the sector, or what that trader usually does.

**`conviction_words`** — verbatim phrases indicating size or conviction
("starter", "half size", "went big"). Empty list when there are none. Never
inferred from tone.

Both feed the attention engine (`design/ATTENTION_ENGINE.md`), which treats
`unclear` as neutral — so an honest `unclear` costs nothing and a wrong guess
corrupts a ranking. **They are captured on the first classification pass on
purpose:** adding them at W9 would mean re-running every historical post through
an LLM to backfill.

---

## 2. Vision output — `llm/vision.py`

One call per image on a `trade_event` or `education` post. Tier: `vision`.
Stored in `post_media.vision_json`.

```json
{
  "chart_symbol": "APOLLOTYRE",
  "timeframe": "daily",
  "image_kind": "chart",
  "text_in_image": ["Buy above 1847", "SL 1790"],
  "annotated_levels": [
    {"kind": "entry",  "price": 1847, "source": "drawn arrow with label"},
    {"kind": "stop",   "price": 1790, "source": "horizontal red line, labelled SL"}
  ],
  "non_chart_evidence": [],
  "structure_note": "tight 6-week base, breakout candle on expanded volume",
  "confidence": 0.74,
  "unreadable": false
}
```

**`text_in_image` is transcription, not interpretation** — copy what is written,
including if it contradicts the post text. `annotated_levels[].source` must say
what in the picture justified the number. If the chart is unreadable, set
`unreadable: true` and leave the arrays empty rather than guessing.

**`image_kind`** is exactly one of `chart | order_confirmation | holdings |
watchlist | other | unknown`. A readable non-chart image is evidence, not an
unreadable chart. For it, `timeframe` is normally `unknown`,
`annotated_levels` is empty, and `non_chart_evidence[]` contains only visibly
printed values. Each item is exactly `{"kind", "value", "source"}`: `kind` is
one of `entry_price | average_price | last_price | quantity | pnl | return_pct`;
`value` is a finite number; and `source` names the exact visible field, row, or
label. Do not derive a return, price, or quantity from another visible number.
`non_chart_evidence` must be empty for `image_kind: "chart"` and for
`unreadable: true`.

For backwards-safe reading of archived `vision_json`, legacy payloads that lack
`image_kind` and `non_chart_evidence` normalize to `image_kind: "unknown"` and
an empty evidence array. Every new canonical serialization includes both keys.

Vision output is **evidence, not truth**: the reconciler weighs it against the
post text and may reject it. A price that appears only in an image and nowhere in
any post text is still citable — the `post_id` of the post carrying the image.

---

## 3. Reconciler output — `llm/reconcile.py`

The core contract. One call per changed thread. Tier: `smart`.
Input is the **whole thread** in chronological order plus vision output per image.
Output is the **complete current state**, re-derived from scratch every time.

Never patch incrementally. Incremental LLM state-diffing drifts within days and
cannot be tested against fixtures.

```json
{
  "symbol": "APOLLOTYRE",
  "status": "added",
  "entries":  [{"price": 1792, "date": "2026-08-04", "size_note": "starter", "post_id": "1953..."}],
  "adds":     [{"price": 1847, "date": "2026-08-11", "qty_pct": 25,  "post_id": "1957..."}],
  "stop":     {"price": 1790, "post_id": "1957...", "moved_from": 1740},
  "targets":  [{"price": 1980, "hit": false, "post_id": "1953..."}],
  "exits":    [],
  "net_result_pct": null,
  "holding_days": null,
  "confidence": 0.88,
  "unresolved": ["position size never stated in rupees or percent"],
  "evidence": {
    "symbol": "1953...",
    "entries[0].price": "1953...",
    "adds[0].price": "1957...",
    "stop.price": "1957..."
  }
}
```

Rules:

- `status` ∈ `open | added | partial | closed | scratched | unclear`.
  Use `unclear` freely. It is a valid, useful answer and far better than a
  confident wrong one.
- `net_result_pct` is populated **only** when the trader stated a result or when
  both entry and exit prices were stated. Never computed from market data —
  this log records what they *said*, not what actually happened.
- Every `evidence` value must be a `post_id` present in the input thread.
- Dotted paths in `evidence` address array elements: `entries[0].price`.

**Idempotence is testable and tested.** Same thread in → byte-identical state
out. The golden fixtures assert this.

---

## 4. Link proposal — `llm/link.py`

For standalone posts that reference a symbol with an open position but do not
reply into its thread (*"booked XYZ, +18%"* three weeks after the entry). Tier:
`smart`.

```json
{
  "post_id": "1961...",
  "proposed_position_id": "a3f9...",
  "proposed_event": {"kind": "exit", "price": 2104, "qty_pct": 100},
  "confidence": 0.62,
  "reasoning": "same symbol, only open position for this handle, 'booked' implies full exit",
  "alternatives": ["could be a new trade closed same-day"]
}
```

`confidence >= reconcile.link_confidence_floor` (default 0.8) → applied.
Below → a `review_queue` row. **Never auto-merge below the floor.** This is the
accuracy ceiling of the whole tool and the one place ambiguity is unavoidable.

---

## 5. Provider interface — `llm/provider.py`

```python
from traderlog.llm import provider

result = provider.chat(
    tier="smart",              # cheap | smart | vision
    system="...",
    user="...",                # str, or a list of multimodal content parts
    task="reconcile",          # for the llm_runs ledger
    ref_id=position_id,
    json_schema=True,          # ask for strict JSON and parse it
)
# -> ProviderResult(content=str|dict, model=str, provider=str, usage=dict, run_id=int)
```

**Call sites name a tier, never a model.** Model ids live only in `config.yaml`.
This is what makes the local-LLM migration a config edit instead of a rewrite.

Each tier is an **ordered fallback chain**, not one model. Stealth and free
endpoints get renamed or withdrawn without notice; the provider walks the chain
on failure and records which model actually answered in `llm_runs.model`. A call
that falls through the whole chain raises `ProviderExhausted`.

Every call writes an `llm_runs` row — success or failure, with tokens, cost and
latency. `daily_budget_usd: 0.0` means free models only; the provider refuses a
paid call rather than silently spending.

---

## 6. Multimodal content parts

For vision calls, `user` is a list, matching the OpenAI/OpenRouter shape adopted
from `manas_os/agents/vision.py`:

```python
[
  {"type": "text", "text": "..."},
  {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
]
```

Images are read from `data/media/`, never re-downloaded from X.

---

## 7. Ingest interface — `ingest/xfetch.py`  *(W1 builds to this)*

```python
def fetch_timeline(handle: str, since: str | None) -> list[RawPost]: ...
```

`RawPost` is a dataclass:

```python
@dataclass
class RawPost:
    post_id: str
    handle: str
    conversation_id: str | None
    in_reply_to: str | None
    ts_utc: str
    text: str
    url: str
    media: list[RawMedia]      # RawMedia(url, media_type)
    raw: dict                  # everything captured, archived verbatim
```

Contract requirements:

- **Timeline WITH replies.** Self-replies are where adds, stop moves and exits
  live. A fetcher that returns only top-level posts satisfies the type signature
  and silently defeats the entire tool.
- **Archive before parse.** Write `raw` and every media file to `data/raw/` and
  `data/media/` before any parsing. Nothing downstream may re-fetch: threads run
  for weeks, X's search window does not, and posts get deleted.
- **Idempotent.** Re-running for the same `since` must not duplicate rows.
  Dedupe on `post_id`.
- **`since=None`** means "as far back as you can reasonably go" for a new trader.

Swapping to the official X API means reimplementing this one function.

---

## 8. API endpoints

Base `http://127.0.0.1:8100`. One named fetch function per endpoint in
`ui/src/api.js` — no generic client.

| Endpoint | Serves | Screen |
|---|---|---|
| `GET /api/health` | liveness + counts + `is_mock` flag | all |
| `GET /api/feed` | recent posts + class + resolved event + thread relationships | TODAY |
| `GET /api/review` | open review-queue items | TODAY |
| `POST /api/review/{id}` | resolve one (`accepted`/`rejected`) | TODAY |
| `GET /api/traders` | roster + style summary (rows carry `stop_stated_pct` / `stop_honored_pct` from `trader_style`, null when absent) | TRADERS |
| `GET /api/traders/{handle}` | profile, style card, open/closed, preach score | TRADERS |
| `GET /api/positions` | the ledger, filterable | LEDGER |
| `GET /api/positions/{id}` | event timeline + source posts + media | LEDGER |
| `GET /api/breadth` | `regime_daily` + `breadth_daily` + trader stances (history rows carry `advances`/`declines` joined from `breadth_daily` by `trade_date`) | MARKET |
| `GET /api/ideas` | watch ideas + themes grouped by symbol | IDEAS |
| `GET /api/library` | edu items + their preach links | LIBRARY |
| `GET /api/symbol/{symbol}` | `{"symbol", "validated", "prices", "source", "positions", "mentions", "is_mock"}` — price pane from `daily_prices` (bhavcopy NSE EQ) + corpus context for one symbol | SYMBOL |
| `GET /api/radar` | cited Symbol co-attention, validation coverage debt, and requested filters | RADAR |

Every payload carries `"is_mock": true` while seeded data is present, so a screen
can say so out loud rather than looking real. Removing the mock data must not
change any response *shape* — only make the arrays empty.

`GET /api/symbol/{symbol}`: `prices` rows are exactly
`{"trade_date", "open", "high", "low", "close", "volume"}` from `daily_prices`
(ascending). `validated` is true only when rows exist — bhavcopy is the
canonical NSE EQ source, and `validated: false` means `prices: []` (the UI says
which part is missing). `source` is `"bhavcopy"` when validated, else `null`.
`positions` are the LEDGER-style rows for the symbol; `mentions` are
`watch_ideas` rows (same projection as `/api/ideas` mentions). Empty arrays are
normal while the corpus is sparse.

`GET /api/radar?days=30&min_traders=2` is the deterministic INS-1 Symbol
co-attention endpoint. `days` is an integer from 1 through 730 (default 30),
and `min_traders` is an integer from 1 through 17 (default 2). The request's
Asia/Kolkata calendar date is the inclusive window end; the preceding `days - 1`
Asia/Kolkata calendar dates are included. Source timestamps remain UTC strings,
but their calendar date is derived in Asia/Kolkata. Only `trade_event`, `watch_idea`, and `theme`
classifier kinds are eligible.

Symbols come from the strictly parsed JSON array in `post_class.symbols`. Each
string is trimmed, has one leading `#` removed, then becomes uppercase; empty
or non-string items are excluded and counted. A post contributes at most one
mention per normalized symbol. Handles keep their exact evidence value but are
compared after trimming one leading `@` and case-folding. A symbol is validated
only when `daily_prices` has at least one row for it.

```json
{
  "requested": {"days": 30, "min_traders": 2},
  "window": {"start_date": "2026-08-01", "end_date": "2026-08-30"},
  "classified_eligible_post_count": 42,
  "included_mention_count": 57,
  "coverage_debt": {
    "invalid_symbol_json_count": 1,
    "invalid_symbol_value_count": 2,
    "invalid_timestamp_count": 0,
    "invalid_handle_count": 0,
    "unvalidated_mention_count": 3,
    "unvalidated_symbols": [
      {"symbol": "EXAMPLE", "mention_count": 3, "distinct_trader_count": 2}
    ]
  },
  "co_attention": [
    {
      "symbol": "APOLLOTYRE",
      "mention_count": 5,
      "distinct_trader_count": 3,
      "first_mention_ts": "2026-08-02T09:00:00+00:00",
      "last_mention_ts": "2026-08-06T10:00:00+00:00",
      "strongest_cluster": {
        "start_date": "2026-08-02",
        "end_date": "2026-08-06",
        "distinct_trader_count": 3,
        "mention_count": 5
      },
      "anchor_date": "2026-08-03",
      "anchor_open": 1792.0,
      "ret_1d": 0.0142,
      "ret_5d": 0.0621,
      "ret_10d": 0.0987,
      "ret_20d": 0.1243,
      "n_eligible": 4,
      "n_missing": 0,
      "tape_state": "computed",
      "evidence": [
        {
          "post_id": "123",
          "handle": "@author",
          "ts_utc": "2026-08-02T09:00:00+00:00",
          "url": "https://x.com/author/status/123",
          "text": "exact archived post text",
          "kind": "watch_idea",
          "confidence": 0.91
        }
      ]
    }
  ],
  "is_mock": false
}
```

`co_attention` contains validated symbols meeting `min_traders` only. Its order
is strongest cluster distinct-trader count descending, cluster end date
descending, total distinct-trader count descending, then symbol ascending. A
strongest cluster is an inclusive seven-calendar-day Asia/Kolkata window. Its
`start_date` is always the actual boundary (`end_date - 6`), even if the first
mention arrives later. It maximizes
distinct normalized traders, then mention count, then the most recent window
end date; this makes equal cases reproducible. Evidence is chronological and
retains the exact source fields. `coverage_debt` names unvalidated symbols
separately and counts malformed JSON, rejected symbol values, timestamps, and
handles rather than substituting values.

**INS-2 tape-after-mention fields are ADDITIVE on every `co_attention` row**
(2026-08-27; derivation in `derive/tape.py`, policy locked and unit-tested
there). The anchor is the symbol's FIRST mention inside the window. The locked
IST boundary: a post strictly before 09:00 IST whose IST date has a session in
the symbol's `daily_prices` anchors to THAT session's open; every other time
(09:00:00 IST or later, or a session-less date) anchors to the next available
session strictly after the post's IST date. `anchor_date`/`anchor_open` are
that anchor session and its open. `ret_1d/5d/10d/20d` are forward CLOSE
returns `close[i+k] / open[anchor] - 1` at +1/+5/+10/+20 trading sessions of
the symbol's own series — holidays fall out because sessions are the actual
price rows, never calendar offsets. A horizon with no session or a null close
is `null`, never zero, and the anchor session's own close is never used (no
close-to-close ambiguity). `n_eligible`/`n_missing` count horizons with/without
a value (they sum to 4). `tape_state` is exactly one of `computed |
no_nse_price_history | no_forward_session | missing_timestamp | capped`; every
non-`computed` row carries null tape fields and no percentages. Only the first
`tape.MAX_TAPE_SYMBOLS` (200) ranked symbols get tape within one request; the
rest are marked `capped`.

---

## 9. Attention engine — `symbol_attention`, `attention_validation`

**Specified, not built.** Full spec: `design/ATTENTION_ENGINE.md`. Tables exist in
`db/schema.sql` so later waves have a target; nothing writes them yet. Depends on
W2, W4, W5, W6 — every input is missing today.

Three commitments that are decisions rather than implementation detail, restated
here because this is the file a later wave will read:

1. **Talk and money are never summed.** An entry with a stated stop weighs ~6× a
   bare mention. It is the only event where the author showed their risk.
2. **`priority` decays with age since first mention** (1.00 at 0–2 sessions →
   0.10 at 16+). A version where more attention monotonically raises the score is
   a machine for buying crowded tops. Reject it in review.
3. **The score is unproven until backtested.** Ship criterion: top decile beats
   the NIFTYMIDSML400 median at +10 sessions over ≥60 clusters. Until then the
   screen ranks by raw attention and says so on the page.

Single writers: `derive/attention.py` and `derive/attention_validate.py`.

---

## 10. STATE.json

Written by `checks`, never by hand.

```json
{
  "wave": "W0",
  "last_verified_commit": "abc1234",
  "updated_at": "2026-08-23T12:00:00+00:00",
  "checks": {"db": "pass", "ingest": "not_built_yet", "...": "..."},
  "counts": {"traders": 6, "posts": 48, "positions": 12, "review_open": 3},
  "blocked_on": null
}
```

Check values: `pass` · `fail: <reason>` · `stale_<n>d` · `not_built_yet` ·
`dry_run`.

---

## 11. Model-work provenance

`design/MODEL_WORK_LOG.jsonl` is the append-only evidence ledger for model-role
contributions. Its complete schema and close procedure are binding in
`design/MODEL_ATTRIBUTION.md`. Each completed handoff must carry one or more
exact `Attribution-ID: <id>` lines that resolve to its ledger records.

The `checks` harness validates the ledger independently of the production
database: JSONL syntax, unique IDs, required fields/enums, completion-report
existence and round-trip ID/path matching, and attribution on every completed
handoff. Unknown exact models remain `unknown` or `exact-model-unavailable`;
they are never inferred from task names or files.

`not_built_yet` is honest for an unbuilt wave, but it means a green run does
**not** prove the tool works end to end. **Each wave flips its own check to a
real assertion as part of that wave's done-test** — otherwise the harness quietly
becomes decorative (audit finding I1).
