import sqlite3
conn = sqlite3.connect('data/coos.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables in coos.db:")
for row in cursor.fetchall():
    print("-", row[0])
conn.close()
