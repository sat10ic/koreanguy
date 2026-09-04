import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
print("total posts:", conn.execute("SELECT COUNT(*) FROM posts WHERE is_mock=0").fetchone()[0])
print("media rows:", conn.execute("SELECT COUNT(*) FROM post_media WHERE is_mock=0").fetchone()[0])
print("--- posts per handle ---")
for r in conn.execute("SELECT handle, COUNT(*) n FROM posts WHERE is_mock=0 GROUP BY handle ORDER BY n DESC"):
    print(f"  {r['handle']}: {r['n']}")
print("--- traders active ---")
for r in conn.execute("SELECT handle, active FROM traders ORDER BY handle"):
    print(f"  {r['handle']}: {r['active']}")
conn.close()