import sqlite3
from pathlib import Path

conn = sqlite3.connect(
    r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db"
)
conn.row_factory = sqlite3.Row
print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
print("total posts:", conn.execute("SELECT COUNT(*) FROM posts WHERE is_mock=0").fetchone()[0])
print("post_media rows (real):", conn.execute("SELECT COUNT(*) FROM post_media WHERE is_mock=0").fetchone()[0])
print("--- per handle ---")
for r in conn.execute(
    "SELECT handle, COUNT(*) n FROM posts WHERE is_mock=0 GROUP BY handle ORDER BY n DESC"
):
    print(f"  {r['handle']}: {r['n']}")
print("--- traders active ---")
for r in conn.execute("SELECT handle, active FROM traders ORDER BY handle"):
    print(f"  {r['handle']}: active={r['active']}")
conn.close()
media = len(list(Path(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\media").glob("*")))
print("media files on disk:", media)