import sqlite3, uuid, os

db_path = os.path.join(os.path.dirname(__file__), "coos.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

seg_id = str(uuid.uuid4())
params = {
    "id": seg_id,
    "ref_id": "d7773f80-ab34-4ad5-b48e-df6d6d4ef268",
    "uid": "ec730653-702e-4f68-bfbc-c9e929c05c07",
    "rid": "dcd6cb12-1cbe-4eab-8b7d-03d6a490f654",
    "mins": 0,
    "desc": "test from python",
}
try:
    cursor.execute(
        "INSERT INTO daily_reflection_segments "
        "(id, reflection_id, user_id, role_id, start_time, end_time, "
        "activity_minutes, ai_description, is_draft, is_reviewed) "
        "VALUES (:id, :ref_id, :uid, :rid, '00:00', '00:00', :mins, :desc, 1, 0)",
        params
    )
    conn.commit()
    print("INSERT OK:", seg_id)
except Exception as e:
    print("ERROR:", type(e).__name__, e)

# Also check how many segments exist
cursor.execute("SELECT COUNT(*) as cnt FROM daily_reflection_segments")
print("Total segments:", cursor.fetchone()["cnt"])
conn.close()
