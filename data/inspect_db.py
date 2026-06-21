import sqlite3
import shutil

db_path = "data/coos_copy.db"
shutil.copy2("data/coos.db", db_path)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute(
    "SELECT persona_id, thread_id, role_id, COUNT(*) FROM chat_transcripts "
    "GROUP BY persona_id, thread_id, role_id"
)
rows = cursor.fetchall()
print("=== DISTINCT PERSONAS, THREADS AND ROLES ===")
for r in rows:
    print(f"Persona ID: {r[0]} | Thread ID: {r[1]} | Role ID: {r[2]} | Count: {r[3]}")

conn.close()
