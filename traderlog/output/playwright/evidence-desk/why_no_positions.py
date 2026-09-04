import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
cols = [r[1] for r in conn.execute("PRAGMA table_info(positions)")]
print("positions cols:", cols)
rows = conn.execute("SELECT * FROM positions").fetchall()
print("--- positions ---")
for r in rows:
    d = dict(r)
    print({k: d[k] for k in ("position_id", "symbol", "handle", "status") if k in d})
total = conn.execute("SELECT COUNT(*) FROM posts WHERE is_mock=0").fetchone()[0]
classified = conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0]
print(f"posts: {total} | post_class rows: {classified} | unclassified: {total - classified}")
for t in ("watch_ideas", "themes", "edu_items", "breadth_notes"):
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n}")
    except Exception as exc:
        print(f"{t}: ERR {exc}")
conn.close()