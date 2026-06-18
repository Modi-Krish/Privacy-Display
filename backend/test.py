import sqlite3
import os

db = sqlite3.connect(os.path.join(os.environ['APPDATA'], 'REAI', 'data', 'reai.db'))
c = db.cursor()
c.execute("SELECT answer FROM responses ORDER BY id DESC LIMIT 1;")
res = c.fetchone()
if res:
    print("LAST ANSWER IN DB:")
    print(repr(res[0]))
else:
    print("NO RESPONSES FOUND")
