import os
import sqlite3

root = r"C:\Users\satta\AppData\Local\Google\Chrome\User Data"
for entry in sorted(os.listdir(root)):
    prof = os.path.join(root, entry)
    cookies = os.path.join(prof, "Network", "Cookies")
    if not os.path.isfile(cookies):
        continue
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % cookies, uri=True)
        rows = conn.execute(
            "SELECT host_key, name FROM cookies "
            "WHERE host_key LIKE '%.x.com' OR host_key LIKE '%twitter.com'"
        ).fetchall()
        names = sorted({r[1] for r in rows})
        auth = [n for n in names if n in ("auth_token", "ct0", "twid")]
        print(f"== {entry}: {len(rows)} x-cookies; auth-ish: {auth}; all: {names[:12]}")
        conn.close()
    except Exception as exc:
        print(f"== {entry}: ERR {exc}")