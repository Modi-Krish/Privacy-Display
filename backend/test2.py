import sqlite3
import os

db = sqlite3.connect(os.path.join(os.environ['APPDATA'], 'REAI', 'data', 'reai.db'))
c = db.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(c.fetchall())
