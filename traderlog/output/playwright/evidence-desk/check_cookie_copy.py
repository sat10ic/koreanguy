import sqlite3

copies = [
    r"C:\Users\satta\AppData\Local\Temp\dsh-x-capture-profile\Default\Network\Cookies",
    r"C:\Users\satta\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
]
for p in copies:
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
        rows = conn.execute(
            "SELECT host_key, name, LENGTH(encrypted_value) FROM cookies "
            "WHERE name IN ('auth_token','ct0','twid')"
        ).fetchall()
        print(p.split("User Data")[-1].split("dsh-x")[-1], "->", rows)
        conn.close()
    except Exception as exc:
        print(p, "ERR", exc)