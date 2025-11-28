import time
import os
import zmq
import uuid
import sqlite3
import shutil
import glob
from datetime import datetime, timedelta
from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config


def get_chrome_history_db():
    """Finds Chrome History DB on macOS"""
    # Check env var first
    env_path = os.getenv("CHROME_HISTORY_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # Typical path on macOS
    path = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default/History"
    )
    if os.path.exists(path):
        return path
    return None


def ingest_browser_history():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://{Config.ZMQ_HOST}:{Config.ZMQ_PULL_PORT}")

    db_path = get_chrome_history_db()
    if not db_path:
        print("Could not find Chrome History database.")
        return

    print(f"Monitoring Chrome History at: {db_path}")

    last_check_time = datetime.now() - timedelta(minutes=1)
    # Convert to WebKit/Chrome timestamp (microseconds since 1601-01-01)
    # But easier is just to track max visit ID

    last_visit_id = 0

    # Initial sync: find max id
    temp_db = "/tmp/chrome_history_copy.db"
    try:
        shutil.copy2(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM visits")
        res = cursor.fetchone()
        if res and res[0]:
            last_visit_id = res[0]
            print(f"Starting from visit ID: {last_visit_id}")
        conn.close()
    except Exception as e:
        print(f"Error initializing: {e}")

    try:
        while True:
            # Polling interval
            time.sleep(10)

            try:
                # Copy DB to avoid locking issues
                shutil.copy2(db_path, temp_db)

                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()

                # Join visits with urls to get titles and URLs
                # Chrome timestamps are microseconds since 1601-01-01
                query = """
                    SELECT visits.id, visits.visit_time, urls.url, urls.title, visits.visit_duration 
                    FROM visits 
                    JOIN urls ON visits.url = urls.id 
                    WHERE visits.id > ? 
                    ORDER BY visits.id ASC
                """

                cursor.execute(query, (last_visit_id,))
                rows = cursor.fetchall()

                for row in rows:
                    visit_id, visit_time, url, title, duration = row
                    last_visit_id = visit_id

                    # Convert Chrome timestamp to unix ms
                    # 11644473600 is seconds between 1601 and 1970
                    timestamp_ms = (visit_time / 1000) - (11644473600 * 1000)

                    event = EventPayload()
                    event.event_id = str(uuid.uuid4())
                    event.timestamp_ms = int(timestamp_ms)
                    event.source = "chrome_history"
                    event.text_payload = f"Visited: {title or url}"

                    event.metadata["url"] = url
                    event.metadata["title"] = title or ""
                    event.metrics["duration_us"] = float(duration)

                    sender.send(event.SerializeToString())
                    print(f"Captured visit: {title[:50]}...")

                conn.close()

            except Exception as e:
                print(f"Error reading history: {e}")

    except KeyboardInterrupt:
        print("\nStopping browser ingestion...")
        if os.path.exists(temp_db):
            os.remove(temp_db)


if __name__ == "__main__":
    ingest_browser_history()
