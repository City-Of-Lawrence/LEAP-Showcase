import sqlite3

DB_PATH = r"LEAPMailings_clean.sqlite"
TABLE_NAME = "Outreach_Master_Unified"
ID_COL = "id"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute(f'PRAGMA table_info("{TABLE_NAME}")')
all_columns = [col[1] for col in cur.fetchall()]
compare_cols = [c for c in all_columns if c != ID_COL]
group_by_clause = ", ".join(f'"{c}"' for c in compare_cols)

sql = f"""
    SELECT MIN("{ID_COL}") AS keep_id, COUNT(*) AS cnt
    FROM "{TABLE_NAME}"
    GROUP BY {group_by_clause}
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT 20
"""
cur.execute(sql)

for row in cur.fetchall():
    print(row)

conn.close()