import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
print("posts:", conn.execute("SELECT COUNT(*) c FROM posts WHERE is_mock=0").fetchone()["c"])
print("media rows:", conn.execute("SELECT COUNT(*) c FROM post_media WHERE is_mock=0").fetchone()["c"])
print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
print("manas posts:", conn.execute("SELECT COUNT(*) c FROM posts WHERE handle='iManasArora' AND is_mock=0").fetchone()["c"])
conn.close()