# SwingEdge Lite

A daily NSE swing-trading screener built on Manas Arora's bread-and-butter setup
plus the Korean builder's 5-stage architecture (Regime → Screen → Verify →
Track → Alert). Read-only paper-trading: no orders, no broker integration.

## Pipeline at a glance

```
fetch.py       OHLCV  ──▶ ohlcv.db
indicators.py  features ─▶ features.db
regime.py      ─▶ output/regime_today.json     (RISK_ON / CAUTION / RISK_OFF)
screen.py      ─▶ output/screen_today.csv      (every universe stock, graded)
verify.py      ─▶ output/candidates.csv        (Layer A + Layer B passes)
                  output/svro_arm_today.json   (Phase 2 prep)
                  output/candidates_history.csv (append-only)
track.py       ─▶ data/portfolio_state.db      (PENDING_CONFIRM → ACTIVE → EXITED_*)
render.py      ─▶ output/dashboard.html
notify.py      ─▶ Telegram (MarkdownV2)
```

## First-time setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -c "from scripts import _db; _db.init_schemas()"

export FYERS_TOKEN="..."
export TG_TOKEN="..."

bash run_daily.sh                  # Linux/macOS
powershell run_daily.ps1           # Windows
```

## Daily run order
`fetch → indicators → regime → screen → verify → track → render → notify`.
Every layer reads only files written by upstream layers. If any layer crashes,
downstream layers degrade gracefully.

## Weekly review
Run `python scripts/watchlist_helper.py` on Sunday. Suggestions only — it never
edits watchlist.csv.

## Key files
- `config.yaml` — thresholds, sizing, notify settings.
- `decisions.md` — answers to the 8 spec open questions; load-bearing.
- `BUILD_GUIDE.md` — master 16-step build plan.
- `spec.txt` — technical spec.
- `FUTURE.md` — rejected mid-build ideas (do NOT build until Phase 1 validated).
- `LIVE_DATA_FLOW.md` — Phase 2 intraday SVRO design via Fyers WebSocket.

## Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| `candidates.csv` empty all week | Thresholds too tight | Inspect `screen_today.csv` for `setup_pass=1` count |
| `Fyers token expired` | Daily token rotation | `python scripts/refresh_token.py` |
| Telegram silent | Bad token / chat_id | Check `logs/notify.log` |
| Tracker not exiting | Missing today's bar | Re-run fetch.py |

## 30-day gate
Phase 2 (intraday SVRO, hosted dashboard, more setups) is locked until Phase 1
has run live for 30 consecutive trading days **and** the tracker shows
hit-rate 35–55% with mean R-multiple > 1.0.
