import sqlite3

conn = sqlite3.connect(r"C:\Users\satta\Downloads\koreanguy\traderlog\data\traderlog.db")
conn.row_factory = sqlite3.Row
print("--- per-ticker state from positions (today) ---")
rows = conn.execute(
    """SELECT symbol, COUNT(DISTINCT handle) traders,
              SUM(CASE WHEN status IN ('open','partial') THEN 1 ELSE 0 END) holding,
              SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) exited
       FROM positions WHERE is_mock=0 GROUP BY symbol ORDER BY traders DESC"""
).fetchall()
for r in rows:
    print(dict(r))
print("--- position_events count by kind ---")
for r in conn.execute("SELECT kind, COUNT(*) n FROM position_events GROUP BY kind"):
    print(f"  {r['kind']}: {r['n']}")
# mention counts from post_class (would drive an 'used/mentioned' column post-W2)
try:
    for r in conn.execute("SELECT symbol FROM ("):
        pass
except Exception as exc:
    print("(symbols column on post_class is a JSON array; special aggregation needed for mentions)")
print("--- total positions ---", conn.execute("SELECT COUNT(*) FROM positions WHERE is_mock=0").fetchone()[0])
conn.close()