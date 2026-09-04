"""Store first-party vision payloads (manifest JSONL) via the validated path.

Each manifest line: {"post_id": ..., "idx": ..., "payload": {...CONTRACTS 2...}}
Loop calls vision.apply_verified_vision + commit. Used to replace the 60
third-party-assisted rows and the 109 honest-unreadable rows with first-party
transcriptions when the vision-capable session is live.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\satta\Downloads\koreanguy")

import sqlite3  # noqa: E402

from traderlog.llm import vision  # noqa: E402

SOURCE = "deepseek-v4-flash-vision-exp (this chat report - first-party)"
manifest = Path(sys.argv[1])
conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
n = 0
for line in manifest.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    item = json.loads(line)
    vision.apply_verified_vision(conn, item["post_id"], item["idx"], item["payload"], source=SOURCE)
    conn.commit()
    n += 1
print(f"stored {n} vision rows")
conn.close()