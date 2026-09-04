import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
print("--- vision rows by model label (non-null vision_json) ---")
for r in conn.execute(
    "SELECT COALESCE(vision_model,'(null)') m, COUNT(*) n, "
    "SUM(CASE WHEN json_extract(vision_json,'$.unreadable')=1 THEN 1 ELSE 0 END) unread "
    "FROM post_media WHERE is_mock=0 GROUP BY m ORDER BY n DESC"
):
    print(f"  {r['m']}: {r['n']} rows ({r['unread']} unreadable)")
print("--- rpmrpm4 + thechartist26 media rows (the 60 to redo) ---")
rows = conn.execute(
    """SELECT m.post_id, m.idx, m.local_path, m.vision_model
       FROM post_media m JOIN posts p ON p.post_id = m.post_id
       WHERE p.is_mock=0 AND p.handle IN ('rpmrpm4','thechartist26') ORDER BY m.post_id, m.idx"""
).fetchall()
print(len(rows), "rows")
for r in rows:
    print(f"  {r['post_id']}/{r['idx']} {r['local_path']} [{r['vision_model']}]")
conn.close()