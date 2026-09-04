"""Pilot: store a small, fully-audited classify+vision slice via the validated
apply_* functions (this-chat LLM work). source label marks it as chat-audited.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import sqlite3

from traderlog.llm import classify, vision

DB = r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db"
SOURCE = "deepseek-v4-flash-vision-exp (this chat report)"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def cls(post_id, payload):
    classify.apply_verified_classification(conn, post_id, payload, source=SOURCE)
    conn.commit()
    print(f"  classified {post_id} -> {payload['kind']}")

def vis(post_id, idx, payload):
    vision.apply_verified_vision(conn, post_id, idx, payload, source=SOURCE)
    conn.commit()
    print(f"  visioned {post_id}/{idx} -> {payload.get('image_kind')}")

NOISE = {"kind": "noise", "confidence": 0.99, "symbols": [], "play_type": "unclear",
         "conviction_words": [], "reason": "cricket/celebrity news, unrelated to markets."}

batch = 0
# --- classifications (14) ---
cls("2091579786334482477", NOISE)
cls("2091577527215223291", NOISE)
cls("2091542345296846871", NOISE)
cls("2091540293846024549", NOISE)
cls("2091441690771062920", NOISE)
cls("2091422320728654282", {"kind": "noise", "confidence": 0.8, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "terse remark; no symbol/level/trade stated."})
cls("2091418106598248619", {"kind": "education", "confidence": 0.8, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "general principle (price action); no position or price."})
cls("2091385387268940106", NOISE)
cls("2091345568480248310", NOISE)
cls("2091197482713890905", {"kind": "education", "confidence": 0.8, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "general market-structure principle; no position."})
cls("2091181054552137815", {"kind": "noise", "confidence": 0.7, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "vague encouragement; no symbol or level."})
cls("2091145546887201255", {"kind": "watch_idea", "confidence": 0.85,
    "symbols": [], "play_type": "breakout",
    "conviction_words": [],
    "reason": "asks which breakout was missed; the four NSE names + levels are shown in the attached chart, not the text."})
cls("2091100962375258264", {"kind": "noise", "confidence": 0.6, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "cryptic '30/75 usually'; no context."})
cls("2091094235131109810", {"kind": "education", "confidence": 0.75, "symbols": [], "play_type": "unclear",
    "conviction_words": [], "reason": "trailing-stop method statement; cites past MOLBIO example, no current price."})

# --- vision: breakout montage (tradinghustlr post, media idx 0) ---
vis("2091145546887201255", 0, {
    "chart_symbol": None, "timeframe": "daily", "image_kind": "chart",
    "text_in_image": [
        "BLUESPRING ENTERPRISES LTD 128.98 (+9.34%)",
        "FINEOTEX CHEMICAL LIMITED 47.43 (+8.91%)",
        "RATEGAIN TRAVEL TECHN LTD 990.05 (+4.91%)",
        "AEROFLEX INDUSTRIES LTD 503.00 (+5.83%)",
    ],
    "annotated_levels": [
        {"kind": "resistance", "price": 44.79, "source": "FINEOTEX chart breakout line labelled 44.79"},
        {"kind": "resistance", "price": 955.30, "source": "RATEGAIN chart breakout line labelled 955.30"},
        {"kind": "resistance", "price": 471.30, "source": "AEROFLEX chart breakout line labelled 471.30"},
    ],
    "non_chart_evidence": [],
    "structure_note": "Four-panel daily breakout montage; older UPPER panel charts present, sheet is a TradingView snapshot 2026-08-22 18:17.",
    "confidence": 0.85, "unreadable": False,
})

# --- vision: RATEGAIN holdings strip (find its post_id/idx) ---
row = conn.execute(
    "SELECT post_id, idx FROM post_media WHERE local_path LIKE '2090713569793126757%' AND is_mock=0 LIMIT 1"
).fetchone()
if row:
    vis(row["post_id"], row["idx"], {
        "chart_symbol": "RATEGAIN", "timeframe": "unknown", "image_kind": "holdings",
        "text_in_image": ["RATEGAIN EQ", "HOLDING"],
        "annotated_levels": [],
        "non_chart_evidence": [
            {"kind": "quantity", "value": 4300, "source": "HOLDING row shows 4,300"},
            {"kind": "average_price", "value": 955.00, "source": "HOLDING row price column 955.00"},
            {"kind": "last_price", "value": 987.95, "source": "HOLDING row LTP 987.95"},
            {"kind": "pnl", "value": 141685, "source": "HOLDING row +1,41,685.00"},
        ],
        "structure_note": "Broker holdings row for RATEGAIN EQ.",
        "confidence": 0.95, "unreadable": False,
    })
else:
    print("  (no RATEGAIN holdings media row found)")

conn.commit()
print("pilot stored")
conn.close()