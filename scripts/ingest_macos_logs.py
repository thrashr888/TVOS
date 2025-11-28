import subprocess
import json
import zmq
import uuid
import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

def ingest_logs(predicate=None):
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://localhost:{Config.ZMQ_PULL_PORT}")
    
    cmd = ["log", "stream", "--style", "json"]
    if predicate:
        cmd.extend(["--predicate", predicate])
        
    print(f"Starting MacOS log ingestion... Command: {' '.join(cmd)}")
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        # 'log stream --style json' outputs a JSON array wrapper or continuous objects?
        # Actually it often outputs a list of objects "[...]" then more "[...]"
        # But typically streaming mode sends events as they come.
        # Let's try to parse line by line. MacOS log stream json format is tricky.
        # It outputs: 
        # [
        #  {...},
        #  {...}
        # ]
        # It might be hard to parse as continuous stream if it's wrapped in [].
        # Actually, 'log stream --style ndjson' exists on some versions? No.
        # Standard 'json' style outputs an array.
        # We might need to buffer or handle the "[\n" and ",\n" and "]\n".
        
        # Workaround: Use grep or sed to clean it up, or manual parsing.
        # A simpler way is to just read line by line and strip commas/brackets.
        
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            if line == "[" or line == "]": continue
            if line.startswith("],"): continue # unlikely
            
            if line.endswith(","):
                line = line[:-1]
                
            try:
                entry = json.loads(line)
                
                # Handle list of entries if multiple on one line (rare)
                if isinstance(entry, list):
                    entries = entry
                else:
                    entries = [entry]
                    
                for log in entries:
                    # Skip if no message
                    if "eventMessage" not in log:
                        continue
                        
                    event = EventPayload()
                    event.event_id = str(uuid.uuid4())
                    
                    # Parse timestamp (e.g. "2023-10-27 10:00:00.123456-0700")
                    # Or use 'timestamp' field? log stream json usually has 'timestamp'
                    ts_str = log.get("timestamp", "")
                    try:
                        # Python 3.11 fromisoformat handles most
                        dt = datetime.datetime.fromisoformat(ts_str)
                        event.timestamp_ms = int(dt.timestamp() * 1000)
                    except:
                        event.timestamp_ms = int(time.time() * 1000)

                    event.source = log.get("processImagePath", "macos_system").split("/")[-1]
                    event.text_payload = log.get("eventMessage", "")
                    
                    # Metadata
                    event.metadata["subsystem"] = log.get("subsystem", "")
                    event.metadata["category"] = log.get("category", "")
                    event.metadata["processID"] = str(log.get("processID", ""))
                    event.metadata["type"] = log.get("messageType", "")
                    
                    sender.send(event.SerializeToString())
                    # print(f"Sent log from {event.source}: {event.text_payload[:50]}...")
                    
            except json.JSONDecodeError:
                pass
                
    except KeyboardInterrupt:
        print("\nStopping ingestion...")
        process.terminate()

if __name__ == "__main__":
    # Optional: Filter for interesting stuff (e.g. errors or specific subsystem)
    # predicate = 'messageType == "error" or messageType == "fault"'
    # ingest_logs(predicate)
    ingest_logs()

