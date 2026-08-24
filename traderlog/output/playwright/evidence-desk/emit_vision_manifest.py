"""Emit the manifest of vision rows needing first-party replacement."""
import json
import sqlite3
import sys
from pathlib import Path

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """SELECT m.post_id, m.idx, m.local_path, m.vision_json, m.vision_model
       FROM post_media m WHERE m.is_mock=0
       AND (m.vision_model LIKE 'deepseek-v4-flash-vision-exp (this chat report)%' OR m.vision_json IS NULL)"""
).fetchall()
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\satta\Downloads\koreanguy\traderlog\output\playwright\evidence-desk\vision_redo_manifest.jsonl")
third_party = 0
unreadable = 0
null = 0
with out.open("w", encoding="utf-8") as fh:
    for r in rows:
        vj = json.loads(r["vision_json"]) if r["vision_json"] else None
        unread = bool(vj and vj.get("unreadable"))
        if r["vision_json"] is None:
            null += 1
            src = "null"
        elif unread:
            unreadable += 1
            src = "unreadable"
        else:
            third_party += 1
            src = "assisted"
        fh.write(json.dumps({"post_id": r["post_id"], "idx": r["idx"],
                             "local_path": r["local_path"], "current": src}) + "\n")
print(f"manifest written: {third_party} assisted (to replace), {unreadable} unreadable (to replace), {null} null (pending)")
conn.close()