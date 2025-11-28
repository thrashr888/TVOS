import duckdb
from tvos.config import Config

def check_db():
    con = duckdb.connect(Config.DUCKDB_PATH, read_only=True)
    result = con.execute("SELECT count(*) FROM events").fetchall()
    print(f"Count: {result[0][0]}")
    
    rows = con.execute("SELECT event_id, source, text_payload FROM events LIMIT 5").fetchall()
    for row in rows:
        print(row)

if __name__ == "__main__":
    check_db()
