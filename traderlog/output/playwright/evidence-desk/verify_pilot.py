import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
print("post_class rows:", conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0])
print("vision rows (non-null vision_json):",
      conn.execute("SELECT COUNT(*) FROM post_media WHERE vision_json IS NOT NULL").fetchone()[0])
print("--- kind distribution ---")
for r in conn.execute("SELECT kind, COUNT(*) n FROM post_class GROUP BY kind ORDER BY n DESC"):
    print(f"  {r['kind']}: {r['n']}")
print("--- the two vision rows ---")
for r in conn.execute("SELECT post_id, idx, image_kind, chart_symbol FROM post_media WHERE vision_json IS NOT NULL"):
    print(f"  {r['post_id']}/{r['idx']}: {r['image_kind']} {r['chart_symbol'] or ''}")
conn.close()