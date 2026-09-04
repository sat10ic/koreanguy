import json
import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """SELECT post_id, idx, local_path FROM post_media
       WHERE is_mock=0 AND vision_json IS NOT NULL
         AND vision_model LIKE 'deepseek-v4-flash-vision-exp (this chat report)%'
         AND vision_model NOT LIKE '%first-party%'
         AND json_extract(vision_json,'$.unreadable')=0
       ORDER BY post_id, idx LIMIT 40"""
).fetchall()
print("remaining assisted (non-first-party) rows:", len(rows))
for r in rows:
    print(f"  {r['post_id']}/{r['idx']} {r['local_path']}")
conn.close()