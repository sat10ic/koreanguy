import os
import sqlite3

p = r"C:\Users\satta\Downloads\koreanguy\traderlog\data\browser_profile\Default\Network\Cookies"
if not os.path.exists(p):
    print("no cookies db")
    raise SystemExit
conn = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
rows = conn.execute(
    "SELECT host_key, name, LENGTH(encrypted_value) FROM cookies "
    "WHERE host_key LIKE '%x.com' OR host_key LIKE '%twitter.com'"
).fetchall()
print("x/twitter cookies:", len(rows))
for r in rows[:15]:
    print(" ", r[0], "|", (r[1] or "")[:40], "|", r[2], "bytes")