import json
import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """SELECT p.post_id, p.handle, p.ts_ist, p.text,
              (SELECT COUNT(*) FROM post_media m WHERE m.post_id=p.post_id AND m.is_mock=0) AS media_n,
              (SELECT GROUP_CONCAT(m.local_path, '|') FROM post_media m WHERE m.post_id=p.post_id AND m.is_mock=0 ORDER BY m.idx) AS media_paths
       FROM posts p
       WHERE p.is_mock=0
       ORDER BY p.ts_ist DESC
       LIMIT 14"""
).fetchall()
for r in rows:
    print("=" * 70)
    print(f"{r['handle']} | {r['ts_ist']} | media={r['media_n']} | {r['post_id']}")
    print((r["text"] or "").replace("\n", " ")[:220])
    if r["media_paths"]:
        print("  media:", r["media_paths"][:300])
conn.close()