import sqlite3

conn = sqlite3.connect('coos.db')
conn.row_factory = sqlite3.Row

print('=== roles ===')
for r in conn.execute('SELECT id, user_id, slug, display_name, is_active FROM roles').fetchall():
    print(dict(r))

print('\n=== daily_reflections ===')
for r in conn.execute('SELECT id, user_id, role_id, reflection_date FROM daily_reflections').fetchall():
    print(dict(r))

print('\n=== daily_reflection_segments ===')
for s in conn.execute('SELECT id, reflection_id, role_id, user_id, is_draft, is_reviewed, xp_settled FROM daily_reflection_segments').fetchall():
    print(dict(s))

print('\n=== raw_tracking_logs by (date, role_id) ===')
for r in conn.execute("""
    SELECT substr(timestamp,1,10) as day, role_id, COUNT(*) as cnt
    FROM raw_tracking_logs
    GROUP BY day, role_id
    ORDER BY day DESC
    LIMIT 20
""").fetchall():
    print(dict(r))

print('\nTotal raw_tracking_logs:', conn.execute('SELECT COUNT(*) FROM raw_tracking_logs').fetchone()[0])

print('\n=== users ===')
for r in conn.execute('SELECT id, current_xp, lifetime_xp FROM users').fetchall():
    print(dict(r))

conn.close()
