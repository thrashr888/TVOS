import time
import zmq
import uuid
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

def ingest_app_logs(log_file_path="/data/api.log"):
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://{Config.ZMQ_HOST}:{Config.ZMQ_PULL_PORT}")

    print(f"Starting app log ingestion from {log_file_path}...")

    # Wait for file to exist
    while not os.path.exists(log_file_path):
        print(f"Waiting for {log_file_path} to be created...")
        time.sleep(5)

    try:
        with open(log_file_path, "r") as f:
            # Go to the end of the file
            f.seek(0, os.SEEK_END)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                line = line.strip()
                if not line:
                    continue

                event = EventPayload()
                event.event_id = str(uuid.uuid4())
                event.timestamp_ms = int(time.time() * 1000)
                event.source = "tvos_api"
                event.text_payload = line
                
                # Basic metadata
                event.metadata["log_type"] = "app_log"
                
                sender.send(event.SerializeToString())
                # print(f"Sent app log: {line[:50]}...")

    except KeyboardInterrupt:
        print("\nStopping app log ingestion...")
    except Exception as e:
        print(f"Error in app log ingestion: {e}")

if __name__ == "__main__":
    ingest_app_logs()

