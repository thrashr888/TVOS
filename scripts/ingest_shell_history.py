import time
import os
import zmq
import uuid
import re
from tvos.protos.events_pb2 import EventPayload
from tvos.config import Config

def follow(thefile):
    """Generator that yields new lines in a file"""
    # Go to the end of the file
    thefile.seek(0, 2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def ingest_shell_history():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)
    sender.connect(f"tcp://{Config.ZMQ_HOST}:{Config.ZMQ_PULL_PORT}")
    
    history_path = os.getenv("SHELL_HISTORY_PATH")
    if not history_path:
        history_path = os.path.expanduser("~/.zsh_history")
        if not os.path.exists(history_path):
            history_path = os.path.expanduser("~/.bash_history")
            
    if not os.path.exists(history_path):
        print(f"Could not find shell history file at {history_path}")
        return

    print(f"Watching shell history at: {history_path}")
    
    # Zsh extended history format: : <timestamp>:<duration>;<command>
    # Bash might be different, but often just command or #timestamp\ncommand
    zsh_pattern = re.compile(r'^: (\d+):(\d+);(.*)$')
    
    try:
        with open(history_path, "r", errors="replace") as f:
            for line in follow(f):
                line = line.strip()
                if not line: continue
                
                event = EventPayload()
                event.event_id = str(uuid.uuid4())
                event.source = "shell_history"
                
                match = zsh_pattern.match(line)
                if match:
                    timestamp_sec = int(match.group(1))
                    duration = match.group(2)
                    command = match.group(3)
                    
                    event.timestamp_ms = timestamp_sec * 1000
                    event.text_payload = command
                    event.metadata["duration_sec"] = duration
                else:
                    # Fallback for bash or simple format
                    event.timestamp_ms = int(time.time() * 1000)
                    event.text_payload = line
                
                # Skip simple/sensitive commands? (Optional)
                # if event.text_payload.strip() in ["ls", "cd", "pwd"]: continue
                
                sender.send(event.SerializeToString())
                print(f"Captured command: {event.text_payload}")
                
    except KeyboardInterrupt:
        print("\nStopping shell history ingestion...")

if __name__ == "__main__":
    ingest_shell_history()

